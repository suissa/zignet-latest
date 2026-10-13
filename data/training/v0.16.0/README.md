# ZigNet Zig 0.16.0 training data

This directory is the target for synthetic examples generated under `skills/zignet-016-synthetic-data/SKILL.md`. The directory did not previously exist at the time this README was authored; existing files in `data/training/` remain untouched.

## Expected files

- `dataset-train.jsonl`
- `dataset-validation.jsonl`
- `dataset-test.jsonl`
- `dataset-stats.json`
- `manifest.json`
- optional `validation/` compiler logs

Each JSONL record should preserve the existing `instruction`, `input`, `output` fields and add structured `metadata` for provenance and quality gates.

## Scope

Only teach verified Zig 0.16.0 changes relative to the closest applicable 0.15.x behavior. Record the exact old compiler version when an old-code sample is compiled. Never label unrun examples as compiler-validated.

## Split policy

Split by scenario/template family before augmentation to prevent near-identical examples leaking between train, validation and test. Suggested initial split: 80/10/10. For a tiny corpus, keep a manually curated test set that is never used to tune generation prompts.

## Do not assume files already exist

The initial directory may contain only this README. The Colab notebook validates the paths and reports counts before training. It must not silently substitute the existing 0.13–0.15 dataset for missing 0.16 data.
