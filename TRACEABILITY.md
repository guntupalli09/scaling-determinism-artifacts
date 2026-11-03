# Traceability: manuscript to research package

Every file below was compared byte for byte (SHA-256) with the study record. Problems: **0**.

| Group | Supports | File | Status |
|---|---|---|---|
| frozen manifest | R01: Within-process executions across 12 engine states | `runs/v1.0.3-iccs/results.jsonl` | ok |
| frozen manifest | R01: Within-process executions across 12 engine states | `runs/v1.0.3/results.jsonl` | ok |
| frozen manifest | R01: Within-process executions across 12 engine states | `runs/v2.0.0/results.jsonl` | ok |
| frozen manifest | R01: Within-process executions across 12 engine states | `runs/v2.1.0/results.jsonl` | ok |
| frozen manifest | R01: Within-process executions across 12 engine states | `runs/v3.0.0/results.jsonl` | ok |
| frozen manifest | R01: Within-process executions across 12 engine states | `runs/v4.0.0/results.jsonl` | ok |
| frozen manifest | R01: Within-process executions across 12 engine states | `runs/v5.0.0/results.jsonl` | ok |
| frozen manifest | R01: Within-process executions across 12 engine states | `runs/v6.0.0/results.jsonl` | ok |
| frozen manifest | R01: Within-process executions across 12 engine states | `runs/v7.0.0/results.jsonl` | ok |
| frozen manifest | R01: Within-process executions across 12 engine states | `runs/v7.1.0/results.jsonl` | ok |
| frozen manifest | R01: Within-process executions across 12 engine states | `runs/v7.2.0/results.jsonl` | ok |
| frozen manifest | R01: Within-process executions across 12 engine states | `runs/v7.2.0+20294216/results.jsonl` | ok |
| frozen manifest | R02: Documents with any output/finding variance (within-process, all states) | `runs/v1.0.3-iccs/results.jsonl` | ok |
| frozen manifest | R02: Documents with any output/finding variance (within-process, all states) | `runs/v1.0.3/results.jsonl` | ok |
| frozen manifest | R02: Documents with any output/finding variance (within-process, all states) | `runs/v2.0.0/results.jsonl` | ok |
| frozen manifest | R02: Documents with any output/finding variance (within-process, all states) | `runs/v2.1.0/results.jsonl` | ok |
| frozen manifest | R02: Documents with any output/finding variance (within-process, all states) | `runs/v3.0.0/results.jsonl` | ok |
| frozen manifest | R02: Documents with any output/finding variance (within-process, all states) | `runs/v4.0.0/results.jsonl` | ok |
| frozen manifest | R02: Documents with any output/finding variance (within-process, all states) | `runs/v5.0.0/results.jsonl` | ok |
| frozen manifest | R02: Documents with any output/finding variance (within-process, all states) | `runs/v6.0.0/results.jsonl` | ok |
| frozen manifest | R02: Documents with any output/finding variance (within-process, all states) | `runs/v7.0.0/results.jsonl` | ok |
| frozen manifest | R02: Documents with any output/finding variance (within-process, all states) | `runs/v7.1.0/results.jsonl` | ok |
| frozen manifest | R02: Documents with any output/finding variance (within-process, all states) | `runs/v7.2.0/results.jsonl` | ok |
| frozen manifest | R02: Documents with any output/finding variance (within-process, all states) | `runs/v7.2.0+20294216/results.jsonl` | ok |
| frozen manifest | R03: v7.2.0 baseline executions (618 docs x 10) | `runs/v7.2.0/results.jsonl` | ok |
| frozen manifest | R04: Exact one-sided 95% upper bound, per-document variance rate (0/618) | `runs/v7.2.0/results.jsonl` | ok |
| frozen manifest | R05: Cross-process executions (15 states x 60 docs x 6 seeds) | `runs/determinism_crossprocess/20261017T002540Z/summary.json` | ok |
| frozen manifest | R05: Cross-process executions (15 states x 60 docs x 6 seeds) | `runs/determinism_crossprocess/20261017T002540Z/raw.json` | ok |
| frozen manifest | R06: Cross-process documents with output variance | `runs/determinism_crossprocess/20261017T002540Z/summary.json` | ok |
| frozen manifest | R07: v7.2.0 cuad fixed_denominator precision/recall/F1 | `runs/phase6/20261017T010324Z/performance.json` | ok |
| frozen manifest | R07: v7.2.0 cuad fixed_denominator precision/recall/F1 | `runs/analysis/v7.2.0/units_cuad.csv` | ok |
| frozen manifest | R08: v7.2.0 cuad direct_mappings_only precision/recall/F1 | `runs/phase6/20261017T010324Z/performance.json` | ok |
| frozen manifest | R08: v7.2.0 cuad direct_mappings_only precision/recall/F1 | `runs/analysis/v7.2.0/units_cuad.csv` | ok |
| frozen manifest | R09: v7.2.0 contractnli fixed_denominator precision/recall/F1 | `runs/phase6/20261017T010324Z/performance.json` | ok |
| frozen manifest | R09: v7.2.0 contractnli fixed_denominator precision/recall/F1 | `runs/analysis/v7.2.0/units_contractnli.csv` | ok |
| frozen manifest | R10: CUAD gold labels agree between test.json and master_clauses.csv (units) | `runs/validation/20261017T021819Z/day1_validation.json` | ok |
| frozen manifest | R11: Day 1 validation checks passing | `runs/validation/20261017T021819Z/day1_validation.json` | ok |
| frozen manifest | R12-v1.0.3-iccs: v1.0.3-iccs CUAD fixed-denominator precision/recall | `runs/phase6/20261017T010324Z/performance.json` | ok |
| frozen manifest | R12-v1.0.3-iccs: v1.0.3-iccs CUAD fixed-denominator precision/recall | `runs/analysis/v1.0.3-iccs/units_cuad.csv` | ok |
| frozen manifest | R12-v7.2.0: v7.2.0 CUAD fixed-denominator precision/recall | `runs/phase6/20261017T010324Z/performance.json` | ok |
| frozen manifest | R12-v7.2.0: v7.2.0 CUAD fixed-denominator precision/recall | `runs/analysis/v7.2.0/units_cuad.csv` | ok |
| frozen manifest | R13: ICCS->v7.2.0 CUAD gold-positive units gained/lost | `runs/phase6/20261017T010324Z/paired_tests.json` | ok |
| frozen manifest | R13p: ICCS->v7.2.0 recall McNemar exact p < 1e-18 | `runs/phase6/20261017T010324Z/paired_tests.json` | ok |
| frozen manifest | R14: nda-3 true positives v4.0.0 -> v5.0.0 -> v7.2.0 | `runs/analysis/v4.0.0/units_contractnli.csv` | ok |
| frozen manifest | R14: nda-3 true positives v4.0.0 -> v5.0.0 -> v7.2.0 | `runs/analysis/v5.0.0/units_contractnli.csv` | ok |
| frozen manifest | R14: nda-3 true positives v4.0.0 -> v5.0.0 -> v7.2.0 | `runs/analysis/v7.2.0/units_contractnli.csv` | ok |
| frozen manifest | R15: ContractNLI v5->v6 gold-positive units gained (nda-18 driven) | `runs/phase6/20261017T010324Z/paired_tests.json` | ok |
| frozen manifest | R16: Counterfactual: v5 with L_BROADDEF_01 reverted / v4 with new pattern (nda-3 TP) | `runs/phase4_counterfactual/20261017T021716Z/counterfactuals.json` | ok |
| frozen manifest | R17: Bisection: first commit with nda-3 drop (47->38) | `runs/phase4_counterfactual/bisect_v2.1_v3.0_20261017T004907Z.json` | ok |
| frozen manifest | R18: Distinct rule-definition states labelled 7.2.0 | `releases/manifest_v2.json` | ok |
| frozen manifest | R19: Distinct engine-code states labelled 7.2.0 | `releases/manifest_v2.json` | ok |
| frozen manifest | R20: ICCS commit rule count | `releases/manifest_v2.json` | ok |
| frozen manifest | R21: Rule-count scaling exponent | `runs/analysis/scaling.json` | ok |
| frozen manifest | R22: Document-length scaling exponent range | `runs/analysis/scaling.json` | ok |
| frozen manifest | R23: S1 injection-attributable cases v7.2.0 / v1.0.3-iccs | `runs/phase5_control/20261017T021750Z/attribution.csv` | ok |
| frozen manifest | R23: S1 injection-attributable cases v7.2.0 / v1.0.3-iccs | `runs/phase5_control/20261017T021750Z/meta.json` | ok |
| frozen manifest | R23: S1 injection-attributable cases v7.2.0 / v1.0.3-iccs | `runs/phase5/20261017T013302Z/cases_full.jsonl` | ok |
| frozen manifest | R24: v7.2.0 attributable cases with a finding removed | `runs/phase5_control/20261017T021750Z/stats.json` | ok |
| frozen manifest | R24: v7.2.0 attributable cases with a finding removed | `runs/phase5_control/20261017T021750Z/attribution.csv` | ok |
| frozen manifest | R25: Paired containment ICCS vs v7.2.0 discordant cells (ICCS-only / v7.2.0-only contained) | `runs/phase5_control/20261017T021750Z/stats.json` | ok |
| frozen manifest | R26: S3 explanation-layer FAIL cases (both releases) | `runs/phase5/20261017T013302Z/cases_full.jsonl` | ok |
| frozen manifest | R26b: Total inference-suite cases | `runs/phase5/20261017T013302Z/cases_full.jsonl` | ok |
| frozen manifest | R27: Proposal-path cases PASS/FAIL/BLOCKED_API | `runs/phase5_proposal/20261017T021711Z/cases_full.json` | ok |
| frozen manifest | R28: Phase 2 pipeline test: targeted fixed / regressions / base findings lost | `runs/phase2/20261017T021857Z/result.json` | ok |
| frozen manifest | R29: Phase 2 failure cases total / LLM generation blocked | `runs/phase2/20261017T021857Z/result.json` | ok |
| frozen manifest | R29: Phase 2 failure cases total / LLM generation blocked | `runs/phase2/20261017T021857Z/llm_generation_status.json` | ok |
| frozen manifest | R30: Engine vs LexNLP McNemar discordant (engine-only / LexNLP-only correct) | `runs/phase6/20261017T010324Z/comparators.json` | ok |
| frozen manifest | R30: Engine vs LexNLP McNemar discordant (engine-only / LexNLP-only correct) | `runs/phase6/20261017T010324Z/paired_units_engine_vs_lexnlp.csv` | ok |
| frozen manifest | file listed in manifest | `releases/manifest_v2.json` | ok |
| frozen manifest | file listed in manifest | `runs/analysis/scaling.json` | ok |
| frozen manifest | file listed in manifest | `runs/analysis/v1.0.3-iccs/units_cuad.csv` | ok |
| frozen manifest | file listed in manifest | `runs/analysis/v4.0.0/units_contractnli.csv` | ok |
| frozen manifest | file listed in manifest | `runs/analysis/v5.0.0/units_contractnli.csv` | ok |
| frozen manifest | file listed in manifest | `runs/analysis/v7.2.0/units_contractnli.csv` | ok |
| frozen manifest | file listed in manifest | `runs/analysis/v7.2.0/units_cuad.csv` | ok |
| frozen manifest | file listed in manifest | `runs/determinism_crossprocess/20261017T002540Z/raw.json` | ok |
| frozen manifest | file listed in manifest | `runs/determinism_crossprocess/20261017T002540Z/summary.json` | ok |
| frozen manifest | file listed in manifest | `runs/phase2/20261017T021857Z/llm_generation_status.json` | ok |
| frozen manifest | file listed in manifest | `runs/phase2/20261017T021857Z/result.json` | ok |
| frozen manifest | file listed in manifest | `runs/phase4_counterfactual/20261017T021716Z/counterfactuals.json` | ok |
| frozen manifest | file listed in manifest | `runs/phase4_counterfactual/bisect_v2.1_v3.0_20261017T004907Z.json` | ok |
| frozen manifest | file listed in manifest | `runs/phase5/20261017T013302Z/cases_full.jsonl` | ok |
| frozen manifest | file listed in manifest | `runs/phase5_control/20261017T021750Z/attribution.csv` | ok |
| frozen manifest | file listed in manifest | `runs/phase5_control/20261017T021750Z/meta.json` | ok |
| frozen manifest | file listed in manifest | `runs/phase5_control/20261017T021750Z/stats.json` | ok |
| frozen manifest | file listed in manifest | `runs/phase5_proposal/20261017T021711Z/cases_full.json` | ok |
| frozen manifest | file listed in manifest | `runs/phase6/20261017T010324Z/comparators.json` | ok |
| frozen manifest | file listed in manifest | `runs/phase6/20261017T010324Z/paired_tests.json` | ok |
| frozen manifest | file listed in manifest | `runs/phase6/20261017T010324Z/paired_units_engine_vs_lexnlp.csv` | ok |
| frozen manifest | file listed in manifest | `runs/phase6/20261017T010324Z/performance.json` | ok |
| frozen manifest | file listed in manifest | `runs/v1.0.3-iccs/results.jsonl` | ok |
| frozen manifest | file listed in manifest | `runs/v1.0.3/results.jsonl` | ok |
| frozen manifest | file listed in manifest | `runs/v2.0.0/results.jsonl` | ok |
| frozen manifest | file listed in manifest | `runs/v2.1.0/results.jsonl` | ok |
| frozen manifest | file listed in manifest | `runs/v3.0.0/results.jsonl` | ok |
| frozen manifest | file listed in manifest | `runs/v4.0.0/results.jsonl` | ok |
| frozen manifest | file listed in manifest | `runs/v5.0.0/results.jsonl` | ok |
| frozen manifest | file listed in manifest | `runs/v6.0.0/results.jsonl` | ok |
| frozen manifest | file listed in manifest | `runs/v7.0.0/results.jsonl` | ok |
| frozen manifest | file listed in manifest | `runs/v7.1.0/results.jsonl` | ok |
| frozen manifest | file listed in manifest | `runs/v7.2.0+20294216/results.jsonl` | ok |
| frozen manifest | file listed in manifest | `runs/v7.2.0/results.jsonl` | ok |
| frozen manifest | file listed in manifest | `runs/validation/20261017T021819Z/day1_validation.json` | ok |
| frozen manifest | the manifest itself | `runs/final_manifest/20261017T052400Z/final_manifest.json` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/PHASE3_VALIDATION_REPORT.md` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/contractnli_bert-base/output_base/conf.yml` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/contractnli_bert-base/output_base/config.json` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/contractnli_bert-base/output_base/metrics.json` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/contractnli_bert-base/output_base/result.json` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/contractnli_bert-base/output_base/test_metrics.json` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/contractnli_bert-base/output_base/test_result.json` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/contractnli_bert-base/step_a_result.json` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/cuad_deberta-v2-xlarge_gpu/nbest_partial.jsonl.gz` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/cuad_roberta-base_gpu/nbest_partial.jsonl.gz` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/cuad_roberta-base_gpu/step_a_result.json` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/cuad_roberta-large_gpu/nbest_partial.jsonl.gz` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/cuad_roberta-large_gpu/step_a_result.json` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/environment.json` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/logs/build_corpus.log` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/logs/cnli_checkout.log` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/logs/cnli_clone.log` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/logs/cnli_env.log` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/logs/cnli_step_a.log` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/logs/cnli_test.log` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/logs/cnli_train.log` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/logs/cuad_deberta-v2-xlarge_validate.log` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/logs/cuad_deps.log` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/logs/cuad_roberta-base_score.log` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/logs/cuad_roberta-base_validate.log` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/logs/cuad_roberta-large_score.log` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/logs/cuad_roberta-large_validate.log` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/logs/fetch_external.log` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/notebook_log.json` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/phase3_status.json` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/pip_freeze_contractnli.txt` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/pip_freeze_cuad.txt` | ok |
| after freeze | Table 4: CUAD RoBERTa-base Step A (pre-registered run, failed) | `runs/phase3_kaggle/20261018T102353Z_v4/stages.json` | ok |
| after freeze | Table 4: corrected Step A, RoBERTa-base | `runs/diagnostics/cuad/colab_20261019T1634Z_roberta-base/step_a_result.json` | ok |
| after freeze | Table 4: corrected Step A, RoBERTa-large | `runs/diagnostics/cuad/kaggle_v5_20261019T1954Z_roberta-large/diag_state/corrected_roberta-large/step_a_result.json` | ok |
| after freeze | Table 4: corrected Step A, RoBERTa-large predictions | `runs/diagnostics/cuad/kaggle_v5_20261019T1954Z_roberta-large/diag_state/corrected_roberta-large/nbest_partial.jsonl.gz` | ok |
| after freeze | Table 4: corrected Step A, DeBERTa | `runs/diagnostics/cuad/modal_20261020T2240Z_deberta_resume/step_a_result.json` | ok |
| after freeze | Table 4: corrected Step A, DeBERTa predictions | `runs/diagnostics/cuad/modal_20261020T2240Z_deberta_resume/nbest_partial.jsonl.gz` | ok |
| after freeze | Table 4: ContractNLI amended Step A | `runs/step_b/contractnli_bert-base/step_a_result_amended.json` | ok |
| after freeze | Step B: RoBERTa-base predictions, 25,338 units | `runs/step_b/cuad_roberta-base/roberta-base/predictions.jsonl.gz` | ok |
| after freeze | Step B: RoBERTa-base CUAD-test slice (re-scores to Step A) | `runs/step_b/cuad_roberta-base/roberta-base/cuad_test/nbest_partial.jsonl.gz` | ok |
| after freeze | Step B: RoBERTa-base re-score | `runs/step_b/cuad_roberta-base/step_a_rescore_result.json` | ok |
| after freeze | Step B: RoBERTa-large predictions, 21,156 units | `runs/step_b/cuad_roberta-large/roberta-large/predictions.jsonl.gz` | ok |
| after freeze | Table 5: Step C RoBERTa-base | `runs/step_b/cuad_roberta-base/step_c/units_cuad.csv` | ok |
| after freeze | Table 5: Step C RoBERTa-large | `runs/step_b/cuad_roberta-large/step_c/units_cuad.csv` | ok |
| after freeze | Table 5: Step C DeBERTa | `runs/step_b/cuad_deberta-v2-xlarge/step_c/units_cuad.csv` | ok |
| after freeze | Table 5: Step C ContractNLI | `runs/step_b/contractnli_bert-base/paired_units_engine_vs_span_nli_bert.csv` | ok |
| after freeze | Table 5: Step C ContractNLI summary | `runs/step_b/contractnli_bert-base/paired_result.json` | ok |
| after freeze | Table 6: stratified analysis | `runs/step_b/stratified/stratified_step_c.json` | ok |
| after freeze | Table 6: stratified analysis script | `runs/step_b/stratified/stratified_step_c.py` | ok |
| after freeze | Appendix A / Table 6 strata: frozen mapping | `comparators/label_mapping.json` | ok |
| after freeze | §5.8: engine runtime per document | `runs/v7.2.0/results.jsonl` | ok |
| figures | manuscript Figure_1.png | `manuscript_final/figures/Figure_1.png` | ok |
| figures | data for Figure_1.png | `runs/phase6/20261017T010324Z/performance.json` | ok |
| figures | manuscript Figure_2.png | `manuscript_final/figures/Figure_2.png` | ok |
| figures | data for Figure_2.png | `runs/analysis/v7.2.0/units_contractnli.csv` | ok |
| figures | manuscript Figure_3.png | `manuscript_final/figures/Figure_3.png` | ok |
| figures | data for Figure_3.png | `runs/analysis/scaling.json` | ok |
| figures | plotting script | `manuscript_final/plot_manuscript_figures.py` | ok |
