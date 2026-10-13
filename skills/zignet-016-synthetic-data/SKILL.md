---
name: zignet-016-synthetic-data
description: Generate compact, semantically diverse, compiler-validated training examples for migrating Zig 0.15 code to Zig 0.16.
---

# Skill: Generate Zig 0.16 synthetic training data

## Objective

Populate `data/training/v0.16.0/` with high-signal examples focused on real Zig 0.15 → 0.16 changes. Prefer semantic coverage over raw volume. Never invent an API or claim compiler validation without recorded evidence.

## Sources of truth

1. Read `docs/zig-0.15-to-0.16-migration-catalog.md`.
2. Use official 0.16 release notes and matching stdlib/build-system documentation.
3. Inspect existing dataset files and schema in `data/training/` before writing. Preserve compatible fields when possible; version new schema explicitly.
4. Confirm each behavior using the pinned Zig 0.16.0 compiler. When comparing legacy code, use a pinned 0.15.x compiler.

## Workflow

1. Inventory the current training directory, record file names, formats, counts, and schemas. Never overwrite the existing 0.13–0.15 corpus.
2. Create a change registry. Every change has a stable `change_id`, source URL/section, baseline version, target version, severity, and validation strategy.
3. Generate scenario plans before code. For each change list user intents, input contexts, edge cases, invalid patterns, and alternative idiomatic implementations.
4. Draft concise examples. Each example should teach one primary concept; allow a second concept only when their interaction is the point.
5. Use contrastive pairs when meaningful: old code + migration request + corrected code + brief reason. Do not train the model to emit obsolete APIs as the answer.
6. Validate code using Zig 0.16.0. If the sample requires a project harness, generate the harness and validate it. Use Zig 0.15.x only for the old side of a migration pair.
7. Run `zig fmt`, tests/builds, duplicate checks, schema checks and leakage checks.
8. Split by scenario family/template before expanding variants. Keep the test split isolated from prompt templates and near-duplicates.
9. Write JSONL and a manifest with counts, versions, hashes, validation rates and known limitations.
10. Review a sample manually and stop if the compiler version or API evidence is uncertain.

## Example schema

Use one JSON object per line. The preferred instruction-tuning shape is:

```json
{
  "instruction": "Migrate this Zig 0.15 code to Zig 0.16 and explain the required API changes.",
  "input": "…old code and task context…",
  "output": "…correct migrated code, then a concise explanation…",
  "metadata": {
    "change_id": "io-explicit-instance",
    "version_from": "0.15.x",
    "version_to": "0.16.0",
    "task": "migration",
    "scenario": "file-read-error-cleanup",
    "compiler_validated": true,
    "compiler_version": "0.16.0",
    "validation_command": "zig test sample.zig",
    "source": "https://ziglang.org/download/0.16.0/release-notes.html#io-as-an-interface",
    "split_group": "io-file-read-cleanup-01"
  }
}
```

If the existing trainer only accepts `instruction/input/output`, preserve those top-level fields and leave metadata available to the data pipeline. Do not put unverified metadata in the model target text.

## Diversity requirements

For every significant change, aim initially for 20–40 *distinct scenarios*, not 20–40 superficial paraphrases. Expand to 50–150 only when validation and evaluation reveal useful coverage gaps. Cover:

- minimal and realistic examples;
- multiple type shapes and control-flow structures;
- success, failure, cleanup and boundary cases;
- explicit vs inferred types;
- API direct use and dependency injection;
- new code, migration, explanation, debugging and code review intents;
- examples that must be rejected, with the exact reason.

The number is a starting budget, not a claim that every feature needs the same sample count.

## Anti-patterns

- Renaming variables while retaining identical logic.
- Repeating one canonical example with trivial constant changes.
- Guessing function signatures from memory.
- Marking `compiler_validated=true` after only syntax highlighting or `zig fmt`.
- Mixing code from different Zig versions without labels.
- Splitting nearly identical variants across train and test.
- Teaching the model to claim a code sample compiles when it has not been run.
- Generating many examples from a single unverified AI-generated answer.

## Acceptance gates

A record is accepted only if it has a valid schema, a traceable change ID, a non-empty scenario, a version label, a deterministic validation result or an explicit `snippet_only` reason, and a unique normalized content hash. Failed examples may be retained only as intentional negative/diagnostic examples and must be labeled accordingly.

## Deliverables

- `dataset-train.jsonl`
- `dataset-validation.jsonl`
- `dataset-test.jsonl`
- `dataset-stats.json`
- `manifest.json` (change coverage, compiler versions, validation evidence and hashes)
- optional `validation/` logs, grouped by change ID
