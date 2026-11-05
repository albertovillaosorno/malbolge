# Emit twenty distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-twenty-v1` (fixed teaching example, not a generated
  challenge).
- Source: [`emit-twenty.c`](emit-twenty.c), SHA-256
  `f6f81dfbc9abef2429d1090866bf6bae42d8495a3ed91219f6e703e37545aee6`.
- Guest artifact: [`emit-twenty.malbolge`](emit-twenty.malbolge), SHA-256
  `e0f9a1d80c98be4a5d1c1bc5fa9800772e2e7fafc8fbbc4a22b72409e9eedfcb`.
- Target: `malbolge-2026`, current 15-trit profile, in an extended
  `.malbolge` `MALBCAP1` capsule, not classic raw Malbolge source.
- Compiler: repository `c2malbolge.py` pipeline, LLVM 22.1.8 native C
  frontend, `c2malbolge_json` and `malbolge_layout` Rust executables.
  Generated on 2026-11-04 against compiler source commit `c9ef844dc`;
  local binary provenance is not independently attested. Recompilation
  verifies bytes.
- Input: none. Guest output: bytes
  `3e 14 35 12 3f 0a a4 9c ad a3 1a a8 a2 95 ab 9f 98 1d ac ae`, no newline.
  DC4 (`14`), DC2 (`12`), LF (`0a`), SUB (`1a`) and GS (`1d`) are
  control bytes; `3e`, `35`, `3f` are printable and twelve bytes have
  their high bit set.
- Guest execution: 54 VM steps; stderr `malbolge-steps-v1:54`.

Twenty source-proven C `putchar` calls yield seventeen disjoint guest
`CrazyData` writes and three `RotateData` writes at the seventh, eleventh,
and eighteenth arithmetic positions. Twelve reached leading no-ops place
relocation at position twelve, and data writes lie outside the code cells.
The normative profile VM independently verifies twenty distinct binary output
bytes, not host C execution or a general byte-stream API.

## Reproduce from the repository root

Build the repository-pinned frontend and debug compiler/VM executables using
[CLI build instructions][cli-build]. Use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-twenty-v1 --capsule \
  --output .temp/emit-twenty-v1-check.malbolge \
  docs/technical/examples/corpus/emit-twenty.c
sha256sum .temp/emit-twenty-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-twenty.malbolge \
  .temp/emit-twenty-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-twenty.malbolge \
  --report-steps | od -An -tx1
```

For unframed graphical source, omit `--capsule` and select the modern target
profile explicitly when running it:

```sh
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-twenty-v1 \
  --output .temp/emit-twenty-v1-raw.malbolge \
  docs/technical/examples/corpus/emit-twenty.c
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools .temp/emit-twenty-v1-raw.malbolge \
  --raw-profile malbolge-2026 --report-steps | od -An -tx1
```

The artifact is `1479` bytes, with the SHA-256 digest above.
Matching output alone does not establish byte-identical compiler reproduction.
The VM must emit `3e 14 35 12 3f 0a a4 9c ad a3 1a a8 a2 95 ab 9f 98 1d ac ae`
with a 54-step stderr receipt. The automated
`tests/test_versioned_example_corpus.py` checks stored hashes, VM behavior and
source-to-capsule recompilation with pinned local tools.

This teaching pair is not the required parametric challenge instance.
General C lowering, cross-backend hashing, and arbitrary binary streams remain
unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
