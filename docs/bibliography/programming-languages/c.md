# C Programming Language

- Review status: Verified
- Evidence status: Verified
- As-of date: 2026-07-26

## Identity

- Canonical name: ISO/IEC 9899:2024, Programming languages - C
- Subject class: Programming language standard
- Stable identifier: ISO/IEC 9899:2024
- Publisher or authority: ISO/IEC JTC 1/SC 22/WG 14

## Repository Relevance

C is the primary human-authored application language and the intended language
for the portable self-hostable compiler implementation. The project defines a
narrow deterministic C profile rather than treating every conforming C program
as lowerable to Malbolge.

## Source Quality And Provenance

ISO identifies ISO/IEC 9899:2024 as Edition 5 of the international C standard.
Its official abstract states that the document specifies program representation,
syntax, constraints, semantic interpretation, input/output representation, and
conforming-implementation limits.

## Verified Claims

- ISO/IEC 9899:2024 is a published C language standard.
- It specifies syntax, constraints, semantic interpretation, and implementation
  restrictions for C programs.
- The Malbolge project still needs a narrower deterministic profile for its
  lowering contract.

## Unresolved Evidence

The exact C feature subset accepted by `malbolge-tidy` is a repository contract,
not something the ISO standard defines.

## Sources

- <https://www.iso.org/standard/82075.html> - accessed 2026-07-26.
