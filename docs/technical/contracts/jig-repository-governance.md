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
- Historical message repair plan
  `5f7e10afc710f9c47093d68f853d26657f8854aa` normalized 32 messages across
  208 linear unsigned commits. Every tree, author/committer identity, timestamp,
  and chronological position remained unchanged.
- The repaired history has zero `JIG-COMMIT-*` diagnostics. Full validation
  remains fail-closed only on current repository findings outside commit
  history.
- Prerequisite completion evidence: `repository-responsibility-scaffold`.

## Diagnostics

Missing authority or contradictory configuration fails closed rather than
selecting an implicit repository policy.

## Examples

- No normative example is required at this planning stage unless the contract
  states one.

## Implementation

The schema-8 `jig.toml` and installed commit-message hook accept the declared
TODO workflow. Jig repaired historical messages transactionally from
`b7686ed1ba2e6369eac124046158fb65ac667747` to
`b88e219e8a14dadfe2a4bd8255cb49f1d4ea87c8`; the original tip remains at
`refs/jig/repair/backups/5f7e10afc710f9c47093d68f853d26657f8854aa`.
Completion still requires a clean full-repository result for current findings.

## References

- [Documentation Authority Taxonomy](../adr/documentation-authority-taxonomy.md)

### Governing ADR Paths

- `docs/technical/adr/documentation-authority-taxonomy.md`
