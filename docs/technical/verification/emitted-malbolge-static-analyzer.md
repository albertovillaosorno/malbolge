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
`malbolge-static-image/v88` retains exact `entry_transition` through
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
becomes `worklist-value-and-control-path-evidence`. Schema v57 applies the same
entry-path C/source mapping to effective-mutation, final-no-op, and pointer-wrap
witnesses. With two leading whitespace bytes, mutation/no-op paths map C=0..2
to raw offsets 2..4 and the wrap path maps C=0..5 to raw offsets 2..7. These are
exact known witness paths only. Schema v58 adds source maps for reachable-cycle,
closed-recurrent, truncated-frontier, and status-labeled terminal entry paths.
The closed near-cap cycle/recurrent path maps C=0..14 to loaded source and
leaves recurrence C=15 null-mapped; the one-word-longer truncated frontier maps
C=0..15
all to loaded source. Terminal path maps preserve the terminal status label.
Schema v59 adds loaded-source coordinates for each control-path state's D
pointer in parallel with C. The short entry-wrap mutation/no-op path keeps D=40
recurrence/null, while the 41-word loaded-mutation fixture maps D=40 to loaded
position 40/raw offset 42/initial byte 122. C and D provenance are independent.
Schema v60 adds the exact committed origin value to each evolved-read witness
and requires it to equal the later observed value. The evolved M[95] fetch binds
9,810 to data-write transition 4; evolved M[41] binds 49,218 to transition 2.
Schema v61 source-maps the exact pre-transition writer state selected by that
provenance. With two leading whitespace bytes, the M[95] writer maps C=3 to raw
offset 5 while recurrence D=95 stays null; the M[41] writer maps C=1 to raw
offset 3 while recurrence D=41 stays null. Writer role/index/value and C/D
source context are therefore joined in one bounded record. Schema v62 adds the
exact historical initial-memory value and initial-memory-membership flag to
every worklist value/source context, independently of loaded-source coordinates.
It
also source-links changed-only evolved fetch/data-read domains: recurrence M[95]
records initial 29,430 versus 9,810, and recurrence M[41] records initial 29,558
versus 49,218. Schema v63 adds exact C/D-alias address sets and one
shortest-path witness per aliased address. A closed two-word input graph has 258
alias
transitions but only addresses 0 and 1. With two leading whitespace bytes those
map to raw offsets 2 and 3; witness paths preserve both C and D source context.
Schema v64 decomposes the explored pointer-wrap total into exact code-pointer,
data-pointer, and simultaneous-wrap transition counts. The canonical synthetic
near-boundary state wraps both pointers; the entry-reachable fixture observes
one D-only wrap and no C/simultaneous wrap before its explicit frontier
truncation. Schema v65 classifies repeated-state edges that merge distinct entry
paths separately from back-edges into the source path. The branch-merged
41-state fixture has 257 repeated edges and 255 exact state merges. Its first
merge records both shortest paths and source-maps them, while the near-cap jump
family has zero state merges despite 257 cycle-closing repeated edges. Schema
v66 publishes that cycle-closing count directly and checks the exact partition.
The merged graph has
255 merges plus 2 cycle-closing repeats; near-cap has 0 plus 257, and each sum
equals the existing repeated-state-edge total. Schema v67 adds the first exact
cycle-closing repeated-edge witness: source state, shortest entry path, target
state, and target index within that path. The branch-merged fixture's target is
loaded C=40 and maps to source position 40; the near-cap target is recurrence
C=15 and therefore remains source-null. Schema v68 separately source-maps each
state in the selected reachable-cycle and closed-recurrent cycle bodies. A
124-byte deep variant has body `(C,D)=(123,243)`: C maps to loaded source byte
39 while D remains recurrence/source-null. Schema v69 records the exact distinct
C and D pointer addresses of every explored state and maps each address back to
loaded source where possible. The near-cap graph has C=0..15 and D addresses
`(0,1,40,121,29405)`; only C=0..14 and D=0,1 are loaded. Under truncation these
are explicitly explored-state domains and do not include unprocessed frontier
states. Schema v69 also publishes every cyclic SCC as exact ordered cycle states
and source-maps each state. Known-graph cyclic components remain partial under
truncation; the closed-recurrent component map is nullable and is emitted only
after complete queue drainage, matching the existing closed-recurrence contract.
Schema v70 partitions explored reads by equality against immutable initial
memory. Every explored fetch is either initial-value-equal or evolved, and every
semantic data read is likewise partitioned; fail-closed invariants require each
partition to sum to its exact explored total. This is deliberately value
equality rather than provenance: a write/reversion could equal the initial
value. The report source-maps the initial-value-equal address sets where loaded
source coordinates exist and leaves recurrence addresses null. Schema v71
extends the same exact initial-value partition to self-encryption inputs. The
non-equal class is named changed-from-initial because a same-transition planned
data write can affect the encryption input before commit validation. Closed
input-crazy has 258 encryption inputs: one initial-value-equal entry input at
address 0 and 257 changed inputs at address 1 spanning 58 exact values. Every
changed branch rejects invalid self-encryption, so zero data writes commit; the
report therefore keeps changed-input value evidence separate from committed
memory provenance and source-maps both classes. Schema v72 attaches a compact
minimum entry-path state count to every exact cyclic SCC. One bounded BFS
supplies the known-graph counts; closed recurrent SCCs publish the same scalar
only after queue closure. The synthetic escaping graph yields cyclic counts
`(1,3)` and recurrent `(3)`, near-cap's 257 SCCs all report 16, and the
124-state deep graph's two SCCs both report 124. Truncation keeps
closed-recurrent depth evidence null. Schema v73 adds role-specific first wrap
witnesses for C, D, and simultaneous C+D pointer wrap in addition to the
existing first observed wrap. The synthetic boundary state proves simultaneous
class assignment but remains intentionally pathless because it is not
entry-reachable evidence. The real EOF wrap fixture fills only the D class and
source-maps that exact reachable D-wrap entry path. Absent class witnesses
remain explored-only absence under truncation.
Schema v74 additionally publishes the sorted distinct explored wrap-transition
signatures rather than only first witnesses. Each signature records source and
result C/D plus wrap-role flags, and the analyzer source-maps source C/D
independently. On the real EOF D-wrap, source C=5 maps to loaded raw offset 7
while source D=40 remains recurrence/source-null. Under truncation this remains
only the set observed in explored states, never a complete reachability claim.
Schema v75 makes reachable non-graphical executable fetches explicit worklist
evidence: exact explored transition count, distinct addresses, exact value
domains, and source-linked value contexts. Closed `b"ut"` contributes 257
self-loop fetches at recurrence `M[2]=29412`. The loaded deep fixture
contributes
two fetches of evolved invalid value 13 at loaded position 123, whose initial
source byte/value was 39; the source map keeps position/raw offset 123 while
marking both initial-value membership checks false. Truncated evidence remains
explored-only.
Schema v76 additionally retains the first exact reachable non-graphical fetch
state and its shortest entry path, then source-maps that path. The recurrence
`b"ut"` case reaches its witness in three states. The loaded deep case reaches
position 123 after 124 states and maps every C position 0 through 123 to loaded
source, directly connecting invalid executable evidence to the bounded control
path. This remains a first-witness link, not exhaustive unbounded reachability.
Schema v77 retains the exact explored input-branch states in deterministic state
order and source-maps each state's C/D pointers independently. Each source
context also records the exact state index when that branch lies on the selected
reachable-cycle, closed-recurrent, or frontier entry path. The 41-state
branch-merged cycle places its single initial input branch at index 0 of both
closed paths. The whitespace-prefixed truncated graph instead links that branch
to frontier index 0 and raw source offset 2. These are explicit bounded path
links; absent indices do not prove an input branch unreachable beyond a
frontier.
Schema v78 retains the complete exact unexplored frontier state set at the
first state-cap truncation. The published count is derived from the deduplicated
set, the first frontier witness/path endpoint must belong to it, and every
frontier state's C/D pointers receive independent source coordinates. The
4,096-state over-cap fixture retains 257 states: 16 at loaded C=15 and 241 at
recurrence C=16. The adjacent restoration fixture retains loaded C=1665 and
recurrence C=1666 as its exact two-state frontier. These states have not been
explored, so the map is boundary evidence rather than successor behavior proof.
Schema v79 retains every exact explored terminal state grouped by status and
source-maps each terminal state's C/D pointers independently. The existing
status-labeled terminal witness remains one shortest entry path; endpoint sets
do not duplicate those paths. Closed `b"u="` publishes all 257 rejected
invalid-self-encryption terminals at loaded C/D=1; closed `b"uP"` independently
publishes all 257 halted endpoints at the same loaded coordinates. A truncated
graph publishes only terminal endpoints explored before its exact frontier.
Closure
therefore promotes the bounded endpoint set to complete reachable terminal
evidence only when the graph itself is closed.
Schema v80 retains every exact explored C=D alias observation as state, alias
address, and fetched value. Result construction requires the observation count
to equal the alias-transition count, the observation addresses to equal the
reported alias-address set, and every exact state to preserve C=D. Public
source contexts map C and D independently. A closed two-word input graph has
258 observations spanning addresses 0 and 1; first-witness paths remain one per
address rather than one per observation. At the 257-state pre-terminal cap,
only the explored C=D=0 entry alias is retained; frontier alternatives remain
unexplored boundary evidence.
Schema v81 retains every exact explored non-graphical executable-fetch state
and value. Result construction requires those observations to project exactly
to the aggregate transition count, address set, and value domains, and each
observed state must retain the exact self-loop edge required by the historical
non-graphical `continue` rule. Closed `b"ut"` has 257 byte/EOF observations at
recurrence C/D=2 while preserving only one shortest representative path. The
loaded-cycle fixture separately maps each observation's loaded C and
recurrence-backed D, so the exhaustive endpoint set adds state/source linkage
without duplicating entry paths or making claims beyond a truncated frontier.
Schema v82 retains every exact explored evolved fetch and evolved semantic
data-read state, including the read address plus immutable initial and observed
values. The exact observations must project to the aggregate evolved-read
count, address set, and value domains, belong to explored graph states, and
remain different from initial memory. Source contexts map the state's C and D
pointers separately from the actual read address. The entry-wrap graph has 256
such data-read states at C=5/D=40/read=40, all with initial value 29,524 and
256 distinct changed values; its final EOF observation reads 59,048. Existing
first-writer witnesses remain compact provenance paths rather than one path per
observation, and truncated frontiers remain outside this explored evidence.
Schema v83 retains every exact explored changed-from-initial encryption-input
state with its encryption address, immutable initial value, and observed value.
Exact observations must reproduce the changed-input count/address/value domains,
belong to explored states, and remain unequal to initial memory. Closed `b"u="`
produces 257 such observations at C=D=encryption-address 1: immutable baseline
61, 58 distinct changed values, and a final EOF observation of 32. These values
are sampled after the same-transition planned data write and before invalid
self-encryption rejects, so they are transition-value evidence rather than
committed-memory provenance; committed data-write count remains zero. Public
source contexts map C, D, and encryption address separately, and truncation
does not infer observations beyond the explored graph.
Schema v84 retains every exact explored planned data-write state, address, and
value. Exact observations must project to the planned-write count, address set,
and value domains and belong to explored states. Closed `b"u="` has 257 planned
writes at address 1. Its state-sorted `(state,address,value)` sequence equals
the 257 changed-encryption `(state,address,observed-value)` sequence exactly.
Public source contexts map C, D, and write address separately. This proves the
same-transition planned value is the self-encryption input on every rejected
branch while committed data-write count remains zero; it does not claim the
planned value ever became committed memory. Truncated frontier states remain
outside both exact observation sets.
Schema v85 retains every exact explored effective committed data-mutation state,
including address, pre-write value, planned written value, final committed
value, and whether same-address self-encryption participates. Exact
observations must reproduce the effective-mutation count/address/previous/result
domains, belong to explored states, and remain true value changes rather than
final no-ops. The entry-wrap graph has 256 observations at C=2/D=40/address 40,
all from previous value 29,524, with 256 distinct final values and no
self-encryption alias. Public contexts map C, D, and mutation address
independently. The graph's one committed final no-op stays in the existing
no-op partition, preserving the exact committed-write split under truncation.
Schema v86 retains every exact explored committed data-write final no-op state,
including address, pre-write value, planned written value, final committed
value, and same-address self-encryption alias identity. Result construction
requires the exact state count/address projection to match the no-op aggregate
and requires every final value to equal its pre-write value. Entry-wrap has one
C=2/D=40/address-40 observation with previous=written=final=29,524 and no alias;
its 256 changed results remain in the effective-mutation partition. Public
contexts map C, D, and write address independently. The existing first no-op
witness retains the sole shortest entry path, and truncation never promotes
unexplored frontier states into exact no-op evidence.
Schema v87 retains every exact explored committed self-encryption state as
state, encryption address, input/output pair, and same-step data-write alias
identity. Exact observations must reproduce the committed self-encryption count,
address set, and output domains; each pair is also checked against the classic
encryption table. The closed `b"u="` graph has one committed observation at
C=D=address 0 with input 117/output 111, while its 257 later invalid encryption
attempts remain rejected input/planned-write evidence. Public contexts map C, D,
and the encryption address independently. This is committed-write evidence only
and never promotes a rejected transition or unexplored frontier state.
Schema v88 retains every exact explored initial-value-equal fetch, semantic data
read, and self-encryption input state. Each state is checked against immutable
initial memory, and its exact state count/address projection must reproduce the
existing initial-value aggregate. Closed `b"u="` has 258 initial-value fetch
states, 257 initial-value data-read states at address 1, and one initial-value
encryption-input state at address 0; the 257 changed encryption-input states
remain the disjoint value-different complement. Public contexts source-map C,
D, and the observed-value address independently. As in schema v70, equality is
value equality rather than provenance, and truncation remains explored-only.
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
of the reviewed state ceiling without truncation. A separate 67-word fixture
decodes as `/ j *` followed by 64 `j` instructions. Rotate after the first jump
merges the 257 input branches; the exact graph closes in 591 states and proves a
41-state cycle entry path with C=0..40, without increasing the 4,096-state cap.
A separate 123-byte `/jj*` plus 119-`o` fixture closes in 1,012 states and
proves a 124-state C=0..123 path. Transition 4 mutates recurrence M[123] from
29,486
to 49,194; the eventual evolved instruction fetch observes the same value and
forms a fixed non-graphical self-loop. A generated 1,665-word restoration
fixture uses nine additional data-return `j`/`*` pairs to rotate M[123] ten
times total, restoring its original graphical value before C reaches it. The
worklist then closes at exactly 4,096 unique/explored states with no frontier
and proves a 1,666-state C=0..1665 entry path. The final C=1665 recurrence
fetch is non-graphical; its source-mapped witness keeps C=0..1664 loaded and
only the recurrence endpoint source-null. The adjacent 1,666-word restoration
image instead reaches 4,096 unique states after 4,095 explored states, retains
a two-state frontier with the full loaded C=0..1665 source path, and reports
`truncated=true`. A generated 1,846-word `/j*i` fixture takes a different
route: after input, jump, and rotate collapse the byte branches, C=3 executes
`i` with loaded M[41]=57 and resumes at C=58, bypassing mutated M[40]. Its exact
graph closes in 4,095 states and proves a 1,793-state path whose loaded C
coordinates are `0,1,2,3,58..1845`; only recurrence C=1846 is source-null and
non-graphical at value 29,441. The adjacent 1,847-word image reaches 4,096
unique states after 4,095 explored states and retains two C=1847 frontier states
instead of claiming closure. A generated 3,582-word late-input fixture keeps C
sequential through loaded position 3579 before `/j*` resolves the input branch.
Its exact graph uses all 4,096 reviewed states with no frontier and proves a
3,583-state C=0..3582 path; C=0..3581 remain loaded/source-mapped and only
recurrence C=3582 is source-null and non-graphical at value 29,421. The adjacent
3,583-word image reaches 4,096 unique states after 4,095 explored states,
retains two exact C=3583 frontier states distinguished by EOF history, and
keeps cycle/closure claims unknown beyond that frontier. The one-word-longer
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
