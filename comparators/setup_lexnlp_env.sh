#!/bin/bash
# Reproducible LexNLP 2.3.0 environment (Phase 3 rule-based comparator).
# Root cause of the Day 1 failure: LexNLP's amount/duration/money parsers call
# locale.setlocale('en_US'); without that system locale the call raises inside LexNLP,
# the error is swallowed, and every digit-based amount is silently dropped.
set -e
localedef -i en_US -f UTF-8 en_US.UTF-8           # required system locale (container-level; redo after restart)
uv python install 3.8
uv venv -p 3.8 /home/user/venvs/lexnlp
VIRTUAL_ENV=/home/user/venvs/lexnlp uv pip install "lexnlp==2.3.0" "scikit-learn==0.24"   # documented pins
/home/user/venvs/lexnlp/bin/python -c "import nltk; [nltk.download(p, quiet=True) for p in ['punkt','averaged_perceptron_tagger','wordnet','stopwords','maxent_ne_chunker','words','omw-1.4']]"
