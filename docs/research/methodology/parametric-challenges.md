# Parametric compiler challenge generator

## Status

Active

## Research Question

What evidence and method are required to evaluate parametric compiler challenge
generator?

## Background

Build deterministic workload generators whose difficulty can grow continuously
instead of saturating at one application-specific threshold. Generate families
covering arithmetic and ternary transforms, expression DAGs, control flow,
function calls, memory pressure, pointer/alias patterns admitted by the C
profile, streaming state machines, graph problems, layout pressure, Malbolge
self-modification, block synthesis, and whole-program compositions with known
semantic oracles. Every instance is identified by family, version, seed, target
profile, and explicit difficulty parameters so two algorithms can be compared on
exactly the same problem rather than on vaguely similar examples.

- Status: Active
- Record type: Methodology
- Planning identity: `parametric-compiler-challenge-generator`
- Last reviewed: 2026-08-09

## Prior Work

Prior-work claims must resolve through canonical records under
`docs/bibliography/`.

## Hypothesis

- Every challenge has stable family/version/seed/profile identity, an oracle,
  and difficulty parameters that can scale beyond trivial saturation while
  remaining reproducible.
- The end-to-end fixture demonstrates the intended behavior from admitted
  source/input through the actual generated/executed Malbolge path.
- The work states a falsifiable question or hypothesis, an explicit baseline,
  and an observation that would reject or materially weaken the proposed
  technique before performance conclusions are accepted.
- If executable algorithm research is required, the stable ID is mirrored under
  `docs/research/algorithms/<id>/` and `algorithms/<id>/`; ordinary product
  engineering is not forced into that mirror.

## Method

Work under this record uses stable identities, explicit inputs and assumptions,
independent correctness evidence where applicable, and retained negative/null
results. Source claims resolve through `docs/bibliography/`.

The first implemented slice is `arithmetic-dag/v1`. It binds family, version,
seed, canonical profile fingerprint, and node count into one replay identity.
Generation emits deterministic `uint32_t` arithmetic DAG source plus a four-byte
little-endian oracle and a canonical manifest containing source/oracle SHA-256
digests. The version-one family keeps every generated node on a live dependency
spine, so increasing `nodes` cannot add dead C statements that disappear from
the observable challenge result. Native warning-clean compilation is regression
evidence for that invariant. The C entry `malbolge_challenge` returns the oracle
value directly;
standalone `main` is only a low-31-bit driver and is not an oracle surface.

The generated source is preflighted through the repository-owned C ABI and libc
validators. Independent native evidence compiles selected generated sources with
the pinned Clang and compares the entry return to the separately retained Python
oracle. That native check detects generator/model disagreement but does not make
host execution guest semantic authority.

## Evidence

- Expected durable artifact surface: `benchmarks/challenges/`, `docs/research/`,
  `tests/analysis/`, `compiler/`.
- Required evidence: reproducible build/run commands, expected outputs or
  interaction traces, artifact hashes, and end-to-end verification.
- Research evidence pending: bibliography-backed context, experiment identity,
  reproducible configuration, retained negative/null results, and a reviewed
  conclusion with threats to validity.

## Results

The first deterministic family is implemented and replayable. Tests lock byte-
identical regeneration, profile-fingerprint binding, difficulty growth, invalid
identity rejection, collision-safe no-replace publication (including a raced
final-path collision), replay rejection for linked artifact leaves, current
C-profile admission, and independent native agreement for representative node
counts.

This result does not satisfy the end-to-end acceptance criterion. No current
backend evidence yet demonstrates a generated challenge compiled to and executed
as a final `.malbolge` artifact, and the broader family set remains
unimplemented.

## Threats to Validity

The first family covers only straight-line unsigned arithmetic DAGs. Workload
selection, generator/model common-mode bugs, native-check host differences,
missing final Malbolge execution, and incomplete family coverage remain
threats. The independent native check narrows only the Python-versus-C-source
agreement risk; it does not prove downstream compiler correctness.

## Conclusion

Active. Retain `arithmetic-dag/v1` as deterministic challenge substrate while
expanding family coverage and waiting for an end-to-end generated Malbolge
execution path before completing this planning objective.

## References

- [Parametric Multi Objective Algorithm
  Evaluation](../adr/parametric-multi-objective-algorithm-evaluation.md)
- [Research Evidence And Algorithm
  Mirror](../adr/research-evidence-and-algorithm-mirror.md)
- [Verification Trust
  Boundary](../../technical/adr/verification-trust-boundary.md)
