# Kaggle version 6 (resume run): what actually happened

- **Intended:** resume CUAD DeBERTa-v2-xlarge Step A from 1,649 / 4,182 questions, using the state dataset
  `triage-phase3-state`.
- **Actual:** the notebook's resume cell matched the committed copy of the version 4 run inside the code
  snapshot (`experiments/followup/runs/phase3_kaggle/20261018T102353Z_v4/`) instead of the state dataset.
  - That copy stores DeBERTa predictions gzipped, so the runner found no checkpoint.
  - It recomputed all 4,182 questions from scratch (12:28–12:59 UTC).
  - CUAD RoBERTa-base/-large and ContractNLI were correctly skipped as already final.
- **Validity:** the run is a valid, complete Step A input.
  - On the 1,649 questions also computed in version 4, top answers are identical (1,649/1,649) and
    n-best probabilities are identical.
  - The environment is identical: torch 2.11.0+cu128, transformers 4.57.6, tokenizers 0.22.2.
  - Code is commit `3505ef4e`, which contains the same driver and decoding as version 4's `3bb4bfcb`.
  - Re-scored locally with the pre-registered scorer, the result reproduces exactly.
- **Outcome:** STEP_A_FAIL. AUPR 28.2 (published 47.8); P@80R 0 (44.0); P@90R 0 (17.8).
  The model's top answer is the null answer for 3,051 / 4,182 questions.
- **Fix:** the resume cell now ignores any `stages.json` under `/experiments/` (commit after this note).
