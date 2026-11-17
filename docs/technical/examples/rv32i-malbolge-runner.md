# RV32I runner in Malbolge

## Status

Proposed

## Purpose

Run standard RV32I machine code inside a project-authored deterministic RV32I
interpreter whose own execution occurs under `malbolge-2026`. This creates a
second-machine demonstration with a contemporary standardized ISA and provides
a compact executable-bytecode workload before final C compiler self-hosting.

## Scope

This document governs the following declared TODO scope:

- `src/examples/programs/contract/self_host/rv32i/`
- `tests/applications/rv32i/`
- `benchmarks/applications/rv32i/`
- `compiler/`
- `runtime/`

## Current Behavior

`rv32i_runner.c` is a freestanding project-authored bootstrap implementing the
base RV32I register file, little-endian memory, U/J/I/B/S/R formats, branches,
jumps, byte/half/word loads and stores, integer ALU operations, FENCE handling,
and EBREAK termination. Its embedded machine-code program computes a looped
sum, stores the result, and reaches a fixed architectural oracle before `OK\n`
is emitted by the outer guest fixture.

The immediate acceptance step is to compile **only** `rv32i_runner.c` as
ordinary C, run the generated Malbolge guest, and compare it with an
independently executed native runner oracle. There is no RISC-V-specific
translation path; a refusal must identify the missing general C capability.
This does not require completing the Apollo AGC demonstration.

The bootstrap does not yet ingest arbitrary binaries and has no completed
Malbolge artifact. The external binary format, deterministic platform, broader
conformance corpus, reference differential execution, and generated execution
remain open.

`rv32i_parity.c` supplies a **native-only C parity fixture**, separate from
the runner compilation target. `tests/cli_native_debug.rs` tests the complete
native runner independently. Guest parity is established by executing the
one generated `.malbolge` artifact from `rv32i_runner.c`, not by translating
test harnesses as extra guest programs.

### Standards and licensing boundary

The runner is new project-authored Apache-2.0 code. It is implemented from the
public
RISC-V ISA contract rather than copied from another emulator. The RISC-V
Instruction Set Manual is published under CC-BY-4.0; repository documentation
must retain standards attribution while implementation code remains independent.

## Bounded Acceptance (2026-11-16)

- The supported machine contract is a pinned unprivileged RV32I base ISA
  revision with fixed memory geometry, deterministic binary loading and
  explicit trap/exit behavior. Prove one toolchain-built RV32I binary under
  real guest execution against an independent oracle. No privileged modes,
  arbitrary ISA extensions, general OS, Linux syscall ABI, or second guest
  C translation target is part of this demonstration.

## Invariants

- The runner implements RV32I instruction semantics inside guest execution.
- Register `x0` remains zero after every instruction.
- Memory behavior and misalignment policy are deterministic and documented.
- Host code may transport binary bytes but may not execute RISC-V instructions
  or replace the guest interpreter.
- Native debug execution is comparison scaffolding, not completion evidence.
- Completion requires a verifier-accepted `malbolge-2026` artifact.

## Failure Behavior

Illegal instructions, unsupported platform requests, malformed binary input,
misaligned accesses outside the selected execution-environment policy, resource
exhaustion, or differential mismatches fail explicitly.

## Verification

Completion requires:

- ordinary C-to-Malbolge compilation and guest execution of the *single*
  RV32I runner, with separate native parity and whole-program oracle tests;
- a documented deterministic RV32I execution environment and binary format;
- instruction-family conformance vectors covering the complete base ISA;
- differential execution against an independent reference implementation;
- at least one compiler-produced RV32I workload, not only hand-encoded words;
- deterministic byte-stream ingestion and observable output/exit semantics;
- generated-artifact size, memory, instruction-count, and runtime measurements;
- translation validation and final execution under `malbolge-2026`.

## References

- [Compiler Pipeline And Guest
  Runtime](../adr/compiler-pipeline-and-guest-runtime.md)
- [Verification Trust
  Boundary](../adr/verification-trust-boundary.md)
