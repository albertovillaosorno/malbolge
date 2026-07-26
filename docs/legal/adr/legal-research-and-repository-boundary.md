# Legal Research And Repository Boundary

## Status

Accepted.

## Context

The repository includes an original public-domain interpreter, project-authored
MIT material, optional user-supplied third-party source such as DOOM, and future
generated artifacts. Engineering intent alone cannot determine ownership,
license effect, distribution rights, or jurisdiction-specific legal outcomes.

Legal documentation therefore needs a durable authority boundary without making
every legal source summary an ADR.

## Decision

`docs/legal/` owns dated legal and source-use research plus repository legal
boundaries. Legal ADRs record repository decisions about how such evidence is
handled; authority summaries and fact-specific analyses remain ordinary legal
records.

Legal records distinguish verified external facts, repository policy, missing
facts, and unresolved interpretation. They do not present themselves as legal
advice and do not infer permission from public availability, interoperability
intent, successful compilation, or a permissive license on unrelated material.

Canonical external source identity belongs in `docs/bibliography/` and is cited
from legal records rather than duplicated.

## Alternatives Considered

### Put all legal content in ADRs

Rejected because case law, licenses, and dated source-use research are evidence,
not repository architecture decisions.

### Put legal analysis in bibliography records

Rejected because bibliography records own source/provenance facts and are
non-governing; they should not become repositories for legal application
analysis.

## Consequences

- The public-domain oracle, MIT project code, user-supplied inputs, and generated
  outputs can have explicit independent boundaries.
- Unresolved legal facts remain visible instead of becoming favorable
  assumptions.
- Repository decisions can cite legal research without pretending an ADR is
  external legal authority.

## Implementation Notes

Consequential legal conclusions remain subject to qualified counsel. Records
must include an as-of date and identify when re-review is required.
