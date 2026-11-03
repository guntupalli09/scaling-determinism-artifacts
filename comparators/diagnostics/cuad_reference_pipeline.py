"""
CUAD diagnostic (DIAG-CUAD-1): run the *reference* CUAD inference pipeline on a sample of test
contracts, so its n-best output can be compared question-by-question with our pre-registered
pipeline (comparators/cuad_qa.py).

This is a diagnostic tool. It changes no pre-registered result.

Reference = TheAtticusProject/cuad @ 67faa0e:
  * features: transformers' legacy squad_convert_examples_to_features (as train.py), slow tokenizer
    (train.py: use_fast=False), max_seq_length 512, doc_stride 256, max_query_length 64 (train.py
    default; run.sh does not override it);
  * model inputs: token_type_ids dropped for roberta-family models (as train.py evaluate());
  * post-processing: utils.compute_predictions_logits, unmodified (our external/cuad_utils.py is
    byte-identical to the repo's utils.py), n_best_size 20, max_answer_length 512,
    version_2_with_negative, null_score_diff_threshold 0.0, do_lower_case False.
--max-query-length lets one factor be isolated (e.g. 100000 = no question truncation).

    python cuad_reference_pipeline.py --model akdeniz27/roberta-base-cuad --titles-file sample.txt --out DIR
"""
import argparse
import importlib.util
import json
import os
import time
from pathlib import Path

import torch
from torch.utils.data import DataLoader
from transformers import AutoModelForQuestionAnswering, AutoTokenizer
from transformers.data.processors.squad import SquadResult, SquadV2Processor, squad_convert_examples_to_features

F = Path(__file__).resolve().parents[2]
ROBERTA_FAMILY = ("xlm", "roberta", "distilbert", "camembert", "bart", "longformer")


def load_reference_utils():
    spec = importlib.util.spec_from_file_location("cuad_utils", F / "external" / "cuad_utils.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    titles = [t.strip() for t in open(a.titles_file, encoding="utf-8") if t.strip()]
    test = json.load(open(F / "external/cuad_split/test.json", encoding="utf-8"))
    # compare stripped titles: two test titles end in a space, which a one-per-line titles file loses
    sub = {"version": test.get("version", "v1"), "data": [d for d in test["data"] if d["title"].strip() in titles]}
    assert len(sub["data"]) == len(titles), "unknown title in sample"
    sub_path = out / "sample_test.json"
    sub_path.write_text(json.dumps(sub))

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(a.model, use_fast=False)
    model = AutoModelForQuestionAnswering.from_pretrained(a.model).eval().to(device)
    examples = SquadV2Processor().get_dev_examples(str(out), filename=sub_path.name)
    t0 = time.time()
    features, dataset = squad_convert_examples_to_features(
        examples=examples, tokenizer=tok, max_seq_length=512, doc_stride=256,
        max_query_length=a.max_query_length, is_training=False, return_dataset="pt", threads=getattr(a, "threads", 1))
    results = []
    for batch in DataLoader(dataset, batch_size=a.batch_size):
        batch = tuple(t.to(device) for t in batch)
        inputs = {"input_ids": batch[0], "attention_mask": batch[1], "token_type_ids": batch[2]}
        if model.config.model_type in ROBERTA_FAMILY:
            del inputs["token_type_ids"]
        with torch.inference_mode():
            o = model(**inputs)
        for i, fi in enumerate(batch[3]):
            f = features[fi.item()]
            results.append(SquadResult(int(f.unique_id), o.start_logits[i].float().cpu().tolist(),
                                       o.end_logits[i].float().cpu().tolist()))
    ref = load_reference_utils()
    ref.compute_predictions_logits(sub, examples, features, results, 20, 512, False,
                                   str(out / "predictions_.json"), str(out / "nbest_predictions_.json"),
                                   str(out / "null_odds_.json"), False, True, 0.0, tok)
    meta = {"model": a.model, "titles": titles, "questions": len(examples), "features": len(features),
            "max_query_length": a.max_query_length, "device": device, "seconds": round(time.time() - t0, 1),
            "torch": torch.__version__, "transformers": __import__("transformers").__version__}
    (out / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--titles-file", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--max-query-length", type=int, default=64)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--threads", type=int, default=1, help="feature-conversion worker processes (same output)")
    main(p.parse_args())
