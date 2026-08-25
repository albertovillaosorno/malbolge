# Malbolge-specific optimization mathematics

This directory is the executable mirror for research ID
`malbolge-specific-optimization-mathematics`. It keeps experiment configuration
and lifecycle metadata close to the executable research surface without
repeating the mathematical results.

## Where the research lives

The documentation mirror's `research.md` owns the human research narrative,
results, limitations, and conclusions. The formal TeX contract owns detailed
equations and derivations.

The repository `correspondence.toml` manifest binds equations to executable
evidence. Mathematics tests under `tests/mathematics/` provide the independent
finite or bounded checks named by that manifest.

## Experiment files

`experiment.toml` owns the versioned experiment plan, verification requirement,
resource budget, and raw benchmark-evidence location. `lifecycle.toml` owns the
research lifecycle state and links this executable mirror back to the human
research record.

Regenerable local outputs belong in the logical
`algorithms/malbolge-specific-optimization-mathematics/out/` location and remain
Git ignored. Durable benchmark samples are promoted only to their owning
versioned evidence directory rather than copied into this README.

## Correctness boundary

Search, optimization, and experimental implementations are untrusted proposal
mechanisms. Deterministic correspondence checks and the repository verification
boundary decide which mathematical or performance claims are admissible.

Exact cardinalities, canonical forms, covering results, and benchmark numbers
are intentionally not cataloged here. Read `research.md` for the interpreted
results, the TeX contract for the proofs, and `correspondence.toml` for the
traceable executable evidence.

## Validation

Run the repository-owned validation from the repository root.

```sh
jig validate --root .
```

Focused mathematics checks may be useful while developing a theorem, but they
do not replace the repository gate required by the owning typed TODO.
