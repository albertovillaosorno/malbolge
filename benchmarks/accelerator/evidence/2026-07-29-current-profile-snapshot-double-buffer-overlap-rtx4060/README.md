# Current-profile snapshot double-buffer overlap evidence

This bundle compares the exact registered `caller-owned-windowed-u32-arrays-v1`
route with `caller-owned-double-window-overlap-u32-arrays-v1` at identical
per-window capacities of one and eight VM memories. The overlap route submits the
next D-to-H window before validating the current callback, then waits before
publishing the next callback. It does not overlap kernels, mutate VM authority, or
retain results beyond callback scope.

The preregistered hypothesis required a lower overlap median and more than half of
fifteen paired wins for the matched window. Both routes satisfy that rule, but the
measured effects are modest and each overlap workspace retains exactly twice the
host memory. The result promotes double buffering as an explicit throughput/memory
tradeoff, not as a universal replacement for the synchronous stream workspace.

## Provenance

- source commit: `a25990ab1ff1dc8b42b1f8886e443bc7f9e69766`
- raw observations: `raw.csv` (80 rows)
- canonical workload SHA-256: `890519535538f56a804832fbe19e1343b4db6f4db7ccf855d3772b0a7427fecb`
- `raw.csv` SHA-256: `b6f286d5255432e27b0c82aef356d80447808d1764ce94d1c37593e191630ce1`
- `overlap.json` SHA-256: `11e11e9bafeb81e92803242e6cefe9731cfadcc11534ce31980c01f66cf6bbec`
- `workload.json` SHA-256: `890519535538f56a804832fbe19e1343b4db6f4db7ccf855d3772b0a7427fecb`

## Environment

- host: Microsoft Windows 11 Pro 10.0.26200, 64-bit
- host memory: 31.91 GiB total; 15.95 GiB free before packaging
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1; NVRTC 13.3.33
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)
- geometry: 14 trits, 4,782,969 words, 19,131,876 bytes per VM

## Protocol and proofs

- fixed batch: 32 independent current-profile VMs after one 64-step resident run
- matched registered windows: one and eight VM memories
- synchronous retained memory: 18.246/145.965 MiB
- overlap retained memory: 36.491/291.929 MiB
- callback counts: 32/4; overlap prefetch submissions: 31/3
- page-lock budget: 512 MiB all-or-none per workspace; every route is active and fully registered
- all four live workspaces remain allocated during paired route sampling
- one warmup per route; 15 retained samples with cyclic first-route rotation
- five retained allocation samples per route
- every timed callback validates complete current-profile results and exact range order
- overlap failure drains pending D-to-H work before releasing session/workspace locks
- one-bank budget and registration disable/budget/Driver rejection use the exact synchronous fallback route

## Median tradeoff

| Window | Route | Retained | Allocation | Snapshot range | Snapshot median | Paired wins | Paired median saving |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | synchronous | 18.246 MiB | 5.3228 ms | 95.0655-101.7034 ms | 95.2102 ms | control | control |
| 1 | overlap | 36.491 MiB | 10.7490 ms | 94.8026-95.2678 ms | 94.9084 ms (1.003x) | 14/15 | 0.2647 ms |
| 8 | synchronous | 145.965 MiB | 54.4017 ms | 94.6631-95.2302 ms | 94.7627 ms | control | control |
| 8 | overlap | 291.929 MiB | 123.0273 ms | 93.5677-94.2151 ms | 93.6493 ms (1.012x) | 15/15 | 1.0636 ms |

Window one lowers the median from 95.2102 to
94.9084 ms, a 1.003x improvement, and wins
14/15 paired observations. Its median paired saving is
0.2647 ms while retained memory and allocation
roughly double. Window eight lowers the median from 94.7627
to 93.6493 ms, a 1.012x improvement, wins
15/15 pairs, and saves 1.0636 ms at the
paired median. It also doubles retained memory to
291.929 MiB and more than doubles the
one-time allocation median.

## Decision

`caller-owned-double-window-overlap-u32-arrays-v1` is promoted as an explicit
registered snapshot option when callback validation or processing is large enough
to overlap next-window D-to-H and the caller accepts twice the retained host memory.
Window eight is the stronger measured point on this RTX 4060; window one proves the
mechanism but its 1.003x median effect is very small. The existing synchronous
workspace remains the minimum-memory choice. Registration failure or a one-bank
budget continues through exact synchronous fallback. Broader devices, other
callback workloads, adaptive bank/window selection, and any kernel/transfer overlap

remain open.
