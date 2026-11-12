# ContractNLI environment / code-path smoke test (CPU)

**Purpose:** catch install and code-path failures before spending free GPU quota. **This is not an experiment.**
- It uses a handful of documents and 4 optimisation steps on CPU.
- Its metrics are meaningless, and no number from it is reported anywhere.
- The STEP_A_FAIL below is expected from an essentially untrained model; it only shows that the checker runs.

Setup:
- micromamba Python 3.8.20, the authors' code at `058c56f`;
- the authors' `requirements.txt`, with the CPU build `torch==1.8.1+cpu`; the Kaggle run uses the GPU build
  `1.8.1+cu111`.

Smoke-only configs (never used on Kaggle):
- `conf_smoke.yml` = `conf_base.yml` with `num_epochs: null`, `max_steps: 4`, `valid_steps: 2`;
- `conf_smoke2.yml` = the same, plus `dev_file: null` and `early_stopping: false`.

| Check | Result |
|---|---|
| Python 3.8 + authors' pins install | **OK** after two pins of unpinned transitive dependencies, both added to `phase3_driver.py` and declared in the report: `packaging==20.9` (transformers 4.5.1's version check crashes under packaging ≥ 22) and `protobuf==3.20.3` (tensorboard 2.4.1 breaks under protobuf ≥ 4) |
| `import torch, transformers, sklearn, numpy` | **OK**: 1.8.1+cpu, 4.5.1, 0.24.1, 1.20.1 |
| `train.py` training steps | **OK**: features built, 4 optimisation steps run |
| `train.py` dev evaluation (`valid_steps`) | **Not testable here.** Killed by the kernel OOM (exit 137): host RAM rose from 13.9 to 14.7 GB of 16 GB within ~3 s of dev evaluation starting, reproducibly. The authors' `Trainer.evaluate` runs forward passes without `torch.no_grad()`. On Kaggle the model and activations live on the 16 GB T4, as on the authors' 16 GB GPUs, so this CPU limit does not carry over. **It is still untested, and the first GPU run is its first real test.** |
| `train.py` without dev evaluation → model saved | **OK** (exit 0): `pytorch_model.bin`, `conf.yml`, tokenizer files |
| `test.py` → `result.json`, `metrics.json` | **OK** (exit 0) on 2 test documents that together mention all 17 hypotheses |
| `test.py` on 2 arbitrary documents | KeyError in the authors' `evaluate_all`. It needs every hypothesis to be mentioned in at least one document, a subset artefact: in the full 123-document test split every hypothesis is mentioned in ≥ 13 documents |
| Pre-registered `contractnli_step_a.py` key paths | **All three resolve**: `macro_label_micro_doc.class.accuracy`, `macro_label_micro_doc.class.f1_entailment`, `micro_label_micro_doc.span.map` (no INCONCLUSIVE) |
| `result.json` shape vs `pair_contractnli.py` | **Matches**: a list of documents with `file_name` and `annotation_sets[0].annotations[<hyp>].choice` |

Discarded attempts:
- A container restart relaunched an earlier smoke command, so two runs collided in one directory.
- One memory sampler tracked the wrong PID.

Neither produced any result that is used.
