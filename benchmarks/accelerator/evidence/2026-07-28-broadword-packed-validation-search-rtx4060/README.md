# Broadword packed-domain validation throughput

This directory retains the 59,049-word rotate-target workload after packed-domain
validation moved from scalar word iteration to exact broadword lane masks. The
validator first rejects high 16-bit content, then adds `0xffff - 59048` independently
in each 32-bit lane; bit 16 is set exactly for values above the classic maximum.
Scalar decoding remains only to report an invalid maximum after failure.

The run used clean source commit
`8c6150a982f21308d05a0367437df4b07fec7497`, one warmup, and 15 fixed interleaved
samples per route. Mask construction, search preparation, CPU table generation,
CUDA setup, NVRTC, and the first resident build are outside retained intervals.

## Protocol

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- raw samples: `raw.csv`
- structured output: `throughput.json`
- outlier policy: retain all
- center: median
- dispersion/uncertainty: observed minimum-to-maximum range
- `throughput.json` SHA-256: `65b9f1f98548967d7f6518a3c92429e37ca0a863973c0cb63e60ac7b06d37a9f`
- `raw.csv` SHA-256: `8de49f15b3b3f7b63710ef421a0cdd72305296d5adf4130740d979fd7b37c8bd`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1, repository-pinned toolkit
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Proof identity

- validator: `u32le-broadword-domain-v1`
- CPU evaluations/table entries: 16/59049
- membership/selector: 59049/1
- CUDA builds/evaluations/packed/reuses: 1/16/16/15
- resident operation/words: `rotate`/59049

Tests also reject threshold and high-bit corruption in the first and final lanes.

## Result

| Route | Scalar packed baseline | Broadword validation | Baseline/current |
| --- | ---: | ---: | ---: |
| CPU ordinary | 214.581 ms | 213.826 ms | 1.004x |
| CPU prepared | 3.300 ms | 3.179 ms | 1.038x |
| CUDA ordinary | 231.443 ms | 227.033 ms | 1.019x |
| CUDA prepared | 2.036 ms | 1.175 ms | 1.733x |

CUDA prepared improves **1.733x**, so the preregistered hypothesis passes. CUDA prepared is **2.706x faster** than same-run CPU.
Controls move much less; their cross-run changes are not attributed to broadword
validation.

## Interpretation boundary

This is amortized repeated-search evidence. Mask generation is untimed and cached by
word count. The arithmetic is an exact validation implementation, not backend trust.
This is not one-shot, stochastic, compiler, synthesis, or superoptimizer evidence.
