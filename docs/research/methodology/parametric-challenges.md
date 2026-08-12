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
- Last reviewed: 2026-08-11

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

The implemented slices are `arithmetic-dag/v1`, `linear-mix/v1`,
`branch-mix/v1`, `memory-walk/v1`, `call-chain/v1`, `pointer-walk/v1`,
`alias-walk/v1`, `stream-state/v1`, `graph-reduce/v1`,
`grid-accumulate/v1`, `layout-chain/v1`, `ternary-fold/v1`, and
`nested-state/v1`. Each binds family, version, seed,
canonical profile fingerprint, and node count into one replay identity.
Generation emits deterministic `uint32_t` C source for the selected topology, a
four-byte little-endian oracle, and a canonical manifest containing
source/oracle
SHA-256 digests. Every version-one family keeps each generated node on a live
dependency path to the observable result, so increasing `nodes` cannot grow only
through dead C statements. Native warning-clean compilation is regression
evidence for that invariant. `linear-mix/v1` uses a family-domain-separated
stream and a strict predecessor chain, contrasting dependency depth with the
DAG family’s extra source-order fan-in. `branch-mix/v1` adds one live
`if`/`else` diamond per node from a third domain-separated stream;
normalized-frontend tests
retain the expected branch count. `memory-walk/v1` uses a fixed eight-cell
local array with deterministic indexed read/write/read steps, and frontend
evidence retains `1 + 3×nodes` array-subscript expressions. `call-chain/v1`
threads the live value through a pure three-argument helper, with normalized
evidence retaining one call per node plus the standalone driver call.
`pointer-walk/v1` keeps one live runtime-selected pointer per node, while
`alias-walk/v1` keeps two such pointers whose sequential writes may alias the
same cell. `stream-state/v1` fixes a seed-derived state transition rule and uses
`nodes` only as stream length, so increasing difficulty appends deterministic
tokens under the same machine. Its normalized frontend preserves one loop, one
indexed stream read, and one live state branch. `graph-reduce/v1` generates
one parent link to an already-computed state plus one weight per vertex. Its
runtime loop combines parent state, predecessor state, and weight into the next
state; normalized evidence retains one loop and six graph/state subscripts.
`grid-accumulate/v1` decouples generation size from generated runtime work: a
node-scaled token vector feeds two loops each bounded by `nodes`, so the emitted
program performs exactly `nodes^2` live `uint32_t` accumulation updates while
source construction remains O(nodes). The independent Python oracle also stays
O(nodes) by using the algebraically equivalent modulo-`2^32` sum. Normalized
frontend evidence retains exactly two loops and one token subscript.
`layout-chain/v1` emits one distinct helper body and call target per node; all
calls are sequentially live, while normalized evidence retains `nodes + 2`
functions and `nodes + 1` call expressions. `ternary-fold/v1` restricts values
to the classic ten-trit domain and applies explicit base-three quotient,
remainder, and recomposition work in a fixed inner transform before the
node-scaled outer fold. The C entry `malbolge_challenge` returns the oracle
value directly;
standalone `main` is only a low-31-bit driver and is not an oracle surface.
`nested-state/v1` adds nested control-flow stress without making generation
quadratic: a node-scaled token stream feeds a fixed four-lane inner loop, so
runtime work performs four live state transitions per node while the Python
oracle remains O(nodes). Normalized frontend evidence retains both loops and the
three indexed inputs (`tokens`, `addends`, `masks`).

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

Thirteen deterministic families are implemented and replayable. Tests lock byte-
identical regeneration and v1 replay vectors for `arithmetic-dag`,
`pointer-walk`, `stream-state`, `graph-reduce`, `grid-accumulate`,
`layout-chain`, `ternary-fold`, and `nested-state`, plus profile-fingerprint
binding and difficulty growth for all thirteen topologies, invalid
identity rejection, collision-safe no-replace publication (including a raced
final-path collision), replay rejection for linked artifact leaves, current
C-profile admission, and independent native agreement for
representative node counts in all thirteen families. `nested-state/v1`
additionally retains a 4,096-node pinned-Clang/native-oracle case, while
`grid-accumulate/v1` retains a 257-node native case whose generated runtime work
contains 66,049 live inner updates. Generation-only stress now replays
`stream-state`, `graph-reduce`, `grid-accumulate`, `ternary-fold`, and
`nested-state` byte-identically at 16,384 nodes while retaining a four-byte
oracle and exact manifest difficulty.

This result does not satisfy the end-to-end acceptance criterion. No current
backend evidence yet demonstrates a generated challenge compiled to and
executed as a final `.malbolge` artifact; the layout/encoding backend required
for that path is still pending. Broader workload families also remain open.

## Threats to Validity

The current families cover unsigned arithmetic with DAG, strict-chain,
branch-diamond, fixed-array memory-walk, helper-call, live pointer-selected
memory, potentially aliasing pointer-pair, streaming state-machine, acyclic
graph-reduction, quadratic grid accumulation, distinct-function
layout-pressure, explicit ternary-fold, and nested-state control-flow
topologies. The 4,096-node nested native case plus five 16,384-node deterministic
generation/replay cases add larger stress evidence, but broader workload
structure and additional native/executed large shapes remain open.
Workload selection, generator/model common-mode bugs, native-check host
differences,
missing final Malbolge execution, and incomplete family coverage remain
threats. The independent native check narrows only the Python-versus-C-source
agreement risk; it does not prove downstream compiler correctness.

## Conclusion

Active. Retain hash-locked v1 replay vectors for `arithmetic-dag`,
`pointer-walk`, `stream-state`, `graph-reduce`, `grid-accumulate`,
`layout-chain`, `ternary-fold`, and `nested-state`, alongside domain-separated
`linear-mix/v1`, `branch-mix/v1`, `memory-walk/v1`, `call-chain/v1`, and
`alias-walk/v1` as deterministic challenge substrates
while expanding family coverage and waiting for an end-to-end generated
Malbolge execution path before completing this planning
objective.

## References

- [Parametric Multi Objective Algorithm
  Evaluation](../adr/parametric-multi-objective-algorithm-evaluation.md)
- [Research Evidence And Algorithm
  Mirror](../adr/research-evidence-and-algorithm-mirror.md)
- [Verification Trust
  Boundary](../../technical/adr/verification-trust-boundary.md)
