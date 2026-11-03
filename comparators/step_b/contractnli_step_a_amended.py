"""
ContractNLI Step A re-check under the approved amendment (review_package/DECISION_STEP_B_APPROVAL.md, B9).

Identical to the pre-registered comparators/gpu/contractnli_step_a.py (same targets, tolerances, accuracy and
F1(E) keys, same metrics file) except that evidence mAP is read at the paper's per-query aggregation,
micro_label_macro_doc.span.map (Koreeda & Manning 2021, sec. 4.2). The pooled value used by the pre-registration
is reported alongside. The pre-registered result file is not touched.

    python contractnli_step_a_amended.py --metrics <test_metrics.json> --preregistered <step_a_result.json> --out <dir>
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "gpu"))
from contractnli_step_a import PATHS, TARGETS, TOL, find  # noqa: E402

AMENDED_PATHS = dict(PATHS, map=[("micro_label_macro_doc", "span", "map")])


def main(a):
    m = json.load(open(a.metrics))
    got, used = {}, {}
    for k, paths in AMENDED_PATHS.items():
        got[k], used[k] = find(m, paths)
    if any(v is None for v in got.values()):
        sys.exit(f"metric key missing: {used}")
    t = TARGETS["bert-base"]
    delta = {k: got[k] - t[k] for k in t}
    ok = all(abs(delta[k]) <= TOL[k] for k in t)
    out = {"checked_at": datetime.now(timezone.utc).isoformat(), "backbone": "bert-base", "targets": t,
           "tolerance": TOL, "reproduced": got, "key_paths_used": used, "delta": delta,
           "pooled_map_preregistered_key": find(m, PATHS["map"])[0],
           "preregistered_status": json.load(open(a.preregistered))["status"],
           "basis": "Protocol amendment B9, approved by Prof. Laakkonen on 2026-11-02 "
                    "(review_package/DECISION_STEP_B_APPROVAL.md)",
           "status": "STEP_A_PASS" if ok else "STEP_A_FAIL"}
    Path(a.out).mkdir(parents=True, exist_ok=True)
    (Path(a.out) / "step_a_result_amended.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--metrics", required=True)
    p.add_argument("--preregistered", required=True)
    p.add_argument("--out", required=True)
    main(p.parse_args())
