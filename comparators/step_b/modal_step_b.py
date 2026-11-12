"""
Runs CUAD Step B workers (worker.py) on a Modal T4, with state in the Modal volume `triage-step-b` under
step_b_state/<model>. Used only within Modal's free monthly credit (RoBERTa-base, about 13 GPU-hours).

Code: `git archive` of one pushed commit, every file checked against the commit's git blob hashes. Corpus texts:
copied from corpus/texts (not in git); the harness checks each against the frozen manifest's SHA-256 before use.

    modal deploy comparators/step_b/modal_step_b.py        # STEPB_COMMIT=<commit> in the environment
    python -c "import modal; modal.Function.from_name('triage-step-b', 'run').spawn(['roberta-base'], 1, [0], 7.5)"
    modal volume get triage-step-b step_b_state/roberta-base <local dir>
"""
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

import modal

HERE = Path(__file__).resolve().parent
F = HERE.parents[1] if modal.is_local() else None   # the container only has /root/<this file>
COMMIT = os.environ.get("STEPB_COMMIT", "HEAD")
PATHS = ["experiments/followup/comparators", "experiments/followup/corpus/manifest.csv",
         "experiments/followup/runs/diagnostics/cuad/kaggle_v5_20261019T1954Z_roberta-large/diag_state/"
         "corrected_roberta-large/nbest_partial.jsonl.gz",
         "experiments/followup/runs/diagnostics/cuad/modal_20261020T2240Z_deberta_resume/nbest_partial.jsonl.gz"]
CUAD_UTILS = ("https://raw.githubusercontent.com/TheAtticusProject/cuad/67faa0e6023b04fcaae6cc09497ab00e5d63a2a2/"
              "utils.py")


def snapshot(commit):
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=HERE, capture_output=True, text=True,
                          check=True).stdout.strip()
    full = subprocess.run(["git", "rev-parse", commit], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
    out = Path(tempfile.mkdtemp(prefix="stepb_code_"))
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
         .pip_install("torch==2.11.0", "transformers==4.57.6", "tokenizers==0.22.2", "sentencepiece", "protobuf",
                      "numpy", "tqdm"))
if CODE_DIR:
    image = (image.add_local_dir(str(CODE_DIR), "/code", copy=True)
             .add_local_dir(str(F / "corpus/texts"), "/code/experiments/followup/corpus/texts", copy=True))

vol = modal.Volume.from_name("triage-step-b", create_if_missing=True)
app = modal.App("triage-step-b", image=image)


@app.function(gpu="T4", volumes={"/vol": vol}, timeout=8 * 3600, cpu=2.0, memory=16384)
def run(queue: list, shard_of: int, shards: list, budget_hours: float):
    import json
    import time
    import urllib.request
    fdir = "/code/experiments/followup"
    data = urllib.request.urlopen(CUAD_UTILS, timeout=300).read()
    want = next(l.split()[0] for l in open(f"{fdir}/comparators/gpu/EXTERNAL.sha256") if l.strip().endswith("cuad_utils.py"))
    assert hashlib.sha256(data).hexdigest() == want, "cuad_utils.py hash mismatch"
    Path(f"{fdir}/external").mkdir(exist_ok=True)
    Path(f"{fdir}/external/cuad_utils.py").write_bytes(data)
    root = Path("/vol/step_b_state")
    root.mkdir(parents=True, exist_ok=True)
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True,
                         text=True).stdout.strip()
    with open(root / "environment_modal.jsonl", "a") as fh:
        fh.write(json.dumps({"provider": "modal", "gpu": gpu, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                             "commit": Path("/code/SOURCE_COMMIT").read_text().strip(), "queue": queue,
                             "shard_of": shard_of, "shards": shards}) + "\n")
    vol.commit()
    deadline = time.time() + budget_hours * 3600
    p = subprocess.Popen(["python", "comparators/step_b/worker.py", "--state-root", str(root), "--queue", *queue,
                          "--shard-of", str(shard_of), "--shards", *map(str, shards), "--deadline-epoch", str(deadline),
                          "--threads", "2"], cwd=fdir)
    while p.poll() is None:            # commit every few minutes so finished chunks survive any stop
        time.sleep(300)
        vol.commit()
    vol.commit()
    return p.returncode
