# Self-hosting examples

`examples/self_host/` holds source fixtures and reserved output locations for
the long-term self-hosting conformance goal.

- `hello-world/` contains a self-checking freestanding C stress fixture. Its
  native CLI execution proves only debug scaffolding and exact byte
  preservation; no generated Malbolge artifact is checked in.
- `stress/` contains five compact self-checking compiler stress fixtures with
  fixed oracles and no hosted dependencies.
- `snake/` contains a Linux-only playable turn-based Snake fixture whose guest
  source uses only fundamental Malbolge byte input/output intrinsics.
- `doom/` reserves the future canonical location for `doom.malbolge`. Generated
  products remain local and ignored.
- `apollo-agc/` contains the project-authored Block II AGC runner bootstrap
  for the future Luminary 099 demonstration.
- `rv32i/` contains a project-authored base RV32I interpreter bootstrap for
  execution as a future `malbolge-2026` artifact.

A checked-in source example may exercise the admitted deterministic C surface,
but native execution never counts as C-to-Malbolge lowering, guest-runtime,
self-hosting, or conformance evidence. Generated `.malbolge` products belong
here only after the compiler produces them and independent verification admits
them.

## Flagship demonstration sequence

The intended demonstration order is DOOM, Apollo 11 Luminary on the AGC runner,
RV32I machine code on the RV32I runner, then compiler self-hosting. This order
is a demonstration milestone sequence; the compiler's existing technical TODO
dependency graph remains authoritative for implementation prerequisites.

## Cross-backend parity harnesses

Snake, Apollo AGC, and RV32I each carry a freestanding `*_parity.c` harness.
The harness includes the checked-in guest implementation, exercises internal
state transitions against fixed constants, and emits one canonical transcript.
Today that same source runs through the native `.c` debug path. Once C-to-
Malbolge lowering exists, the harness itself is compiled to `.malbolge` and the
final artifact must emit byte-identical output under the selected Malbolge
profile.

The oracle therefore does not need a host-only rewrite when the backend arrives.
A parity-harness success is bounded evidence for the covered vectors. It does
not close the owning application TODO until the declared generated artifact and
full workload also exist.
