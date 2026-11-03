# ContractNLI Span NLI BERT (bert-base): amended Step A, Step B and Step C

Basis: protocol amendment B9, approved 2026-11-02 (review_package/DECISION_STEP_B_APPROVAL.md).

## Inputs (unchanged, from the pre-registered Kaggle run)
- Model run: runs/phase3_kaggle/20261018T102353Z_v4/contractnli_bert-base (conf_base.yml, seed 42, one training run).
- Predictions: output_base/test_result.json (authors' test.py output on the ContractNLI test split, 123 documents).
- Metrics: output_base/test_metrics.json (authors' evaluator).

## Amended Step A (step_a_result_amended.json): STEP_A_PASS
Same targets, tolerances and keys as the pre-registered check, except evidence mAP at the paper's per-query
aggregation (micro_label_macro_doc.span.map).

| Metric | Target | Reproduced | Delta | Tolerance |
|---|---|---|---|---|
| Evidence mAP (per query, paper definition) | .885 | .8635 | -.0215 | ±.03 |
| Evidence mAP (pooled, pre-registered key; reported only) | .885 | .7511 | -.1339 | ±.03 |
| NLI accuracy | .838 | .8240 | -.0140 | ±.03 |
| F1 (entailment) | .765 | .7750 | +.0100 | ±.05 |

The pre-registered result (STEP_A_FAIL on pooled mAP) is unchanged and stays the official Step A record.

## Step B: no new inference needed
The frozen `nda` slice (123 documents) is the ContractNLI test split: every text's SHA-256 equals the manifest's
text_sha256, and test_result.json contains predictions for all 123. The model was not retrained or re-run; the
model weights were not needed because its predictions on the identical texts already exist from the original run.

## Step C (paired_result.json, paired_units_engine_vs_span_nli_bert.csv) [PRELIM: draft mapping]
615 units (123 NDAs x 5 mapped hypotheses), gold from the ContractNLI test split, engine v7.2.0.

| System | P | R | F1 |
|---|---|---|---|
| TriageCounsel v7.2.0 | .623 (.528-.709) | .304 (.247-.368) | .409 |
| Span NLI BERT | .898 (.848-.933) | .816 (.759-.862) | .855 |

Exact McNemar on per-unit correctness: only engine correct 30, only Span NLI BERT correct 161, p = 7.2e-23.
The supervised comparator, trained on ContractNLI's own training split, is significantly better on these units.
Values depend on the draft hypothesis mapping (comparators/label_mapping.json), pending review.

    python comparators/step_b/contractnli_step_a_amended.py --metrics <run>/output_base/test_metrics.json \
        --preregistered <run>/step_a_result.json --out runs/step_b/contractnli_bert-base
    python comparators/gpu/pair_contractnli.py --result <run>/output_base/test_result.json \
        --step-a runs/step_b/contractnli_bert-base/step_a_result_amended.json --out runs/step_b/contractnli_bert-base
