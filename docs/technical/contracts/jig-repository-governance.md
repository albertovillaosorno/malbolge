# Jig repository governance

- Status: Proposed
- Planning identity: `jig-repository-governance`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Documentation Authority Taxonomy](../adr/documentation-authority-taxonomy.md)

## Purpose

Integrate the evolving Jig validator as repository-local tooling, preserve its
fail-closed rules, and configure only genuine project-specific differences
without weakening unrelated linter contracts.

## Proposed Model

This record defines the contract that implementation must satisfy for
`jig-repository-governance`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- The repository-local Jig installation and `jig.toml` describe the actual
  polyglot repository without fake language/tool requirements or weakened
  reviewed lint policy.
- The authoritative rule/specification is deterministic, versionable, and does
  not depend on undocumented host behavior.

## Failure Behavior

Missing authority or contradictory configuration fails closed rather than
selecting an implicit repository policy.

## Verification

- Expected durable artifact surface: `jig.toml`, `.dependencies/`, `todo/`,
  `TODO.md`.
- Required evidence: reviewed authority text plus deterministic
  parser/schema/governance tests for the declared boundary.

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
