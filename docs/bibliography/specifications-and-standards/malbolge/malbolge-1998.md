# Original Malbolge Language And Interpreter

## Status

Verified; evidence verified.

## Subject

- Canonical name: Malbolge 1998 specification and reference interpreter
- Subject class: Historical language specification and implementation
- Stable identifier: Ben Olmstead, 1998 Malbolge
- Publisher or authority: Ben Olmstead; canonical web copies hosted by Lou
  Scheffer

## Repository Use

These sources define the historical language specification and identify the
untouched interpreter retained under
`src/interoperability/historical-malbolge/adapter-outbound/main.c`. The
repository
treats specification/interpreter disagreements as explicit implementation
defects.

## Provenance

The canonical specification identifies Ben Olmstead and 1998 and explicitly
relinquishes copyright in the language, documentation, and interpreter. The
interpreter page presents itself as the original interpreter and contains the
same public-domain dedication in the source header.

The repository treats the specification and interpreter as historical primary
sources. Later commentary may help explain them but cannot silently override the
recorded machine behavior.

## Identity And Version

- Canonical name: Malbolge 1998 specification and reference interpreter
- Subject class: Historical language specification and implementation
- Stable identifier: Ben Olmstead, 1998 Malbolge
- Publisher or authority: Ben Olmstead; canonical web copies hosted by Lou
  Scheffer

## License Or Terms

This is external material. Citation does not relicense the source or import its
terms into the repository MIT license.

## Evidence

### Verified

- Words are ten trits and range from 0 through 59048.
- Historical memory contains exactly 59049 words.
- The machine uses A, C, and D registers with shared code/data memory.
- Loading ignores whitespace and fills remaining memory using the crazy
  operation.
- Executed instructions are decoded using position-dependent translation and
  then the executed cell is self-encrypted.
- The language, documentation, and interpreter were dedicated to the public
  domain by the author.

### Unresolved

The historical C implementation contains implementation assumptions and defects
that are not automatically normative language semantics. Those are cataloged by
separate repository work.

## Sources

- <https://www.lscheffer.com/malbolge_spec.html> - accessed 2026-07-26.
- <https://www.lscheffer.com/malbolge_interp.html> - accessed 2026-07-26.
