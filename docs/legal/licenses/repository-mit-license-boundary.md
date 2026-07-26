# Repository MIT License Boundary

- Status: Repository boundary accepted
- As-of date: 2026-07-26
- Counsel review: Not performed

## Question Presented

What material does the repository represent as MIT licensed?

## Verified Baseline

The root `LICENSE` contains the MIT License with copyright notice for Alberto
Villa Osorno, 2026.

## Repository Boundary

Repository-authored code, documentation, tests, research artifacts, and tooling
are MIT licensed unless an owning file or legal record states another boundary.

Third-party material does not become MIT merely because repository tooling reads,
transforms, compiles, verifies, or emits an artifact derived from that material.
The historical Malbolge interpreter keeps its own public-domain dedication.
User-supplied source retains its own applicable provenance and terms.

## Not Established

This record does not decide the license status of every possible generated
artifact. Output licensing can depend on the inputs, incorporated material, and
applicable upstream terms.

## Required Facts Or Authorities

Generated or transformed third-party material requires source-specific review
before the repository makes a public licensing representation about that output.

## Sources

- `LICENSE`
- [Ben Olmstead public-domain boundary](ben-olmstead-malbolge-public-domain.md)

## Review Boundary

Re-review before changing the project license, introducing vendored third-party
code, or publishing generated third-party transformations as repository-owned
artifacts.
