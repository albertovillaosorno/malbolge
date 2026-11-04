# Emit eleven distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-eleven-v1` (fixed teaching example, not a generated
  challenge).
- Source: [`emit-eleven.c`](emit-eleven.c), SHA-256
  `4a42a412d63b0131f9d6c613b4f6dedca7fc2a01fd94433add89e5c873853c39`.
- Guest artifact: [`emit-eleven.malbolge`](emit-eleven.malbolge), SHA-256
  `6b7381c638e959fa3f1cca6376317340c4278c4611bc518aa54b4ce2fcc6d8af`.
- Target: `malbolge-2026`, current 15-trit profile, in an extended
  `.malbolge` `MALBCAP1` capsule, not classic raw Malbolge source.
- Compiler: repository `c2malbolge.py` pipeline, LLVM 22.1.8 native C
  frontend, `c2malbolge_json` and `malbolge_layout` Rust executables.
  Generated on 2026-11-04 against source commit `17657a218`;
  local binary provenance is not independently attested. Recompilation
  verifies bytes.
- Input: none. Guest output: bytes `50 1d 1a 36 05 b4 ba b3 84 cf 9e`,
  no newline. The sequence includes GS, SUB, ENQ and six high-bit values;
  it must not be decoded as UTF-8 text.
- Guest execution: 24 VM steps; stderr `malbolge-steps-v1:24`.

Eleven distinct C `putchar` calls yield ten CrazyData effects and one
RotateData effect on disjoint guest words. This is real binary output
verified by the normative profile VM, not host C execution or a general
byte-stream API.

## Reproduce from the repository root

Build the repository-pinned frontend and debug compiler/VM executables using
the [CLI build instructions][cli-build]. Use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-eleven-v1 --capsule \
  --output .temp/emit-eleven-v1-check.malbolge \
  docs/technical/examples/corpus/emit-eleven.c
sha256sum .temp/emit-eleven-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-eleven.malbolge \
  .temp/emit-eleven-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-eleven.malbolge \
  --report-steps | od -An -tx1
```

For unframed, graphical source, omit `--capsule` and explicitly select
the modern target profile when running it:

```sh
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-eleven-v1 \
  --output .temp/emit-eleven-v1-raw.malbolge \
  docs/technical/examples/corpus/emit-eleven.c
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools .temp/emit-eleven-v1-raw.malbolge \
  --raw-profile malbolge-2026 --report-steps | od -An -tx1
```

The artifact is `1239` bytes, with the SHA-256 digest above.
Matching output alone does not establish byte-identical compiler reproduction.
The VM must emit `50 1d 1a 36 05 b4 ba b3 84 cf 9e` with the 24-step stderr
receipt. The automated `tests/test_versioned_example_corpus.py` checks
stored hashes, VM behavior, and source-to-capsule recompilation with pinned
local tools.

This teaching pair is not the required parametric challenge instance.
General C lowering, cross-backend hashing, and arbitrary binary streams remain
unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
