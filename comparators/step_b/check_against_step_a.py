"""
Pre-flight check for a CUAD Step B session: run the Step B harness (cuad_step_b.py) on the two smallest CUAD-test
contracts and compare with the model's committed corrected Step A predictions on the same contracts (identical
texts, questions and procedure). Must agree on every top answer, with probabilities within 0.01 (GPU numerics;
the Step A sample validation saw at most 0.0035), or the session does not start.

For models whose Step B skips the cuad_test slice, this is what ties the reused Step A predictions to the
harness that produces the rest of the corpus.

    python check_against_step_a.py --model roberta-large --out DIR
"""
import argparse
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cuad_step_b as b  # noqa: E402

D = b.F / "runs/diagnostics/cuad"
STEP_A = {"roberta-large": D / "kaggle_v5_20261019T1954Z_roberta-large/diag_state/corrected_roberta-large/nbest_partial.jsonl.gz",
          "deberta-v2-xlarge": D / "modal_20261020T2240Z_deberta_resume/nbest_partial.jsonl.gz"}
DOCS = ["cuad_test_074", "cuad_test_070"]       # the two smallest CUAD-test contracts
TOL = 0.01


def main(a):
    import torch
    from transformers import AutoModelForQuestionAnswering, AutoTokenizer
    hub = f"akdeniz27/{a.model}-cuad"
    rows, qs = b.corpus()
    by = {r["doc_id"]: r for r in rows}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(hub, use_fast=False)
    model = AutoModelForQuestionAnswering.from_pretrained(hub).eval().to(device)
    b.infer_chunk(b.squad_dict({"units": [[d, list(qs)] for d in DOCS]}, by, qs), out, tok, model, device, 16, 2)
    got = json.load(gzip.open(out / "nbest.json.gz", "rt"))
    ref = {}
    src = STEP_A[a.model]
    if not src.exists():                         # Kaggle unpacks .gz files in uploaded datasets
        src = src.with_suffix("")
    for line in (gzip.open(src, "rt") if src.suffix == ".gz" else open(src)):
        r = json.loads(line)
        ref[r["id"]] = r["nbest"]
    agree, maxdp, n = 0, 0.0, 0
    for uid, nb in got.items():
        doc_id, cat = uid.split("__", 1)
        rn = ref[f"{by[doc_id]['source_ref']}__{cat}"]
        n += 1
        agree += nb[0]["text"] == rn[0]["text"]
        maxdp = max(maxdp, abs(nb[0]["probability"] - rn[0]["probability"]))
    res = {"model": a.model, "device": device, "questions": n, "top_agree": agree, "max_abs_dp_top": maxdp,
           "tolerance": TOL, "ok": agree == n and maxdp <= TOL}
    (out / "check.json").write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps(res))
    sys.exit(0 if res["ok"] else 1)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True, choices=sorted(STEP_A))
    p.add_argument("--out", required=True)
    main(p.parse_args())
