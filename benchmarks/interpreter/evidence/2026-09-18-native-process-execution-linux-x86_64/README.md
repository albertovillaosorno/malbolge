# Secondary Linux native-process execution evidence

This directory retains host-real Linux x86-64 fused native execution samples
from `native_process_execution` at clean producer commit
`dba5fd50a3d198539624f28c543ca2629cc5aeb9`.
The workload is a normative two-step rotate/output VM trace, lowered to one
independently verified fused object before measurement.

| Scale | Lifecycle median ns | Resident median ns | Lifecycle/resident |
| ---: | ---: | ---: | ---: |
| 1 | 79,718 | 23,233 | 3.431x |
| 2 | 152,607 | 40,000 | 3.815x |
| 4 | 427,110 | 104,934 | 4.070x |

`one-shot-lifecycle` times verified load, the MBNPC1 process call, semantic
completion admission, and release for every call. `resident-call` loads one
311-byte executable mapping before the timer, performs only repeated verified
calls in the timed interval, and releases it afterward. Each call uses fresh
caller buffers covering the exact verified memory footprint.

All 90 retained samples completed their requested calls with semantic
memory/output checks and without poisoning the persistent process session.
The 754-byte fused object was executed through the tracked POSIX worker; raw
samples retain every observation, including the scale-four lifecycle outlier.

The enclosing Cargo invocation completed with status zero in 13.09 s wall time
and reached 629,136 KiB maximum resident set size; that resource record includes
release compilation as well as execution. `metadata.json` binds the producer,
benchmark/worker/protocol/raw hashes, host and toolchain identity, exact timing
scope, retain-all policy, observed ranges, and summary statistics.

These measurements compare process lifecycle cost with resident process calls;
they are not an interpreter-to-native speedup measurement. Host-real AArch64 and
Windows execution remain outside this evidence, and observed min/max ranges are
descriptive rather than confidence intervals.
