"""
ContractNLI Span NLI BERT — Step A check (reproduce paper Table 3 on the ContractNLI test split).

PRE-REGISTERED 2026-10-17, before any model was trained:
  Targets (Koreeda & Manning 2021, Table 3, mean of 3 best of a 100-config sweep):
    bert-base : evidence mAP .885, NLI accuracy .838, F1(E) .765
    bert-large: evidence mAP .922, NLI accuracy .875, F1(E) .834
  Pass iff |mAP - t| <= 0.03 AND |Acc - t| <= 0.03 AND |F1(E) - t| <= 0.05.
  We train ONE published configuration (conf_base.yml, seed 42), not the sweep, so a shortfall is
  plausible; it is reported as STEP_A_FAIL, never tuned toward the target.
  Metrics are read from the authors' own test.py output (metrics.json). The exact key paths are
  version-specific: if any required key is missing the result is INCONCLUSIVE (keys printed),
  not PASS.

    python contractnli_step_a.py --metrics <prefix>metrics.json --backbone bert-base --out <dir>
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

TARGETS = {"bert-base": {"map": 0.885, "accuracy": 0.838, "f1_entailment": 0.765},
           "bert-large": {"map": 0.922, "accuracy": 0.875, "f1_entailment": 0.834}}
TOL = {"map": 0.03, "accuracy": 0.03, "f1_entailment": 0.05}
# Candidate key paths in the authors' metrics.json (contract_nli/evaluation.py evaluate_all).
PATHS = {"accuracy": [("macro_label_micro_doc", "class", "accuracy"), ("micro_label_micro_doc", "class", "accuracy")],
         "f1_entailment": [("macro_label_micro_doc", "class", "f1_entailment"), ("micro_label_micro_doc", "class", "f1_entailment")],
         "map": [("micro_label_micro_doc", "span", "map"), ("macro_label_micro_doc", "span", "map")]}


def find(d, paths):
    for p in paths:
        cur = d
        try:
            for k in p:
                cur = cur[k]
            return float(cur), ".".join(p)
        except (KeyError, TypeError):
            continue
    return None, None


def flat_keys(d, prefix=""):
    out = []
    for k, v in d.items():
        out += flat_keys(v, f"{prefix}{k}.") if isinstance(v, dict) else [prefix + k]
    return out


def main(a):
    m = json.load(open(a.metrics))
    got, used = {}, {}
    for k, paths in PATHS.items():
        got[k], used[k] = find(m, paths)
    out = {"checked_at": datetime.now(timezone.utc).isoformat(), "backbone": a.backbone,
           "targets": TARGETS[a.backbone], "tolerance": TOL, "reproduced": got, "key_paths_used": used}
    if any(v is None for v in got.values()):
        out["status"] = "INCONCLUSIVE_KEYS_NOT_FOUND"
        out["available_keys"] = flat_keys(m)
    else:
        t = TARGETS[a.backbone]
        ok = all(abs(got[k] - t[k]) <= TOL[k] for k in t)
        out["delta"] = {k: got[k] - t[k] for k in t}
        out["status"] = "STEP_A_PASS" if ok else "STEP_A_FAIL"
    Path(a.out).mkdir(parents=True, exist_ok=True)
    (Path(a.out) / "step_a_result.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--metrics", required=True)
    p.add_argument("--backbone", required=True, choices=sorted(TARGETS))
    p.add_argument("--out", required=True)
    main(p.parse_args())
