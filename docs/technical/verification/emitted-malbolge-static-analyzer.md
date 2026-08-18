# Emitted Malbolge static analyzer

## Status

Active implementation

## Purpose

Analyze generated Malbolge for lexical and address validity, self-modification,
control-flow reachability, code/data aliasing, wraparound, dataflow, invalid
executable cells, and input-dependent cycles or hangs.

## Scope

This document governs the following declared TODO scope:

- `verifier/`
- `tests/differential/`
- `tests/exhaustive/`
- `tests/fuzz/`

## Current Behavior

### Implemented initial-image slice

`verifier/emitted_malbolge.py` statically inspects raw `malbolge-1998` source
without executing guest instructions. It applies the historical loader's six
C-locale whitespace bytes, graphical ASCII boundary, two-word recurrence base,
59,049-word capacity, and position-dependent 94-cell decode table. Reports are
canonical JSON and include the exact historical profile identity/capacity,
required source words, SHA-256 of the exact raw source bytes, admitted initial
cells with original byte offsets, stable findings, and analysis limits. Schema
`malbolge-static-image/v56` retains exact `entry_transition` through
`fifth_transition` compatibility fields and `bounded_continuations`, and adds
nullable `bounded_exact_cycle` evidence.
Sixteen transitions remain the default, while one explicit finite request
may select any total bound from 1 through 256. One single-pass finite trace
replays committed writes before each bounded read, then resolves fetch/data
cells,
decode, C/D alias, planned data write, encryption address/input/output,
accumulator dependency, halt/rejection, pointer succession, and wrap. The
prefix transfer canonicalizes effective memory as exact sparse overrides and
can prove repeated concrete `(C,D,A,memory)` state only when the accumulator is
known. Schema v25 publishes the first such repeated-state proof as
`bounded_exact_cycle`, including first-seen/repeated transition indices, period,
registers, and sparse memory overrides. Schema v25 also publishes
`bounded_state_snapshots` for every analyzed transition. Each snapshot binds
the pre-step C/D/A registers to canonical sparse evolved-memory overrides; an
input-dependent accumulator remains null. A null cycle certificate means only
that the selected finite trace established no exact concrete repeat. It does
not prove that longer or input-dependent execution is acyclic.
Schema v25 adds opt-in `bounded_worklist` evidence under an explicit
`worklist_state_limit` from 1 through 4,096, also exposed as
`--worklist-state-limit N`. The worklist transfer owns and enforces that
ceiling; the public analyzer reuses it so direct calls cannot bypass the
reviewed bound.
Input branches cover all 256 byte values plus EOF;
a separate EOF-state bit prevents later ordinary bytes after EOF. Canonical
`(C,D,A,memory,EOF-state)` nodes are explored FIFO and deduplicated. The
immutable 59,049-word initial image is expanded once per requested worklist and
shared beneath each state's sparse evolved-memory overrides; recurrence-backed
reads therefore do not rebuild the same initial prefix for every state. The
`input_branch_points` metric counts only non-EOF input states that actually
expand to byte-plus-EOF alternatives; an EOF-sticky input has one successor. A
`maximum_first_seen_transition_index` is updated when each unique successor is
admitted, so queued states retain their first-seen depth even if the state cap
truncates before exploration. A complete queue drain reports closed bounded
reachability; hitting the unique-state cap reports `truncated=true` with a
nonempty frontier and makes CLI acceptance
nonzero. Schema v25 derives `reachable_cycle_detected` and the deterministic
`reachable_cycle_witness` from exact directed edges in the admitted known
graph. Each witness state publishes C/D/A, canonical sparse memory overrides,
and the sticky EOF flag. Schema v26 additionally publishes
`reachable_cycle_entry_path`, the deterministic shortest path from the canonical
entry state to the first state of that selected cycle witness using only exact
known edges. The path may be published for a cycle already proved before a
worklist cap is reached; it remains bounded known-graph evidence and never
promotes an unexplored frontier to reachable or closed. Schema v27 also
publishes one `terminal_status_witnesses` entry for every terminal status
actually observed
by the bounded worklist. Each witness binds that status to one exact terminal
source state and the deterministic shortest known-edge path from the canonical
entry state. Statuses are ordered canonically; an observed witness remains exact
if truncation occurs later, while absence never characterizes the unexplored
frontier. Schema v29 adds `closed_terminal_status_counts`: after the worklist
queue drains, it repeats the complete canonical terminal-status counts and may
therefore be empty; a truncated worklist publishes `null` because unseen states
could still reach additional terminals. The existing `terminal_status_counts`
remains observed known-graph evidence regardless of later truncation. Schema v30
adds nullable `closed_all_paths_terminate`: a drained finite exact-state graph
publishes true exactly when it is acyclic, false when a reachable directed cycle
proves at least one nonterminating path, and null under truncation. Schema v31
adds nullable `closed_all_paths_halt`: after the same finite closure it is true
only when every complete terminal status is `halted`, false for any rejection or
reachable cycle, and null under truncation. Thus termination includes rejection
while all-path halt denotes successful historical halt. When a worklist is
requested, CLI success now requires that closed all-path halt proof; closed
rejection graphs therefore fail even when a shallower prefix was accepted.
Schema v32 adds nullable `frontier_state_witness` and `frontier_entry_path`. A
truncated worklist deterministically selects its first pending FIFO frontier
state and publishes the exact entry path to that state; if the state cap blocks
the first successor admission, the path may end at that exact unadmitted
successor. Closed worklists publish null for both fields. The witness identifies
the bounded unknown boundary only and does not imply that its outgoing behavior
was explored. An empty
cycle witness proves only that no cycle was found in the
admitted known graph; under truncation it does not characterize the unexplored
frontier. Repeat edges caused only by branch merges do not become cycle claims;
a proven graph cycle also makes CLI acceptance nonzero. Schema v25 also
publishes exact SCC summaries over only the admitted known-edge graph:
`known_graph_strong_component_count`, `known_graph_cyclic_component_count`,
`known_graph_cyclic_state_count`, and
`known_graph_largest_cyclic_component_states`. The SCC cycle verdict is checked
against the independent deterministic cycle-witness search before publication.
Under truncation these counts characterize only edges already known; unexplored
outgoing edges may later merge components, so the report does not promote the
partial SCC partition to whole-program evidence. After a complete queue drain,
schema v25 additionally identifies cyclic sink SCCs as exact closed recurrent
regions and publishes their component/state counts, largest size, and one
deterministic cycle witness. Schema v28 adds `closed_recurrent_entry_path`, the
deterministic shortest known-edge path from canonical entry to that selected
recurrent witness. A closed acyclic graph publishes an empty path; truncation
publishes `null` alongside the other closed-recurrence fields because unknown
outgoing edges may invalidate sink closure. A synthetic escaping-cycle fixture
proves this path targets the recurrent sink rather than blindly reusing the
first general cycle witness. Schema v25 models a provable
non-graphical fixed fetch as an exact self-loop edge instead of a terminal
status. The three-word `b"utO"` fixture
(two inputs then halt) exercises 65,536 merge edges without a graph cycle, while
two-word `b"ut"` reaches a fixed-fetch self-loop beyond a two-transition prefix.
A false cycle flag under truncation does not prove the unexplored graph acyclic.
Schema v25 also publishes `explored_accessed_addresses`,
`explored_highest_accessed_address`, and `explored_minimum_words` for worklist
transitions. These are exact for explored states only. The recurrence-read
fixture `b"('"` touches addresses 0, 1, 2, and 41 and therefore requires 42
words within its closed explored graph. Schema v34 additionally publishes exact
explored mutation evidence: code/data alias transition count, committed write
count and addresses, and self-encryption transition count and addresses. Only a
transition with an exact successor contributes committed writes, so a planned
`*` or `p` write followed by invalid self-encryption remains rejection evidence
rather than a claimed committed mutation. These fields are complete for a
closed requested worklist and remain explicitly explored-only when the state
cap truncates the graph. The code/data-aliasing and self-modification
analysis-limit identities include that selected worklist scope. Schema v35
adds `explored_data_mutation_witness` for the first FIFO-explored committed data
write whose final memory value differs from the exact pre-write data value. It
records the source state and shortest entry path, address, previous value,
planned write value, final value after any same-address self-encryption, and
alias flag. The entry-wrap fixture's first such event is the byte-1 branch at
`(C,D,A)=(2,40,1)`, which changes M[40] from 29,524 to 29,523. A null witness
means no effective data mutation was observed in explored states and makes no
claim across a truncated frontier. Schema v36 adds
`bounded_worklist_data_mutation_source_context`, which maps the witness address
back to loaded position/raw byte offset/initial byte when it belongs to the
loaded source image and reports whether the pre-write value still matches that
initial byte. Recurrence addresses stay explicitly unmapped. A 41-word admitted
extension of the entry-wrap fixture with two leading whitespace bytes mutates
loaded position 40 (initial byte 122), maps it to raw offset 42, and proves its
pre-write value still matches the initial source byte. The source-map limit
identity includes selected worklist size and closed/truncated status whenever
this context is requested. Schema v37 adds
`explored_effective_data_mutation_transition_count` and
`explored_effective_data_mutation_addresses`. They count only committed data
writes whose final value after any same-address self-encryption differs from the
exact pre-write data value. Rejected plans and no-op committed writes are not
classified as effective data mutation. The entry-wrap fixture has 256 effective
explored data-mutation transitions, all at address 40; byte input 0 is the one
committed no-op branch. Schema v38 adds
`bounded_worklist_effective_data_mutation_source_map`, which maps every distinct
effective mutation address to loaded position, raw byte offset, and initial
source byte when the address belongs to the loaded image. Recurrence addresses
remain in the ordered map with null source coordinates. A 41-word variant with
a second `*` has effective mutation addresses `(40,41)`; with two leading
whitespace bytes, address 40 maps to raw offset 42 and address 41 remains
recurrence-derived. The source-map limit suffix is now
`data-mutation-evidence` to cover both the first witness and aggregate map.
Schema v39 adds `bounded_worklist_committed_write_source_map`, mapping every
distinct committed write address to loaded source coordinates when possible.
This includes self-encryption and committed data writes rather than only data
writes that change final memory. With two leading whitespace bytes, the
entry-wrap fixture maps committed addresses 0 through 6 to raw offsets 2 through
8 while recurrence address 40 stays explicitly unmapped. The source-map limit
suffix becomes `worklist-mutation-evidence` to describe the full explored
mutation footprint. Schema v40 separately publishes committed data-write count
and addresses plus role-specific committed-data-write and self-encryption source
maps. The entry-wrap graph has 257 committed data-write transitions at address
40, while its explored self-encryption addresses are 0 through 6. Role-specific
maps avoid inferring data-write participation by subtracting address sets, which
would be unsound if a future reachable address participates in both roles.
Schema v41 adds `explored_effective_data_mutation_value_domains`, preserving the
exact sorted sets of observed pre-write and final values for each effectively
mutated address. Entry-wrap observes only pre-write 29,524 and 256 distinct
final values at address 40. In the 41-word multi-mutation graph, recurrence
address 41 has singleton pre-write/final domains 29,409 and 9,803. The total
reported value domain is bounded by explored transitions under the explicit
worklist state cap;
a truncated graph does not imply values beyond its frontier are absent. Schema
v42 adds `bounded_worklist_effective_data_mutation_value_source_map`, directly
joining each exact observed value domain to loaded source coordinates when the
address belongs to the source image. It also records whether the initial source
byte occurs in the observed pre-write domain. Loaded address 40 in the 41-word
fixture reports true; recurrence address 41 carries null source coordinates and
a null initial-byte match result. This preserves the loaded-versus-recurrence
source-map boundary while exposing bounded value-flow evidence. Schema v43
updates the `dataflow` analysis-limit identity to include the requested worklist
size, closed/truncated status, and explored-only scope when worklist evidence is
present. Prefix-only analysis keeps its existing identity unchanged. Schema v44
adds exact per-address observed value domains for instruction fetches, semantic
data reads, and self-encryption inputs across the explored worklist. The closed
input-crazy graph records 58 encryption-input values at address 1 despite those
branches rejecting; the truncated entry-wrap graph records 257 semantic
data-read values at address 40. Ordering is canonical by address and value. A
truncated worklist does not imply its observed value domains are complete beyond
the frontier. Schema v45 adds source-linked maps for explored fetch, semantic
data-read, and encryption-input domains. Loaded addresses retain source
position, raw byte offset, initial source byte, and an exact
initial-byte-membership flag; recurrence addresses remain null-mapped. The
source-map worklist suffix becomes
`worklist-value-evidence`, reflecting both mutation and observed read-value
evidence under the selected finite graph scope. Schema v46 adds exact
per-address domains for committed data-write values and committed
self-encryption outputs. Rejected input-crazy branches contribute no committed
data-write values, while the accepted entry self-encryption contributes output
111 at address 0. The truncated entry-wrap graph has 257 committed data-write
values at address 40, matching the 257 exact semantic data-read values observed
there. These output
domains remain explored-only across a truncated frontier. Schema v47 adds
`explored_evolved_fetch_witness` and `explored_evolved_data_read_witness` for
the first FIFO-explored entry-reachable read that differs from immutable initial
memory. The closed six-state `b"(&&$^"` graph reaches instruction fetch
M[95]=9,810 from initial 29,430; the closed five-state `b"(&&%M"` graph reaches
a
semantic data read M[41]=49,218 from initial 29,558. Both witnesses bind the
exact state and shortest known entry path, directly proving bounded execution
consumes prior-mutated memory. Schema v48 replays each witness's exact shortest
entry path and reports the last committed writer kind plus its one-based path
transition index. The evolved M[95] fetch comes from transition 4's data write;
the evolved M[41] read comes from transition 2's data write. Writer selection
uses commit order, so same-address self-encryption wins over an earlier data
write in that transition. Schema v49 adds source-linked committed data-write
and self-encryption output value maps. In the whitespace-prefixed 41-word
fixture, address 40 data writes map to loaded position 40/raw offset 42 and do
not contain initial source byte 122. Self-encryption at loaded position 0 maps
to raw offset 2 and has output 111 rather than initial byte 117. A recurrence
write at address 40 in the short entry-wrap fixture remains explicitly unmapped.
Schema v50 adds planned data-write transition count, addresses, and exact value
domains independently of commit success. The closed input-crazy graph has 257
planned writes at address 1 spanning 58 values and no committed data writes
because all 257 branches reject. Entry-wrap has 257 planned writes at address 40
and its planned values equal its committed write values. This makes rejected
plans observable without mislabeling them as durable mutation. Schema v51 adds
a source-linked map for planned data-write value domains. Closed input-crazy's
rejected plans map to loaded position/raw offset 1 and initial byte 61, but its
committed data-write value map remains empty. The short entry-wrap fixture's
planned address 40 remains recurrence-derived and therefore null-mapped. Schema
v52 separately counts committed data writes whose final value after any
same-address self-encryption equals their pre-write value. Entry-wrap has one
final no-op and 256 effective mutations at address 40; their sum exactly equals
the 257 committed data writes. Input-halt and input-crazy have zero committed
data-write no-ops. This final-value classification remains valid if mutation
roles alias. Schema v53 adds `explored_data_write_noop_witness` for the first
FIFO-explored entry-reachable committed data-write final no-op. Entry-wrap's
byte-0 branch has address 40 with previous/planned/final value 29,524 and
shortest entry path `(C,D)=(0,0),(1,1),(2,40)`; it does not alias
self-encryption. A null
witness means only that no final no-op was observed in the explored graph unless
the worklist is closed. Schema v54 adds exact explored transition counts and
distinct address sets for evolved fetches and semantic data reads. The closed
`b"(&&$^"` graph has one evolved fetch at address 95; closed `b"(&&%M"` has one
evolved data read at address 41. Entry-wrap observes zero evolved fetches and
256 evolved data-read transitions at address 40. Aggregate absence remains only
an explored-graph statement under truncation. Schema v55 adds exact per-address
domains containing only values that differ from immutable initial memory. The
closed evolved-fetch graph reports value 9,810 at address 95; the closed
evolved-data-read graph reports 49,218 at address 41. Entry-wrap's 256 evolved
data-read values at address 40 equal the exact 256 effective-mutation final
values and exclude initial/no-op value 29,524. Schema v56 links evolved-read
witness control flow to source coordinates by mapping every entry-path state's C
pointer. The six-state evolved-fetch path maps C=0 through 4 to loaded/raw
positions 0 through 4 and leaves recurrence C=95 null-mapped. The evolved-data
read path maps C=0 through 3 entirely to loaded source. The source-map suffix
becomes `worklist-value-and-control-path-evidence`.
Schema v25 adds
`explored_wraparound_transition_count` and changes the report's wraparound
analysis-limit identity to include a requested closed/truncated worklist. Schema
v33 adds `explored_wraparound_witness` for the first FIFO-explored wrap. The
witness records the exact source state, its shortest known entry path, resulting
C/D pointers, and separate code/data wrap booleans. A null witness means only
that the explored graph contains no observed wrap; truncation never promotes
that absence across the frontier. A canonical near-boundary snapshot proves
C/D=59,048 advance to zero and is counted exactly without implying that entry
reaches that snapshot. Separately,
the admitted 22-word `b"u'<%$#>=<;:987654321NN"` fixture proves a real
entry-reachable wrap on its EOF branch: input sets A=59,048, `p` writes 59,048
to M[40], two `j` steps steer D back to 40, and the sixth transition wraps D to
zero. A 1,544-state public worklist reaches that branch and reports one explored
wrap while retaining a 257-state frontier and `truncated=true`. The two-word
`b"u="` fixture (input then crazy) closes in 258 states,
resolving all 257 byte/EOF branches to concrete invalid-self-encryption
terminals. The five-word `b"u'&%$"` fixture closes in 1,286 states after one
input and four `j` steps. Its deterministic cycle entry path contains six exact
states with `(C,D)` pairs `(0,0),(1,1),(2,40),(3,37),(4,29489),(5,29489)`,
extending checked input-dependent cycle depth while remaining within the
explicit worklist cap. The 15-word `b"u'&%$#\"!~}|{zyx"` fixture extends
that family through 14 post-input jumps: its exact graph closes in 3,856 states
and the deterministic cycle entry path contains 16 states, exercising about 94%
of the reviewed state ceiling without truncation. The one-word-longer
`b"u'&%$#\"!~}|{zyxw"` fixture reaches the 4,096-state maximum after
3,840 states are explored. It leaves 257 exact frontier states and records
first-seen depth 17, publishes the deterministic path to the first unexplored
state, and
keeps cycle/all-path claims unknown across that frontier. This is still bounded
evidence and does not establish automatic or unbounded reachability. Without
this opt-in graph, a `p` whose accumulator
depends on prior input remains unresolved rather than assigned a guessed value.
A non-graphical fetch
is stronger: the preserved 1998 interpreter executes `continue` before decode,
encryption, or pointer advancement, so the unchanged C/D state proves a fixed
fetch cycle. The two-word `b"c'"` fixture reaches exactly that third-step state
at `C=2`, `D=40`, `M[2]=29503`. The three-word `b"('&"` fixture continues
through three exact `j` steps and proves a recurrence-backed fourth fixed-fetch
cycle at `C=3`, `D=39`, `M[3]=29487`. The transfer module now reconstructs
memory/state through one generic next-transition primitive over an explicit
finite accepted prefix. The four-word `b"('&%"` fixture continues through four
`j` steps and then uses that primitive to prove a fifth recurrence-backed fixed
fetch at `C=4`, `D=29490`, `M[4]=29489`. Historical recurrence words are
derived only when a bounded read needs them.
Schema v25 publishes `bounded_fetch_source_map`: each resolved instruction
fetch carries its bounded transition index, fetched address/value, and original
loaded source position/raw byte offset/initial byte when that address belongs to
the loaded source image. Recurrence-only addresses carry null source
coordinates.
The context also distinguishes a still-original source value from an evolved
fetch value. Schema v25 separately publishes `bounded_fetch_value_lineage` for
every resolved fetch, `bounded_data_read_value_lineage` for every semantic `j`,
`i`, `*`, or `p` data operand, and
`bounded_encryption_input_value_lineage` for each resolved self-encryption
input.
Origins are exactly `loaded-source`, `recurrence-initialization`, `data-write`,
or `self-encryption`; prior writes retain the exact transition index. Data-read
lineage is sampled before current-transition writes, while encryption-input
lineage is sampled after a same-transition data write and before encryption
commits. The `b"(&&$^"` fixture proves transition 6 fetches recurrence address
95 from the value written by transition 4, `b"(&&%M"` proves transition 4 reads
evolved `M[41]=49218` from transition 2's data write, and the entry rotate-alias
fixture proves its same-transition data write becomes the encryption input. The
companion `bounded_memory_access_source_map` applies source-coordinate rules to
every exact fetch, actual data read, planned data write, and self-encryption
address role in the bounded prefix.
The bounded memory requirement records the sorted addresses touched by
fetch/data/write/encryption semantics and the
minimum word count needed to load the source and reproduce those accesses. A
future pointer value alone is not a memory touch; for example the proven
non-graphical third-step cycle keeps `D=40` without reading address 40.

Initial-image admission is deliberately narrower than whole-program safety.
Schema v25 keeps 16 exact transitions as the default and admits an explicit
finite `transition_limit` from 1 through 256. The CLI exposes the same
request as
`--transition-limit N`. Analysis stops earlier on halt, rejection, fixed-fetch
cycle, exact repeated concrete state, or unresolved input-dependent state. A
published exact cycle makes the CLI result nonzero because the requested finite
prefix was not traversed to its bound. The legacy second-through-fifth
fields project the first four continuation records, while memory/source-access
evidence uses the complete selected trace. A 32-cell sequential-output fixture
proves transition 17 and later reporting under an explicit request, and a
256-cell fixture closes the reviewed maximum. The report records the selected
bound in `bounded_transition_limit`, the bounded-memory scope, and every
limit-dependent analysis string. Reachability beyond that selected finite bound,
automatic or unbounded dataflow/evolved-memory equivalence, higher-level
C/source-map linkage, and graphs beyond an explicit worklist cap remain open.

## Invariants

- The fixed historical address range is closed structurally; this does not
  imply which addresses are reachable or whether a particular run wraps a
  pointer.
- Per-cell encryption-target classification does not imply reachability. The
  bounded transfer records resolve only the explicitly selected finite prefix.
- Finite-prefix report evidence never implies control flow after the selected
  transition limit. A separate next-transition call requires the caller to
  supply the exact accepted prefix explicitly. Replay first requires at least
  two source words for the historical recurrence base. The entry opcode is then
  independently decoded from source cell zero, its transition is recomputed from
  that derived opcode, and every continuation record is recomputed from the
  current bounded state before its writes are replayed. General
  reachability remains unproved.
- Every reported initial cell preserves its loaded position and raw-source byte
  offset, and every report binds the exact source bytes and historical profile.
  Bounded fetch and memory-access source context map only addresses in that
  loaded image; recurrence addresses remain explicitly unmapped instead of
  receiving invented offsets. Fetch-value lineage is independent of source
  coordinates and may therefore identify a recurrence address as originating
  from an exact earlier write without inventing a source position. Worklist data
  mutation context follows the same rule: only loaded-image addresses receive
  source coordinates, and its limit identity carries the selected worklist
  frontier.
- Bounded memory evidence counts only addresses actually touched by the analyzed
  prefix and never treats a future code/data pointer as an observed access.
- Worklist mutation counts and address sets describe exact explored states; a
  truncated frontier never promotes those observations to whole-program
  mutation absence or completeness.
- Future dynamic analyses must state their bounded assumptions rather than
  executing arbitrary guest work to completion or treating unknown as safe.
- The verifier is tested against valid cases and deliberately mutated invalid
  cases so acceptance and rejection boundaries are evidenced independently.

## Failure Behavior

Unknown or unproved equivalence is rejection or an explicitly bounded result,
never implicit acceptance. The CLI prints canonical JSON for both admitted and
rejected initial images, returning a nonzero status when the image is rejected.
Unreadable source fails before a semantic report is emitted.

## Verification

- Expected durable artifact surface: `verifier/`, `tests/differential/`,
  `tests/exhaustive/`, `tests/fuzz/`.
- Required evidence: known-valid fixtures, seeded invalid mutations,
  counterexamples for rejected candidates, and deterministic replay.
- Prerequisite completion evidence: `safe-rust-malbolge-vm`,
  `canonical-malbolge-target-profile`.
- Current executable evidence covers known-valid source, exact loader
  whitespace, lexical rejection, recurrence underflow, historical capacity,
  all 8,836 graphical-byte/position decode pairs against an independent table
  anchored to the preserved historical interpreter `xlat1`, load-admission
  parity anchored to its `strchr("ji*p</vo", ...)` check, historical pointer
  assignment/wrap closure, `i`/`v`/ordinary post-step encryption-target
  classification anchored to the preserved interpreter order, positional decode
  rejection, exact second-step input/no-op/halt/invalid-encryption fixtures,
  explicit input-dependent-crazy unresolved evidence, a 25-case public CLI
  differential including recurrence-backed entry `j`, 16 seeded invalid
  positional mutations with byte-exact replay, exact third/fourth/fifth-step
  halt or fixed-fetch-cycle evidence, recurrence-backed bounded memory
  requirements, default-16 plus explicit-32 and maximum-256 sequential-output
  bound fixtures, bounded loaded-source/raw-offset fetch/read/write/encryption
  provenance, exact loaded/recurrence/prior-data-write fetch-value lineage,
  byte-exact CLI/library report parity, bounded analysis limits, CLI
  second/third/fourth rejection status, and CLI read failure.

## References

- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/verification-trust-boundary.md`
