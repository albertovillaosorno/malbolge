# Linux x86-64 collapsed rotate/no-op process phase evidence

This directory retains phase-separated measurements from
`native_process_execution` at clean producer commit `14e9282a22724804f9018d15c0537584392f8263`.
The workload is the reviewed non-aliasing two-step rotate followed by
no-operation shape. Every native artifact is independently verified, and every
call-bearing sample validates exact guest completion after timing.

| Scale | Interpreter ns | Prepare ns | Load/release ns | Resident ns | Lifecycle ns |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1,557 (1,331-2,132) | 35,630 (24,298-46,737) | 118,930 (77,015-159,975) | 23,695 (21,925-41,149) | 109,061 (98,629-187,830) |
| 2 | 1,900 (1,785-2,696) | 58,195 (42,602-88,238) | 202,119 (147,375-311,101) | 44,496 (41,137-68,596) | 230,209 (196,737-313,898) |
| 4 | 2,758 (2,511-4,310) | 97,961 (84,379-129,415) | 394,482 (279,067-489,475) | 86,393 (77,353-118,090) | 475,349 (385,881-566,166) |

Each table cell is the retained median followed by the observed min-max range.
`metadata.json` also records inclusive IQR for every mode/scale. All 225
retained samples completed with status zero under the retain-all policy.

`object-preparation` times collapsed semantic admission, canonical Windows COFF
emission, and independent verification. `load-release` measures strict-W^X
mapping lifecycle without a guest call. The resident mode keeps the exact
mapping outside the timer and measures process-backed calls through `MBNPC1`.

`one-shot-lifecycle` includes load, call, semantic completion admission, and
release. The enclosing benchmark invocation took 30.49 s wall time,
50.77 s user time, and 7.06 s system time, reaching 742,284 KiB
maximum RSS; that resource envelope includes a 20.73 s release rebuild
before measurement execution.

At scale 1, resident process execution was 15.218x the interpreter median and one-shot lifecycle was 70.046x. At scale 2, resident process execution was 23.419x the interpreter median and one-shot lifecycle was 121.163x. At scale 4, resident process execution was 31.325x the interpreter median and one-shot lifecycle was 172.353x. These ratios are descriptive overhead measurements for this
micro-workload; no positive native speedup is claimed.

`raw.csv` retains every sample. `metadata.json` binds the producer commit,
benchmark/worker/protocol/call-contract/raw hashes, host and toolchain identity,
timing boundaries, resources, statistics, and limitations.

This is Linux x86-64 evidence only. It does not execute AArch64 or Windows
code. The internal-alias rotate/no-operation shape remains excluded by semantic
admission. Observed min/max and IQR are descriptive rather than confidence
intervals.

The guarded JIT tier remains unimplemented, so no JIT baseline is reported and
no general tiering-policy claim is made.
