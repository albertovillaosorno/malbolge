# Documentation readiness and implementation gate

## Status

Proposed

## Intent

Establish the documentation baseline that must pass before normal product
implementation history begins. The gate requires the four documentation families
and their local ADR roots, a usable repository bibliography baseline, all
existing TODO decisions routed to an owning durable document or an explicitly
unresolved record, valid local links, and no accidental global `docs/adr/`.
`.jig/cspell/` remains intact as validation integration data.
Scaffolding, configuration, and concurrent Jig development may exist before this
gate, but new product implementation work starts only after the documentation
baseline is reviewable. Documentation and planning commits may precede this
gate. Passing it authorizes product implementation commits; subsequent
implementation proceeds TODO by TODO with its governing documents already
available.

## Contract

### Proposed Model

This record defines the contract that implementation must satisfy for
`documentation-readiness-and-implementation-gate`. The implementation may change
internal representation or language choices without changing the observable
behavior, trust boundary, or ownership rules stated by its governing decisions.

### Invariants

- The four documentation families and their local ADR roots are present,
  correctly owned, and free of an accidental global `docs/adr/` authority.
- Every family and nested documentation directory has one `README.md` catalog,
  and no competing `index.md` catalog is maintained.
- Family records are Markdown-only; machine-governed `.tex` specifications live
  under `math/` instead of the documentation families.
- The repository bibliography baseline is sufficient to support all sources
  cited by the initial promoted documentation.
- Every active TODO decision is routed to a real durable authority or an
  explicit unresolved/proposed record, with valid local links and no fake
  completion claims.
- `.jig/cspell/` remains validation integration data and is not
  reclassified as a documentation authority family.
- Product implementation work has not been used to bypass missing documentation
  authority; scaffolding/configuration and concurrent Jig work are allowed
  before this gate.

## Evidence Boundary

- Expected durable evidence: reviewed documentation tree, bibliography coverage
  catalog/coverage report, TODO-to-authority mapping, link/path audit, and clean
  planning-registry audit.
- Prerequisite completion evidence:
  `planning-corpus-promotion-to-durable-documentation` and
  `repository-bibliography-taxonomy-and-citation-provenance`.
- Documentation/bootstrap commits may precede this gate; product implementation
  commits require this gate to be accepted.

## Diagnostics

Missing or competing authority blocks promotion rather than creating a duplicate
or placeholder decision.

## Examples

- No normative example is required at this planning stage unless the contract
  states one.

## Implementation

Not implemented. This proposed contract does not claim executable support yet.

## References

- [Documentation Authority Taxonomy](../adr/documentation-authority-taxonomy.md)

### Governing ADR Paths

- `docs/technical/adr/documentation-authority-taxonomy.md`
