# Tiered native execution engine

## Status

Active implementation

## Purpose

Build a tiered execution engine instead of choosing between interpretation, AOT,
and JIT. Decode Malbolge into a compact execution IR, simplify that IR through
verified state-graph mathematics, compile demonstrably stable regions to native
machine code before execution, specialize hot or mutation-sensitive regions at
runtime, and deoptimize safely to the interpreter whenever a code-version guard
or speculative assumption fails. The normative VM contract remains the semantic
baseline; native tiers are accelerators of identical observable behavior.

## Scope

This document governs the following declared TODO scope:

- `vm/`
- `execution/`
- `tests/vm/`
- `benchmarks/interpreter/`

## Current Behavior

### Implemented Foundation

`execution/ir/main.rs` now owns portable effect IR v1 as product code. It
defines `EffectOp`, `MemoryLiveIn`, and `RegionEffectProgram` under the existing
responsibility-oriented topology; Cargo composition uses explicit paths rather
than introducing a language-shaped crate boundary.

State-graph verification projects normative `ProfileStepTrace` records into that
IR only after exact region verification. An untrusted portable artifact must
match IR version, canonical profile fingerprint, verifier-derived live-ins,
semantic-step budget, bounded outcome, and every state-changing effect before a
verified artifact exists. Guard hits apply only admitted effects. Guard misses
run the normative `ProfileMachine` for the same verified budget and reconstruct
the incremental lineage from real traces; typed VM rejection propagates
unchanged.

`execution/cache/main.rs` now owns collision-safe native artifact identity.
`RegionEffectProgram` has a versioned layout-independent canonical byte
encoding, frozen by an independently rendered fixture. Native keys additionally
bind host OS, x86-64/AArch64 ISA, backend identity/revision, native ABI revision,
and sorted required features. FNV-1a is only a bucket accelerator; full canonical
IR and target equality remain authoritative after collisions.

`execution/native/main.rs` now owns the first host-code artifact boundary. The
bootstrap backend lowers one structurally consistent `RegionEffectProgram` into
deterministic freestanding C23 and binds the candidate to the exact
`NativeArtifactKey`. Generated code performs all entry-observation, memory,
input/EOF, pointer, and output-capacity checks before any guest-visible commit.
Repeated writes to one address collapse to its first required value and final
committed value, so a guard miss cannot leave an intermediate region state.

Pinned Clang 22.1.8 materializes the same bootstrap representation as real
Windows COFF objects for both x86-64 and AArch64 under strict warning-clean C23
compilation. Source and object containers remain explicitly `Untrusted*`:
matching IR/target identity proves provenance of the claim, not semantic
correctness of compiler-produced machine code.

### Remaining Implementation

Independent native semantic admission, direct x86-64/AArch64 instruction
selection, executable-memory policy/invocation, durable native cache
serialization/storage/eviction, AOT/JIT orchestration, and the end-to-end tier
selector remain open. The interpreter remains the only normative execution
authority and the guaranteed fallback.

## Invariants

- Interpreter, AOT, JIT, native cache, and deoptimization share one observable
  VM contract; disabling every native tier produces the same guest behavior.
- Observable state, I/O, termination, and diagnostics match the declared
  semantic profile across positive, boundary, and adversarial fixtures.

## Failure Behavior

Invalid programs, unsupported profiles, or broken native assumptions fail
deterministically without changing guest-visible state silently.

## Verification

- Expected durable artifact surface: `vm/`, `execution/`, `tests/vm/`,
  `benchmarks/interpreter/`.
- Required evidence: semantic fixtures, state/I/O traces where diagnostic, and
  differential results against independent specification-conformant
  implementations; the historical interpreter is compared only on its documented
  agreement domain.
- Prerequisite completion evidence: `safe-rust-malbolge-vm`,
  `self-modification-state-graph-optimizer`.
- Current executable foundation is covered by `tests/state_graph_research.rs`
  and `tests/tiered_execution.rs`: artifact tampering fails closed, verified
  effects/deoptimization match their normative baselines, canonical IR matches a
  byte-exact independent fixture, forced bucket collisions never authorize
  native-cache reuse, bootstrap source is deterministic/atomic/key-bound, and
  pinned Clang emits real x86-64 and AArch64 COFF object candidates.
- Native object candidates are not executed or admitted as verified artifacts by
  this evidence; that trust-boundary step remains explicit follow-on work.
## References

### Host Architecture Baseline

- `docs/technical/adr/host-cpu-and-accelerator-runtime-baseline.md`

- [Tiered Native Execution](../../adr/tiered-native-execution.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/tiered-native-execution.md`
- `docs/technical/adr/verification-trust-boundary.md`
