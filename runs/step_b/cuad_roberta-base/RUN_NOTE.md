# CUAD Step B + Step C: RoBERTa-base (akdeniz27/roberta-base-cuad) [Step C: PRELIM draft mapping]

Basis: amendment B9, approved 2026-11-02 (review_package/DECISION_STEP_B_APPROVAL.md).

## Step B run
- Harness comparators/step_b/cuad_step_b.py (validated: 82/82 equivalence with the reference pipeline), code commit
  de40eaf5, frozen corpus manifest SHA 3bcd0d90...c755b (checked on use), all 618 documents x 41 CUAD questions.
- Modal T4 (free monthly credit), volume triage-step-b; environment log: environment_modal.jsonl.
  Two calls (2 Nov 09:11Z; 2 Nov 17:33Z). The second was restarted by Modal on a new container twice (21:05Z, 03:49Z
  on 3 Nov); each restart resumed from the finished chunks, and only the chunk in progress was recomputed. No chunk
  appears twice in run_log_shards0of1.jsonl.
- 335/335 chunks, 1,296,105 features, 20.1 GPU-hours of inference. Finished 3 Nov 06:27Z.
- Merge: 25,338 units = 618 x 41 (all present; the merge refuses otherwise).
  roberta-base/predictions.jsonl.gz SHA-256 33ded6c69560e695e8075bfab08bc60a38091afefd159d245080a08681b37d58.
  roberta-base/cuad_test/nbest_partial.jsonl.gz: the 4,182 cuad_test units in the Step A format; uncompressed
  SHA-256 b306fcc1a7c7a5ee56e55cd8669e841e097de39afc61f4d93dac20165ed0c28f.

## Check against Step A (unchanged comparators/cuad_step_a.py, official evaluate.py)
The Step B cuad_test slice scores AUPR 42.603, P@80R 31.140 (step_a_rescore_result.json): STEP_A_PASS, identical
to the corrected Step A result (runs/diagnostics/cuad/colab_20261019T1634Z_roberta-base/step_a_result.json) to every
printed digit.

## Step C (unchanged evaluate_paired.py v7.2.0, 2,142 cuad_test units x 21 mapped categories)
    python -m experiments.followup.evaluate_paired v7.2.0 \
        --cuad-model-dir experiments/followup/runs/step_b/cuad_roberta-base/roberta-base/cuad_test \
        --out-dir experiments/followup/runs/step_b/cuad_roberta-base/step_c
(run on the uncompressed nbest_partial.jsonl, SHA above.)

| System (2,142 units) | Precision (95% CI) | Recall (95% CI) | F1 (95% CI) | Accuracy |
|---|---|---|---|---|
| TriageCounsel v7.2.0 | .663 (.607-.715) | .354 (.315-.395) | .462 (.419-.501) | .790 |
| CUAD RoBERTa-base | .553 (.522-.584) | .985 (.971-.993) | .708 (.682-.734) | .794 |

Exact McNemar on per-unit correctness: only engine correct 384, only model correct 392, p = .80 (no significant
difference in per-unit accuracy). The model has far higher recall and F1; the engine has higher precision.
