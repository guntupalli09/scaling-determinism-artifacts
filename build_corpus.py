"""
Phase 1: assemble and freeze the follow-up evaluation corpus (v1).

Slices
  mcc_*         MCC 2026 Q1-Q2 stratified sample (manifest/sample.csv). Unseen by every
                release up to v7.2.0; development data for later engine states.
  nda           ContractNLI test split (123 real NDAs, gold labels for 17 hypotheses).
  licensing     All CUAD license / IP agreements (gold labels for 41 CUAD categories).
  cuad_test     Full CUAD test split (102 contracts): the paired-comparison set for the
                CUAD comparator, which was trained on the CUAD train split only.

Writes corpus/manifest.csv (+ MANIFEST.sha256). Document texts go to
corpus/texts/ (gitignored, regenerable from the sources and the manifest hashes).

    python -m experiments.followup.build_corpus
"""
import csv
import hashlib
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from triagebench.html_extract import extract_primary  # noqa: E402

FOLLOWUP = Path(__file__).parent
EXTERNAL = FOLLOWUP / "external"
OUT = FOLLOWUP / "corpus"
TEXTS = OUT / "texts"
MCC_DIRS = {"employment": "Employement", "services": "Services", "purchase": "Purchases", "lease": "Lease"}
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "real_contracts"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _norm_key(text: str) -> str:
    """Whitespace/case-insensitive fingerprint used only for overlap checks."""
    return _sha(re.sub(r"\s+", " ", text).strip().lower()[:20000])


def _write(doc_id: str, text: str) -> str:
    (TEXTS / f"{doc_id}.txt").write_text(text, encoding="utf-8")
    return _sha(text)


def mcc_rows():
    for r in csv.DictReader(open(FOLLOWUP / "manifest" / "sample.csv", encoding="utf-8")):
        path = REPO_ROOT / "Benchmark - TC" / MCC_DIRS[r["category"]] / "archive" / "documents" / r["archive_name"]
        text = extract_primary(path.read_bytes())
        yield {"doc_id": r["doc_id"], "slice": f"mcc_{r['category']}", "doc_type": r["category"],
               "source": "MCC", "source_ref": r["archive_name"], "split": "eval",
               "has_gold": "no", "text": text}


def contractnli_rows():
    data = json.load(open(EXTERNAL / "contract-nli" / "test.json", encoding="utf-8"))
    for i, d in enumerate(sorted(data["documents"], key=lambda d: d["id"]), 1):
        yield {"doc_id": f"cnli_{d['id']:04d}", "slice": "nda", "doc_type": "nda",
               "source": "ContractNLI", "source_ref": d["file_name"], "split": "test",
               "has_gold": "contractnli", "text": d["text"]}


def _cuad_types():
    types = {}
    for root, _, files in os.walk(EXTERNAL / "cuad" / "CUAD_v1" / "full_contract_pdf"):
        for f in files:
            types[os.path.splitext(f)[0].lower()] = Path(root).name
    return types


def _cuad_contexts():
    out = {}
    for split, name in (("test", "test.json"), ("train", "train_separate_questions.json")):
        for d in json.load(open(EXTERNAL / "cuad_split" / name, encoding="utf-8"))["data"]:
            out[d["title"]] = (split, d["paragraphs"][0]["context"])
    return out


def cuad_rows():
    types, contexts = _cuad_types(), _cuad_contexts()
    titles = sorted(contexts)
    n = 0
    for title in titles:
        split, text = contexts[title]
        ctype = types.get(title.lower(), "")
        is_license = ctype in ("License_Agreements", "IP") or re.search(r"licen", title, re.I)
        if is_license:
            n += 1
            yield {"doc_id": f"cuad_lic_{n:03d}", "slice": "licensing", "doc_type": "licensing",
                   "source": "CUAD", "source_ref": title, "split": split, "has_gold": "cuad", "text": text}
    m = 0
    for title in titles:
        split, text = contexts[title]
        if split == "test":
            m += 1
            yield {"doc_id": f"cuad_test_{m:03d}", "slice": "cuad_test", "doc_type": types.get(title.lower(), "other"),
                   "source": "CUAD", "source_ref": title, "split": "test", "has_gold": "cuad", "text": text}


def build():
    TEXTS.mkdir(parents=True, exist_ok=True)
    fixture_keys = {_norm_key(p.read_text(encoding="utf-8", errors="ignore"))
                    for p in FIXTURES.rglob("*") if p.is_file() and p.suffix in (".txt", ".htm", ".html")}
    rows, seen = [], {}
    for gen in (mcc_rows(), contractnli_rows(), cuad_rows()):
        for r in gen:
            text = r.pop("text")
            key = _norm_key(text)
            r["chars"] = len(text)
            r["text_sha256"] = _write(r["doc_id"], text)
            # The licensing and cuad_test slices may legitimately share CUAD documents.
            r["duplicate_of"] = seen.get(key, "") if r["slice"] != "cuad_test" else ""
            r["in_dev_fixtures"] = "yes" if key in fixture_keys else "no"
            seen.setdefault(key, r["doc_id"])
            rows.append(r)
    fields = ["doc_id", "slice", "doc_type", "source", "source_ref", "split", "has_gold",
              "chars", "text_sha256", "duplicate_of", "in_dev_fixtures"]
    with open(OUT / "manifest.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    digest = hashlib.sha256((OUT / "manifest.csv").read_bytes()).hexdigest()
    (OUT / "MANIFEST.sha256").write_text(f"{digest}  manifest.csv\n")
    summary = {}
    for r in rows:
        s = summary.setdefault(r["slice"], {"docs": 0, "with_gold": 0, "duplicates": 0, "in_dev_fixtures": 0})
        s["docs"] += 1
        s["with_gold"] += r["has_gold"] != "no"
        s["duplicates"] += bool(r["duplicate_of"])
        s["in_dev_fixtures"] += r["in_dev_fixtures"] == "yes"
    result = {"manifest_sha256": digest, "slices": summary, "total_rows": len(rows)}
    (OUT / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
