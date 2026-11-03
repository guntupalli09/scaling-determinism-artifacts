"""
Phase 2/4: frozen, hashed ruleset releases.

Every historical release is identified by semantic version + Git commit +
SHA-256 of its canonicalised rule definitions, as agreed with Prof. Laakkonen.
Each release is materialised from Git into an isolated tree and executed in a
subprocess, so no two releases ever share imported code.

    python -m experiments.followup.releases freeze        # writes releases/manifest_v2.json
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FOLLOWUP_DIR = Path(__file__).parent
CHECKOUT_DIR = FOLLOWUP_DIR / ".releases"
MANIFEST_PATH = FOLLOWUP_DIR / "releases" / "manifest_v2.json"
WORKER = FOLLOWUP_DIR / "release_worker.py"

# Final commit of each release (last commit touching the rule engine while
# rules/version.json carried that version). "role" says how a release is used.
RELEASES = [
    {"label": "v1.0.3-iccs", "version": "1.0.3", "commit": "ae097e74", "role": "checkpoint",
     "note": "Commit the ICCS 2026 experiments ran on"},
    {"label": "v1.0.3", "version": "1.0.3", "commit": "1a270a56", "role": "checkpoint",
     "note": "Final v1.0.3 state"},
    {"label": "v2.0.0", "version": "2.0.0", "commit": "468dee0f", "role": "checkpoint"},
    {"label": "v2.1.0", "version": "2.1.0", "commit": "3600870f", "role": "checkpoint"},
    {"label": "v3.0.0", "version": "3.0.0", "commit": "decaa703", "role": "checkpoint"},
    {"label": "v4.0.0", "version": "4.0.0", "commit": "623d3c72", "role": "checkpoint"},
    {"label": "v5.0.0", "version": "5.0.0", "commit": "5aed1d53", "role": "checkpoint"},
    {"label": "v6.0.0", "version": "6.0.0", "commit": "96cf3954", "role": "checkpoint"},
    {"label": "v7.0.0", "version": "7.0.0", "commit": "7d4f3b19", "role": "checkpoint"},
    {"label": "v7.1.0", "version": "7.1.0", "commit": "c251a6da", "role": "checkpoint"},
    {"label": "v7.2.0", "version": "7.2.0", "commit": "51d709e8", "role": "baseline",
     "note": "Frozen Phase 1 baseline; predates Benchmark - TC (added 2026-08-01)"},
    # Later engine states still labelled 7.2.0. They were changed after the MCC
    # Q1-Q2 corpus was in the repo, so they are not clean on that corpus.
    {"label": "v7.2.0+f5257056", "version": "7.2.0", "commit": "f5257056", "role": "post-corpus"},
    {"label": "v7.2.0+8b79a386", "version": "7.2.0", "commit": "8b79a386", "role": "post-corpus"},
    {"label": "v7.2.0+6b9bfc8e", "version": "7.2.0", "commit": "6b9bfc8e", "role": "post-corpus"},
    {"label": "v7.2.0+20294216", "version": "7.2.0", "commit": "20294216", "role": "post-corpus"},
]

EXCLUDE = ["Benchmark - TC", "static", "artifacts", "experiments", "tests", "triagebench",
           "triagebench_live", "benchmarks", "IEEE TPS 2026", "rules/Submission", "templates", "docs"]


def by_label(label: str) -> dict:
    return next(r for r in RELEASES if r["label"] == label)


def materialize(release: dict) -> Path:
    target = CHECKOUT_DIR / release["label"]
    if (target / "rules_engine.py").exists():
        return target
    target.mkdir(parents=True, exist_ok=True)
    pathspec = ["."] + [f":(exclude){p}" for p in EXCLUDE]
    archive = subprocess.run(["git", "archive", release["commit"], "--", *pathspec],
                             cwd=REPO_ROOT, check=True, capture_output=True).stdout
    subprocess.run(["tar", "-x", "-C", str(target)], input=archive, check=True)
    return target


def run_worker(release: dict, job: dict, timeout: int = 7200, env: dict = None):
    tree = materialize(release)
    proc = subprocess.run([sys.executable, "-I", str(WORKER)], cwd=tree, input=json.dumps(job),
                          capture_output=True, text=True, timeout=timeout, env=env)
    if proc.returncode != 0:
        raise RuntimeError(f"{release['label']} worker failed:\n{proc.stderr[-3000:]}\n{proc.stdout[-500:]}")
    return json.loads(proc.stdout)


def _file_sha256(tree: Path, rel: str) -> str:
    p = tree / rel
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""


def freeze() -> list:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    out = []
    for release in RELEASES:
        tree = materialize(release)
        info = run_worker(release, {"mode": "rules"})
        full_commit = subprocess.run(["git", "rev-parse", release["commit"]], cwd=REPO_ROOT,
                                     check=True, capture_output=True, text=True).stdout.strip()
        commit_date = subprocess.run(["git", "log", "-1", "--format=%cI", release["commit"]], cwd=REPO_ROOT,
                                     check=True, capture_output=True, text=True).stdout.strip()
        entry = {**release, "commit": full_commit, "commit_date": commit_date,
                 "rules_engine_py_sha256": _file_sha256(tree, "rules_engine.py"),
                 "version_json_sha256": _file_sha256(tree, "rules/version.json"), **info}
        out.append(entry)
        print(f"{entry['label']:<18} {entry['rule_count']:>4} rules  {entry['ruleset_sha256'][:16]}  "
              f"engine {entry['rules_engine_py_sha256'][:12]}")
    MANIFEST_PATH.write_text(json.dumps(out, indent=2) + "\n")
    return out


if __name__ == "__main__":
    if sys.argv[1:] == ["freeze"]:
        freeze()
    else:
        sys.exit(__doc__)
