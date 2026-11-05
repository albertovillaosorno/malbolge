# Emit fourteen distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-fourteen-v1` (fixed teaching example, not a generated
  challenge).
- Source: [`emit-fourteen.c`](emit-fourteen.c), SHA-256
  `923b7245d13803ffbb1615b4f9684fd076a618f4e25d80861ab1e0fe2a807c14`.
- Guest artifact: [`emit-fourteen.malbolge`](emit-fourteen.malbolge), SHA-256
  `e3ea5ad67954382872f2f2a6dbd03dfb497a91a52a1fbe04d2aa92afd9e7b438`.
- Target: `malbolge-2026`, current 15-trit profile, in an extended
  `.malbolge` `MALBCAP1` capsule, not classic raw Malbolge source.
- Compiler: repository `c2malbolge.py` pipeline, LLVM 22.1.8 native C
  frontend, `c2malbolge_json` and `malbolge_layout` Rust executables.
  Generated on 2026-11-04 against compiler source commit `ad2bcfb41`;
  local binary provenance is not independently attested. Recompilation
  verifies bytes.
- Input: none. Guest output: bytes `59 45 2c 48 53 17 4c 4f 3d 40 5b 31 19 34`,
  no newline. ETB (`17`) and EM (`19`) are nonprinting binary control bytes.
- Guest execution: 31 VM steps; stderr `malbolge-steps-v1:31`.

Fourteen source-proven C `putchar` calls yield twelve disjoint guest
`CrazyData` writes and two `RotateData` writes at the sixth and thirteenth
arithmetic positions. The normative profile VM independently verifies
fourteen distinct output bytes, not host C execution or a general byte-stream
API.

## Reproduce from the repository root

Build the repository-pinned frontend and debug compiler/VM executables using
[CLI build instructions][cli-build]. Use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-fourteen-v1 --capsule \
  --output .temp/emit-fourteen-v1-check.malbolge \
  docs/technical/examples/corpus/emit-fourteen.c
sha256sum .temp/emit-fourteen-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-fourteen.malbolge \
  .temp/emit-fourteen-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-fourteen.malbolge \
  --report-steps | od -An -tx1
```

For unframed graphical source, omit `--capsule` and select the modern target
profile explicitly when running it:

```sh
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-fourteen-v1 \
  --output .temp/emit-fourteen-v1-raw.malbolge \
  docs/technical/examples/corpus/emit-fourteen.c
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools .temp/emit-fourteen-v1-raw.malbolge \
  --raw-profile malbolge-2026 --report-steps | od -An -tx1
```

The artifact is `1295` bytes, with the SHA-256 digest above.
Matching output alone does not establish byte-identical compiler reproduction.
The VM must emit `59 45 2c 48 53 17 4c 4f 3d 40 5b 31 19 34` with a
31-step stderr receipt. The automated `tests/test_versioned_example_corpus.py`
checks stored hashes, VM behavior and source-to-capsule recompilation with
pinned local tools.

This teaching pair is not the required parametric challenge instance.
General C lowering, cross-backend hashing, and arbitrary binary streams remain
unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
