# User-Supplied DOOM Interoperability Boundary

## Status

Engineering boundary accepted; legal application remains fact-specific

## As-of Date

2026-07-26

## Question Presented

How can the repository test interoperability against DOOM source without
redistributing DOOM source or game data or claiming ownership of generated
third-party material?

## Verified Baseline

The official `id-Software/DOOM` repository identifies the released source under
GNU GPL 2.0 and states that real DOOM game data is still required. The engineering
profile in this repository pins commit
`a77dfb96cb91780ca334d0d4cfd86957558007e0`; a fresh checkout of that commit with
Git line-ending conversion disabled matched the 165 official files in the ignored
local source tree byte-for-byte. Its historical README also explains that a
copyrighted sound library prevented release of the DOS source path reviewed by the
authors.

The source evidence is cataloged in [DOOM bibliography record][doom-bib].

## Not Established

This record does not establish that any particular user's source or data copy is
lawfully acquired, that a particular generated output may be redistributed, or
that all transformations have the same license consequences in every
jurisdiction.

## Required Facts

A public release of transformed DOOM source or game-derived data would require a
new review of the exact inputs, output, notices, distribution method, and
applicable license obligations.

## Authorities

- Canonical external authorities are referenced through `docs/bibliography/`
  where available.

## Analysis

The public repository does not vendor DOOM source or game data. The current DOOM
quality profile accepts engine source matching the pinned upstream commit above; a
different revision requires a different explicit profile. A user may place that source
checkout in the Git-ignored root `doom/` directory for local interoperability testing.
External `data/` remains outside the source-code pin and requires its own provenance.

Repository-authored generator infrastructure and generated transforms such as
`algorithms/doom/quality/main.rs` and `algorithms/doom/amalgamate/main.rs` may
inspect or transform that local input. Generated intermediate files remain under
Git-ignored `out/` directories unless a later source-specific legal review
approves another publication boundary.

Source similarity thresholds, behavior probes, stable anchors, and threshold
source binding are engineering controls only. They do not establish that a
particular input/output distribution is lawful or that a percentage has legal
significance.

The tooling must preserve provenance and required notices and must not label a
transformed third-party source file as MIT merely because the transformation
algorithm is MIT licensed.

Re-review before any DOOM-derived generated source, binary, `.malbolge`, or game
data is committed or distributed by this repository.

[doom-bib]: ../../bibliography/organizations-and-projects/id-software-doom.md

## Conclusion Boundary

This record is bounded repository research and is not legal advice.

## Sources

- [DOOM open source bibliography record][doom-bib]
- `.gitignore`
