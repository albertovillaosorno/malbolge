# Documentation Model

The repository organizes documentation by authority family before subject
category. This prevents unrelated decisions from collapsing into one global ADR
catalog and gives every durable proposition one owning surface.

## Authority Families

- `technical/` owns repository architecture, contracts, specifications, examples,
  and implementation behavior. It does not own external source authority, legal
  conclusions, or research results.
- `research/` owns questions, hypotheses, methods, experiments, algorithm
  studies, results, and papers. An experiment does not create product policy.
- `legal/` owns dated legal/source-use analysis, license and interoperability
  boundaries, and unresolved legal facts. It does not own technical architecture.
- `bibliography/` owns external evidence, source identity, provenance, standards,
  tools, projects, and scholarly references. It does not create policy, legal
  authorization, or experimental conclusions.

Each family owns an `adr/` directory. ADRs record bounded durable decisions for
that family; they do not replace the family's ordinary records.

A global `docs/adr/` is forbidden. The repository intentionally avoids the
single-ADR-monolith pattern even though individual ADRs use a disciplined,
decision-oriented structure.

## Editorial Support

`docs/cspell/` is repository documentation support used by CSpell. It is not a
fifth authority family and does not own product knowledge.

## Planning Promotion

`ROADMAP.md` and `todo/roadmap/` describe unfinished work. Before product
implementation begins, settled planning decisions are promoted into the owning
documentation family. TODO text is not copied as history; durable decisions,
contracts, research questions, evidence boundaries, and source records are
rewritten into their authoritative form.
