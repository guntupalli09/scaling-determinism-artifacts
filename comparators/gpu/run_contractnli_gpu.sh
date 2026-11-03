#!/bin/bash
# ContractNLI Span NLI BERT (Koreeda & Manning 2021). No released weights -> train, then Step A, then pairing.
# Usage: bash run_contractnli_gpu.sh  (run from experiments/followup/)
set -euo pipefail
WORK=${WORK:-$HOME/contract-nli-bert}
[ -d "$WORK" ] || git clone https://github.com/stanfordnlp/contract-nli-bert "$WORK"
git -C "$WORK" checkout 058c56f
python -m venv "$WORK/.venv" && . "$WORK/.venv/bin/activate"
pip install -r "$WORK/requirements.txt"   # torch 1.7.1 / transformers 4.5.1 as pinned by the authors (install a CUDA build of torch matching your driver)
mkdir -p "$WORK/data" && cp external/contract-nli/{train,dev,test}.json "$WORK/data/"
python -c "import torch; assert torch.cuda.is_available(), 'no CUDA device'"
( cd "$WORK" && python train.py ./data/conf_base.yml ./output_base )            # single published base configuration, seed 42
( cd "$WORK" && python test.py ./output_base ./data/test.json ./output_base/test_ )  # writes test_result.json, test_metrics.json
deactivate
python comparators/gpu/contractnli_step_a.py --metrics "$WORK/output_base/test_metrics.json" --backbone bert-base \
    --out runs/comparators/contractnli_span_nli_bert_base_gpu
python comparators/gpu/pair_contractnli.py --result "$WORK/output_base/test_result.json" \
    --step-a runs/comparators/contractnli_span_nli_bert_base_gpu/step_a_result.json \
    --out runs/comparators/contractnli_span_nli_bert_base_gpu
