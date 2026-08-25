# Independent CUDA ticket event timeline

This bundle retains CUDA-event interval attribution from clean source commit
`8d4d8a481184e536e860d094511093981e9dd2d7`. It uses the exact workload from the prior grouped-throughput evidence:
one proof-bound full-domain CRAZY ticket contains 59,049 data words and 59,049 zero
accumulators. Groups 2/4/8 submit all tickets and wait in reverse order.

## Protocol and identity

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- structured output: `timeline.json`
- chronological group observations: `observations.csv`
- individual event intervals: `intervals.csv`
- source commit: `8d4d8a481184e536e860d094511093981e9dd2d7`
- one warmup per group; 15 retained samples per group
- cyclic first-group rotation across groups 2/4/8; all samples retained
- event origin, preparation, CPU reference, validation, and origin destruction are
  outside retained wall intervals
- overlap significance threshold: 0.001 ms
- exact prepared storage: `proof-bound-u32le-primitive-input-v1`
- exact kernel lifetime: `cuda-independent-stream-kernel-launch-v1`
- exact event timeline: `cuda-independent-stream-kernel-timeline-v1`
- workload SHA-256: `a523502c24560424c7139b527019e3f26ded512db205dec12a073e4801d7f7dc`
- `timeline.json` SHA-256: `f5d5d81d80aab653c67b6b59b94baf4a72fed989809a9b924def08f3d1f93326`
- `observations.csv` SHA-256: `27cfc82fb4c259df22ca894ad7a5f8c8d6e80dfe64e51f1d6cae0b275c5bfee2`
- `intervals.csv` SHA-256: `1ad4e58574f9d4233b75d04f3c904146f44902925351973aad0201a19817c904`

## Environment

- host: Microsoft Windows 11 Pro 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA toolkit: 13.3.1 (`nvcc` 13.3.73)
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Results

| Group | Wall median | Event span median | Event sum / union | Overlap median | Ratio | Samples with overlap | Max peak |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 2.0268 ms | 0.410624 ms | 0.013504 / 0.013344 ms | 0.000000 ms | 1.000x | 2/15 | 2 |
| 4 | 3.5078 ms | 1.270784 ms | 0.083968 / 0.073728 ms | 0.006144 ms | 1.072x | 8/15 | 3 |
| 8 | 6.2840 ms | 3.014656 ms | 0.165152 / 0.159040 ms | 0.015360 ms | 1.091x | 15/15 | 5 |

The preregistered group-eight hypothesis passes: all 15 retained samples exceed the
one-microsecond overlap threshold, median overlap is
0.015360 ms, median interval concurrency is
1.091x, and the observed maximum peak is
5. Group four crosses in 8/15 samples; group two
crosses in only 2/15, giving a scale control rather than a universal claim.

## Interpretation boundary

This is positive evidence for origin-relative CUDA-event interval overlap in the
instrumented one-shot ticket path on one RTX 4060. The absolute group-eight median
overlap is only 15.36 microseconds. Event span
(3.014656 ms) remains much larger than the union of
kernel-marked intervals (0.159040 ms), so synchronous
allocation, H-to-D upload, D-to-H download, cleanup, and host orchestration still
dominate the complete ticket wall interval. This is not kernel-transfer overlap,
not a pure kernel-duration profile, not a cross-device result, and not an adaptive
stream-policy promotion. CUDA permits elapsed intervals in non-null streams to

include interleaved work, and event instrumentation can perturb scheduling.
