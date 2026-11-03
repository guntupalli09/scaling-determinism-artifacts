"""
Traceability check: does the research package contain, byte for byte, every file the manuscript's numbers come from?

    python trace_manuscript.py PACKAGE_DIR          (PACKAGE_DIR = the unpacked scaling-determinism-artifacts/)

Checks:
1. every source file listed in the frozen results manifest (runs/final_manifest/.../final_manifest.json, 17 Oct 2026),
   with the SHA-256 recorded at freeze time;
2. the comparator files produced after the freeze (Step A, B, C and the stratified analysis), against the study
   directory;
3. the manuscript figures, with their data and plotting script.
Writes TRACEABILITY.md into PACKAGE_DIR and exits non-zero if anything is missing or differs.
"""
import hashlib
import json
import sys
from pathlib import Path

F = Path(__file__).resolve().parents[2]            # experiments/followup (the study directory)
PKG = Path(sys.argv[1]).resolve()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
rows, bad = [], 0


def check(group, claim, rel, want=None):
    global bad
    p = PKG / rel
    if not p.exists():
        status = "MISSING"
    else:
        want = want or sha(F / rel)
        status = "ok" if sha(p) == want else "DIFFERS"
    bad += status != "ok"
    rows.append((group, claim, rel, status))


# 1. frozen manifest (values recomputed from these files at freeze time, 0 mismatches)
m = json.loads((F / "runs/final_manifest/20261017T052400Z/final_manifest.json").read_text())
for e in m["entries"]:
    for s in e.get("sources", []):
        check("frozen manifest", f"{e['id']}: {e['claim']}", s["path"], s["sha256"])
for rel, h in m["files"].items():
    if not rel.startswith("runs/analysis/figures/"):    # draft figures superseded by manuscript_final/figures
        check("frozen manifest", "file listed in manifest", rel, h)
check("frozen manifest", "the manifest itself", "runs/final_manifest/20261017T052400Z/final_manifest.json")

# 2. after the freeze: comparators (manuscript §5.9, Tables 4-6)
S = "runs/step_b"
post = [
    ("Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed)", "runs/phase3_kaggle/20261018T102353Z_v4"),
    ("Table 4: corrected Step A, RoBERTa-base", "runs/diagnostics/cuad/colab_20261019T1634Z_roberta-base/step_a_result.json"),
    ("Table 4: corrected Step A, RoBERTa-large", "runs/diagnostics/cuad/kaggle_v5_20261019T1954Z_roberta-large/diag_state/corrected_roberta-large/step_a_result.json"),
    ("Table 4: corrected Step A, RoBERTa-large predictions", "runs/diagnostics/cuad/kaggle_v5_20261019T1954Z_roberta-large/diag_state/corrected_roberta-large/nbest_partial.jsonl.gz"),
    ("Table 4: corrected Step A, DeBERTa", "runs/diagnostics/cuad/modal_20261020T2240Z_deberta_resume/step_a_result.json"),
    ("Table 4: corrected Step A, DeBERTa predictions", "runs/diagnostics/cuad/modal_20261020T2240Z_deberta_resume/nbest_partial.jsonl.gz"),
    ("Table 4: ContractNLI amended Step A", f"{S}/contractnli_bert-base/step_a_result_amended.json"),
    ("Step B: RoBERTa-base predictions, 25,338 units", f"{S}/cuad_roberta-base/roberta-base/predictions.jsonl.gz"),
    ("Step B: RoBERTa-base CUAD-test slice (re-scores to Step A)", f"{S}/cuad_roberta-base/roberta-base/cuad_test/nbest_partial.jsonl.gz"),
    ("Step B: RoBERTa-base re-score", f"{S}/cuad_roberta-base/step_a_rescore_result.json"),
    ("Step B: RoBERTa-large predictions, 21,156 units", f"{S}/cuad_roberta-large/roberta-large/predictions.jsonl.gz"),
    ("Table 5: Step C RoBERTa-base", f"{S}/cuad_roberta-base/step_c/units_cuad.csv"),
    ("Table 5: Step C RoBERTa-large", f"{S}/cuad_roberta-large/step_c/units_cuad.csv"),
    ("Table 5: Step C DeBERTa", f"{S}/cuad_deberta-v2-xlarge/step_c/units_cuad.csv"),
    ("Table 5: Step C ContractNLI", f"{S}/contractnli_bert-base/paired_units_engine_vs_span_nli_bert.csv"),
    ("Table 5: Step C ContractNLI summary", f"{S}/contractnli_bert-base/paired_result.json"),
    ("Table 6: stratified analysis", f"{S}/stratified/stratified_step_c.json"),
    ("Table 6: stratified analysis script", f"{S}/stratified/stratified_step_c.py"),
    ("Appendix A / Table 6 strata: frozen mapping", "comparators/label_mapping.json"),
    ("§5.8: engine runtime per document", "runs/v7.2.0/results.jsonl"),
]
for claim, rel in post:
    p = F / rel
    files = [p] if p.is_file() else sorted(x for x in p.rglob("*") if x.is_file() and "__pycache__" not in x.parts
                                          and "inputs" not in x.parts and not any(y.startswith("chunk_") for y in x.parts))
    for x in files:
        check("after freeze", claim, str(x.relative_to(F)))

# 3. manuscript figures
for fig, data in [("Figure_1.png", "runs/phase6/20261017T010324Z/performance.json"),
                  ("Figure_2.png", "runs/analysis/v7.2.0/units_contractnli.csv"),
                  ("Figure_3.png", "runs/analysis/scaling.json")]:
    check("figures", f"manuscript {fig}", f"manuscript_final/figures/{fig}")
    check("figures", f"data for {fig}", data)
check("figures", "plotting script", "manuscript_final/plot_manuscript_figures.py")

out = ["# Traceability: manuscript to research package", "",
       f"Every file below was compared byte for byte (SHA-256) with the study record. Problems: **{bad}**.", "",
       "| Group | Supports | File | Status |", "|---|---|---|---|"]
seen = set()
for g, c, r, s in rows:
    if (r, c) in seen:
        continue
    seen.add((r, c))
    out.append(f"| {g} | {c} | `{r}` | {s} |")
(PKG / "TRACEABILITY.md").write_text("\n".join(out) + "\n")
print(f"{len(seen)} checks, {bad} problems")
for g, c, r, s in rows:
    if s != "ok":
        print(s, r, "<-", c)
sys.exit(1 if bad else 0)
