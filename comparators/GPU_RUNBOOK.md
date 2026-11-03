# GPU runbook — Phase 3 comparators blocked on GPU (BLOCKED_GPU)

Everything needed to run these immediately on a CUDA machine. The protocol is Prof. Laakkonen's:
**(A)** reproduce the published metrics on the comparator's own test split; **(B)** only if A passes,
convert our frozen data (`corpus/manifest.csv`, sha256 in `corpus/MANIFEST.sha256`); **(C)** keep
predictions per contract and per clause for the paired statistics. No comparator number is reported
as valid unless Step A passes.

Common setup:
```bash
git clone <this repo> && cd Triage && git checkout claude/adoring-heisenberg-gd2tv1
python -m experiments.followup.build_corpus          # regenerates corpus/texts/ from sources; verify MANIFEST.sha256
```

### Free-GPU route: Kaggle (`comparators/kaggle/`, added 2026-10-17)

A ready-to-run Kaggle notebook (GPU T4 x2, free tier) that runs everything below with the same gating, resumable
across 12 h sessions. See `comparators/kaggle/README.md` for the two manual actions it needs. Not yet run on a GPU.

### Turnkey kit: `comparators/gpu/` (added 2026-10-17)

**Validation status: NOT VALIDATED on a GPU.** None of these scripts has run on a CUDA device. The only
checks so far:
- shell syntax;
- the gating logic of `contractnli_step_a.py` and `pair_contractnli.py`, exercised on *synthetic*
  metrics files (PASS / INCONCLUSIVE / refusal paths);
- the CUAD inference and scorer path, which is the CPU code currently running Step A.

Treat the first GPU run as a validation run. Inspect logs and `step_a_result.json` before trusting
anything.

```bash
cd experiments/followup
bash comparators/gpu/fetch_external.sh            # CUAD split, ContractNLI, official CUAD evaluate.py; aborts on any sha256 mismatch (EXTERNAL.sha256)
bash comparators/gpu/run_cuad_gpu.sh roberta-base # then roberta-large, deberta-v2-xlarge
bash comparators/gpu/run_contractnli_gpu.sh       # train conf_base.yml (seed 42) -> test.py -> Step A -> pairing
```
Both runners stop after Step A unless its status is `STEP_A_PASS`, as the protocol requires.
- **Do not tune.** Step A tolerances are pre-registered in `cuad_step_a.py` (commit `09e7990f`) and
  `contractnli_step_a.py`.
- `STEP_A_FAIL` and `INCONCLUSIVE_KEYS_NOT_FOUND` are reported as such; they are never scored as zero.
  - For the ContractNLI metric key paths, see the `available_keys` list in `step_a_result.json`.
- The CPU RoBERTa-base checkpoint (`runs/comparators/cuad_roberta-base/nbest_partial.jsonl`) is
  device-agnostic. It may be copied into the GPU output directory to resume, with the same decoding
  settings.
- Do not mix it with a different model.

## 1. ContractNLI — Span NLI BERT (Koreeda & Manning, 2021)

Status: **BLOCKED_GPU.** Checked on 2026-10-17:
- `stanfordnlp/contract-nli-bert` (HEAD `058c56f`) ships training code only. It has no Git tags,
  even though the README mentions tagged versions, no weight files and no download link.
- No official Hugging Face model exists under the stanfordnlp or author accounts.
- The only checkpoints are community uploads (e.g. `nikotang/span-nli-bert-large`). Those would be a
  different system and would need their own Step A.

Step A targets (paper Table 3, test split, mean ± sd over 3 models):

| Backbone | Evidence mAP | Evidence P@R80 | NLI Acc | NLI F1(C) | NLI F1(E) |
|---|---|---|---|---|---|
| BERT-base | .885 | .663 | .838 | .287 | .765 |
| BERT-large | .922 | .793 | .875 | .357 | .834 |

```bash
git clone https://github.com/stanfordnlp/contract-nli-bert && cd contract-nli-bert && git checkout 058c56f
python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt   # torch 1.7.1, transformers 4.5.1
mkdir -p data && cp <Triage>/experiments/followup/external/contract-nli/{train,dev,test}.json data/
# Single-configuration reproduction (the paper's 100-config sweep + best-3 average is optional, cluster-scale):
python train.py ./data/conf_base.yml ./output_base                  # conf_base.yml: bert-base-uncased, lr 3e-5, 5 epochs, seed 42
python test.py ./output_base ./data/test.json ./output_base/test_   # Step A: compare with the table above
```
Step B is trivial for this comparator: our `nda` slice *is* the ContractNLI test split (123 documents,
identical texts, verified by hash in `runs/validation/`). Step C: keep the per-document,
per-hypothesis predictions from `test.py` and join on `source_ref` = `file_name`.

Rough cost: BERT-base trains in about 1–2 GPU-hours on one modern GPU; BERT-large in about 4–6.

## 2. CUAD — RoBERTa-large and DeBERTa-v2-xlarge (Hendrycks et al., 2021)

Status: **BLOCKED_GPU** (CPU estimates: RoBERTa-large about 3 days, DeBERTa-xlarge 8–10 days for Step A alone).
RoBERTa-base Step A is running on CPU (`runs/comparators/cuad_roberta-base/`).

Step A targets (paper Table 2, CUAD test split): RoBERTa-base AUPR 42.6 / P@80R 31.1;
RoBERTa-large 48.2 / 38.1; DeBERTa-xlarge 47.8 / 44.0 (P@90R 17.8).

```bash
python -m venv /opt/cuad && /opt/cuad/bin/pip install torch transformers numpy scikit-learn
cd experiments/followup
for M in akdeniz27/roberta-large-cuad akdeniz27/deberta-v2-xlarge-cuad; do
  /opt/cuad/bin/python comparators/cuad_qa.py validate --model $M \
      --test-json external/cuad_split/test.json --out runs/comparators/cuad_$(basename $M)
  mkdir -p /tmp/eval && cp runs/comparators/cuad_$(basename $M)/nbest_predictions_.json /tmp/eval/
  # official scorer (external/cuad_evaluate.py, TheAtticusProject/cuad main): set model_path=/tmp/eval
done
```
`cuad_qa.py` uses CUDA automatically when available (same SQuAD-v2 protocol: max_seq 512, stride 256, n-best 20).

Step B/C, only for models that pass Step A:
```bash
/opt/cuad/bin/python comparators/cuad_qa.py corpus --model <M> --questions comparators/cuad_questions.json \
    --manifest corpus/manifest.csv --texts corpus/texts --out runs/comparators/cuad_<M>_corpus
```
`cuad_questions.json` = the CUAD question text per category, taken verbatim from `external/cuad_split/test.json`.
Output is one JSON line per (contract, category) with the n-best spans and probabilities.

## 3. What does NOT need a GPU but is blocked elsewhere
- The pure-LLM baseline rerun and Phase 2 LLM rule proposals need an LLM API key (**BLOCKED_API**).
