# Prepared CUDA primitive phase decomposition

This directory retains the first public, exact subphase decomposition of the
59,049-word prepared CUDA rotate-candidate route. The benchmark composes
`CudaPreparedPrimitivePhaseProfile` with
`PackedPrimitiveEncodingPhaseProfile`; it does not alter ordinary or prepared
execution semantics.

The run used a clean detached worktree at source commit
`86307502c69f0386339b3e0055bf86ba60f138a8`. One warmup establishes the resident
session and cached broadword masks, then 15 profiles are retained in fixed order
with no outlier removal.

## Protocol

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- raw profiles: `raw.csv`
- structured output: `phases.json`
- warmup: one exact prepared profile
- retained profiles: 15
- outlier policy: retain all
- center: median
- dispersion/uncertainty: observed minimum-to-maximum range
- `phases.json` SHA-256: `77f3457249c2a3285b0e49987f2995ddb546d8b5c560e958de512fa554ed6504`
- `raw.csv` SHA-256: `ec7028e7ae402faa74197049b09a3a522a639bac2e3bf1e650be1b6988579ffc`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1, repository-pinned toolkit
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Proof identity

The profiler failed closed unless it observed:

- exact packed result equality with the independent CPU reference
- validator: `u32le-broadword-domain-v1`
- minimum required named coverage: 95.0%
- observed coverage: median 97.35%, minimum 95.40%, maximum 97.68%
- CUDA builds/evaluations/packed/reuses: 1/16/16/15
- resident CUDA operation/words: `rotate`/59049

## Median phase result

| Layer | Phase | Median |
| --- | --- | ---: |
| CUDA | Launch and synchronize | 0.0605 ms |
| CUDA | Device-to-host copy | 0.0934 ms |
| CUDA | Immutable byte copy | 0.0332 ms |
| CUDA | Layer total | 0.1965 ms |
| Encoding | Contract checks | 0.0023 ms |
| Encoding | Mask lookup | 0.0008 ms |
| Encoding | `int.from_bytes` | 0.2993 ms |
| Encoding | High-mask check | 0.0784 ms |
| Encoding | Threshold check | 0.2615 ms |
| Encoding | Failure diagnostic | 0.0000 ms |
| Encoding | Result construction | 0.0032 ms |
| Encoding | Layer total | 0.6558 ms |
| Combined | End-to-end total | 0.8684 ms |

Using median component divided by median end-to-end time for orientation,
launch/transfer/immutable-copy represent about **21.5%**, while integer
decode plus high-mask and threshold checks represent about **73.6%**.
The samplewise coverage result, rather than this ratio of medians, is the normative
completeness check.

## Interpretation boundary

This is descriptive attribution, not a speedup claim. Phase medians are separate
distributions and need not sum exactly. The retained result shows that the current
prepared route is dominated by exact big-integer packed-domain validation rather
than GPU execution or transfer. Any replacement must preserve immutable bytes,
capability/count checks, all-word domain rejection, validator identity, exact CPU
equality, and the independent admission boundary.
