# Annotated Malbolge source syntax and formatter

## Status

Active

## Purpose

Provide a readable, commentable, multiline authoring/view format that lowers
deterministically to ordinary canonical Malbolge bytes. Preserve canonical
position-sensitive semantics and historical/raw `.malbolge` compatibility.

## Scope

This contract governs the annotated-source canonicalizer/formatter, source
maps, compiler/decompiler integration, and explicit interpreter/tooling entry
points that opt into annotated parsing. It does not redefine the raw classic or
profile loaders.

## Current Behavior

### Existing whitespace rule

Canonical Malbolge already ignores ASCII whitespace during loading. Therefore
line breaks, indentation, and blank lines can be inserted without consuming a
loaded position. The new feature is not multiline execution; that property
already exists.

### Annotated syntax v1

Version one adds presentation syntax only before canonical loading:

- ASCII whitespace remains semantically empty and may appear freely.
- A full-line comment begins when `#` is the first non-whitespace byte on a
  line and the following byte is horizontal ASCII space or tab. Bare `#`, a
  hash immediately before a line ending/end of file, and prefixes such as `#X`
  remain code. This makes every graphical canonical byte sequence representable
  without an escape syntax.
- Inline `code # comment` syntax is not admitted in v1. Comments are a
  presentation-layer line form, not a token that can begin after code.
- Block comments are not admitted in v1.
- The canonicalizer removes comments and ASCII whitespace, then submits the
  resulting graphical bytes to the exact selected-profile loader.
- Raw `.malbolge` input never gains implicit comment semantics. Annotated
  parsing
  must be selected by an explicit source format/entry point.

`format_annotated_source()` inserts deterministic LF line breaks at an explicit
nonzero byte width. It emits no horizontal whitespace in code lines, so wrapping
cannot create the `# ` or `#\t` marker accidentally. Bare and line-start hash
bytes remain ordinary code.

### Implemented frontend

`src/runtime/virtual-machine/domain/annotated.rs` now owns the presentation
frontend.
`canonicalize_annotated_source()` returns exact canonical bytes plus one
annotated offset/line/column for every loaded position.
`format_annotated_source()` provides deterministic automatic wrapping.
`Machine`, `ExecutionMachine`, and `ProfileMachine` expose explicit annotated
constructors; their existing raw `from_source` APIs remain unchanged. After
canonicalization, the ordinary classic/profile loader remains final admission

authority.

The reusable `format_annotated_source()` remains structure-neutral. The
`malbolge_decompile --representation annotated` output now adds an initial-state
structural view using the same profile-admitted `analyze_initial` evidence as
its analysis and C representations. It splits after initially decoded halt and
indirect-control cells, otherwise wraps at 64 canonical bytes. Full-line
comments carry the selected profile identity, an explicit warning that future
self-modification invalidates static decode, and each region's exact inclusive
canonical position range, last initially decoded instruction, and control-flow
class. Every code line is emitted through the canonical formatter, and the
annotated canonicalizer recovers the exact original loaded bytes and their
new offset/line/column map.

These boundaries are initial VM analysis, **not** reconstructed C blocks or
indirect jump targets. Compiler C/IR-aligned comments and source-map
composition against emitted layout remain follow-on work.

### Structure-aware formatting

Compiler/decompiler tools may use source maps to place deterministic breaks and
comments at C/IR region boundaries. For example, an annotated generated view may
look conceptually like:

```text
    # C function: update_player
<canonical Malbolge bytes for region A>

    # C block: collision branch
<canonical Malbolge bytes for region B>
```

Those comments are documentation only. Removing every comment and whitespace
byte must recover the same canonical executable sequence. The formatter may use
a deterministic bounded-width fallback when no higher-level structural boundary
is available.

### Source-map consequence

Canonicalization records a mapping from annotated byte/line ranges to canonical
loaded positions. Compiler C-level source maps and
decompiler/reverse-engineering
annotations may layer on that mapping without turning comments into executable
metadata.

## Invariants

- `canonicalize(annotated)` is an ordinary canonical Malbolge byte sequence.
- The selected profile loader remains the final source-admission authority.
- Whitespace/comments consume zero canonical loaded positions.
- `canonicalize(format(canonical)) == canonical` byte-for-byte.
- Formatting, comment text, indentation, newline convention, and wrap width
  never
  change decode phase, memory layout, self-modification, or execution.
- Canonical `.malbolge` files are never reinterpreted merely because they
  contain
  hash bytes.
- Comment recognition is ASCII/byte-defined and locale-independent.

## Failure Behavior

Unknown source-format versions, malformed annotated input, non-ASCII
presentation
bytes outside an explicitly admitted future encoding, or canonicalized source
rejected by the selected profile loader fail closed with deterministic
diagnostics. No tool silently retries the same bytes as a different source
format.

## Verification

Required evidence includes:

- raw canonical programs containing hash and slash bytes remain unchanged;
- bare `#`/`#X` and inline hashes remain code while `# ` / `#\t` full-line
  comments disappear without changing loaded positions;
- LF/CRLF/CR presentation produces identical canonical bytes;
- formatter round trips are byte-exact;
- automatic wrapping cannot accidentally create a comment marker from code;
- source-map positions match loader positions after comment/whitespace removal;
- classic facade/current-profile VMs produce identical observations from
  canonical bytes and their annotated presentation equivalents.

`tests/vm/annotated.rs` covers those boundaries with seven strict
fixtures, including exact source-map positions and hash-heavy formatter
round-trips.

## References

- [Historical Malbolge semantics](../specification/malbolge-1998.md)
- [Malbolge decompiler](malbolge-decompiler.md)
- [C-Level Source Debugging](../adr/c-level-source-debugging.md)
- [Specification Authority And Malbolge
  Evolution](../adr/specification-authority-and-malbolge-evolution.md)

`tests/decompiler.rs` additionally round-trips the profile-explicit annotated
view through the canonicalizer, checks retained loaded-position offset and
line/column mapping, compares historical/current VM observations, confirms
initial indirect/halt region boundaries, rejects invalid canonical input, and
checks byte-identical CLI output through stdout and `--output`.
