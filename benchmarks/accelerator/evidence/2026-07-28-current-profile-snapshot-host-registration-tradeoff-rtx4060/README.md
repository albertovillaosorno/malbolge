# Current-profile snapshot host-registration evidence

This bundle compares paired pageable and bounded page-locked caller-owned snapshot
workspaces on one unchanged RTX 4060 resident session. It is a CUDA backend
transfer/lifetime result, not a CPU-relative or cross-device speedup claim. Ordinary
snapshot ownership remains fresh and independent; host registration is available only
through the explicit workspace contract.

## Provenance

- source commit: `fe04457de2c318a841f6bcfcd5e5a4ea494c8f3e`
- raw observations: `raw.csv` (570 rows)
- canonical workload SHA-256: `e4d223bf64951fae8435752edea81d52540f7b9cd5f78b9c2ef59acd697ac614`
- `raw.csv` SHA-256: `4123034795e50e7ddab4680a2572c42daed01e562f41b232394e72890fd8c367`
- `tradeoff.json` SHA-256: `bc4ad1dfdcad32bf8b8a3c0f79e59035cf77f6497fc7c55e1c5914cfc83712b3`
- `workload.json` SHA-256: `e4d223bf64951fae8435752edea81d52540f7b9cd5f78b9c2ef59acd697ac614`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)
- geometry: 14 trits, 4,782,969 words, 19,131,876 bytes per VM
- physical host memory observed before the run: 31.91 GiB total, 18.57 GiB free

## Protocol and proofs

- workspace identity: `caller-owned-independent-u32-arrays-v1`
- registration identity: `bounded-all-or-pageable-u32-arrays-v1`
- page-lock budget: 256 MiB, all-or-none per workspace
- one untimed 64-step resident advance per batch
- one warmup per route; 15 retained paired samples with alternating first route
- five retained allocation samples per route and batch
- every complete result matches the exact current-profile no-op oracle
- every result aliases exactly the caller-owned array for its request position
- batches one/eight register all 1/8 arrays; batch thirty-two registers zero arrays
  and records `budget-exceeded`
- invalid budgets fail closed; Driver rejection rolls back prior registrations and
  falls back only after clean rollback
- workspace, session, and runtime closure release every page lock deterministically
- ordinary `snapshot()` and ordinary workspace defaults remain pageable and unchanged

## Median tradeoff

| Batch | Buffer | Registered | Fallback | Pageable | Bounded | Hot speedup | Strict crossover |
| ---: | ---: | :---: | --- | ---: | ---: | ---: | ---: |
| 1 | 18.246 MiB | true | none | 3.4229 ms | 3.1718 ms | 1.079x | 2 |
| 8 | 145.965 MiB | true | none | 29.5885 ms | 26.7148 ms | 1.108x | 3 |
| 32 | 583.859 MiB | false | budget-exceeded | 99.4115 ms | 99.9298 ms | 0.995x | none |

For batch one, bounded registration is faster in 15/15 paired observations. The
median paired saving is 192.8 microseconds, incremental setup costs 0.3888 ms, and
strict crossover is two snapshots. For batch eight it is faster in 14/15 pairs,
saves 3.0532 ms at the paired median, and amortizes 8.1171 ms of incremental setup
by snapshot three. Full-memory D-to-H improves 1.092x/1.108x at those active
batches.

Batch thirty-two is the required negative control. Its 583.859 MiB workspace exceeds
the 256 MiB budget, so the bounded route registers zero arrays, records
`budget-exceeded`, remains pageable, and receives no crossover or speedup claim. Its
small timing difference is contextual variance rather than registration evidence.

## Decision

Bounded host registration is promoted as an explicit repeated-snapshot option for
stable caller-owned workspaces, not as a default or universal pinned-memory policy.
On this RTX 4060 it improves active batches one and eight and amortizes incremental
setup within two and three snapshots. The byte budget is authoritative: oversized
workspaces fall back all-or-none without changing exact results or ordinary ownership.
The next boundary is chunked/streaming host materialization and broader live-hardware
repetition; asynchronous transfer requires a separate lifetime and ordering contract.
