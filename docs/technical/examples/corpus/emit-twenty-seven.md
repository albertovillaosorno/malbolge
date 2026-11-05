# Emit twenty-seven distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-twenty-seven-v1` (fixed teaching example, not a generated
  challenge).
- Source: [`emit-twenty-seven.c`](emit-twenty-seven.c), SHA-256
  `cc703648b791fd1d36131c1a373edba2ebd75c33517fead73531b50d1df5a518`.
- Guest artifact: [`emit-twenty-seven.malbolge`](emit-twenty-seven.malbolge),
  SHA-256
  `bd99663a6cef14f03546a72c4236a6849b35770733da141c652cf433da4f0ff9`.
- Target: `malbolge-2026`, current 15-trit profile, in an extended
  `.malbolge` `MALBCAP1` capsule, not classic raw Malbolge source.
- Compiler: repository `c2malbolge.py` pipeline, LLVM 22.1.8 native C
  frontend, `c2malbolge_json` and `malbolge_layout` Rust executables.
  Generated on 2026-11-04 against compiler source commit `bbd77ed04`;
  local binary provenance is not independently attested. Recompilation
  verifies bytes.
- Input: none. Guest output: bytes
  `51 3e 35 38 54 1f 4e 33 3d 39 05 53 23 1b b5 2c cb 12` followed by
  `c6 2e af b4 f8 ca 0e 95 2d`, no newline.
  US (`1f`), ENQ (`05`), ESC (`1b`), DC2 (`12`) and SO (`0e`)
  are control bytes; fourteen are printable ASCII and eight have
  their high bit set.

Twenty-seven source-proven C `putchar` calls yield twenty-four disjoint
guest `CrazyData` writes and three `RotateData` writes at the eighth,
fifteenth and twenty-second arithmetic positions. Twenty-seven leading
no-ops place relocation at source position twenty-seven; twenty-three
reached trailing no-ops precede the halt. All guest data writes remain
outside code cells.
The normative profile VM independently verifies twenty-seven distinct
binary output bytes, not host C execution or a general byte-stream API.

## Reproduce from the repository root

Build the repository-pinned frontend and debug compiler/VM executables using
[CLI build instructions][cli-build]. Use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-twenty-seven-v1 --capsule \
  --output .temp/emit-twenty-seven-v1-check.malbolge \
  docs/technical/examples/corpus/emit-twenty-seven.c
sha256sum .temp/emit-twenty-seven-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-twenty-seven.malbolge \
  .temp/emit-twenty-seven-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-twenty-seven.malbolge \
  --report-steps | od -An -tx1
```

For unframed graphical source, omit `--capsule` and select the modern target
profile explicitly when running it:

```sh
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-twenty-seven-v1 \
  --output .temp/emit-twenty-seven-v1-raw.malbolge \
  docs/technical/examples/corpus/emit-twenty-seven.c
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools .temp/emit-twenty-seven-v1-raw.malbolge \
  --raw-profile malbolge-2026 --report-steps | od -An -tx1
```

The artifact is `1887` bytes, with the SHA-256 digest above.
Matching output alone does not establish byte-identical compiler reproduction.
The VM must emit
`51 3e 35 38 54 1f 4e 33 3d 39 05 53 23 1b b5 2c cb 12` followed by
`c6 2e af b4 f8 ca 0e 95 2d` with a 105-step stderr receipt. The automated
`tests/test_versioned_example_corpus.py` checks stored hashes, VM behavior and
source-to-capsule recompilation with pinned local tools.

This teaching pair is not the required parametric challenge instance.
General C lowering, cross-backend hashing, and arbitrary binary streams remain
unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
