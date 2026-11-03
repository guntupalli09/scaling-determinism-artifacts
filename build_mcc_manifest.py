"""
Phase 1 (follow-up study): build the independent MCC evaluation manifest.

Applies the documented inclusion/exclusion criteria (see
experiments/followup/READINESS_AND_CRITERIA.md, section 3) to the Stanford
Material Contracts Corpus exhibits under ``Benchmark - TC/``, draws a
deterministic stratified sample, and writes:

  manifest/candidates.csv    every exhibit with its include/exclude reason
  manifest/sample.csv        the stratified evaluation sample (with text SHA-256)
  manifest/composition.json  corpus composition before/after filtering
  manifest/MANIFEST.sha256   SHA-256 of sample.csv, to freeze in Git

Re-running with the same seed and corpus produces byte-identical output.

    python -m experiments.followup.build_mcc_manifest --per-type 100 --seed 20261016
"""
import argparse
import csv
import hashlib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from triagebench.html_extract import extract_primary  # noqa: E402

CORPUS_ROOT = REPO_ROOT / "Benchmark - TC"
OUT_DIR = Path(__file__).parent / "manifest"
CATEGORY_DIRS = ["Employement", "Services", "Purchases", "Lease"]

MIN_CHARS = 3_000      # below this an exhibit is a cover page, letter stub or failed extraction
MAX_CHARS = 400_000    # above this it is usually a credit facility / plan with schedules

# Exhibits filed under the "employment" label that are not bilateral agreements.
# Matched against the archive filename and the first 600 characters of text.
NON_AGREEMENT_PATTERNS = re.compile(
    r"equity\s*incentive|incentive\s*(award\s*)?plan|omnibus|stock\s*purchase\s*plan|\bespp\b|"
    r"\brsu\b|restricted\s*stock\s*unit|performance\s*share|option\s*(award|grant|agreement)|"
    r"form\s*of\s*(award|grant|rsu|restricted|option|performance)|deferred\s*compensation\s*plan|"
    r"bonus\s*plan|severance\s*plan|\bltip\b|annual\s*incentive|director\s*(rsa|compensation)",
    re.IGNORECASE,
)


def _text_for(doc_path: Path) -> str:
    try:
        return extract_primary(doc_path.read_bytes())
    except Exception:
        return ""


def _exclusion_reason(row, text: str, seen_hashes: set) -> str:
    if bool(row["amend"]) and not bool(row["restate"]):
        return "amendment_not_restated"
    if bool(row["termination"]):
        return "termination_agreement"
    if bool(row["joinder"]):
        return "joinder"
    if not text:
        return "extraction_failed"
    if len(text) < MIN_CHARS:
        return "too_short"
    if len(text) > MAX_CHARS:
        return "too_long"
    head = f"{row['archive_name']} {text[:600]}"
    if NON_AGREEMENT_PATTERNS.search(head):
        return "plan_or_award_not_agreement"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if digest in seen_hashes:
        return "duplicate_text"
    seen_hashes.add(digest)
    return ""


def build(per_type: int, seed: int) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    candidates = []
    seen_hashes: set = set()
    for category_dir in CATEGORY_DIRS:
        root = CORPUS_ROOT / category_dir / "archive"
        df = pd.read_parquet(root / "metadata.parquet").sort_values("archive_name")
        for _, row in df.iterrows():
            text = _text_for(root / "documents" / row["archive_name"])
            reason = _exclusion_reason(row, text, seen_hashes)
            candidates.append({
                "category": row["label"],
                "archive_name": row["archive_name"],
                "cik": str(row["cik"]),
                "company_name": row["company_name"],
                "date_filed": str(row["date_filed"]),
                "quarter": f"{row['year']}{row['quarter']}",
                "restated": bool(row["restate"]),
                "image_count": int(row["image_count"]),
                "chars": len(text),
                "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest() if text else "",
                "excluded_reason": reason,
            })

    # One exhibit per company per type, so a single issuer's drafting style cannot dominate.
    eligible_by_type = defaultdict(list)
    seen_company = set()
    for c in candidates:
        if c["excluded_reason"]:
            continue
        key = (c["category"], c["cik"])
        if key in seen_company:
            c["excluded_reason"] = "same_company_already_eligible"
            continue
        seen_company.add(key)
        eligible_by_type[c["category"]].append(c)

    # Stratify by filing quarter within each type; take everything when the pool is smaller.
    rng = random.Random(seed)
    sample = []
    for category in sorted(eligible_by_type):
        pool = eligible_by_type[category]
        if len(pool) <= per_type:
            sample.extend(pool)
            continue
        by_quarter = defaultdict(list)
        for c in pool:
            by_quarter[c["quarter"]].append(c)
        quarters = sorted(by_quarter)
        for i, q in enumerate(quarters):
            share = round(per_type * len(by_quarter[q]) / len(pool))
            if i == len(quarters) - 1:
                share = per_type - sum(1 for s in sample if s["category"] == category)
            sample.extend(rng.sample(sorted(by_quarter[q], key=lambda c: c["archive_name"]), share))
    sample.sort(key=lambda c: (c["category"], c["archive_name"]))
    for i, c in enumerate(sample, 1):
        c["doc_id"] = f"mcc_{c['category'][:3]}_{i:04d}"

    fields = [k for k in candidates[0] if k != "doc_id"]
    with open(OUT_DIR / "candidates.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(candidates)
    with open(OUT_DIR / "sample.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["doc_id"] + fields)
        w.writeheader()
        w.writerows(sample)
    manifest_hash = hashlib.sha256((OUT_DIR / "sample.csv").read_bytes()).hexdigest()
    (OUT_DIR / "MANIFEST.sha256").write_text(f"{manifest_hash}  sample.csv\n")

    composition = {
        "seed": seed,
        "per_type_target": per_type,
        "raw_by_type": dict(Counter(c["category"] for c in candidates)),
        "exclusions": {k: v for k, v in sorted(Counter(c["excluded_reason"] for c in candidates if c["excluded_reason"]).items())},
        "eligible_by_type": {k: len(v) for k, v in sorted(eligible_by_type.items())},
        "sample_by_type": dict(Counter(c["category"] for c in sample)),
        "sample_by_quarter": dict(sorted(Counter(c["quarter"] for c in sample).items())),
        "sample_distinct_companies": len({c["cik"] for c in sample}),
        "sample_restated": sum(c["restated"] for c in sample),
        "sample_chars_median": sorted(c["chars"] for c in sample)[len(sample) // 2] if sample else 0,
        "manifest_sha256": manifest_hash,
    }
    (OUT_DIR / "composition.json").write_text(json.dumps(composition, indent=2) + "\n")
    return composition


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--per-type", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20261016)
    args = parser.parse_args()
    print(json.dumps(build(args.per_type, args.seed), indent=2))
