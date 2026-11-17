# Apollo 11 Luminary AGC in Malbolge

## Status

Proposed

## Purpose

Run the historically identified Apollo 11 Lunar Module AGC software inside a
project-authored Block II AGC interpreter whose own execution occurs under
`malbolge-2026`. The demonstration must execute the guidance software rather
than substitute host-side guidance, decoded telemetry, or prerecorded output.

## Scope

This document governs the following declared TODO scope:

- `src/examples/programs/contract/self_host/apollo-agc/`
- `tests/applications/apollo-agc/`
- `benchmarks/applications/apollo-agc/`
- `compiler/`
- `runtime/`

## Current Behavior

`apollo_agc_runner.c` is a freestanding project-authored bootstrap. It already
models 15-bit one's-complement words, the Block II erasable/fixed bank geometry,
architectural bank registers, fixed-fixed addressing, and a subset of basic
instructions sufficient to execute a real encoded AGC smoke program. The smoke
program reaches a fixed machine-state oracle and emits `OK\n` in native debug
execution.

The next milestone is compiling and executing **only** `apollo_agc_runner.c`
with the ordinary C-to-Malbolge workflow and independently comparing its real
guest behavior against its native C execution. No custom AGC
translator or host-executed guidance is a permitted shortcut. Missing language
support must be reported against the compiler with a reproducible failing C
source, not worked around with a special static fixture.

This is not yet a Luminary execution claim. Extracodes, full overflow behavior,
editing registers, interrupts and unprogrammed sequences, mission-specific I/O,
rope ingestion, and differential evidence remain incomplete.

`apollo_agc_parity.c` is a **native-only C parity fixture**. The independent
whole-program test lives in `tests/cli_native_debug.rs`; guest verification
compiles only `apollo_agc_runner.c` and compares its actual VM output with
the native runner oracle. The bounded test vectors do not prove full AGC
conformance.

### Historical and legal boundary

The intended historical payload is Luminary 099 / LMY99 revision 1 for the
Apollo 11 Lunar Module AGC. The widely used Virtual AGC/MIT Museum transcription
identifies the source as public domain. Repository admission still requires an
explicit pinned source identity, exact assembled rope-image identity, retained
attribution/provenance, and review under the repository legal boundary.

The AGC interpreter is new project-authored Apache-2.0 code. No third-party AGC
emulator implementation is copied into the runner.

## Invariants

- AGC instruction execution, memory banking, arithmetic, scheduler-relevant
  state, and mission I/O semantics execute inside the guest program.
- Host tooling may supply deterministic bytes and capture output; it may not
  execute AGC instructions or guidance algorithms on behalf of the guest.
- The pinned Luminary source/image identity remains separate from the
  project-authored runner and from generated Malbolge artifacts.
- A native C run is scaffolding and comparison evidence, not completion.
- Completion requires a verifier-accepted `malbolge-2026` artifact.

## Failure Behavior

Unsupported AGC instructions, invalid rope identities, resource exhaustion,
divergent reference traces, or target-profile failures are explicit failures.
The demonstration must never silently replace missing AGC behavior with a host
implementation.

## Verification

Completion requires:

- ordinary C-to-Malbolge build and real guest execution of the *single*
  AGC runner, with separate native parity and whole-program oracle tests;
- a pinned and reproducibly assembled Luminary 099 image with provenance;
- complete admitted Block II semantics for the exercised mission workload;
- independent reference-machine differential traces;
- at least one deterministic DSKY/mission scenario with a fixed state/output
  oracle;
- C guest-profile validation and native-debug comparison evidence;
- generated-artifact size, memory, instruction-count, and runtime measurements;
- translation validation and final execution under `malbolge-2026`.

## References

- [Compiler Pipeline And Guest
  Runtime](../adr/compiler-pipeline-and-guest-runtime.md)
- [Verification Trust
  Boundary](../adr/verification-trust-boundary.md)
- [Legal Research And Repository
  Boundary](../../legal/adr/legal-research-and-repository-boundary.md)
