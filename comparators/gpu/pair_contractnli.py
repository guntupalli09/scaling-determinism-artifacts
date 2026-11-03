"""
Pair Span NLI BERT predictions with the v7.2.0 engine on identical (NDA, hypothesis) units.
Refuses to run unless the comparator's Step A passed. Uses the same draft mapping
(comparators/label_mapping.json, PRELIMINARY_MAPPING_PENDING_REVIEW) and gold labels as
evaluate_paired.py; writes per-unit pairs and an exact McNemar test.

    python pair_contractnli.py --result <prefix>result.json --step-a <dir>/step_a_result.json --out <dir>
"""
import argparse
import csv
import json
import sys
from pathlib import Path

F = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(F.parents[1]))
from experiments.followup.stats import mcnemar_exact, prf  # noqa: E402


def main(a):
    if json.load(open(a.step_a))["status"] != "STEP_A_PASS":
        sys.exit("Step A did not pass: comparator results must not be reported (protocol).")
    pred = {d["file_name"]: d["annotation_sets"][0]["annotations"] for d in json.load(open(a.result))}
    gold = {d["file_name"]: d["annotation_sets"][0]["annotations"]
            for d in json.load(open(F / "external/contract-nli/test.json"))["documents"]}
    mapping = json.load(open(F / "comparators/label_mapping.json"))["contractnli"]
    engine = {}
    for r in csv.DictReader(open(F / "runs/analysis/v7.2.0/units_contractnli.csv")):
        engine[(r["doc_id"], r["category"])] = r["engine"] == "True"
    man = {r["doc_id"]: r["source_ref"] for r in csv.DictReader(open(F / "corpus/manifest.csv")) if r["slice"] == "nda"}
    rows = []
    for doc_id, fname in man.items():
        for hyp, cfg in mapping.items():
            g = gold[fname][hyp]["choice"] == cfg["choice"]
            rows.append({"doc_id": doc_id, "hypothesis": hyp, "gold": g, "engine": engine[(doc_id, hyp)],
                         "span_nli_bert": pred[fname][hyp]["choice"] == cfg["choice"]})
    out = Path(a.out)
    with open(out / "paired_units_engine_vs_span_nli_bert.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    def m(key):
        tp = sum(r["gold"] and r[key] for r in rows)
        fp = sum((not r["gold"]) and r[key] for r in rows)
        fn = sum(r["gold"] and not r[key] for r in rows)
        return prf(tp, fp, fn)
    res = {"units": len(rows), "engine": m("engine"), "span_nli_bert": m("span_nli_bert"),
           "mcnemar_correctness": mcnemar_exact([r["engine"] == r["gold"] for r in rows],
                                                [r["span_nli_bert"] == r["gold"] for r in rows]),
           "status": "PRELIMINARY_MAPPING_PENDING_REVIEW"}
    (out / "paired_result.json").write_text(json.dumps(res, indent=2, default=str) + "\n")
    print(json.dumps(res, indent=2, default=str)[:2000])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--result", required=True)
    p.add_argument("--step-a", required=True)
    p.add_argument("--out", required=True)
    main(p.parse_args())
