"""
One GPU worker for CUAD Step B: works through a queue of models, for each its own shard(s) of the chunk plan,
until the deadline. Used by the Kaggle notebook (one worker per GPU) and by Modal.

  roberta-base       : whole corpus (its cuad_test slice regenerates the Step A predictions, then re-scored);
  roberta-large,
  deberta-v2-xlarge  : corpus minus cuad_test (that slice = corrected Step A predictions, already committed),
                       after check_against_step_a.py passes in this session.

    python worker.py --state-root DIR --queue roberta-base roberta-large deberta-v2-xlarge \
        --shard-of 2 --shards 0 --deadline-epoch <unix time>
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKIP = {"roberta-base": [], "roberta-large": ["cuad_test"], "deberta-v2-xlarge": ["cuad_test"]}


def remaining_chunks(state, shard_of, shards):
    plan = state / "plan.json"
    if not plan.exists():
        return None
    n = len(json.load(open(plan))["chunks"])
    return [i for i in range(n) if i % shard_of in shards and not (state / f"chunk_{i:04d}" / "nbest.json.gz").exists()]


def main(a):
    root = Path(a.state_root)
    tag = f"shards{'-'.join(map(str, a.shards))}of{a.shard_of}"
    for m in a.queue:
        state = root / m
        state.mkdir(parents=True, exist_ok=True)
        left = remaining_chunks(state, a.shard_of, a.shards)
        if left == []:
            print(f"[{tag}] {m}: my shards are complete", flush=True)
            continue
        hours = (a.deadline_epoch - time.time()) / 3600
        if hours < 0.3:
            print(f"[{tag}] deadline reached before {m}", flush=True)
            return
        if SKIP[m]:
            chk = state / f"preflight_{tag}"
            r = subprocess.run([sys.executable, str(HERE / "check_against_step_a.py"), "--model", m, "--out", str(chk)])
            if r.returncode != 0:
                print(f"[{tag}] {m}: PRE-FLIGHT CHECK FAILED; not running this model (see {chk}/check.json)", flush=True)
                continue
        hours = (a.deadline_epoch - time.time()) / 3600
        cmd = [sys.executable, str(HERE / "cuad_step_b.py"), "run", "--model", f"akdeniz27/{m}-cuad",
               "--state", str(state), "--budget-hours", f"{hours:.3f}", "--shard-of", str(a.shard_of),
               "--shards", *map(str, a.shards), "--threads", str(a.threads)]
        if SKIP[m]:
            cmd += ["--skip-slices", *SKIP[m]]
        subprocess.run(cmd, check=True)
        if remaining_chunks(state, a.shard_of, a.shards):
            print(f"[{tag}] {m}: stopped by the session budget; resume next session", flush=True)
            return
        print(f"[{tag}] {m}: my shards are complete", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--state-root", required=True)
    p.add_argument("--queue", nargs="+", required=True, choices=sorted(SKIP))
    p.add_argument("--shard-of", type=int, default=1)
    p.add_argument("--shards", type=int, nargs="+", default=[0])
    p.add_argument("--deadline-epoch", type=float, required=True)
    p.add_argument("--threads", type=int, default=2)
    main(p.parse_args())
