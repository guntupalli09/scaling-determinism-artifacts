"""
Corrected CUAD diagnostic run (DIAG-CUAD-2): the reference CUAD inference pipeline
(cuad_reference_pipeline.py), applied to the full CUAD test split in resumable chunks of contracts.

Its output is merged into nbest_partial.jsonl (the format of the pre-registered run) and scored with the
UNCHANGED pre-registered scorer, comparators/cuad_step_a.py, with the same thresholds.

Why this pipeline: on a fixed-seed 3-contract sample (123 questions) it reproduces the authors' own
released test predictions (Zenodo record 4599830, roberta-base nbest_predictions_.json) exactly:
123/123 top answers and identical probabilities. Our pre-registered pipeline matches only 89/123.
See review_package/PHASE3_DIAGNOSTIC_REPORT.md.

The result is a CORRECTED DIAGNOSTIC RUN. It never replaces the pre-registered Step A result.

    python cuad_reference_full.py --model akdeniz27/roberta-base-cuad --out DIR [--chunk 4]
"""
import argparse
import json
import os
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
F = HERE.parents[1]
sys.path.insert(0, str(HERE))
import cuad_reference_pipeline as ref  # noqa: E402


def main(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    titles = [d["title"] for d in json.load(open(F / "external/cuad_split/test.json", encoding="utf-8"))["data"]]
    chunks = [titles[i:i + a.chunk] for i in range(0, len(titles), a.chunk)]
    for n, chunk in enumerate(chunks):
        cdir = out / f"chunk_{n:03d}"
        if (cdir / "nbest_predictions_.json").exists():
            continue                      # finished chunk: resume past it
        cdir.mkdir(exist_ok=True)
        (cdir / "titles.txt").write_text("\n".join(chunk) + "\n")
        ref.main(types.SimpleNamespace(model=a.model, titles_file=str(cdir / "titles.txt"), out=str(cdir),
                                       max_query_length=64, batch_size=a.batch_size,
                                       threads=a.threads))
        (cdir / "sample_test.json").unlink(missing_ok=True)
        print(f"[{n + 1}/{len(chunks)}] chunk done", flush=True)
    merged = {}
    for cdir in sorted(out.glob("chunk_*")):
        merged.update(json.load(open(cdir / "nbest_predictions_.json")))
    with open(out / "nbest_partial.jsonl", "w") as fh:
        for qid, nb in merged.items():
            fh.write(json.dumps({"id": qid, "nbest": [{"text": x["text"], "probability": x["probability"]}
                                                       for x in nb]}) + "\n")
    print(f"merged {len(merged)} questions -> {out / 'nbest_partial.jsonl'}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--chunk", type=int, default=4)
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--threads", type=int, default=os.cpu_count() or 1)
    main(p.parse_args())
