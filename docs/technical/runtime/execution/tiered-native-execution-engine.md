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

`execution/native/coff.rs` now provides a second, independent structural gate for
those Windows objects. It parses COFF bytes directly in safe Rust rather than
trusting Clang/LLVM diagnostics, requires machine identity to match the native
key, requires exactly one executable/non-writable `.text` section and the exact
`malbolge_native_region_apply` external function, rejects unexpected external
functions or undefined external symbols, and admits relocations only when their
targets are defined inside the same object. ARM64's compiler-generated `.rdata`
constant relocations therefore remain valid while host-library dependencies fail
closed. The result is named `StructurallyAdmittedNativeObjectArtifact`; it still
has no semantic execution authority.

`execution/native/direct.rs` now crosses that semantic boundary for one minimal
native program only: a direct deoptimization stub. The x86-64 sequence is
`mov eax, 1; ret`; the AArch64 sequence is `mov w0, #1; ret`. Both are wrapped in
a deterministic minimal COFF object with timestamp zero, one executable `.text`,
one external entry symbol, and no relocations. Independent hex fixtures freeze
the complete 117-byte x86-64 and 119-byte AArch64 objects. Promotion to
`VerifiedDeoptNativeObjectArtifact` first requires structural COFF admission and
then exact equality with the canonical object bytes. A changed opcode can remain
structurally valid but is rejected semantically.

This verified stub never reads the state argument, never commits guest-visible
state, and always returns native guard-miss status `1`, forcing deterministic
deoptimization to the normative interpreter. It is therefore the first
semantically admitted native artifact but intentionally provides no acceleration.
Development evidence links both ISA objects and executes the x86-64 DLL with a
null state pointer, returning `1`; direct region-effect fast paths remain open.

The next reviewed template is `direct-initial-halt`. Admission requires an exact
one-effect IR: zero entry registers/input/output counters, no input/output
effect, no memory live-ins or writes, no prior termination, unchanged exit
observation except `HaltInstruction`, terminated one-step outcome, and budget
one. Both ISAs preflight the ABI state before committing only the termination
byte. Complete COFF fixtures freeze the generated objects and object-byte
tampering fails semantic admission after structural COFF acceptance. Development
evidence links both ISA objects; x86-64 execution proves valid state returns
`applied=0` with only termination changed, while accumulator mismatch and null
state return guard miss without mutation. This is the first accelerated
state-applying native subset; all other IR still requires deopt/bootstrap/VM.

`select_verified_direct_native()` now removes direct-backend identity selection
from callers. It first classifies the IR: exact initial-halt uses the admitted
fast path, otherwise the selector emits and verifies the direct deopt stub. Only
program shape controls this fallback; an emission/admission error after selection
is propagated rather than silently retried. Non-Windows host formats fail
explicitly because direct ELF/Mach-O templates do not exist yet.

### Remaining Implementation

Semantic admission beyond the deopt and exact initial-halt templates, general
direct accelerated x86-64/AArch64 region-effect instruction selection, executable-memory
policy/invocation, durable native cache
serialization/storage/eviction, AOT/JIT orchestration, and the end-to-end tier
selector beyond this direct-template choice remain open. The interpreter remains
the only normative execution
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
- Safe-Rust COFF tests admit both real objects, including ARM64 internal
  relocations, while rejecting truncated bytes, mismatched machine identity, and
  a renamed callable entry. Structural admission remains non-semantic.
- Clang bootstrap objects remain structurally admitted but semantically
  untrusted. The direct deopt-only objects are the sole current semantically
  admitted machine-code artifacts; their complete bytes match independent
  fixtures and opcode tampering fails after structural admission.
- Development execution evidence links both direct ISA objects and runs the
  x86-64 function with a null state pointer, observing guard-miss status `1`.
## References

### Host Architecture Baseline

- `docs/technical/adr/host-cpu-and-accelerator-runtime-baseline.md`

- [Tiered Native Execution](../../adr/tiered-native-execution.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/tiered-native-execution.md`
- `docs/technical/adr/verification-trust-boundary.md`
