# Current-profile resident snapshot phase evidence

This bundle retains a descriptive phase decomposition of explicit complete
snapshots after current-profile state is already resident on the RTX 4060. It does
not claim a speedup and does not time session setup or the preceding 64-step
resident `advance()`.

## Provenance

- source commit: `4d1e6626edefc5bcbb2524dc816b284b210a5cfa`
- raw observations: `raw.csv` (270 rows)
- canonical workload SHA-256: `0cad900af14f9fc2c7fce66bdab2cc6453d171de418b5ff6b888b6a5d0166500`
- `raw.csv` SHA-256: `7411b4ed8c8352a0c64881fff452ee9fb7a4dc2f86e602f063ebe7c3ff4212ee`
- `phases.json` SHA-256: `330f0b3642884d0e3293b676eea2caa9239f934ed50f147374122f44bc2bae15`
- `workload.json` SHA-256: `0407f7b491299008805eb360ff79997fa243da593842f419da0bcabf9a74da9d`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)
- geometry: 14 trits, 4,782,969 words, 19,131,876 bytes per VM

## Protocol

For each batch size 1, 8, and 32, the benchmark opens one resident session,
executes one untimed 64-step segment, excludes one ordinary full-snapshot warmup,
and retains fifteen `profile_snapshot()` samples. Every complete result is checked
against the exact no-op workload. Each sample proves one resident chunk, nonnegative
phases, and named components no larger than inclusive total.

The `host_memory_allocate` phase measures creation of the final independent Python
`array('I')` results. It includes observable allocation, zero-fill, and operating-
system page-commit effects, but does not claim an internal allocator breakdown.

## Median phases

| Batch | Total | Final arrays | Full memory D-to-H | State D-to-H | Output D-to-H | Decode | Coverage |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 3.1616 ms | 0.0012 ms (0.038%) | 3.0506 ms (96.489%) | 0.0470 ms | 0.0349 ms | 0.0183 ms | 99.817% |
| 8 | 65.7829 ms | 41.0609 ms (62.419%) | 24.5029 ms (37.248%) | 0.0929 ms | 0.0345 ms | 0.0690 ms | 99.986% |
| 32 | 271.1391 ms | 173.1827 ms (63.872%) | 97.5069 ms (35.962%) | 0.0944 ms | 0.0347 ms | 0.1962 ms | 99.996% |

Per-VM total rises from 3.1616 ms at batch one to 8.2229 ms at batch eight and
8.4731 ms at batch thirty-two. Named coverage is at least 99.817%.

## Interpretation

The hypothesis is supported. Batch one reuses its existing final memory array, so
full-memory D-to-H accounts for 96.489% of median time. Batches eight and thirty-two
must create independent mutable result arrays: allocation accounts for 62.419% and
63.872%, while memory transfer accounts for 37.248% and 35.962%. State/output
transfers and decode are each below 0.15%; decode is at most 0.105%.

Pinned memory alone is not selected by this evidence because it does not remove the
dominant requirement to produce fresh independently mutable Python arrays. Reusing
session-owned buffers would silently change ownership and allow later snapshots to
mutate earlier results. The next design experiment must use an explicit alternate
contract such as caller-owned storage or streaming output, with ordinary
`ProfileRunResult` semantics left unchanged. Broader hardware evidence remains
necessary before a cross-device claim.
