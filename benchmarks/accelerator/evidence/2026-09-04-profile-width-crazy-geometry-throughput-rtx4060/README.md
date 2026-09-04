# Profile-width crazy geometry throughput - RTX 4060

This retained evidence compares the resident tritwise, native `5+5+r`, and
padded `5+5+5` CUDA crazy implementations over the same frozen 16,384-step
N10-N14 workload. Every timed execution is followed by complete-state equality
against the independent expected image.

Adapter construction, NVRTC compilation, resource queries, and validation are
outside the timed regions. Each geometry/width has one warmup, 15 end-to-end
`CudaProfileRunAdapter.evaluate` samples, and 15 resident-session `advance`
samples. Route blocks use the benchmark's cyclic first-route-by-width order.

| Width | Tritwise resident ms | Native resident ms | Padded resident ms | Best resident vs tritwise | Tritwise end-to-end ms | Native end-to-end ms | Padded end-to-end ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| N10 | 7.544 | 3.809 | 3.977 | native 1.980x | 14.669 | 6.699 | 6.834 |
| N11 | 8.370 | 4.320 | 4.092 | padded 2.046x | 11.593 | 7.487 | 7.481 |
| N12 | 8.808 | 4.600 | 4.092 | padded 2.153x | 12.960 | 8.670 | 8.185 |
| N13 | 9.316 | 5.003 | 4.101 | padded 2.272x | 15.574 | 11.329 | 10.398 |
| N14 | 9.601 | 5.510 | 4.118 | padded 2.332x | 23.520 | 19.652 | 17.678 |

The Driver reports 188 constant bytes for tritwise and 59,237 for both lookup
routes, zero static-shared/local bytes, and 35-40 registers per thread across
the matrix. Every route admits six active 256-thread blocks per SM, matching all
1,536 resident threads available per SM on this device. Resource and occupancy
queries are observations, not semantic authority.

N10 has the lowest median for native lookup in both timed regions. N11 is nearly
tied end-to-end while padded wins resident-only; padded has the lowest median in
both regions for N12-N14. The route-block protocol does not remove every
thermal/order effect, so small differences are not treated as significance.

The hermetic CUDA bundle contains no Nsight Compute, CUPTI, or NVPerf surface,
and this run therefore makes no constant-cache hit-rate or traffic claim. Cache
counter evidence and the final deterministic route-selection decision remain
open rather than being inferred from wall time.
