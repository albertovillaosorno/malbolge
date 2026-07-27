# Native x86-64 and AArch64 backends

## Status

Active bootstrap; direct ISA backends proposed

## Purpose

Implement native-code emitters for x86-64 and AArch64 behind one execution-IR
backend contract. Architecture-specific register allocation, instruction
selection, calling conventions, executable-memory handling, instruction-cache
synchronization, and hardening remain adapters rather than VM semantics.

## Scope

This document governs the following declared TODO scope:

- `vm/`
- `execution/`
- `tests/vm/`
- `benchmarks/interpreter/`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`native-x86-64-and-aarch64-backends`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

A shared bootstrap host-code path is now implemented under
`execution/native/main.rs`. It consumes portable effect IR, validates structural
state/input/output/memory flow, renders deterministic freestanding C23, and
binds the candidate to the same collision-safe `NativeArtifactKey` used by the
cache identity layer. Pinned Clang 22.1.8 compiles that source into real Windows
COFF object candidates for both x86-64 and AArch64.

A safe-Rust COFF parser now structurally admits those compiler outputs without
invoking LLVM inspection tools. Admission binds the COFF machine to the target
ISA, requires the exact callable entry in executable/non-writable `.text`, and
rejects unresolved external dependencies. Internal ARM64 relocations to defined
`.rdata` constants are allowed. Structural admission deliberately stops before
semantic equivalence or execution authority.

A first direct backend now exists for the safe fallback case. It emits canonical
minimal COFF directly in Rust for x86-64 and AArch64, with machine code that only
returns guard-miss status `1`. Complete object bytes are independently frozen;
semantic admission requires exact object equality after structural COFF checks.
The direct stub therefore cannot mutate guest state and always deoptimizes. It is
not the region-effect fast-path backend required to complete this TODO.

A second direct template now admits the exact initial-halt subset and is the first
state-applying fast path. It verifies zero entry registers/counters and live
termination before writing only the halt termination byte. Any mismatch returns
guard miss without mutation. Complete independently rendered COFF fixtures bind
both ISA implementations; x86-64 execution evidence covers hit, miss, and null
state, while ARM64 object linkage is verified on the development host. This
remains a deliberately tiny subset rather than general instruction selection.

`direct-halt-registers` now covers the same halt-only effect across arbitrary
32-bit entry registers. The x86-64 owner emits immediate comparisons; the
AArch64 owner emits reviewed `movz`/`movk` immediate materialization. Complete
independent object fixtures cover nontrivial register values, and x86-64 native
execution proves exact-register hit plus one-register atomic miss. This extends
parameterization, not the admitted guest-effect surface.

This does not complete this TODO. The bootstrap deliberately delegates
instruction selection to Clang and stores compiler output only as an
`UntrustedNativeObjectArtifact`. Clang-produced structurally admitted COFF remains semantically untrusted. A
direct deopt-only emitter/verifier is implemented for both ISAs; accelerated
direct region-effect emitters, executable-memory handling, calling/runtime
integration, and instruction-cache synchronization remain unimplemented.

## Invariants

- x86-64 and AArch64 are first-class host targets, consume the same portable
  execution IR, and independently pass cross-backend differential suites
  including executable-memory and instruction-cache edge cases.
- Native cache identity includes host ISA and every assumption required by the
  compiled region.
- Bootstrap lowering performs all local guards before the first guest-visible
  write; guard failure never commits a partial output, memory, register, cursor,
  or termination transition.
- Compiler-produced object bytes remain untrusted until an independent native
  admission boundary proves behavior against verifier-owned effect evidence.
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
  differential results against independent specification-conformant
  implementations; the historical interpreter is compared only on its documented
  agreement domain.
- Prerequisite completion evidence: `tiered-native-execution-engine`.
- Bootstrap evidence: `tests/tiered_execution.rs` verifies deterministic source,
  exact cache-key binding, collapsed repeated writes, preflight-before-commit,
  target/backend rejection, real x86-64/AArch64 COFF generation using pinned
  Clang 22.1.8, direct safe-Rust COFF parsing, ARM64 internal relocation closure,
  and fail-closed mutation rejection. Direct-deopt evidence additionally uses
  independent complete-object fixtures, rejects a one-byte opcode mutation after
  structural admission, links both ISA objects, and executes x86-64 guard miss
  without dereferencing its state pointer.
- Performance evidence pending: raw measurements plus a reproducible
  scaling/statistical summary tied to exact workload and hardware/software
  identity.
## References

### Host Architecture Baseline

- `docs/technical/adr/host-cpu-and-accelerator-runtime-baseline.md`

- [Tiered Native Execution](../../adr/tiered-native-execution.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/tiered-native-execution.md`
- `docs/technical/adr/verification-trust-boundary.md`
