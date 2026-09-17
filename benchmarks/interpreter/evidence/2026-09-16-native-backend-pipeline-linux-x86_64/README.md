# Secondary Linux native-backend pipeline evidence

This directory retains release-profile measurements produced by
`native_backend_pipeline` from clean source commit
`bd4154af5b93d5fd46a74abf0fd01e79fed6d4d0` on the repository secondary
Linux host. The workload is one VM-derived current-profile
`rotate/jump-code` two-step trace.
Both target ISAs run the same select → fused-admit → COFF-emit → semantic-
verify pipeline; generated machine code is not loaded or executed.

Host: Intel Xeon E5-2690 v3, 12 physical cores / 24 logical processors,
Fedora Linux 44, kernel 7.2.5-200.fc44.x86_64, Cargo/Rust 1.98.0 and LLVM
22.1.8. Each ISA/scale pair has 15 retained samples after one untimed warmup.
The retained run completed 90 samples with zero benchmark-stage failures. The
whole Cargo benchmark invocation used 11.01 s wall time and reached 588,592
KiB maximum resident set size.

| ISA | Scale | Median ns | Min ns | Max ns | Median ns/object | Bytes/object |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| x86_64 | 1 | 61,019 | 59,872 | 87,901 | 61,019.0 | 717 |
| x86_64 | 2 | 118,969 | 116,615 | 130,870 | 59,484.5 | 717 |
| x86_64 | 4 | 247,573 | 232,082 | 418,065 | 61,893.2 | 717 |
| aarch64 | 1 | 61,538 | 59,933 | 79,330 | 61,538.0 | 891 |
| aarch64 | 2 | 120,755 | 118,307 | 135,332 | 60,377.5 | 891 |
| aarch64 | 4 | 248,454 | 234,136 | 420,302 | 62,113.5 | 891 |

At scale 4, median elapsed time is 4.057× the scale-1 x86-64 median and
4.037× the scale-1 AArch64 median. These are backend-pipeline scaling
measurements on one host, not execution-speed comparisons between ISAs. The
AArch64 rows measure target-code generation and verification on this x86-64
host; they do not execute AArch64 code.

`raw.csv` retains every sample. No retained sample is discarded as an outlier.
The summary uses the median as center, population standard deviation and
min/max as dispersion, and the observed range as bounded uncertainty.

`metadata.json` records workload/source hashes, host and toolchain identity,
resource usage, stage identity, success/failure counts, and those statistical
policies. `source-commit.txt` binds the run to the exact producer commit.

Concrete executable-memory integration and foreign-call shims
remain pending, so this evidence does not support an interpreter-to-native
execution speedup claim.
