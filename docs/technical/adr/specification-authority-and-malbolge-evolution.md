# Specification Authority And Malbolge Evolution

## Status

Accepted.

## Context

Malbolge has two primary historical artifacts from 1998: Ben Olmstead's prose
specification and his C interpreter. They disagree in observable places. Most
notably, the specification defines `<` as input and `/` as output, while the C
interpreter implements those operations in reverse. The prose specification also
says execution of a non-graphical cell ends immediately, while the C interpreter
loops without advancing its pointers.

A modern compiler, verifier, optimizer, native backend, GPU executor, or cluster
cannot have a coherent semantic target if implementation accidents silently
outrank the written machine definition.

## Decision

The 1998 prose specification is the normative authority for classic Malbolge
semantics in this repository.

Ben Olmstead's original C interpreter remains immutable historical evidence and
a differential oracle only over the subset where its behavior is defined and
agrees with the normative specification. When the interpreter contradicts the
specification, the specification wins.

Historical interpreter bugs are documented as implementation defects. Modern
implementations must not reproduce them in their normal execution mode merely to
preserve compatibility with programs that accidentally depended on those bugs.

An explicitly named legacy-interpreter mode may emulate selected Ben-interpreter
behavior for archaeology, differential diagnosis, or historical corpus study.
That mode is not the compiler target, does not redefine the language, and cannot
be used as verification authority for specification-conformant output.

Extensions such as larger memory use versioned target profiles derived from the
normative machine. Classic ten-trit arithmetic, crazy operation, rotate,
decoding, self-modification, input/output meanings, termination, and pointer
rules remain the base semantics unless a later profile explicitly changes them.

## Alternatives Considered

### Treat the original C interpreter as the language authority

Rejected. It preserves historical program compatibility at the cost of turning
implementation defects and C undefined behavior into language semantics. It also
creates a poor foundation for independent Rust/C implementations and accelerator
backends.

### Preserve every historical program through bug-compatible default semantics

Rejected. Nostalgic compatibility is less important than one deterministic,
reviewable machine definition suitable for compilers, verifiers, GPUs, clusters,
and future implementations.

### Remove the original interpreter

Rejected. The file is valuable primary evidence, exposes historical defects, and
provides differential coverage for the large semantic intersection where it
matches the written specification.

## Consequences

- `<` means input and `/` means output in the modern classic profile.
- Executing a non-graphical current cell terminates the classic machine as the
  specification states.
- Historical programs that depended on interpreter bugs may behave differently
  under the modern VM.
- Test corpora must distinguish specification conformance from Ben-interpreter
  compatibility.
- GPU, cluster, JIT/AOT, optimizer, and verifier implementations share one clean
  semantic contract instead of reproducing host-C accidents.
- The historical interpreter remains useful without being the architecture's
  semantic root.

## Implementation Notes

The canonical classic profile should identify itself as
specification-conformant. If a legacy Ben-interpreter mode is implemented, its
identity and diagnostics must be explicit enough that generated artifacts are
never accidentally verified against it as if it were the language specification.
