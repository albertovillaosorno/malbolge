# Historical Compatibility And Malbolge Evolution

## Status

Accepted.

## Context

The 1998 machine has a fixed ten-trit word and 59049-word address space. Modern
experiments need larger programs and memory while classic programs require a
credible historical oracle and byte-level compatibility expectations.

## Decision

There is one modern Malbolge product with explicit target profiles.

The original 1998 machine is the compatibility baseline, not a separately
maintained Classic product. Programs whose historical behavior is defined and
stays inside original bounds must remain observationally equivalent to the
historical oracle.

Extensions such as larger memory use versioned target-profile semantics. Classic
word arithmetic, crazy operation, rotate behavior, decoding, and self-modifying
execution remain the semantic basis unless an extension explicitly states a new
operation.

A compatibility capsule may use historical whitespace behavior so one
`.malbolge` artifact can provide a classic fallback diagnostic while exposing an
extended image to modern runtimes.

## Alternatives Considered

### Modify classic semantics globally

Rejected because it would destroy differential compatibility and make historical
program meaning depend on the modern implementation.

### Maintain separate Classic and Extended products

Rejected because duplicated tools and documentation would drift. Profiles are a
cleaner compatibility boundary.

## Consequences

- Target requirements must be explicit and diagnosable.
- Modern memory/address extensions require a versioned specification.
- The historical interpreter remains a reference for its defined domain, not an
  implementation template for new code.

## Implementation Notes

The target-profile authority is versioned independently from compiler
optimization configuration. Extended artifacts must identify the profile needed
to interpret them safely.
