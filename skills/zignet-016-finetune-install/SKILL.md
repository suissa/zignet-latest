---
name: zignet-016-finetune-install
description: Install and verify the software stack required to QLoRA fine-tune the ZigNet Qwen2.5-Coder-7B model on a GPU or in Colab.
---

# Skill: Install and prepare ZigNet fine-tuning

## Goal

Prepare an isolated Python environment for LoRA/QLoRA fine-tuning of `fulgidus/zignet-qwen2.5-coder-7b` (confirm its base-model architecture/config before training). Prefer a compatible Instruct checkpoint and chat template. Do not assume a GGUF quantized inference file is a valid Transformers training checkpoint.

## Recommended environment

- Python 3.10 or 3.11
- PyTorch build matching the available CUDA runtime
- `transformers`, `datasets`, `accelerate`, `peft`, `trl`, `bitsandbytes`, `safetensors`, `huggingface_hub`
- Optional `sentencepiece` if the tokenizer requires it
- Git and enough disk for model weights, cache, checkpoints and adapter
- Zig 0.16.0 separately, for data validation (not required for GPU training itself)

## Installation workflow

1. Inspect GPU, driver, Python and free disk/RAM. Stop if the hardware budget is already exceeded.
2. Create a virtual environment; do not upgrade system Python packages.
3. Install a PyTorch wheel compatible with the host CUDA/driver according to the official PyTorch selector.
4. Install the Hugging Face packages in a pinned requirements file after verifying mutual compatibility.
5. Run an import smoke test and `torch.cuda.is_available()`. If false on a GPU target, stop and diagnose rather than silently training on CPU.
6. Load tokenizer and model config from the exact intended training checkpoint. Verify tokenizer/chat template and license.
7. Test loading the base model in 4-bit NF4 with double quantization and BF16 compute when supported, otherwise FP16.
8. Test one forward/backward step on a tiny batch, then clear the cache.
9. Record versions, model revision, dataset manifest hash, GPU name, peak VRAM and training configuration.
10. Only then launch full training.

## General QLoRA defaults

- 4-bit NF4 quantization, double quantization.
- LoRA target modules must be discovered from the model architecture; common Qwen targets include attention projections and MLP projections, but inspect module names before configuring.
- Start with rank 8 or 16, alpha 16 or 32, dropout 0.05.
- Microbatch 1, gradient accumulation 8–16, gradient checkpointing enabled.
- Sequence length 1024 initially; increase only after measuring VRAM.
- Learning rate around 1e-4 to 2e-4 is a starting point, not a universal optimum.
- Use a small pilot, evaluation, and early stopping rather than blindly running many epochs.
- Save adapter checkpoints, not full model weights, unless there is a specific reason.
- Keep a held-out test set and compare base model vs adapter on identical prompts.

## Security and reproducibility

- Never commit Hugging Face tokens or secrets.
- Do not run untrusted repository scripts as root.
- Pin the model revision and dependency versions for a final experiment.
- Store training logs and metrics without private prompt data.
- If a dependency changes, rerun the smoke test and document the change.

## Output

Create a run directory containing config, package versions, model revision, dataset manifest hash, logs, evaluation metrics, adapter weights and a short model card. The output adapter should be loadable with PEFT and should identify the base model explicitly.
