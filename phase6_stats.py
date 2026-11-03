"""
Phase 6 — preliminary statistical package (experiment P6-STATS-1).

Rules applied:
  * McNemar (exact, two-sided) ONLY on genuinely paired observations: the same
    (contract, category) units scored by two systems/releases. Holm correction across the
    family of release-to-release comparisons.
  * Precision / recall: Wilson 95% intervals. F1: document-level cluster bootstrap 95% interval
    (units within one contract are not independent).
  * Determinism: descriptive (counts) with an exact one-sided 95% upper bound on the per-document
    variance rate when 0 events are observed (1 - 0.05**(1/n)); no hypothesis test.
  * Every row names the raw paired-unit file it was computed from.
  * Every mapping-dependent row carries PRELIMINARY_MAPPING_PENDING_REVIEW.

    python -m experiments.followup.phase6_stats  ->  runs/phase6/<timestamp>/
"""
import csv
import json
import random
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from experiments.followup.stats import mcnemar_exact, prf

F = Path(__file__).parent
A = F / "runs" / "analysis"
TAG = "PRELIMINARY_MAPPING_PENDING_REVIEW"
CHECKPOINTS = ["v1.0.3-iccs", "v2.0.0", "v2.1.0", "v3.0.0", "v4.0.0", "v5.0.0", "v6.0.0", "v7.0.0", "v7.1.0", "v7.2.0"]


def units(label, which):
    p = A / label / f"units_{which}.csv"
    return p, [dict(u, gold=u["gold"] == "True", engine=u["engine"] == "True",
                    in_release_scope=u.get("in_release_scope", "True") == "True") for u in csv.DictReader(open(p))]


def cluster_bootstrap_f1(us, key="engine", iters=2000, seed=20261017):
    docs = sorted({u["doc_id"] for u in us})
    by = {d: [u for u in us if u["doc_id"] == d] for d in docs}
    rng = random.Random(seed)
    vals = []
    for _ in range(iters):
        s = [u for _ in docs for u in by[docs[rng.randrange(len(docs))]]]
        tp = sum(u["gold"] and u[key] for u in s)
        fp = sum((not u["gold"]) and u[key] for u in s)
        fn = sum(u["gold"] and not u[key] for u in s)
        f = prf(tp, fp, fn)["f1"]
        if f is not None:
            vals.append(f)
    vals.sort()
    return (vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]) if vals else (None, None)


def perf_row(label, which, subset, us, src, key="engine", tag=TAG):
    tp = sum(u["gold"] and u[key] for u in us)
    fp = sum((not u["gold"]) and u[key] for u in us)
    fn = sum(u["gold"] and not u[key] for u in us)
    m = prf(tp, fp, fn)
    lo, hi = cluster_bootstrap_f1(us, key)
    return {"system": label, "dataset": which, "subset": subset, "units": len(us), "docs": len({u["doc_id"] for u in us}),
            "tp": tp, "fp": fp, "fn": fn, "precision": m["precision"], "precision_ci": [m["precision_ci"]["lo"], m["precision_ci"]["hi"]],
            "recall": m["recall"], "recall_ci": [m["recall_ci"]["lo"], m["recall_ci"]["hi"]], "f1": m["f1"], "f1_ci_cluster_bootstrap": [lo, hi],
            "status": tag, "source": str(src.relative_to(F))}


def holm(rows, pkey="p_value"):
    order = sorted(range(len(rows)), key=lambda i: rows[i][pkey])
    m, running = len(rows), 0.0
    for rank, i in enumerate(order):
        adj = min(1.0, (m - rank) * rows[i][pkey])
        running = max(running, adj)
        rows[i]["p_holm"] = running
    return rows


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = F / "runs" / "phase6" / stamp
    out.mkdir(parents=True, exist_ok=False)
    perf, paired, transitions = [], [], []

    # 1. performance per release (fixed denominator + release scope), CUAD and ContractNLI
    for L in CHECKPOINTS + ["v7.2.0+20294216"]:
        for which in ("cuad", "contractnli"):
            src, us = units(L, which)
            perf.append(perf_row(L, which, "fixed_denominator", us, src))
            scoped = [u for u in us if u["in_release_scope"]]
            if scoped:
                perf.append(perf_row(L, which, "release_scope", scoped, src))
            if which == "cuad":
                perf.append(perf_row(L, which, "direct_mappings_only", [u for u in us if u["strength"] == "direct"], src))

    # 2. paired release comparisons (same units): consecutive + ICCS vs v7.2.0
    pairs = list(zip(CHECKPOINTS, CHECKPOINTS[1:])) + [("v1.0.3-iccs", "v7.2.0"), ("v7.2.0", "v7.2.0+20294216")]
    recall_rows = []
    for which in ("cuad", "contractnli"):
        fam = []
        for a, b in pairs:
            sa, ua = units(a, which)
            sb, ub = units(b, which)
            ka = {(u["doc_id"], u["category"]): u for u in ua}
            kb = {(u["doc_id"], u["category"]): u for u in ub}
            keys = sorted(set(ka) & set(kb))
            assert len(keys) == len(ka) == len(kb), "unit sets must be identical for a paired test"
            ca = [ka[k]["engine"] == ka[k]["gold"] for k in keys]
            cb = [kb[k]["engine"] == kb[k]["gold"] for k in keys]
            t = mcnemar_exact(ca, cb)
            row = {"dataset": which, "a": a, "b": b, **t, "status": TAG,
                   "source": [str(sa.relative_to(F)), str(sb.relative_to(F))]}
            fam.append(row)
            # recall-specific paired test: gold-positive units only (TP gained vs TP lost)
            pos = [k for k in keys if ka[k]["gold"]]
            tr_ = mcnemar_exact([ka[k]["engine"] for k in pos], [kb[k]["engine"] for k in pos])
            recall_rows.append({"dataset": which, "a": a, "b": b, "units": "gold-positive only", **tr_,
                                "test": "exact McNemar on detection of gold-positive units (recall change)",
                                "status": TAG, "source": row["source"]})
            # transitions per category: TP/FP gained and lost
            cats = sorted({k[1] for k in keys})
            for c in cats:
                ks = [k for k in keys if k[1] == c]
                tr = {"dataset": which, "from": a, "to": b, "category": c,
                      "tp_gained": sum(kb[k]["gold"] and kb[k]["engine"] and not ka[k]["engine"] for k in ks),
                      "tp_lost": sum(ka[k]["gold"] and ka[k]["engine"] and not kb[k]["engine"] for k in ks),
                      "fp_gained": sum((not kb[k]["gold"]) and kb[k]["engine"] and not ka[k]["engine"] for k in ks),
                      "fp_removed": sum((not ka[k]["gold"]) and ka[k]["engine"] and not kb[k]["engine"] for k in ks)}
                if any(v for k2, v in tr.items() if k2.startswith(("tp_", "fp_"))):
                    transitions.append(tr)
        consecutive = [r for r in fam if (r["a"], r["b"]) in list(zip(CHECKPOINTS, CHECKPOINTS[1:]))]
        holm(consecutive)
        holm([r for r in recall_rows if r["dataset"] == which and (r["a"], r["b"]) in list(zip(CHECKPOINTS, CHECKPOINTS[1:]))])
        for r in fam:
            r.setdefault("p_holm", None)
            r["test"] = "exact McNemar on unit correctness (same units)"
        paired += fam
    for r in recall_rows:
        r.setdefault("p_holm", None)
    paired += recall_rows

    # 3. engine vs comparators on common units (only comparators that exist)
    comps = []
    lex_dirs = sorted((F / "runs/comparators/lexnlp").glob("*/predictions.jsonl")) if (F / "runs/comparators/lexnlp").exists() else []
    if lex_dirs:
        lex = {}
        for line in open(lex_dirs[-1]):
            r = json.loads(line)
            for cat, v in r["predictions"].items():
                lex[(r["doc_id"], cat)] = v["present"]
        src, us = units("v7.2.0", "cuad")
        common = [dict(u, lexnlp=lex[(u["doc_id"], u["category"])]) for u in us if (u["doc_id"], u["category"]) in lex]
        t = mcnemar_exact([u["engine"] == u["gold"] for u in common], [u["lexnlp"] == u["gold"] for u in common])
        lex_tag = "UNVALIDATED_NO_PUBLISHED_REFERENCE (LexNLP has no published benchmark; sanity-validated only) + " + TAG
        comps.append({"comparison": "v7.2.0 engine vs LexNLP 2.3.0", "dataset": "cuad_test", "units": len(common),
                      "categories": sorted({u["category"] for u in common}), **t, "status": lex_tag,
                      "lexnlp_source": str(lex_dirs[-1].relative_to(F)), "engine_source": str(src.relative_to(F))})
        perf.append(perf_row("LexNLP-2.3.0", "cuad", "lexnlp_categories", common, lex_dirs[-1], key="lexnlp", tag=lex_tag))
        perf.append(perf_row("v7.2.0", "cuad", "lexnlp_categories", common, src, key="engine"))
        with open(out / "paired_units_engine_vs_lexnlp.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["doc_id", "category", "gold", "engine", "lexnlp"], extrasaction="ignore")
            w.writeheader()
            w.writerows(common)
    cuad_step_a = F / "runs/comparators/cuad_roberta-base/step_a_result.json"
    comps.append({"comparison": "v7.2.0 engine vs CUAD RoBERTa-base",
                  "status": ("see step_a_result.json" if cuad_step_a.exists() else
                             "NOT RUN: comparator Step A (reproduction on CUAD test split) not complete")})
    comps.append({"comparison": "v7.2.0 engine vs ContractNLI Span NLI BERT", "status": "BLOCKED_GPU (no released weights)"})

    # 4. determinism (descriptive)
    det = []
    for L in CHECKPOINTS + ["v1.0.3", "v7.2.0+20294216"]:
        s = json.load(open(F / "runs" / L / "summary.json"))["overall"]
        n = s["docs"]
        det.append({"release": L, "docs": n, "runs_per_doc": s["runs_per_doc"], "executions": n * s["runs_per_doc"],
                    "docs_with_output_variance": s["docs_with_output_variance"],
                    "upper95_per_doc_variance_rate": (1 - 0.05 ** (1 / n)) if s["docs_with_output_variance"] == 0 else None,
                    "scope": "within-process repetitions (fresh engine per run)", "source": f"runs/{L}/results.jsonl"})
    xp = sorted((F / "runs/determinism_crossprocess").glob("*/summary.json"))
    if xp:
        for L, v in json.load(open(xp[-1])).items():
            n = v["docs"]
            det.append({"release": L, "docs": n, "runs_per_doc": v["seeds"], "executions": n * v["seeds"],
                        "docs_with_output_variance": v["docs_output_variance_across_processes"],
                        "docs_with_finding_variance": v["docs_finding_variance_across_processes"],
                        "upper95_per_doc_variance_rate": (1 - 0.05 ** (1 / n)) if v["docs_output_variance_across_processes"] == 0 else None,
                        "scope": "separate processes, PYTHONHASHSEED varied", "source": str(xp[-1].relative_to(F))})

    meta = {"experiment_id": "P6-STATS-1", "timestamp": stamp,
            "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=F).stdout.strip(),
            "corpus_manifest_sha256": (F / "corpus/MANIFEST.sha256").read_text().split()[0],
            "bootstrap": {"type": "document-level cluster", "iterations": 2000, "seed": 20261017},
            "mapping_status": json.load(open(F / "comparators/label_mapping.json"))["_status"]}
    for name, obj in (("meta", meta), ("performance", perf), ("paired_tests", paired), ("comparators", comps),
                      ("determinism", det), ("transitions", transitions)):
        (out / f"{name}.json").write_text(json.dumps(obj, indent=1, default=str) + "\n")
    with open(out / "transitions.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(transitions[0].keys()))
        w.writeheader()
        w.writerows(transitions)
    print(out)


if __name__ == "__main__":
    main()
