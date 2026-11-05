# Emit twenty-two distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-twenty-two-v1` (fixed teaching example, not a generated
  challenge).
- Source: [`emit-twenty-two.c`](emit-twenty-two.c), SHA-256
  `140a3ad6d13fefddfdc910fca0121a00f5a3fd0c262bb962108d3d694fdb1013`.
- Guest artifact: [`emit-twenty-two.malbolge`](emit-twenty-two.malbolge),
  SHA-256
  `8d65a853bf783a7af690f44aa04029838bf9056179eee1033c04ac972c0c1fdb`.
- Target: `malbolge-2026`, current 15-trit profile, in an extended
  `.malbolge` `MALBCAP1` capsule, not classic raw Malbolge source.
- Compiler: repository `c2malbolge.py` pipeline, LLVM 22.1.8 native C
  frontend, `c2malbolge_json` and `malbolge_layout` Rust executables.
  Generated on 2026-11-04 against compiler source commit `31cdf6236`;
  local binary provenance is not independently attested. Recompilation
  verifies bytes.
- Input: none. Guest output: bytes
  `39 16 37 05 41 0c 30 8e 24 9f 1b a0 23 97 15 28 27 29 14 32 1e 1f`,
  no newline.
  SYN (`16`), ENQ (`05`), FF (`0c`), ESC (`1b`), NAK (`15`),
  DC4 (`14`), RS (`1e`) and US (`1f`) are control bytes; ten are
  printable ASCII and four have their high bit set.
- Guest execution: 57 VM steps; stderr `malbolge-steps-v1:57`.

Twenty-two source-proven C `putchar` calls yield twenty disjoint guest
`CrazyData` writes and two `RotateData` writes at the eighth and fifteenth
arithmetic positions. Ten leading no-ops place relocation at position ten.
One reached trailing no-op precedes the halt. All guest data writes remain
outside the code cells.
The normative profile VM independently verifies twenty-two distinct
binary output bytes, not host C execution or a general byte-stream API.

## Reproduce from the repository root

Build the repository-pinned frontend and debug compiler/VM executables using
[CLI build instructions][cli-build]. Use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-twenty-two-v1 --capsule \
  --output .temp/emit-twenty-two-v1-check.malbolge \
  docs/technical/examples/corpus/emit-twenty-two.c
sha256sum .temp/emit-twenty-two-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-twenty-two.malbolge \
  .temp/emit-twenty-two-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-twenty-two.malbolge \
  --report-steps | od -An -tx1
```

For unframed graphical source, omit `--capsule` and select the modern target
profile explicitly when running it:

```sh
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-twenty-two-v1 \
  --output .temp/emit-twenty-two-v1-raw.malbolge \
  docs/technical/examples/corpus/emit-twenty-two.c
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools .temp/emit-twenty-two-v1-raw.malbolge \
  --raw-profile malbolge-2026 --report-steps | od -An -tx1
```

The artifact is `1503` bytes, with the SHA-256 digest above.
Matching output alone does not establish byte-identical compiler reproduction.
The VM must emit
`39 16 37 05 41 0c 30 8e 24 9f 1b a0 23 97 15 28 27 29 14 32 1e 1f`
with a 57-step stderr receipt. The automated
`tests/test_versioned_example_corpus.py` checks stored hashes, VM behavior and
source-to-capsule recompilation with pinned local tools.

This teaching pair is not the required parametric challenge instance.
General C lowering, cross-backend hashing, and arbitrary binary streams remain
unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
