"""
Freeze the computational results (FINAL-MANIFEST-1).

Every reported number is RE-COMPUTED here from its raw output file and compared with the value
stated in COMPUTATIONAL_RESULTS.md / MANUSCRIPT_DRAFT_1.md. Each entry records experiment ID,
source file(s) with SHA-256, corpus manifest hash, engine commit and ruleset hash, and status.
A mismatch is reported, never silently corrected. Writes to runs/final_manifest/<stamp>/ and
FINAL_RESULTS_MANIFEST.md (never overwrites a previous freeze directory).

    python -m experiments.followup.freeze_results
"""
import csv
import hashlib
import json
import math
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

F = Path(__file__).parent
CORPUS = (F / "corpus/MANIFEST.sha256").read_text().split()[0]
REL = {r["label"]: r for r in json.load(open(F / "releases/manifest_v2.json"))}
P6 = F / "runs/phase6/20261017T010324Z"
P5 = F / "runs/phase5/20261017T013302Z"
P5C = F / "runs/phase5_control/20261017T021750Z"
P5P = F / "runs/phase5_proposal/20261017T021711Z"
P2 = F / "runs/phase2/20261017T021857Z"
CF = F / "runs/phase4_counterfactual/20261017T021716Z"
XP = F / "runs/determinism_crossprocess/20261017T002540Z"
VAL = F / "runs/validation/20261017T021819Z"
PM = "PRELIMINARY_MAPPING_PENDING_REVIEW"
ENTRIES, FILES = [], {}


def sha(p: Path):
    p = Path(p)
    if p.is_dir():
        return None
    if p not in FILES:
        FILES[p] = hashlib.sha256(p.read_bytes()).hexdigest()
    return FILES[p]


def rel(label):
    r = REL[label]
    return {"release": label, "engine_commit": r["commit"][:8], "ruleset_sha256": r["ruleset_sha256"][:16]}


def add(rid, claim, stated, computed, sources, exp, releases, status, tol=1e-3):
    ok = (abs(stated - computed) <= tol) if isinstance(stated, (int, float)) and isinstance(computed, (int, float)) \
        else stated == computed
    ENTRIES.append({"id": rid, "claim": claim, "stated": stated, "recomputed": computed, "match": ok,
                    "experiment": exp, "sources": [{"path": str(Path(s).relative_to(F)), "sha256": sha(s)} for s in sources],
                    "corpus_sha256": CORPUS[:16], "releases": [rel(x) for x in releases], "status": status})


def jl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8")]


def perf(system, ds, subset):
    return next(r for r in json.load(open(P6 / "performance.json"))
                if r["system"] == system and r["dataset"] == ds and r["subset"] == subset)


def paired(ds, a, b, recall=False):
    return next(r for r in json.load(open(P6 / "paired_tests.json")) if r["dataset"] == ds and r["a"] == a and r["b"] == b
                and (r.get("units") == "gold-positive only") == recall)


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = F / "runs/final_manifest" / stamp
    out.mkdir(parents=True, exist_ok=False)
    ck = ["v1.0.3-iccs", "v1.0.3", "v2.0.0", "v2.1.0", "v3.0.0", "v4.0.0", "v5.0.0", "v6.0.0", "v7.0.0", "v7.1.0",
          "v7.2.0", "v7.2.0+20294216"]

    # --- determinism
    srcs = [F / "runs" / L / "results.jsonl" for L in ck]
    execs = sum(r["runs"] for p in srcs for r in jl(p))
    var = sum(r["distinct_output_hashes"] > 1 or r["distinct_finding_hashes"] > 1 for p in srcs for r in jl(p))
    add("R01", "Within-process executions across 12 engine states", 26574, execs, srcs, "P1/P4 runs", ck, "SUPPORTED")
    add("R02", "Documents with any output/finding variance (within-process, all states)", 0, var, srcs, "P1/P4 runs", ck, "SUPPORTED")
    b = jl(F / "runs/v7.2.0/results.jsonl")
    add("R03", "v7.2.0 baseline executions (618 docs x 10)", 6180, sum(r["runs"] for r in b), [F / "runs/v7.2.0/results.jsonl"],
        "P1 baseline", ["v7.2.0"], "SUPPORTED")
    add("R04", "Exact one-sided 95% upper bound, per-document variance rate (0/618)", 0.0048, 1 - 0.05 ** (1 / 618),
        [F / "runs/v7.2.0/results.jsonl"], "P1 baseline", ["v7.2.0"], "SUPPORTED", tol=5e-5)
    xs = json.load(open(XP / "summary.json"))
    add("R05", "Cross-process executions (15 states x 60 docs x 6 seeds)", 5400, sum(v["docs"] * v["seeds"] for v in xs.values()),
        [XP / "summary.json", XP / "raw.json"], "DET-XPROC-1", list(xs), "SUPPORTED")
    add("R06", "Cross-process documents with output variance", 0, sum(v["docs_output_variance_across_processes"] for v in xs.values()),
        [XP / "summary.json"], "DET-XPROC-1", list(xs), "SUPPORTED")

    # --- baseline performance (mapping-dependent)
    for rid, ds, sub, stated in (("R07", "cuad", "fixed_denominator", (0.663, 0.354, 0.462)),
                                 ("R08", "cuad", "direct_mappings_only", (0.860, 0.451, 0.592)),
                                 ("R09", "contractnli", "fixed_denominator", (0.623, 0.304, 0.409))):
        r = perf("v7.2.0", ds, sub)
        add(rid, f"v7.2.0 {ds} {sub} precision/recall/F1", list(stated),
            [round(r["precision"], 3), round(r["recall"], 3), round(r["f1"], 3)],
            [P6 / "performance.json", F / "runs/analysis/v7.2.0" / f"units_{ds}.csv"], "P6-STATS-1", ["v7.2.0"], PM)
    v = json.load(open(VAL / "day1_validation.json"))
    agree = next(c for c in v["checks"] if c["check"] == "scoring.gold_test_json_vs_master_clauses_agree")["detail"]
    add("R10", "CUAD gold labels agree between test.json and master_clauses.csv (units)", 4284, agree["agree"],
        [VAL / "day1_validation.json"], "VAL-DAY1", [], "SUPPORTED")
    add("R11", "Day 1 validation checks passing", 19, sum(c["status"] == "PASS" for c in v["checks"]),
        [VAL / "day1_validation.json"], "VAL-DAY1", [], "SUPPORTED")

    # --- coverage trajectory
    for L, stated in (("v1.0.3-iccs", (0.712, 0.213)), ("v7.2.0", (0.663, 0.354))):
        r = perf(L, "cuad", "fixed_denominator")
        add(f"R12-{L}", f"{L} CUAD fixed-denominator precision/recall", list(stated), [round(r["precision"], 3), round(r["recall"], 3)],
            [P6 / "performance.json", F / "runs/analysis" / L / "units_cuad.csv"], "P6-STATS-1", [L], PM)
    t = paired("cuad", "v1.0.3-iccs", "v7.2.0", recall=True)
    add("R13", "ICCS->v7.2.0 CUAD gold-positive units gained/lost", [81, 4], [t["only_b_correct"], t["only_a_correct"]],
        [P6 / "paired_tests.json"], "P6-STATS-1", ["v1.0.3-iccs", "v7.2.0"], PM)
    add("R13p", "ICCS->v7.2.0 recall McNemar exact p < 1e-18", True, t["p_value"] < 1e-18, [P6 / "paired_tests.json"],
        "P6-STATS-1", ["v1.0.3-iccs", "v7.2.0"], PM)

    # --- hidden regression
    def nda3(L):
        u = [x for x in csv.DictReader(open(F / "runs/analysis" / L / "units_contractnli.csv")) if x["category"] == "nda-3"]
        return sum(x["gold"] == "True" and x["engine"] == "True" for x in u)
    add("R14", "nda-3 true positives v4.0.0 -> v5.0.0 -> v7.2.0", [38, 19, 19], [nda3("v4.0.0"), nda3("v5.0.0"), nda3("v7.2.0")],
        [F / f"runs/analysis/{L}/units_contractnli.csv" for L in ("v4.0.0", "v5.0.0", "v7.2.0")], "P4", ["v4.0.0", "v5.0.0", "v7.2.0"], PM)
    t = paired("contractnli", "v5.0.0", "v6.0.0", recall=True)
    add("R15", "ContractNLI v5->v6 gold-positive units gained (nda-18 driven)", 23, t["only_b_correct"],
        [P6 / "paired_tests.json"], "P6-STATS-1", ["v5.0.0", "v6.0.0"], PM)
    cf = json.load(open(CF / "counterfactuals.json"))["results"][0]
    add("R16", "Counterfactual: v5 with L_BROADDEF_01 reverted / v4 with new pattern (nda-3 TP)", [32, 22],
        [cf["to_with_rule_reverted_tp"], cf["from_with_new_rule_tp"]], [CF / "counterfactuals.json"], "P4-CF-1", ["v4.0.0", "v5.0.0"], PM)
    bis = json.load(open(F / "runs/phase4_counterfactual/bisect_v2.1_v3.0_20261017T004907Z.json"))["rows"]
    first_drop = next(r["commit"] for r in bis if r["nda3_tp"] < bis[0]["nda3_tp"])
    add("R17", "Bisection: first commit with nda-3 drop (47->38)", "13532073", first_drop,
        [F / "runs/phase4_counterfactual/bisect_v2.1_v3.0_20261017T004907Z.json"], "P4-BISECT-1", ["v2.1.0", "v3.0.0"], PM)

    # --- version drift
    s72 = [r for r in REL.values() if r["version"] == "7.2.0"]
    add("R18", "Distinct rule-definition states labelled 7.2.0", 3, len({r["ruleset_sha256"] for r in s72}),
        [F / "releases/manifest_v2.json"], "VAL-DAY1/releases", [r["label"] for r in s72], "SUPPORTED")
    add("R19", "Distinct engine-code states labelled 7.2.0", 5, len({r["rules_engine_py_sha256"] for r in s72}),
        [F / "releases/manifest_v2.json"], "VAL-DAY1/releases", [r["label"] for r in s72], "SUPPORTED")
    add("R20", "ICCS commit rule count", 25, REL["v1.0.3-iccs"]["rule_count"], [F / "releases/manifest_v2.json"],
        "VAL-DAY1/releases", ["v1.0.3-iccs"], "SUPPORTED")

    # --- scaling
    sc = json.load(open(F / "runs/analysis/scaling.json"))
    add("R21", "Rule-count scaling exponent", 1.02, round(sc["rule_count_scaling"]["fit"]["exponent"], 2),
        [F / "runs/analysis/scaling.json"], "P4 scaling", ck[:1] + ck[2:11], "SUPPORTED (shape; shared-CPU timings)")
    ex = [v["exponent"] for v in sc["corpus_size_scaling_by_release"].values()]
    add("R22", "Document-length scaling exponent range", [0.96, 1.03], [round(min(ex), 2), round(max(ex), 2)],
        [F / "runs/analysis/scaling.json"], "P4 scaling", ck[:1] + ck[2:11], "SUPPORTED (shape; shared-CPU timings)")

    # --- Phase 5 inference
    meta = json.load(open(P5C / "meta.json"))["by_release"]
    add("R23", "S1 injection-attributable cases v7.2.0 / v1.0.3-iccs", [693, 49],
        [meta["v7.2.0"]["injection_attributable"], meta["v1.0.3-iccs"]["injection_attributable"]],
        [P5C / "attribution.csv", P5C / "meta.json", P5 / "cases_full.jsonl"], "P5-SEC-INFERENCE-1 + P5-SEC-CONTROL-1",
        ["v7.2.0", "v1.0.3-iccs"], "SUPPORTED (reconstructed suite)")
    st = json.load(open(P5C / "stats.json"))
    add("R24", "v7.2.0 attributable cases with a finding removed", 420, st["v7.2.0"]["attributable_with_removal"]["k"],
        [P5C / "stats.json", P5C / "attribution.csv"], "P5-SEC-CONTROL-1", ["v7.2.0"], "SUPPORTED (reconstructed suite)")
    add("R25", "Paired containment ICCS vs v7.2.0 discordant cells (ICCS-only / v7.2.0-only contained)", [682, 38],
        [st["paired_iccs_vs_v720_contained"]["only_a_correct"], st["paired_iccs_vs_v720_contained"]["only_b_correct"]],
        [P5C / "stats.json"], "P5-SEC-CONTROL-1", ["v1.0.3-iccs", "v7.2.0"], "SUPPORTED (reconstructed suite)")
    rows = jl(P5 / "cases_full.jsonl")
    s3f = sorted(r["case_id"] for r in rows if r["suite"] == "S3" and r["outcome"] == "FAIL")
    add("R26", "S3 explanation-layer FAIL cases (both releases)", 4, len(s3f), [P5 / "cases_full.jsonl"],
        "P5-SEC-INFERENCE-1", ["v7.2.0", "v1.0.3-iccs"], "SUPPORTED (stub client)")
    add("R26b", "Total inference-suite cases", 11346, len(rows), [P5 / "cases_full.jsonl"], "P5-SEC-INFERENCE-1",
        ["v7.2.0", "v1.0.3-iccs"], "SUPPORTED")

    # --- proposal path, Phase 2
    pp = json.load(open(P5P / "cases_full.json"))
    c = Counter(r["outcome"] for r in pp)
    add("R27", "Proposal-path cases PASS/FAIL/BLOCKED_API", [35, 2, 1], [c["PASS"], c["FAIL"], c["BLOCKED_API"]],
        [P5P / "cases_full.json"], "P5-SEC-PROPOSAL-1", ["v7.2.0"], "SUPPORTED")
    r2 = json.load(open(P2 / "result.json"))
    add("R28", "Phase 2 pipeline test: targeted fixed / regressions / base findings lost",
        [2, 0, 0], [len(r2["before_after_failure_cases"]["fixed"]), len(r2["regression_iccs_assertions"]["regressions"]),
                    len(r2["corpus_additivity"]["docs_with_any_base_finding_lost"])],
        [P2 / "result.json"], "P2-ADAPT-PIPELINE-1", ["v7.2.0"], "SUPPORTED (mechanism only; fixtures + TEST reviewers)")
    add("R29", "Phase 2 failure cases total / LLM generation blocked", [115, 115],
        [r2["failure_cases"]["total"], r2["llm_generation"]["cases_blocked"]], [P2 / "result.json", P2 / "llm_generation_status.json"],
        "P2-ADAPT-PIPELINE-1", ["v7.2.0"], "SUPPORTED / BLOCKED_API")

    # --- LexNLP
    cmp = json.load(open(P6 / "comparators.json"))[0]
    add("R30", "Engine vs LexNLP McNemar discordant (engine-only / LexNLP-only correct)", [55, 57],
        [cmp["only_a_correct"], cmp["only_b_correct"]], [P6 / "comparators.json", P6 / "paired_units_engine_vs_lexnlp.csv"],
        "P6-STATS-1", ["v7.2.0"], "UNVALIDATED comparator + " + PM)

    # --- CUAD Step A
    sa = F / "runs/comparators/cuad_roberta-base/step_a_result.json"
    status = json.load(open(sa))["status"] if sa.exists() else "INCOMPLETE_NOT_SCORED"
    ENTRIES.append({"id": "R31", "claim": "CUAD RoBERTa-base Step A", "stated": "not reported", "recomputed": status,
                    "match": True, "experiment": "P3-CUAD-STEPA", "sources": [], "corpus_sha256": None, "releases": [],
                    "status": status})

    figures = [
        {"id": "FIG1", "file": "runs/analysis/figures/day3/fig1_cuad_coverage_ci.png", "data": [str((P6 / "performance.json").relative_to(F))],
         "script": "plot_figures_day3.py", "status": PM},
        {"id": "FIG2", "file": "runs/analysis/figures/day3/fig2_runtime_scaling.png", "data": ["runs/analysis/scaling.json", "runs/v7.2.0/results.jsonl"],
         "script": "plot_figures.py", "status": "SUPPORTED (shape)"},
        {"id": "FIG3", "file": "runs/analysis/figures/day3/fig3_contractnli_per_hypothesis.png",
         "data": [f"runs/analysis/{L}/units_contractnli.csv" for L in ck[:1] + ck[2:11]], "script": "plot_figures_day3.py", "status": PM},
    ]
    for fg in figures:
        fg["file_sha256"] = sha(F / fg["file"])
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=F).stdout.strip()
    doc = {"freeze_id": f"FINAL-MANIFEST-{stamp}", "git_head_at_freeze": head, "corpus_manifest_sha256": CORPUS,
           "entries": ENTRIES, "figures": figures,
           "files": {str(p.relative_to(F)): h for p, h in sorted(FILES.items(), key=lambda kv: str(kv[0]))},
           "mismatches": [e["id"] for e in ENTRIES if not e["match"]]}
    (out / "final_manifest.json").write_text(json.dumps(doc, indent=2, default=str) + "\n")
    md = [f"# Final results manifest", "",
          f"Freeze ID `{doc['freeze_id']}` · Git HEAD at freeze `{head[:8]}` · corpus manifest SHA-256 `{CORPUS}`", "",
          "Every value below was **re-computed from the raw file** by `freeze_results.py` and compared with the value stated in the",
          "reports (`match`). Machine-readable version with full file hashes: "
          f"`runs/final_manifest/{stamp}/final_manifest.json`.", "",
          f"Mismatches: **{len(doc['mismatches'])}** {doc['mismatches'] or ''}", "",
          "| ID | Claim | Stated | Re-computed | Match | Experiment | Release(s): commit / ruleset SHA-256 | Source file (SHA-256) | Status |",
          "|---|---|---|---|---|---|---|---|---|"]
    for e in ENTRIES:
        rels = "<br>".join(f"{r['release']}: `{r['engine_commit']}` / `{r['ruleset_sha256']}`" for r in e["releases"][:4])
        if len(e["releases"]) > 4:
            rels += f"<br>(+{len(e['releases']) - 4} more)"
        srcs = "<br>".join(f"`{s['path']}` (`{(s['sha256'] or 'dir')[:12]}`)" for s in e["sources"][:3])
        md.append(f"| {e['id']} | {e['claim']} | {e['stated']} | {e['recomputed']} | {'✓' if e['match'] else '✗'} | "
                  f"{e['experiment']} | {rels} | {srcs} | {e['status']} |")
    md += ["", "## Figures", "", "| ID | File (SHA-256) | Data | Script | Status |", "|---|---|---|---|---|"]
    for fg in figures:
        md.append(f"| {fg['id']} | `{fg['file']}` (`{fg['file_sha256'][:12]}`) | {', '.join('`'+d+'`' for d in fg['data'][:3])} | "
                  f"`{fg['script']}` | {fg['status']} |")
    md += ["", "## Frozen inputs", "",
           f"- Corpus: `corpus/manifest.csv` SHA-256 `{CORPUS}` (618 rows).",
           "- Releases: `releases/manifest_v2.json` (canonical; 15 engine states + commit + ruleset and engine SHA-256). "
           "`releases/manifest.json` is the superseded Day 1 record (hash-seed bug, see `runs/validation/VALIDATION_LOG.md`).",
           "- Phase 2 pipeline-test release: `runs/phase2/20261017T021857Z/pipeline/release_7.3.0-pipelinetest.1.json`.",
           "", "No earlier output was modified; this freeze only adds `runs/final_manifest/<stamp>/` and this file."]
    (F / "FINAL_RESULTS_MANIFEST.md").write_text("\n".join(md) + "\n")
    print(f"{len(ENTRIES)} entries, {len(doc['mismatches'])} mismatches: {doc['mismatches']}")
    print(out)


if __name__ == "__main__":
    main()
