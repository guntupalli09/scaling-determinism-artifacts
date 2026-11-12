"""
Phase 3/6: paired evaluation against expert gold labels (CUAD test split, ContractNLI test split).

Unit of comparison = (contract, category). Every system's prediction for every unit is
written to runs/analysis/<label>/units_*.csv so McNemar pairing and CIs are exact.
Category <-> rule correspondence: comparators/label_mapping.json (DRAFT, pending review).

    python -m experiments.followup.evaluate_paired v7.2.0 [--cuad-model-dir runs/comparators/cuad_roberta-base]
"""
import argparse
import csv
import json
from pathlib import Path

from experiments.followup.stats import bootstrap_f1_ci, mcnemar_exact, prf

FOLLOWUP = Path(__file__).parent
EXTERNAL = FOLLOWUP / "external"
RUNS = FOLLOWUP / "runs"


def _manifest():
    return {r["doc_id"]: r for r in csv.DictReader(open(FOLLOWUP / "corpus" / "manifest.csv", encoding="utf-8"))}


def _engine(label):
    return {json.loads(l)["doc_id"]: set(json.loads(l)["rule_ids_fired"])
            for l in open(RUNS / label / "results.jsonl", encoding="utf-8")}


def _release_rules(label):
    m = json.load(open(FOLLOWUP / "releases" / "manifest_v2.json"))
    return set(next(r for r in m if r["label"] == label)["rule_ids"])


def cuad_gold():
    gold = {}
    for d in json.load(open(EXTERNAL / "cuad_split" / "test.json", encoding="utf-8"))["data"]:
        for qa in d["paragraphs"][0]["qas"]:
            cat = qa["id"].split("__", 1)[1]
            gold[(d["title"], cat)] = len(qa["answers"]) > 0
    return gold


def cuad_model_preds(model_dir):
    """Present iff the best non-empty answer outscores the null answer (SQuAD-v2 decision rule)."""
    preds = {}
    path = Path(model_dir) / "nbest_partial.jsonl"
    if not path.exists():
        return None
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        title, cat = r["id"].split("__", 1)
        nb = r["nbest"]
        null = next((x["probability"] for x in nb if x["text"] == ""), 0.0)
        best = max((x["probability"] for x in nb if x["text"]), default=0.0)
        preds[(title, cat)] = best > null
    return preds


def lexnlp_preds(lexnlp_dir=None):
    path = Path(lexnlp_dir) / "predictions.jsonl" if lexnlp_dir else Path("/nonexistent")
    if not path.exists():
        return None
    out = {}
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        for cat, v in r["predictions"].items():
            out[(r["doc_id"], cat)] = v["present"]
    return out


def _metrics(units, key):
    tp = sum(u["gold"] and u[key] for u in units)
    fp = sum((not u["gold"]) and u[key] for u in units)
    fn = sum(u["gold"] and not u[key] for u in units)
    m = prf(tp, fp, fn)
    m["f1_ci"] = bootstrap_f1_ci([(u["gold"], u[key]) for u in units])
    m["accuracy"] = sum(u["gold"] == u[key] for u in units) / len(units) if units else None
    m["units"] = len(units)
    return m


def evaluate(label, cuad_model_dir=None, lexnlp_dir=None, out_dir=None):
    # Default is the release's analysis directory; comparator runs pass their own out_dir so
    # frozen engine-only analyses are never overwritten.
    out_dir = Path(out_dir) if out_dir else RUNS / "analysis" / label
    out_dir.mkdir(parents=True, exist_ok=True)
    mapping = json.load(open(FOLLOWUP / "comparators" / "label_mapping.json"))
    manifest, engine, rules = _manifest(), _engine(label), _release_rules(label)
    report = {"label": label, "mapping_status": mapping["_status"], "cuad": {}, "contractnli": {}}

    # ---- CUAD test split --------------------------------------------------------------
    gold = cuad_gold()
    model = cuad_model_preds(cuad_model_dir) if cuad_model_dir else None
    lex = lexnlp_preds(lexnlp_dir)
    units = []
    for doc_id, r in manifest.items():
        if r["slice"] != "cuad_test" or doc_id not in engine:
            continue
        for cat, cfg in mapping["cuad"].items():
            if cat.startswith("_"):
                continue
            # Fixed unit set across releases: a release with no mapped rule predicts "absent",
            # which is exactly what the coverage curve has to measure.
            mapped = [x for x in cfg["rules"] if x in rules]
            if (r["source_ref"], cat) not in gold:
                continue
            u = {"doc_id": doc_id, "category": cat, "strength": cfg["strength"], "in_release_scope": bool(mapped),
                 "gold": gold[(r["source_ref"], cat)], "engine": bool(engine[doc_id] & set(mapped))}
            if model is not None:
                u["cuad_model"] = model.get((r["source_ref"], cat))
            if lex is not None and cat in mapping["lexnlp"]:
                u["lexnlp"] = lex.get((doc_id, cat))
            units.append(u)
    _write_units(out_dir / "units_cuad.csv", units)
    report["cuad"]["engine_overall"] = _metrics(units, "engine")
    report["cuad"]["engine_direct_only"] = _metrics([u for u in units if u["strength"] == "direct"], "engine")
    report["cuad"]["engine_release_scope"] = _metrics([u for u in units if u["in_release_scope"]], "engine")
    report["cuad"]["engine_by_category"] = {
        c: _metrics([u for u in units if u["category"] == c], "engine") for c in sorted({u["category"] for u in units})}
    for comp in ("cuad_model", "lexnlp"):
        common = [u for u in units if u.get(comp) is not None]
        if not common:
            report["cuad"][comp] = "not available"
            continue
        report["cuad"][comp] = {
            "on_common_units": _metrics(common, comp),
            "engine_on_same_units": _metrics(common, "engine"),
            "mcnemar_engine_vs_" + comp: mcnemar_exact([u["engine"] == u["gold"] for u in common],
                                                       [u[comp] == u["gold"] for u in common]),
        }

    # ---- ContractNLI test split (engine only; NLI comparator needs a GPU) -----------------
    data = json.load(open(EXTERNAL / "contract-nli" / "test.json", encoding="utf-8"))
    by_file = {d["file_name"]: d for d in data["documents"]}
    nli_units = []
    for doc_id, r in manifest.items():
        if r["slice"] != "nda" or doc_id not in engine:
            continue
        doc = by_file[r["source_ref"]]
        ann = doc["annotation_sets"][0]["annotations"]
        for hyp, cfg in mapping["contractnli"].items():
            mapped = [x for x in cfg["rules"] if x in rules]
            nli_units.append({"doc_id": doc_id, "category": hyp, "strength": cfg["strength"],
                              "in_release_scope": bool(mapped),
                              "gold": ann[hyp]["choice"] == cfg["choice"],
                              "engine": bool(engine[doc_id] & set(mapped))})
    _write_units(out_dir / "units_contractnli.csv", nli_units)
    report["contractnli"]["engine_overall"] = _metrics(nli_units, "engine") if nli_units else "no units"
    scoped = [u for u in nli_units if u["in_release_scope"]]
    report["contractnli"]["engine_release_scope"] = _metrics(scoped, "engine") if scoped else "no units"
    report["contractnli"]["engine_by_hypothesis"] = {
        c: _metrics([u for u in nli_units if u["category"] == c], "engine") for c in sorted({u["category"] for u in nli_units})}
    report["contractnli"]["comparator"] = "pending: contract-nli-bert has no released weights; training requires a GPU"
    (out_dir / "paired_report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def _write_units(path, units):
    if not units:
        path.write_text("")
        return
    keys = sorted({k for u in units for k in u}, key=lambda k: ["doc_id", "category", "strength", "in_release_scope", "gold"].index(k)
                  if k in ("doc_id", "category", "strength", "in_release_scope", "gold") else 10)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(units)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("label")
    p.add_argument("--cuad-model-dir")
    p.add_argument("--lexnlp-dir")
    p.add_argument("--out-dir")
    a = p.parse_args()
    rep = evaluate(a.label, a.cuad_model_dir, a.lexnlp_dir, a.out_dir)
    e = rep["cuad"]["engine_overall"]
    print(f"CUAD units={e['units']} P={e['precision']} R={e['recall']} F1={e['f1']}")
    n = rep["contractnli"]["engine_overall"]
    if isinstance(n, dict):
        print(f"ContractNLI units={n['units']} P={n['precision']} R={n['recall']} F1={n['f1']}")
