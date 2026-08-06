# Bibliography completion

## Status

Accepted and implemented

## Intent

Finish the repository-wide external-source catalog without inventing sources,
duplicating identities, or turning bibliography records into policy.

## Contract

### Coverage model

The accepted bibliography taxonomy remains unchanged. Completion adds the source
records and coverage evidence required by actual technical, research, legal,
interoperability, toolchain, dependency, and publication claims.

One external source identity has one canonical record. Several repository
documents may cite that record, but they must not copy competing version,
provenance, or licensing metadata.

### Source quality

Material claims prefer primary or authoritative sources. Every record preserves
stable identity, version or publication metadata when applicable, retrieval or
review date, repository relevance, verified claims, source links, and explicit
uncertainty.

### Honest completeness

Closed taxonomy categories are not padded. An empty category is valid when the
repository has no relevant dependency or cited authority. A category becomes
incomplete only when repository content relies on an uncataloged source.

### Coverage audit

A deterministic coverage ledger maps material external claims and declared
third-party dependencies to canonical records. The audit reports uncataloged
claims, duplicate identities, stale version pins, broken local citations, and
missing provenance without fetching the network during ordinary validation.

## Evidence Boundary

Durable evidence consists of canonical Markdown source records, category
catalogs, the coverage ledger, the bibliography validator, tests, and links from
owning technical, research, and legal documents.

The bibliography records source identity and provenance. It does not decide
repository policy, legal permission, implementation correctness, or experimental
truth.

## Diagnostics

Missing records, duplicate canonical identities, malformed source sections,
missing dates, absent uncertainty, broken local citation targets, stale required
coverage, and fabricated filler fail validation.

## Examples

A compiler document that relies on an LLVM release cites one canonical LLVM
record with the exact version and authoritative documentation. A second document
reuses that record rather than creating another LLVM identity.

An unused library category may remain empty. Adding a placeholder record merely
to increase the record count is invalid.

## Implementation

Complete. The bibliography contains 47 source/provenance records, including 44
required baseline records. The validator checks record shape, dated uncertainty,
unique stable identities, exact Python dependency pins, and 17 distinct durable
external references discovered across source, manifests, technical documents,
completed lifecycle evidence, generated text artifacts, and Jig configuration.

Open TODO records and synthetic tests are excluded from durable-reference
coverage because they are planning state and negative fixtures rather than
implemented authority. New durable URLs, dependency-pin drift, duplicate stable
identifiers, malformed records, and missing baseline identities fail closed.

## References

- [Bibliography taxonomy ADR][taxonomy]
- [Bibliography catalog](../../bibliography/README.md)
- [Bibliography provenance template][template]

[taxonomy]: ../../bibliography/adr/source-taxonomy-and-citation-provenance.md
[template]: ../../bibliography/provenance-and-methodology/template.md
