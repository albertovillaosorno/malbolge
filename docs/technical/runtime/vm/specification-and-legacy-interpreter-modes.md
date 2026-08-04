# Interpreter Authority And Specification Comparison Modes

## Status

Active implementation

## Purpose

Make original-interpreter behavior the normal and verifier-eligible classic
semantics while retaining the written specification as an explicit comparison
mode.

## Scope

- `vm/`
- `execution/`
- `tests/vm/`
- `benchmarks/interpreter/`

## Current Behavior

### Model

`Machine` executes `ExecutionMode::Interpreter` by default. Its `step`, `run`,
`step_traced`, and `run_traced` entry points all use the same authority.
Observation never changes semantics.

`ExecutionMachine` permits explicit mode selection:

- `Interpreter` follows defined, reproducible behavior of the original
  interpreter and is verifier eligible;
- `Specification` follows the contradictory prose rules for comparison and is
  not verifier eligible.

Stable identifiers are `interpreter` and `specification`. The parser aliases
`reference-interpreter` and the former name `legacy-ben` to `interpreter` for
backward compatibility. Unknown names fail explicitly.

### Interpreter Authority

The portable interpreter surface includes:

- `<` as output and `/` as input;
- bounded non-progress for a current cell outside graphical ASCII;
- deterministic byte input, byte output, EOF, ternary arithmetic, decode,
  self-modification, and pointer transitions.

One non-graphical step returns `Continued` without changing registers, memory,
I/O, or termination. A bounded `run` therefore exhausts its budget rather than
hanging the host process.

### Undefined Historical Behavior

The modern VM does not reproduce C undefined behavior. A source with too few
recurrence words is rejected. A transition that would index the encryption table
outside its defined range returns
`UnsupportedInterpreterBehavior::InvalidSelfEncryptionTarget` atomically.
Locale, text mode, character set, host integer width, and old memory models are
not guest semantics.

### Specification Comparison

`ExecutionMode::Specification` retains `<` as input, `/` as output, and
immediate termination on a non-graphical current cell. It exists for research
and migration analysis only. Its traces remain mode tagged and its results
cannot satisfy
compiler or verifier obligations for `malbolge-1998`.

### Profile Boundary

`ProfileKind::HistoricalConformance` uses interpreter authority. Current and
versioned profiles retain their own declared semantics even when their geometry
matches the historical profile.

## Invariants

- Default, traced, profiled-historical, C-oracle, native, and accelerated
  classic paths agree on observable state and I/O.
- Specification comparison is never selected implicitly.
- Undefined C behavior is diagnosed before mutation.
- Stable mode identity participates in traces and semantic cache boundaries.
- The former `legacy-ben` spelling is only a parser alias.

## Failure Behavior

Unknown modes fail parsing. Unsupported historical C behavior returns a
mode-tagged typed error without partial state publication. Optional backends may
decline execution, but they may not substitute specification semantics.

## Verification

- `tests/vm/modes.rs` covers authority, comparison, mode identity, I/O,
  non-progress, loader rejection, and atomic undefined-behavior rejection.
- `tests/vm/conformance.rs` covers classic public transitions.
- `tests/vm/differential.rs` matches the independent C semantic signature.
- `tests/vm/cuda_step.rs` and `tests/vm/cuda_run.rs` compare CUDA classic paths
  with the interpreter-authority Rust VM.
- `tests/vm/profile_machine.rs` proves `malbolge-1998` profile equivalence.

## References

- [Interpreter Authority And Malbolge
  Evolution](../../adr/specification-authority-and-malbolge-evolution.md)
- [Historical Interpreter Behavior And Undefined C
  Boundaries](../../specification/historical-undefined-behavior.md)
- `docs/bibliography/specifications-and-standards/malbolge/`
  `ben-olmstead-2014-interview.md`

### Governing ADR Paths

- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
- `docs/technical/adr/verification-trust-boundary.md`
