# Bibliography Source Taxonomy And Citation Provenance

## Status

Accepted.

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
validation tooling, research methodology, AI/code generation, and relevant
organizations/projects.

Material claims prefer primary or authoritative sources. Records preserve stable
identity, version or publication metadata when applicable, retrieval date,
source quality, repository relevance, and unresolved evidence.

A bibliography citation never creates repository policy, establishes legal
permission, or proves an experimental conclusion by itself.

## Alternatives Considered

### Research-owned bibliography

Rejected because technical and legal documents consume the same external
sources.

### Per-document source lists without canonical records

Rejected because source identity, version drift, and provenance would be copied
and become inconsistent.

## Consequences

- One source record can support several documentation families.
- Source currentness and uncertainty remain visible without changing product
  decisions automatically.
- Research papers can generate `.bib` projections from canonical evidence later
  without making BibTeX the only human-readable source catalog.

## Implementation Notes

`docs/bibliography/adr/` owns only bibliography-governance decisions. Subject
records use `docs/bibliography/template.md` as the baseline shape.
