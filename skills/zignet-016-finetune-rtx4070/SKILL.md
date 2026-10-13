---
name: zignet-016-finetune-rtx4070
description: Run ZigNet 0.16 QLoRA fine-tuning on an RTX 4070 12 GB VRAM with a strict 20 GB system-RAM budget.
---

# Skill: Fine-tune with RTX 4070 12 GB VRAM

## Hard resource budget

Target hardware: RTX 4070 with 12 GB VRAM, 64 GB installed RAM, but the training process must stay within 20 GB host RAM. Use a process/container memory limit where possible. Do not assume the full 64 GB is available.

## Configuration

- QLoRA 4-bit NF4 + double quantization.
- Microbatch 1.
- Gradient accumulation 16 (effective batch 16 unless distributed).
- Sequence length 512 for first pilot; 1024 only after measured headroom.
- Gradient checkpointing on; `use_cache=False`.
- LoRA rank 8 initially, alpha 16, dropout 0.05.
- BF16 only if the GPU/PyTorch reports support; otherwise FP16.
- DataLoader workers 0–2; avoid caching tokenized data entirely in RAM.
- Stream/prepare JSONL on disk; use bounded preprocessing.
- Save adapter every 100–250 steps and keep only 2–3 checkpoints.
- Start with 50–200 training examples and 10–30 evaluation examples for a smoke run; then scale.

## Procedure

1. Read the shared setup skill and inspect the actual model architecture and template.
2. Verify `nvidia-smi`, CUDA, free VRAM, host memory and disk.
3. Set `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` if supported by the installed PyTorch.
4. Run a one-batch load/forward/backward test. Measure peak GPU and process RAM.
5. If VRAM exceeds 10.5 GB or host RSS exceeds 18 GB, reduce sequence length first; then reduce LoRA rank / optimizer overhead and disable workers.
6. Train with gradient checkpointing and frequent adapter-only checkpoints. Do not load a second copy of the model for evaluation; evaluate sequentially.
7. Monitor `nvidia-smi`, process RSS, disk space, loss and validation loss.
8. Stop if the process exceeds 20 GB host RAM, OOM repeats, validation loss diverges, or the model starts regressing on non-0.16 Zig tasks.
9. Evaluate on compiler-validated held-out migration tasks and a small general Zig regression set.
10. Export PEFT adapter + run metadata. Merge into full weights only if RAM/disk allow and there is a deployment need.

## Expected limitations

7B QLoRA on 12 GB VRAM is tight and configuration-sensitive; 512-token sequences and batch 1 are the safe starting point, not a guarantee. A 7B model is not a realistic full-fine-tuning target on this GPU. Use adapter training only and measure peak memory before committing to a long run.
