# Emit thirteen distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-thirteen-v1` (fixed teaching example, not a generated
  challenge).
- Source: [`emit-thirteen.c`](emit-thirteen.c), SHA-256
  `59a96352ab35a582e2424d15818ce59c105fc8222cd3b07394c1486e3ed32e0e`.
- Guest artifact: [`emit-thirteen.malbolge`](emit-thirteen.malbolge), SHA-256
  `10b08a4c61f6e5a28f9ef1e01809cdc455178b0523328205bb101325c7a78bc5`.
- Target: `malbolge-2026`, current 15-trit profile, in an extended
  `.malbolge` `MALBCAP1` capsule, not classic raw Malbolge source.
- Compiler: repository `c2malbolge.py` pipeline, LLVM 22.1.8 native C
  frontend, `c2malbolge_json` and `malbolge_layout` Rust executables.
  Generated on 2026-11-04 against source commit `b9e741a1f`;
  local binary provenance is not independently attested. Recompilation
  verifies bytes.
- Input: none. Guest output: bytes `42 43 30 16 54 09 bf c6 c8 87 e3 ab a4`,
  no newline. Nontext control and high-bit values are binary, not UTF-8.
- Guest execution: 29 VM steps; stderr `malbolge-steps-v1:29`.

Thirteen source-proven C `putchar` calls yield twelve disjoint guest
`CrazyData` writes and one `RotateData` write at the sixth arithmetic
position. The normative profile VM independently verifies 13 distinct output
bytes, not host C execution or a general byte-stream API.

## Reproduce from the repository root

Build the repository-pinned frontend and debug compiler/VM executables using
[CLI build instructions][cli-build]. Use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-thirteen-v1 --capsule \
  --output .temp/emit-thirteen-v1-check.malbolge \
  docs/technical/examples/corpus/emit-thirteen.c
sha256sum .temp/emit-thirteen-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-thirteen.malbolge \
  .temp/emit-thirteen-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-thirteen.malbolge \
  --report-steps | od -An -tx1
```

For unframed graphical source, omit `--capsule` and select the modern target
profile explicitly when running it:

```sh
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-thirteen-v1 \
  --output .temp/emit-thirteen-v1-raw.malbolge \
  docs/technical/examples/corpus/emit-thirteen.c
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools .temp/emit-thirteen-v1-raw.malbolge \
  --raw-profile malbolge-2026 --report-steps | od -An -tx1
```

The artifact is `1279` bytes, with the SHA-256 digest above.
Matching output alone does not establish byte-identical compiler reproduction.
The VM must emit `42 43 30 16 54 09 bf c6 c8 87 e3 ab a4` with a 29-step
stderr receipt. The automated `tests/test_versioned_example_corpus.py`
checks stored hashes, VM behavior and source-to-capsule recompilation with
pinned local tools.

This teaching pair is not the required parametric challenge instance.
General C lowering, cross-backend hashing, and arbitrary binary streams remain
unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
