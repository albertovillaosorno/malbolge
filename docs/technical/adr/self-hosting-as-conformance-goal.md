# Self-Hosting As Conformance Goal

## Status

Accepted.

## Decision ID

`jig.malbolge.technical.self-hosting-as-conformance-goal`

## Context

A C-to-Malbolge compiler can appear successful while depending on host-only
facilities that make the compiler itself impossible to express in its admitted C
profile. A stronger long-term test is compiling and running the compiler under
Malbolge semantics.

## Decision

Self-hosting is the long-term conformance goal.

A portable `c2malbolge.c` is written inside the same deterministic C profile
promised to users. The native compiler compiles it to `c2malbolge.malbolge`.
That Malbolge-hosted compiler must then consume C bytes and emit a valid
`.malbolge` program without delegating the essential compilation algorithm to a
host service.

Native and hosted outputs are compared by canonical artifact identity or by an
explicit verified normalization when byte identity is not a promised property.

## Advantages

- Makes the self-hosting as conformance goal boundary explicit, reviewable, and
  stable before implementation depends on it.

## Disadvantages

- Self-hosting substantially raises portability and bootstrap constraints on the
  compiler.

## Consequences

- Host-only conveniences cannot quietly become compiler semantic dependencies.
- Binary byte-stream input/output is a first-class guest capability.
- Self-hosting provides an end-to-end stress test beyond application examples.

## Rejected Alternatives

### Treat self-hosting as a novelty demo

Rejected because it provides valuable pressure on ABI, runtime, I/O, compiler
portability, deterministic output, and verification contracts.

### Require self-hosting before the first compiler works

Rejected because it would block incremental implementation and validation of the
underlying compiler stages.

## Evidence

The hosted compiler may be slow. Correctness and independence from hidden host
compilation are required before performance optimization.
