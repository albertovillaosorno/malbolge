# Jig repository governance

## Status

Active; validation is blocked only by the reviewed pytest configuration.

## Intent

Integrate the evolving Jig validator as repository-local tooling, preserve its
fail-closed rules, and configure only genuine project-specific differences
without weakening unrelated linter contracts.

## Contract

### Proposed Model

This record defines the contract that implementation must satisfy for
`jig-repository-governance`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

### Invariants

- The repository-local Jig installation and `jig.toml` describe the actual
  polyglot repository without fake language/tool requirements or weakened
  reviewed lint policy.
- The authoritative rule/specification is deterministic, versionable, and does
  not depend on undocumented host behavior.

## Evidence Boundary

- Repository-local Jig 26.3.1 is installed under `.dependencies/jig/bin/` and
  executes from the repository-local source-linked authority.
- Current `jig check` and `jig validate` runs report only `JIG-LINT-001`
  and `JIG-LINT-005` for `pytest.ini`; documentation, TODO, ADR, header,
  taxonomy, commit-history, and architecture diagnostics are otherwise clean.
- The remaining failure is not waived here. The pytest configuration owner must
  reconcile the reviewed addopts/plugin contract before this TODO can close.
- Prerequisite completion evidence: `repository-responsibility-scaffold`.

## Diagnostics

Missing authority or contradictory configuration fails closed rather than
selecting an implicit repository policy.

## Examples

- No normative example is required at this planning stage unless the contract
  states one.

## Implementation

The repository-local launcher and `jig.toml` are installed and executable. The
contract remains incomplete only because current pytest configuration does not
yet satisfy its reviewed linter authority.

## References

- [Documentation Authority Taxonomy](../adr/documentation-authority-taxonomy.md)

### Governing ADR Paths

- `docs/technical/adr/documentation-authority-taxonomy.md`
