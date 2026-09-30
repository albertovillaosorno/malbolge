# Ben Olmstead Malbolge Public-Domain Boundary

## Status

Evidence recorded; repository boundary accepted

## As-of Date

2026-09-29

## Question Presented

How does the repository distinguish Ben Olmstead's historical Malbolge material
from project-authored Apache-2.0 material?

## Verified Baseline

The original Malbolge specification states that Ben Olmstead relinquished
copyright in the language, documentation, and interpreter and identifies
Malbolge as public domain. The original interpreter source separately contains a
public-domain dedication in its header.

The source evidence is cataloged in
`docs/bibliography/specifications-and-standards/malbolge/malbolge-1998.md`.

## Not Established

This record does not attempt to assign a modern SPDX identifier to Ben
Olmstead's custom public-domain dedication, and it does not claim that public
domain is equivalent to the Apache License 2.0.

## Required Facts

Any future redistribution package that changes how the historical file is
bundled must preserve the file's original notice and re-review the package
boundary.

## Authorities

- Canonical external authorities are referenced through `docs/bibliography/`
  where available.

## Analysis

`src/interoperability/historical-malbolge/adapter-outbound/main.c` is retained
as historical primary implementation
evidence and is not relicensed under the repository Apache-2.0 license. The
repository
may add project-authored wrappers, tests, documentation, and replacement
implementations under Apache-2.0 without rewriting the historical source notice.

The root `LICENSE-APACHE-2.0` applies to repository-authored material unless a
file or record states a different applicable boundary.

Re-review if the historical file is replaced, modified, vendored from a
different source, or included in a distribution with materially different
license metadata.

## Conclusion Boundary

This record is bounded repository research and is not legal advice.

## Sources

- `docs/bibliography/specifications-and-standards/malbolge/malbolge-1998.md`
- `src/interoperability/historical-malbolge/adapter-outbound/main.c`
- `LICENSE-APACHE-2.0`
