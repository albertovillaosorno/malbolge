# Current-profile streamed snapshot window evidence

This bundle measures one exact batch-32 resident snapshot through fixed reusable
host windows of one, eight, or thirty-two VM memories. Every callback validates
complete current-profile results while those results still alias the reusable
window arrays. The consumer retains no result memories, so the route demonstrates
bounded host materialization rather than deferred full-batch accumulation.

This is an RTX 4060 CUDA backend memory/throughput result. It is not a CPU-relative,
cross-device, or asynchronous-transfer claim. Ordinary snapshots and the existing
full caller-owned workspace retain their established ownership contracts.

## Provenance

- source commit: `28849367eeb6b99eacd05d249174575f0bf9961b`
- raw observations: `raw.csv` (60 rows)
- canonical workload SHA-256: `81b5d3544da6a00978d7e35bbb1ac7411ade00746b7ed9be353253338280e765`
- `raw.csv` SHA-256: `2b6854a45a389d667e6bb1165550c2eed949e14ff1997dbcd3d6fbc8fada6a31`
- `tradeoff.json` SHA-256: `971b3abec5e8d5ea035eedabce3724454b1b0eb2e8d48dcbd46a1ceb8ec1347f`
- `workload.json` SHA-256: `81b5d3544da6a00978d7e35bbb1ac7411ade00746b7ed9be353253338280e765`

## Environment

- host: Microsoft Windows 11 Pro 10.0.26200, 64-bit
- host memory: 31.91 GiB total; 16.55 GiB free before packaging
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1; NVRTC 13.3.33
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)
- geometry: 14 trits, 4,782,969 words, 19,131,876 bytes per VM

## Protocol and proofs

- stream identity: `caller-owned-windowed-u32-arrays-v1`
- registration identity: `bounded-all-or-pageable-u32-arrays-v1`
- fixed batch: 32 independent current-profile VMs after one 64-step resident run
- host windows: 1/8/32 memories, producing 32/4/1 ordered callbacks
- page-lock budget: 256 MiB, all-or-none per fixed window
- one warmup per route; 15 retained samples with cyclic first-route rotation
- five retained allocation samples per route
- every callback validates full memory length, exact outcome, and global range order
- callback results alias only the active prefix of the reusable window arrays
- session advance/snapshot/close, workspace close, and nested stream fail while active
- consumer failure releases both locks and permits an exact retry
- invalid budgets, non-callable consumer, forged/closed state, and shape drift fail closed

## Median tradeoff

| Window | Retained host memory | Callbacks | Registered | Fallback | Snapshot | Speedup vs full | Faster pairs vs full |
| ---: | ---: | ---: | :---: | --- | ---: | ---: | ---: |
| 1 | 18.246 MiB | 32 | true | none | 97.5194 ms | 1.023x | 14/15 |
| 8 | 145.965 MiB | 4 | true | none | 96.2771 ms | 1.036x | 13/15 |
| 32 | 583.859 MiB | 1 | false | budget-exceeded | 99.7597 ms | 1.000x | control |

Window one reduces retained host memory by 96.875%
and is faster than the full route in 14/15 paired samples.
Its median pair saving is 2.8415 ms. Window eight
reduces memory by 75.000%, wins
13/15 pairs, and saves
3.3675 ms at the paired median. Both fit the
256 MiB registration budget. The full 583.859 MiB route registers zero arrays,
records `budget-exceeded`, and remains the pageable control.

Window eight is 1.013x faster than window one at the route
median and wins 11/15 paired observations, with a
0.5260 ms paired-median saving. That modest
throughput difference costs eight times the retained host memory. The evidence
therefore retains both bounded choices rather than declaring one universal window.

## Decision

`caller-owned-windowed-u32-arrays-v1` is promoted as an explicit complete-snapshot
materialization option for consumers that can process and release each callback
before the next window. Window one is the minimum-memory route; window eight is the
measured balanced point on this RTX 4060. The fixed host budget remains authoritative,
and page-lock fallback is unchanged. No generator, background worker, stream overlap,
or asynchronous copy is introduced; those require a separate lifetime and ordering

contract. Broader live-hardware repetition remains open.
