"""
ContractNLI diagnostic (DIAG-CNLI-1): recompute evidence mAP under both aggregations independently from
the raw predictions (test_result.json) and the gold test split. It does not use the authors' evaluator.

  pooled  : one AP over all (document, hypothesis, span) items, pooled over documents and labels.
            Equals the authors' micro_label_micro_doc.span.map; this is the key pre-registered in
            comparators/gpu/contractnli_step_a.py.
  per-query: AP per (document, hypothesis) query, a ranking of that document's spans, then the mean over
            queries. Equals the authors' micro_label_macro_doc.span.map. This is the paper's
            "mean average precision (mAP) that is micro averaged over labels" (Koreeda & Manning 2021, §4.2).

Evidence is scored only where the hypothesis is not NotMentioned, as in the authors' evaluation.py.
This changes no pre-registered result.

    python contractnli_map_aggregations.py --result <test_result.json> --metrics <test_metrics.json> --out <json>
"""
import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import average_precision_score

F = Path(__file__).resolve().parents[2]


def main(a):
    pred = {d["id"]: d for d in json.load(open(a.result))}
    gold = json.load(open(F / "external/contract-nli/test.json"))
    ys, ps, aps = [], [], []
    for doc in gold["documents"]:
        ann = doc["annotation_sets"][0]["annotations"]
        pa = pred[doc["id"]]["annotation_sets"][0]["annotations"]
        for lab, g in ann.items():
            if g["choice"] == "NotMentioned":
                continue
            y = np.zeros(len(doc["spans"]))
            y[g["spans"]] = 1
            p = np.array(pa[lab]["span_probs"])
            ys.append(y)
            ps.append(p)
            aps.append(average_precision_score(y, p))
    m = json.load(open(a.metrics))
    out = {
        "pooled_map_independent": float(average_precision_score(np.concatenate(ys), np.concatenate(ps))),
        "pooled_map_authors_evaluator": m["micro_label_micro_doc"]["span"]["map"],
        "per_query_map_independent": float(np.mean(aps)),
        "per_query_map_authors_evaluator": m["micro_label_macro_doc"]["span"]["map"],
        "queries": len(aps),
        "paper_definition": "mAP micro averaged over labels (per-query mean AP); Koreeda & Manning 2021, sec. 4.2",
        "paper_target_bert_base": 0.885,
        "preregistered_key": "micro_label_micro_doc.span.map (pooled)",
        "status_note": "Diagnostic only. The pre-registered Step A result (STEP_A_FAIL, pooled mAP .751) is unchanged.",
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--result", required=True)
    p.add_argument("--metrics", required=True)
    p.add_argument("--out", required=True)
    main(p.parse_args())
