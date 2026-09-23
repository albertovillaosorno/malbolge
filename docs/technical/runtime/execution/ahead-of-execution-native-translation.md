# Ahead-of-execution native translation

## Status

Proposed

## Purpose

Make verified ahead-of-execution translation the primary native execution
path. Use the portable execution IR between Malbolge decode and
architecture-specific code generation, then build or load exact native artifacts
before guest execution from reachable code-state evidence. When verification
proves a finite closed self-modification graph, materialize its reachable
code-state variants as native blocks and lower
runtime self-modification to guarded transitions among those precompiled
variants.

Offline CPU, GPU, or superoptimization search may propose stronger reductions,
but independent deterministic verification remains the only admission authority.
Unproven regions fall back to ordinary VM execution.

## Scope

This document governs the following declared TODO scope:

- `vm/`
- `execution/`
- `tests/vm/`
- `benchmarks/interpreter/`

## Current Behavior

### Implemented Foundation

The direct native path now supports a process-local AOT preparation boundary.
Reachable region variants can be compiled transactionally into a private
exact-key cache, deduplicated by complete artifact identity, and published only
after every requested fast path has passed profile preflight, native emission,
and semantic verification. Empty input, deoptimization-only variants,
unsupported
hosts, or any failed variant produce no partial AOT product.

The completed preparation cache is consumed into a sealed
VerifiedAheadOfExecutionNativeSet. Runtime AOT lookup accepts only that
read-only set and never emits or inserts code on a miss. Single-region lookup
distinguishes exact native hit, uncovered direct identity, and unsupported host
format after
profile preflight. Ordered direct sequences publish only when every exact step
is already present in the sealed AOT set; partial coverage remains unchanged.

Finite exact-state graph claims now have a deterministic admission path. Each
node carries a complete ProfileMachineState checkpoint, exact one-step portable
IR, and an optional successor. Admission replays every node with ProfileMachine,
requires byte-equivalent portable-IR reprojection, requires continued edges to
land on the complete claimed successor checkpoint, rejects open/unreachable or
duplicate exact states, and only then transactionally prepares every native
fast path into one sealed AOT set.

### Remaining Scope

Durable AOT artifact storage/loading, import/admission of reduced dependency
state-graph evidence, runtime native transition dispatch between admitted graph
states, and verified collapsed multi-step native effects remain open.

## Invariants

- Only regions whose code-state assumptions are explicit may be compiled before
  execution, and cache keys include every assumption required for safe native
  reuse.
- A verifier-proven finite closed state graph may be materialized as precompiled
  native code-state variants with explicit transitions. A runtime state absent
  from that admitted graph cannot silently reuse one of those variants.
- A native transition may collapse multiple guest steps only when
  deterministic verification proves the complete net effect on registers,
  memory, I/O, termination, and every retained code-state dependency.
- Offline optimizer, CPU, or GPU output is untrusted proposal material until
  deterministic verification proves its exact state effect and native identity.
- Ahead-of-execution work has no frame-critical latency budget, but its
  preparation time and resource use remain benchmarked separately from runtime.
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
  `self-modification-state-graph-optimizer`.
- Performance evidence pending: raw measurements plus a reproducible
  scaling/statistical summary tied to exact workload and hardware/software
  identity.
## References

- [Tiered Native Execution](../../adr/tiered-native-execution.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/tiered-native-execution.md`
- `docs/technical/adr/verification-trust-boundary.md`
