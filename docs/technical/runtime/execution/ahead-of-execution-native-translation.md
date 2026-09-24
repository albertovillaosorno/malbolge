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

Register-masked v6 IR now has its own transactional AOT object boundary. The
runtime re-runs semantic/profile admission, emits and independently verifies one
of the six reviewed v6 templates, deduplicates exact mask-aware artifact keys,
and publishes an object-only sealed set. Read-only lookup distinguishes exact
hits, uncovered identities, and unsupported host format without runtime
emission. These values deliberately do not grant load or invocation authority.

The research state-graph boundary can now hand a verifier-admitted region to
production only through its product-owned register-masked v6 program. The native
side re-runs its own semantic/profile admission and object verification. An
integration fixture proves a reviewed one-step region crosses this boundary,
while a verified multi-step region remains unsupported rather than gaining
native authority from its research provenance. Product-owned multi-step v6
reprojection now independently derives read-before-write memory/register
live-ins, verifies trace continuity/profile/outcome, and rejects derived
execution geometry because schema v6 carries no explicit geometry token.

Register-masked v6 now also has a product-owned exact-topology admission path.
Each untrusted node supplies a complete entry checkpoint, one bounded v6
program, and an optional successor. Admission normatively replays the declared
step
budget, reprojects the full trace region, compares the exact v6 program, and
requires budget-exhausted exits to equal the claimed successor checkpoint.
Only closed, reachable topology proceeds to transactional v6 object preparation.

A multi-step node may therefore gain topology authority without gaining native
execution authority when no reviewed collapsed native shape exists.

Dependency-reduced v6 graph evidence now crosses a separate product-owned
admission boundary. Every untrusted node carries a complete witness checkpoint,
v6 program, reduced-identity claim, and successor. Admission normatively replays
the witness, reprojects the v6 program, and independently derives the reduced
guard from opaque geometry, termination, memory/register live-ins, masked live
register values, and ordered input observations relative to the candidate
cursor. Prior output history, absolute input cursor, unobserved input, dead
registers, and memory outside live-ins do not become reduced identity.

A budget-exhausted witness exit must satisfy the admitted successor guard, not
necessarily equal the successor witness checkpoint. Duplicate reduced
identities are rejected so one runtime guard cannot ambiguously identify two
nodes.

Reduced graphs now have a bounded AOT-first runtime dispatcher. Each turn first
checks the admitted reduced identity against the complete actual entry state,
performs read-only exact AOT selection, and invokes only the selected verified
artifact through a caller-owned native executor port. A committed continuing
transition may advance only when the declared successor guard matches the
complete actual runtime exit; the dispatcher never searches for another node by
approximation or witness similarity.

Guard miss is required to return the unchanged entry checkpoint. Uncovered
objects, unsupported reviewed native shapes, unsupported host formats, and
transition-budget exhaustion return explicit lower-tier fallback with the exact
resume state and committed-transition count. A mutated guard miss or terminal
completion with the wrong termination condition is a hard dispatch failure.

Reduced graph provenance now has a canonical durable codec. Encoding first
re-admits the complete claim, then stores only profile identity/fingerprint,
complete witness checkpoints, step budgets, and topology; verifier-derived
identity and v6 programs are deliberately not serialized as authority. Loading
resolves the exact profile fingerprint, validates canonical checkpoints,
replays every witness under a caller-owned per-node step limit, reprojects v6,
re-derives reduced identities, and runs ordinary closed/reachable graph
admission before publishing a verified graph. Malformed, truncated, trailing,
unknown-profile, over-budget, or unverifiable bytes fail closed; untrusted node
counts do not drive eager allocation.

Typed persistence now binds those canonical provenance bytes to the existing
bounded single-blob port. Publication encodes and verifies before replacement;
restore performs a bounded blob load before any decode/replay and represents a
missing blob explicitly. The existing filesystem blob adapter therefore gives
reduced-graph provenance same-directory staged replacement, publication locking,
and explicit post-publication durability confirmation without moving path or I/O
policy into the graph codec.

Verified register-masked AOT objects also have single-object durable storage.
Only canonical COFF bytes are persisted; native keys are never serialized as
authority. Restore receives the expected v6 program, runtime capability, host,
and byte bound from the caller, reconstructs the current exact key, and reruns
structural plus canonical-byte verification before returning an object-only
artifact. Restored artifacts can be sealed into an exact-key AOT set without
re-emission, while executable-memory authority remains outside this boundary.

Complete ordered v6 object sets now also cross one atomic durable bundle
boundary. Canonical bundle framing contains only a schema marker/version, the
expected object count, per-object lengths, and verified COFF payloads; no native
key is serialized as authority. Publication selects every expected exact
artifact read-only and constructs the entire bounded blob before the single
replacement, so a missing later artifact cannot publish a prefix.

Restore compares the untrusted stored count with the caller-owned expected
program sequence before object decoding, and that stored count never controls an
eager allocation. Every object is rebound to its expected program/runtime/host
and independently reverified before any sealed AOT set is returned. Reordered,
truncated, trailing, incomplete, oversized, or unverifiable bundles fail closed,
while the filesystem blob adapter supplies the single atomic publication point
and explicit durability confirmation.

Whole reduced v6 graphs now also have explicit executable residency ownership.
Every node selects its exact artifact from the sealed AOT set before
publication.
Unique native keys retain one reusable mapping, while duplicate keys share that
mapping without weakening node identity.

A late load failure releases earlier unique mappings in reverse load order.
Failed rollback releases retain exact ready-executable ownership for caller
retry. Explicit whole-graph release follows the same reverse-order rule and
reports checked aggregate mapping/byte weight without executing guest code.

The first reviewed collapsed multi-step semantic shape is now admitted for v6
no-operation followed by halt. Admission rechecks the exact two-effect outcome,
register masks, both code-cell live-ins, no-operation encryption, pointer
successors, effect continuity, and terminal completion while retaining complete
canonical v6 identity. This proof grants no host target, object, executable
memory, or invocation authority.

### Remaining Scope

The admitted no-operation/halt shape now has its own backend identity and
byte-canonical Windows COFF templates for x86-64 and AArch64. Independent
verification reconstructs semantic admission, exact v6 key/target assumptions,
COFF structure, and canonical bytes before promoting the object. A dedicated
load image then proves relocation closure, ISA alignment, and strict RW-to-RX
W^X policy.

A dedicated typestate lifecycle admits exact copy, RW-to-RX,
instruction synchronization, and retryable release ownership. ABI preparation
reconstructs the two-step net effect with dead A/I/O rebasing and binds only to
the exact synchronized collapsed executable.

Dedicated runner and actual foreign-call execution authority for this collapsed
shape remain open. Additional multi-step shapes stay unsupported until each
receives an equally explicit semantic and native proof.

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
