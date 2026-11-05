# Emit twenty-nine distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-twenty-nine-v1` (fixed teaching example, not a generated
  challenge).
- Source: [`emit-twenty-nine.c`](emit-twenty-nine.c), SHA-256
  `4262ba655782c6678cc266922e23086dd397232afe6b41196492c3919f81c6e3`.
- Guest artifact: [`emit-twenty-nine.malbolge`](emit-twenty-nine.malbolge),
  SHA-256
  `0066976f557e119fa30b580fe6c73018dd4ca922700a7796a59d0acea2f46d26`.
- Target: `malbolge-2026`, current 15-trit profile, in an extended
  `.malbolge` `MALBCAP1` capsule, not classic raw Malbolge source.
- Compiler: repository `c2malbolge.py` pipeline, LLVM 22.1.8 native C
  frontend, `c2malbolge_json` and `malbolge_layout` Rust executables.
  Generated on 2026-11-04 against compiler source commit `e70b372d2`;
  local binary provenance is not independently attested. Recompilation
  verifies bytes.
- Input: none. Guest output: bytes
  `87 b7 bc b1 8a ce 9f 9c b5 2c cb 12 c6 2e af b4 f8 ca` followed by
  `0e 95 2d ab 33 3d 39 05 53 23 1b`, no newline. Eight bytes are
  printable ASCII, four are controls and seventeen have their high bit set.

Twenty-nine source-proven C `putchar` calls yield twenty-five disjoint guest
`CrazyData` writes and four `RotateData` writes at arithmetic indices zero,
eight, fifteen and twenty-two. Nine leading no-ops place the first data
relocation; one reached no-op separates the first and second arithmetic
pairs. The 105-step normative VM writes only to data cells outside the
105-cell source. The VM independently verifies all twenty-nine distinct
binary output bytes, not host C execution or a general byte-stream API.

## Reproduce from the repository root

Build the repository-pinned frontend and debug compiler/VM executables using
[CLI build instructions][cli-build]. Use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-twenty-nine-v1 --capsule \
  --output .temp/emit-twenty-nine-v1-check.malbolge \
  docs/technical/examples/corpus/emit-twenty-nine.c
sha256sum .temp/emit-twenty-nine-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-twenty-nine.malbolge \
  .temp/emit-twenty-nine-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-twenty-nine.malbolge \
  --report-steps | od -An -tx1
```

For unframed graphical source, omit `--capsule` and select the modern target
profile explicitly when running it:

```sh
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-twenty-nine-v1 \
  --output .temp/emit-twenty-nine-v1-raw.malbolge \
  docs/technical/examples/corpus/emit-twenty-nine.c
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools .temp/emit-twenty-nine-v1-raw.malbolge \
  --raw-profile malbolge-2026 --report-steps | od -An -tx1
```

The capsule is `1887` bytes, with the SHA-256 digest above.
Matching output alone does not establish byte-identical compiler reproduction.
The VM must emit the exact 29-byte sequence above with a 105-step stderr
receipt. The automated `tests/test_versioned_example_corpus.py` checks stored
hashes, VM behavior and source-to-capsule recompilation with pinned local tools.

This teaching pair is not the required parametric challenge instance.
General C lowering, cross-backend hashing, and arbitrary binary streams remain
unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
