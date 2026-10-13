---
name: zignet-016-finetune-cpu
description: Assess CPU-only adapter training under a strict 1 vCPU and 1 GB RAM VPS budget and choose safe alternatives.
---

# Skill: CPU-only training under 1 vCPU / 1 GB RAM

## Hard constraint and honest feasibility

The VPS may use at most 70% of 1 GB RAM (about 700 MB) and one vCPU. **QLoRA fine-tuning a 7B model is not feasible within this budget.** Even quantized model loading, optimizer state, activations and Python libraries exceed the memory ceiling by a wide margin. Do not attempt to load the 7B checkpoint on this host.

## Allowed workflow on the VPS

1. Run only lightweight orchestration: validate JSONL line-by-line, schema-check, deduplicate by hash, compute dataset manifests, upload shards, and collect worker status.
2. Enforce a cgroup/systemd memory limit near 700 MB and low CPU priority. Check actual host memory accounting; leave headroom for the OS/SSH.
3. Use streaming reads; never load the whole dataset into memory.
4. Do not install PyTorch/Transformers on the 1 GB orchestrator unless specifically tested to fit; prefer a small standard-library Python validator.
5. Store only metadata and small shard manifests locally. Keep training artifacts in external object storage or a separate machine.

## If training must be CPU-only

Use a substantially larger CPU machine for actual training. A practical 7B full-model or even adapter-training footprint is far beyond 1 GB; exact requirements depend on quantization and backend. For CPU-only experiments, begin with a smaller model (for example a 0.5B–1.5B model) and a host with several to tens of GB RAM, then benchmark.

## Can N VPSs with 1 vCPU / 1 GB be combined?

Not by simply training separate copies and merging adapters. LoRA updates are coupled to the same base model and optimizer trajectory; averaging independently trained adapters is not equivalent to one distributed training run and may reduce quality.

True distributed training requires a framework with synchronized gradients/optimizer states, communication overhead, compatible model sharding and memory per worker. At 1 vCPU/1 GB, network and RAM overhead make 7B training impractical. Splitting the dataset among N VPSs and training N independent adapters does not magically pool RAM/VRAM.

## Recommended distributed design

- Keep the 1 GB VPSs as stateless data-generation/validation workers.
- Partition tasks by `change_id`; each worker creates/validates examples and writes a shard plus manifest.
- Merge data shards deterministically, deduplicate and run global schema/split checks.
- Run one QLoRA training job on the RTX 4070, Google Colab GPU or a larger rented GPU.
- If CPU training is mandatory, use a larger-memory CPU server and test a smaller model first.

## Acceptance gates

Refuse to start model loading if estimated or measured memory exceeds 700 MB. Do not claim distributed training support unless a real synchronized distributed run has been tested. Keep data generation, dataset validation and model training as separate tasks.
