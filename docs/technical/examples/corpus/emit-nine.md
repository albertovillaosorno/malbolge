# Emit T, =, and seven high-bit bytes — version 1

## Identity and scope

- Example ID: `emit-nine-v1` (fixed teaching example, not a generated
  challenge).
- Source: [`emit-nine.c`](emit-nine.c), SHA-256
  `45229743a0d515e503b190695307694985a7ba47c2dc74f616839e8bf680f430`.
- Guest artifact: [`emit-nine.malbolge`](emit-nine.malbolge), SHA-256
  `1d09fccde1f7d346ebc7e72439b82544da2dda37ff2a6e93b020996189e7bbeb`.
- Target: `malbolge-2026`, current 15-trit profile, in an extended
  `.malbolge` `MALBCAP1` capsule, not classic raw Malbolge source.
- Compiler: repository `c2malbolge.py` pipeline, LLVM 22.1.8 native C
  frontend, `c2malbolge_json` and `malbolge_layout` Rust executables.
  Generated on 2026-11-04 against source commit `d43bd4648`;
  local binary provenance is not independently attested. Recompilation
  verifies bytes.
- Input: none. Guest output: bytes `54 3d 8d d1 c0 b4 bf d2 a2`, no newline.
  Seven bytes have the high bit set; they must not be decoded as UTF-8 text.
- Guest execution: 21 VM steps; stderr `malbolge-steps-v1:21`.

Nine distinct C `putchar` calls yield eight CrazyData effects and one
RotateData effect on disjoint guest words. This is real binary
output verified by the normative profile VM, not host C execution or a
general byte-stream API.

## Reproduce from the repository root

Build the repository-pinned frontend and debug compiler/VM executables using
the [CLI build instructions][cli-build]. Use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-nine-v1 --capsule \
  --output .temp/emit-nine-v1-check.malbolge \
  docs/technical/examples/corpus/emit-nine.c
sha256sum .temp/emit-nine-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-nine.malbolge \
  .temp/emit-nine-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-nine.malbolge \
  --report-steps | od -An -tx1
```

For unframed, graphical source, omit `--capsule` and explicitly select
the modern target profile when running it:

```sh
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-nine-v1 \
  --output .temp/emit-nine-v1-raw.malbolge \
  docs/technical/examples/corpus/emit-nine.c
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools .temp/emit-nine-v1-raw.malbolge \
  --raw-profile malbolge-2026 --report-steps | od -An -tx1
```

The artifact is `1215` bytes, with the SHA-256 digest above.
Matching output alone does not establish byte-identical compiler reproduction.
The VM must emit `54 3d 8d d1 c0 b4 bf d2 a2` with the 21-step stderr
receipt. The automated `tests/test_versioned_example_corpus.py` checks
stored hashes, VM behavior, and source-to-capsule recompilation with pinned
local tools.

This teaching pair is not the required parametric challenge instance.
General C lowering, cross-backend hashing, and arbitrary binary streams remain
unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
