# Independent CUDA ticket transfer event timeline

This bundle retains upload/kernel/download CUDA-event attribution from clean
source commit `cbcc7fb2097a6562a497c75cd985403f2c751868`. It uses the same proof-bound full-domain CRAZY
workload as the streamed throughput comparison: 59,049 data words and 59,049
zero accumulators per ticket. Groups 2/4/8 submit all tickets and wait in reverse.

## Protocol and identity

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- structured output: `timeline.json`
- chronological group observations: `observations.csv`
- individual ticket phases: `phases.csv`
- source commit: `cbcc7fb2097a6562a497c75cd985403f2c751868`
- one warmup per group; 15 retained samples per group
- cyclic first-group rotation across groups 2/4/8; all samples retained
- event origin, preparation, CPU reference, validation, and origin destruction
  are outside retained wall intervals
- per-ticket event creation, elapsed queries, and destruction are timed
- overlap significance threshold: 0.001 ms
- exact prepared storage: `proof-bound-u32le-primitive-input-v1`
- exact kernel lifetime: `cuda-independent-stream-kernel-launch-v1`
- streamed transfer lifetime: `cuda-independent-stream-ticket-transfer-v1`
- phase timeline: `cuda-independent-stream-ticket-transfer-timeline-v1`
- workload SHA-256: `a523502c24560424c7139b527019e3f26ded512db205dec12a073e4801d7f7dc`
- `timeline.json` SHA-256: `1606e20465f248b04e633f1c49a879a9f117906b62647204f4cb1248b30df5f9`
- `observations.csv` SHA-256: `f5d8c5b15889a65544bc643e3e9ce95fba9bca6ee326fbd7558789228dd2f85a`
- `phases.csv` SHA-256: `5cdb3dd11d8a85b45eeb1e189125b7d39a29910c08a89272fb16810e165ab840`

## Environment

- host: Microsoft Windows 11 Pro 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA toolkit: 13.3.1 (`nvcc` 13.3.73)
- NVIDIA driver: 610.88
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Results

| Group | Wall median | Upload sum | Kernel sum | Download sum | Transfer/kernel overlap | Samples |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 3.4823 ms | 0.242848 ms | 0.082560 ms | 0.144064 ms | 0.000000 ms | 0/15 |
| 4 | 6.2380 ms | 0.477696 ms | 0.165408 ms | 0.288480 ms | 0.000000 ms | 0/15 |
| 8 | 12.9495 ms | 0.956352 ms | 0.340768 ms | 0.588512 ms | 0.000000 ms | 0/15 |

The preregistered group-eight hypothesis fails. No retained sample in any
group exceeds the one-microsecond transfer/kernel overlap threshold; all
upload/kernel, kernel/download, upload/download, and combined transfer/kernel
median intersections are exactly 0.000000 ms. Group eight records
1.885632 ms of summed device phases versus 12.9495 ms wall time,
or 0.146 of the complete instrumented interval.

## Interpretation boundary

This retained negative result establishes phase ordering and absence of observed
cross-ticket transfer/kernel event overlap for one deterministic workload on one
RTX 4060. It does not prove that CUDA hardware can never overlap copies and
kernels, nor does it identify one host operation as the entire residual cost.
Registration, allocation, Python/Driver orchestration, event management, result
construction, unregistration, and free are outside the three device phase sums
but remain inside wall time. The synchronous ticket stays the production default.
