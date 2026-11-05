# Emit twenty-four distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-twenty-four-v1` (fixed teaching example, not a generated
  challenge).
- Source: [`emit-twenty-four.c`](emit-twenty-four.c), SHA-256
  `1bab4a3ece74188988944e0f98834aa3f86709c517508f125d93dc126b0119ea`.
- Guest artifact: [`emit-twenty-four.malbolge`](emit-twenty-four.malbolge),
  SHA-256
  `97cbe0aa9f95c315919cfec5f3cfbc151f3f31e28fd1272bf740bb2e0f1f2f73`.
- Target: `malbolge-2026`, current 15-trit profile, in an extended
  `.malbolge` `MALBCAP1` capsule, not classic raw Malbolge source.
- Compiler: repository `c2malbolge.py` pipeline, LLVM 22.1.8 native C
  frontend, `c2malbolge_json` and `malbolge_layout` Rust executables.
  Generated on 2026-11-04 against compiler source commit `38e157d4b`;
  local binary provenance is not independently attested. Recompilation
  verifies bytes.
- Input: none. Guest output: bytes
  `3e 0b 2c 12 36 01 3d 95 0f 9d 17 8b 21 93 92 20 94 0e 9b 18 8a 1c 2f 23`,
  no newline.
  VT (`0b`), DC2 (`12`), SOH (`01`), SI (`0f`), ETB (`17`),
  SO (`0e`), CAN (`18`) and FS (`1c`) are control bytes; eight are
  printable ASCII and eight have their high bit set.

Twenty-four source-proven C `putchar` calls yield twenty-one disjoint
guest `CrazyData` writes and three `RotateData` writes at the eighth,
fifteenth and twenty-second arithmetic positions. Twenty-one leading
no-ops place relocation at source position twenty-one. One reached trailing
no-op precedes the halt. All guest data writes remain outside code cells.
The normative profile VM independently verifies twenty-four distinct
binary output bytes, not host C execution or a general byte-stream API.

## Reproduce from the repository root

Build the repository-pinned frontend and debug compiler/VM executables using
[CLI build instructions][cli-build]. Use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-twenty-four-v1 --capsule \
  --output .temp/emit-twenty-four-v1-check.malbolge \
  docs/technical/examples/corpus/emit-twenty-four.c
sha256sum .temp/emit-twenty-four-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-twenty-four.malbolge \
  .temp/emit-twenty-four-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-twenty-four.malbolge \
  --report-steps | od -An -tx1
```

For unframed graphical source, omit `--capsule` and select the modern target
profile explicitly when running it:

```sh
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-twenty-four-v1 \
  --output .temp/emit-twenty-four-v1-raw.malbolge \
  docs/technical/examples/corpus/emit-twenty-four.c
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools .temp/emit-twenty-four-v1-raw.malbolge \
  --raw-profile malbolge-2026 --report-steps | od -An -tx1
```

The artifact is `1623` bytes, with the SHA-256 digest above.
Matching output alone does not establish byte-identical compiler reproduction.
The VM must emit
`3e 0b 2c 12 36 01 3d 95 0f 9d 17 8b 21 93 92 20 94 0e 9b 18 8a 1c 2f 23`
with a 72-step stderr receipt. The automated
`tests/test_versioned_example_corpus.py` checks stored hashes, VM behavior and
source-to-capsule recompilation with pinned local tools.

This teaching pair is not the required parametric challenge instance.
General C lowering, cross-backend hashing, and arbitrary binary streams remain
unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
