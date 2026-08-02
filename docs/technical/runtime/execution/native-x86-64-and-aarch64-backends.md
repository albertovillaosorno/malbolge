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
`src/runtime/tiered-execution/adapter-outbound/native/main.rs`. It consumes
portable effect IR, validates structural
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
minimal COFF directly in Rust for x86-64 and AArch64, with machine code that
only
returns guard-miss status `1`. Complete object bytes are independently frozen;
semantic admission requires exact object equality after structural COFF checks.
The direct stub therefore cannot mutate guest state and always deoptimizes. It
is
not the region-effect fast-path backend required to complete this TODO.

A second direct template now admits the exact initial-halt subset and is the
first
state-applying fast path. It verifies zero entry registers/counters and live
termination before writing only the halt termination byte. Any mismatch returns
guard miss without mutation. Complete independently rendered COFF fixtures bind
both ISA implementations; x86-64 execution evidence covers hit, miss, and null
state, while ARM64 object linkage is verified on the development host. This
remains a deliberately tiny subset rather than general instruction selection.

`direct-halt-registers` revision 5 now covers the same halt-only effect across
arbitrary 32-bit entry registers and full 64-bit input/output counter
observations.
The x86-64 owner emits `mov rdx, imm64` plus exact counter comparisons; the
AArch64
owner emits all four reviewed `movz`/`movk` halfwords. Every guard branches to
one
non-mutating miss return and only termination is committed. Independent
495/564-byte objects bind counters above `u32::MAX`; counter, opcode, and
revision
mismatch fail closed. Development execution proves x86-64 full-width counter hit
and atomic counter miss; independent fixture decoding confirms AArch64
full-width
immediates and one common miss target. This widens admitted entry state, not the
guest-effect surface.

`direct-halt-fetch` revision 2 binds a VM-decoded graphical `v` live-in to halt
termination. Both ISA owners reuse the fetched-terminal template: full entry
observation, memory pointer, exact IR footprint, exact `memory[C]`, and prior
termination are guarded before writing only tag `1`. Independent complete
objects
are 535/628 bytes. x86-64 development execution proves hit and atomic
live-in/capacity/null misses; independent AArch64 decoding confirms the expected
guards, halt tag, and common miss target.

`direct-non-graphical` revision 2 is the first reviewed direct template with an
exact memory live-in. The VM-owned graphical-cell predicate admits one
non-graphical live-in at `C`; each ISA guards the full entry observation, memory
pointer, exact IR footprint, exact `memory[C]`, and prior termination before
committing only termination tag `2`. Independent complete objects are 538/631
bytes. x86-64 development execution proves hit and atomic live-in/capacity/null
misses; independent AArch64 decoding confirms the expected guards and common
miss
target. This reads verified memory evidence but still performs no guest-memory
or
I/O write.

`direct-no-operation` revision 2 is the first reviewed non-terminal template and
first guest-memory-writing fast path. VM-owned no-op classification, `XLAT2`,
and
profile successor functions independently derive the required IR. Each ISA
reuses
the fetched-cell guards, then atomically writes the encrypted code cell and
exact
next `C/D`. Independent complete objects are 557/658 bytes. x86-64 development
execution proves `memory[5]:77->65`, `C:5->6`, `D:7->8` plus atomic
live-in/capacity/null misses; independent AArch64 decoding confirms the same
commit and one common miss target.

`direct-jump-data` revision 1 adds the first instruction-specific semantic data
read. Two distinct live-ins bind code and data cells; VM-owned decode,
encryption,
and successor helpers derive the transition while `C == D` remains rejected.
Each ISA guards the complete entry, exact 125-word IR footprint, code live-in
35,
and data live-in 123 before atomically writing code 93 and `C/D` 6/124.
Independent complete objects are 564/699 bytes. x86-64 development execution
proves exact hit behavior plus atomic live-in/footprint/null misses; independent
AArch64 decoding confirms both reads, the commit, and one common miss target.

`direct-jump-code` revision 1 adds the exact post-jump encryption sequence.
Three
distinct live-ins bind entry code, entry data, and the graphical cell selected
by
`memory[D]`; VM-owned decode must classify the entry code cell as `i`. Each ISA
guards the complete entry, exact 13-word footprint, values 93/11/68 at addresses
5/7/11, and prior live termination before atomically writing `memory[11]=33` and
`C/D=12/8`. Independent complete objects are 622/731 bytes. x86-64 development
execution proves exact hit plus atomic code/data/encryption/footprint/null
misses
and twelve common-target `rel32` branches; independent AArch64 decoding confirms
three reads, the commit, and twelve branches to one miss. Address aliasing
remains
rejected.

`direct-rotate` revision 1 adds the first reviewed template with two
guest-memory
writes. Two distinct live-ins bind entry code and data cells; VM-owned decode
must
classify the code cell as `*`, while `profile_rotate()` derives the exact data
and
accumulator result. Each ISA guards the complete entry, exact 9-word footprint,
`memory[5]=34`, `memory[7]=10`, and prior live termination before atomically
writing data 1594326, encrypted code 122, and `A/C/D=1594326/6/8`. Independent
complete objects are 578/732 bytes. x86-64 development execution proves exact
hit
plus atomic code/data/footprint/null misses; independent AArch64 decoding
confirms
two reads, both writes, all register commits, and eleven branches to one miss.
Address aliasing remains rejected.

All memory-backed templates consume the exact key-bound IR footprint as their
ABI
capacity guard before any dereference. Crazy and I/O effects remain outside this
reviewed subset.

This does not complete this TODO. The bootstrap deliberately delegates
instruction selection to Clang and stores compiler output only as an
`UntrustedNativeObjectArtifact`. Clang-produced structurally admitted COFF
remains semantically untrusted. Reviewed direct terminal, no-op, jump-code,
jump-data, and rotate emitters/verifiers are implemented for both ISAs; crazy
and
I/O selection,
executable-memory handling, calling/runtime integration, and instruction-cache
synchronization remain unimplemented.

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
  Clang 22.1.8, direct safe-Rust COFF parsing, ARM64 internal relocation
  closure,
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
