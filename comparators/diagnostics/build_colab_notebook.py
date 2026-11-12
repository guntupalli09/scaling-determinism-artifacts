"""
Writes colab_diag.ipynb: the same CUAD diagnostic job as diag_kaggle.ipynb (cuad_diag_kaggle.py), for a free
Google Colab GPU. It runs on whichever provider starts first. It is diagnostic only, like the Kaggle notebook.

What makes it the same experiment:
- **Code.** Only the files the job needs are taken from one commit (default 87bd32b4) with `git archive` and embedded
  in the notebook. Before anything runs, the notebook checks every file against that commit's git blob hashes.
- **Data, scorer and thresholds.** fetch_external.sh downloads the data and aborts on any sha256 mismatch. The scorer
  (cuad_step_a.py + the official evaluate.py) and its thresholds are inside the same snapshot.
- **Models.** The same Hugging Face checkpoints and the same Zenodo reference release.
- **Library pins.** Same as Kaggle: transformers 4.57.6, tokenizers 0.22.2.

State and outputs go to Google Drive (MyDrive/triage_phase3_diag/colab_<models>/). A disconnected session can be
resumed by running the notebook again, and the results can be read back from Drive.

    python experiments/followup/comparators/diagnostics/build_colab_notebook.py [--commit 87bd32b4] [--models roberta-base]
"""
import argparse
import base64
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PATHS = ["experiments/followup/comparators", "experiments/followup/runs/diagnostics/cuad/sample_seed20261018/titles.txt"]


def md(t):
    return {"cell_type": "markdown", "metadata": {}, "source": t.strip("\n").splitlines(keepends=True)}


def code(t):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": t.strip("\n").splitlines(keepends=True)}


def snapshot(commit):
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=HERE, capture_output=True, text=True,
                          check=True).stdout.strip()
    full = subprocess.run(["git", "rev-parse", commit], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
    tar = subprocess.run(["git", "archive", "--format=tar.gz", f"--add-virtual-file=SOURCE_COMMIT:{full}\n", full,
                          *PATHS], cwd=root, capture_output=True, check=True).stdout
    tree = subprocess.run(["git", "ls-tree", "-r", full, "--", *PATHS], cwd=root, capture_output=True, text=True,
                          check=True).stdout
    blobs = {line.split("\t", 1)[1]: line.split()[2] for line in tree.splitlines()}
    return full, tar, blobs


def seed_cell(seed_dir, models):
    """Seeds the Drive state with an earlier session's step log and finished chunks, so the run resumes exactly
    where that session stopped. Each chunk keeps only text and probability, the two fields the merge step reads."""
    seed_dir = Path(seed_dir)
    log = (seed_dir / "diag_state/diag_log.jsonl").read_bytes()
    gz = next(seed_dir.glob("chunks_*_nbest.jsonl.gz")).read_bytes()
    corr = f"corrected_{models[0]}"
    return code(f"""
# seed: diag_log + finished chunks from {seed_dir.name} (sha256-checked against the committed files)
import gzip
SEED_LOG = base64.b64decode("{base64.b64encode(log).decode()}")
SEED_GZ = base64.b64decode("{base64.b64encode(gz).decode()}")
assert hashlib.sha256(SEED_LOG).hexdigest() == "{hashlib.sha256(log).hexdigest()}", "seed log corrupted"
assert hashlib.sha256(SEED_GZ).hexdigest() == "{hashlib.sha256(gz).hexdigest()}", "seed chunks corrupted"
if not os.path.exists(os.path.join(STATE, "diag_log.jsonl")):
    open(os.path.join(STATE, "diag_log.jsonl"), "wb").write(SEED_LOG)
    chunks = {{}}
    for line in gzip.decompress(SEED_GZ).decode().splitlines():
        r = json.loads(line)
        chunks.setdefault(r["chunk"], {{}})[r["id"]] = r["nbest"]
    for c, preds in chunks.items():
        os.makedirs(os.path.join(STATE, "{corr}", c), exist_ok=True)
        json.dump(preds, open(os.path.join(STATE, "{corr}", c, "nbest_predictions_.json"), "w"))
    json.dump({{"seeded_from": "{seed_dir.name}", "chunks": sorted(chunks)}}, open(os.path.join(STATE, "..", "SEEDED_FROM.json"), "w"))
done = sorted(d for d in os.listdir(os.path.join(STATE, "{corr}")) if os.path.exists(os.path.join(STATE, "{corr}", d, "nbest_predictions_.json")))
print("finished chunks in state:", len(done), done[:1], "...", done[-1:])
""")


def cells(full, tar, blobs, models, budget, tag=None, seed=None):
    tag = tag or "_".join(models)
    return [
        md(f"""
# Phase 3 CUAD diagnostic on Google Colab (same job as the Kaggle notebook)

**Diagnostic only.** The pre-registered Step A results (all STEP_A_FAIL) are final and untouched. Every output is labelled
CORRECTED_DIAGNOSTIC.

- **Code:** commit `{full}`, verified file by file against its git blob hashes.
- **Models:** {", ".join(models)}.
- **Before you start:** Runtime → Change runtime type → **T4 GPU**. Then Runtime → **Run all**, and allow Google Drive
  access when asked.
- **Outputs:** saved to `MyDrive/triage_phase3_diag/colab_{tag}/`.
- **If the session disconnects,** run all again: finished steps and chunks are skipped.
"""),
        code(f"""
import base64, hashlib, io, json, os, subprocess, sys, tarfile, time
out = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], capture_output=True, text=True)
assert out.returncode == 0 and out.stdout.strip(), "No GPU: Runtime -> Change runtime type -> T4 GPU, then Run all"
GPU = out.stdout.strip(); print("GPU:", GPU)
from google.colab import drive
drive.mount("/content/drive")
STATE = "/content/drive/MyDrive/triage_phase3_diag/colab_{tag}/diag_state"
os.makedirs(STATE, exist_ok=True)
"""),
        code(f"""
# embedded code snapshot of commit {full[:10]}, checked against the commit's git blob hashes
TAR_SHA256 = "{hashlib.sha256(tar).hexdigest()}"
BLOBS = {json.dumps(blobs)}
data = base64.b64decode("{base64.b64encode(tar).decode()}")
assert hashlib.sha256(data).hexdigest() == TAR_SHA256, "snapshot corrupted"
REPO = "/content/Triage"
if os.path.exists(REPO):
    subprocess.run(["rm", "-rf", REPO], check=True)
with tarfile.open(fileobj=io.BytesIO(data)) as t:
    t.extractall(REPO)
for path, sha in BLOBS.items():
    b = open(os.path.join(REPO, path), "rb").read()
    assert hashlib.sha1(b"blob %d\\0" % len(b) + b).hexdigest() == sha, "file differs from the commit: " + path
COMMIT = open(os.path.join(REPO, "SOURCE_COMMIT")).read().strip()
print("code commit:", COMMIT, "| files verified:", len(BLOBS))
"""),
    ] + ([seed_cell(seed, models)] if seed else []) + [
        code("""
F = os.path.join(REPO, "experiments/followup")
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "transformers==4.57.6", "tokenizers==0.22.2"], check=True, timeout=1800)
subprocess.run(["bash", "comparators/gpu/fetch_external.sh"], cwd=F, check=True, stdout=subprocess.DEVNULL, timeout=3600)
import torch, transformers
env = {"provider": "colab", "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "gpu": GPU, "commit": COMMIT,
       "cuda": torch.cuda.is_available(), "torch": torch.__version__, "transformers": transformers.__version__,
       "python": sys.version.split()[0]}
with open(os.path.join(STATE, "..", "environment.jsonl"), "a") as fh:
    fh.write(json.dumps(env) + "\\n")
print(env)
assert env["cuda"], "CUDA not available"
"""),
        code(f"""
MODELS, BUDGET = {models!r}, {budget}
log_path = os.path.join(STATE, "..", "notebook_run.log")
import threading
with open(log_path, "a") as fh:
    p = subprocess.Popen([sys.executable, "comparators/diagnostics/cuad_diag_kaggle.py", "--state", STATE,
                          "--tmp", "/content/diag_tmp", "--budget-hours", str(BUDGET), "--models", *MODELS],
                         cwd=F, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    watchdog = threading.Timer((BUDGET + 0.5) * 3600, p.kill)   # hard stop 30 min after the job's own budget
    watchdog.start()
    for line in p.stdout:
        print(line, end=""); fh.write(line); fh.flush()
    p.wait(); watchdog.cancel()
print("exit", p.returncode, "(killed by watchdog; state so far is kept on Drive)" if p.returncode == -9 else "")
lp = os.path.join(STATE, "diag_log.jsonl")
for l in open(lp) if os.path.exists(lp) else []:
    print(l.strip())
"""),
    ]


def main(a):
    full, tar, blobs = snapshot(a.commit)
    nb = {"cells": cells(full, tar, blobs, a.models, a.budget_hours, a.tag, a.seed),
          "metadata": {"accelerator": "GPU", "colab": {"provenance": [], "gpuType": "T4"},
                       "kernelspec": {"display_name": "Python 3", "name": "python3"}, "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 5}
    out = HERE / a.out
    out.write_text(json.dumps(nb, indent=1) + "\n")
    print(out, full, len(blobs), "files")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--commit", default="87bd32b4")
    p.add_argument("--models", nargs="+", default=["roberta-base"])
    p.add_argument("--budget-hours", type=float, default=9.0)
    p.add_argument("--out", default="colab_diag.ipynb")
    p.add_argument("--tag", help="Drive folder name (default: model names)")
    p.add_argument("--seed", help="run dir whose diag_log.jsonl and chunks_*_nbest.jsonl.gz seed the state")
    main(p.parse_args())
