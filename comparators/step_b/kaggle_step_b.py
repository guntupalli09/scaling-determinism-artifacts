"""
Run CUAD Step B on Kaggle's free GPU (T4 x2) through the Kaggle API: one worker per GPU, each on its own shard
of the chunk plan, so both GPUs work on the same model. Everything is private; only the free accelerator is used.

    python kaggle_step_b.py push  --code-ref <pushed commit> [--state DIR] [--queue ...] [--budget-hours 11]
    python kaggle_step_b.py status
    python kaggle_step_b.py fetch --out DIR     # the session's /kaggle/working/step_b_state

Private datasets: <user>/triage-step-b-code (git archive of the commit), <user>/triage-step-b-corpus (the frozen
corpus texts, verified against the manifest hashes on use), <user>/triage-step-b-state (the state carried between
sessions; --state uploads it). Credentials: ~/.kaggle (never printed).
"""
import argparse
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
F = HERE.parents[1]
KERNEL, CODE, CORPUS, STATE = "triage-step-b", "triage-step-b-code", "triage-step-b-corpus", "triage-step-b-state"
ACCEL = "NvidiaTeslaT4"
# What the notebook needs (the same list modal_step_b.py ships): not the committed run outputs, which grow the archive
CODE_PATHS = ["experiments/followup/comparators", "experiments/followup/corpus/manifest.csv",
              "experiments/followup/runs/diagnostics/cuad/kaggle_v5_20261019T1954Z_roberta-large/diag_state/"
              "corrected_roberta-large/nbest_partial.jsonl.gz",
              "experiments/followup/runs/diagnostics/cuad/modal_20261020T2240Z_deberta_resume/nbest_partial.jsonl.gz"]
QUEUE = ["roberta-base", "roberta-large", "deberta-v2-xlarge"]
CUAD_UTILS = ("https://raw.githubusercontent.com/TheAtticusProject/cuad/67faa0e6023b04fcaae6cc09497ab00e5d63a2a2/"
              "utils.py")


def api():
    from kaggle.api.kaggle_api_extended import KaggleApi
    k = KaggleApi()
    k.authenticate()
    return k


def user(k):
    return k.get_config_value("username") or "santhoshguntupalli"


def dataset(k, slug, folder, msg, marker):
    meta = {"title": slug.replace("-", " "), "id": f"{user(k)}/{slug}", "licenses": [{"name": "other"}]}
    (Path(folder) / "dataset-metadata.json").write_text(json.dumps(meta))
    try:
        k.dataset_status(f"{user(k)}/{slug}")
        exists = True
    except Exception:
        exists = False
    if exists:
        r = k.dataset_create_version(folder, msg, dir_mode="zip", quiet=True)
    else:
        r = k.dataset_create_new(folder, public=False, dir_mode="zip", quiet=True)
    err = getattr(r, "error", None)
    print(f"dataset {slug}: upload status {getattr(r, 'status', r)!r}{' error ' + repr(err) if err else ''}", flush=True)
    if err:
        sys.exit(f"dataset {slug}: upload failed")
    # A kernel started before the new version is processed mounts the previous one, and dataset_status can report the
    # previous version as ready: wait until this push's marker file can be downloaded from it.
    import time
    for _ in range(120):
        time.sleep(15)
        with tempfile.TemporaryDirectory() as t:
            try:
                k.dataset_download_file(f"{user(k)}/{slug}", marker, path=t, quiet=True)
                break                                   # the marker exists only in this push's version
            except Exception:
                continue
    else:
        sys.exit(f"dataset {slug}: new version not visible after 30 min")
    time.sleep(60)
    return f"{user(k)}/{slug}"


def cuad_utils_sha():
    for line in open(F / "comparators/gpu/EXTERNAL.sha256"):
        if line.strip().endswith("external/cuad_utils.py"):
            return line.split()[0]
    sys.exit("cuad_utils.py hash not found in EXTERNAL.sha256")


def notebook(queue, budget, commit, marker, with_state):
    def code(src):
        return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
                "source": src.strip("\n").splitlines(keepends=True)}
    setup = f'''
import glob, hashlib, json, os, shutil, subprocess, sys, tarfile, time, urllib.request
START = time.time(); DEADLINE = START + {budget} * 3600
REPO, OUT = "/tmp/Triage", "/kaggle/working/step_b_state"
os.makedirs(REPO, exist_ok=True)
# Kaggle unpacks archives on upload: accept the archive or its extracted tree
arch = glob.glob("/kaggle/input/**/triage_code.tar.gz", recursive=True)
if arch:
    with tarfile.open(arch[0]) as t:
        t.extractall(REPO)
else:
    shutil.copytree(os.path.dirname(glob.glob("/kaggle/input/**/SOURCE_COMMIT", recursive=True)[0]), REPO, dirs_exist_ok=True)
commit = open(f"{{REPO}}/SOURCE_COMMIT").read().strip(); assert commit == "{commit}", commit
# this push's marker must be in the code (and state) uploads mounted here, or a stale version was attached
for slug in ["{CODE}"] + (["{STATE}"] if {with_state!r} else []):
    assert glob.glob(f"/kaggle/input/**/{{slug}}/**/{marker}", recursive=True), f"stale dataset version: {{slug}}"
F = f"{{REPO}}/experiments/followup"
os.makedirs(f"{{F}}/corpus/texts", exist_ok=True)
ct = glob.glob("/kaggle/input/**/corpus_texts.tar", recursive=True)
if ct:
    with tarfile.open(ct[0]) as t:
        t.extractall(f"{{F}}/corpus")
else:
    src = [d for d in glob.glob("/kaggle/input/**/texts", recursive=True) if "/experiments/" not in d][0]
    shutil.copytree(src, f"{{F}}/corpus/texts", dirs_exist_ok=True)
assert len(os.listdir(f"{{F}}/corpus/texts")) == 618, "corpus texts incomplete"
prev = sorted(glob.glob("/kaggle/input/**/{STATE}/**/step_b_state/*/plan.json", recursive=True))  # the --state upload only
assert len({{os.path.dirname(os.path.dirname(p)) for p in prev}}) <= 1, prev
if prev and not os.path.exists(OUT):
    shutil.copytree(os.path.dirname(os.path.dirname(prev[0])), OUT); print("resuming from", os.path.dirname(os.path.dirname(prev[0])))
    import gzip  # Kaggle unpacks .gz files in uploaded datasets: restore the chunk outputs the workers look for
    # (seen: chunk_N/nbest.json/ as a directory holding the one uncompressed file; also handle a plain nbest.json)
    for p in glob.glob(f"{{OUT}}/*/chunk_*/nbest.json"):
        inner = [os.path.join(p, f) for f in os.listdir(p)] if os.path.isdir(p) else [p]
        assert len(inner) == 1 and os.path.isfile(inner[0]), (p, inner)
        json.load(open(inner[0]))                    # must be the complete JSON, or the session stops here
        with open(inner[0], "rb") as s, gzip.open(p + ".gz.tmp", "wb") as d:
            shutil.copyfileobj(s, d)
        shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
        os.replace(p + ".gz.tmp", p + ".gz")
    print("resumed chunks", {{m: len(glob.glob(f"{{OUT}}/{{m}}/chunk_*/nbest.json.gz")) for m in os.listdir(OUT)
                              if os.path.isdir(f"{{OUT}}/{{m}}")}})
os.makedirs(OUT, exist_ok=True)
data = urllib.request.urlopen("{CUAD_UTILS}", timeout=300).read()
assert hashlib.sha256(data).hexdigest() == "{cuad_utils_sha()}", "cuad_utils.py hash mismatch"
os.makedirs(f"{{F}}/external", exist_ok=True)
open(f"{{F}}/external/cuad_utils.py", "wb").write(data)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "transformers==4.57.6", "tokenizers==0.22.2",
                "sentencepiece", "protobuf"], check=True, timeout=1800)
print("commit", commit, "| texts", len(os.listdir(f"{{F}}/corpus/texts")))
!nvidia-smi --query-gpu=name,memory.total --format=csv
'''
    run = f'''
import torch
n = torch.cuda.device_count(); print("GPUs:", n)
procs = []
for g in range(max(n, 1)):
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(g), TOKENIZERS_PARALLELISM="false")
    shards = [str(g)] if n > 1 else ["0"]
    log = open(f"{{OUT}}/worker_gpu{{g}}_{{int(START)}}.log", "w")
    procs.append(subprocess.Popen([sys.executable, f"{{F}}/comparators/step_b/worker.py", "--state-root", OUT,
        "--queue", *{queue!r}, "--shard-of", str(max(n, 1)), "--shards", *shards,
        "--deadline-epoch", str(DEADLINE), "--threads", "2"], cwd=F, env=env, stdout=log, stderr=subprocess.STDOUT))
while any(p.poll() is None for p in procs):
    time.sleep(300)
    done = {{m: len(glob.glob(f"{{OUT}}/{{m}}/chunk_*/nbest.json.gz")) for m in {queue!r}}}
    print(time.strftime("%H:%M"), done, flush=True)
    if time.time() > DEADLINE + 1800:
        for p in procs: p.kill()
print("exit codes", [p.returncode for p in procs])
'''
    return {"cells": [code(setup), code(run)], "metadata": {"kernelspec": {"display_name": "Python 3",
            "language": "python", "name": "python3"}}, "nbformat": 4, "nbformat_minor": 4}


def push(a):
    k = api()
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=HERE, capture_output=True, text=True,
                          check=True).stdout.strip()
    commit = subprocess.run(["git", "rev-parse", a.code_ref], cwd=root, capture_output=True, text=True,
                            check=True).stdout.strip()
    pushed = subprocess.run(["git", "branch", "-r", "--contains", commit], cwd=root, capture_output=True, text=True).stdout
    if not pushed.strip():
        sys.exit("commit is not on the remote: push it first")
    sources = []
    import time
    marker = f"PUSH_{commit[:12]}_{int(time.time())}"   # unique per push: proves the mounted versions are this push's
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["git", "archive", "--format=tar.gz", f"--add-virtual-file=SOURCE_COMMIT:{commit}\n",
                        f"--add-virtual-file={marker}:{marker}\n", "-o", f"{d}/triage_code.tar.gz", commit,
                        *CODE_PATHS], cwd=root, check=True)
        sources.append(dataset(k, CODE, d, f"code {commit[:10]}", marker))
    if a.upload_corpus:
        with tempfile.TemporaryDirectory() as d:
            with tarfile.open(f"{d}/corpus_texts.tar", "w") as t:
                t.add(F / "corpus/texts", arcname="texts")
            (Path(d) / marker).write_text(marker + "\n")
            sources.append(dataset(k, CORPUS, d, "frozen corpus texts", marker))
    else:
        sources.append(f"{user(k)}/{CORPUS}")
    if a.state:
        with tempfile.TemporaryDirectory() as d:
            shutil.copytree(a.state, f"{d}/step_b_state", ignore=shutil.ignore_patterns("preflight_*", "*.log"))
            (Path(d) / marker).write_text(marker + "\n")
            sources.append(dataset(k, STATE, d, "step b state", marker))
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "step_b.ipynb").write_text(json.dumps(notebook(a.queue, a.budget_hours, commit, marker, bool(a.state)), indent=1))
        (Path(d) / "kernel-metadata.json").write_text(json.dumps({
            "id": f"{user(k)}/{KERNEL}", "title": KERNEL, "code_file": "step_b.ipynb", "language": "python",
            "kernel_type": "notebook", "is_private": "true", "enable_gpu": "true", "enable_internet": "true",
            "machine_shape": ACCEL, "dataset_sources": sources, "competition_sources": [], "kernel_sources": [],
            "model_sources": []}, indent=1))
        r = k.kernels_push(d, acc=ACCEL) if "acc" in k.kernels_push.__code__.co_varnames else k.kernels_push(d)
        print(getattr(r, "url", r), getattr(r, "error", ""))


def status(a):
    k = api()
    print(k.kernels_status(f"{user(k)}/{KERNEL}"))


def fetch(a):
    k = api()
    Path(a.out).mkdir(parents=True, exist_ok=True)
    k.kernels_output(f"{user(k)}/{KERNEL}", a.out, force=True, quiet=True)
    print("fetched to", a.out)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("push")
    s.add_argument("--code-ref", required=True)
    s.add_argument("--queue", nargs="+", default=QUEUE)
    s.add_argument("--budget-hours", type=float, default=11.0)
    s.add_argument("--state", help="local step_b_state to resume from")
    s.add_argument("--upload-corpus", action="store_true", help="(re)upload the corpus texts dataset")
    sub.add_parser("status")
    f = sub.add_parser("fetch")
    f.add_argument("--out", required=True)
    a = p.parse_args()
    {"push": push, "status": status, "fetch": fetch}[a.cmd](a)
