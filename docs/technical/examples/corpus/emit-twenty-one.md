# Emit twenty-one distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-twenty-one-v1` (fixed teaching example, not a generated
  challenge).
- Source: [`emit-twenty-one.c`](emit-twenty-one.c), SHA-256
  `221655ff1f398b6745e2174e611b554c479b3c278a6069e14c1ac6f32e70d26c`.
- Guest artifact: [`emit-twenty-one.malbolge`](emit-twenty-one.malbolge),
  SHA-256
  `4d5bc3b62c7525898863d2a3b9dae6f62f8700ab6ae6f3557425896c9f6f661d`.
- Target: `malbolge-2026`, current 15-trit profile, in an extended
  `.malbolge` `MALBCAP1` capsule, not classic raw Malbolge source.
- Compiler: repository `c2malbolge.py` pipeline, LLVM 22.1.8 native C
  frontend, `c2malbolge_json` and `malbolge_layout` Rust executables.
  Generated on 2026-11-04 against compiler source commit `e615351f7`;
  local binary provenance is not independently attested. Recompilation
  verifies bytes.
- Input: none. Guest output: bytes
  `41 0e 3b 0f 3f 0a 40 8e 26 92 27 96 22 97 8d 15 31 18 35 1a 2f`, no newline.
  SO (`0e`), SI (`0f`), LF (`0a`), NAK (`15`), CAN (`18`) and
  SUB (`1a`) are control bytes; ten bytes are printable ASCII and five
  have their high bit set.
- Guest execution: 60 VM steps; stderr `malbolge-steps-v1:60`.

Twenty-one source-proven C `putchar` calls yield eighteen disjoint guest
`CrazyData` writes and three `RotateData` writes at the eighth, fifteenth
and sixteenth arithmetic positions. Fifteen leading no-ops place relocation
at position fifteen; one reached trailing no-op precedes the halt. All data
writes remain outside the code cells.
The normative profile VM independently verifies twenty-one distinct
binary output bytes, not host C execution or a general byte-stream API.

## Reproduce from the repository root

Build the repository-pinned frontend and debug compiler/VM executables using
[CLI build instructions][cli-build]. Use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-twenty-one-v1 --capsule \
  --output .temp/emit-twenty-one-v1-check.malbolge \
  docs/technical/examples/corpus/emit-twenty-one.c
sha256sum .temp/emit-twenty-one-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-twenty-one.malbolge \
  .temp/emit-twenty-one-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-twenty-one.malbolge \
  --report-steps | od -An -tx1
```

For unframed graphical source, omit `--capsule` and select the modern target
profile explicitly when running it:

```sh
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-twenty-one-v1 \
  --output .temp/emit-twenty-one-v1-raw.malbolge \
  docs/technical/examples/corpus/emit-twenty-one.c
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools .temp/emit-twenty-one-v1-raw.malbolge \
  --raw-profile malbolge-2026 --report-steps | od -An -tx1
```

The artifact is `1527` bytes, with the SHA-256 digest above.
Matching output alone does not establish byte-identical compiler reproduction.
The VM must emit
`41 0e 3b 0f 3f 0a 40 8e 26 92 27 96 22 97 8d 15 31 18 35 1a 2f`
with a 60-step stderr receipt. The automated
`tests/test_versioned_example_corpus.py` checks stored hashes, VM behavior and
source-to-capsule recompilation with pinned local tools.

This teaching pair is not the required parametric challenge instance.
General C lowering, cross-backend hashing, and arbitrary binary streams remain
unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
