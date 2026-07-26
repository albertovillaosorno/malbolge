# User-Supplied DOOM Interoperability Boundary

- Status: Engineering boundary accepted; legal application remains fact-specific
- As-of date: 2026-07-26
- Counsel review: Not performed

## Question Presented

How can the repository test interoperability against DOOM source without
redistributing DOOM source or game data or claiming ownership of generated
third-party material?

## Verified Baseline

The official `id-Software/DOOM` repository identifies the released source under
GNU GPL 2.0 and states that real DOOM game data is still required. Its historical
README also explains that a copyrighted sound library prevented release of the
DOS source path reviewed by the authors.

The source evidence is cataloged in
[DOOM bibliography record][doom-bib].

## Repository Boundary

The public repository does not vendor DOOM source or game data. A user may place
their own source checkout in the Git-ignored root `doom/` directory for local
interoperability testing.

Repository-authored `interop/algorithms/amalgamate.rs`, `quality.rs`, and host
adapters may inspect or transform that local input. Generated intermediate files
remain under Git-ignored `out/` directories unless a later source-specific legal
review approves another publication boundary.

The tooling must preserve provenance and required notices and must not label a
transformed third-party source file as MIT merely because the transformation
algorithm is MIT licensed.

## Not Established

This record does not establish that any particular user's source or data copy is
lawfully acquired, that a particular generated output may be redistributed, or
that all transformations have the same license consequences in every
jurisdiction.

## Required Facts Or Authorities

A public release of transformed DOOM source or game-derived data would require a
new review of the exact inputs, output, notices, distribution method, and
applicable license obligations.

## Sources

- [DOOM open source bibliography record][doom-bib]
- `.gitignore`

## Review Boundary

Re-review before any DOOM-derived generated source, binary, `.malbolge`, or game
data is committed or distributed by this repository.

[doom-bib]: ../../bibliography/organizations-and-projects/id-software-doom.md
