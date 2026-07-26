# Tiered Native Execution

## Status

Accepted.

## Decision ID

`jig.malbolge.technical.tiered-native-execution`

## Context

Literal interpretation of a sequential self-modifying machine can impose large
host overhead. Some regions may have mathematically reducible mutation histories
or runtime-stable code states that can execute as native host instructions.

## Decision

The runtime uses optional tiered execution over one exact VM contract.

The interpreter is always available and remains the semantic fallback. A
portable execution IR may feed ahead-of-execution native translation and a
guarded JIT for hot mutable regions. Native backends initially target x86-64 and
AArch64.

Every specialization states its code/data assumptions. JIT assumptions are
runtime guarded; a failed guard deoptimizes to an equivalent interpreter state.
Native code caches include all semantic assumptions required for safe reuse.

Users can disable JIT, AOT, or all native execution. `--interpreter-only` must
perform no hidden native generation or native-cache reuse.

## Advantages

- Makes the tiered native execution boundary explicit, reviewable, and stable
  before implementation depends on it.

## Disadvantages

- The decision increases cross-backend implementation and validation cost.

## Consequences

- Native execution is an optimization layer, never the VM specification.
- Deoptimization and cache identity become correctness-critical components.
- Interpreter-only benchmarks provide a stable baseline for execution research.

## Rejected Alternatives

### Interpreter only

Retained as a required mode but rejected as the only execution strategy because
it prevents research into eliminating host overhead while preserving semantics.

### Translate the whole program once before execution

Rejected as a universal strategy because arbitrary self-modification can
invalidate static assumptions.

## Evidence

State-graph reductions can feed both AOT and JIT, but a graph optimization must
be verified before it changes native-execution assumptions.
