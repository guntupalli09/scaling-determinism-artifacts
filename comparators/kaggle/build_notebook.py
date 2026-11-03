"""
Writes phase3_kaggle.ipynb (the notebook is generated so that its cells stay reviewable here).

    python experiments/followup/comparators/kaggle/build_notebook.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(keepends=True)}


def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": text.strip("\n").splitlines(keepends=True)}


CELLS = [
    md("""
# Phase 3 comparators — free Kaggle GPU

Runs the Phase 3 protocol of *Bounding the Cost of Determinism* on Kaggle's free **GPU T4 x2**:

1. **CUAD RoBERTa-base** Step A (reproduce Hendrycks et al. 2021, Table 2), then — only if the pre-registered
   check passes — Step B (frozen corpus) and Step C (paired comparison with the v7.2.0 engine);
   then RoBERTa-large and DeBERTa-v2-xlarge the same way.
2. **ContractNLI Span NLI BERT-base**: train the published `conf_base.yml` (seed 42) on one GPU, `test.py`,
   pre-registered Step A, pairing only after a PASS. Runs on the second T4 in parallel.

**Settings this notebook needs (right-hand panel → Session options):** Accelerator **GPU T4 x2**, Internet **On**
(Internet requires a phone-verified Kaggle account). Run it with **Save Version → Save & Run All (Commit)** so
it runs unattended and `/kaggle/working/phase3_state` is saved as the version's output.

Nothing here tunes models or thresholds. Each session stops itself after `BUDGET_HOURS` (below Kaggle's 12 h
limit); unfinished work is reported as INCOMPLETE and resumes in the next version (see the last cell).
"""),
    code("""
REPO_URL = "https://github.com/guntupalli09/Triage.git"
BRANCH = "claude/adoring-heisenberg-gd2tv1"
COMMIT = ""            # optional: pin an exact commit of the research branch
MODELS = ["roberta-base", "roberta-large", "deberta-v2-xlarge"]   # processed in this order
BUDGET_HOURS = 11.0    # self-imposed stop, below Kaggle's 12 h session limit
STATE = "/kaggle/working/phase3_state"   # saved as notebook output -> persistent
WORK = "/tmp/phase3"                      # clones and environments; not saved
"""),
    md("Resume: if a previous version's output (or a dataset holding a `phase3_state/` folder) is attached as input, continue from the most advanced copy."),
    code("""
import glob, json, os, shutil

def progress(d):
    try:
        st = json.load(open(os.path.join(d, "stages.json")))
        return max(v.get("at", "") for v in st.values()), len(st)
    except Exception:
        return ("", 0)

# A state folder is any attached directory holding stages.json + environment.json (Kaggle may unpack an
# uploaded phase3_state.zip flat at the dataset root, without the phase3_state/ folder).
# The code snapshot also contains committed past runs (experiments/followup/runs/...): never resume from those.
candidates = [os.path.dirname(p) for p in glob.glob("/kaggle/input/**/stages.json", recursive=True)
              if os.path.exists(os.path.join(os.path.dirname(p), "environment.json"))
              and "/experiments/" not in p]
if candidates and not os.path.exists(os.path.join(STATE, "stages.json")):
    src = max(candidates, key=progress)
    print("resuming from", src, progress(src))
    shutil.copytree(src, STATE, dirs_exist_ok=True)
else:
    print("fresh state" if not candidates else "working state already present")
os.makedirs(STATE, exist_ok=True)
"""),
    md("Code: the repository is private, so the exact research-branch snapshot is attached as a private dataset "
       "(`triage_code.tar.gz`, built with `git archive`, commit recorded in `SOURCE_COMMIT`). Without it the notebook "
       "falls back to `git clone`, which needs the repository to be reachable."),
    code("""
import subprocess, tarfile
os.makedirs(WORK, exist_ok=True)
repo = os.path.join(WORK, "Triage")
if not os.path.exists(repo):
    archives = glob.glob("/kaggle/input/**/triage_code.tar.gz", recursive=True)
    extracted = [os.path.dirname(p) for p in glob.glob("/kaggle/input/**/SOURCE_COMMIT", recursive=True)]
    if archives:
        os.makedirs(repo)
        with tarfile.open(archives[0]) as t:
            t.extractall(repo)
    elif extracted:                      # Kaggle may have unpacked the archive already
        shutil.copytree(extracted[0], repo)
    elif COMMIT:
        subprocess.run(["git", "clone", "-q", "--branch", BRANCH, REPO_URL, repo], check=True)
        subprocess.run(["git", "checkout", "-q", COMMIT], cwd=repo, check=True)
    else:
        subprocess.run(["git", "clone", "-q", "--depth", "1", "--branch", BRANCH, REPO_URL, repo], check=True)
src = os.path.join(repo, "SOURCE_COMMIT")
print("code commit:", open(src).read().strip() if os.path.exists(src) else
      subprocess.run(["git", "log", "-1", "--format=%H %cd %s"], cwd=repo, capture_output=True, text=True).stdout)
!nvidia-smi --query-gpu=name,memory.total --format=csv
import torch; print("CUDA available:", torch.cuda.is_available(), "| devices:", torch.cuda.device_count())
"""),
    md("Run the driver. Progress lines are printed here; full logs go to `phase3_state/logs/`."),
    code("""
import sys
cmd = [sys.executable, "experiments/followup/comparators/kaggle/phase3_driver.py", "--state", STATE,
       "--tmp", WORK, "--budget-hours", str(BUDGET_HOURS), "--models", *MODELS]
proc = subprocess.run(cmd, cwd=repo)
print("driver exit code:", proc.returncode)
"""),
    code("""
from IPython.display import Markdown, display
report = os.path.join(STATE, "PHASE3_VALIDATION_REPORT.md")
if not os.path.exists(report):
    subprocess.run([sys.executable, "experiments/followup/comparators/kaggle/phase3_report.py", "--state", STATE], cwd=repo)
display(Markdown(open(report).read()))
"""),
    md("""
### Next session
If the report says **INCOMPLETE** with `INCOMPLETE_BUDGET` / `DEFERRED_INSUFFICIENT_BUDGET`:
*Add Input → Your Work → Notebooks → this notebook* (its latest version's output), then **Save & Run All** again.
The resume cell picks up `phase3_state/` and every stage continues from its checkpoint.
"""),
]


def main():
    nb = {"cells": CELLS, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                        "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 5}
    (HERE / "phase3_kaggle.ipynb").write_text(json.dumps(nb, indent=1) + "\n")
    print(HERE / "phase3_kaggle.ipynb")


if __name__ == "__main__":
    main()
