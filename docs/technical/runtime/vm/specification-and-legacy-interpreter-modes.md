# Specification And Legacy-Interpreter Execution Modes

## Status

Proposed

## Purpose

Make specification-conformant execution the only normal Malbolge semantics while
retaining an explicitly named `legacy-ben` execution mode for archaeology,
differential diagnosis, and historical-corpus study.

## Scope

This document governs the following declared TODO scope:

- `vm/`
- `execution/`
- `tests/vm/`
- `benchmarks/interpreter/`

## Current Behavior

### Proposed Model

The default VM implements the normative 1998 specification plus the selected
versioned extension profile. It does not emulate known C-interpreter defects.

`legacy-ben` is an opt-in implementation-compatibility mode. It may reproduce
selected observable behavior of Ben Olmstead's C interpreter, including known
specification disagreements, only when that behavior can be modeled without
relying on host undefined behavior.

The mode identity is part of traces, diagnostics, benchmark metadata, and cache
keys. A result produced in `legacy-ben` cannot satisfy a specification
conformance proof or verifier obligation.

### Implementation Status

Not implemented.

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

- Expected durable artifact surface: `vm/`, `execution/`, `tests/vm/`,
  `benchmarks/interpreter/`.
- Required evidence: specification fixtures, explicit legacy discrepancy
  fixtures, and differential traces against independent implementations; Ben
  interpreter comparison is limited to its documented agreement domain.
- Prerequisite completion evidence: `safe-rust-malbolge-vm`,
  `historical-undefined-behavior-catalogue`.
## References

- [Specification Authority And Malbolge
  Evolution](../../adr/specification-authority-and-malbolge-evolution.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
- `docs/technical/adr/verification-trust-boundary.md`
