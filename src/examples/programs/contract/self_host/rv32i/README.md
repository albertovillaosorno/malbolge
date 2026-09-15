# RV32I runner bootstrap

`rv32i_runner.c` is a project-authored MIT-licensed bootstrap interpreter for
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
repository-authored code. The runner therefore remains MIT-licensed project
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
