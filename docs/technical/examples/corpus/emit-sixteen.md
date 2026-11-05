# Emit sixteen distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-sixteen-v1` (fixed teaching example, not a generated
  challenge).
- Source: [`emit-sixteen.c`](emit-sixteen.c), SHA-256
  `e49132f84f6a2afff02dd289f1e0844325e0fe6bf372fcb39ebac4b5f1dd6a72`.
- Guest artifact: [`emit-sixteen.malbolge`](emit-sixteen.malbolge), SHA-256
  `74ad2a4f6cb71221199a1bbeaa79feb8639c10d0646f697442c42aea96d5b094`.
- Target: `malbolge-2026`, current 15-trit profile, in an extended
  `.malbolge` `MALBCAP1` capsule, not classic raw Malbolge source.
- Compiler: repository `c2malbolge.py` pipeline, LLVM 22.1.8 native C
  frontend, `c2malbolge_json` and `malbolge_layout` Rust executables.
  Generated on 2026-11-04 against compiler source commit `621ead262`;
  local binary provenance is not independently attested. Recompilation
  verifies bytes.
- Input: none. Guest output: bytes
  `3f 49 36 13 5a 0a ba b3 c3 86 cc aa 01 07 d5 c5`, no newline.
  DC3 (`13`), LF (`0a`), SOH (`01`), and BEL (`07`) are control bytes;
  eight values have their high bit set.
- Guest execution: 35 VM steps; stderr `malbolge-steps-v1:35`.

Sixteen source-proven C `putchar` calls yield thirteen disjoint guest
`CrazyData` writes and three `RotateData` writes at the sixth, thirteenth,
and fourteenth arithmetic positions. The normative profile VM independently
verifies sixteen distinct output bytes, not host C execution or a general
byte-stream API.

## Reproduce from the repository root

Build the repository-pinned frontend and debug compiler/VM executables using
[CLI build instructions][cli-build]. Use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-sixteen-v1 --capsule \
  --output .temp/emit-sixteen-v1-check.malbolge \
  docs/technical/examples/corpus/emit-sixteen.c
sha256sum .temp/emit-sixteen-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-sixteen.malbolge \
  .temp/emit-sixteen-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-sixteen.malbolge \
  --report-steps | od -An -tx1
```

For unframed graphical source, omit `--capsule` and select the modern target
profile explicitly when running it:

```sh
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-sixteen-v1 \
  --output .temp/emit-sixteen-v1-raw.malbolge \
  docs/technical/examples/corpus/emit-sixteen.c
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools .temp/emit-sixteen-v1-raw.malbolge \
  --raw-profile malbolge-2026 --report-steps | od -An -tx1
```

The artifact is `1327` bytes, with the SHA-256 digest above.
Matching output alone does not establish byte-identical compiler reproduction.
The VM must emit `3f 49 36 13 5a 0a ba b3 c3 86 cc aa 01 07 d5 c5` with a
35-step stderr receipt. The automated `tests/test_versioned_example_corpus.py`
checks stored hashes, VM behavior and source-to-capsule recompilation with
pinned local tools.

This teaching pair is not the required parametric challenge instance.
General C lowering, cross-backend hashing, and arbitrary binary streams remain
unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
