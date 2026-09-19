# Linux x86-64 native-process versus interpreter evidence

This directory retains the first equivalent-workload comparison between the
normative `ProfileMachine` interpreter and host-real fused process-native
execution. The clean producer commit is
`ee5b3e88b72c8cee437ed7f022bf59825975f276`.

The workload is one normative two-step rotate/output trace. Interpreter entry
checkpoints, the resident executable mapping, and resident caller buffers are
prepared before their timers. Every retained execution is checked against the
same exact final guest state after timing.

| Scale | Int. ns | Resident ns | Res./int. | Lifecycle ns | Life/int. |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2,188 | 31,111 | 14.219x | 166,536 | 76.113x |
| 2 | 3,003 | 52,730 | 17.559x | 241,335 | 80.365x |
| 4 | 3,819 | 101,172 | 26.492x | 461,741 | 120.906x |

All 135 retained samples completed with zero failures. For this tiny region,
resident process-native execution is slower than direct interpretation by
14.219x, 17.559x, and 26.492x at scales 1, 2, and 4 respectively. One-shot
load/call/release is slower still; no positive native speedup is claimed.

The result is intentionally narrow. Process-native timing includes IPC and
semantic completion admission, while interpreter timing covers only the exact
two-step run on prebuilt checkpoints. The comparison therefore measures this
current process boundary, not an in-process unsafe call or future JIT design.

The warmed enclosing Cargo invocation completed with status zero in 6.85 s
wall time and reached 338,788 KiB maximum resident set size. `raw.csv`
retains every sample; `metadata.json` binds source/worker/protocol/raw
hashes, host and toolchain identity, timing policy, resources, and limitations.

Host-real AArch64 and Windows execution remain outside this evidence. Observed
min/max ranges are descriptive rather than confidence intervals, and this
microbenchmark does not define cache-aware AOT/JIT performance policy.
