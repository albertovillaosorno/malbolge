# Current-profile caller-owned snapshot workspace evidence

This bundle compares ordinary resident snapshots with the explicit caller-owned
workspace on the same clean RTX 4060 session. Ordinary calls allocate fresh
independent mutable arrays. Workspace calls overwrite the same arrays by documented
contract. This is a CUDA backend ownership/throughput result, not a CPU-relative or
cross-device speedup claim.

## Provenance

- source commit: `f09f09309ff9c2f0ef03a69c63bd07a657ebb014`
- raw observations: `raw.csv` (555 rows)
- canonical workload SHA-256: `232de4d90fb7e3a474d37234c7d99285f4a196b36267adf9e2b8208b1decef1a`
- `raw.csv` SHA-256: `d6b15451d6afd0dd4eabfc65da0e70ef5154e175f55c0f058f493dfb5cfbd62e`
- `tradeoff.json` SHA-256: `a9dbd23b3a0058452286e8264ffa4677d399e147f98911920abe401efda20777`
- `workload.json` SHA-256: `8f1ece7d7c91f667242625e296268848f96a11cedbc0f05f54c2748184b93ae5`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)
- geometry: 14 trits, 4,782,969 words, 19,131,876 bytes per VM

## Protocol and proofs

- workspace identity: `caller-owned-independent-u32-arrays-v1`
- one untimed 64-step resident advance per batch
- one ordinary and one workspace warmup excluded
- 15 retained paired snapshots per route; first route alternates by sample parity
- five retained workspace-allocation samples per batch
- every complete result matches the exact no-op oracle
- ordinary memories are independent within and across calls
- workspace results alias exactly the supplied arrays and later calls overwrite them
- every workspace phase sample reports zero result-array allocation
- forged, resized, duplicate, wrong-type, wrong-count, and closed-session state fails
  closed before download

## Median tradeoff

| Batch | Ordinary | Workspace | Hot speedup | Allocate once | Strict crossover | Workspace bytes |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 8.1785 ms | 3.1631 ms | 2.586x | 4.9179 ms | 1 | 18.246 MiB |
| 8 | 65.7327 ms | 24.6510 ms | 2.667x | 41.3042 ms | 2 | 145.965 MiB |
| 32 | 272.1251 ms | 100.3275 ms | 2.712x | 173.7859 ms | 2 | 583.859 MiB |

The median-derived batch-one crossover is technically one snapshot, but its margin
is narrow: allocation plus one workspace snapshot is 8.0810 ms versus 8.1785 ms
ordinary. Ordinary remains the simpler one-shot default. Batches eight and thirty-two
recover the explicit allocation on the second snapshot with much larger margins.

## Phase shift

| Batch | Ordinary array allocation | Workspace allocation | Workspace memory D-to-H |
| ---: | ---: | ---: | ---: |
| 1 | 4.9478 ms | 0 ns | 3.0519 ms (96.484%) |
| 8 | 40.9665 ms | 0 ns | 24.4918 ms (99.354%) |
| 32 | 173.5689 ms | 0 ns | 100.0124 ms (99.686%) |

Workspace hot paths are transfer-dominated: full-memory D-to-H accounts for 96.485%,
99.389%, and 99.686% at batches one, eight, and thirty-two. The workspace removes
repeated array allocation but retains 18.246/145.965/583.859 MiB for its lifetime.

## Decision

The workspace is promoted as an explicit repeated-snapshot capacity, not as a silent
optimization of ordinary `snapshot()`. Ordinary snapshots retain fresh independent
ownership. Callers choosing the workspace accept overwrite/alias semantics and an
upfront retained-memory commitment. The next measured boundary is page-locking or
host registration of these stable caller-owned arrays, with a bounded memory budget,
explicit fallback, exact result preservation, and no change to ordinary ownership.
Batch-one benefit must be treated as marginal until broader hardware repeats it.
