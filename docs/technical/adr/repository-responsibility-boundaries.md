# Repository Responsibility Boundaries

## Status

Accepted.

## Decision ID

`jig.malbolge.technical.repository-responsibility-boundaries`

## Context

The project uses Rust, C, C++, CUDA, Python, LaTeX, and Malbolge while aiming to
remain portable across implementation technologies. Organizing the repository by
language or by Rust crate would make build-system mechanics dictate system
architecture.

## Decision

Repository boundaries are responsibilities, not programming languages.

Compiler, VM, execution, runtime, verification, optimization, acceleration,
interoperability, algorithms, tests, benchmarks, tools, and documentation own
separate responsibilities. A responsibility may contain several implementation
languages when they implement the same capability.

Cargo package/module requirements may create local `src/` directories where the
toolchain requires them, but they do not create repository-level ownership by
themselves. The root Rust composition surface remains thin.

## Advantages

- Makes the repository responsibility boundaries boundary explicit, reviewable,
  and stable before implementation depends on it.

## Disadvantages

- The decision constrains future implementation until a later ADR deliberately
  supersedes it.

## Consequences

- Language choice can change without moving conceptual ownership.
- Hardware adapters remain peers under acceleration rather than language roots.
- Research algorithms may mix CPU, GPU, Python, and LaTeX artifacts under one
  algorithm identity.
- Build manifests use explicit paths instead of requiring architectural crate
  boundaries.

## Rejected Alternatives

### Language roots

Rejected because `rust/`, `python/`, `c/`, or a generic `crates/` hierarchy
would separate implementations that must evolve under the same semantic owner.

### One flat source directory

Rejected because it hides subsystem boundaries and makes accelerator,
interoperability, verifier, and research ownership ambiguous.

## Evidence

Top-level directories must correspond to durable responsibilities represented by
`TODO.md` or accepted documentation. Empty speculative roots should not
accumulate.
