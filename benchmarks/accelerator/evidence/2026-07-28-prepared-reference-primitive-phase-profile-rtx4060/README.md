# Prepared CPU-reference primitive phase profile

This directory retains the exact subphase profile after prepared validation changed
from whole-buffer broadword domain arithmetic to byte equality against immutable CPU
truth generated once during preparation. Incorrect values inside the legal classic
domain are now rejected, not merely domain-checked.

The run used clean source commit
`a5c85767bf8038cc27e281144220094be06630de`, one warmup, and 15 retained profiles.
Visible residuals account for public-layer orchestration; coverage is 100% by
construction and every residual remains explicit in raw output.

## Protocol

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- raw profiles: `raw.csv`
- structured output: `phases.json`
- `phases.json` SHA-256: `8d7517238c025529cf4b63f90cb17fc031ed1fd10b4b319dde09f10d3846477b`
- `raw.csv` SHA-256: `64239cb58462b0b1a56f981bbf73cd2f259f62cfa79deb76d79efa5ab52d528d`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1, repository-pinned toolkit
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Proof identity

- exact CPU equality: true
- prepared validator: `cpu-reference-packed-equality-v1`
- prepared reference words: 59049
- coverage: median/min/max 100.0%/100.0%/100.0%
- CUDA builds/evaluations/packed/reuses: 1/16/16/15

## Median phase result

| Layer | Phase | Broadword baseline | CPU-reference equality | Baseline/current |
| --- | --- | ---: | ---: | ---: |
| CUDA | Layer total | 0.1965 ms | 0.1573 ms | 1.249x |
| Validation | Layer total | 0.6558 ms | 0.0278 ms | 23.590x |
| Combined | End-to-end | 0.8684 ms | 0.1935 ms | 4.488x |

Active medians are launch/sync 0.0437 ms,
D-to-H 0.0837 ms, immutable bytes
0.0281 ms, contract
0.0020 ms, exact compare
0.0180 ms, and result construction
0.0032 ms.

Validation improves **23.590x** and end-to-end improves
**4.488x**, so the preregistered hypothesis passes.

## Interpretation boundary

The one-time CPU-reference generation is excluded and consumes 236,196 bytes for
this workload. This optimization applies only to reusable prepared state. Ordinary
results retain broadword validation, and proposal acceptance remains verifier-only.
