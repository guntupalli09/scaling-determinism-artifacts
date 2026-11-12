"""
Phase 3 CUAD diagnostic job for a free Kaggle GPU session (DIAG-CUAD-2).
Diagnostic only: it never changes the pre-registered Step A results.

Per model (roberta-base, roberta-large, deberta-v2-xlarge), each step resumable from --state:
  1. Official reference: download the authors' release (Zenodo 4599830). Score their own
     nbest_predictions_.json with the UNCHANGED pre-registered scorer, as a sanity check of the scorer and
     test split.
  2. Weights: compare the community checkpoint used in the pre-registered run (akdeniz27/*-cuad)
     tensor by tensor with the official checkpoint.
  3. Pipeline validation: run the reference pipeline (cuad_reference_pipeline.py) on the fixed-seed
     sample. Compare it with the authors' predictions (top-answer agreement, max |Δp|).
  4. Corrected full run: cuad_reference_full.py on the whole test split, then the unchanged scorer
     (comparators/cuad_step_a.py, same thresholds). Reported as CORRECTED DIAGNOSTIC, never as Step A.

    python cuad_diag_kaggle.py --state /kaggle/working/diag_state --budget-hours 11
"""
import argparse
import gzip
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
F = HERE.parents[1]
REPO = F.parents[1]
MODELS = {"roberta-base": "akdeniz27/roberta-base-cuad", "roberta-large": "akdeniz27/roberta-large-cuad",
          "deberta-v2-xlarge": "akdeniz27/deberta-v2-xlarge-cuad"}
ZENODO = "https://zenodo.org/api/records/4599830/files/{}.zip/content"
SAMPLE = F / "runs/diagnostics/cuad/sample_seed20261018/titles.txt"


def log(state, **kw):
    path = state / "diag_log.jsonl"
    with open(path, "a") as fh:
        fh.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **kw}) + "\n")
    print(json.dumps(kw), flush=True)


def done(state, key):
    p = state / "diag_log.jsonl"
    return p.exists() and any(json.loads(l).get("step") == key and json.loads(l).get("ok") for l in open(p))


def score(pred_dir, model):
    r = subprocess.run([sys.executable, "comparators/cuad_step_a.py", "--pred-dir", str(pred_dir), "--model", model],
                       cwd=F, capture_output=True, text=True)
    res = Path(pred_dir) / "step_a_result.json"
    return json.loads(res.read_text()) if res.exists() else {"status": "NOT_SCORED", "stderr": r.stderr[-800:]}


def to_jsonl(nbest_json, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    nb = json.load(open(nbest_json))
    with open(out_dir / "nbest_partial.jsonl", "w") as fh:
        for k, v in nb.items():
            fh.write(json.dumps({"id": k, "nbest": [{"text": x["text"], "probability": x["probability"]} for x in v]}) + "\n")
    return nb


def official(state, tmp, key):
    zpath = tmp / f"{key}.zip"
    if not zpath.exists():
        # bounded: abort a stalled transfer (<100 kB/s for 5 min) and retry, so a stall cannot hang the session
        subprocess.run(["curl", "-fsSL", "--retry", "5", "--retry-delay", "30", "--connect-timeout", "60",
                        "--speed-limit", "100000", "--speed-time", "300", "-o", str(zpath), ZENODO.format(key)],
                       check=True, timeout=3 * 3600)
    odir = tmp / f"official_{key}"
    if not odir.exists():
        with zipfile.ZipFile(zpath) as z:
            z.extractall(odir)
    return next(odir.rglob("nbest_predictions_.json")).parent


def main(a):
    state, tmp = Path(a.state), Path(a.tmp)
    state.mkdir(parents=True, exist_ok=True)
    tmp.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + a.budget_hours * 3600
    for key, hub in MODELS.items():
        if key not in a.models:
            continue
        od = official(state, tmp, key)
        # 1. authors' own predictions through the unchanged scorer
        log(state, step=f"{key}:start", note="progress marker")
        if not done(state, f"{key}:official_score"):
            res = score_dir = state / f"official_{key}"
            to_jsonl(od / "nbest_predictions_.json", score_dir)
            res = score(score_dir, key)
            log(state, step=f"{key}:official_score", ok=True, status=res["status"], reproduced=res.get("reproduced"),
                published=res.get("published"))
            (score_dir / "nbest_partial.jsonl").unlink()   # the authors' file is not ours to redistribute in bulk
        # 2. weights: community upload vs official checkpoint
        if not done(state, f"{key}:weights"):
            import torch
            from transformers import AutoModelForQuestionAnswering
            o = AutoModelForQuestionAnswering.from_pretrained(str(od)).state_dict()
            c = AutoModelForQuestionAnswering.from_pretrained(hub).state_dict()
            common = [k for k in o if k in c and o[k].shape == c[k].shape]
            md = max((o[k].float() - c[k].float()).abs().max().item() for k in common)
            log(state, step=f"{key}:weights", ok=True, official_tensors=len(o), community_tensors=len(c),
                common=len(common), max_abs_diff=md)
            del o, c
        # 3. reference pipeline on the fixed sample vs the authors' predictions
        if not done(state, f"{key}:sample_validation"):
            sdir = state / f"sample_{key}"
            sdir.mkdir(parents=True, exist_ok=True)
            try:
                with open(sdir / "run.log", "w") as fh:
                    r = subprocess.run([sys.executable, str(HERE / "cuad_reference_pipeline.py"), "--model", hub,
                                        "--titles-file", str(SAMPLE), "--out", str(sdir)], cwd=F, stdout=fh,
                                       stderr=subprocess.STDOUT, timeout=3600)   # minutes on a T4
            except subprocess.TimeoutExpired:
                log(state, step=f"{key}:sample_validation", ok=False, note="timeout after 1 h",
                    log_tail=(sdir / "run.log").read_text()[-3000:])
                raise SystemExit(f"sample validation timed out for {key}")
            if r.returncode != 0:
                log(state, step=f"{key}:sample_validation", ok=False, exit=r.returncode,
                    log_tail=(sdir / "run.log").read_text()[-3000:])
                raise SystemExit(f"sample validation failed for {key}; see {sdir / 'run.log'}")
            ours = json.load(open(sdir / "nbest_predictions_.json"))
            theirs = json.load(open(od / "nbest_predictions_.json"))
            ws = lambda t: " ".join(t.split())
            agree = sum(ws(ours[q][0]["text"]) == ws(theirs[q][0]["text"]) for q in ours)
            maxdp = max(abs(x["probability"] - y["probability"]) for q in ours for x, y in zip(ours[q], theirs[q]))
            log(state, step=f"{key}:sample_validation", ok=True, questions=len(ours), top_agree=agree, max_abs_dp=maxdp)
            (sdir / "sample_test.json").unlink(missing_ok=True)
        # 4. corrected full run + unchanged scorer
        if not done(state, f"{key}:corrected_full"):
            if time.time() > deadline:
                log(state, step=f"{key}:corrected_full", ok=False, note="budget exhausted before start")
                break
            fdir = state / f"corrected_{key}"
            fdir.mkdir(parents=True, exist_ok=True)
            flog = open(fdir / "run.log", "a")
            p = subprocess.Popen([sys.executable, str(HERE / "cuad_reference_full.py"), "--model", hub, "--out", str(fdir)],
                                 cwd=F, stdout=flog, stderr=subprocess.STDOUT)
            while p.poll() is None:
                if time.time() > deadline:
                    p.terminate()
                    p.wait(120)
                    log(state, step=f"{key}:corrected_full", ok=False, note="stopped at budget; resumable",
                        chunks_done=len(list(fdir.glob("chunk_*/nbest_predictions_.json"))))
                    return
                time.sleep(10)
            if p.returncode != 0:
                log(state, step=f"{key}:corrected_full", ok=False, exit=p.returncode,
                    log_tail=(fdir / "run.log").read_text()[-3000:])
                raise SystemExit(f"corrected run failed for {key}")
            res = score(fdir, key)
            log(state, step=f"{key}:corrected_full", ok=res["status"] in ("STEP_A_PASS", "STEP_A_FAIL"),
                label="CORRECTED_DIAGNOSTIC (not the pre-registered Step A)", status=res["status"],
                reproduced=res.get("reproduced"), published=res.get("published"))
            with open(fdir / "nbest_partial.jsonl", "rb") as src, gzip.open(fdir / "nbest_partial.jsonl.gz", "wb") as dst:
                shutil.copyfileobj(src, dst)
        shutil.rmtree(tmp / f"official_{key}", ignore_errors=True)
        (tmp / f"{key}.zip").unlink(missing_ok=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--state", default="/kaggle/working/diag_state")
    p.add_argument("--tmp", default="/tmp/diag")
    p.add_argument("--budget-hours", type=float, default=11.0)
    p.add_argument("--models", nargs="+", default=list(MODELS))
    main(p.parse_args())
