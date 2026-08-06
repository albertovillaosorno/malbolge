# Repository responsibility scaffold

## Status

Accepted implementation

## Purpose

Define the repository topology by semantic responsibility rather than
implementation language, build system, or target hardware.

## Scope

This contract governs:

- `src/`
- `tests/`
- `benchmarks/`
- `tools/`
- `docs/`
- `Cargo.toml`
- `.jig/taxonomy.json`
- all `src/<domain>/<function>/function.yml` manifests

## Current Behavior

### Source domains

The root `src/` surface contains only its `README.md` catalog, its governed
sidecar, and ten semantic domains:

- `automation/`
- `examples/`
- `interface/`
- `interoperability/`
- `optimization/`
- `performance/`
- `research/`
- `runtime/`
- `specification/`
- `tooling/`

Each domain owns a catalog and sidecar. Every directory immediately below a
domain is a governed function with one `function.yml` manifest. Functions own
architecture kinds such as domain, application, ports, adapters, composition,
contracts, and mathematics.

### Mixed-language ownership

Languages remain implementation details within functions. The virtual-machine
function, for example, owns Rust domain/application code and its independent C
adapter under one semantic boundary. Root language buckets such as `src/rust/`,
`src/c/`, `src/cpp/`, `src/cuda/`, or `src/python/` are forbidden.

### Cargo composition

Cargo entrypoints are explicit paths inside governed functions. Root
`src/lib.rs` and `src/main.rs` do not exist. Cargo remains build composition
rather than a repository ownership model.

### Repository-wide surfaces

`tests/`, `benchmarks/`, and `tools/` contain repository-wide composition and
evidence that cannot be owned by one implementation function. Documentation is
partitioned by its technical, research, legal, bibliography, and typed-planning
authorities.

### Implementation status

The scaffold is implemented. Source domains, function manifests, language
manifests, taxonomy, sidecars, tests, and Cargo paths provide deterministic
machine-readable ownership evidence.

## Invariants

- Semantic responsibility determines ownership.
- Every second-level source function has exactly one governed manifest.
- Mixed implementation languages may coexist inside one function.
- Language-only source roots and unowned implementation parts are rejected.
- Cargo paths stay inside governed functions.
- Speculative empty source directories are rejected.
- Changes to the accepted domain set require reviewed authority, documentation,
  manifest, and test updates in one change.

## Failure Behavior

Missing catalogs, sidecars, function manifests, ownership metadata, or Cargo
paths outside a governed function fail validation. An undocumented new root does
not acquire ownership merely because a build tool can discover it.

## Verification

- `tests/test_repository_scaffold.py` validates the exact domain catalog,
  function-manifest coverage, mixed-language evidence, Cargo composition, and
  forbidden or empty roots.
- Jig validates every governed function, part, graph edge, sidecar, and language
  manifest against `.jig/taxonomy.json` and `.jig/layout/definitions.json`.
- `jig validate --root .` is the repository-wide acceptance gate.

## References

- [Repository responsibility boundaries][responsibility-boundaries]
- [Source catalog](../../../src/README.md)
- [Repository handoff](../../../AGENTS.md)

[responsibility-boundaries]: ../adr/repository-responsibility-boundaries.md
