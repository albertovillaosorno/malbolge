# Independent CUDA ticket stream throughput

This bundle retains grouped one-stream-per-ticket throughput from clean source
commit `96a85f9ce1b1d8956c425722bfe88684eab5c0e6`. Each ticket evaluates the same proof-bound full-domain CRAZY
batch: 59,049 data words and 59,049 zero accumulators. Sequential routes repeat
submit+wait; grouped routes submit every ticket first and wait in reverse order.

## Protocol and identity

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- structured output: `throughput.json`
- raw chronological samples: `raw.csv`
- source commit: `96a85f9ce1b1d8956c425722bfe88684eab5c0e6`
- one warmup per route; 15 retained samples per route
- cyclic first-route rotation across six routes; all samples retained
- groups: 2, 4, and 8 tickets
- preparation, CPU reference, CUDA/NVRTC setup, and validation are untimed
- exact prepared storage: `proof-bound-u32le-primitive-input-v1`
- exact kernel lifetime: `cuda-independent-stream-kernel-launch-v1`
- workload SHA-256: `a523502c24560424c7139b527019e3f26ded512db205dec12a073e4801d7f7dc`
- `throughput.json` SHA-256: `8572827d46a7a38b223b05ffc2ad5a39ca1cbc9715fef237a44b5bd7b9c37935`
- `raw.csv` SHA-256: `196fd91cce77b06d3125df6a5f2fd8374f2524ee34d9c69ab0127a8e55ae8cc3`

## Environment

- host: Microsoft Windows 11 Pro 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA toolkit: 13.3.1 (`nvcc` 13.3.73)
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Results

| Group | Sequential median | Grouped median | Ratio | Paired wins | Paired-median saving |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 2.1745 ms | 1.5970 ms | 1.362x | 15/15 | 0.5334 ms |
| 4 | 3.6403 ms | 3.0304 ms | 1.201x | 15/15 | 0.6092 ms |
| 8 | 7.5313 ms | 5.6971 ms | 1.322x | 15/15 | 1.8240 ms |

The preregistered group-eight hypothesis passes: grouped execution reaches
5.6971 ms versus
7.5313 ms sequential, a
1.322x improvement with
15/15 paired wins. Groups two and four also improve,
but remain controls rather than additional preregistered hypotheses.

## Interpretation boundary

This evidence establishes grouped-ticket throughput for one deterministic kernel
workload on one RTX 4060. It does not by itself prove physical kernel overlap,
because CUDA scheduling and synchronous allocation/copy behavior are not measured
by timeline events. It is not compiler, synthesis, cross-device, asynchronous
transfer, or independent-stream scaling evidence beyond groups 2/4/8. Exact output
validation remains outside every retained interval but is mandatory for every
sample.
