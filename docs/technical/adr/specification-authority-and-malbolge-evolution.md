# Interpreter Authority And Malbolge Evolution

## Status

Accepted; supersedes the previous specification-first decision in this file.

## Decision ID

`jig.malbolge.technical.specification-authority-and-malbolge-evolution`

## Context

Malbolge has two primary 1998 artifacts: Ben Olmstead's prose specification and
his C interpreter. They disagree observably. The prose assigns `<` to input and
`/` to output, while the interpreter does the reverse. The prose terminates on a
non-graphical current cell, while the interpreter performs no state transition
and repeatedly revisits that cell.

In a 2014 interview, Olmstead said the `33..126` behavior was intended and that,
on that point, the specification contained the bug. The preserved source
independently proves the implemented behavior. Compatibility with the ecosystem
therefore requires a deterministic account of the interpreter, not silent
preference for contradictory prose.

The original C program also contains host assumptions and undefined behavior.
Those cannot become portable language semantics merely because they occur in the
historical implementation.

## Decision

For the frozen `malbolge-1998` profile, Ben Olmstead's original interpreter is
the semantic authority wherever its behavior is defined, reproducible, and
independent of accidental host behavior.

The written specification remains important explanatory and comparison evidence.
`ExecutionMode::Specification` exposes that comparison explicitly, but it is not
the default and is not verifier eligible.

The authoritative classic rules include:

- `<` emits the low byte of `A`;
- `/` reads one byte into `A`, or the classic EOF word when input is exhausted;
- a current cell outside `33..126` performs one bounded non-progress step rather
  than terminating;
- all other defined arithmetic, decode, rotation, crazy-operation,
  self-modification, and pointer behavior follow the preserved interpreter.

Modern implementations must not execute historical C undefined behavior.
Insufficient recurrence input, invalid self-encryption table indices, locale
classification, text-mode translation, and host integer or memory-model quirks
fail safely or are defined by an explicit versioned profile.

`ExecutionMode::Interpreter` is the default classic mode and the only
verifier-eligible classic execution mode. The parser accepts `legacy-ben` as a
backward-compatible alias for `interpreter`; it does not identify a second
language or feature-gated product line.

Current Malbolge remains a versioned living language. Profiles such as
`malbolge-2026.*` may deliberately retain or change documented behavior under
their own immutable identities. No profile silently inherits semantics from
another merely because word and memory geometry match.

## Advantages

- Preserves compatibility with programs and tools built around the original
  interpreter.
- Aligns the frozen historical profile with the author's stated intent.
- Keeps the prose disagreement available for explicit study.
- Separates deterministic interpreter behavior from undefined host-C behavior.
- Gives Rust, C, native, and accelerator implementations one portable target.

## Disadvantages

- Existing specification-first outputs and semantic signatures change.
- Some documents and tests must distinguish historical interpreter authority
  from later versioned profile semantics.
- The non-graphical behavior requires bounded host APIs to prevent an unbounded
  host hang.

## Consequences

- Classic Rust, independent C, profile-historical, native, and accelerator paths
  must agree with interpreter authority.
- `<` is output and `/` is input for `malbolge-1998`.
- Non-graphical execution consumes a requested step without state progress.
- Specification comparison is explicit and cannot satisfy verification.
- Undefined interpreter behavior remains a typed atomic failure.
- Differential signatures and compatibility fixtures bind to the new authority.
- The original interpreter remains immutable primary evidence.

## Rejected Alternatives

### Keep the prose specification as authority

Rejected because it contradicts both the preserved implementation and the
language author's later statement of intent, reducing historical compatibility.

### Reproduce every observable C behavior

Rejected because out-of-bounds accesses, uninitialized reads, locale dependence,
and historical memory-model assumptions are not deterministic portable
semantics.

### Remove specification comparison

Rejected because the discrepancy is historically important and useful for
research, diagnostics, and migration analysis.

## Evidence

- `src/interoperability/historical-malbolge/adapter-outbound/main.c` implements
  reversed I/O and non-progress outside `33..126`.
- `tests/vm/modes.rs` proves interpreter authority, explicit comparison mode,
  bounded non-progress, and safe rejection of undefined behavior.
- `tests/vm/differential.rs` and the independent C oracle share a reviewed
  interpreter-derived semantic signature.
- `docs/bibliography/specifications-and-standards/malbolge/`
  `ben-olmstead-2014-interview.md` records the author testimony and provenance.
