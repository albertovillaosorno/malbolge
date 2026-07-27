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

### Remaining Implementation

No host machine-code artifact is emitted yet. x86-64/AArch64 backends, durable
native cache serialization/storage/eviction, executable-memory policy, AOT/JIT
orchestration, and the end-to-end tier selector remain open. The interpreter
remains the only normative execution authority and the guaranteed fallback.

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
  byte-exact independent fixture, and forced bucket collisions never authorize
  native-cache reuse.
## References

### Host Architecture Baseline

- `docs/technical/adr/host-cpu-and-accelerator-runtime-baseline.md`

- [Tiered Native Execution](../../adr/tiered-native-execution.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/tiered-native-execution.md`
- `docs/technical/adr/verification-trust-boundary.md`
