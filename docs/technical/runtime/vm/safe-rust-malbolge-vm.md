# Safe Rust Malbolge VM

## Status

Active implementation

## Purpose

Implement the primary modern VM in safe Rust with explicit errors, deterministic
state transitions, tracing hooks, and instruction-level conformance with the
normative 1998 specification.

## Scope

This document governs the following declared TODO scope:

- `vm/`
- `execution/`
- `tests/vm/`
- `benchmarks/interpreter/`

## Current Behavior

### Model

The safe-Rust VM is the primary normative classic execution engine. Internal
representation may change without changing observable behavior, the verification
trust boundary, or the authority of the written 1998 specification.

### Implementation Status

The safe-Rust classic VM is implemented under `vm/` with exact ten-trit words,
fixed memory, deterministic loading, byte I/O, atomic single-step transitions,
bounded execution, and optional in-memory trace hooks.

The classic public trace surface records before/after observations, decoded
instruction bytes, committed I/O, termination, and rejected transition results
without changing guest semantics. `ProfileMachine` now exposes the parallel
`ProfileStepTrace` surface with exact canonical profile identity and profile-width
`u32` registers/cells. `TraceInput::EndOfInput` is profile-neutral: current traces
record EOF accumulator 4,782,968 rather than inheriting the classic 59,048 value.
Memory-transition correctness remains directly covered by instruction and
atomicity fixtures rather than duplicated by either trace layer.

The classic execution facade carries an explicit canonical target-profile
identity. `ExecutionMachine::from_source()` remains bound to `malbolge-1998` for
classic compatibility, while `from_source_for_profile()` performs a typed
`safe-rust-classic` capability preflight before source loading. The current
14-trit `malbolge-2026.2` profile therefore still fails before reaching this
classic loader rather than being truncated or silently reinterpreted.

A separate safe-Rust `ProfileMachine` now implements the canonical schema-v2
single-word-modular profile model through 14 trits/4,782,969 words under runtime
identity `safe-rust-profiled`. It deliberately does not replace classic `Word`,
`Memory`, tracing, or legacy-mode APIs. `ProfileMachine::from_state()` is the
validated reconstruction boundary for verification/deoptimization work: the
supplied memory image must have exact profile length, every cell must be inside
the profile word domain, and all three registers must be in-domain. Construction
never truncates or wraps invalid host values. Historical differential fixtures
run the same 1998 program through both engines and compare all 59,049 final memory words,
registers, byte I/O/EOF, and termination. Current-profile fixtures additionally
exercise addresses above 59,048 and independent scalar expectations for 14-trit
crazy and rotate.

Independent differential evidence now exists against the separately implemented
pure-C VM. Both implementations compute semantic signature
`0xa74cec75a875c85a` without sharing transition implementation code. The
signature covers word operations, the complete loaded `ctO` memory image, normal
byte I/O and halt, rejected jump atomicity, and non-graphical termination.

The typed TODO remains active until its declared repository-wide validation
command passes at retirement time.

## Invariants

- The Rust VM implements the stabilized state machine without `unsafe`,
  arbitrary historical array assumptions, or host-dependent integer behavior and
  passes the classic specification-conformance corpus.
- Observable state, I/O, termination, and diagnostics match the declared
  semantic profile across positive, boundary, and adversarial fixtures.
- Tracing is observational and cannot alter guest state or execution results.
- The independent C implementation is evidence, not an implementation dependency
  of the Rust VM.
- `ProfileMachine` generalizes only profile-width geometry and preserves the same
  sequential/self-modifying semantic core; it never changes classic `Machine`.
- Profile state reconstruction is fail-closed: exact memory shape and all word/
  register values are validated before a machine exists.
- Classic and profiled trace hooks wrap their respective real step engines and
  therefore cannot become an alternate transition implementation.

## Failure Behavior

Invalid programs, unsupported profiles, or broken native assumptions fail
deterministically without changing guest-visible state silently. Rejected
transitions expose their diagnostic without partially committing registers,
memory, input consumption, or output.

## Verification

- `tests/vm/` exercises all seven instruction families, no-op behavior, pointer
  wrap, byte/EOF I/O, loader boundaries, bounded execution, self-encryption,
  jump-target encryption, rejected-transition atomicity, and trace hooks.
- `tests/vm/profile_requirements.rs` verifies canonical profile identity,
  current-profile fail-closed preflight, transition-profile acceptance, and the
  exact historical-profile ceiling diagnostic.
- `tests/vm/differential.rs` recomputes semantic signature
  `0xa74cec75a875c85a` from the public Rust API.
- `tests/vm/c_conformance.c` independently produces and asserts the same
  signature from the pure-C VM.
- `tests/vm/profile_tracing.rs` traces current-profile EOF/output/halt, proves
  traced and plain current execution agree on outcome, I/O, registers and sampled
  memory, and exercises a real 14-trit recurrence jump whose rejected encryption
  target remains observationally atomic.
- `tests/vm/profile_state.rs` validates exact state reconstruction errors and
  places both current pointers at 4,782,968, proving the last cell is encrypted
  before `C` and `D` wrap to zero.
- `tests/compatibility/specification/` contains versioned specification fixtures
  for historical disagreement edges and byte-I/O semantics.
- Trace hooks are observational only: classic and profile-driven traced/untraced
  executions over the same state and input must produce identical observable
  outcomes, output, and final state.
- Expected durable artifact surface: `vm/`, `execution/`, `tests/vm/`,
  `benchmarks/interpreter/`.
- The historical interpreter is compared only on its documented agreement
  domain.
- Prerequisite completion evidence: `canonical-malbolge-target-profile`,
  `historical-malbolge-semantics-specification`.

## References

- [Specification Authority And Malbolge
  Evolution](../../adr/specification-authority-and-malbolge-evolution.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
- `docs/technical/adr/verification-trust-boundary.md`
