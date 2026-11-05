# Emit nineteen distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-nineteen-v1` (fixed teaching example, not a generated
  challenge).
- Source: [`emit-nineteen.c`](emit-nineteen.c), SHA-256
  `9fe717e9e002dee994ece2089602b5c8813edc23f364f37e6424d823a903d9fa`.
- Guest artifact: [`emit-nineteen.malbolge`](emit-nineteen.malbolge), SHA-256
  `7836c69e89d97d7d82b1fcec171199e34a1223a2f239447e62f696737ced1379`.
- Target: `malbolge-2026`, current 15-trit profile, in an extended
  `.malbolge` `MALBCAP1` capsule, not classic raw Malbolge source.
- Compiler: repository `c2malbolge.py` pipeline, LLVM 22.1.8 native C
  frontend, `c2malbolge_json` and `malbolge_layout` Rust executables.
  Generated on 2026-11-04 against compiler source commit
  `a53740a77`; local binary provenance is not independently
  attested. Recompilation verifies bytes.
- Input: none. Guest output: bytes
  `53 21 1a 3c 38 03 17 55 0e 49 2b 10 46 16 40 4c 3a 19 58`, no newline.
  SUB (`1a`), ETX (`03`), ETB (`17`), SO (`0e`), DLE (`10`), SYN (`16`)
  and EM (`19`) are control bytes; the other twelve are printable ASCII.
- Guest execution: 40 VM steps; stderr `malbolge-steps-v1:40`.

Nineteen source-proven C `putchar` calls yield sixteen disjoint guest
`CrazyData` writes and three `RotateData` writes at the seventh, ninth, and
fourteenth arithmetic positions. The normative profile VM independently
verifies nineteen distinct output bytes, not host C execution or a general
byte-stream API.

## Reproduce from the repository root

Build the repository-pinned frontend and debug compiler/VM executables using
[CLI build instructions][cli-build]. Use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-nineteen-v1 --capsule \
  --output .temp/emit-nineteen-v1-check.malbolge \
  docs/technical/examples/corpus/emit-nineteen.c
sha256sum .temp/emit-nineteen-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-nineteen.malbolge \
  .temp/emit-nineteen-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-nineteen.malbolge \
  --report-steps | od -An -tx1
```

For unframed graphical source, omit `--capsule` and select the modern target
profile explicitly when running it:

```sh
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-nineteen-v1 \
  --output .temp/emit-nineteen-v1-raw.malbolge \
  docs/technical/examples/corpus/emit-nineteen.c
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools .temp/emit-nineteen-v1-raw.malbolge \
  --raw-profile malbolge-2026 --report-steps | od -An -tx1
```

The artifact is `1367` bytes, with the SHA-256 digest above.
Matching output alone does not establish byte-identical compiler reproduction.
The VM must emit `53 21 1a 3c 38 03 17 55 0e 49 2b 10 46 16 40 4c 3a 19 58`
with a 40-step stderr receipt. The automated
`tests/test_versioned_example_corpus.py` checks stored hashes, VM behavior and
source-to-capsule recompilation with pinned local tools.

This teaching pair is not the required parametric challenge instance.
General C lowering, cross-backend hashing, and arbitrary binary streams remain
unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
