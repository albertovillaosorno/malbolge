# Parametric compiler challenge generator

## Status

Completed

## Research Question

What evidence and method are required to evaluate parametric compiler challenge
generator?

## Background

Build deterministic source-level workload generators whose difficulty can grow
continuously instead of saturating at one application-specific threshold. The
bounded milestone covers arithmetic and ternary transforms, DAG and tree shapes,
control flow, calls, memory/alias pressure, streaming and graph state, layout
pressure, nested state, and heterogeneous composition with known semantic
oracles. Every instance is identified by family, version, seed, target profile,
and explicit difficulty parameters so algorithms can be compared on exactly the
same source-level problem.

Target-native self-modification, block synthesis, and final `.malbolge`
composition require later layout/search/linking capabilities. They are retained
as downstream scaling and versioned-corpus obligations rather than keeping this
source/oracle infrastructure permanently open.

- Status: Completed
- Record type: Methodology
- Planning identity: `parametric-compiler-challenge-generator`
- Last reviewed: 2026-09-04

## Prior Work

Prior-work claims must resolve through canonical records under
`docs/bibliography/`.

## Hypothesis

- Every challenge has stable family/version/seed/profile identity, an oracle,
  and difficulty parameters that can scale beyond trivial saturation while
  remaining reproducible.
- The source/oracle substrate remains deterministic and independently checked
  without relying on an unfinished target backend for its own completion.
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
`branch-mix/v1`, `binary-tree/v1`, `memory-walk/v1`, `call-chain/v1`,
`pointer-walk/v1`, `alias-walk/v1`, `stream-state/v1`, `sort-reduce/v1`,
`graph-reduce/v1`, `grid-accumulate/v1`, `layout-chain/v1`,
`ternary-fold/v1`, `nested-state/v1`, and `composed-pipeline/v1`. Each binds
family, version, seed,
canonical profile fingerprint, and node count into one replay identity.
Generation emits deterministic `uint32_t` C source for the selected topology, a
four-byte little-endian oracle, and a canonical manifest containing
source/oracle SHA-256 digests.

Hash-locked replay vectors use immutable `malbolge-2026.3` identity so
advancement of the mutable current profile cannot rewrite retained manifests.
Every version-one family keeps each generated node on a live
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
indexed stream read, and one live state branch. `sort-reduce/v1` generates a
node-scaled item vector, performs data-dependent compare/swap ordering in a

nested loop, then folds every sorted item into the observable result. Its
independent Python oracle uses `sorted(...)` rather than the emitted
bubble-style
ordering logic; normalized frontend evidence retains three loops, one branch,
and five live array subscripts. `graph-reduce/v1` generates
one parent link to an already-computed state plus one weight per vertex. Its
runtime loop combines parent state, predecessor state, and weight into the next
state; normalized evidence retains one loop and six graph/state subscripts.
`binary-tree/v1` places `nodes` generated leaves in a fixed binary heap and

reduces internal parents from the bottom up. Its two loops preserve hierarchical
fan-in while every leaf remains on the observable root path; normalized frontend
evidence retains two loops and seven live array subscripts.
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

`composed-pipeline/v1` adds heterogeneous whole-program composition pressure:
one node-scaled loop combines state-selected local-memory reads/writes, a live
branch, and two helper calls while every iteration feeds the next. Its Python
oracle performs the same defined `uint32_t` transition with explicit wrapping,
and native evidence checks 1, 64, and 257 nodes. Normalized frontend evidence
retains one loop, one branch, nine live subscripts, and three calls.

The generated source is preflighted through the repository-owned C ABI and libc
validators. Independent native evidence compiles selected generated sources with
the pinned Clang and compares the entry return to the separately retained Python
oracle. That native check detects generator/model disagreement but does not make
host execution guest semantic authority.

## Evidence

- Expected durable artifact surface: `benchmarks/challenges/`, `docs/research/`,
  `tests/analysis/`, `compiler/`.
- Required evidence for this bounded milestone: deterministic regeneration,
  canonical manifests and hashes, C-profile admission, normalized-frontend
  structure, independent native-oracle agreement, and scalable replay.
- Completion evidence is retained in the generator tests and this reviewed
  methodology record. Comparative performance, target-native execution, and
  synthesis-specific scaling require their own downstream evidence and do not
  inherit a claim from source-level generation.

## Results

Sixteen deterministic families are implemented and replayable. Tests lock byte-
identical regeneration and v1 replay vectors for `arithmetic-dag`,
`pointer-walk`, `stream-state`, `sort-reduce`, `graph-reduce`, `binary-tree`,
`grid-accumulate`, `layout-chain`, `ternary-fold`, `nested-state`, and
`composed-pipeline`, plus profile-fingerprint binding and difficulty growth for
all sixteen topologies,
invalid
identity rejection, collision-safe no-replace publication (including a raced
final-path collision), replay rejection for linked artifact leaves, current
C-profile admission, and independent native agreement for
representative node counts in all sixteen families. `nested-state/v1`
additionally retains a 4,096-node pinned-Clang/native-oracle case, while
`grid-accumulate/v1` retains a 257-node native case whose generated runtime work
contains 66,049 live inner updates. Generation-only stress now replays
`stream-state`, `sort-reduce`, `graph-reduce`, `binary-tree`,
`grid-accumulate`, `ternary-fold`, `nested-state`, and `composed-pipeline`
byte-identically at 16,384 nodes while
retaining a four-byte
oracle and exact manifest difficulty.

This completes the bounded source/oracle generator milestone. No current backend
evidence demonstrates a generated challenge compiled to and executed as a final
`.malbolge` artifact, and no target-native block-synthesis/self-modification
challenge is claimed here. Those capabilities remain explicit downstream work:
the versioned example corpus owns representative end-to-end `.malbolge` pairs,
while the empirical synthesis scaling study owns synthesis-specific challenge
axes once the required backend/search/linking capabilities exist.

## Threats to Validity

The current families cover unsigned arithmetic with DAG, strict-chain,
branch-diamond, fixed-array memory-walk, helper-call, live pointer-selected
memory, potentially aliasing pointer-pair, streaming state-machine,
data-dependent sorting/fold, acyclic graph-reduction, hierarchical binary-tree
reduction, quadratic grid
accumulation, distinct-function
layout-pressure, explicit ternary-fold, nested-state control-flow, and
heterogeneous composed-pipeline topologies. The 4,096-node nested native case
plus eight 16,384-node deterministic generation/replay cases add larger stress
evidence. Broader target-native workload structure is outside this bounded
milestone and remains owned by the downstream scaling and versioned-corpus work.

Workload selection, generator/model common-mode bugs, native-check host
differences, missing final Malbolge execution, and incomplete family coverage
remain threats. The independent native check narrows only the
Python-versus-C-source agreement risk; it does not prove downstream compiler
correctness.

## Conclusion

Completed bounded milestone. Retain hash-locked v1 replay vectors for
`arithmetic-dag`,
`pointer-walk`, `stream-state`, `sort-reduce`, `graph-reduce`, `binary-tree`,
`grid-accumulate`, `layout-chain`, `ternary-fold`, `nested-state`, and
`composed-pipeline`, alongside domain-separated `linear-mix/v1`,
`branch-mix/v1`, `memory-walk/v1`, `call-chain/v1`, and `alias-walk/v1` as
deterministic challenge substrates. Future target-native families extend this
frozen substrate only under their downstream owners; they do not reopen the
completed P1 generator milestone.

## References

- [Parametric Multi Objective Algorithm
  Evaluation](../adr/parametric-multi-objective-algorithm-evaluation.md)
- [Research Evidence And Algorithm
  Mirror](../adr/research-evidence-and-algorithm-mirror.md)
- [Verification Trust
  Boundary](../../technical/adr/verification-trust-boundary.md)
