# Phase 3 validation report

**Phase 3 status: INCOMPLETE.** Step A passed for 0 of 4 comparators. At least one comparator has not reached a terminal Step A or has unfinished Steps B/C; nothing below that is marked in progress is a result.

Generated 2026-10-18T10:23:53+00:00 from `/kaggle/working/phase3_state`. Protocol: Step A (reproduce published metrics, pre-registered tolerances) → Step B (frozen corpus) → Step C (paired comparison), B/C only after Step A PASS. No tuning.

## Sessions

| Started (UTC) | GPUs | Repo commit | Dirty |
|---|---|---|---|
| 2026-10-17T23:23:47+00:00 | Tesla T4, 15360 MiB, 580.178.04; Tesla T4, 15360 MiB, 580.178.04 | `3bb4bfcb7b` | False |

Data: OK (manifest sha256 `3bcd0d90806f2441…`)

## CUAD (Hendrycks et al. 2021, Table 2), test split, 4,182 questions

| Model | Step A | AUPR (published) | P@80R (published) | Step B frozen corpus | Step C paired |
|---|---|---|---|---|---|
| roberta-base | STEP_A_FAIL | 37.7 (42.6) | 26.8 (31.1) | gated (Step A not passed) | gated (Step A not passed) |
| roberta-large | STEP_A_FAIL | 44.6 (48.2) | 34.7 (38.1) | gated (Step A not passed) | gated (Step A not passed) |
| deberta-v2-xlarge | INCOMPLETE_BUDGET (1649/4182 questions) | not scored | not scored | waits on Step A | waits on Step A |

## ContractNLI Span NLI BERT-base (Koreeda & Manning 2021, Table 3), test split

- Environment: OK 1.8.1+cu111; training (conf_base.yml, seed 42, one GPU): **COMPLETE**; test.py: **COMPLETE**
- Step A: **STEP_A_FAIL**. mAP 0.751 (target 0.885), accuracy 0.824 (0.838), F1(E) 0.775 (0.765); key paths `{'accuracy': 'macro_label_micro_doc.class.accuracy', 'f1_entailment': 'macro_label_micro_doc.class.f1_entailment', 'map': 'micro_label_micro_doc.span.map'}`
- Pairing: GATED_STEP_A_NOT_PASSED

## Known deviations from the original setups (declared, not tuned)

- CUAD: community checkpoints `akdeniz27/*-cuad`; our re-implementation of HF SQuAD-v2 post-processing (max_seq 512, stride 256, n-best 20, fp32); tolerance pre-registered in `cuad_step_a.py` (commit `09e7990f`).
- ContractNLI: one published configuration (conf_base.yml, seed 42) instead of the paper's 100-config sweep averaged over the best 3; torch 1.8.1+cu111 (the authors' README build for newer GPUs) instead of 1.7.1; other pins as in the authors' requirements.txt, plus packaging==20.9 and protobuf==3.20.3 (unpinned transitive dependencies whose current versions break transformers 4.5.1 / tensorboard 2.4.1).
- Hardware: Kaggle free GPU (see Sessions). Results from a different GPU may differ in the last digits.

