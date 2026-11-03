# CUAD Step C (paired with engine v7.2.0) from the corrected Step A predictions [PRELIM: draft mapping]

Basis: amendment B9, approved 2026-11-02 (review_package/DECISION_STEP_B_APPROVAL.md).

The pre-registered driver (comparators/kaggle/phase3_driver.py) computes CUAD Step C with
`evaluate_paired v7.2.0 --cuad-model-dir <Step A dir>`: units are the CUAD test slice (102 contracts x 21 mapped
categories = 2,142 units, the only slice with gold labels), and the comparator input is its Step A test-set
predictions. The 102 cuad_test texts are byte-identical to the CUAD test contexts. Step C therefore does not depend
on the rest of Step B, and is computed here from the corrected Step A predictions, with the unchanged
evaluate_paired.py and its pre-registered decision rule (present iff best non-empty answer > null answer).

Inputs (uncompressed, SHA-256):
- roberta-large: runs/diagnostics/cuad/kaggle_v5_20261019T1954Z_roberta-large/diag_state/corrected_roberta-large/
  nbest_partial.jsonl.gz -> 2aee3796223d542d5310ea73882170173347e8151fdb6bd01cd27569b050f850
- deberta-v2-xlarge: runs/diagnostics/cuad/modal_20261020T2240Z_deberta_resume/nbest_partial.jsonl.gz
  -> ba58ddf2e3700f260df2b4d756c810951cbbbe907532fcb649cb5cb706ae0968
- roberta-base: from its Step B run (cuad_roberta-base/RUN_NOTE.md); the regenerated cuad_test slice scores identically
  to Step A (AUPR 42.603, P@80R 31.140). cuad_roberta-base/roberta-base/cuad_test/nbest_partial.jsonl
  -> b306fcc1a7c7a5ee56e55cd8669e841e097de39afc61f4d93dac20165ed0c28f

| System (2,142 units) | Precision (95% CI) | Recall (95% CI) | F1 (95% CI) | Accuracy |
|---|---|---|---|---|
| TriageCounsel v7.2.0 | .663 (.607-.715) | .354 (.315-.395) | .462 (.419-.501) | .790 |
| CUAD RoBERTa-base | .553 (.522-.584) | .985 (.971-.993) | .708 (.682-.734) | .794 |
| CUAD RoBERTa-large | .598 (.565-.630) | .974 (.957-.985) | .741 (.716-.767) | .827 |
| CUAD DeBERTa-v2-xlarge | .590 (.558-.622) | .994 (.984-.998) | .741 (.716-.766) | .823 |

Exact McNemar on per-unit correctness:
- engine vs RoBERTa-base: only engine correct 384, only model correct 392, p = .80;
- engine vs RoBERTa-large: only engine correct 315, only model correct 394, p = .0034;
- engine vs DeBERTa-v2-xlarge: only engine correct 325, only model correct 396, p = .0091.

RoBERTa-large and DeBERTa are more accurate per unit (significant); RoBERTa-base's per-unit accuracy does not differ
significantly from the engine's. All three comparators have far higher recall and F1; the engine has higher precision.

    python -m experiments.followup.evaluate_paired v7.2.0 --cuad-model-dir <dir with nbest_partial.jsonl> \
        --out-dir experiments/followup/runs/step_b/cuad_<model>/step_c
