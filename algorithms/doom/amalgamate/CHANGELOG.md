# DOOM Amalgamation Changelog

This is the engineering log for the DOOM amalgamation stage inside Malbolge.

The quality stage already owns modernization of the guest C corpus. This stage
has a narrower responsibility: consume that accepted normalized tree and produce
one deterministic, source-bound `doom.c` without changing program behavior.

It is not a C-to-Malbolge compiler and it does not claim that the resulting file
has already executed under Malbolge semantics. It prepares one stable C
input for
that later compiler stage.

## Architecture: A Second Source-Bound Transform

The accepted pipeline is:

```text
quality/out/doom_fixed/linuxdoom-1.10/
                  |
                  v
      amalgamation_oracle.py
                  |
                  v
       ignored oracle/doom.c
                  |
                  v
         algorithms/diff
                  |
                  v
       amalgamate/main.rs
                  |
                  v
          out/doom.c
```

The normalized multi-file tree is the source. The local single-file oracle is
only authoring evidence. The generated Rust transform is the durable algorithm.
At materialization time it requires the admitted normalized source and does not
require the oracle.

Quality and amalgamation remain separate algorithms because they have different
source identities, target semantics, and failure boundaries. The quality stage
may change guest code. The amalgamation stage may only preserve accepted code
while changing its translation-unit packaging.

## Building the Single-Translation-Unit Oracle

The oracle builder is
`algorithms/doom/generator/amalgamation_oracle.py`.

I did not accept plain textual concatenation. A valid amalgamation has to
preserve
preprocessing order, internal linkage, declarations, source locations, and the
relationship between project and system headers.

The accepted builder currently processes:

- 65 C translation units;
- 83 unique project headers;
- 148 expanded project includes;
- 564 duplicate-header elisions;
- one guarded include cycle;
- 19 private-name bindings that require isolation.

The final oracle contains 2,505,975 bytes and 79,313 lines.

### Translation-unit ordering

The translation units are emitted in one deterministic order declared by the
builder. Filesystem enumeration order is not authoritative.

Ordering matters because declarations, compile-time configuration, and private
bindings can become observable after formerly separate translation units share a
single preprocessing and identifier namespace.

The builder rejects missing or unexpected translation units instead of silently
changing the order or omitting a file.

### Project-header expansion

Project-local quoted includes are expanded into the single output. System
includes remain includes and are not copied into the artifact.

Header expansion tracks canonical project-relative paths, include guards, and
the
active expansion stack. Duplicate guarded headers are elided deterministically.
A guarded recursive include is also elided rather than recursing indefinitely.

The builder records expansion statistics so a header graph change is visible in
review instead of becoming an unexplained `doom.c` hash change.

### Internal-linkage isolation

Separate C translation units may legally reuse the same `static` function or
object name. A single translation unit may not contain those collisions
unchanged.

The builder identifies the private bindings that collide across source files and
renames them with deterministic translation-unit-specific names. References in
the owning translation unit are rewritten with the same binding map.

Only private bindings that need isolation are renamed. External identifiers and
public ABI names remain unchanged.

The accepted artifact currently contains 19 such private binding rewrites.

### Preprocessor and source-location preservation

The builder preserves conditional-preprocessor structure and does not attempt to
interpret system headers or replace the C preprocessor.

Generated `#line` transitions retain the original project source identity for
compiler diagnostics. The native debug adapter separately reports the launched
artifact as `doom.c`, so runtime titles identify the actual executable input
while
Clang diagnostics can still point into the normalized source files.

### Provenance

The output preserves the accepted source attribution and license material from
the normalized corpus. WADs and other runtime data never enter the amalgamation
source identity, oracle payload, or generated Rust transform.

## Source-Bound Algorithm Generation

`algorithms/doom/generator/amalgamate.py` configures the generic exact
transform.
Its source is the accepted normalized `linuxdoom-1.10/` tree. Its target is an
oracle tree containing exactly one path: `doom.c`.

`algorithms/diff` then:

1. snapshots the admitted normalized source and local oracle;
2. authors the deterministic exact reconstruction plan;
3. protects target-only bytes behind authenticated source-bound recovery;
4. emits standalone Rust into `algorithms/doom/amalgamate/main.rs`;
5. verifies the complete target snapshot before final publication.

Possessing `main.rs` alone is insufficient to materialize `doom.c`. Missing,
unrelated, or mutated normalized source fails before output publication.

The transform refuses an existing output root instead of merging with it. This
keeps publication transactional and prevents stale files from being mistaken for
accepted output.

## Generated Rust Hygiene

The first generated transforms embedded protected payload hex in very long
physical lines. That was valid Rust but violated the repository's 80-column
source contract and made review unnecessarily poor.

The generic Rust emitter now:

- emits the repository-standard structured `File` and `Path` header;
- marks the artifact as generated and not hand-edited;
- records the boundary contract and related documents;
- marks the file as intentionally large;
- splits protected hex into deterministic 64-character chunks;
- guarantees a maximum physical line length of 80 characters.

A regression test compiles and materializes emitted Rust and fails if the header
is missing or any generated line exceeds 80 characters. No large-file
line-length
exception is used.

The accepted generated transform is:

- path: `algorithms/doom/amalgamate/main.rs`;
- size: 5,744,748 bytes;
- lines: 80,510;
- maximum line length: 80;
- SHA-256:
  `ec1ddf2ad07c8664f46739f878ec83b1a6690f45d5c1fbbb5025cb2a79208d1e`.

Repeated recipe generation produces the same bytes.

## Materialization and Identity

Compiling `amalgamate/main.rs` with pinned Rust 1.97.1 and `-D warnings`
produces
a standalone transform. Running it against the exact accepted normalized source
publishes one file named `doom.c`.

The accepted canonical C artifact is:

- path: `algorithms/doom/amalgamate/out/doom.c` (ignored);
- size: 2,505,975 bytes;
- lines: 79,313;
- SHA-256:
  `e1d8d2fc12f721815c6fc84e486e40e9d017fe858aeeda58df15b03df5d2b2b1`.

The following copies are byte-identical:

- the ignored local oracle;
- first materialization;
- repeated materialization;
- `algorithms/doom/amalgamate/out/doom.c`;
- `tests/applications/doom/out/doom.c`.

The fixture is local and ignored because the repository versions the algorithm,
not third-party-derived generated C.

## Semantic Verification

Byte identity with the oracle proves deterministic reconstruction. It does not
by
itself prove that combining 65 translation units preserved C behavior, so the
amalgamation has separate compiler and runtime evidence.

### Strict Clang matrix

The materialized `doom.c` passes Clang 22.1.8 with strict warnings and `-Werror`
for:

- Linux x86-64;
- Linux AArch64;
- Windows x86-64;
- Windows AArch64;
- macOS x86-64;
- macOS AArch64.

The Windows host adapter also passes the same strict warning profile on its host
surface.

### Multi-TU versus single-TU behavior

A deterministic no-CRT harness was compiled twice with the same guest/runtime
boundary:

- once from the 65 normalized translation units;
- once from the generated `doom.c`.

Both executions exited successfully and produced the same framebuffer/audio
transcript:

```text
92ff55046afd3976
4571f707b08d56cd
912da30aff88aaed
```

This is the direct behavioral acceptance evidence for the packaging change.

### Sanitizers and native play

The materialized single-TU source builds with ASan+UBSan and links with the
Windows adapter. Sanitizer work during the quality/runtime pass exposed fixed
signed-shift, fixed-point overflow, tangent-boundary, and renderer-wrap defects.

The final bytes were also used for roughly 20 minutes of native play without
reproducing the reported long-range autoaim crash. Manual play supplements the
deterministic harness; it does not replace it.

## Negative and Determinism Tests

The stage is fail-closed in the cases that matter for source binding and
publication:

- empty source tree: rejected;
- missing source file: rejected;
- unexpected source shape: rejected;
- mutated normalized source: rejected;
- existing output root: rejected;
- repeated generation: byte-identical;
- repeated materialization: byte-identical;
- partial target publication after failure: absent.

The DOOM generator and generic diff suite currently pass 140/140 tests when the
pinned Rust compiler path is supplied explicitly. The emitted transforms compile
and materialize inside that suite.

The repository guest-C validator accepts all 65 normalized input translation
units. The final single-TU artifact passes the strict six-target Clang matrix.

Historical commit-message repair now leaves zero `JIG-COMMIT-*`
diagnostics. Remaining Jig findings concern current repository files and are
not an amalgamation diagnostic.

## Final Source-Level Acceptance

The amalgamation stage is complete at the C boundary.

It now has:

- one deterministic C-aware oracle builder;
- one source-bound generated Rust algorithm;
- one canonical ignored `doom.c` product;
- exact source/oracle/materialization identity;
- strict compiler acceptance;
- direct multi-TU/single-TU behavioral equivalence;
- negative source-binding and transactional-publication tests;
- reproducible documentation and artifact identities.

The next work is outside this stage: lower the accepted `doom.c` through the
C-to-Malbolge compiler, link the versioned host capabilities, generate
`doom.malbolge`, and execute that artifact under Malbolge semantics. Until that
happens, this changelog claims source-level C acceptance only.

The modernization and runtime history remains in `../quality/CHANGELOG.md`.
