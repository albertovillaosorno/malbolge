# Apollo AGC runner bootstrap

`apollo_agc_runner.c` is project-authored MIT-licensed guest C for the future
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

The runner itself remains repository-authored MIT material regardless of which
historical image is selected as input.

## Native debug run

From the repository root:

```text
malbolge src/examples/programs/contract/self_host/apollo-agc/apollo_agc_runner.c
```

Expected output is exactly `OK\n`. Native execution is only debug scaffolding;
completion requires a verifier-accepted `malbolge-2026` artifact executing the
historical Luminary workload inside Malbolge semantics.

## Deterministic parity harness

`apollo_agc_parity.c` includes the runner as guest C and exercises bounded
machine vectors for one's-complement arithmetic, erasable/fixed bank selection,
superbank behavior, switched and fixed-fixed memory, prohibited fixed-memory
writes, basic opcode families, quarter-code operations, INDEX state, and indexed
fetch. It also reruns the embedded rope smoke program.

```text
malbolge src/examples/programs/contract/self_host/apollo-agc/apollo_agc_parity.c
```

The exact transcript is `AGC-PARITY-v1
OK
`. This harness is deliberately
freestanding so the same source can later be lowered to `.malbolge` and compared
byte-for-byte with native C. Passing these bounded vectors does not claim full
Block II or Luminary conformance.
