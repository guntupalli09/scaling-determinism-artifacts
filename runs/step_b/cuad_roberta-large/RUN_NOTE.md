# CUAD Step B: RoBERTa-large (akdeniz27/roberta-large-cuad)

Basis: amendment B9, approved 2026-11-02 (review_package/DECISION_STEP_B_APPROVAL.md).

- Harness comparators/step_b/cuad_step_b.py (82/82 equivalence with the reference pipeline). Frozen corpus manifest
  SHA 3bcd0d90...c755b (checked on use). All 41 CUAD questions on the 516 non-cuad_test documents (cuad_test is
  skipped: its predictions are the corrected Step A predictions, already used for Step C in step_c/).
- Kaggle T4 x2, two sessions: runs/step_b/kaggle_sessions/20261102_s1 (code a6cc4f29, chunks 0-135) and
  20261103_s2 (code ba76c395, chunks 136-293). Each session's pre-flight check reproduced the committed Step A
  predictions on two CUAD-test contracts (82/82 top answers, max |dp| 0.0).
- 294/294 chunks, 1,141,478 features, 42.6 GPU-hours of inference; no chunk computed twice.
- Merge: 21,156 units = 516 x 41 (all present).
  roberta-large/predictions.jsonl.gz SHA-256 66635866be5196383cfd8a60120191feca5a7355779f8d0544d90a87bddf5256.
- Step C (cuad_test, 2,142 units): step_c/ and ../CUAD_STEP_C_NOTE.md.
