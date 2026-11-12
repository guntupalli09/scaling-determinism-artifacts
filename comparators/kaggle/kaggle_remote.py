"""
Drive the Phase 3 notebook on Kaggle through the official Kaggle CLI (no browser).

Needs KAGGLE_USERNAME and KAGGLE_KEY (or KAGGLE_API_TOKEN) in the environment. Everything is
created private. Only the free accelerator is ever requested (NvidiaTeslaT4 = GPU T4 x2).

    python kaggle_remote.py push   [--resume-state DIR]   # upload notebook (+ state dataset) and run it
    python kaggle_remote.py status                         # queued / running / complete / error
    python kaggle_remote.py fetch  --out DIR               # download the version's output (phase3_state/)

Resume: --resume-state uploads a previously fetched phase3_state/ as the private dataset
<user>/triage-phase3-state and attaches it; the notebook's resume cell continues from it.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SLUG = "triage-phase3-comparators"
STATE_SLUG = "triage-phase3-state"
CODE_SLUG = "triage-phase3-code"
FREE_ACCELERATOR = "NvidiaTeslaT4"
KAGGLE = [sys.executable, "-m", "kaggle.cli"] if shutil.which("kaggle") is None else ["kaggle"]


def user():
    u = os.environ.get("KAGGLE_USERNAME")
    if not u:
        sys.exit("KAGGLE_USERNAME is not set")
    return u


def kaggle(*args, check=True):
    p = subprocess.run([*KAGGLE, *args], capture_output=True, text=True)
    print(p.stdout.strip(), p.stderr.strip(), sep="\n" if p.stderr.strip() else "")
    if check and p.returncode != 0:
        sys.exit(p.returncode)
    return p


def push_state(state_dir):
    u = user()
    with tempfile.TemporaryDirectory() as d:
        dst = Path(d) / "phase3_state"
        # Model weights are re-creatable and large; the checkpoints that matter are the JSONL/JSON files.
        shutil.copytree(state_dir, dst, ignore=shutil.ignore_patterns("*.bin", "*.pt", "*.safetensors", "optimizer*"))
        (Path(d) / "dataset-metadata.json").write_text(json.dumps(
            {"title": "triage phase3 state", "id": f"{u}/{STATE_SLUG}", "licenses": [{"name": "other"}]}))
        exists = kaggle("datasets", "status", f"{u}/{STATE_SLUG}", check=False).returncode == 0
        if exists:
            kaggle("datasets", "version", "-p", d, "-m", "phase3 state", "--dir-mode", "zip")
        else:
            kaggle("datasets", "create", "-p", d, "--dir-mode", "zip")
    return f"{u}/{STATE_SLUG}"


def push_code(ref):
    """Private snapshot of the research branch (the GitHub repository is private, so Kaggle cannot clone it)."""
    u = user()
    # git archive run inside a subdirectory archives only that subdirectory: always run it at the repo root.
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=HERE, capture_output=True, text=True,
                          check=True).stdout.strip()
    commit = subprocess.run(["git", "rev-parse", ref], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
    with tempfile.TemporaryDirectory() as d:
        archive = Path(d) / "triage_code.tar.gz"
        subprocess.run(["git", "archive", "--format=tar.gz", f"--add-virtual-file=SOURCE_COMMIT:{commit}\n",
                        "-o", str(archive), commit], cwd=root, check=True)
        listing = subprocess.run(["tar", "-tzf", str(archive)], capture_output=True, text=True, check=True).stdout
        if "experiments/followup/comparators/kaggle/phase3_driver.py" not in listing:
            sys.exit("code snapshot is incomplete; refusing to upload")
        (Path(d) / "dataset-metadata.json").write_text(json.dumps(
            {"title": "triage phase3 code", "id": f"{u}/{CODE_SLUG}", "licenses": [{"name": "other"}]}))
        exists = kaggle("datasets", "status", f"{u}/{CODE_SLUG}", check=False).returncode == 0
        if exists:
            kaggle("datasets", "version", "-p", d, "-m", f"code {commit[:10]}")
        else:
            kaggle("datasets", "create", "-p", d)
    print("code snapshot:", commit)
    return f"{u}/{CODE_SLUG}"


def push(a):
    u = user()
    sources = [push_code(a.code_ref)]
    sources += [push_state(a.resume_state)] if a.resume_state else []
    with tempfile.TemporaryDirectory() as d:
        shutil.copy(HERE / "phase3_kaggle.ipynb", Path(d) / "phase3_kaggle.ipynb")
        (Path(d) / "kernel-metadata.json").write_text(json.dumps({
            "id": f"{u}/{SLUG}", "title": SLUG, "code_file": "phase3_kaggle.ipynb", "language": "python",
            "kernel_type": "notebook", "is_private": "true", "enable_gpu": "true", "enable_internet": "true",
            "machine_shape": FREE_ACCELERATOR, "dataset_sources": sources, "competition_sources": [],
            "kernel_sources": [], "model_sources": []}, indent=1))
        kaggle("kernels", "push", "-p", d, "--accelerator", FREE_ACCELERATOR)


def status(a):
    kaggle("kernels", "status", f"{user()}/{SLUG}")


def fetch(a):
    Path(a.out).mkdir(parents=True, exist_ok=True)
    kaggle("kernels", "output", f"{user()}/{SLUG}", "-p", a.out)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("push")
    s.add_argument("--resume-state")
    s.add_argument("--code-ref", default="origin/claude/adoring-heisenberg-gd2tv1",
                   help="commit or ref of the research branch to snapshot (must be pushed)")
    sub.add_parser("status")
    f = sub.add_parser("fetch")
    f.add_argument("--out", required=True)
    a = p.parse_args()
    {"push": push, "status": status, "fetch": fetch}[a.cmd](a)
