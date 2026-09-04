# Jig repository governance

## Status

Accepted; schema 21 with modular settings is adopted.

## Intent

Use the standalone Jig validator installed on the host `PATH`, preserve its
fail-closed rules, and configure only genuine project-specific differences
without weakening unrelated linter contracts.

## Contract

### Proposed Model

This record defines the contract that implementation must satisfy for
`jig-repository-governance`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

### Invariants

- The standalone Jig identity, `.jig/jig.toml` bootstrap, and modular
  `.jig/settings/` documents describe the actual polyglot repository without
  fake language/tool requirements or weakened reviewed lint policy.
- The authoritative rule/specification is deterministic, versionable, and does
  not depend on undocumented host behavior.

## Evidence Boundary

- Jig 26.3.0 resolves from `PATH`, uses configuration schema 21, and reads
  repository policy from the schema-1 modular `.jig/settings/` generation.
- `.jig/settings/repository.toml` explicitly disables source-mirrored test
  layout because root `tests/` is accepted repository-wide evidence rather than
  implementation owned by exactly one source function.
- Malbolge declares its typed TODO document, lifecycle roots, record shape,
  acceptance requirements, validation-command requirement, strict dependency
  lanes, `p0` through `p5` priority order, and all six closed change-class path
  policies explicitly.
- Git governance declares `JIG_SHIT.md` as required local-only evidence and
  binds that policy to the tracked root `.gitignore`; the ledger may exist
  locally but must not become governed source.
- The canonical validation command is `jig validate --root .`.
- The generated TODO and roadmap are projections of typed records and
  `.jig/roadmap.json`, respectively.
- Commit-message validation accepts compliant new commits with this
  configuration.
- `tests/test_governance_paths.py` rejects authored path references that enter a
  second `.jig` root, preventing silent duplicated-segment tool paths outside
  Jig's own configuration tree.
- Historical message repair plan
  `5f7e10afc710f9c47093d68f853d26657f8854aa` normalized 32 messages across
  208 linear unsigned commits. Every tree, author/committer identity, timestamp,
  and chronological position remained unchanged.
- The repaired history has zero `JIG-COMMIT-*` diagnostics.
- Prerequisite completion evidence: `repository-responsibility-scaffold`.

## Diagnostics

Missing authority or contradictory configuration fails closed rather than
selecting an implicit repository policy.

## Examples

- No normative example is required at this planning stage unless the contract
  states one.

## Implementation

The schema-21 `.jig/jig.toml` is a pinned bootstrap for the modular
`.jig/settings/` generation, and the PATH-delegating commit-message hook accepts
the declared TODO workflow. Jig repaired historical messages transactionally
from
`b7686ed1ba2e6369eac124046158fb65ac667747` to
`b88e219e8a14dadfe2a4bd8255cb49f1d4ea87c8`; the original tip remains at
`refs/jig/repair/backups/5f7e10afc710f9c47093d68f853d26657f8854aa`.
Later Jig upgrades remain explicit schema and dependency maintenance rather
than an implicit source-link refresh.

## References

- [Documentation Authority Taxonomy](../adr/documentation-authority-taxonomy.md)

### Governing ADR Paths

- `docs/technical/adr/documentation-authority-taxonomy.md`
