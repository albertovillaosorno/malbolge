# Malbolge TextMate grammar

> **Status: WIP.**
>
> The grammar can be developed independently, but the Linguist package remains
> blocked on a functional `c2malbolge` and a real compiler-produced sample.

This directory stages the TextMate-compatible grammar intended for a future
GitHub Linguist contribution.

## Scope

The grammar exports exactly one TextMate scope:

```text
source.malbolge
```

No filename extension is hard-coded here. The final extension or filename
mapping belongs to Linguist's `languages.yml` entry and should be decided at
submission time.

## Semantic basis

The grammar follows the source-admission boundary implemented by the canonical
Rust VM and documented by the interpreter-authority Malbolge contract.

The current Rust loader accepts these source-representation classes:

- C-locale ASCII whitespace bytes `0x09`, `0x0A`, `0x0B`, `0x0C`, `0x0D`,
  and `0x20`;
- graphical ASCII source units `0x21..0x7E`;
- every other byte is rejected as source representation.

The VM then performs position-dependent instruction admission. For the `i`th
non-whitespace source byte:

```text
xlat1[(source_byte - 33 + i) mod 94]
```

The result must decode to one of the eight classic instructions:

```text
j i * p < / v o
```

A TextMate grammar does not maintain the required global non-whitespace position
modulo 94 as parser state. Assigning a fixed opcode scope to literal `j`, `i`,
`*`, `p`, `<`, `/`, `v`, or `o` would therefore be wrong: the literal glyph is
not the decoded instruction by itself.

The grammar deliberately limits itself to facts it can represent correctly:

- `meta.encoded-source-unit.malbolge` for graphical source units;
- `invalid.illegal.control-character.malbolge` for rejected ASCII controls;
- `invalid.illegal.non-ascii.malbolge` for non-ASCII source text;
- accepted whitespace remains unscoped.

Position-dependent validity remains the responsibility of the Malbolge loader,
compiler, and VM rather than syntax highlighting.

## Profile compatibility

The classic loader (`src/runtime/virtual-machine/domain/loader.rs`) and
profile-driven loader
(`src/runtime/virtual-machine/domain/profile_machine.rs`) use the same
position-dependent decode model.
Profile evolution does not require a second TextMate grammar merely because
machine capacity or other target properties change.

The historical Ben interpreter is also not a separate syntax target. Its known
execution defects belong to runtime compatibility, not lexical highlighting.

## Source-whitespace contract

The Rust classic/profiled loaders, independent C VM, annotated frontend,
decompiler, and grammar use the same six-byte C-locale ASCII whitespace set.
Vertical tab `0x0B` is therefore ignored without consuming a loaded position,
matching the retained historical interpreter in the C locale.

## Upstream packaging

When the grammar is ready to publish, keep the dedicated grammar repository
minimal:

```text
LICENSE-MIT
README.md
syntaxes/
`-- malbolge.tmLanguage.json
```

Linguist should consume the published repository through its supported command:

```sh
script/add-grammar <GRAMMAR_REPOSITORY_URL>
```

Do not manually edit Linguist-generated grammar metadata.

## Validation

Before publishing the grammar repository:

1. Parse `syntaxes/malbolge.tmLanguage.json` as strict JSON.
1. Verify `scopeName` is exactly `source.malbolge`.
1. Verify the regex classes still match the selected VM source boundary.
1. Verify the six-byte source-whitespace set remains exact.
1. Run the current Linguist grammar compiler against the published repository.
1. Run `script/add-grammar` from a clean current Linguist checkout.

The local reference checkout documents the compiler contract, but this
workstation currently lacks the Go/Docker runtime required by Linguist's grammar
compiler wrapper. That upstream-specific gate remains incomplete rather than
being treated as passed.
