# Guarded self-modification JIT

## Status

Proposed

## Purpose

Use JIT compilation as a latency-bounded rescue tier for hot mutable code-state
versions absent from verified AOT artifacts. Exact AOT/native-cache hits always
take precedence. Attach explicit guards to assumptions about self-modifying
cells, code/data aliasing, addressing, and control flow.

A failed guard or exhausted compilation budget deoptimizes to the interpreter.
Newly observed
states may become candidates for later specialization or a future AOT build, but
observation alone never grants native execution authority.

## Scope

This document governs the following declared TODO scope:

- `vm/`
- `execution/`
- `tests/vm/`
- `benchmarks/interpreter/`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`guarded-self-modification-jit`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

JIT compilation and dispatch are not implemented. The shared performance-
admission gate rejects any comparison other than normative interpreter versus
in-process native execution for one exact cohort. AOT-first rescue composition
now bypasses that gate for exact AOT hits and host-format interpreter fallback.

An uncovered result retains its complete native artifact key through promotion,
so `JitEligible` cannot silently rebuild a different compilation identity. A
caller-owned positive nanosecond/object-byte budget is then mandatory before the
route can become `JitCompilation`.

A replaceable compiler port now receives that exact identity and budget, must
enforce both ceilings, and returns only compiled, budget-exhausted, cancelled,
unsupported, or adapter-failure evidence. Application orchestration
independently rechecks successful time/size claims. Scheduled composition
invokes
that compiler
only for `JitCompilation`; exact AOT and interpreter routes bypass it.

Artifact admission, installation, and execution remain unimplemented.

## Invariants

- Every speculative native specialization has explicit code-state guards and a
  tested deoptimization path that reconstructs an equivalent interpreter state
  on guard failure.
- Exact admitted AOT/native-cache hits suppress duplicate JIT compilation
  for the same semantic and code-state identity.
- Synchronous compilation has an explicit resource/time budget. Exhaustion,
  cancellation, or unsupported specialization falls back to the interpreter.
- Tail latency, compilation/admission cost, and steady-state execution are
  measured separately. Promotion requires paired equivalent interpreter and
  in-process-native aggregate latency evidence proving at least 11/10 (1.1x)
  speedup; callers may require a stricter ratio but never a weaker one.
- Process/IPC native measurements never authorize JIT promotion, even if a
  larger fused region amortizes IPC enough to exceed the numeric speedup gate.
  Such measurements remain pipeline and benchmark evidence only.
- Observable state, I/O, termination, and diagnostics match the declared
  semantic profile across positive, boundary, and adversarial fixtures.
- Performance conclusions use equivalent workloads and report raw-sample
  provenance, resource budgets, dispersion/uncertainty, and failure/success
  behavior rather than only a best-case number.

## Failure Behavior

Invalid programs, unsupported profiles, or broken native assumptions fail
deterministically without changing guest-visible state silently.

## Verification

- Expected durable artifact surface: `vm/`, `execution/`, `tests/vm/`,
  `benchmarks/interpreter/`.
- Required evidence: semantic fixtures, state/I/O traces where diagnostic, and
  differential results against independent interpreter-compatible
  implementations; the original C source is compared only where its behavior is
  defined and reproducible.
- Prerequisite completion evidence: `tiered-native-execution-engine`,
  `native-x86-64-and-aarch64-backends`,
  `ahead-of-execution-native-translation`,
  `self-modification-state-graph-optimizer`.
- Performance evidence pending: raw in-process measurements plus a reproducible
  scaling/statistical summary tied to exact workload and hardware/software
  identity.
## References

- [Tiered Native Execution](../../adr/tiered-native-execution.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/tiered-native-execution.md`
- `docs/technical/adr/verification-trust-boundary.md`
