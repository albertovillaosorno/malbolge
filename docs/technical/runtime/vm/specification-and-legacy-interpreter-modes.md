# Specification And Legacy-Interpreter Execution Modes

## Status

Active implementation

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

### Model

`Machine` is always the normative 1998 classic machine. Its constructors,
`step`, `run`, and tracing APIs cannot select historical behavior.

`ExecutionMachine` is the explicit mode-selection facade. Construction requires
an `ExecutionMode` supplied by the caller. `ExecutionMode::Specification` routes
to normative semantics. `ExecutionMode::LegacyBen` is accepted only when the
Cargo `legacy-ben` feature is enabled; default builds reject it with the
mode-tagged `LegacyBenDisabled` diagnostic.

`ExecutionMode::stable_id()` is the stable mode identity for traces,
diagnostics, benchmark metadata, and cache-key composition. The values are
`specification` and `legacy-ben`. Callers must not derive a mode from a program,
corpus name, cache entry, or historical filename.

`ExecutionMode::is_verifier_eligible()` is true only for `Specification`.
`ExecutionMachine::verifier_eligible()` projects the same trust-boundary fact.
A `legacy-ben` result therefore cannot satisfy compiler or verifier conformance
obligations even when its execution completed successfully.

### Selected Legacy Behavior

The legacy compatibility surface models only reproducible behavior that can be
expressed safely:

- H-001 reverses the historical `<` and `/` I/O behavior. The raw decoded byte
  remains visible in traces while the selected mode determines its effect.
- H-002 models a non-graphical current cell as bounded non-progress. One
  requested step returns `Continued` without changing registers, memory, I/O, or
  termination; bounded `run` therefore exhausts its budget instead of hanging
  the host process.
- H-003 is not reproduced. Sources with fewer than two recurrence words return
  the ordinary deterministic load failure with `legacy-ben` attached to the
  execution diagnostic.
- H-004 is not reproduced. A legacy transition that would expose an invalid
  self-encryption index returns `UnsupportedLegacyBehavior` atomically rather
  than performing an out-of-bounds table access.

Host-dependent text I/O, locale classification, character-set behavior, integer
width, and historical memory-model assumptions are not compatibility semantics.
The modern implementation never invokes host undefined behavior to imitate the
1998 C program.

### Trace And Diagnostic Identity

Every `StepTrace` carries its explicit `ExecutionMode`. Normative `Machine`
traces always report `Specification`; traces emitted through `ExecutionMachine`
report the facade's immutable selected mode.

Construction and transition failures from the facade are wrapped in
`ExecutionError`, which carries both the stable mode and a typed failure kind.
Unknown textual mode names return `ExecutionModeParseError` and never fall back
to a default.

### Implementation Status

The explicit mode facade, feature gate, stable identity, verifier eligibility,
selected legacy behavior, mode-tagged traces, and mode-tagged diagnostics are
implemented. The typed TODO remains active until its declared repository-wide
validation command passes at retirement time.

## Invariants

- Normal `Machine` execution always follows the selected normative specification
  profile and cannot opt into historical defects.
- `<` is input and `/` is output in normal classic execution.
- A non-graphical current instruction terminates normal classic execution.
- `legacy-ben` is never selected implicitly from a program, corpus, cache, or
  historical filename.
- Default Cargo builds reject `legacy-ben`; enabling the feature still requires
  explicit runtime mode selection.
- Undefined C behavior is diagnosed or modeled explicitly; the modern VM never
  invokes undefined host behavior to imitate the original interpreter.
- Compiler output and verifier acceptance target normative profiles, not
  `legacy-ben`.
- Stable mode identity must participate in any benchmark record or semantic
  cache key that can contain execution results.

## Failure Behavior

An unknown execution mode fails parsing explicitly. Requesting `legacy-ben` in a
build without the feature returns `LegacyBenDisabled`. Unsupported historical
behavior returns a mode-tagged typed diagnostic and does not partially commit
state. Failure to emulate a historical defect never changes normative VM
semantics.

## Verification

- `tests/vm/modes.rs` proves default-build rejection of `legacy-ben`, explicit
  mode parsing, stable identity, verifier eligibility, and normative facade
  equivalence.
- With the `legacy-ben` feature, the same suite proves H-001 reversed I/O, H-002
  bounded non-progress, H-003 deterministic loader rejection, and H-004 atomic
  unsupported-behavior rejection.
- Mode tests assert `StepTrace.mode` and `ExecutionError.mode()` on positive and
  discrepancy paths.
- `tests/compatibility/specification/spec-io-roundtrip.malbolge` remains the
  shared H-001 source fixture; the historical interpreter remains untouched.
- Expected durable artifact surface: `vm/`, `execution/`, `tests/vm/`,
  `benchmarks/interpreter/`.
- Historical interpreter comparison is limited to its documented agreement
  domain.
- Prerequisite completion evidence: `safe-rust-malbolge-vm`,
  `historical-undefined-behavior-catalogue`.

## References

- [Specification Authority And Malbolge
  Evolution](../../adr/specification-authority-and-malbolge-evolution.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)
- [Historical Interpreter Defects And Specification
  Discrepancies](../../specification/historical-undefined-behavior.md)

### Governing ADR Paths

- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
- `docs/technical/adr/verification-trust-boundary.md`
