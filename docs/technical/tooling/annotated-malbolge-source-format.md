# Annotated Malbolge source syntax and formatter

## Status

Proposed

## Purpose

Provide a readable, commentable, multiline authoring/view format that lowers
deterministically to ordinary canonical Malbolge bytes. Preserve canonical
position-sensitive semantics and historical/raw `.malbolge` compatibility.

## Scope

This contract governs a future annotated-source canonicalizer/formatter, its
source maps, compiler/decompiler integration, and explicit interpreter/tooling
entry points that opt into annotated parsing. It does not redefine the raw
classic or profile loaders.

## Current Behavior

### Existing whitespace rule

Canonical Malbolge already ignores ASCII whitespace during loading. Therefore
line breaks, indentation, and blank lines can be inserted without consuming a
loaded position. The new feature is not multiline execution; that property
already exists.

### Proposed annotated syntax v1

Version one adds presentation syntax only before canonical loading:

- ASCII whitespace remains semantically empty and may appear freely.
- A full-line comment begins when `//` is the first non-whitespace token on a
  line and continues through LF, CRLF, CR, or end of file.
- Inline `code // comment` syntax is not admitted in v1. Slash is a legitimate
  Malbolge source byte, so inline comment recognition would make ordinary code
  unnecessarily ambiguous.
- Block comments are not admitted in v1.
- The canonicalizer removes comments and ASCII whitespace, then submits the
  resulting graphical bytes to the exact selected-profile loader.
- Raw `.malbolge` input never gains implicit comment semantics. Annotated parsing
  must be selected by an explicit source format/entry point.

A formatter may insert line breaks automatically because those breaks do not
change loaded positions. It must never emit a code line whose first
non-whitespace bytes accidentally form the full-line comment marker. If needed,
it inserts a semantically empty line break before or between those bytes.

### Structure-aware formatting

Compiler/decompiler tools may use source maps to place deterministic breaks and
comments at C/IR region boundaries. For example, an annotated generated view may
look conceptually like:

```text
// C function: update_player
<canonical Malbolge bytes for region A>

// C block: collision branch
<canonical Malbolge bytes for region B>
```

Those comments are documentation only. Removing every comment and whitespace
byte must recover the same canonical executable sequence. The formatter may use
a deterministic bounded-width fallback when no higher-level structural boundary
is available.

### Source-map consequence

Canonicalization records a mapping from annotated byte/line ranges to canonical
loaded positions. Compiler C-level source maps and decompiler/reverse-engineering
annotations may layer on that mapping without turning comments into executable
metadata.

## Invariants

- `canonicalize(annotated)` is an ordinary canonical Malbolge byte sequence.
- The selected profile loader remains the final source-admission authority.
- Whitespace/comments consume zero canonical loaded positions.
- `canonicalize(format(canonical)) == canonical` byte-for-byte.
- Formatting, comment text, indentation, newline convention, and wrap width never
  change decode phase, memory layout, self-modification, or execution.
- Canonical `.malbolge` files are never reinterpreted merely because they contain
  two slash bytes.
- Comment recognition is ASCII/byte-defined and locale-independent.

## Failure Behavior

Unknown source-format versions, malformed annotated input, non-ASCII presentation
bytes outside an explicitly admitted future encoding, or canonicalized source
rejected by the selected profile loader fail closed with deterministic
diagnostics. No tool silently retries the same bytes as a different source
format.

## Verification

Required evidence includes:

- raw canonical programs containing slash bytes remain unchanged;
- full-line comments disappear without changing loaded positions;
- LF/CRLF/CR presentation produces identical canonical bytes;
- formatter round trips are byte-exact;
- automatic wrapping cannot accidentally create a comment marker from code;
- source-map positions match loader positions after comment/whitespace removal;
- classic and current-profile VMs produce identical observations from canonical
  bytes and their annotated presentation equivalents.

## References

- [Historical Malbolge semantics](../specification/malbolge-1998.md)
- [Malbolge decompiler](malbolge-decompiler.md)
- [C-Level Source Debugging](../adr/c-level-source-debugging.md)
- [Specification Authority And Malbolge Evolution](../adr/specification-authority-and-malbolge-evolution.md)
