# Historical Interpreter Evidence

This directory owns deterministic host-tool evidence for Ben Olmstead's
immutable interpreter. It does not benchmark the modern VM and does not make
historical undefined C behavior normative.

`sanitizer-cases.json` declares one clean interpreter-authority program and the
two H-003 loader boundaries. The runner materializes inline hex sources only in
`.temp`, verifies the pinned historical source hash, compiles the untouched
source with Clang 22.1.8 AddressSanitizer and UndefinedBehaviorSanitizer, and
normalizes findings without retaining addresses or host-specific stacks.

`evidence/windows-x86_64-sanitizer-findings.json` is the reviewed normalized
result. Empty and one-word sources both expose an AddressSanitizer
`heap-buffer-overflow`; the clean interpreter roundtrip emits byte `0xA8` and
has no sanitizer finding.

Run the check from the repository root:

```powershell
.dependencies\python\3.14.6\Scripts\python-jig.cmd -m `
  scripts.validate.historical_interpreter_sanitizer
```

The Windows `_halloc` compatibility function is generated and linked as a
separate temporary translation unit. The historical `main.c` is never patched,
wrapped, copied back, or used as a source of safe modern semantics.

## Native backend pipeline benchmark

`native_backend_pipeline` measures the reviewed fused native backend preparation
pipeline on the same VM-derived two-step `rotate/jump-code` workload for x86-64
and AArch64. Each retained timing includes direct sequence selection, fused
admission, COFF emission, and independent semantic object verification.

Run it from the repository root with:

```sh
cargo bench --bench native_backend_pipeline
```

The benchmark emits CSV to standard output. It retains 15 samples per ISA at
pipeline repetition scales 1, 2, and 4 for both cold uncached and warm exact-
cache modes. Warm samples seed a fresh direct-artifact cache outside the timer;
every timed warm selection must report two exact hits per pipeline iteration and
zero insertions. The harness performs one untimed warmup per ISA/scale/mode,
alternates ISA and mode order across retained samples, and records exact cache,
verified-object, emitted-byte, end-to-end, and per-stage timing counters.

This benchmark does **not** allocate executable memory or invoke generated
machine code. It therefore measures backend preparation and verification cost,
not native execution throughput or interpreter-to-native speedup. AArch64 is a
target encoding generated and verified on the benchmark host; it is not executed
when the host is x86-64. Host-specific retained measurements belong under
`evidence/` with exact source, workload, toolchain, hardware, operating-system,
resource-budget, raw-sample, and statistical provenance.
