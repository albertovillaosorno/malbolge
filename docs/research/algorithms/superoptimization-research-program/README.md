# Superoptimization Research Program

## Purpose

Catalog `docs/research/algorithms/superoptimization-research-program/`.

## Owns

Records physically owned by
`docs/research/algorithms/superoptimization-research-program/`.

## Does Not Own

Product semantics, verifier authority, measured benchmark results, or ordinary
engineering implementation.

## Contents

- `research.md`
- `algorithms/superoptimization-research-program/`

## Workload identity integrity

The frozen two-word pilot, three-word holdout, and four-word learned-guidance
holdout compute workload SHA-256 from compact sorted JSON. Each binds the
original standard-library `JSONEncoder` class at import and compares exact
bytes against the public JSON writer before accepting the identity. Encoder-only,
writer-only, and joint substitutions fail with typed errors; equivalent writers
retain the preregistered bytes. This is a process-local source-integrity check,
not a defense against modifications to Python's underlying JSON implementation.
