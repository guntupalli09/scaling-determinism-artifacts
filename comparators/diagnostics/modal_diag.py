"""
Runs the CUAD diagnostic job (cuad_diag_kaggle.py) on a Modal T4. It is the same job as diag_kaggle.ipynb and
colab_diag*.ipynb, for when the Kaggle and Colab free GPU allowances are exhausted. Diagnostic only, like the other
two.

What makes it the same experiment:
- **Code.** The same `git archive` of one commit (default 87bd32b4) as the Colab notebooks. Every file is checked
  against the commit's git blob hashes before the image is built.
- **Data, scorer and thresholds.** fetch_external.sh downloads the data and aborts on any sha256 mismatch. The
  scorer is the unchanged cuad_step_a.py + official evaluate.py; the thresholds are unchanged.
- **Library pins.** Same as Kaggle and Colab: transformers 4.57.6 and tokenizers 0.22.2. Torch is 2.11.0, the version
  Colab used.
- **Seed (optional).** An earlier session's diag_log.jsonl and finished chunks (a committed run record,
  sha256-checked) are copied into the state, so the run resumes exactly where that session stopped.

State lives in the Modal volume `triage-phase3-diag`, under `<tag>/diag_state`.

    modal run --detach comparators/diagnostics/modal_diag.py --models deberta-v2-xlarge \
        --tag deberta_resume_kaggle_v6 --seed runs/diagnostics/cuad/kaggle_v6_20261020T0109Z_deberta_partial
    modal volume get triage-phase3-diag <tag>/diag_state <local dir>
"""
import gzip
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

import modal

HERE = Path(__file__).resolve().parent
COMMIT = os.environ.get("DIAG_COMMIT", "87bd32b4")
PATHS = ["experiments/followup/comparators", "experiments/followup/runs/diagnostics/cuad/sample_seed20261018/titles.txt"]


def snapshot(commit):
    """git archive of the job's files at `commit`, extracted and checked against the commit's blob hashes."""
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=HERE, capture_output=True, text=True,
                          check=True).stdout.strip()
    full = subprocess.run(["git", "rev-parse", commit], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
    out = Path(tempfile.mkdtemp(prefix="diag_code_"))
    tar = subprocess.run(["git", "archive", full, *PATHS], cwd=root, capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(out)], input=tar, check=True)
    (out / "SOURCE_COMMIT").write_text(full + "\n")
    tree = subprocess.run(["git", "ls-tree", "-r", full, "--", *PATHS], cwd=root, capture_output=True, text=True,
                          check=True).stdout
    for line in tree.splitlines():
        sha, path = line.split()[2], line.split("\t", 1)[1]
        b = (out / path).read_bytes()
        assert hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest() == sha, f"file differs from {full}: {path}"
    return out, full


CODE_DIR, FULL_COMMIT = snapshot(COMMIT) if modal.is_local() else (None, None)

image = (modal.Image.debian_slim(python_version="3.12")
         .apt_install("curl", "unzip")
         .pip_install("torch==2.11.0", "transformers==4.57.6", "tokenizers==0.22.2", "sentencepiece", "protobuf",
                      "numpy", "pandas", "scikit-learn", "tqdm"))
if CODE_DIR:
    image = image.add_local_dir(str(CODE_DIR), "/code", copy=True)

vol = modal.Volume.from_name("triage-phase3-diag", create_if_missing=True)
app = modal.App("triage-phase3-diag", image=image)


@app.function(gpu="T4", volumes={"/vol": vol}, timeout=8 * 3600, cpu=2.0, memory=16384)
def run(models: list, tag: str, budget_hours: float, seed_log: bytes = b"", seed_chunks_gz: bytes = b""):
    import time
    state = Path(f"/vol/{tag}/diag_state")
    state.mkdir(parents=True, exist_ok=True)
    corr = state / f"corrected_{models[0]}"
    if seed_log and not (state / "diag_log.jsonl").exists():
        (state / "diag_log.jsonl").write_bytes(seed_log)
        chunks = {}
        for line in gzip.decompress(seed_chunks_gz).decode().splitlines():
            r = json.loads(line)
            chunks.setdefault(r["chunk"], {})[r["id"]] = r["nbest"]
        for c, preds in chunks.items():
            (corr / c).mkdir(parents=True, exist_ok=True)
            (corr / c / "nbest_predictions_.json").write_text(json.dumps(preds))
        vol.commit()
    done = sorted(d.name for d in corr.glob("chunk_*") if (d / "nbest_predictions_.json").exists()) if corr.exists() else []
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                         capture_output=True, text=True).stdout.strip()
    import torch
    import transformers
    env = {"provider": "modal", "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "gpu": gpu,
           "commit": Path("/code/SOURCE_COMMIT").read_text().strip(), "cuda": torch.cuda.is_available(),
           "torch": torch.__version__, "transformers": transformers.__version__, "finished_chunks_at_start": len(done)}
    with open(state.parent / "environment.jsonl", "a") as fh:
        fh.write(json.dumps(env) + "\n")
    vol.commit()
    print(env, flush=True)
    F = "/code/experiments/followup"
    subprocess.run(["bash", "comparators/gpu/fetch_external.sh"], cwd=F, check=True, stdout=subprocess.DEVNULL,
                   timeout=3600)
    p = subprocess.Popen(["python", "comparators/diagnostics/cuad_diag_kaggle.py", "--state", str(state), "--tmp",
                          "/tmp/diag", "--budget-hours", str(budget_hours), "--models", *models], cwd=F)
    while p.poll() is None:          # commit the volume every few minutes so finished chunks survive any stop
        time.sleep(300)
        vol.commit()
    vol.commit()
    log = (state / "diag_log.jsonl").read_text() if (state / "diag_log.jsonl").exists() else ""
    print("exit", p.returncode, "\n" + log, flush=True)
    return log


@app.local_entrypoint()
def main(models: str = "deberta-v2-xlarge", tag: str = "", seed: str = "", budget_hours: float = 5.0):
    models = models.split(",")
    tag = tag or "_".join(models)
    seed_log = seed_gz = b""
    if seed:
        sd = Path(seed)
        seed_log = (sd / "diag_state/diag_log.jsonl").read_bytes()
        seed_gz = next(sd.glob("chunks_*_nbest.jsonl.gz")).read_bytes()
        print("seed:", sd.name, hashlib.sha256(seed_log).hexdigest()[:12], hashlib.sha256(seed_gz).hexdigest()[:12])
    print("code:", FULL_COMMIT, "| models:", models, "| tag:", tag)
    print(run.remote(models, tag, budget_hours, seed_log, seed_gz))
