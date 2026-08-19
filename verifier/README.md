# Emitted Malbolge Verifier

This directory owns verifier-side analysis that is deliberately smaller than a
Malbolge execution engine. Candidate generators, optimizers, and compilers do
not gain correctness authority by invoking these tools; each checker publishes
only the bounded result its contract can establish.

`emitted_malbolge.py` implements the first slice of the emitted-Malbolge static
analyzer. It checks the `malbolge-1998` initial source image: exact C-locale
whitespace, graphical ASCII, historical profile capacity, and position-dependent
load decode. Schema v69 retains the legacy exact entry-through-fifth
fields, `bounded_continuations`, and adds nullable `bounded_exact_cycle`
evidence. Sixteen transitions remain the default; callers may request a finite
total limit from 1 through 256. The
single-pass bounded trace replays
committed writes before resolving fetch/data cells, code/data aliasing, planned
writes, encryption input/output, input dependence, halt/rejection, pointer
succession, and wrap without unbounded guest execution. The
report also publishes the minimum word footprint and exact addresses actually
touched by the analyzed prefix; merely-held future C/D pointers are not counted.
For each resolved bounded fetch, schema v25 maps loaded-source addresses back
to the original loaded position/raw byte offset and initial source byte, while
recurrence-only fetches remain explicitly unmapped. The record also states
whether the fetched value still equals that initial source byte. Schema v25
also publishes `bounded_fetch_value_lineage`: each resolved fetch records
whether its value comes from the loaded source, recurrence initialization, or
the latest prior committed data write/self-encryption transition. The companion
`bounded_data_read_value_lineage` applies the same origin vocabulary to actual
`j`, `i`, `*`, and `p` data operands before the current transition commits any
writes. `bounded_encryption_input_value_lineage` then records the value consumed
by self-encryption after any same-transition data write but before encryption
commits. The `b"(&&%M"` fixture proves transition 4 reads evolved `M[41]=49218`
from transition 2's data write, while the entry rotate-alias fixture proves its
planned data write becomes the encryption input in the same transition. Writer
order matches the exact bounded transfer, so self-encryption supersedes an
aliased data write after that input is sampled. A second bounded access map
applies exact source coordinates to each fetch, actual data read, planned data
write, and self-encryption address role.
It can also prove the historical non-graphical-fetch fixed cycle because
`continue` precedes pointer advance. The prefix module now has both one
generic next-transition primitive over an
explicit accepted prefix and one single-pass finite continuation iterator.
Explicit replay first requires at least two source words to seed the historical
recurrence. The entry opcode is independently decoded from source cell zero, the
supplied entry transition is recomputed from that derived opcode before replay,
and every supplied continuation record is recomputed from the current bounded
state before its writes can influence later analysis. Forged entries and
noncontiguous/forged prefixes fail closed. The finite transfer also
canonicalizes evolved memory as exact sparse overrides and can identify a
repeated concrete `(C,D,A,memory)` state when the accumulator is known. Schema
v25 publishes the first such proof as `bounded_exact_cycle`, including the
first-seen/repeated transition indices, period, registers, and sparse memory
overrides. It also publishes `bounded_state_snapshots` for every analyzed
transition. Each snapshot records the pre-step C/D/A registers and canonical
sparse evolved-memory overrides; input-derived unknown `A` remains null rather
than being guessed. A null cycle field means only that this selected finite
prefix did not establish an exact concrete repeat; it does not prove a longer
or input-dependent cycle absent. An optional exact-state worklist can be
requested with `--worklist-state-limit N`, where `N` is 1 through 4,096. The
direct worklist transfer API enforces the same reviewed ceiling, and the public
analyzer reuses that transfer-owned limit rather than duplicating policy. It
branches historical input into all 256 byte values plus EOF, keeps EOF sticky
for later reads, deduplicates `(C,D,A,memory,EOF-state)`, and reports either
closed reachability or explicit frontier truncation in `bounded_worklist`. The
worklist expands the immutable 59,049-word initial memory once per request and
reuses it beneath sparse evolved-memory overrides, avoiding repeated recurrence
construction without changing exact state identity. The
`input_branch_points` count includes only real byte-plus-EOF expansions; an
EOF-sticky `/` transition has one successor and is not counted as a branch.
`maximum_first_seen_transition_index` advances when a unique state is admitted,
so a truncated queued frontier retains its exact first-seen depth even before
those states are explored. Schema v25 also records
`reachable_cycle_detected` and a deterministic
`reachable_cycle_witness` from exact directed edges in the known graph. Every
witness state carries C/D/A, canonical sparse memory overrides, and the sticky
EOF flag. Schema v26 adds `reachable_cycle_entry_path`, the deterministic
shortest known-edge path from the canonical entry state to that selected cycle.
A path remains exact when its edges are already known under truncation, but it
makes no claim about the unexplored frontier. Schema v27 also emits one
`terminal_status_witnesses` record per terminal status actually observed. Each
record contains a concrete terminal source state and the deterministic shortest
known-edge entry path to it. An observed witness remains exact if later
exploration truncates; no witness is inferred for an unexplored status. Schema
v29 adds `closed_terminal_status_counts`: after a complete queue drain it is the
complete canonical terminal count tuple, including empty when no terminal is
reachable; truncation publishes null. The ordinary terminal counts remain
observed known-graph evidence. Schema v30 adds nullable
`closed_all_paths_terminate`: a drained finite exact-state graph publishes true
iff it is acyclic, false when a reachable cycle proves a nonterminating path,
and null under truncation. Schema v31 adds nullable `closed_all_paths_halt`: it
is true only after closure when every complete terminal status is `halted`,
false for any rejection or reachable cycle, and null under truncation. The
five-word `b"u'&%$"` fixture closes in 1,286 states after one input and four
`j` steps, binding a six-state exact cycle entry path through
`(C,D)=(0,0),(1,1),(2,40),(3,37),(4,29489),(5,29489)`. This extends checked
input-dependent cycle depth without weakening the explicit 4,096-state ceiling.
The 15-word `b"u'&%$#\"!~}|{zyx"` input-plus-14-jump fixture closes in
3,856 states and binds a 16-state entry path, exercising about 94% of that state
budget without truncation. A separate 67-word `/ j *` then 64-`j` fixture uses
rotate after the first jump to merge the 257 input branches. Its graph closes in
only 591 states and proves a 41-state cycle entry path with C=0..40, extending
checked input-dependent depth without raising the 4,096-state ceiling. A
separate 123-byte `/jj*` plus 119-`o` fixture uses two pre-merge jumps and
closes in
1,012 states with a 124-state C=0..123 entry path. Transition 4 changes
recurrence M[123] from 29,486 to 49,194; the later evolved fetch at C=123
observes that exact data-write value and becomes a fixed non-graphical
self-loop.
The one-word-longer
`b"u'&%$#\"!~}|{zyxw"` fixture reaches the reviewed 4,096-state maximum
after 3,840 explored states, leaves 257 exact frontier states, and remains
explicitly truncated with no cycle or all-path conclusion. This remains bounded
evidence, not automatic or unbounded reachability. This separates generic
termination from successful historical halt. Requested
worklist CLI success requires that all-path halt proof, so a closed rejection
graph
cannot be masked by an accepted shallower prefix. Schema v32 adds nullable
`frontier_state_witness` and `frontier_entry_path`: every truncated worklist
selects its first pending FIFO frontier state and publishes the exact entry path
to it, including the first unadmitted successor when the cap prevents any
successor admission. Closed worklists publish null for both fields. This makes
the bounded unknown boundary reproducible without claiming the frontier was
explored. An empty cycle witness means no cycle was proved
in the admitted known graph; it says
nothing about a truncated frontier. Repeat-heavy branch merges
are not treated as cycles, and a proven cycle makes requested CLI analysis
fail. Schema v25 also reports the known graph's exact SCC count, cyclic SCC
count, cyclic-state count, and largest cyclic SCC size. These values use only
admitted known edges; a truncated frontier may later connect components, so they
are not whole-program SCC claims. A fully drained worklist additionally
publishes cyclic sink-SCC counts, recurrent-state count, largest recurrent size,
and one deterministic recurrent witness. Schema v28 adds the nullable
`closed_recurrent_entry_path`: an exact shortest entry path only after graph
closure. A closed acyclic graph uses an empty path; truncation uses null because
unknown outgoing edges could invalidate sink recurrence. Historical
fixed-fetch cycles become exact
self-loop graph edges rather than terminal states. Thus `b"utO"`
(two inputs then halt) has many merge edges but no cycle, while `b"ut"` reaches
a fixed-fetch self-loop. Schema v25 additionally records exact explored-graph
memory addresses, the highest accessed address, and minimum word capacity under
`bounded_worklist`; truncation keeps that footprint explicitly incomplete.
Schema v34 also records exact mutation evidence over explored worklist states:
`explored_code_data_alias_transition_count`, committed write count and
addresses, and self-encryption transition count and addresses. A write is
committed evidence
only when the exact transition has a successor; a planned data write on an
invalid-self-encryption rejection is therefore not promoted to a committed
mutation. Closed worklists cover the complete reachable exact-state graph under
the selected historical model, while truncated worklists keep these values
explicitly explored-only. The report's code/data-aliasing and self-modification
analysis-limit strings include that bounded worklist scope when requested.
Schema v35 adds `explored_data_mutation_witness` for the first FIFO-explored
committed data write whose final memory value differs from the value read at
that data address. The witness binds the exact source state and shortest entry
path, address, previous value, planned write value, final value after any
same-address self-encryption, and the alias flag. A null witness means only that
no effective data mutation was observed in the explored graph.
Schema v36 adds `bounded_worklist_data_mutation_source_context`. When the
witness address belongs to the loaded source image, it maps that address to the
loaded position, raw byte offset, initial byte, and whether the witness's
pre-write value still matches the initial source byte. Recurrence addresses
remain explicitly unmapped. The source-map analysis-limit identity includes the
selected worklist size and closed/truncated status whenever this evidence is
requested.
Schema v37 adds `explored_effective_data_mutation_transition_count` and
`explored_effective_data_mutation_addresses`. These count only committed data
writes whose final value, after any same-address self-encryption, differs from
the exact value read before the write. Rejected plans and committed no-op writes
therefore remain distinguishable from effective data mutation. The entry-wrap
fixture has 256 such explored transitions, all at address 40; its byte-0 branch
is the one committed no-op data write.
Schema v38 adds `bounded_worklist_effective_data_mutation_source_map`, mapping
every distinct effective mutation address back to loaded position, raw byte
offset, and initial source byte when that address belongs to the loaded image.
Recurrence addresses remain present with null source coordinates. A 41-word
variant with a second `*` reaches effective mutations at addresses 40 and 41;
with two leading whitespace bytes, address 40 maps to raw offset 42 while 41
remains recurrence-derived. The source-map limit now names worklist
`data-mutation-evidence` because it covers both the first witness and aggregate
address map.
Schema v39 adds `bounded_worklist_committed_write_source_map`, applying the same
loaded-source coordinates to every distinct committed write address, including
self-encryption as well as data writes. The whitespace-prefixed entry-wrap
fixture maps committed addresses 0 through 6 to raw offsets 2 through 8 and
retains recurrence address 40 with null source coordinates. The source-map limit
therefore names broader `worklist-mutation-evidence`, covering first/effective
data mutation evidence plus the complete explored committed-write footprint.
Schema v40 separates committed data-write evidence from self-encryption. The
worklist publishes `explored_committed_data_write_transition_count` and distinct
addresses, and the report adds role-specific committed-data-write and
self-encryption source maps. Entry-wrap has 257 committed data-write transitions
at address 40, while self-encryption occurs at addresses 0 through 6. This keeps
role identity exact even when future addresses participate in both mutation
classes.
Schema v41 adds `explored_effective_data_mutation_value_domains`: for each
effectively mutated address it records the exact sorted set of observed
pre-write values and final values across explored worklist transitions. The
entry-wrap graph observes one pre-write value, 29,524, and 256 distinct final
values at address 40. In the 41-word multi-mutation fixture, recurrence
address 41 has the exact singleton domain 29,409 to 9,803. Domain size remains
bounded by the selected finite worklist state cap, and truncation remains
explored-only. Schema v42 adds
`bounded_worklist_effective_data_mutation_value_source_map`, joining each exact
value domain to loaded position/raw offset/initial byte when available and
reporting whether that initial byte appears in the observed pre-write domain.
Loaded address 40 in the 41-word fixture reports true; recurrence address 41
keeps null source coordinates and a null match result rather than inventing
source lineage. Schema v43 updates the `dataflow` analysis-limit identity to
include requested worklist size, closed/truncated status, and explored-only
scope whenever worklist evidence is present. Prefix-only callers retain the
existing `dataflow:<N>-transition-prefix-only` identity. Schema v44 adds exact
per-address `explored_fetch_value_domains`, `explored_data_read_value_domains`,
and `explored_encryption_input_value_domains` across every explored worklist
transition. The closed input-crazy fixture retains 58 exact encryption-input
values at address 1 even though those branches reject, while the truncated
entry-wrap graph observes 257 semantic data-read values at address 40. These
domains characterize explored states only when the worklist truncates. Schema
v45 adds source-linked maps for those fetch, data-read, and encryption-input
domains. Loaded addresses carry loaded position, raw byte offset, initial source
byte, and whether that byte appears in the observed domain; recurrence addresses
remain explicitly unmapped. The worklist source-map suffix becomes
`worklist-value-evidence` because the mapped evidence now includes reads as well
as mutation footprints. Schema v46 adds exact per-address committed data-write
and self-encryption output value domains. Rejected planned writes remain absent
from committed domains: closed input-crazy has no committed data-write values
but retains the committed entry self-encryption output 111. Entry-wrap records
257 committed data-write values at address 40, matching its explored data-read
domain there. Truncation keeps these write domains explored-only. Schema v47
adds first exact entry-reachable witnesses for instruction fetches and semantic
data reads whose observed value differs from immutable initial memory. The
closed six-state `b"(&&$^"` graph fetches M[95]=9,810 after initial 29,430; the
closed five-state `b"(&&%M"` graph reads M[41]=49,218 after initial 29,558. Each
witness includes the exact source state and shortest known entry path. Schema
v48 replays that exact entry path to identify the last committed writer for the
evolved address. The M[95] fetch names transition 4's data write; the M[41]
data read names transition 2's data write. Writer classification applies commit
order, so same-address self-encryption supersedes a data write when it is the
final writer. Schema v49 applies the existing source-linked value context to
committed data-write and self-encryption output domains. In the whitespace-
prefixed 41-word fixture, data writes to loaded position 40 map to raw offset 42
and exclude initial byte 122; self-encryption at loaded position 0 maps to raw
offset 2 and changes initial 117 to output 111. Recurrence-targeted writes
remain explicitly null-mapped. Schema v50 separately publishes planned
data-write transition count, addresses, and exact value domains before commit
validation. Closed input-crazy has 257 planned writes at address 1 spanning 58
values but zero committed data writes because every branch rejects; entry-wrap
has 257 planned writes at address 40 whose value domain exactly matches its
committed write domain. Schema v51 maps planned data-write value domains back to
loaded source coordinates without changing commit classification. Input-crazy's
rejected plans map to loaded position/raw offset 1 and initial byte 61 while its
committed data-write map remains empty. Entry-wrap's planned writes target
recurrence address 40 and remain explicitly null-mapped. Schema v52 classifies
committed data writes by their final post-encryption effect. It publishes final
no-op count and addresses beside effective mutation count. Entry-wrap has one
final no-op and 256 effective mutations at address 40, exactly partitioning its
257 committed data writes. Closed input-halt/crazy have no committed data-write
no-ops. Schema v53 adds `explored_data_write_noop_witness` for the first
FIFO-explored entry-reachable committed data-write final no-op. Entry-wrap's
byte-0 branch reaches address 40 with previous, planned, and final value
29,524; its shortest entry path has `(C,D)` pairs `(0,0),(1,1),(2,40)` and does
not alias self-encryption. A missing witness remains only an explored-graph
statement under truncation. Schema v54 adds exact explored transition counts and
distinct addresses for evolved instruction fetches and semantic data reads.
The closed six-state `b"(&&$^"` graph has one evolved fetch at address 95; the
closed five-state `b"(&&%M"` graph has one evolved data read at address 41.
Entry-wrap has no evolved fetches and 256 evolved data-read transitions at
address 40.
Truncation keeps aggregate absence explored-only. Schema v55 adds exact
per-address value domains containing only evolved fetch/data-read values. The
closed fetch fixture reports `(9810,)` at address 95 and the closed data-read
fixture reports `(49218,)` at address 41. Entry-wrap's 256 evolved values at
address 40 exactly equal its 256 effective-mutation final values, excluding the
initial/no-op value 29,524. Schema v56 maps each state on evolved-read witness
entry paths from its C pointer back to loaded source coordinates when possible.
The `b"(&&$^"` fetch path maps C=0 through 4 to raw offsets 0 through 4, then
keeps recurrence-backed C=95 explicitly unmapped; the `b"(&&%M"` data-read path
maps C=0 through 3 entirely to loaded source. The source-map worklist suffix is
now `worklist-value-and-control-path-evidence`. Schema v57 extends that exact C
path/source mapping to the first effective data-mutation witness, first final
no-op data-write witness, and first pointer-wrap witness. In the two-whitespace
entry-wrap fixture, mutation and no-op paths map C=0..2 to raw offsets 2..4,
while the wrap path maps C=0..5 to raw offsets 2..7. Schema v58 extends source
linkage to graph-level exact paths: reachable-cycle, closed-recurrent, truncated
frontier, and status-labeled terminal witnesses. The near-cap cycle/recurrent
path maps loaded C=0..14 then leaves recurrence C=15 null; the one-word-longer
frontier maps C=0..15 entirely to source. Terminal maps retain their status.
Schema v59 adds parallel D-pointer source coordinates to every control-path
state. Short entry-wrap D=40 remains recurrence/null-mapped, while the 41-word
loaded mutation fixture maps D=40 to loaded position 40/raw offset 42 and
initial byte 122. C and D source provenance therefore stay independently
explicit. Schema v60 extends evolved-read last-writer provenance with the exact
committed origin value. Replay fails closed if that value differs from the later
observed evolved read. The M[95] fetch therefore binds writer transition 4 value
9,810, and the M[41] data read binds writer transition 2 value 49,218. Schema
v61 source-maps the exact pre-transition writer state behind each evolved-read
witness. With two leading whitespace bytes, the M[95] writer transition 4 maps
C=3 to raw offset 5 while D=95 stays recurrence-backed; the M[41] writer
transition 2 maps C=1 to raw offset 3 while D=41 stays recurrence-backed. Schema
v62 adds the exact historical initial-memory value to every worklist
value/source context, including recurrence addresses, and source-links
changed-only evolved
value domains. Evolved M[95] records initial 29,430 versus `(9810,)`; evolved
M[41] records initial 29,558 versus `(49218,)`, both recurrence/null-mapped.
Schema v63 makes worklist C/D aliasing reproducible instead of count-only: it
publishes sorted aliased addresses and the first shortest-path witness per
address. Closed two-word input graphs have 258 alias transitions across
addresses 0 and 1; with two leading whitespace bytes those addresses map to raw
offsets 2
and 3, and each witness path is source-mapped as well. Schema v64 splits the
combined explored pointer-wrap count into exact C-wrap, D-wrap, and simultaneous
wrap counts. The synthetic near-boundary state records one simultaneous C+D
wrap; the entry-reachable wrap fixture records one D-only wrap and zero C or
simultaneous wraps, while remaining explicitly truncated. Schema v65 separates
non-cycle state merges from cycle-closing repeated edges. The 41-state merged
fixture has 257 repeated edges but 255 exact merges; its first merge joins the
`C=2,D=40,A=1` branch into the already-known `C=3,D=41,A=19714` state and
publishes source maps for both entry paths. The near-cap jump family has zero
merges despite 257 repeated edges. Schema v66 makes the complementary repeated
edge class explicit: the merged fixture has 255 merges plus 2 cycle-closing
repeats, while the near-cap jump family has 0 merges plus 257 cycle-closing
repeats. In both cases the partition exactly equals `repeated_state_edges`.
Schema v67 publishes the first cycle-closing repeated-edge witness with its
source state, shortest entry path, target state, and target index on that path.
The 41-state branch-merged fixture closes at loaded C=40 and source-maps that
target; the near-cap jump fixture closes at recurrence C=15, which stays
explicitly source-null. Schema v68 source-maps the selected reachable-cycle and
closed-recurrent cycle bodies themselves. The 124-byte deep variant maps body
C=123 to loaded source byte 39 while D=243 remains recurrence/source-null.
Schema v69 additionally records the complete distinct C and D pointer addresses
from explored states and source-maps those domains. Near-cap C=0..14 is loaded
while C=15 is recurrence; its D domain is `(0,1,40,121,29405)`. Truncation keeps
these sets explored-only rather than including queued frontier states. Schema
v69 also publishes every cyclic SCC as an ordered tuple of exact cycle states
with source maps. Known-graph components remain bounded evidence under
truncation; closed-recurrent component maps are nullable and exist only after
queue closure.
Schema v25 also counts exact explored transitions whose C or D pointer wraps and
binds the wraparound analysis-limit string to the requested worklist scope.
Schema v33 adds `explored_wraparound_witness` for the first such FIFO-explored
event. It binds the exact source state and entry path to the resulting C/D
pointers and states separately which pointer wrapped. A null witness means no
wrap was observed in the explored graph; under truncation it says nothing about
the remaining frontier. The
`b"u="` input-then-crazy fixture closes in 258 states: every byte/EOF branch
resolves concretely instead of retaining an unknown accumulator.
A four-word `b"('&%"` fixture uses it to prove a recurrence-backed fifth
fixed-fetch cycle at `C=4`, `D=29490`, `M[4]=29489`; schema v25 publishes that
exact transition and its bounded memory footprint. Schema v25 keeps sixteen
transitions as the default but makes finite depth explicit. Library callers and
the CLI `--transition-limit N` option may request from 1 through 256 exact
transitions. The report binds that request in `bounded_transition_limit`,
numeric memory-scope identity, and every bounded analysis-limit string. A
32-cell
sequential-output fixture proves transition 17 and later are reported exactly
when requested, while a 256-cell fixture proves the reviewed safety ceiling.
Automatic or unbounded reachability, higher-level C/source-map linkage, and
longer state graphs beyond an explicit worklist cap remain unproved.

The initial-image report is bounded by the selected historical profile. Sources
that exceed 59,049 loaded words receive a capacity finding without materializing
per-cell decode records. For admitted-size sources, every `InitialCell`
preserves both its whitespace-stripped loaded position and its original source
byte offset.
Stable `MALBOLGE-STATIC-001` through `MALBOLGE-STATIC-004` findings distinguish
lexical, recurrence-base, capacity, and positional-decode failures.

The CLI always emits the canonical UTF-8 report bytes when source bytes are
readable, without platform newline translation. It returns zero only when the
admitted image also has an accepted trace through the requested finite bound (or
halts exactly before that bound). The default request is 16 transitions. Proven
rejection, unresolved input-dependent state, a fixed-fetch cycle, or a
published exact repeated-state certificate returns nonzero; an exact halt at any
resolved prefix step remains an accepted terminal result. Requests outside 1
through 256 fail before source analysis.

Each report also carries a SHA-256 identity for the exact raw source bytes. This
distinguishes inputs that have the same loaded-word semantics, including
whitespace-only mutations, without treating the hash as semantic proof.
