# Linux x86-64 AOT process phase evidence

This directory retains phase-separated measurements from
`native_process_execution` at clean producer commit
`511327d491fa2c0ade77753084f701236a18aab9`. The
workload is one normative two-step rotate/output VM trace; every native
artifact is independently verified, and call-bearing modes validate exact
guest completion after timing.

| Scale | Interpreter ns | Prepare ns | Load/release ns | Resident ns | Lifecycle ns |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2,577 (2,295-3,068) | 122,198 (90,095-141,341) | 130,782 (89,054-242,769) | 36,802 (35,147-44,163) | 122,686 (113,662-132,526) |
| 2 | 3,366 (3,029-13,856) | 204,110 (170,072-227,107) | 216,742 (171,426-253,486) | 65,924 (63,456-82,877) | 240,775 (219,382-297,527) |
| 4 | 4,143 (3,854-5,087) | 361,494 (323,558-402,372) | 388,479 (335,792-482,308) | 124,748 (117,645-230,260) | 462,107 (431,954-490,359) |

Each table cell is the retained median followed by the observed min-max range.
`metadata.json` also records inclusive IQR for every mode/scale. All 225
retained samples completed with status zero under the retain-all policy.

`object-preparation` times exact selection, fused semantic admission, COFF
emission, and independent verification for the same workload. `load-release`
measures executable mapping lifecycle without a guest call. The resident mode
keeps the exact mapping outside the timer and measures process-backed calls.

`one-shot-lifecycle` includes load, call, semantic admission, and release.
The warmed enclosing benchmark took 8.75 s wall time,
4.42 s user time, and
3.96 s system time, reaching
339,016 KiB maximum RSS.

`raw.csv` retains every sample. `metadata.json` binds source hashes,
host and toolchain identity, timing boundaries, resources, statistics, and
limitations.

This is Linux x86-64 evidence only. It does not execute AArch64 or Windows
code, and the resident path includes IPC plus semantic completion admission.
The guarded JIT tier remains unimplemented, so this evidence cannot provide
the JIT baseline required before the broader AOT comparison is complete.
No general native-speedup claim is made.
