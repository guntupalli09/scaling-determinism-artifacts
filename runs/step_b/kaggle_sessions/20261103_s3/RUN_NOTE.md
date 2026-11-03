# Kaggle Step B session 3 (3 Nov 2026): DeBERTa-v2-xlarge

Kernel santhoshguntupalli/triage-step-b, code commit a5f4092d, T4 x2, queue deberta-v2-xlarge only, 7 h budget (kept
inside the weekly Kaggle GPU quota). Pushed 10:46Z; both workers stopped by the session budget at about 17:20Z
(exit codes 0, 0).

- Pre-flight check on both GPUs: 82/82 top answers agree with the committed Step A predictions, max |dp| = 0.0.
- 43 of 294 chunks done (shard 0 next chunk 44, shard 1 next chunk 43); 13.1 GPU-hours of inference; no chunk computed
  twice. About 6.8 chunks per hour on two T4s, so the remaining 251 chunks need roughly 37 more hours.
- Only the deberta-v2-xlarge state is kept here (the roberta-large outputs are in runs/step_b/cuad_roberta-large).
  These chunk outputs are the only copy until the merge; the next session resumes from this state.
