# Planning corpus promotion to durable documentation

## Status

Accepted and implemented

## Intent

Once typed TODO coverage is stable, classify every settled planning
choice into its durable owning surface instead of copying TODO prose wholesale.
Create bounded ADRs for decisions, technical specifications/contracts for
repository behavior, research records and `.tex` artifacts for investigations,
legal records for dated source-use/interoperability analysis, and bibliography
records for external evidence. Populate each TODO's `contract` and `adr_paths`
with real authorities as those records are created. Proposed or unresolved
choices remain visibly proposed; implementation details remain in their owning
technical documents. No global catch-all ADR, duplicate authority, or

chat-history archive is created during promotion.

## Contract

### Proposed Model

This record defines the contract that implementation must satisfy for
`planning-corpus-promotion-to-durable-documentation`. The implementation may
change internal representation or language choices without changing the
observable behavior, trust boundary, or ownership rules stated by its governing
decisions.

### Invariants

- Every settled planning decision is routed to one owning durable document
  family; unresolved choices remain explicitly proposed rather than being
  silently treated as accepted architecture.
- ADRs record bounded decisions and tradeoffs, technical documents describe
  repository-owned behavior, research records hold investigations and
  mathematics, legal records hold dated legal/source-use analysis, and
  bibliography records hold external evidence.
- TODO prose is not copied wholesale into documentation; transient
  scheduling/status language is removed during promotion.
- As authorities are created, TODO `contract` and `adr_paths` fields point to
  real existing files with no invented placeholder paths or duplicate
  authorities.

## Evidence Boundary

- Expected durable artifact surface: the four documentation families plus
  updated `contract`/`adr_paths` metadata across the active TODO registry.
- Prerequisite completion evidence: `documentation-authority-taxonomy`,
  `repository-bibliography-taxonomy-and-citation-provenance`,
  `academic-research-methodology-and-evidence-model`, and
  `complete-bibliography`.
- Evidence must include a complete mapping from active TODO intent to owning
  durable documentation or an explicit unresolved decision record.

## Diagnostics

Missing or competing authority blocks promotion rather than creating a duplicate
or placeholder decision.

## Examples

- No normative example is required at this planning stage unless the contract
  states one.

## Implementation

Implemented. All 80 open and 15 completed typed records resolve to real
contracts; ADR paths resolve where declared. The former README status narrative
is preserved as a dated architecture snapshot, all `Migrated root planning
detail` tails are removed, stale typed links are corrected, and tests prevent
root-planning duplication from returning. Unresolved decisions remain in their
open typed records rather than being presented as accepted authority.

## References

- [Documentation Authority Taxonomy](../adr/documentation-authority-taxonomy.md)

### Governing ADR Paths

- `docs/technical/adr/documentation-authority-taxonomy.md`
