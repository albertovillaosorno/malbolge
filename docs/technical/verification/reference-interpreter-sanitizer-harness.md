# Reference interpreter sanitizer harness

## Status

Active

## Purpose

Build the historical interpreter under AddressSanitizer and
UndefinedBehaviorSanitizer where supported, preserve failing fixtures, and use
the evidence to distinguish defined interpreter semantics from host-dependent
or undefined C behavior without editing Ben's source.

## Scope

This document governs the following declared TODO scope:

- `src/interoperability/historical-malbolge/`
- `tests/compatibility/`
- `benchmarks/interpreter/`

## Current Behavior

### Implemented Model

This record defines the contract that implementation must satisfy for
`reference-interpreter-sanitizer-harness`. The implementation may change
internal representation or language choices without changing the observable
behavior, trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

Implemented on pinned Windows x86-64 Clang 22.1.8. The runner verifies the
immutable source hash, generates a temporary `_halloc` compatibility unit,
compiles the untouched interpreter with AddressSanitizer and
UndefinedBehaviorSanitizer, and compares normalized findings against reviewed
JSON evidence.

The executable runner is
`src/automation/repository/composition/scripts/validate/`
`historical_interpreter_sanitizer.py`. Cases are declared in
`benchmarks/interpreter/sanitizer-cases.json`; reviewed results live in
`benchmarks/interpreter/evidence/windows-x86_64-sanitizer-findings.json`.
Both JSON authorities reject duplicate keys and invalid UTF-8 through the stable
sanitizer-harness error boundary before evidence comparison. Manifest and
reviewed-result JSON are admitted only as direct, non-redirected regular files,
with a one-MiB input bound and opened-inode identity checked before and after
reads. In-root source fixtures and the pinned historical source obey the same
regular-file and stable-snapshot rules, each with a one-MiB limit; fixture
locations cannot traverse outside the repository or follow linked directories.
The pinned source hash is verified before a byte-exact copy is staged in the
private temporary build directory; Clang compiles that verified snapshot, never
reopening the original pathname after verification. The original `main.c`
remains untouched and temporary source copies are deleted with the build.
FIFO and symlink substitutions fail without waiting for external input.
Case identifiers must be portable ASCII filename stems (at most 128 characters),
excluding path
separators, traversal, and Windows device names; case-insensitive duplicates
are rejected before any fixture file is written. Direct case construction and
the execution sink enforce the same filename admission.

## Invariants

- The untouched historical interpreter can be built and exercised under
  supported sanitizers, and sanitizer findings are captured as fixtures without
  treating undefined behavior as normative semantics.
- Defined interpreter behavior is authoritative and deterministic; sanitizer
  findings identify non-portable or undefined host behavior.

## Failure Behavior

Missing authority or contradictory configuration fails closed rather than
selecting an implicit repository policy.

## Verification

- Expected durable artifact surface:
  `src/interoperability/historical-malbolge/`, `tests/compatibility/`, and
  `benchmarks/interpreter/`.
- Required evidence: reviewed authority text plus deterministic
  parser/schema/governance tests for the declared boundary.
- Prerequisite completion evidence: `historical-interpreter-legal-boundary`,
  `historical-undefined-behavior-catalogue`.
- The pinned 4,738-byte source SHA-256 is checked before compilation.
- The clean interpreter roundtrip emits `0xA8` with no sanitizer finding.
- Empty and one-word sources reproduce normalized AddressSanitizer
  `heap-buffer-overflow` findings without retaining unstable addresses.
- `tests/test_historical_interpreter_sanitizer.py` verifies schema, identity,
  clean behavior, and both H-003 failures.

### Reproduction

```powershell
.dependencies\\python\\3.14.7\\Scripts\\python-jig.cmd -m `
  scripts.validate.historical_interpreter_sanitizer
```

The complete temporary build, shim, executable, dynamic runtime copy, and source
fixtures are deleted after each run. The historical source is never patched.

## References

- [Specification Authority And Malbolge
  Evolution](../adr/specification-authority-and-malbolge-evolution.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
- `docs/technical/adr/verification-trust-boundary.md`
