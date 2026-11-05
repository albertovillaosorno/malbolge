# Emit fifteen distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-fifteen-v1` (fixed teaching example, not a generated
  challenge).
- Source: [`emit-fifteen.c`](emit-fifteen.c), SHA-256
  `a82eecdcfc33fafa28e365d3d8a9792c649f2edd65d23d90d33ea8ecf04e801c`.
- Guest artifact: [`emit-fifteen.malbolge`](emit-fifteen.malbolge), SHA-256
  `c69df83c4073806ef27c976de1a029a9f550ad7937e3432a7bda0908a8b58d9b`.
- Target: `malbolge-2026`, current 15-trit profile, in an extended
  `.malbolge` `MALBCAP1` capsule, not classic raw Malbolge source.
- Compiler: repository `c2malbolge.py` pipeline, LLVM 22.1.8 native C
  frontend, `c2malbolge_json` and `malbolge_layout` Rust executables.
  Generated on 2026-11-04 against compiler source commit `ae460796a`;
  local binary provenance is not independently attested. Recompilation
  verifies bytes.
- Input: none. Guest output: bytes
  `51 2e 19 38 3e 89 d2 ad a3 b7 c8 88 08 d5 c6`, no newline.
  EM (`19`) and BS (`08`) are control bytes; nine values have
  their high bit set.
- Guest execution: 33 VM steps; stderr `malbolge-steps-v1:33`.

Fifteen source-proven C `putchar` calls yield thirteen disjoint guest
`CrazyData` writes and two `RotateData` writes at the sixth and thirteenth
arithmetic positions. The normative profile VM independently verifies
fifteen distinct output bytes, not host C execution or a general byte-stream
API.

## Reproduce from the repository root

Build the repository-pinned frontend and debug compiler/VM executables using
[CLI build instructions][cli-build]. Use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-fifteen-v1 --capsule \
  --output .temp/emit-fifteen-v1-check.malbolge \
  docs/technical/examples/corpus/emit-fifteen.c
sha256sum .temp/emit-fifteen-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-fifteen.malbolge \
  .temp/emit-fifteen-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-fifteen.malbolge \
  --report-steps | od -An -tx1
```

For unframed graphical source, omit `--capsule` and select the modern target
profile explicitly when running it:

```sh
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-fifteen-v1 \
  --output .temp/emit-fifteen-v1-raw.malbolge \
  docs/technical/examples/corpus/emit-fifteen.c
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools .temp/emit-fifteen-v1-raw.malbolge \
  --raw-profile malbolge-2026 --report-steps | od -An -tx1
```

The artifact is `1311` bytes, with the SHA-256 digest above.
Matching output alone does not establish byte-identical compiler reproduction.
The VM must emit `51 2e 19 38 3e 89 d2 ad a3 b7 c8 88 08 d5 c6` with a
33-step stderr receipt. The automated `tests/test_versioned_example_corpus.py`
checks stored hashes, VM behavior and source-to-capsule recompilation with
pinned local tools.

This teaching pair is not the required parametric challenge instance.
General C lowering, cross-backend hashing, and arbitrary binary streams remain
unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
