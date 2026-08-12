# Emitted Malbolge Verifier

This directory owns verifier-side analysis that is deliberately smaller than a
Malbolge execution engine. Candidate generators, optimizers, and compilers do
not gain correctness authority by invoking these tools; each checker publishes
only the bounded result its contract can establish.

`emitted_malbolge.py` implements the first slice of the emitted-Malbolge static
analyzer. It checks the `malbolge-1998` initial source image: exact C-locale
whitespace, graphical ASCII, historical profile capacity, and position-dependent
load decode. Schema v21 retains the legacy exact entry-through-fifth
fields, `bounded_continuations`, and adds nullable `bounded_exact_cycle`
evidence. Sixteen transitions remain the default; callers may request a finite
total limit from 1 through 256. The
single-pass bounded trace replays
committed writes before resolving fetch/data cells, code/data aliasing, planned
writes, encryption input/output, input dependence, halt/rejection, pointer
succession, and wrap without unbounded guest execution. The
report also publishes the minimum word footprint and exact addresses actually
touched by the analyzed prefix; merely-held future C/D pointers are not counted.
For each resolved bounded fetch, schema v21 maps loaded-source addresses back
to the original loaded position/raw byte offset and initial source byte, while
recurrence-only fetches remain explicitly unmapped. The record also states
whether the fetched value still equals that initial source byte. Schema v21
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
v21 publishes the first such proof as `bounded_exact_cycle`, including the
first-seen/repeated transition indices, period, registers, and sparse memory
overrides. It also publishes `bounded_state_snapshots` for every analyzed
transition. Each snapshot records the pre-step C/D/A registers and canonical
sparse evolved-memory overrides; input-derived unknown `A` remains null rather
than being guessed. A null cycle field means only that this selected finite
prefix did not establish an exact concrete repeat; it does not prove a longer
or input-dependent cycle absent. An optional exact-state worklist can be
requested with `--worklist-state-limit N`, where `N` is 1 through 4,096. It
branches historical input into all 256 byte values plus EOF, keeps EOF sticky
for later reads, deduplicates `(C,D,A,memory,EOF-state)`, and reports either
closed reachability or explicit frontier truncation in `bounded_worklist`.
Schema v21 also records `reachable_cycle_detected` from exact directed edges in
the known graph. Repeat-heavy branch merges are not treated as cycles, and a
proven cycle makes requested CLI analysis fail. Historical fixed-fetch cycles
become exact self-loop graph edges rather than terminal states. Thus `b"utO"`
(two inputs then halt) has many merge edges but no cycle, while `b"ut"` reaches
a fixed-fetch self-loop. Schema v21 additionally records exact explored-graph
memory addresses, the highest accessed address, and minimum word capacity under
`bounded_worklist`; truncation keeps that footprint explicitly incomplete. The
`b"u="` input-then-crazy fixture closes in 258 states: every byte/EOF branch
resolves concretely instead of retaining an unknown accumulator.
A four-word `b"('&%"` fixture uses it to prove a recurrence-backed fifth
fixed-fetch cycle at `C=4`, `D=29490`, `M[4]=29489`; schema v21 publishes that
exact transition and its bounded memory footprint. Schema v21 keeps sixteen
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
