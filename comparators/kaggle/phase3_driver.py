"""
Phase 3 driver for a free Kaggle GPU session (also runs on any CUDA machine).

Protocol (Prof. Laakkonen, unchanged):
  Step A  reproduce the comparator's published metrics on its own test split, scored by the
          pre-registered scorers (comparators/cuad_step_a.py, comparators/gpu/contractnli_step_a.py);
  Step B  only if Step A passed: run the comparator on our frozen corpus (corpus/manifest.csv);
  Step C  only if Step A passed: paired per-unit comparison with the v7.2.0 engine (exact McNemar).
Nothing here tunes a model, a threshold or a tolerance; a STEP_A_FAIL is final for that comparator.

Order on GPU 0: for each CUAD model in --models: Step A -> (if PASS) Step B -> Step C.
ContractNLI (train conf_base.yml, seed 42 -> test.py -> Step A -> pairing) runs on GPU 1 in
parallel when two GPUs are visible (Kaggle T4 x2), otherwise after the CUAD queue. It is pinned to
ONE GPU because the authors' train.py would otherwise use DataParallel and double the effective
batch size of the published configuration.

Everything persistent lives under --state (default /kaggle/working/phase3_state, which Kaggle
saves as the notebook version's output). Every stage is resumable from there:
  * CUAD inference checkpoints after every question (resume loses at most one question);
  * ContractNLI training is not resumable inside train.py, so it only starts when the remaining
    budget covers --cnli-train-hours, and a partial training directory is discarded.
The driver stops itself at --budget-hours (default 11, below Kaggle's 12 h limit) so the session
ends cleanly and its output is saved. Interrupted work is reported as INCOMPLETE, never as a result.

    python experiments/followup/comparators/kaggle/phase3_driver.py --state /kaggle/working/phase3_state
"""
import argparse
import csv
import fcntl
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
F = HERE.parents[1]                      # experiments/followup
REPO = F.parents[1]
CUAD_MODELS = {"roberta-base": "akdeniz27/roberta-base-cuad",
               "roberta-large": "akdeniz27/roberta-large-cuad",
               "deberta-v2-xlarge": "akdeniz27/deberta-v2-xlarge-cuad"}
CUAD_PINS = ["transformers==4.57.6", "tokenizers==0.22.2"]   # versions used for the CPU run
CNLI_REPO, CNLI_COMMIT = "https://github.com/stanfordnlp/contract-nli-bert", "058c56f"
CNLI_TORCH = "torch==1.8.1+cu111"        # the authors' README build for newer GPUs (sm_60/sm_75 OK)
# 2021-era versions of two unpinned transitive dependencies; found by the CPU smoke test:
# transformers 4.5.1's version check fails under packaging>=22, tensorboard 2.4.1 under protobuf>=4.
CNLI_EXTRA_PINS = ["packaging==20.9", "protobuf==3.20.3"]
MICROMAMBA = "https://micro.mamba.pm/api/micromamba/linux-64/latest"
FROZEN_MANIFEST_SHA = "3bcd0d90806f244197d7afe6ca1752dbcae4dad6430d06c7b81fd4130a8c755b"
CUAD_TEST_QUESTIONS = 4182


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Budget:
    def __init__(self, deadline):
        self.deadline = deadline

    def left_h(self):
        return (self.deadline - time.time()) / 3600


class Driver:
    def __init__(self, a):
        self.a = a
        self.state = Path(a.state)
        self.state.mkdir(parents=True, exist_ok=True)
        (self.state / "logs").mkdir(exist_ok=True)
        self.budget = Budget(a.deadline)
        self.tmp = Path(a.tmp)
        self.tmp.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- bookkeeping
    def mark(self, stage, status, **extra):
        path = self.state / "stages.json"
        with open(self.state / ".stages.lock", "w") as lock:   # the ContractNLI worker writes here too
            fcntl.flock(lock, fcntl.LOCK_EX)
            stages = json.loads(path.read_text()) if path.exists() else {}
            stages[stage] = {"status": status, "at": now(), **extra}
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(stages, indent=2, default=str) + "\n")
            os.replace(tmp, path)
        print(f"[{now()}] {stage}: {status} {extra if extra else ''}", flush=True)

    def stage(self, stage):
        path = self.state / "stages.json"
        return json.loads(path.read_text()).get(stage, {}).get("status") if path.exists() else None

    def run(self, name, cmd, cwd, env=None, check=True):
        """Run a subprocess with a log file under state/logs; stop it at the budget deadline."""
        log = self.state / "logs" / f"{name}.log"
        with open(log, "a", encoding="utf-8") as fh:
            fh.write(f"\n===== {now()} {' '.join(map(str, cmd))}\n")
            fh.flush()
            p = subprocess.Popen([str(c) for c in cmd], cwd=cwd, env={**os.environ, **(env or {})},
                                 stdout=fh, stderr=subprocess.STDOUT, start_new_session=True)
            while p.poll() is None:
                if time.time() > self.budget.deadline:
                    os.killpg(p.pid, signal.SIGTERM)
                    try:
                        p.wait(60)
                    except subprocess.TimeoutExpired:
                        os.killpg(p.pid, signal.SIGKILL)
                    fh.write(f"===== {now()} stopped at session budget\n")
                    return "BUDGET"
                time.sleep(5)
        if p.returncode != 0 and check:
            raise RuntimeError(f"{name} failed with exit {p.returncode}; see {log}")
        return p.returncode

    # ---------------------------------------------------------------- environment
    def environment(self):
        snapshot = REPO / "SOURCE_COMMIT"          # private-repo route: code arrives as a git-archive snapshot
        commit = snapshot.read_text().strip() if snapshot.exists() else self.git("rev-parse", "HEAD")
        info = {"at": now(), "python": sys.version.split()[0], "repo_commit": commit,
                "code_source": "git-archive snapshot" if snapshot.exists() else "git clone",
                "repo_dirty": False if snapshot.exists() else bool(self.git("status", "--porcelain")), "budget_deadline_utc":
                datetime.fromtimestamp(self.budget.deadline, timezone.utc).isoformat(timespec="seconds")}
        try:
            smi = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
                                 capture_output=True, text=True)
            info["gpus"] = [g.strip() for g in smi.stdout.splitlines() if g.strip()] if smi.returncode == 0 else []
        except FileNotFoundError:          # no NVIDIA driver at all
            info["gpus"] = []
        path = self.state / "environment.json"
        sessions = json.loads(path.read_text()) if path.exists() else []
        sessions.append(info)
        path.write_text(json.dumps(sessions, indent=2) + "\n")
        print(json.dumps(info, indent=1), flush=True)
        if not info["gpus"]:
            self.mark("environment", "BLOCKED_NO_GPU", note="enable the GPU T4 x2 accelerator; nothing was run")
            sys.exit(3)
        return info

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.strip()

    # ---------------------------------------------------------------- data
    def data(self):
        if self.stage("data") == "OK" and (F / "corpus/texts").exists() and (F / "external/cuad_split/test.json").exists():
            return
        self.run("fetch_external", ["bash", "comparators/gpu/fetch_external.sh"], cwd=F)
        self.run("build_corpus", [sys.executable, "-m", "experiments.followup.build_corpus"], cwd=REPO)
        got = hashlib.sha256((F / "corpus/manifest.csv").read_bytes()).hexdigest()
        if got != FROZEN_MANIFEST_SHA:
            self.mark("data", "BLOCKED_CORPUS_MISMATCH", got=got, expected=FROZEN_MANIFEST_SHA)
            raise SystemExit("rebuilt corpus differs from the frozen manifest: refusing to run on different data")
        bad = [r["doc_id"] for r in csv.DictReader(open(F / "corpus/manifest.csv", encoding="utf-8"))
               if hashlib.sha256((F / "corpus/texts" / f"{r['doc_id']}.txt").read_bytes()).hexdigest() != r["text_sha256"]]
        if bad:
            self.mark("data", "BLOCKED_TEXT_HASH_MISMATCH", docs=bad[:20])
            raise SystemExit("document text hashes differ from the frozen manifest")
        self.mark("data", "OK", manifest_sha256=got)

    # ---------------------------------------------------------------- CUAD
    def cuad_deps(self):
        if self.stage("cuad_deps") != "OK":
            self.run("cuad_deps", [sys.executable, "-m", "pip", "install", "-q", *CUAD_PINS], cwd=REPO)
            freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True).stdout
            (self.state / "pip_freeze_cuad.txt").write_text(freeze)
            self.mark("cuad_deps", "OK")

    def cuad(self, key, gpu):
        model, env = CUAD_MODELS[key], {"CUDA_VISIBLE_DEVICES": gpu}
        a_dir, b_dir, c_dir = (self.state / f"cuad_{key}_gpu", self.state / f"cuad_{key}_gpu_corpus",
                               self.state / f"paired_cuad_{key}")
        # Step A: inference on the CUAD test split, then the pre-registered scorer.
        if self.stage(f"cuad_{key}_step_a") not in ("STEP_A_PASS", "STEP_A_FAIL"):
            self.mark(f"cuad_{key}_step_a", "RUNNING")
            r = self.run(f"cuad_{key}_validate", [sys.executable, "comparators/cuad_qa.py", "validate", "--model", model,
                                                  "--test-json", "external/cuad_split/test.json", "--out", a_dir],
                         cwd=F, env=env)
            if r == "BUDGET":
                self.mark(f"cuad_{key}_step_a", "INCOMPLETE_BUDGET", questions_done=self.count(a_dir / "nbest_partial.jsonl"),
                          questions_expected=CUAD_TEST_QUESTIONS)
                return False
            rc = self.run(f"cuad_{key}_score", [sys.executable, "comparators/cuad_step_a.py", "--pred-dir", a_dir,
                                                "--model", key], cwd=F, check=False)
            res = a_dir / "step_a_result.json"
            if rc != 0 or not res.exists():
                self.mark(f"cuad_{key}_step_a", "INCOMPLETE_NOT_SCORED", exit=rc)
                return False
            sa = json.loads(res.read_text())
            self.mark(f"cuad_{key}_step_a", sa["status"], reproduced=sa.get("reproduced"), published=sa.get("published"))
        if self.stage(f"cuad_{key}_step_a") != "STEP_A_PASS":
            self.mark(f"cuad_{key}_step_bc", "GATED_STEP_A_NOT_PASSED")
            return True
        # Step B: the same frozen decoding on our frozen corpus (all slices, all 41 categories).
        if self.stage(f"cuad_{key}_step_b") != "COMPLETE":
            self.mark(f"cuad_{key}_step_b", "RUNNING")
            r = self.run(f"cuad_{key}_corpus", [sys.executable, "comparators/cuad_qa.py", "corpus", "--model", model,
                                                "--questions", "comparators/cuad_questions.json",
                                                "--manifest", "corpus/manifest.csv", "--texts", "corpus/texts",
                                                "--out", b_dir], cwd=F, env=env)
            expected = self.count(F / "corpus/manifest.csv") * len(json.load(open(F / "comparators/cuad_questions.json")))
            done = self.count(b_dir / "predictions.jsonl")
            if r == "BUDGET" or done != expected:
                self.mark(f"cuad_{key}_step_b", "INCOMPLETE_BUDGET" if r == "BUDGET" else "INCOMPLETE",
                          units_done=done, units_expected=expected)
                return False
            self.mark(f"cuad_{key}_step_b", "COMPLETE", units=done)
        # Step C: paired units on the CUAD test slice (engine v7.2.0 vs this model), own output dir.
        if self.stage(f"cuad_{key}_step_c") != "COMPLETE":
            self.run(f"cuad_{key}_paired", [sys.executable, "-m", "experiments.followup.evaluate_paired", "v7.2.0",
                                            "--cuad-model-dir", a_dir, "--out-dir", c_dir], cwd=REPO)
            self.mark(f"cuad_{key}_step_c", "COMPLETE", report=str(c_dir / "paired_report.json"))
        return True

    @staticmethod
    def count(path):
        if not Path(path).exists():
            return 0
        with open(path, encoding="utf-8") as fh:
            return sum(1 for line in fh if line.strip()) - (1 if Path(path).suffix == ".csv" else 0)

    # ---------------------------------------------------------------- ContractNLI
    def contractnli(self, gpu):
        st = self.state / "contractnli_bert-base"
        out, env = st / "output_base", {"CUDA_VISIBLE_DEVICES": gpu}
        work = self.tmp / "contract-nli-bert"
        if self.stage("cnli_step_a") in ("STEP_A_PASS", "STEP_A_FAIL") and self.stage("cnli_pairing") in (
                "COMPLETE", "GATED_STEP_A_NOT_PASSED"):
            return True
        if not (work / ".git").exists():
            self.run("cnli_clone", ["git", "clone", "-q", CNLI_REPO, work], cwd=self.tmp)
        self.run("cnli_checkout", ["git", "checkout", "-q", CNLI_COMMIT], cwd=work)
        py = self.cnli_env(work)
        (work / "data").mkdir(exist_ok=True)
        for s in ("train", "dev", "test"):
            shutil.copy(F / "external/contract-nli" / f"{s}.json", work / "data" / f"{s}.json")
        # Training: one published configuration, unmodified, seed 42.
        if self.stage("cnli_train") != "COMPLETE":
            if self.budget.left_h() < self.a.cnli_train_hours:
                self.mark("cnli_train", "DEFERRED_INSUFFICIENT_BUDGET", hours_left=round(self.budget.left_h(), 2),
                          hours_needed=self.a.cnli_train_hours)
                return False
            if out.exists():
                shutil.rmtree(out)        # a partial run cannot be resumed by train.py
            self.mark("cnli_train", "RUNNING")
            r = self.run("cnli_train", [py, "train.py", "./data/conf_base.yml", out], cwd=work, env=env)
            if r == "BUDGET":
                self.mark("cnli_train", "INCOMPLETE_BUDGET")
                return False
            self.mark("cnli_train", "COMPLETE")
        if self.stage("cnli_test") != "COMPLETE":
            r = self.run("cnli_test", [py, "test.py", out, "./data/test.json", f"{out}/test_"], cwd=work, env=env)
            if r == "BUDGET":
                self.mark("cnli_test", "INCOMPLETE_BUDGET")
                return False
            self.mark("cnli_test", "COMPLETE")
        self.run("cnli_step_a", [sys.executable, "comparators/gpu/contractnli_step_a.py", "--metrics",
                                 out / "test_metrics.json", "--backbone", "bert-base", "--out", st], cwd=F)
        sa = json.loads((st / "step_a_result.json").read_text())
        self.mark("cnli_step_a", sa["status"], reproduced=sa.get("reproduced"), key_paths=sa.get("key_paths_used"))
        if sa["status"] != "STEP_A_PASS":
            self.mark("cnli_pairing", "GATED_STEP_A_NOT_PASSED")
            return True
        self.run("cnli_pairing", [sys.executable, "comparators/gpu/pair_contractnli.py", "--result", out / "test_result.json",
                                  "--step-a", st / "step_a_result.json", "--out", st], cwd=F)
        self.mark("cnli_pairing", "COMPLETE", report=str(st / "paired_result.json"))
        return True

    def cnli_env(self, work):
        """Python 3.8 + the authors' pinned requirements, isolated from the notebook's Python."""
        mm, env_dir = self.tmp / "bin/micromamba", self.tmp / "cnli-env"
        py = env_dir / "bin/python"
        if py.exists() and self.stage("cnli_env") == "OK":
            return py
        if not mm.exists():
            self.run("cnli_env", ["bash", "-c", f"curl -fsSL {MICROMAMBA} | tar -xj -C {self.tmp} bin/micromamba"], cwd=self.tmp)
        self.run("cnli_env", [mm, "create", "-y", "-q", "-p", env_dir, "-c", "conda-forge", "python=3.8"], cwd=self.tmp,
                 env={"MAMBA_ROOT_PREFIX": str(self.tmp / "mamba")})
        # The authors' pins, minus torch==1.7.1 (no build for these GPUs); torch comes from CNLI_TORCH.
        req = self.tmp / "cnli_requirements.txt"
        authors = (work / "requirements.txt").read_text().splitlines()
        req.write_text("".join(l + "\n" for l in authors if l.strip() and not l.startswith("torch==")))
        self.run("cnli_env", [py, "-m", "pip", "install", "-q", CNLI_TORCH, "-f",
                              "https://download.pytorch.org/whl/torch_stable.html"], cwd=self.tmp)
        self.run("cnli_env", [py, "-m", "pip", "install", "-q", "-r", req, *CNLI_EXTRA_PINS], cwd=self.tmp)
        ok = subprocess.run([py, "-c", "import torch; assert torch.cuda.is_available(); print(torch.__version__)"],
                            capture_output=True, text=True)
        if ok.returncode != 0:
            self.mark("cnli_env", "BLOCKED_TORCH_CUDA", stderr=ok.stderr[-500:])
            raise RuntimeError("ContractNLI env cannot see the GPU")
        (self.state / "pip_freeze_contractnli.txt").write_text(
            subprocess.run([py, "-m", "pip", "freeze"], capture_output=True, text=True).stdout)
        self.mark("cnli_env", "OK", torch=ok.stdout.strip())
        return py

    # ---------------------------------------------------------------- orchestration
    def main(self):
        if self.a.worker == "contractnli":
            try:
                self.contractnli(gpu=self.a.gpu)
            except Exception as e:  # recorded, never converted into a score
                self.mark("contractnli_worker", "ERROR", error=str(e)[:500])
                raise
            return
        info = self.environment()
        self.data()
        worker = None
        two_gpus = len(info["gpus"]) >= 2
        if two_gpus and not self.a.skip_contractnli:
            worker = subprocess.Popen([sys.executable, __file__, "--worker", "contractnli", "--gpu", "1",
                                       "--state", self.state, "--tmp", self.tmp, "--deadline", str(self.budget.deadline),
                                       "--cnli-train-hours", str(self.a.cnli_train_hours)], cwd=REPO)
        # One GPU: RoBERTa-base first, then ContractNLI, then the larger CUAD models.
        queue = [("cuad", k) for k in self.a.models]
        if not two_gpus and not self.a.skip_contractnli:
            queue.insert(1, ("cnli", None))
        try:
            self.cuad_deps()
            for kind, key in queue:
                if time.time() > self.budget.deadline:
                    break
                if kind == "cnli":
                    try:
                        self.contractnli(gpu="0")
                    except Exception as e:      # ContractNLI failure must not stop the CUAD queue
                        self.mark("contractnli_worker", "ERROR", error=str(e)[:500])
                elif not self.cuad(key, gpu="0"):
                    break
        except Exception as e:                   # recorded and reported, never converted into a score
            self.mark("cuad_queue", "ERROR", error=str(e)[:500])
        finally:
            if worker is not None:
                worker.wait()
            subprocess.run([sys.executable, str(HERE / "phase3_report.py"), "--state", str(self.state)], check=False)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--state", default="/kaggle/working/phase3_state")
    p.add_argument("--tmp", default="/tmp/phase3", help="scratch space that need not persist (envs, clones)")
    p.add_argument("--models", nargs="+", default=list(CUAD_MODELS), choices=list(CUAD_MODELS))
    p.add_argument("--budget-hours", type=float, default=11.0)
    p.add_argument("--deadline", type=float, help="absolute epoch seconds (set for the worker)")
    p.add_argument("--cnli-train-hours", type=float, default=5.0,
                   help="minimum budget left before ContractNLI training may start (it cannot resume)")
    p.add_argument("--skip-contractnli", action="store_true")
    p.add_argument("--worker", choices=["contractnli"])
    p.add_argument("--gpu", default="0")
    a = p.parse_args()
    if a.deadline is None:
        a.deadline = time.time() + a.budget_hours * 3600
    Driver(a).main()
