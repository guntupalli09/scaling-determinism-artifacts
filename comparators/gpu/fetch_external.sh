#!/bin/bash
# Fetch the comparator inputs on a fresh machine and verify them against the hashes used in this study.
# Run from experiments/followup/. Any hash mismatch aborts: do not run Step A on different data.
set -euo pipefail
mkdir -p external
curl -fL --retry 5 --connect-timeout 60 --speed-limit 100000 --speed-time 300 -o external/cuad_data.zip    https://raw.githubusercontent.com/TheAtticusProject/cuad/main/data.zip
curl -fL --retry 5 --connect-timeout 60 --speed-limit 100000 --speed-time 300 -o external/contract-nli.zip https://stanfordnlp.github.io/contract-nli/resources/contract-nli.zip
curl -fL --retry 5 --connect-timeout 60 --speed-limit 100000 --speed-time 300 -o external/cuad_evaluate.py https://raw.githubusercontent.com/TheAtticusProject/cuad/main/evaluate.py
curl -fL --retry 5 --connect-timeout 60 --speed-limit 100000 --speed-time 300 -o external/CUAD_v1.zip      https://zenodo.org/api/records/4595826/files/CUAD_v1.zip/content   # needed by build_corpus.py (contract types)
curl -fL --retry 5 --connect-timeout 60 --speed-limit 100000 --speed-time 300 -o external/cuad_utils.py      https://raw.githubusercontent.com/TheAtticusProject/cuad/67faa0e6023b04fcaae6cc09497ab00e5d63a2a2/utils.py  # reference post-processing (diagnostics)
curl -fL --retry 5 --connect-timeout 60 --speed-limit 100000 --speed-time 300 -o external/category_descriptions.csv https://raw.githubusercontent.com/TheAtticusProject/cuad/main/category_descriptions.csv  # read by evaluate.py
unzip -q -o external/cuad_data.zip -d external/cuad_split || [ $? -eq 1 ]   # exit 1 = warnings only (e.g. non-ASCII file names); the sha256 check below guards the data
unzip -q -o external/contract-nli.zip -d external || [ $? -eq 1 ]   # exit 1 = warnings only (e.g. non-ASCII file names); the sha256 check below guards the data
unzip -q -o external/CUAD_v1.zip -d external/cuad || [ $? -eq 1 ]   # exit 1 = warnings only (e.g. non-ASCII file names); the sha256 check below guards the data
sha256sum -c comparators/gpu/EXTERNAL.sha256
