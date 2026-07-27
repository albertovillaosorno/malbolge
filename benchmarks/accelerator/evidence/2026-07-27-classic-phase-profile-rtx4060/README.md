# Resident classic CUDA phase-profile evidence

This directory retains the pre-optimization phase decomposition that explains
why larger resident batches did not improve end-to-end throughput.

## Provenance

- source commit: `9ed6e9b994392be4c8e75d9783baded80da50dbf`
- platform: Windows x86-64
- Python: 3.14.6, repository-pinned wrapper
- CUDA: 13.3 Update 1, repository-pinned redistributables
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`)
- samples: 15 per batch size
- batch sizes: 1, 8, 32, 128
- workload: 64 committed no-op transitions per classic VM
- `phases.json` SHA-256: `edf9c58a8cc793e707ee94d497c7c40e7f72a73b29897b649d141bc6849b4292`

## Result

Median phase share of total wall time:

| Batch | Total ns | Validate/plan | Host build | Decode | Kernel+sync |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 32,951,200 | 31.39% | 37.59% | 27.81% | 0.2170% |
| 8 | 287,277,100 | 29.26% | 39.17% | 30.98% | 0.0291% |
| 32 | 1,143,321,000 | 29.08% | 39.16% | 30.11% | 0.0283% |
| 128 | 4,698,614,500 | 28.59% | 39.16% | 30.00% | 0.0097% |

At batch 128, kernel execution plus synchronization is only
0.0097% of total wall time.
Validation/planning, Python host-buffer construction, and Python result decoding
consume approximately
97.76% combined.
Upload and download are also small relative to those host-side phases.

This establishes a bottleneck location, not merely a correlation: optimizing
kernel occupancy or increasing batch size cannot materially fix the measured
end-to-end path while the host representation work dominates by orders of
magnitude. The next optimization should remove redundant full-memory validation
and Python integer flatten/decode work before attempting CUDA kernel tuning.

## Integrity boundary

`profile_evaluate()` runs the same resident CUDA transition path and a dedicated
test requires its exact result to equal ordinary `evaluate()`. The diagnostic
clocking itself is not a correctness authority; Rust/Python differential tests
remain the semantic authority.
