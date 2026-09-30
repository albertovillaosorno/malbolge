# Repository Apache-2.0 License Boundary

## Status

Repository boundary accepted

## As-of Date

2026-09-29

## Question Presented

What material does the repository represent as Apache-2.0 licensed?

## Verified Baseline

The root `LICENSE-APACHE-2.0` contains the Apache License, Version 2.0.
Repository-authored files retain their 2026 Alberto Villa Osorno copyright
notices.

## Not Established

This record does not decide the license status of every possible generated
artifact. Output licensing can depend on the inputs, incorporated material, and
applicable upstream terms.

## Required Facts

Generated or transformed third-party material requires source-specific review
before the repository makes a public licensing representation about that output.

## Authorities

- Canonical external authorities are referenced through `docs/bibliography/`
  where available.

## Analysis

Repository-authored code, documentation, tests, research artifacts, and tooling
are Apache-2.0 licensed unless an owning file or legal record states another
boundary.

Third-party material does not become Apache-2.0 merely because repository
tooling
reads, transforms, compiles, verifies, or emits an artifact derived from that
material. The historical Malbolge interpreter keeps its own public-domain
dedication. User-supplied source retains its own applicable provenance and
terms.

Prior repository revisions published under MIT remain available under their
then-applicable terms; this record governs the current tree. Re-review before
changing the project license again, introducing vendored third-party code,
or publishing generated third-party transformations as repository-owned
artifacts.

## Conclusion Boundary

This record is bounded repository research and is not legal advice.

## Sources

- `LICENSE-APACHE-2.0`
- [Ben Olmstead public-domain boundary](ben-olmstead-malbolge-public-domain.md)
