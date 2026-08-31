# Adaptive profile resource budget — RTX 4060

This evidence reruns the product resource-budget measurement after N15 became
the current profile. The live CUDA Driver API snapshot records memory and coarse
compute resources; the same document retains deterministic synthetic N10
through N15 capacity rows under a 128 MiB resource snapshot.

The live device reports `sm_89`, 24 multiprocessors, 1,024 maximum threads per
block, 8,215,396,352 total Driver API bytes, and 6,975,913,984 free bytes at the
measurement point. After the deterministic reserve, 6,462,451,712 bytes remain
usable for modeled resident state. The 57,395,692-byte current N15 model admits
112 complete items in the first live-device chunk.

Synthetic zero-I/O item sizes for N10 through N15 are 236,260; 708,652;
2,125,828; 6,377,356; 19,131,940; and 57,395,692 bytes. Under the same synthetic
128 MiB snapshot, first-chunk capacities are 532, 177, 59, 19, 6, and 2. These
are capacity-model rows, not throughput measurements on hypothetical hardware.

The separate retained 100,000-GiB synthetic bundle remains the no-ceiling probe:
its requested work is not clamped to development-GPU VRAM and is split only by
the explicit backend indexing boundary. Together these bundles establish live
resource discovery, exact adaptive resident-byte accounting, and a no-fixed-VRAM
capacity counterexample. They do not authorize semantic narrowing.
