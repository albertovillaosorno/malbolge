# Documentation Authority Taxonomy

## Status

Accepted.

## Decision ID

`jig.malbolge.technical.documentation-authority-taxonomy`

## Context

The repository needs durable technical specifications, research records, legal
analysis, source provenance, mathematical contracts, and typed unfinished work.
A global ADR tree scales poorly because unrelated domains compete for one
namespace, while permissive documentation layouts allow duplicate catalogs and
ambiguous ownership to accumulate.

The repository also needs a shape that Jig can validate mechanically without
requiring Malbolge to implement a second documentation linter.

## Decision

Documentation is organized by authority family before subject taxonomy. Exactly
four authoritative families live under `docs/`:

- `docs/technical/`;
- `docs/research/`;
- `docs/legal/`; and
- `docs/bibliography/`.

Each family owns a local `adr/` directory. A global `docs/adr/` directory is not
permitted. `docs/todo/` is typed governance state, not a fifth authority family.
Validation integration data such as CSpell dictionaries lives under
`integrations/`, and machine-governed `.tex` specifications live under `math/`.

### Closed First-Level Categories

Technical documentation may use:

- `architecture`;
- `compatibility`;
- `compiler`;
- `contracts`;
- `examples`;
- `generated`;
- `integrations`;
- `interoperability`;
- `runtime`;
- `specification`;
- `tooling`; and
- `verification`.

Research documentation may use:

- `algorithms`;
- `experiments`;
- `methodology`;
- `papers`; and
- `studies`.

Legal documentation may use:

- `authorities`;
- `cases`;
- `contracts`;
- `doctrines`;
- `interoperability`;
- `jurisdictions`;
- `licenses`;
- `platforms`;
- `repository`; and
- `statutes`.

Bibliography documentation may use:

- `languages`;
- `legal-and-regulatory`;
- `libraries`;
- `organizations-and-projects`;
- `platforms-and-runtimes`;
- `provenance-and-methodology`;
- `publications`;
- `specifications-and-standards`; and
- `tooling`.

### Catalog Contract

Every family and nested documentation directory uses `README.md` as its catalog.
A second `index.md` catalog is not maintained. Catalog H2 sections are exactly:

1. `Purpose`; 2. `Owns`; 3. `Does Not Own`; and 4. `Contents`.

### Record Schemas

Family records are Markdown-only. ADRs use the exact H2 sequence:

1. `Status`; 2. `Decision ID`; 3. `Context`; 4. `Decision`; 5. `Advantages`; 6.
   `Disadvantages`; 7. `Consequences`; 8. `Rejected Alternatives`; and 9.
   `Evidence`.

Ordinary technical records use `Status`, `Purpose`, `Scope`, `Current Behavior`,
`Invariants`, `Failure Behavior`, `Verification`, and `References`. Technical
contracts use `Status`, `Intent`, `Contract`, `Evidence Boundary`,
`Diagnostics`, `Examples`, `Implementation`, and `References`.

Research, legal, and bibliography records use their family-specific schemas
recorded by Jig and mirrored by the current repository templates. A schema
change is a governance migration and must update both the validator and these
accepted authorities together.

### Planning And Mathematical Authority

Active typed work lives under `docs/todo/open/<area>/<id>.mdc`. Completed work
moves to `docs/todo/completed/<area>/<id>.mdc` only after its durable evidence
is accepted and its exact heading leaves `TODO.md`.

Human explanations of mathematics remain in the appropriate documentation
family. Machine-governed mathematical sources live under `math/specification/`
or `math/algorithms/`. A `.tex` specification defines mathematics; it does not
by itself prove that an implementation satisfies the mathematics.

## Advantages

- Every durable proposition has one visible authority owner.
- ADRs remain close to the documentation family they govern.
- Catalog and record shapes are deterministic enough for fail-closed validation.
- Research prose, executable experiments, and mathematical contracts remain
  distinct without being separated by implementation language.
- TODO lifecycle state and CSpell data no longer masquerade as documentation
  authority.

## Disadvantages

- Exact taxonomy makes structural changes explicit migrations rather than cheap
  ad hoc folder creation.
- New documentation categories require an accepted governance change instead of
  appearing opportunistically.
- Strict schemas require editorial work when old documents are promoted.

## Consequences

- Readers navigate by authority family and then by responsibility.
- Every nested documentation directory has one `README.md` catalog.
- `index.md` is not used as a competing catalog convention.
- `.jig/cspell/` is validation integration data outside `docs/`.
- `.tex` artifacts are kept under `math/`, outside Markdown-only documentation
  families.
- Jig may validate this topology directly instead of Malbolge owning a duplicate
  validator.

## Rejected Alternatives

### Global ADR Repository

A single `docs/adr/` tree was rejected because it becomes a monolithic taxonomy
spanning unrelated knowledge owners.

### Research-Owned Bibliography

Bibliography was not nested under research because technical and legal records
consume the same external evidence.

### Documentation-Owned Mathematical Sources

Keeping `.tex` under `docs/` was rejected once documentation became
Markdown-only. Mathematical contracts are machine-governed artifacts with a
separate correspondence obligation.

### Duplicate README And Index Catalogs

Maintaining both `README.md` and `index.md` was rejected because two catalogs
can drift while appearing equally authoritative.

## Evidence

- The four documentation-family catalogs exist at `docs/technical/README.md`,
  `docs/research/README.md`, `docs/legal/README.md`, and
  `docs/bibliography/README.md`; every current nested documentation directory
  outside typed TODO state has a `README.md`, with no competing `index.md`.
- Each authoritative family has a local `adr/`; no global `docs/adr/` exists.
  CSpell data remains under `.jig/cspell/`, and no `.tex` source lives
  under the Markdown-only documentation families.
- A local topology comparison on 2026-07-27 shows Jig using the selected
  family-local model: `bibliography`, `legal`, `research`, and `technical` each
  own `adr/`, with no global `docs/adr/`. SHAR separates bibliography, legal,
  and technical documentation but retains a global `docs/adr`, demonstrating the
  useful family split while retaining the centralized decision namespace this
  ADR rejects.
- The current STM checkout has no `docs/` tree, so it is not presented as
  current positive topology evidence. The earlier STM-style global-ADR pattern
  remains only a design antecedent for the rejected monolithic alternative; this
  record does not infer historical files that are absent from the checkout.
- `docs/todo/open/`, `.jig/cspell/`, and
  `src/specification/formal-model/README.md` demonstrate the
  explicit non-family governance, editorial-data, and mathematical boundaries.
