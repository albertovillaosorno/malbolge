# Emitted Malbolge Verifier

This directory owns verifier-side analysis that is deliberately smaller than a
Malbolge execution engine. Candidate generators, optimizers, and compilers do
not gain correctness authority by invoking these tools; each checker publishes
only the bounded result its contract can establish.

`emitted_malbolge.py` implements the first slice of the emitted-Malbolge static
analyzer. It checks the `malbolge-1998` initial source image: exact C-locale
whitespace, graphical ASCII, historical profile capacity, and position-dependent
load decode. Schema v9 retains the exact entry through fifth transitions and
adds a bounded memory requirement for that exact prefix. The bounded
five-transition prefix replays
committed writes before resolving fetch/data cells, code/data aliasing, planned
writes, encryption input/output, input dependence, halt/rejection, pointer
succession, and wrap without a worklist or unbounded guest execution. The
report also publishes the minimum word footprint and exact addresses actually
touched by the analyzed prefix; merely-held future C/D pointers are not counted.
For each resolved bounded fetch, schema v9 maps loaded-source addresses back to
the original loaded position/raw byte offset and initial source byte, while
recurrence-only fetches remain explicitly unmapped. The record also states
whether the fetched value still equals that initial source byte.
It can also prove the historical non-graphical-fetch fixed cycle because
`continue` precedes pointer advance. The prefix module now has one generic
next-transition primitive over an explicit finite accepted prefix. Supplied
transition records are recomputed from the current bounded state before their
writes can influence later analysis; noncontiguous/forged prefixes fail closed.
A four-word `b"('&%"` fixture uses it to prove a recurrence-backed fifth
fixed-fetch cycle at `C=4`, `D=29490`, `M[4]=29489`; schema v9 publishes that
exact transition and its bounded memory footprint. Automatic/report-level
sixth-and-later control flow, non-fetch source/data/write provenance, and
longer input-dependent cycles remain unproved.

The initial-image report is bounded by the selected historical profile. Sources
that exceed 59,049 loaded words receive a capacity finding without materializing
per-cell decode records. For admitted-size sources, every `InitialCell`
preserves both its whitespace-stripped loaded position and its original source
byte offset.
Stable `MALBOLGE-STATIC-001` through `MALBOLGE-STATIC-004` findings distinguish
lexical, recurrence-base, capacity, and positional-decode failures.

The CLI always emits the canonical UTF-8 report bytes when source bytes are
readable, without platform newline translation. It returns zero only when the
admitted image also has an accepted bounded five-transition prefix. Proven
entry/second rejection, unresolved input-dependent state, or a
third/fourth/fifth-step fixed fetch cycle returns nonzero; a halt at any
resolved prefix step remains an exact accepted terminal result.

Each report also carries a SHA-256 identity for the exact raw source bytes. This
distinguishes inputs that have the same loaded-word semantics, including
whitespace-only mutations, without treating the hash as semantic proof.
