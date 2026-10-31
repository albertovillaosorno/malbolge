# Bibliography

## Purpose

Catalog external evidence and source provenance.

## Owns

Source identity, versions, terms, provenance, and verified source claims.

## Does Not Own

Repository policy, legal conclusions, or research conclusions.

## Contents

- `adr/`
- `languages/`
- `legal-and-regulatory/`
- `libraries/`
- `organizations-and-projects/`
- `platforms-and-runtimes/`
- `provenance-and-methodology/`
- `publications/`
- `specifications-and-standards/`
- `tooling/`
- `disclaimer.md`
- `provenance-and-methodology/template.md`

## Validation boundary

Bibliography source records, validation dependency evidence, and durable
references are decoded from bounded regular-file descriptors (at most 16 MiB
per file). The validator checks file identity and timestamps before and after
reads, rejects redirected source leaves and inspected directory aliases, and
requires valid UTF-8. A filesystem mutation during validation fails closed
rather than accepting a replacement source record or outside URL.
