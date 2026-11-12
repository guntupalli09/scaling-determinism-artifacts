# Quarantined: LexNLP Day 1 output (INVALID — environment failure, not a performance score)

- Symptom: `durations` and `money` returned no entities even on canonical inputs
  ("This term shall continue for 3 years." -> []), so every category using them read as "absent".
- Root cause (found 2026-10-17): `lexnlp.utils.amount_delimiting.infer_delimiters` switches to the
  `en_US` system locale; the container had only C/C.utf8/POSIX, `locale.setlocale` raised
  `locale.Error: unsupported locale setting`, LexNLP swallowed it, and all digit-based amounts were dropped.
  Traceback captured in the Day 2 session; reproduce by removing the en_US.UTF-8 locale.
- Repair: `localedef -i en_US -f UTF-8 en_US.UTF-8` (see comparators/setup_lexnlp_env.sh), sklearn restored to
  the documented pin 0.24. Sanity validation then passes for dates/durations/money/amounts
  (runs/comparators/lexnlp_sanity/).
- These predictions are retained only as diagnostic evidence and must never be scored.
