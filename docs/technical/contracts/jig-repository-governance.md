# Jig repository governance

## Status

Active; schema 8 is adopted and full repository validation remains open.

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
- The active source-linked Jig requires configuration schema 8. Malbolge declares
  its typed TODO document, lifecycle roots, record shape, acceptance requirements,
  validation-command requirement, strict dependency-lane policy, and all six
  closed change-class path policies explicitly.
- Git governance declares `JIG_SHIT.md` as required local-only evidence and
  binds that policy to the tracked root `.gitignore`; the ledger may exist
  locally but must not become governed source.
- The canonical validation command is
  `.dependencies/jig/bin/jig.cmd validate --root .`. It builds and runs the
  source-linked authority; the versioned release executable is not the active
  schema-8 validator.
- Commit-message validation accepts compliant new commits with this
  configuration.
- The source-linked validator parses schema 8 and reaches exhaustive policy
  evaluation. Full validation remains fail-closed on inherited history-wide
  commit-policy findings, including obsolete scopes and missing commit bodies.
- Prerequisite completion evidence: `repository-responsibility-scaffold`.

## Diagnostics

Missing authority or contradictory configuration fails closed rather than
selecting an implicit repository policy.

## Examples

- No normative example is required at this planning stage unless the contract
  states one.

## Implementation

The schema-8 `jig.toml` and installed commit-message hook accept the declared
TODO workflow. The source-linked validator builds and reaches exhaustive policy
evaluation. Completion still requires an explicit resolution for inherited
history findings and a clean full-repository result without waived diagnostics.

## References

- [Documentation Authority Taxonomy](../adr/documentation-authority-taxonomy.md)

### Governing ADR Paths

- `docs/technical/adr/documentation-authority-taxonomy.md`
