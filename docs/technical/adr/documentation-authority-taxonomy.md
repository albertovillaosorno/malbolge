# Documentation Authority Taxonomy

## Status

Accepted.

## Context

The repository needs durable decisions, technical specifications, research
records, legal analysis, and source provenance. A single global ADR tree scales
poorly because unrelated domains compete for one taxonomy and decision records
begin to absorb material that should remain ordinary documentation.

The repository also needs a shape that Jig can validate mechanically without
requiring Malbolge to own a second documentation-linter implementation.

## Decision

Documentation is organized by authority family before subject taxonomy.

The four authority families are `technical`, `research`, `legal`, and
`bibliography`. Each family owns a local `adr/` directory for decisions that
belong to that family. A global `docs/adr/` directory is not permitted.

ADRs contain bounded durable decisions and material alternatives. They do not
contain implementation tutorials, research result dumps, legal-source summaries,
bibliography entries, TODO history, or chat transcripts merely because those
items influenced a decision.

`docs/cspell/` remains under `docs/` as editorial tooling support. It is not an
authority family.

## Alternatives Considered

### Global ADR repository

A single `docs/adr/` tree can provide strong individual ADR discipline, but at
large scale it becomes a monolithic taxonomy spanning unrelated knowledge
owners. This repository rejects that shape.

### No ADRs outside technical documentation

Keeping every decision under technical documentation would incorrectly make
research-method, legal-handling, and bibliography-governance decisions appear
to be technical behavior.

## Consequences

- Readers choose the authority family before navigating subject taxonomy.
- Decision records remain near the documentation they govern.
- Bibliography and research remain independent surfaces.
- Jig can validate one closed documentation topology later without Malbolge
  implementing a duplicate validator.
- Cross-family decisions require one primary owning ADR and references from
  affected documents rather than duplicated accepted authorities.

## Implementation Notes

The documentation root is governed by `docs/README.md`. Each family maintains
an index, template surface, and local ADR guidance. Empty subject directories may
exist during planning, but authority is created only by reviewed records.
