# Apollo AGC runner bootstrap

`apollo_agc_runner.c` is project-authored Apache-2.0-licensed guest C for the
future
Apollo 11 demonstration. It does not copy an existing AGC emulator. The current
bootstrap models 15-bit one's-complement words, Block II erasable/fixed memory
banking, the architectural A/L/Q/EB/FB/Z/BB register locations, and a useful
subset of the basic instruction families. A project-authored eight-instruction
rope smoke test must leave exact state before the fixture emits `OK\n`.

This is intentionally **not** claimed as Luminary-capable yet. The open TODO
requires the remaining Block II semantics, extracodes, editing registers,
interrupt/unprogrammed sequences, mission I/O behavior, deterministic rope
image ingestion, and execution of the real Apollo 11 Lunar Module software.

## Historical source boundary

The future historical payload is Luminary 099 / LMY99 revision 1, as preserved
by Virtual AGC and the MIT Museum transcription work. The commonly used
Apollo-11 transcription repository labels that source public domain. No
Luminary source or rope image is copied into this directory by the bootstrap;
the historical identity and exact assembled image must be pinned and verified
before the TODO can close.

The runner itself remains repository-authored Apache-2.0 material regardless
of which
historical image is selected as input.

## Native debug run

From the repository root:

```text
malbolge src/examples/programs/contract/self_host/apollo-agc/apollo_agc_runner.c
```

Expected output is exactly `OK\n`. Native execution is only debug scaffolding;
completion requires a verifier-accepted `malbolge-2026` artifact executing the
historical Luminary workload inside Malbolge semantics.

## Native parity versus whole-program execution

- **Guest C compilation target:** `apollo_agc_runner.c` only. The normal
  compiler produces one `.malbolge` artifact from this source; there is no special
  AGC/RISC-V compiler or second guest test program.
- **Native parity fixture:** `apollo_agc_parity.c` includes that runner
  and exercises deterministic machine-state and instruction vectors. It is a host test,
  **not** a second `.malbolge` translation target.
- **Separate whole-program test:** `tests/cli_native_debug.rs` runs the
  unmodified runner with the native debugging CLI, checking exit status and
  exact `OK` plus newline. The guest-artifact test must later run the generated
  Malbolge program and compare its actual behavior against that native oracle.

The parity fixture is executable today through the native debug CLI and emits
an exact canonical transcript. It does not claim that the guest compiler
already supports the runner or that a historical mission/external ISA workload
is complete.
