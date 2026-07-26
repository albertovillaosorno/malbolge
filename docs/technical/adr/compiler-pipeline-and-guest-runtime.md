# Compiler Pipeline And Guest Runtime

## Status

Accepted.

## Decision ID

`jig.malbolge.technical.compiler-pipeline-and-guest-runtime`

## Context

Directly expanding every C operation into raw Malbolge would produce enormous
artifacts, repeat synthesis work, and couple source-language structure to
position-dependent target encoding.

## Decision

Compilation uses staged deterministic representations.

The conceptual path is C/Clang evidence, normalized typed compiler IR, ternary
or Malbolge-oriented IR, layout/self-modification solving, and final encoded
`.malbolge` output. Source maps and proof obligations survive the stages needed
for diagnostics and verification.

Reusable guest functionality such as allocation, streams, arithmetic helpers,
calling convention support, and libc operations executes inside Malbolge
semantics. For sufficiently large programs the compiler may target a compact
guest bytecode interpreted by a reusable runtime inside Malbolge instead of
resynthesizing every application operation independently.

## Advantages

- Makes the compiler pipeline and guest runtime boundary explicit, reviewable,
  and stable before implementation depends on it.

## Disadvantages

- The decision constrains future implementation until a later ADR deliberately
  supersedes it.

## Consequences

- Intermediate representations require closed deterministic contracts.
- Runtime code becomes a reusable optimization surface.
- Compiler correctness can be checked stage-by-stage instead of only through
  end-to-end output tests.

## Rejected Alternatives

### Direct C-to-character translation

Rejected because source constructs do not correspond cleanly to position-
dependent self-modifying target instructions.

### Host callbacks for complex guest operations

Rejected because a program that delegates parsing, allocation, hashing, or
formatting to the host is not demonstrating those computations under Malbolge
semantics.

## Evidence

A compact bytecode design remains research until benchmark and verifier evidence
shows that its code-size/compile-time benefit justifies runtime overhead.
