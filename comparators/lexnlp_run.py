"""
Phase 3 rule-based comparator: LexNLP 2.3.0 (lexpredict-lexnlp).

Runs in a Python 3.8 virtualenv with scikit-learn 0.23.1 (the version LexNLP's
pickled date model was trained with). Imports nothing from the repo.

LexNLP extracts typed entities rather than clauses. A CUAD category is predicted
present when the configured extractor returns at least one entity inside a sentence
matching the category's trigger regex (comparators/label_mapping.json, "lexnlp").
That adaptation is ours and is documented as such. Governing Law is excluded: its
geo-entity dictionary (lexpredict-legal-dictionary) is no longer at its published URL.

  python lexnlp_run.py --mapping label_mapping.json --manifest ../corpus/manifest.csv \
      --texts ../corpus/texts --slices cuad_test --out ../runs/comparators/lexnlp
"""
import argparse
import csv
import json
import re
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

from lexnlp.extract.en import dates, durations, money  # noqa: E402
from lexnlp.nlp.en.segments.sentences import get_sentence_span_list  # noqa: E402

EXTRACTORS = {
    "dates": lambda s: list(dates.get_dates(s)),
    "durations": lambda s: list(durations.get_durations(s)),
    "money": lambda s: list(money.get_money(s)),
}


def run(args):
    sanity = json.load(open(args.sanity))["extractors"]
    passing = {k for k, v in sanity.items() if v["status"] == "PASS"}
    mapping = {k: v for k, v in json.load(open(args.mapping))["lexnlp"].items()
               if not k.startswith("_") and v["extractor"] in EXTRACTORS and v["extractor"] in passing}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "scored_categories.json").write_text(json.dumps({"sanity_file": args.sanity, "passing_extractors": sorted(passing),
                                                            "categories": sorted(mapping)}, indent=2))
    rows = [r for r in csv.DictReader(open(args.manifest, encoding="utf-8"))
            if not args.slices or r["slice"] in args.slices]
    path = out / "predictions.jsonl"
    done = set()
    if path.exists():
        done = {json.loads(l)["doc_id"] for l in open(path, encoding="utf-8")}
    t0 = time.time()
    with open(path, "a", encoding="utf-8") as fh:
        for i, r in enumerate(rows, 1):
            if r["doc_id"] in done:
                continue
            text = (Path(args.texts) / f"{r['doc_id']}.txt").read_text(encoding="utf-8")
            spans = get_sentence_span_list(text)
            preds = {}
            for cat, cfg in mapping.items():
                trig = re.compile(cfg["trigger"], re.I | re.S)
                hits = []
                for s0, s1, *_ in spans:
                    sent = text[s0:s1]
                    if not trig.search(sent):
                        continue
                    try:
                        ents = EXTRACTORS[cfg["extractor"]](sent)
                    except Exception:
                        ents = []
                    if ents:
                        hits.append({"start": s0, "end": s1, "entities": [str(e) for e in ents][:5]})
                preds[cat] = {"present": bool(hits), "evidence": hits[:3]}
            fh.write(json.dumps({"doc_id": r["doc_id"], "slice": r["slice"], "predictions": preds}) + "\n")
            fh.flush()
            if i % 10 == 0:
                print(f"[{i}/{len(rows)}] {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--mapping", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--texts", required=True)
    p.add_argument("--slices", nargs="*")
    p.add_argument("--out", required=True)
    p.add_argument("--sanity", required=True, help="sanity.json from lexnlp_sanity.py; only PASSING extractors are scored")
    run(p.parse_args())
