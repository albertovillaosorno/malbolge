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

The bootstrap does not yet ingest arbitrary binaries and has no completed
Malbolge artifact. The external binary format, deterministic platform, broader
conformance corpus, reference differential execution, and generated execution
remain open.

### Standards and licensing boundary

The runner is new project-authored MIT code. It is implemented from the public
RISC-V ISA contract rather than copied from another emulator. The RISC-V
Instruction Set Manual is published under CC-BY-4.0; repository documentation
must retain standards attribution while implementation code remains independent.

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
