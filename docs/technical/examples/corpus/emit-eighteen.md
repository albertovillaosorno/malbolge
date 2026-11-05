# Emit eighteen distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-eighteen-v1` (fixed teaching example, not a generated
  challenge).
- Source: [`emit-eighteen.c`](emit-eighteen.c), SHA-256
  `ac2df0d8547294c5307acaa9e9777eac94f98f83842b039b5fde50ad98bcb091`.
- Guest artifact: [`emit-eighteen.malbolge`](emit-eighteen.malbolge), SHA-256
  `23855763efbc636c108d5da73b723391e66d481c489de17482344b37326c5b8a`.
- Target: `malbolge-2026`, current 15-trit profile, in an extended
  `.malbolge` `MALBCAP1` capsule, not classic raw Malbolge source.
- Compiler: repository `c2malbolge.py` pipeline, LLVM 22.1.8 native C
  frontend, `c2malbolge_json` and `malbolge_layout` Rust executables.
  Generated on 2026-11-04 against compiler source commit `592f9fd22`;
  local binary provenance is not independently attested. Recompilation
  verifies bytes.
- Input: none. Guest output: bytes
  `54 22 19 3e 38 03 09 dd 87 d1 a5 99 bf 08 c7 c6 c2 91`, no newline.
  EM (`19`), ETX (`03`), HT (`09`), and BS (`08`) are control bytes;
  ten values have their high bit set.
- Guest execution: 39 VM steps; stderr `malbolge-steps-v1:39`.

Eighteen source-proven C `putchar` calls yield fifteen disjoint guest
`CrazyData` writes and three `RotateData` writes at the seventh, ninth, and
fourteenth arithmetic positions. The normative profile VM independently
verifies eighteen distinct output bytes, not host C execution or a general
byte-stream API.

## Reproduce from the repository root

Build the repository-pinned frontend and debug compiler/VM executables using
[CLI build instructions][cli-build]. Use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-eighteen-v1 --capsule \
  --output .temp/emit-eighteen-v1-check.malbolge \
  docs/technical/examples/corpus/emit-eighteen.c
sha256sum .temp/emit-eighteen-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-eighteen.malbolge \
  .temp/emit-eighteen-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-eighteen.malbolge \
  --report-steps | od -An -tx1
```

For unframed graphical source, omit `--capsule` and select the modern target
profile explicitly when running it:

```sh
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-eighteen-v1 \
  --output .temp/emit-eighteen-v1-raw.malbolge \
  docs/technical/examples/corpus/emit-eighteen.c
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools .temp/emit-eighteen-v1-raw.malbolge \
  --raw-profile malbolge-2026 --report-steps | od -An -tx1
```

The artifact is `1359` bytes, with the SHA-256 digest above.
Matching output alone does not establish byte-identical compiler reproduction.
The VM must emit `54 22 19 3e 38 03 09 dd 87 d1 a5 99 bf 08 c7 c6 c2 91`
with a 39-step stderr receipt. The automated
`tests/test_versioned_example_corpus.py` checks stored hashes, VM behavior and
source-to-capsule recompilation with pinned local tools.

This teaching pair is not the required parametric challenge instance.
General C lowering, cross-backend hashing, and arbitrary binary streams remain
unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
