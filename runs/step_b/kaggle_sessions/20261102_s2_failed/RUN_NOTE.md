# Kaggle Step B session 2 attempt (2 Nov 2026) - failed in setup, no inference run

Code fa055809. Failed about 4 minutes in, before any worker started: IsADirectoryError in the resume step.
Kaggle had unpacked each uploaded chunk_N/nbest.json.gz into a directory chunk_N/nbest.json/ holding the one
uncompressed file (checked: identical JSON to the committed session 1 outputs for all 136 chunks).
Fixed in the next commit: the resume step reads that file, checks it parses, and re-compresses it. Tested on the
layout downloaded from this failed session: 136/136 chunks recognised, all identical to the committed copies.
