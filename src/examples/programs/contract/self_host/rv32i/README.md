# RV32I runner bootstrap

`rv32i_runner.c` is a project-authored Apache-2.0-licensed bootstrap
interpreter for
the 32-bit RISC-V integer ISA. It is written from the public ISA contract
rather
than copied from another emulator. The current bootstrap implements integer
registers, little-endian memory, U/J/I/B/S/R instruction formats, branches,
jumps, byte/half/word loads and stores, integer ALU operations, FENCE handling,
and EBREAK termination. ECALL/platform services are intentionally outside
this bootstrap and remain part of the open TODO.

The embedded project-authored machine-code smoke program computes the sum
`10 + 9 + ... + 1`, stores `55` at address 256, and executes EBREAK. The C
fixture validates the architectural state and emits exactly `OK\n`.

## Standards and licensing boundary

The RISC-V Instruction Set Manual is published by RISC-V International under
CC-BY-4.0. This directory incorporates no source code from an existing RISC-V
emulator; only the standardized instruction semantics are implemented in new
repository-authored code. The runner therefore remains Apache-2.0-licensed
project
code.

The open TODO is intentionally broader than this bootstrap. Completion requires
deterministic external RV32I binary ingestion, a documented minimal platform,
reference differential vectors, compiler-produced RV32I workloads, resource
measurements, and finally verifier-accepted execution after the runner itself is
lowered to `malbolge-2026`.

## Native debug run

From the repository root:

```text
malbolge src/examples/programs/contract/self_host/rv32i/rv32i_runner.c
```

Expected output is exactly `OK\n`. Native execution is debug scaffolding only;
it is not evidence that a RISC-V binary has executed inside Malbolge yet.

## Native parity versus whole-program execution

- **Guest C compilation target:** `rv32i_runner.c` only. The normal compiler
  produces one `.malbolge` artifact from this source; there is no special
  AGC/RISC-V compiler or second guest test program.
- **Native parity fixture:** `rv32i_parity.c` includes that runner and exercises
  deterministic machine-state and instruction vectors. It is a host test,
  **not** a second `.malbolge` translation target.
- **Separate whole-program test:** `tests/cli_native_debug.rs` runs the
  unmodified runner with the native debugging CLI, checking exit status and
  exact `OK` plus newline. The guest-artifact test must later run the generated
  Malbolge program and compare its actual behavior against that native oracle.

The parity fixture is executable today through the native debug CLI and emits
an exact canonical transcript. It does not claim that the guest compiler
already supports the runner or that a historical mission/external ISA workload
is complete.
