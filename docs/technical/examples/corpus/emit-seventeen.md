# Emit seventeen distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-seventeen-v1` (fixed teaching example, not a generated
  challenge).
- Source: [`emit-seventeen.c`](emit-seventeen.c), SHA-256
  `a02514adb41a373560e30ed7a4b68cf995872b0c0aca174a20abbdb8618b9cb6`.
- Guest artifact: [`emit-seventeen.malbolge`](emit-seventeen.malbolge), SHA-256
  `2f2087fcac832159d1759b9d1b3fd7da96f51904eafd27eda84f2242573df952`.
- Target: `malbolge-2026`, current 15-trit profile, in an extended
  `.malbolge` `MALBCAP1` capsule, not classic raw Malbolge source.
- Compiler: repository `c2malbolge.py` pipeline, LLVM 22.1.8 native C
  frontend, `c2malbolge_json` and `malbolge_layout` Rust executables.
  Generated on 2026-11-04 against compiler source commit `9248975ee`;
  local binary provenance is not independently attested. Recompilation
  verifies bytes.
- Input: none. Guest output: bytes
  `59 3f 2c 48 50 1b 18 32 15 4d 4b 3b 42 0f 44 30 17`, no newline.
  ESC (`1b`), CAN (`18`), NAK (`15`), SI (`0f`), and ETB (`17`) are
  control bytes; the other twelve values are printable ASCII.
- Guest execution: 37 VM steps; stderr `malbolge-steps-v1:37`.

Seventeen source-proven C `putchar` calls yield fourteen disjoint guest
`CrazyData` writes and three `RotateData` writes at the seventh, ninth, and
fourteenth arithmetic positions. The normative profile VM independently
verifies seventeen distinct output bytes, not host C execution or a general
byte-stream API.

## Reproduce from the repository root

Build the repository-pinned frontend and debug compiler/VM executables using
[CLI build instructions][cli-build]. Use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-seventeen-v1 --capsule \
  --output .temp/emit-seventeen-v1-check.malbolge \
  docs/technical/examples/corpus/emit-seventeen.c
sha256sum .temp/emit-seventeen-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-seventeen.malbolge \
  .temp/emit-seventeen-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-seventeen.malbolge \
  --report-steps | od -An -tx1
```

For unframed graphical source, omit `--capsule` and select the modern target
profile explicitly when running it:

```sh
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-seventeen-v1 \
  --output .temp/emit-seventeen-v1-raw.malbolge \
  docs/technical/examples/corpus/emit-seventeen.c
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools .temp/emit-seventeen-v1-raw.malbolge \
  --raw-profile malbolge-2026 --report-steps | od -An -tx1
```

The artifact is `1343` bytes, with the SHA-256 digest above.
Matching output alone does not establish byte-identical compiler reproduction.
The VM must emit `59 3f 2c 48 50 1b 18 32 15 4d 4b 3b 42 0f 44 30 17`
with a 37-step stderr receipt. The automated
`tests/test_versioned_example_corpus.py` checks stored hashes, VM behavior and
source-to-capsule recompilation with pinned local tools.

This teaching pair is not the required parametric challenge instance.
General C lowering, cross-backend hashing, and arbitrary binary streams remain
unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
