# Specification Authority And Malbolge Evolution

## Status

Accepted.

## Decision ID

`jig.malbolge.technical.specification-authority-and-malbolge-evolution`

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

The 1998 prose specification is the normative authority for the frozen
`malbolge-1998` historical/conformance profile in this repository. It defines
what the original language meant and remains the semantic oracle for historical
conformance; it is not an eternal resource ceiling on current Malbolge.

Current Malbolge is a versioned living language derived from that machine. Its
defining ternary arithmetic, crazy operation, rotate behavior, self-modification,
post-instruction encryption, sequential guest execution, and deterministic
semantics are preserved as the language core unless a later reviewed profile
explicitly changes them. Historical implementation defects and accidental host-C
limits are not part of that core.

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

Useful evolution such as larger memory uses versioned target profiles derived
from the normative machine. The current language is not branded as a separate
"extended" Malbolge merely because it removes a historical ceiling. The exact
1998 ten-trit/59,049-word machine remains available by selecting
`malbolge-1998`; current profiles may generalize word/address capacity while
preserving the defining ternary operations and self-modifying execution model.
The scaling mechanism must be explicit and deterministic rather than silently
borrowing host pointer width or memory behavior.

## Advantages

- Makes the specification authority and malbolge evolution boundary explicit,
  reviewable, and stable before implementation depends on it.

## Disadvantages

- The decision constrains future implementation until a later ADR deliberately
  supersedes it.

## Consequences

- `<` means input and `/` means output in `malbolge-1998` and in current
  profiles unless explicitly versioned otherwise.
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

## Rejected Alternatives

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

## Evidence

The canonical historical profile identifies itself as `malbolge-1998` and
specification-conformant. The canonical current profile has a distinct versioned
identity and must never be confused with historical conformance. If a legacy
Ben-interpreter mode is implemented, its identity and diagnostics remain
explicit enough that generated artifacts are never accidentally verified
against it as if it were a language profile.
