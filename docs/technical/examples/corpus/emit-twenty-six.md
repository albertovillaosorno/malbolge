# Emit twenty-six distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-twenty-six-v1` (fixed teaching example, not a generated
  challenge).
- Source: [`emit-twenty-six.c`](emit-twenty-six.c), SHA-256
  `d43d8cfc015160c9e6b26ec14b23cea1931d9d5f7968bdfa334da25dcc1bcea8`.
- Guest artifact: [`emit-twenty-six.malbolge`](emit-twenty-six.malbolge),
  SHA-256
  `ee6f2e7133685a4c913c2cc2a6ba54664f34ab8f5f6a0623b63caf84bd81c586`.
- Target: `malbolge-2026`, current 15-trit profile, in an extended
  `.malbolge` `MALBCAP1` capsule, not classic raw Malbolge source.
- Compiler: repository `c2malbolge.py` pipeline, LLVM 22.1.8 native C
  frontend, `c2malbolge_json` and `malbolge_layout` Rust executables.
  Generated on 2026-11-04 against compiler source commit `4edd28763`;
  local binary provenance is not independently attested. Recompilation
  verifies bytes.
- Input: none. Guest output: bytes
  `51 3e 35 38 54 1f 4e 33 3d 39 05 53 23 1b b5 2c cb 12 c6 2e af b4 f8 ca 0e 95`,
  no newline.
  US (`1f`), ENQ (`05`), ESC (`1b`), DC2 (`12`) and SO (`0e`)
  are control bytes; thirteen are printable ASCII and eight have
  their high bit set.

Twenty-six source-proven C `putchar` calls yield twenty-three disjoint
guest `CrazyData` writes and three `RotateData` writes at the eighth,
fifteenth and twenty-second arithmetic positions. Twenty-six leading
no-ops place relocation at source position twenty-six; twenty-five
reached trailing no-ops precede the halt. All guest data writes remain
outside code cells.
The normative profile VM independently verifies twenty-six distinct
binary output bytes, not host C execution or a general byte-stream API.

## Reproduce from the repository root

Build the repository-pinned frontend and debug compiler/VM executables using
[CLI build instructions][cli-build]. Use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-twenty-six-v1 --capsule \
  --output .temp/emit-twenty-six-v1-check.malbolge \
  docs/technical/examples/corpus/emit-twenty-six.c
sha256sum .temp/emit-twenty-six-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-twenty-six.malbolge \
  .temp/emit-twenty-six-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-twenty-six.malbolge \
  --report-steps | od -An -tx1
```

For unframed graphical source, omit `--capsule` and select the modern target
profile explicitly when running it:

```sh
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-twenty-six-v1 \
  --output .temp/emit-twenty-six-v1-raw.malbolge \
  docs/technical/examples/corpus/emit-twenty-six.c
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools .temp/emit-twenty-six-v1-raw.malbolge \
  --raw-profile malbolge-2026 --report-steps | od -An -tx1
```

The artifact is `1887` bytes, with the SHA-256 digest above.
Matching output alone does not establish byte-identical compiler reproduction.
The VM must emit
`51 3e 35 38 54 1f 4e 33 3d 39 05 53 23 1b b5 2c cb 12 c6 2e af b4 f8 ca 0e 95`
with a 105-step stderr receipt. The automated
`tests/test_versioned_example_corpus.py` checks stored hashes, VM behavior and
source-to-capsule recompilation with pinned local tools.

This teaching pair is not the required parametric challenge instance.
General C lowering, cross-backend hashing, and arbitrary binary streams remain
unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
