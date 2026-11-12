"""
CUAD comparator — Step A scorer (reproduce published metrics on the CUAD test split).

PRE-REGISTERED (written and committed 2026-10-17, before any complete prediction set existed):
  * Scoring: the official CUAD evaluate.py (external/cuad_evaluate.py, TheAtticusProject/cuad
    main branch) functions get_answers / get_precisions_recalls / get_prec_at_recall / get_aupr,
    imported unmodified.
  * Completeness: every one of the 4,182 test question ids must have an n-best list; otherwise
    the script refuses to score (no partial results).
  * Pass criterion vs. CUAD paper Table 2 (Hendrycks et al., 2021), RoBERTa-base:
        |AUPR - 42.6| <= 3.0 points  AND  |P@80R - 31.1| <= 5.0 points
    Tolerance rationale: the checkpoint is a community upload and our inference re-implements the
    HF SQuAD-v2 post-processing, so small differences are expected; larger ones mean the
    comparator is not the published system. Outcome is reported as-is; no tuning toward the
    target is permitted (decoding settings are frozen in cuad_qa.py).

    python comparators/cuad_step_a.py --pred-dir runs/comparators/cuad_roberta-base --model roberta-base
"""
import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PUBLISHED = {"roberta-base": {"aupr": 42.6, "p_at_80r": 31.1, "p_at_90r": 0.0},
             "roberta-large": {"aupr": 48.2, "p_at_80r": 38.1, "p_at_90r": 0.0},
             "deberta-v2-xlarge": {"aupr": 47.8, "p_at_80r": 44.0, "p_at_90r": 17.8}}
TOL = {"aupr": 3.0, "p_at_80r": 5.0}


def load_official():
    import os
    os.chdir(HERE.parent / "external")  # evaluate.py reads category_descriptions.csv relative to CWD
    spec = importlib.util.spec_from_file_location("cuad_eval", HERE.parent / "external" / "cuad_evaluate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(a):
    a.pred_dir = str(Path(a.pred_dir).resolve())
    ev = load_official()
    test = json.load(open(HERE.parent / "external/cuad_split/test.json", encoding="utf-8"))
    gt = ev.get_answers(test)
    nbest = {}
    for line in open(Path(a.pred_dir).resolve() / "nbest_partial.jsonl", encoding="utf-8"):
        r = json.loads(line)
        nbest[r["id"]] = [{"text": x["text"], "probability": x["probability"]} for x in r["nbest"]]
    missing = sorted(set(gt) - set(nbest))
    out = {"model": a.model, "checked_at": datetime.now(timezone.utc).isoformat(), "questions_expected": len(gt),
           "questions_present": len(set(gt) & set(nbest)), "published": PUBLISHED[a.model], "tolerance": TOL}
    if missing:
        out["status"] = "INCOMPLETE_NOT_SCORED"
        out["missing"] = len(missing)
        print(json.dumps(out, indent=2))
        sys.exit(2)
    precisions, recalls, confs = ev.get_precisions_recalls(nbest_to_preds(nbest), gt)
    p80, _ = ev.get_prec_at_recall(precisions, recalls, confs, recall_thresh=0.8)
    p90, _ = ev.get_prec_at_recall(precisions, recalls, confs, recall_thresh=0.9)
    aupr = ev.get_aupr(precisions, recalls)
    got = {"aupr": 100 * aupr, "p_at_80r": 100 * p80, "p_at_90r": 100 * p90}
    pub = PUBLISHED[a.model]
    ok = abs(got["aupr"] - pub["aupr"]) <= TOL["aupr"] and abs(got["p_at_80r"] - pub["p_at_80r"]) <= TOL["p_at_80r"]
    out.update({"reproduced": got, "delta": {k: got[k] - pub[k] for k in got},
                "status": "STEP_A_PASS" if ok else "STEP_A_FAIL"})
    (Path(a.pred_dir) / "step_a_result.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


def nbest_to_preds(nbest):
    # get_precisions_recalls expects the raw n-best dict and thresholds it internally.
    return nbest


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--pred-dir", required=True)
    p.add_argument("--model", required=True, choices=sorted(PUBLISHED))
    main(p.parse_args())
