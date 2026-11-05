# Emit twenty-three distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-twenty-three-v1` (fixed teaching example, not a generated
  challenge).
- Source: [`emit-twenty-three.c`](emit-twenty-three.c), SHA-256
  `6df4c2a4e60d238b7dc6bb3201a9ec739fc1e0b5a08d751b5c8916062ee3b662`.
- Guest artifact: [`emit-twenty-three.malbolge`](emit-twenty-three.malbolge),
  SHA-256
  `6a4351b4fb7afc894fca6ac00790b97de44db6150ffd955c13a5462ba08b8f66`.
- Target: `malbolge-2026`, current 15-trit profile, in an extended
  `.malbolge` `MALBCAP1` capsule, not classic raw Malbolge source.
- Compiler: repository `c2malbolge.py` pipeline, LLVM 22.1.8 native C
  frontend, `c2malbolge_json` and `malbolge_layout` Rust executables.
  Generated on 2026-11-04 against compiler source commit `1e2462556`;
  local binary provenance is not independently attested. Recompilation
  verifies bytes.
- Input: none. Guest output: bytes
  `42 0e 2f 17 39 04 8e 24 9f 1b a0 23 97 15 28 27 29 14 32 1e 8b 26 92`,
  no newline.
  SO (`0e`), ETB (`17`), EOT (`04`), ESC (`1b`), NAK (`15`), DC4 (`14`)
  and RS (`1e`) are control bytes; ten are printable ASCII and six
  have their high bit set.
- Guest execution: 57 VM steps; stderr `malbolge-steps-v1:57`.

Twenty-three source-proven C `putchar` calls yield twenty disjoint guest
`CrazyData` writes and three `RotateData` writes at the seventh, fourteenth
and twenty-first arithmetic positions. Eight leading no-ops place relocation
at position eight. One reached trailing no-op precedes the halt. All guest
data writes remain outside the code cells.
The normative profile VM independently verifies twenty-three distinct
binary output bytes, not host C execution or a general byte-stream API.

## Reproduce from the repository root

Build the repository-pinned frontend and debug compiler/VM executables using
[CLI build instructions][cli-build]. Use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-twenty-three-v1 --capsule \
  --output .temp/emit-twenty-three-v1-check.malbolge \
  docs/technical/examples/corpus/emit-twenty-three.c
sha256sum .temp/emit-twenty-three-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-twenty-three.malbolge \
  .temp/emit-twenty-three-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-twenty-three.malbolge \
  --report-steps | od -An -tx1
```

For unframed graphical source, omit `--capsule` and select the modern target
profile explicitly when running it:

```sh
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-twenty-three-v1 \
  --output .temp/emit-twenty-three-v1-raw.malbolge \
  docs/technical/examples/corpus/emit-twenty-three.c
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools .temp/emit-twenty-three-v1-raw.malbolge \
  --raw-profile malbolge-2026 --report-steps | od -An -tx1
```

The artifact is `1503` bytes, with the SHA-256 digest above.
Matching output alone does not establish byte-identical compiler reproduction.
The VM must emit
`42 0e 2f 17 39 04 8e 24 9f 1b a0 23 97 15 28 27 29 14 32 1e 8b 26 92`
with a 57-step stderr receipt. The automated
`tests/test_versioned_example_corpus.py` checks stored hashes, VM behavior and
source-to-capsule recompilation with pinned local tools.

This teaching pair is not the required parametric challenge instance.
General C lowering, cross-backend hashing, and arbitrary binary streams remain
unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
