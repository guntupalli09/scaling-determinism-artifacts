#!/bin/bash
# CUAD comparators on a CUDA machine. Protocol: Step A (reproduce Table 2) -> only if STEP_A_PASS, Step B/C.
# Usage: bash run_cuad_gpu.sh <model-key>   where model-key in {roberta-base, roberta-large, deberta-v2-xlarge}
# Run from experiments/followup/ in a checkout of the research branch, after build_corpus.py has regenerated corpus/texts.
set -euo pipefail
KEY="$1"
case "$KEY" in
  roberta-base) M=akdeniz27/roberta-base-cuad ;;
  roberta-large) M=akdeniz27/roberta-large-cuad ;;
  deberta-v2-xlarge) M=akdeniz27/deberta-v2-xlarge-cuad ;;
  *) echo "unknown model key"; exit 1 ;;
esac
OUT=runs/comparators/cuad_${KEY}_gpu
python -c "import torch; assert torch.cuda.is_available(), 'no CUDA device'"
# Step A (resumable; decoding settings frozen in comparators/cuad_qa.py)
python comparators/cuad_qa.py validate --model "$M" --test-json external/cuad_split/test.json --out "$OUT"
# Pre-registered scorer (official evaluate.py; tolerance fixed in cuad_step_a.py, commit 09e7990f). Exit 2 = incomplete.
python comparators/cuad_step_a.py --pred-dir "$OUT" --model "$KEY"
STATUS=$(python -c "import json;print(json.load(open('$OUT/step_a_result.json'))['status'])")
if [ "$STATUS" != "STEP_A_PASS" ]; then echo "Step A: $STATUS -> stop. Report the discrepancy; do not tune."; exit 3; fi
# Step B/C: our frozen corpus, all 41 CUAD questions, per (contract, category) n-best preserved
python comparators/cuad_qa.py corpus --model "$M" --questions comparators/cuad_questions.json \
    --manifest corpus/manifest.csv --texts corpus/texts --out "${OUT}_corpus"
# Paired evaluation on the CUAD test slice (engine vs model, identical units, exact McNemar)
cd ../.. && python -m experiments.followup.evaluate_paired v7.2.0 --cuad-model-dir "experiments/followup/$OUT"
