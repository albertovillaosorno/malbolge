# N10-N14 CRAZY geometry resident resources - RTX 4060

This retained run records exact one-request CUDA buffer accounting and live batch
planning for the same N10-N14 workload and three arithmetic geometries used by
the CRAZY geometry throughput matrix. It does not time kernels and it never
allocates the 100,000-request planning horizon.

For one request, all three arithmetic routes have identical state, full-memory,
minimum input, and output-capacity buffers. The initial H-to-D byte count equals
the allocated byte count for this single-request, zero-input workload. Planner
item bytes exclude the four-byte minimum input buffer, while the planner keeps an
independent eight-byte fixed overhead per chunk.

| Width | Allocated / initial H-to-D bytes per VM | Planner item bytes |
| --- | ---: | ---: |
| N10 | 301,800 | 301,796 |
| N11 | 774,192 | 774,188 |
| N12 | 2,191,368 | 2,191,364 |
| N13 | 6,442,896 | 6,442,892 |
| N14 | 19,197,480 | 19,197,476 |

The live first admitted chunks were 16,360 items for all N10 routes;
6,396/6,400/6,406 at N11; 2,263/2,257/2,265 at N12; 769 for all N13 routes; and
258/257/257 at N14, ordered tritwise/native/padded. These small cross-route
differences are retained with each route's measured free-memory snapshot. They
are not attributed to the CRAZY arithmetic itself because the per-VM footprint
is identical.

`resources.json` preserves all 15 width/geometry rows, resource snapshots,
reserve/usable memory, chunk counts and first-chunk sizes. `source-commit.txt`
identifies the clean diagnostic commit. This evidence does not establish
failure/fallback behavior or select a production CRAZY geometry.
