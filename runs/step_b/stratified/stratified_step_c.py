"""Step C split by the frozen mapping strength (direct / partial), from the committed per-unit files. Exploratory."""
import csv, json
from math import comb
from pathlib import Path
F = Path(__file__).resolve().parents[3]
def mcn(b, c):
    n, k = b + c, min(b, c); return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)
def stats(s, k):
    tp = sum(r[k] and r["gold"] for r in s); fp = sum(r[k] and not r["gold"] for r in s); fn = sum((not r[k]) and r["gold"] for r in s)
    P = tp / (tp + fp) if tp + fp else None; R = tp / (tp + fn)
    return {"precision": P, "recall": R, "f1": 2 * P * R / (P + R) if P and R else 0.0, "accuracy": sum(r[k] == r["gold"] for r in s) / len(s)}
B = lambda v: v == "True"
out = {}
for m in ["roberta-base", "roberta-large", "deberta-v2-xlarge"]:
    rows = [dict(r, gold=B(r["gold"]), model=B(r["cuad_model"]), engine=B(r["engine"]))
            for r in csv.DictReader(open(F / f"runs/step_b/cuad_{m}/step_c/units_cuad.csv"))]
    for st in ["all", "direct", "partial"]:
        s = rows if st == "all" else [r for r in rows if r["strength"] == st]
        oe = sum(r["engine"] == r["gold"] != r["model"] for r in s); om = sum(r["model"] == r["gold"] != r["engine"] for r in s)
        out[f"cuad/{m}/{st}"] = {"units": len(s), "engine": stats(s, "engine"), "model": stats(s, "model"),
                                 "only_engine_correct": oe, "only_model_correct": om, "mcnemar_p": mcn(oe, om)}
strength = {h: v["strength"] for h, v in json.load(open(F / "comparators/label_mapping.json"))["contractnli"].items()}
rows = [dict(r, gold=B(r["gold"]), model=B(r["span_nli_bert"]), engine=B(r["engine"]))
        for r in csv.DictReader(open(F / "runs/step_b/contractnli_bert-base/paired_units_engine_vs_span_nli_bert.csv"))]
for st in ["all", "direct", "partial"]:
    s = rows if st == "all" else [r for r in rows if strength[r["hypothesis"]] == st]
    oe = sum(r["engine"] == r["gold"] != r["model"] for r in s); om = sum(r["model"] == r["gold"] != r["engine"] for r in s)
    out[f"contractnli/span_nli_bert/{st}"] = {"units": len(s), "engine": stats(s, "engine"), "model": stats(s, "model"),
                                              "only_engine_correct": oe, "only_model_correct": om, "mcnemar_p": mcn(oe, om)}
(Path(__file__).parent / "stratified_step_c.json").write_text(json.dumps(out, indent=1) + "\n")
for k, v in out.items():
    print(f"{k:40s} n={v['units']:5d} engine acc {v['engine']['accuracy']:.3f} model acc {v['model']['accuracy']:.3f} "
          f"{v['only_engine_correct']}/{v['only_model_correct']} p={v['mcnemar_p']:.3g}")
