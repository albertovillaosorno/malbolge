# Native-view rotate-target selector evidence

This bundle retains crossover protocol version 7 and a same-run selector-preparer
comparison. The active selector scans the already validated immutable payload bytes
through a native u32 view instead of copying all words into a Python `array`.

## Provenance

- implementation commit: `fa65e6e8e0e26ca8247ad888218b396bf2f28dc6`
- immediate crossover baseline source commit: `4cb61a7b9e58fb147e3b1646df9f001069b3cb06`
- raw observations: `raw.csv` (980 rows)
- aggregate workload SHA-256: `4448fd7594a50646c5da2ccea28b239fb80da4b16a005739f33db56ce5aa3777`
- `raw.csv` SHA-256: `892f8998dd9b6b4b7a7546232dc46faa3ceb842a020ef16d248a6edb7d32f4a6`
- `crossover.json` SHA-256: `1cc066fea82288707cb115ffb233b9ac34d6848e68a66f4e6f2b17600713704e`
- `selector-comparison.json` SHA-256: `f2e175b9abe51dc2d2fdb504ce1df861ff97db4acbb5f852f6f1107f260b4ab5`
- `baseline-crossover.json` SHA-256: `eceeabb59455857bd062b9ad10b1c836f97e8d43fc455e215793a14e196347e5`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Proofs

- active selector: `classic-u32le-native-view-preimage-v2`
- historical selector model: `classic-u32le-array-copy-preimage-v1`
- builder: `classic-u32le-bitset-inplace-first-representatives-v2`
- prepared reference: `cpu-scalar-packed-equality-v2`
- prepared input: `proof-bound-u32le-primitive-input-v1`
- candidate storage: `u32-index-fixed-width-payloads-rotation-v1`
- membership: `u32-rotation-or-pair-or-reference-binary-search-v1`
- ordinary validator: `u32le-broadword-domain-v1`
- exact selector positions match at all four scales and equal one for the canonical workload
- exact proposal, independent admission, cardinality, malformed/forged/fabricated, and CUDA session proofs remain required

## Selector component comparison

| Candidates | Array-copy time | Native-view time | Time ratio | Array peak | Native peak | Peak change |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.0257 ms | 0.0158 ms | 1.627x faster | 1,545 B | 1,785 B | 15.534% higher |
| 64 | 0.0283 ms | 0.0188 ms | 1.505x faster | 1,849 B | 1,821 B | 1.514% lower |
| 1,024 | 0.0875 ms | 0.0791 ms | 1.106x faster | 5,993 B | 1,885 B | 68.547% lower |
| 59,049 | 3.7642 ms | 3.9644 ms | 0.950x | 252,597 B | 1,885 B | **99.254% lower** |

The full-domain selector is 5.318% slower while removing essentially all copied-word
peak. The one-candidate native state retains 56 bytes more and peaks 240 bytes higher;
this is not a universal tiny-batch memory improvement.

## Full-domain preparation and memory

| Metric | Native selector v7 | In-place builder v6 | Change |
| --- | ---: | ---: | ---: |
| cold preparation | 64.465 ms | 64.606 ms | 1.002x |
| warm preparation | 64.780 ms | 65.101 ms | 1.005x |
| retained state | 710,647 B | 710,647 B | unchanged |
| peak allocation | 946,675 B | 962,052 B | **1.598% lower** |

Full-domain cold/warm crossover remains **1/1**. At 1,024 candidates total peak falls
from 19,116 to 18,075 bytes. One- and 64-candidate total peaks remain unchanged.

## Execution controls

CUDA ordinary changes from 91.191 to
90.236 ms (1.011x improvement), fresh build from
1.0101 to
1.0175 ms (0.993x), and reuse from
0.3738 to
0.3568 ms (1.048x). These are contextual controls;
the selector change occurs during preparation and no CUDA execution speedup is
attributed to it.

## Decision

The native-view selector is promoted. It preserves exact positions and all existing
proofs, removes 99.254% of the full-domain selector component peak, lowers complete
preparation peak by 1.598%, keeps retained state unchanged, and preserves one-run
crossover. Its full-domain selector-local timing regression and tiny-batch memory
cost remain explicit. Candidate-state creation, approximately 237 KiB incremental
beside the retained batch, is the next measured preparation-memory boundary.
