# Emit thirty-four distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-thirty-four-v1` (fixed teaching example, not a challenge).
- Source: [`emit-thirty-four.c`](emit-thirty-four.c), SHA-256
  `af99582479ac6ead9b3c326835e7c2d5f3f1102338f8f3769026d72989d8e196`.
- Guest artifact: [`emit-thirty-four.malbolge`](emit-thirty-four.malbolge),
  SHA-256 `a21549a604de61c889020a1574560fc02ef9c34beee0afa592e02c31a1857959`.
- Target: `malbolge-2026` current 15-trit profile, `MALBCAP1` extended
  `.malbolge` capsule rather than classic raw Malbolge.
- Compiler: repository `c2malbolge.py`, LLVM 22.1.8 frontend,
  `c2malbolge_json` and `malbolge_layout` Rust binaries, with exact
  34-byte admission introduced in source commit `d810b4e87` on 2026-11-05.
  Local binary provenance is not independently attested; byte-exact
  recompilation is checked separately.
- Input: none. Guest output: 34 bytes, hex
  `3f 11 2c 14 39 04 a8 50 36 3d 42 44 2f 0b d6 9c e3 a0`
  followed by `d2 ad 93 e0 9f e4 aa d5 ae 09 d4 ac e1 9e e2 ab`,
  no newline. Nine bytes are printable ASCII, five are controls and
  twenty have their high bit set.

Thirty-four exact source-proven `putchar` calls lower to 30 `CrazyData`
updates and four `RotateData` updates at zero-based byte indices 6, 13,
20 and 27. Twenty-six initial no-ops precede data-pointer relocation;
one additional reached no-op precedes byte index seven. All 34 writes
target distinct data cells at 109..121 and 124..176, beyond the
97-cell source. The real guest computes all 34 outputs and consumes no
input. This is a finite verified compiler mode, not general C output.

## Reproduce from the repository root

Build the pinned frontend, adapter, layout and VM binaries as described in
[CLI build instructions][cli-build]. Use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-thirty-four-v1 --capsule \
  --output .temp/emit-thirty-four-v1-check.malbolge \
  docs/technical/examples/corpus/emit-thirty-four.c
sha256sum .temp/emit-thirty-four-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-thirty-four.malbolge \
  .temp/emit-thirty-four-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-thirty-four.malbolge \
  --report-steps | od -An -tx1
```

The capsule is 1823 bytes. The normative VM must emit the exact 34-byte
sequence and `malbolge-steps-v1:97` on stderr. The corpus regression
checks source/artifact hashes, VM output and byte-identical source
recompilation. Matching output alone does not establish artifact identity.

This retained teaching pair is not a parametric challenge instance.
General C lowering, cross-backend hashing and arbitrary binary streams
remain unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
