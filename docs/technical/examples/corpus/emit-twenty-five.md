# Emit twenty-five distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-twenty-five-v1` (fixed teaching example, not a generated
  challenge).
- Source: [`emit-twenty-five.c`](emit-twenty-five.c), SHA-256
  `64dcdaa83db80adbc87c3cb0ff76a1ef834cc60d367eff442f25c4dfeb37beb9`.
- Guest artifact: [`emit-twenty-five.malbolge`](emit-twenty-five.malbolge),
  SHA-256
  `2d58c920bb132efe10668d4f6035bdf8ed988c2114323f7ac859277ac2579683`.
- Target: `malbolge-2026`, current 15-trit profile, in an extended
  `.malbolge` `MALBCAP1` capsule, not classic raw Malbolge source.
- Compiler: repository `c2malbolge.py` pipeline, LLVM 22.1.8 native C
  frontend, `c2malbolge_json` and `malbolge_layout` Rust executables.
  Generated on 2026-11-04 against compiler source commit `6ccbbae4f`;
  local binary provenance is not independently attested. Recompilation
  verifies bytes.
- Input: none. Guest output: bytes
  `51 3e 35 38 54 1f 4e 33 3d 39 05 53 23 1b b5 2c cb 12 c6 2e af b4 f8 ca 0e`,
  no newline.
  US (`1f`), ENQ (`05`), ESC (`1b`), DC2 (`12`) and SO (`0e`)
  are control bytes; thirteen are printable ASCII and seven have
  their high bit set.

Twenty-five source-proven C `putchar` calls yield twenty-two disjoint
guest `CrazyData` writes and three `RotateData` writes at the eighth,
fifteenth and twenty-second arithmetic positions. Twenty-six leading
no-ops place relocation at source position twenty-six; twenty-seven
reached trailing no-ops precede the halt. All guest data writes remain
outside code cells.
The normative profile VM independently verifies twenty-five distinct
binary output bytes, not host C execution or a general byte-stream API.

## Reproduce from the repository root

Build the repository-pinned frontend and debug compiler/VM executables using
[CLI build instructions][cli-build]. Use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-twenty-five-v1 --capsule \
  --output .temp/emit-twenty-five-v1-check.malbolge \
  docs/technical/examples/corpus/emit-twenty-five.c
sha256sum .temp/emit-twenty-five-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-twenty-five.malbolge \
  .temp/emit-twenty-five-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-twenty-five.malbolge \
  --report-steps | od -An -tx1
```

For unframed graphical source, omit `--capsule` and select the modern target
profile explicitly when running it:

```sh
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-twenty-five-v1 \
  --output .temp/emit-twenty-five-v1-raw.malbolge \
  docs/technical/examples/corpus/emit-twenty-five.c
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools .temp/emit-twenty-five-v1-raw.malbolge \
  --raw-profile malbolge-2026 --report-steps | od -An -tx1
```

The artifact is `1887` bytes, with the SHA-256 digest above.
Matching output alone does not establish byte-identical compiler reproduction.
The VM must emit
`51 3e 35 38 54 1f 4e 33 3d 39 05 53 23 1b b5 2c cb 12 c6 2e af b4 f8 ca 0e`
with a 105-step stderr receipt. The automated
`tests/test_versioned_example_corpus.py` checks stored hashes, VM behavior and
source-to-capsule recompilation with pinned local tools.

This teaching pair is not the required parametric challenge instance.
General C lowering, cross-backend hashing, and arbitrary binary streams remain
unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
