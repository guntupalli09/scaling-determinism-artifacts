"""
Writes diag_kaggle.ipynb: the Kaggle notebook for the Phase 3 CUAD diagnostic job (cuad_diag_kaggle.py).
A separate notebook from the pre-registered phase3_kaggle.ipynb, so the two kinds of run cannot be confused.

    python experiments/followup/comparators/diagnostics/build_diag_notebook.py [--models roberta-base] [--budget-hours 9]

One model per Kaggle run keeps each session well inside Kaggle's 12 h limit, so its output is always saved.
Every step has a hard timeout (v3 hung for 18 h past the limit and saved nothing).
"""
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def md(t):
    return {"cell_type": "markdown", "metadata": {}, "source": t.strip("\n").splitlines(keepends=True)}


def code(t):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": t.strip("\n").splitlines(keepends=True)}


CELLS = [
    md("""
# Phase 3 CUAD diagnostic: reference pipeline and corrected runs

**Diagnostic only.** The pre-registered Step A results (all STEP_A_FAIL) are final and untouched.
This notebook runs `comparators/diagnostics/cuad_diag_kaggle.py` for one model per run; every output is labelled
CORRECTED_DIAGNOSTIC.
GPU T4 x2, Internet on. Output: `/kaggle/working/diag_state/` (`diag_log.jsonl` holds every step).
"""),
    code("""
import glob, json, os, shutil, subprocess, sys, tarfile
STATE, WORK = "/kaggle/working/diag_state", "/tmp/diag_work"
os.makedirs(WORK, exist_ok=True)
# resume: an attached earlier diag_state (any folder with diag_log.jsonl, never inside the code snapshot)
prev = [os.path.dirname(p) for p in glob.glob("/kaggle/input/**/diag_log.jsonl", recursive=True) if "/experiments/" not in p]
if prev and not os.path.exists(os.path.join(STATE, "diag_log.jsonl")):
    shutil.copytree(prev[0], STATE, dirs_exist_ok=True); print("resuming from", prev[0])
os.makedirs(STATE, exist_ok=True)
repo = os.path.join(WORK, "Triage")
if not os.path.exists(repo):
    arch = glob.glob("/kaggle/input/**/triage_code.tar.gz", recursive=True)
    ext = [os.path.dirname(p) for p in glob.glob("/kaggle/input/**/SOURCE_COMMIT", recursive=True)]
    if arch:
        os.makedirs(repo)
        with tarfile.open(arch[0]) as t:
            t.extractall(repo)
    else:
        shutil.copytree(ext[0], repo)
print("code commit:", open(os.path.join(repo, "SOURCE_COMMIT")).read().strip())
!nvidia-smi --query-gpu=name,memory.total --format=csv
"""),
    code("""
F = os.path.join(repo, "experiments/followup")
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "transformers==4.57.6", "tokenizers==0.22.2"], check=True, timeout=1800)
subprocess.run(["bash", "comparators/gpu/fetch_external.sh"], cwd=F, check=True, stdout=subprocess.DEVNULL, timeout=3600)
import torch; print("CUDA available:", torch.cuda.is_available())
"""),
    code("""
MODELS, BUDGET = __MODELS__, __BUDGET__
try:   # hard stop 30 min after the job's own budget, so the session always ends and saves its output
    r = subprocess.run([sys.executable, "comparators/diagnostics/cuad_diag_kaggle.py", "--state", STATE,
                        "--budget-hours", str(BUDGET), "--models", *MODELS], cwd=F, timeout=(BUDGET + 0.5) * 3600)
    print("exit", r.returncode)
except subprocess.TimeoutExpired:
    print("HARD TIMEOUT: job killed; state so far is kept")
lp = os.path.join(STATE, "diag_log.jsonl")
for l in open(lp) if os.path.exists(lp) else []:
    print(l.strip())
"""),
]


def main(a):
    cells = json.loads(json.dumps(CELLS).replace("__MODELS__", repr(a.models).replace('"', "'"))
                       .replace("__BUDGET__", str(a.budget_hours)))
    nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                        "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
    (HERE / "diag_kaggle.ipynb").write_text(json.dumps(nb, indent=1) + "\n")
    print(HERE / "diag_kaggle.ipynb")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--models", nargs="+", default=["roberta-base"])
    p.add_argument("--budget-hours", type=float, default=9.0)
    main(p.parse_args())
