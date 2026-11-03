"""
Independent reproduction of the Phase 5 injection-attributable result (REPRO-P5-1).

Shares NO code with phase5_security.py / phase5_benign_control.py / release_worker.py:
  * release trees are materialised afresh with `git archive` into new temporary directories;
  * a separate in-process harness imports RuleEngine directly and returns rule_id multisets;
  * insertion positions are recomputed from fresh baseline analyses (end of the earliest finding);
  * the attributable criterion is re-implemented: multiset(injected) != multiset(benign control).
Only the inputs are shared: corpus texts (verified against corpus/manifest.csv hashes) and the
payload / neutral strings recorded in the original runs' meta.json. Historical outputs are read,
never written.

    python -m experiments.followup.repro_injection_independent
"""
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

F = Path(__file__).resolve().parent
REPO = F.parents[1]
ORIG_P5 = F / "runs/phase5/20261017T013302Z"
ORIG_CTRL = F / "runs/phase5_control/20261017T021750Z"
RELEASES = {"v7.2.0": "51d709e8", "v1.0.3-iccs": "ae097e74"}

HARNESS = r'''
import sys, json, io, contextlib
sys.path.insert(0, ".")
with contextlib.redirect_stdout(io.StringIO()):
    from rules_engine import RuleEngine
    eng = RuleEngine()
out = []
for item in json.loads(sys.stdin.read()):
    with contextlib.redirect_stdout(io.StringIO()):
        res = eng.analyze(item["text"])
    fs = res["findings"]
    ids = [(f["rule_id"] if isinstance(f, dict) else f.rule_id) for f in fs]
    ends = [(f["end_index"] if isinstance(f, dict) else f.end_index) for f in fs]
    out.append({"key": item["key"], "ids": ids, "first_end": min(ends) if ends else None})
print(json.dumps(out))
'''


def materialise(commit: str) -> Path:
    d = Path(tempfile.mkdtemp(prefix=f"repro_{commit}_"))
    arch = subprocess.run(["git", "archive", commit, "--", ".", ":(exclude)Benchmark - TC", ":(exclude)static",
                           ":(exclude)artifacts", ":(exclude)experiments", ":(exclude)tests"],
                          cwd=REPO, capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(d)], input=arch, check=True)
    return d


def analyse(tree: str, items: list) -> list:
    p = subprocess.run([sys.executable, "-I", "-c", HARNESS], cwd=tree, input=json.dumps(items),
                       capture_output=True, text=True, timeout=7200)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-2000:])
    return json.loads(p.stdout.strip().splitlines()[-1])


CACHE = Path(tempfile.gettempdir()) / "repro_p5_cache"  # resumability only; keyed by commit + exact batch input


def run_batches(tree, items, commit, workers=3, size=60):
    CACHE.mkdir(exist_ok=True)
    batches = [items[i:i + size] for i in range(0, len(items), size)]
    keys = [hashlib.sha256((commit + json.dumps(b, sort_keys=True)).encode()).hexdigest() for b in batches]
    todo = [(k, b) for k, b in zip(keys, batches) if not (CACHE / k).exists()]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(analyse, str(tree), b): k for k, b in todo}
        for fut, k in futs.items():
            (CACHE / k).write_text(json.dumps(fut.result()))
    out = []
    for k in keys:
        out += json.loads((CACHE / k).read_text())
    return {r["key"]: r for r in out}


def insert(text, payload, pos, first_end):
    if pos == "end":
        return text + "\n\n" + payload + "\n"
    k = first_end if first_end is not None else len(text) // 2
    return text[:k] + " " + payload + " " + text[k:]


def main(releases):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = F / "runs/repro_injection" / stamp
    out.mkdir(parents=True, exist_ok=False)
    meta = json.load(open(ORIG_P5 / "meta.json"))
    payloads = meta["patterns"]
    neutral = json.load(open(ORIG_CTRL / "meta.json"))["neutral_text"]
    neutral = neutral if isinstance(neutral, str) else list(neutral.values())[0]
    man = list(csv.DictReader(open(F / "corpus/manifest.csv", encoding="utf-8")))
    texts = {}
    for r in man:
        t = (F / "corpus/texts" / f"{r['doc_id']}.txt").read_text(encoding="utf-8")
        assert hashlib.sha256(t.encode()).hexdigest() == r["text_sha256"], r["doc_id"]
        texts[r["doc_id"]] = t
    orig = {}
    for r in csv.DictReader(open(ORIG_CTRL / "attribution.csv")):
        orig[(r["release"], r["doc_id"], r["payload"], r["position"])] = r["injection_attributable"] == "True"
    summary, trees = {}, {}
    try:
        for label, commit in ((k, RELEASES[k]) for k in releases):
            tree = trees[label] = materialise(commit)
            base = run_batches(tree, [{"key": d, "text": t} for d, t in texts.items()], commit)
            items = []
            for d, t in texts.items():
                fe = base[d]["first_end"]
                for pos in ("end", "in_clause"):
                    items.append({"key": f"B0|{d}|{pos}", "text": insert(t, neutral, pos, fe)})
                    for pn, pl in payloads.items():
                        items.append({"key": f"{pn}|{d}|{pos}", "text": insert(t, pl, pos, fe)})
            res = run_batches(tree, items, commit)
            rows, agree, disagree = [], 0, []
            for d in texts:
                for pos in ("end", "in_clause"):
                    ben = Counter(res[f"B0|{d}|{pos}"]["ids"])
                    for pn in payloads:
                        inj = Counter(res[f"{pn}|{d}|{pos}"]["ids"])
                        attr = inj != ben
                        o = orig[(label, d, pn, pos)]
                        agree += attr == o
                        if attr != o:
                            disagree.append([d, pn, pos, attr, o])
                        rows.append({"doc_id": d, "payload": pn, "position": pos, "attributable": attr,
                                     "removed": sorted((ben - inj).elements()), "added": sorted((inj - ben).elements())})
            with open(out / f"cases_{label}.csv", "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
            k = sum(r["attributable"] for r in rows)
            summary[label] = {"commit": commit, "cases": len(rows), "attributable": k, "rate": k / len(rows),
                              "case_level_agreement_with_original": agree, "disagreements": disagree[:50],
                              "n_disagreements": len(disagree),
                              "top_rules": Counter(x for r in rows if r["attributable"] for x in r["removed"] + r["added"]).most_common(6)}
            print(label, json.dumps({k2: v for k2, v in summary[label].items() if k2 != "disagreements"}))
    finally:
        for t in trees.values():
            shutil.rmtree(t, ignore_errors=True)
    doc = {"experiment_id": "REPRO-P5-1", "timestamp": stamp, "original": [str(ORIG_P5.relative_to(F)), str(ORIG_CTRL.relative_to(F))],
           "git_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip(),
           "corpus_manifest_sha256": (F / "corpus/MANIFEST.sha256").read_text().split()[0], "summary": summary}
    (out / "summary.json").write_text(json.dumps(doc, indent=2) + "\n")
    print(out)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--releases", nargs="+", default=list(RELEASES), choices=list(RELEASES))
    main(ap.parse_args().releases)
