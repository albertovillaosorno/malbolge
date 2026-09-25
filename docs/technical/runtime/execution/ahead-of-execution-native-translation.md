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

A second reviewed semantic shape now admits exactly two consecutive v6
no-operations. It independently rechecks both register-write masks, both
code-cell live-ins and encryptions, exact effect continuity, both pointer
successor steps, budget-exhausted completion at two steps, and canonical v6
identity. This pair admission grants no target, object, executable-memory, or
call authority.

A third reviewed semantic shape now admits one v6 no-operation followed by
rotate. It independently rechecks both write masks, three distinct memory
live-ins, both code encryptions, the exact rotated data/accumulator value,
pointer successors, effect continuity, budget-exhausted completion, and
canonical v6 identity. This admission grants no target, object, executable
memory, ABI, or call authority.

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

A caller-owned runner port receives only that exact bound executable view.
Loaded-call orchestration restores the complete entry snapshot after runner
failure and delegates final status/state admission to the existing semantic
verifier. The persistent process host now projects that bound call through the
existing `MBNPC1` wire, validates the returned mapping/state/buffer evidence
before semantic completion, and owns the foreign call only inside the isolated
worker. Real x86-64 POSIX-worker evidence executes and releases the collapsed
Windows-ABI object without poisoning the session.

The no-operation pair now has its own backend identity and byte-canonical
Windows COFF templates for x86-64 and AArch64. Independent verification
reconstructs pair semantic admission, exact v6 key/target assumptions, COFF
structure, and canonical bytes before promoting the object.

Its dedicated relocation-free load image now proves exact COFF extraction, ISA
alignment, and the strict W^X policy. Pair-specific typestate then admits exact
copy, the same-mapping RW-to-RX transition, complete instruction
synchronization, and retryable release ownership without granting call
authority.

ABI preparation for the no-operation pair now derives both encryption writes
and the exact two-step exit while permitting only dead accumulator and I/O
history to rebase. Binding accepts only the exact synchronized pair executable
whose retained load image matches that prepared call.

A caller-owned pair runner port now receives only that exact bound executable
view. Runner failure restores the complete rebased entry snapshot, and returned
status/state is admitted through the existing semantic completion contract.

The persistent process host now projects that exact pair call through the
existing `MBNPC1` protocol, validates returned mapping/state/buffer
evidence, and delegates the foreign call only to the isolated worker. Real
x86-64 POSIX-worker evidence executes and releases the collapsed pair object
without poisoning the session.

The no-operation/rotate shape now has a distinct backend identity and
byte-canonical Windows COFF templates for x86-64 and AArch64. Independent
verification reconstructs semantic admission, exact v6 key/target assumptions,
COFF structure, and canonical bytes before promotion.

Its dedicated relocation-free load image proves exact extraction, ISA alignment,
and strict W^X. Shape-specific typestate admits exact copy, same-mapping
RW-to-RX, complete instruction synchronization, and retained release evidence.
The platform adapter now transactionally allocates, copies, protects, and
synchronizes this exact shape, releasing on post-allocation failure; explicit
release retains retry ownership.

ABI preparation derives both code encryptions, the rotate data write, and the
exact two-step exit while permitting only dead accumulator and I/O rebasing.
Binding accepts only the exact synchronized no-operation/rotate executable.

A caller-owned runner now receives only that bound view. Runner failure restores
the complete rebased entry snapshot, and returned status/state is admitted
through exact semantic completion.

The persistent process host now projects that exact bound call through the
existing `MBNPC1` protocol and validates returned mapping/state/buffer evidence
before semantic completion. The foreign call stays isolated in the worker. Real
x86-64 POSIX-worker evidence executes and releases the no-operation/rotate
object without poisoning the session.

A fourth semantic shape now admits only the non-aliasing v6 rotate followed by
no-operation form. It independently rechecks the rotate data/code live-ins,
both code encryptions, rotation result, register masks, exact continuity,
pointer successors, and budget-exhausted completion. The internal-alias form
where rotate rewrites the second instruction remains rejected.

That non-aliasing rotate/no-operation shape now has a distinct backend identity
and canonical x86-64/AArch64 Windows COFF. Verification reconstructs semantic
admission, exact v6 key/target assumptions, COFF structure, and canonical bytes.

Its dedicated relocation-free load image proves exact extraction, ISA alignment,
and strict W^X. Shape-specific typestate admits exact copy, same-mapping
RW-to-RX, complete instruction synchronization, and retained release evidence.
The platform adapter transactionally allocates, copies, protects, synchronizes,
and releases this exact image; failed release retains retry ownership.

ABI preparation derives both code encryptions, the rotate data write, and the
exact two-step exit while permitting only dead accumulator and I/O rebasing.
Binding accepts only the exact synchronized rotate/no-operation executable.

A caller-owned runner now receives only that exact bound view. Runner failure
restores the complete rebased entry snapshot, and returned status/state is
admitted through exact semantic completion.

The persistent process host projects that exact bound call through the existing
`MBNPC1` protocol and validates returned mapping/state/buffer evidence before
semantic completion. The foreign call stays isolated in the worker. Real x86-64
POSIX-worker evidence executes and releases the rotate/no-operation object
without poisoning the session; no AArch64 runtime execution is claimed.

Additional multi-step shapes stay unsupported until each receives equally
explicit semantic and native proof.

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
- Retained Linux x86-64 phase evidence now binds 225 raw samples to the
  clean producer under `benchmarks/interpreter/evidence/`, in the
  `2026-09-24-aot-process-phases-linux-x86_64/` bundle. It records exact
  preparation, load/release, one-shot lifecycle, resident transition, and
  interpreter
  timing with median, observed range, inclusive IQR, resource use, source
  hashes, and zero retained-sample failures. Equivalent JIT comparison belongs
  to the later `guarded-self-modification-jit` milestone, which depends on
  this AOT work and is not yet implemented.
## References

- [Tiered Native Execution](../../adr/tiered-native-execution.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/tiered-native-execution.md`
- `docs/technical/adr/verification-trust-boundary.md`
