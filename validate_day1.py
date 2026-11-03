"""
Independent validation of the Day 1 results (Day 2, item 4).

Deliberately avoids the code paths that produced the results where it can:
  - corpus texts are re-derived from the original sources and re-hashed;
  - every ruleset hash is recomputed from a FRESH `git show` materialisation (not the
    .releases/ cache used on Day 1);
  - the v7.2.0 baseline commit is checked against the commit that introduced the MCC corpus;
  - execution counts and determinism are recounted from the raw results.jsonl files;
  - a document sample is re-executed directly and compared finding-by-finding;
  - CUAD gold labels are re-derived from a second source (master_clauses.csv) and the
    precision/recall of two releases is recomputed with independent code.

    python -m experiments.followup.validate_day1   ->  runs/validation/day1_validation.json (+ .md)
"""
import ast
import csv
import hashlib
import json
import random
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
F = Path(__file__).parent
OUT = F / "runs" / "validation"
CHECKS = []


def check(name, ok, detail):
    CHECKS.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + " :: " + json.dumps(detail)[:300])


def sha(b):
    return hashlib.sha256(b).hexdigest()


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.strip()


# ---------------------------------------------------------------- 1. corpus manifest
def validate_corpus():
    man_bytes = (F / "corpus" / "manifest.csv").read_bytes()
    recorded = (F / "corpus" / "MANIFEST.sha256").read_text().split()[0]
    check("corpus.manifest_sha256_matches_recorded", sha(man_bytes) == recorded, {"recorded": recorded, "actual": sha(man_bytes)})
    rows = list(csv.DictReader(open(F / "corpus" / "manifest.csv", encoding="utf-8")))
    ids = [r["doc_id"] for r in rows]
    check("corpus.row_count_618", len(rows) == 618, {"rows": len(rows)})
    check("corpus.doc_ids_unique", len(set(ids)) == len(ids), {"duplicates": [k for k, v in Counter(ids).items() if v > 1]})
    bad = [r["doc_id"] for r in rows if sha((F / "corpus" / "texts" / f"{r['doc_id']}.txt").read_text(encoding="utf-8").encode()) != r["text_sha256"]]
    check("corpus.all_text_hashes_match", not bad, {"mismatches": bad[:20], "n_checked": len(rows)})
    check("corpus.slice_counts", Counter(r["slice"] for r in rows) == Counter(
        {"mcc_employment": 100, "mcc_services": 100, "mcc_purchase": 100, "mcc_lease": 32, "nda": 123, "licensing": 61, "cuad_test": 102}),
        dict(Counter(r["slice"] for r in rows)))

    # Re-derive texts from the ORIGINAL sources (independent of build_corpus.py).
    cnli = {d["file_name"]: d["text"] for d in json.load(open(F / "external/contract-nli/test.json", encoding="utf-8"))["documents"]}
    cuad = {}
    for name in ("test.json", "train_separate_questions.json"):
        for d in json.load(open(F / "external/cuad_split" / name, encoding="utf-8"))["data"]:
            cuad[d["title"]] = d["paragraphs"][0]["context"]
    mism = []
    for r in rows:
        if r["source"] == "ContractNLI":
            src = cnli[r["source_ref"]]
        elif r["source"] == "CUAD":
            src = cuad[r["source_ref"]]
        else:
            continue
        if sha(src.encode()) != r["text_sha256"]:
            mism.append(r["doc_id"])
    check("corpus.cnli_cuad_texts_rederived_from_source", not mism, {"mismatches": mism[:20]})
    # MCC: re-extract a random sample with the reference (independent) HTML extractor and
    # require near-equal length; byte-identity with the primary extractor is checked above.
    sys.path.insert(0, str(REPO))
    from triagebench.html_extract import extract_primary, extract_reference
    dirs = {"employment": "Employement", "services": "Services", "purchase": "Purchases", "lease": "Lease"}
    mcc = [r for r in rows if r["source"] == "MCC"]
    sample = random.Random(1).sample(mcc, 25)
    diffs = []
    for r in sample:
        raw = (REPO / "Benchmark - TC" / dirs[r["doc_type"]] / "archive/documents" / r["source_ref"]).read_bytes()
        p = extract_primary(raw)
        ref = extract_reference(raw)
        diffs.append({"doc_id": r["doc_id"], "primary_hash_ok": sha(p.encode()) == r["text_sha256"],
                      "len_primary": len(p), "len_reference": len(ref),
                      "len_diff_pct": round(100 * abs(len(p) - len(ref)) / max(1, len(p)), 2)})
    check("corpus.mcc_sample_reextract_hash_ok", all(d["primary_hash_ok"] for d in diffs), {"n": len(diffs)})
    check("corpus.mcc_sample_independent_extractor_len_within_8pct",
          all(d["len_diff_pct"] <= 8 for d in diffs), {"max_len_diff_pct": max(d["len_diff_pct"] for d in diffs)})
    # Selection-rule re-check on the MCC sample: one per company per type, no bare amendments.
    import pandas as pd
    meta = {}
    for t, d in dirs.items():
        df = pd.read_parquet(REPO / "Benchmark - TC" / d / "archive/metadata.parquet")
        for _, m in df.iterrows():
            meta[m["archive_name"]] = m
    viol = [r["doc_id"] for r in mcc if bool(meta[r["source_ref"]]["amend"]) and not bool(meta[r["source_ref"]]["restate"])]
    check("corpus.mcc_no_bare_amendments", not viol, {"violations": viol})
    comp = Counter((r["doc_type"], str(meta[r["source_ref"]]["cik"])) for r in mcc)
    check("corpus.mcc_one_per_company_per_type", max(comp.values()) == 1, {"max_per_company_type": max(comp.values())})


# ---------------------------------------------------------------- 2. ruleset hashes, fresh
DUMP = r'''
import dataclasses, enum, hashlib, io, json, sys, contextlib
sys.path.insert(0, ".")
def plain(o):
    if dataclasses.is_dataclass(o) and not isinstance(o, type):
        return {f.name: plain(getattr(o, f.name)) for f in dataclasses.fields(o)}
    if isinstance(o, enum.Enum): return plain(o.value)
    if isinstance(o, dict): return {str(k): plain(v) for k, v in o.items()}
    if isinstance(o, (set, frozenset)): return sorted((plain(v) for v in o), key=lambda x: json.dumps(x, sort_keys=True))
    if isinstance(o, (list, tuple)): return [plain(v) for v in o]
    if hasattr(o, "pattern") and hasattr(o, "flags"): return {"regex": o.pattern, "flags": int(o.flags)}
    if isinstance(o, (str, int, float, bool)) or o is None: return o
    return repr(o)
with contextlib.redirect_stdout(io.StringIO()):
    from rules_engine import RuleEngine
    rules = [plain(r) for r in RuleEngine().rules]
for r in rules:  # set-semantic fields are canonicalised by sorting (see release_worker.SET_SEMANTIC_FIELDS)
    if isinstance(r.get("contract_types"), list):
        r["contract_types"] = sorted(r["contract_types"], key=lambda x: json.dumps(x, sort_keys=True))
rules.sort(key=lambda r: r.get("rule_id", ""))
c = json.dumps(rules, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
print(json.dumps({"n": len(rules), "sha": hashlib.sha256(c.encode()).hexdigest()}))
'''


def validate_releases():
    man = json.load(open(F / "releases" / "manifest_v2.json"))
    rows = []
    for rel in man:
        tmp = Path(tempfile.mkdtemp(prefix="rel_"))
        try:
            arch = subprocess.run(["git", "archive", rel["commit"], "--", ".", ":(exclude)Benchmark - TC", ":(exclude)static",
                                   ":(exclude)artifacts", ":(exclude)experiments", ":(exclude)tests"],
                                  cwd=REPO, capture_output=True, check=True).stdout
            subprocess.run(["tar", "-x", "-C", str(tmp)], input=arch, check=True)
            res = subprocess.run([sys.executable, "-I", "-c", DUMP], cwd=tmp, capture_output=True, text=True, timeout=600,
                                 env={"PYTHONHASHSEED": "12345", "PATH": "/usr/bin:/bin"})
            got = json.loads(res.stdout.strip().splitlines()[-1])
            version = json.loads((tmp / "rules/version.json").read_text()).get("version")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        rows.append({"label": rel["label"], "commit": rel["commit"][:8], "date": rel["commit_date"], "version_json": version,
                     "rule_count": got["n"], "ruleset_sha256": got["sha"],
                     "matches_manifest": got["sha"] == rel["ruleset_sha256"] and got["n"] == rel["rule_count"]})
    check("releases.all_hashes_reproduce_from_fresh_checkout", all(r["matches_manifest"] for r in rows),
          {"mismatches": [r["label"] for r in rows if not r["matches_manifest"]]})
    iccs = next(r for r in rows if r["label"] == "v1.0.3-iccs")
    check("releases.iccs_state_has_25_rules", iccs["rule_count"] == 25, {"rule_count": iccs["rule_count"]})
    return rows


def version_drift_table():
    """Every commit that changed the rule engine while version.json said 7.2.0."""
    out = []
    log = git("log", "--format=%H %cI", "--", "rules_engine.py", "rules/")
    for line in log.splitlines():
        c, d = line.split()
        try:
            v = json.loads(git("show", f"{c}:rules/version.json")).get("version")
        except Exception:
            continue
        if v == "7.2.0":
            out.append({"commit": c[:8], "date": d})
    return out


def validate_baseline_precedes_mcc():
    first_mcc = git("log", "--diff-filter=A", "--format=%H %cI", "--", "Benchmark - TC/Employement/archive/metadata.parquet").splitlines()[-1]
    mcc_commit, mcc_date = first_mcc.split()
    base = json.load(open(F / "releases" / "manifest_v2.json"))
    b = next(r for r in base if r["label"] == "v7.2.0")
    tree_has_mcc = bool(git("ls-tree", "-d", "--name-only", b["commit"], "Benchmark - TC"))
    is_ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", b["commit"], mcc_commit], cwd=REPO).returncode == 0
    detail = {"baseline_commit": b["commit"][:8], "baseline_commit_date": b["commit_date"],
              "mcc_introduced_commit": mcc_commit[:8], "mcc_introduced_date": mcc_date,
              "baseline_tree_contains_mcc": tree_has_mcc, "baseline_is_ancestor_of_mcc_commit": is_ancestor}
    check("baseline.v7.2.0_precedes_mcc_introduction",
          (not tree_has_mcc) and is_ancestor and b["commit_date"] < mcc_date, detail)
    return detail


# ---------------------------------------------------------------- 3. execution counts / determinism
def validate_runs():
    total, per = 0, {}
    labels = ["v1.0.3-iccs", "v1.0.3", "v2.0.0", "v2.1.0", "v3.0.0", "v4.0.0", "v5.0.0", "v6.0.0", "v7.0.0", "v7.1.0",
              "v7.2.0", "v7.2.0+20294216"]
    for lab in labels:
        rows = [json.loads(l) for l in open(F / "runs" / lab / "results.jsonl", encoding="utf-8")]
        ids = [r["doc_id"] for r in rows]
        execs = sum(r["runs"] for r in rows)
        per[lab] = {"lines": len(rows), "unique_docs": len(set(ids)), "executions": execs,
                    "runs_per_doc": sorted({r["runs"] for r in rows}),
                    "docs_output_variance": sum(r["distinct_output_hashes"] > 1 for r in rows),
                    "docs_finding_variance": sum(r["distinct_finding_hashes"] > 1 for r in rows)}
        total += execs
    check("runs.no_duplicate_or_missing_docs", all(v["lines"] == v["unique_docs"] == 618 for v in per.values()),
          {k: (v["lines"], v["unique_docs"]) for k, v in per.items()})
    check("runs.total_executions_26574", total == 26574, {"total": total})
    check("runs.zero_variance_all_releases", all(v["docs_output_variance"] == 0 and v["docs_finding_variance"] == 0 for v in per.values()),
          {k: v["docs_output_variance"] for k, v in per.items()})
    return per, total


def validate_reexecution(n=30):
    """Re-run a sample directly (fresh process, fresh engine) and compare finding sets to stored results."""
    sys.path.insert(0, str(REPO))
    from experiments.followup.releases import by_label, run_worker
    out = {}
    for lab in ("v1.0.3-iccs", "v5.0.0", "v7.2.0"):
        stored = {json.loads(l)["doc_id"]: json.loads(l) for l in open(F / "runs" / lab / "results.jsonl", encoding="utf-8")}
        sample = random.Random(7).sample(sorted(stored), n)
        docs = [{"doc_id": d, "path": str((F / "corpus/texts" / f"{d}.txt").resolve())} for d in sample]
        res = run_worker(by_label(lab), {"mode": "analyze", "runs": 1, "docs": docs})
        mism = [r["doc_id"] for r in res if r["finding_set_sha256"] != stored[r["doc_id"]]["finding_set_sha256"]
                or r["output_sha256"] != stored[r["doc_id"]]["output_sha256"]]
        out[lab] = {"n": n, "mismatches": mism}
    check("reexec.sample_matches_stored_outputs", all(not v["mismatches"] for v in out.values()), out)
    return out


# ---------------------------------------------------------------- 4. independent rescoring
def _norm(s):
    return "".join(ch for ch in s.lower() if ch.isalnum())


def validate_scoring():
    mapping = json.load(open(F / "comparators/label_mapping.json"))["cuad"]
    # Second gold source: master_clauses.csv (spans stored as python-list strings).
    mc = {}
    for r in csv.DictReader(open(F / "external/cuad/CUAD_v1/master_clauses.csv", encoding="utf-8")):
        key = _norm(r["Filename"].rsplit(".", 1)[0])
        cols = {_norm(k): v for k, v in r.items()}
        mc[key] = cols
    man = [r for r in csv.DictReader(open(F / "corpus/manifest.csv", encoding="utf-8")) if r["slice"] == "cuad_test"]
    agree, disagree, missing = 0, [], []
    gold2 = {}
    for r in man:
        cols = mc.get(_norm(r["source_ref"]))
        if cols is None:
            missing.append(r["doc_id"])
            continue
        for cat in mapping:
            if cat.startswith("_"):
                continue
            v = cols.get(_norm(cat))
            if v is None:
                missing.append(f"{r['doc_id']}:{cat}")
                continue
            try:
                spans = ast.literal_eval(v)
            except Exception:
                spans = [v] if v.strip() else []
            gold2[(r["doc_id"], cat)] = len(spans) > 0
    results = {}
    for lab in ("v1.0.3-iccs", "v7.2.0"):
        units = list(csv.DictReader(open(F / "runs/analysis" / lab / "units_cuad.csv", encoding="utf-8")))
        for u in units:
            g2 = gold2.get((u["doc_id"], u["category"]))
            if g2 is None:
                continue
            if (u["gold"] == "True") == g2:
                agree += 1
            else:
                disagree.append((u["doc_id"], u["category"]))
        # Recompute P/R from raw engine output + mapping + release rules (independent of units CSV).
        rules = set(next(r for r in json.load(open(F / "releases/manifest_v2.json")) if r["label"] == lab)["rule_ids"])
        fired = {json.loads(l)["doc_id"]: set(json.loads(l)["rule_ids_fired"]) for l in open(F / "runs" / lab / "results.jsonl")}
        tp = fp = fn = 0
        for (doc, cat), g in gold2.items():
            mapped = set(mapping[cat]["rules"]) & rules
            p = bool(fired[doc] & mapped)
            tp += g and p
            fp += (not g) and p
            fn += g and not p
        rep = json.load(open(F / "runs/analysis" / lab / "paired_report.json"))["cuad"]["engine_overall"]
        results[lab] = {"independent": {"tp": tp, "fp": fp, "fn": fn}, "reported": {k: rep[k] for k in ("tp", "fp", "fn")}}
    check("scoring.gold_test_json_vs_master_clauses_agree",
          not disagree, {"agree": agree, "disagree": len(disagree), "examples": disagree[:10], "missing": missing[:10]})
    check("scoring.independent_recount_matches_report",
          all(v["independent"] == v["reported"] for v in results.values()), results)
    return results


def main():
    global OUT
    OUT = OUT / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUT.mkdir(parents=True, exist_ok=False)  # never overwrite an earlier validation run
    started = datetime.now(timezone.utc).isoformat()
    validate_corpus()
    rel_rows = validate_releases()
    drift = version_drift_table()
    base = validate_baseline_precedes_mcc()
    per, total = validate_runs()
    reexec = validate_reexecution()
    scoring = validate_scoring()
    report = {"experiment_id": "VAL-DAY1", "started": started, "finished": datetime.now(timezone.utc).isoformat(),
              "git_head": git("rev-parse", "HEAD"), "checks": CHECKS, "release_table": rel_rows,
              "commits_labelled_7_2_0": drift, "baseline_vs_mcc": base, "runs": per, "total_executions": total,
              "reexecution": reexec, "scoring": scoring}
    (OUT / "day1_validation.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    lines = ["# Day 1 validation", "", f"Run {started} at HEAD `{report['git_head'][:8]}`.", "",
             "| Check | Status |", "|---|---|"] + [f"| {c['check']} | {c['status']} |" for c in CHECKS]
    lines += ["", "## Version-drift table (rule definitions recomputed from fresh checkouts)", "",
              "| Version label | Commit | Commit date | Rule count | Canonical ruleset SHA-256 |", "|---|---|---|---|---|"]
    lines += [f"| {r['version_json']} ({r['label']}) | `{r['commit']}` | {r['date'][:19]} | {r['rule_count']} | `{r['ruleset_sha256']}` |"
              for r in rel_rows]
    (OUT / "day1_validation.md").write_text("\n".join(lines) + "\n")
    print(f"\n{sum(c['status'] == 'PASS' for c in CHECKS)}/{len(CHECKS)} checks passed")


if __name__ == "__main__":
    main()
