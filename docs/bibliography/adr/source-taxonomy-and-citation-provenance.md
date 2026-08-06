# Bibliography Source Taxonomy And Citation Provenance

## Status

Accepted.

## Decision ID

`jig.malbolge.bibliography.source-taxonomy-and-citation-provenance`

## Context

Technical specifications, research papers, legal analysis, and governance all
consume external evidence. Nesting bibliography under research would imply that
source records belong only to academic experiments, while duplicating source
metadata across documentation families would create drift and conflicting
provenance.

## Decision

`docs/bibliography/` is the repository-wide non-governing source and provenance
catalog.

Records are organized by source subject, not by the document family that cites
them. The initial taxonomy covers programming languages, compiler/runtime
systems, Malbolge and esolangs, superoptimization/program synthesis,
verification/formal methods, accelerator computing, protocols/standards,
validation tooling, documentation/publication systems, research methodology,
AI/code generation, and relevant organizations/projects.

Material claims prefer primary or authoritative sources. Records preserve stable
identity, version or publication metadata when applicable, retrieval date,
source quality, repository relevance, verified claims, and unresolved evidence.
A claim-level provenance ledger records important direct checks, contradictions,
resolutions, and discarded evidence patterns without turning Git history into
external authority.

A bibliography citation never creates repository policy, establishes legal
permission, or proves an experimental conclusion by itself.

## Advantages

- Makes the bibliography source taxonomy and citation provenance boundary
  explicit, reviewable, and stable before implementation depends on it.

## Disadvantages

- Exact taxonomy increases migration work when the documentation contract
  changes.

## Consequences

- One source record can support several documentation families.
- Source currentness and uncertainty remain visible without changing product
  decisions automatically.
- Research papers can generate `.bib` projections from canonical evidence later
  without making BibTeX the only human-readable source catalog.

## Rejected Alternatives

### Research-owned bibliography

Rejected because technical and legal documents consume the same external
sources.

### Per-document source lists without canonical records

Rejected because source identity, version drift, and provenance would be copied
and become inconsistent.

## Evidence

`docs/bibliography/adr/` owns only bibliography-governance decisions. Subject
records use `docs/bibliography/provenance-and-methodology/template.md` as the
baseline shape.

`docs/bibliography/provenance-and-methodology/repository/` owns claim-level
verification ledgers. Those ledgers may cite Git commits as internal decision
provenance, but external facts still resolve to primary or authoritative
bibliography records.

The repository baseline currently contains 47 source/provenance records. The
coverage ledger names the required first-pass classes and 44 canonical baseline
records spanning historical Malbolge, languages, host architectures, compiler
tooling, accelerators, superoptimization, verification, research methodology,
standards, publication metadata, and validation tooling. Every current source
record retains a dated review/access marker and an explicit unresolved or
uncertainty boundary. Empty closed-taxonomy categories are cataloged rather than
padded with fabricated source records.

`src/automation/repository/composition/scripts/validate/bibliography.py`
enforces the closed first-level taxonomy,
README coverage, one canonical template, source-record heading order, dated
provenance, explicit uncertainty, nonempty sources, unique stable identities,
exact validation-package pins, durable external-reference coverage, and the
required baseline. `tests/test_bibliography.py` exercises those fail-closed
boundaries. The validator checks repository evidence shape and coverage; it does
not independently re-fetch or re-prove external claims.
