# Planning corpus promotion to durable documentation

- Status: Proposed
- Planning identity: `planning-corpus-promotion-to-durable-documentation`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Documentation Authority Taxonomy](../adr/documentation-authority-taxonomy.md)

## Purpose

Once ROADMAP and typed TODO coverage are stable, classify every settled planning
choice into its durable owning surface instead of copying TODO prose wholesale.
Create bounded ADRs for decisions, technical specifications/contracts for
repository behavior, research records and `.tex` artifacts for investigations,
legal records for dated source-use/interoperability analysis, and bibliography
records for external evidence. Populate each TODO's `contract` and `adr_paths`
with real authorities as those records are created. Proposed or unresolved
choices remain visibly proposed; implementation details remain in their owning
technical documents. No global catch-all ADR, duplicate authority, or
chat-history archive is created during promotion.

## Proposed Model

This record defines the contract that implementation must satisfy for
`planning-corpus-promotion-to-durable-documentation`. The implementation may
change internal representation or language choices without changing the
observable behavior, trust boundary, or ownership rules stated by its governing
decisions.

## Invariants

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

## Failure Behavior

Missing or competing authority blocks promotion rather than creating a duplicate
or placeholder decision.

## Verification

- Expected durable artifact surface: the four documentation families plus
  updated `contract`/`adr_paths` metadata across the active TODO registry.
- Evidence must include a complete mapping from active roadmap/TODO intent to
  owning durable documentation or an explicit unresolved decision record.

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
