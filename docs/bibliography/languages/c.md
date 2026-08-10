# C Programming Language

## Status

Verified; evidence verified.

## Subject

- Canonical name: ISO/IEC 9899:2024, Programming languages - C
- Subject class: Programming language standard
- Stable identifier: ISO/IEC 9899:2024
- Publisher or authority: ISO/IEC JTC 1/SC 22/WG 14

## Repository Use

C is the primary human-authored application language and the intended language
for the portable self-hostable compiler implementation. The project defines a
narrow deterministic C profile rather than treating every conforming C program
as lowerable to Malbolge.

## Provenance

ISO identifies ISO/IEC 9899:2024 as Edition 5 of the international C standard.
Its official abstract states that the document specifies program representation,
syntax, constraints, semantic interpretation, input/output representation, and
conforming-implementation limits.

## Identity And Version

- Canonical name: ISO/IEC 9899:2024, Programming languages - C
- Subject class: Programming language standard
- Stable identifier: ISO/IEC 9899:2024
- Publisher or authority: ISO/IEC JTC 1/SC 22/WG 14

## License Or Terms

This is external material. Citation does not relicense the source or import its
terms into the repository MIT license.

## Evidence

### Verified

- ISO/IEC 9899:2024 is a published C language standard.
- It specifies syntax, constraints, semantic interpretation, and implementation
  restrictions for C programs.
- The Malbolge project still needs a narrower deterministic profile for its
  lowering contract.
- WG14 C23 issue 1040 remains open and records unresolved freestanding-library
  wording, including the apparent omission of `<stdckdint.h>` from one header
  list.
- WG14 DR 329 records that `fabs`, `ceil`, `floor`, and `trunc` return exact
  results independent of the current rounding direction in the IEC 60559
  binding, while `sqrt` is rounding-direction dependent and transcendental
  functions may require stronger inexact-result treatment.
- WG14 N3220 specifies the C23 formatted-output grammar and bounded
  `snprintf`/`vsnprintf` semantics, including the would-have-written result
  when the destination truncates output.
- The C formatted-output contract leaves `%p` pointer text
  implementation-defined, so the guest runtime may select and document a stable
  representation instead of inheriting host pointer spelling.

### Unresolved

The exact C feature and library subset accepted by `tools/tidy` is a repository
contract, not something the ISO standard defines. Open WG14 issue 1040 is one
reason the guest library surface is independently versioned.

## Sources

- <https://www.iso.org/standard/82075.html> - accessed 2026-07-26.
- <https://www9.open-std.org/JTC1/SC22/WG14/issues/c23/log.html> - accessed
  2026-08-08.
- <https://www.open-std.org/jtc1/sc22/wg14/www/docs/dr_329.htm> - accessed
  2026-08-09.
- <https://www.open-std.org/jtc1/sc22/wg14/www/docs/n3220.pdf> - accessed
  2026-08-09.
