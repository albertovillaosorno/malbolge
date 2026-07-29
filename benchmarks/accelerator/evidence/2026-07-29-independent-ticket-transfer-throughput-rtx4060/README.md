# Independent CUDA ticket transfer throughput

This bundle retains the preregistered synchronous-copy versus registered-stream
comparison from clean source commit `431f542ab6321eeb12b7bcb9195318f25cf376a5`. Every ticket evaluates the
same proof-bound full-domain CRAZY batch: 59,049 data words and 59,049 zero
accumulators. All fourteen routes preserve identical ticket counts and exact bytes.

## Protocol and identity

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- structured output: `throughput.json`
- raw chronological samples: `raw.csv`
- source commit: `431f542ab6321eeb12b7bcb9195318f25cf376a5`
- one warmup per route; 15 retained samples per route
- cyclic first-route rotation across 14 routes; all samples retained
- groups: 1, 2, 4, and 8 tickets
- preparation, CPU reference, CUDA/NVRTC setup, and validation are untimed
- exact prepared storage: `proof-bound-u32le-primitive-input-v1`
- exact kernel lifetime: `cuda-independent-stream-kernel-launch-v1`
- streamed transfer lifetime: `cuda-independent-stream-ticket-transfer-v1`
- workload SHA-256: `a523502c24560424c7139b527019e3f26ded512db205dec12a073e4801d7f7dc`
- `throughput.json` SHA-256: `edeed94f6ccca041d1db034ba7dfbc75c506e7c02069018c6f049d95e459916e`
- `raw.csv` SHA-256: `329716e4f429b7ab65096a61266af732b6630faf2bba2f66a643ea1b41d3214f`

## Environment

- host: Microsoft Windows 11 Pro 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA toolkit: 13.3.1 (`nvcc` 13.3.73)
- NVIDIA driver: 610.88
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Results

| Group | Sync sequential | Sync grouped | Streamed sequential | Streamed grouped | Streamed / sync grouped | Wins vs sync grouped |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1.4710 ms | n/a | 1.8794 ms | n/a | n/a | n/a |
| 2 | 1.7885 ms | 1.3863 ms | 3.3180 ms | 3.1791 ms | 0.436x | 0/15 |
| 4 | 3.8243 ms | 3.0611 ms | 6.7215 ms | 6.4038 ms | 0.478x | 0/15 |
| 8 | 7.4564 ms | 5.9408 ms | 13.4266 ms | 12.0138 ms | 0.494x | 0/15 |

The preregistered group-eight hypothesis fails. Streamed grouped execution is
1.118x faster than
streamed sequential with
14/15 paired
wins, but reaches 12.0138 ms versus
5.9408 ms for the synchronous grouped default. Its
same-run ratio is only
0.494x with 0/15
paired wins. The default therefore remains synchronous.

## Interpretation boundary

This is a retained negative performance result for one deterministic full-domain
CRAZY workload on one RTX 4060. It establishes exact opt-in transfer semantics but
does not promote registered transfers as the default. Registration,
unregistration, allocation, copies, kernel launch, synchronization, immutable
result construction, and free all remain inside wall time. No CUDA-event markers
attribute physical H-to-D/kernel/D-to-H overlap, and no cross-device, compiler,
synthesis, or broader-workload claim is made.
