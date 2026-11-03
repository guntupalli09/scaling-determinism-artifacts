"""
Reviewer verification for "The Cost of Scaling Determinism" (research package).

Runs with the Python standard library only:
    python verify.py            # 1) every file against SHA256SUMS; 2) recompute Tables 5 and 6 (Step C);
                                # 3) recompute the injection-attribution counts (Table 3)
Prints each recomputed value next to the value reported in the manuscript and exits non-zero on any mismatch.
"""
import csv
import hashlib
import json
import sys
from math import comb, sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ok = True


def check(label, got, want, tol=0.0005):
    global ok
    good = abs(got - want) <= tol if isinstance(want, float) else got == want
    ok &= good
    print(f"  {'OK ' if good else 'BAD'} {label}: {got if not isinstance(got, float) else round(got, 3)} "
          f"(manuscript {want})")


# 1) file integrity
print("1) File integrity (SHA256SUMS)")
bad = 0
for line in open(ROOT / "SHA256SUMS"):
    h, p = line.rstrip("\n").split("  ", 1)
    if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != h:
        bad += 1
        print("  BAD", p)
print(f"  {'OK ' if not bad else 'BAD'} all files match" if not bad else f"  {bad} files differ")
ok &= not bad


def mcnemar(b, c):
    n, k = b + c, min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


def prf(rows, key):
    tp = sum(r[key] and r["gold"] for r in rows)
    fp = sum(r[key] and not r["gold"] for r in rows)
    fn = sum((not r[key]) and r["gold"] for r in rows)
    p, r_ = tp / (tp + fp), tp / (tp + fn)
    return p, r_, 2 * p * r_ / (p + r_), sum(x[key] == x["gold"] for x in rows) / len(rows)


B = lambda v: v == "True"
SB = ROOT / "runs/step_b"

# 2) Step C (Tables 5 and 6)
print("2) Step C, Tables 5 and 6 (engine v7.2.0 vs comparators, per-unit files)")
T5 = {"roberta-base": (.553, .985, .708, .794, 384, 392), "roberta-large": (.598, .974, .741, .827, 315, 394),
      "deberta-v2-xlarge": (.590, .994, .741, .823, 325, 396)}
T6 = {("roberta-base", "direct"): (.812, 180, 141), ("roberta-large", "direct"): (.845, 143, 138),
      ("deberta-v2-xlarge", "direct"): (.848, 144, 142), ("roberta-base", "partial"): (.777, 204, 251),
      ("roberta-large", "partial"): (.810, 172, 256), ("deberta-v2-xlarge", "partial"): (.800, 181, 254)}
for m, want in T5.items():
    rows = [dict(r, gold=B(r["gold"]), model=B(r["cuad_model"]), engine=B(r["engine"]))
            for r in csv.DictReader(open(SB / f"cuad_{m}/step_c/units_cuad.csv"))]
    check(f"CUAD units ({m})", len(rows), 2142)
    p, r_, f, a = prf(rows, "model")
    for lab, g, w in zip(["P", "R", "F1", "Acc"], [p, r_, f, a], want[:4]):
        check(f"{m} {lab}", g, w)
    oe = sum(x["engine"] == x["gold"] != x["model"] for x in rows)
    om = sum(x["model"] == x["gold"] != x["engine"] for x in rows)
    check(f"{m} McNemar only-engine / only-model", (oe, om), want[4:])
    for st in ["direct", "partial"]:
        s = [x for x in rows if x["strength"] == st]
        w = T6[(m, st)]
        check(f"{m} {st} accuracy", prf(s, "model")[3], w[0])
        check(f"{m} {st} McNemar", (sum(x["engine"] == x["gold"] != x["model"] for x in s),
                                     sum(x["model"] == x["gold"] != x["engine"] for x in s)), w[1:])
pe, re_, fe, ae = prf(rows, "engine")
for lab, g, w in zip(["P", "R", "F1", "Acc"], [pe, re_, fe, ae], [.663, .354, .462, .790]):
    check(f"engine CUAD {lab}", g, w)
cn = [dict(r, gold=B(r["gold"]), model=B(r["span_nli_bert"]), engine=B(r["engine"]))
      for r in csv.DictReader(open(SB / "contractnli_bert-base/paired_units_engine_vs_span_nli_bert.csv"))]
check("ContractNLI units", len(cn), 615)
for lab, g, w in zip(["P", "R", "F1", "Acc"], prf(cn, "model"), [.898, .816, .855, .902]):
    check(f"Span NLI BERT {lab}", g, w)
for lab, g, w in zip(["P", "R", "F1", "Acc"], prf(cn, "engine"), [.623, .304, .409, .689]):
    check(f"engine ContractNLI {lab}", g, w)
oe = sum(x["engine"] == x["gold"] != x["model"] for x in cn)
om = sum(x["model"] == x["gold"] != x["engine"] for x in cn)
check("ContractNLI McNemar", (oe, om), (30, 161))
print(f"  (exact McNemar p, ContractNLI: {mcnemar(oe, om):.2g})")

# 3) Injection attribution (Table 3)
print("3) Injection attribution, Table 3")
att = list(csv.DictReader(open(next((ROOT / "runs/phase5_control").glob("*/attribution.csv")))))
for rel, want, want_changed in [("v1.0.3-iccs", 49, 235), ("v7.2.0", 693, 748)]:
    rows = [r for r in att if r["release"] == rel]
    check(f"{rel} cases", len(rows), 4944)
    k = sum(r["injection_attributable"] == "True" for r in rows)
    check(f"{rel} injection-attributable", k, want)
    check(f"{rel} changed vs. original", sum(r["vs_original"] != "PASS" for r in rows), want_changed)
lo, hi = wilson(693, 4944)
check("v7.2.0 Wilson CI low (%)", round(100 * lo, 1), 13.1, 0.05)
check("v7.2.0 Wilson CI high (%)", round(100 * hi, 1), 15.0, 0.05)
key = lambda r: (r["doc_id"], r["payload"], r["position"])
a = {key(r): r["injection_attributable"] == "True" for r in att if r["release"] == "v1.0.3-iccs"}
b = {key(r): r["injection_attributable"] == "True" for r in att if r["release"] == "v7.2.0"}
check("paired: contained only at 25 rules / only at 189 rules",
      (sum(b[k] and not a[k] for k in a), sum(a[k] and not b[k] for k in a)), (682, 38))

print("\nALL CHECKS PASSED" if ok else "\nSOME CHECKS FAILED")
sys.exit(0 if ok else 1)
