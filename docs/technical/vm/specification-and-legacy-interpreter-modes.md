# Specification And Legacy-Interpreter Execution Modes

- Status: Proposed
- Planning identity: `specification-and-legacy-interpreter-modes`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Specification Authority And Malbolge
  Evolution](../adr/specification-authority-and-malbolge-evolution.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

## Purpose

Make specification-conformant execution the only normal Malbolge semantics while
retaining an explicitly named `legacy-ben` execution mode for archaeology,
differential diagnosis, and historical-corpus study.

## Proposed Model

The default VM implements the normative 1998 specification plus the selected
versioned extension profile. It does not emulate known C-interpreter defects.

`legacy-ben` is an opt-in implementation-compatibility mode. It may reproduce
selected observable behavior of Ben Olmstead's C interpreter, including known
specification disagreements, only when that behavior can be modeled without
relying on host undefined behavior.

The mode identity is part of traces, diagnostics, benchmark metadata, and cache
keys. A result produced in `legacy-ben` cannot satisfy a specification
conformance proof or verifier obligation.

## Invariants

- Normal execution always follows the selected normative specification profile.
- `<` is input and `/` is output in normal classic execution.
- A non-graphical current instruction terminates normal classic execution.
- `legacy-ben` is never selected implicitly from a program, corpus, cache, or
  historical filename.
- Undefined C behavior is diagnosed or modeled explicitly; the modern VM never
  invokes undefined host behavior to imitate the original interpreter.
- Compiler output and verifier acceptance target normative profiles, not
  `legacy-ben`.

## Failure Behavior

An unknown execution mode or unsupported legacy behavior fails explicitly.
Failure to emulate a historical defect never changes the normative VM semantics.

## Verification

- Specification fixtures must pass in normal mode.
- Deliberate discrepancy fixtures must demonstrate the expected difference
  between normal mode and `legacy-ben` where the legacy behavior is supported.
- Every legacy behavior is tied to a documented historical defect or
  discrepancy.
- Differential testing against `tools/malbolge/main.c` is restricted to states
  where invoking that interpreter is defined and safe.

## Implementation Status

Not implemented.
