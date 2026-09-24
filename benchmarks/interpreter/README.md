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
pipeline on VM-derived two-step `crazy/crazy`, `no-operation/output`, and
`rotate/jump-code` workloads for x86-64 and AArch64. Each retained timing
includes direct sequence selection, fused admission, COFF emission, and
independent semantic object verification.

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

## Native process execution benchmark

`native_process_execution` measures host-real fused execution through the
tracked POSIX process worker on Linux x86-64. The workload is a normative
two-step rotate/output trace; setup derives and independently verifies one fused
artifact, then retains only the exact required caller-memory prefix for timed
process transfers.

Run it from the repository root with:

```sh
cargo bench --bench native_process_execution
```

The benchmark retains 15 samples at scales 1, 2, and 4 for five modes.
`interpreter` prebuilds complete normative `ProfileMachine` instances outside
the timer, then times only their exact two-step `run(2)` execution.

`object-preparation` times exact selection, admission, COFF emission, and
independent verification of the same rotate/output artifact. It reports zero
completed calls. `load-release` times only verified executable load plus
release cycles and likewise reports zero completed calls.

`one-shot-lifecycle` performs verified load, process call, semantic admission,
and release for every call. `resident-call` loads one exact fused mapping before
the timer, performs only repeated verified process calls inside the timer, and
releases the mapping after the timer.

Interpreter checkpoint cloning and native worker/fused-artifact setup stay
outside timed intervals. Resident caller buffers are also prepared before its
timer, while one-shot lifecycle deliberately retains its complete per-call
transaction.

`object-preparation` validates every regenerated artifact against the fixture
artifact but performs no load or guest call. `load-release` validates every
lifecycle transition but executes no guest call. Call-bearing modes validate
exact semantic completion after timing.

Process modes use one persistent child, one untimed warmup per scale/mode, and
alternating mode order across retained samples. Resident rows report exact
retained executable mapping bytes; other modes retain none.

These measurements are Linux x86-64 host evidence only. They do not execute
AArch64 or Windows code, and native timed intervals exclude fused
selection/emission/object verification; the separate backend-pipeline benchmark
owns that preparation cost. Interpreter/native ratios therefore describe this
exact two-step workload and timing boundary, not a general VM speedup claim.
Retained measurements belong under `evidence/` with source/toolchain/worker
hashes, host identity, raw samples, resource budgets, failure counts,
dispersion, and uncertainty.

The retained five-mode Linux x86-64 AOT phase bundle is under
`benchmarks/interpreter/evidence/2026-09-24-aot-process-phases-linux-x86_64/`.
