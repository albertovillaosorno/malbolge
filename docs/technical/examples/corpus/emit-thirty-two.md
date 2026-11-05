# Emit thirty-two distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-thirty-two-v1` (fixed teaching example, not a challenge).
- Source: [`emit-thirty-two.c`](emit-thirty-two.c), SHA-256
  `a10e977d9912ef2bea54c9bb702a1295345a5ffe58b7721a8afac4e2bb02dd7b`.
- Guest artifact: [`emit-thirty-two.malbolge`](emit-thirty-two.malbolge),
  SHA-256 `f9322856b876e52e368a51b54cdecab167fc0b9d5baa8e11aa2bdbe95c201205`.
- Target: `malbolge-2026` current 15-trit profile, `MALBCAP1` extended
  `.malbolge` capsule rather than classic raw Malbolge.
- Compiler: repository `c2malbolge.py`, LLVM 22.1.8 frontend,
  `c2malbolge_json` and `malbolge_layout` Rust binaries, built from
  source commit `571d08418` on 2026-11-05. Local binary provenance
  is not independently attested; byte-exact recompilation is checked.
- Input: none. Guest output: 32 bytes, hex
  `41 17 32 18 50 23 5c 27 4b 34 4f 09 d4 ac e1 9e` followed by
  `e2 ab 0b d6 9c e3 a0 d2 ad 93 e0 9f e4 aa d5 ae`, no newline.
  Nine bytes are printable ASCII, four are controls and nineteen
  have their high bit set.

Thirty-two exact source-proven `putchar` calls lower to 29 distinct guest
`CrazyData` writes and three `RotateData` writes at byte indices 11, 18,
and 25. Thirty initial no-ops precede the data-pointer relocation; one
additional reached no-op precedes byte index four. All 32 writes target
distinct data cells at 105..168 beyond the 97-cell source. The real guest
computes the 32 outputs, with no guest input consumed. This is a finite
verified compiler mode, not a general C byte-stream implementation.

## Reproduce from the repository root

Build the pinned frontend, adapter, layout and VM binaries as described in
[CLI build instructions][cli-build]. Use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-thirty-two-v1 --capsule \
  --output .temp/emit-thirty-two-v1-check.malbolge \
  docs/technical/examples/corpus/emit-thirty-two.c
sha256sum .temp/emit-thirty-two-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-thirty-two.malbolge \
  .temp/emit-thirty-two-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-thirty-two.malbolge \
  --report-steps | od -An -tx1
```

The capsule is 1823 bytes. The normative VM must emit the exact 32-byte
sequence and `malbolge-steps-v1:97` on stderr. `tests/test_versioned_example_corpus.py`
verifies source/artifact hashes, VM output and source recompilation.
Matching output alone does not establish artifact identity; reproducible
capsule bytes are required independently.

This retained teaching pair is not a parametric challenge instance.
General C lowering, cross-backend hashing and arbitrary binary streams
remain unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
