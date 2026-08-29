# Safe Rust Malbolge VM

## Status

Accepted implementation

## Purpose

Implement the primary modern VM in safe Rust with explicit errors, deterministic
state transitions, tracing hooks, and instruction-level conformance with the
defined, reproducible behavior of the original interpreter.

## Scope

This document governs the following declared TODO scope:

- `vm/`
- `execution/`
- `tests/vm/`
- `benchmarks/interpreter/`

## Current Behavior

### Model

The safe-Rust VM is the primary interpreter-authority classic execution engine.
Internal representation may change without changing observable behavior, the
verification trust boundary, or the authority of defined original-interpreter
semantics.

### Implementation Status

The safe-Rust classic VM is implemented under `vm/` with exact ten-trit words,
fixed memory, deterministic loading, byte I/O, atomic single-step transitions,
bounded execution, and optional in-memory trace hooks.

The classic public trace surface records before/after observations, decoded
instruction bytes, committed I/O, termination, rejected transition results, and
an allocation-free `MemoryDelta` with at most one instruction-data change plus
one final self-encryption change. `ProfileMachine` exposes the parallel
`ProfileStepTrace`/`ProfileMemoryDelta` surface with exact canonical profile
identity and profile-width `u32` addresses/words. Deltas contain actual final
changed cells only: unchanged writes are omitted, a data/encryption collision at
one address is represented once by its final encrypted value, and
halt, modern-profile non-graphical termination, historical non-graphical
non-progress, and rejected transitions report no memory change.
The public `profile_cell_is_graphical()` predicate owns the profile-width
33-through-126 decode boundary used by tracing, execution, and verified native
eligibility. `decode_profile_instruction()` owns the corresponding positional

translation and reduces wider code pointers by the normative 94-position phase.
`profile_cell_decodes_to_no_operation()` owns no-op classification,
`encrypt_profile_cell()` owns the post-step `XLAT2` transformation, and
`profile_pointer_successor()` owns exact profile-domain pointer wraparound.
Native
backends consume these VM-owned functions rather than redefining Malbolge cell
semantics, translation tables, or pointer arithmetic.

Both traced and untraced APIs still invoke the same transition engine. The
internal profile step result now carries both the already-validated memory delta
and fixed-role semantic reads. `ProfileStepTrace::memory_reads` records the real
code fetch, optional data-pointer read, and optional encryption-target read, for
a
maximum of three semantic reads per request. Rejected transitions retain reads
completed before the error; diagnostic/delta bookkeeping reads are excluded.

`step()` discards this evidence and `step_traced()` publishes it.
`TraceInput::EndOfInput` remains profile-neutral: current N15 traces record EOF
accumulator 14,348,906 rather than inheriting the classic 59,048 value.
Independent research fixtures reconstruct
complete before/after memory differences for every classic/current instruction
family and require exact equality with the trace delta.

The explicit annotated-source frontend is implemented separately from raw
loading. `canonicalize_annotated_source()` removes ASCII whitespace and only
full-line `# ` / `#\t` comments while recording loaded-position source
locations; bare/inline hashes remain code. `format_annotated_source()` inserts
deterministic LF wrapping. `Machine`, `ExecutionMachine`, and `ProfileMachine`
provide explicit annotated constructors, while every existing `from_source()`
entry point retains canonical raw semantics. Canonicalized bytes still pass

through the ordinary selected-profile loader before execution.

The classic execution facade carries an explicit canonical target-profile
identity. `ExecutionMachine::from_source()` remains bound to `malbolge-1998` for
classic compatibility, while `from_source_for_profile()` performs a typed
`safe-rust-classic` capability preflight before source loading. The current N15
`malbolge-2026` profile therefore still fails before reaching this classic
loader rather than being truncated or silently reinterpreted.

A separate safe-Rust `ProfileMachine` implements the canonical schema-v2
single-word-modular profile model under runtime identity `safe-rust-profiled`.
The current reference is N15/14,348,907 words; the backend's declared `u32`
representation can encode exact ternary geometry through N20/3,486,784,401
words, independently of current-profile selection.

A separate public `ChunkedProfileWord` value contract now consumes the generated
semantic-width constants projected from `malbolge.json`. It stores exactly
`ceil(N/5)` little-endian base-243 chunks, constrains the final partial chunk to
its native trits, and implements crazy, rotate, modular successor, small-modulus
residue, low-byte projection, EOF, and narrower-width projection without
computing `3^N` in a host integer. An optional `u32` conversion succeeds only
when the concrete value fits; it is not a width admission rule.

This does not yet widen `ProfileMachine` memory or registers. Product tests show
N10 through N20 equal the existing `u32` primitives, while independent
trit-vector oracles cover N21, N31, N41, and N100; N100 is represented directly
although it cannot convert to `u64`. Memory addressing, resident transport, and
accelerator execution remain separate migration boundaries.

`ProfileMachine` deliberately does not replace classic `Word`, `Memory`,
tracing,
or legacy-mode APIs. `ProfileMachine::from_state()` is a
validated initial-state constructor: the supplied memory image must have exact
profile length, every cell must be inside the profile word domain, and all three
registers must be in-domain. Complete checkpoint/deoptimization state uses
`ProfileMachineIoState` plus `ProfileMachineState`; it additionally preserves
the
full input stream, consumed-input cursor, committed output, and stable
termination
reason. `snapshot_state()` clones that complete state, and `from_snapshot()`

restores it without semantic reset. Construction never truncates or wraps
invalid
host values, and an input cursor beyond its stream is rejected before checkpoint
construction. Historical differential fixtures
run the same 1998 program through both engines and compare all 59,049 final
memory words,
registers, byte I/O/EOF, and termination. Current-profile fixtures additionally
exercise addresses above 59,048 and independent scalar expectations for N15
crazy and rotate.

Independent differential evidence now exists against the separately implemented
pure-C VM. Both implementations compute semantic signature
`0xa9dabd8fc51d13c9` without sharing transition implementation code. The
signature covers word operations, the complete loaded `ubO` memory image,
interpreter-compatible byte I/O and halt, rejected jump atomicity, and
historical non-graphical non-progress.

The implementation and its independent evidence have passed the declared
repository-wide validation gate. Future compiler, optimizer, and execution-tier
work consumes the public VM contracts without reopening this implementation
objective.

## Invariants

- The Rust VM implements the stabilized state machine without `unsafe`,
  arbitrary historical array assumptions, or host-dependent integer behavior and
  passes the classic specification-conformance corpus.
- Observable state, I/O, termination, and diagnostics match the declared
  semantic profile across positive, boundary, and adversarial fixtures.
- Tracing is observational and cannot alter guest state or execution results.
- The independent C implementation is evidence, not an implementation dependency
  of the Rust VM.
- `ProfileMachine` generalizes only profile-width geometry and preserves the
  same
  sequential/self-modifying semantic core; it never changes classic `Machine`.
- Profile state reconstruction is fail-closed: exact memory shape, all word/
  register values, and checkpoint input cursor are validated before use.
- Complete profile checkpoints preserve input position, committed output, and
  termination as well as memory/register state; restoration does not restart
  I/O.
- Classic and profiled trace hooks wrap their respective real step engines and
  therefore cannot become an alternate transition implementation. Their memory
  deltas are the validated transition result, not a second write planner.

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
  `0xa9dabd8fc51d13c9` from the public Rust API.
- `tests/vm/c_conformance.c` independently produces and asserts the same
  signature from the pure-C VM.
- `tests/vm/profile_reads.rs` covers every current-profile instruction family
  plus rejected jump encryption and requires exact fetch/data/encryption
  semantic
  read roles, addresses, values, and operation counts from the real step engine.
- `tests/vm/profile_tracing.rs` traces current-profile EOF/output/halt, proves
  traced and plain current execution agree on outcome, I/O, registers and
  sampled
  memory, verifies halt/rejection expose an empty memory delta, and exercises a
  real N15 recurrence jump whose rejected encryption target remains
  observationally atomic.
- `tests/vm/profile_state.rs` validates exact initial-state/checkpoint errors,
  round-trips consumed input, committed output, registers and termination
  through
  snapshot restoration, and places both current pointers at 14,348,906 to prove
  the last cell is encrypted before `C` and `D` wrap to zero.
- `tests/compatibility/specification/` contains versioned specification fixtures
  for historical disagreement edges and byte-I/O semantics.
- Trace hooks are observational only: classic and profile-driven traced/untraced
  executions over the same state and input must produce identical observable
  outcomes, output, and final state. State-graph research additionally compares
  trace memory deltas to complete before/after memory images for every
  instruction
  family in both profiles.
- Expected durable artifact surface: `vm/`, `execution/`, `tests/vm/`,
  `benchmarks/interpreter/`.
- The original C source is compared only where its behavior is defined and
  reproducible; undefined host behavior remains a safe failure.
- Prerequisite completion evidence: `canonical-malbolge-target-profile`,
  `historical-malbolge-semantics-specification`.

- `tests/vm/annotated.rs` verifies hash-safe comment recognition, line-ending
  independence, byte-exact automatic-wrap round trips, exact source-map
  positions, fail-closed presentation errors, and canonical-versus-annotated
  execution equality for classic/facade/current profile paths.

## References

- [Specification Authority And Malbolge
  Evolution](../../adr/specification-authority-and-malbolge-evolution.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
- `docs/technical/adr/verification-trust-boundary.md`
