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

The interpreter is always available and remains the semantic fallback. Native
tier policy is AOT-first: portable execution IR and verified state-graph
evidence may feed ahead-of-execution native translation before guest execution
begins.
When the verifier proves a finite closed self-modification graph, the AOT path
may compile each reachable code-state variant and implement mutation as guarded
transitions among those precompiled native blocks. Native backends initially
target x86-64 and AArch64.

A guarded JIT is a secondary rescue tier for hot mutable states absent from the
admitted AOT/native-cache set. Exact AOT hits take precedence, and synchronous
JIT work has a bounded resource/time budget before interpreter fallback.

Every specialization states its code/data assumptions. Failed guards deoptimize
to an equivalent interpreter state. Native caches include every semantic
assumption required for safe reuse.

Offline CPU, GPU, or superoptimization search may propose stronger reductions,
including collapsed multi-step state effects, but independent deterministic
verification is the only authority that may admit those effects for native
execution.

Users can disable JIT, AOT, or all native execution. `--interpreter-only` must
perform no hidden native generation or native-cache reuse.

## Advantages

- Makes the tiered native execution boundary explicit, reviewable, and stable
  before implementation depends on it.

## Disadvantages

- The decision increases cross-backend implementation and validation cost.

## Consequences

- Native execution is an optimization layer, never the VM specification.
- AOT artifact generation/loading is the preferred native steady-state path.
- JIT latency budgets, deoptimization, and cache identity are
  correctness-critical components.
- Interpreter-only benchmarks provide a stable baseline for execution research.

## Rejected Alternatives

### Interpreter only

Retained as a required mode but rejected as the only execution strategy because
it prevents research into eliminating host overhead while preserving semantics.

### Translate one unguarded whole-program image before execution

Rejected as a universal strategy because arbitrary self-modification can
invalidate static assumptions. This does not reject AOT over a verifier-proven
finite state graph: separate code-state variants with exact transition guards
are compatible with the decision.

## Evidence

State-graph reductions can feed both AOT and JIT, but a graph optimization must
be verified before it changes native-execution assumptions.
