# Interoperability

Interoperability code adapts user-supplied or external source material without
making that material part of repository architecture or ownership.

`algorithms/` contains deterministic product transformations such as C source
amalgamation and modernization. These are engineering algorithms and do not
require research capsules unless a separate falsifiable research question is
opened.

`adapters/` isolates host/platform effects needed by interoperability fixtures.
Generated transformation output stays under Git-ignored `out/` directories.
