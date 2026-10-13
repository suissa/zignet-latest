# ZigNet Zig 0.16.0 migration seed dataset

This directory contains **50 seed records for each change category** in the Zig 0.15.x → 0.16.0 migration catalog. The files preserve `instruction`, `input`, `output` and provenance/quality metadata.

## Important validation status

All records are explicitly marked `compiler_validated: false` and `validation_status: "snippet_only"`. They are not yet suitable for direct fine-tuning. Some are scaffolds that must be replaced with precise API examples and standalone harnesses. Do not report these as compiler-verified examples.

## Files and counts

- One JSONL file per migration category, 50 records each.
- `manifest.json`: coverage, sources, limitations and validation policy.
- `dataset-stats.json`: counts and validation status.

## Required next step

Compile legacy examples with a pinned Zig 0.15.x compiler and target examples with Zig 0.16.0; run `zig fmt`, tests/builds, schema validation, semantic deduplication, leakage checks, and human review. Split by scenario family before augmentation. Use actual package fingerprints and verify all 0.16 API signatures from the standard library/release notes.

Official source: https://ziglang.org/download/0.16.0/release-notes.html
