# Emit twelve distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-twelve-v1` (fixed teaching example, not a generated
  challenge).
- Source: [`emit-twelve.c`](emit-twelve.c), SHA-256
  `f5e8963f704c59cc34e15b217d30f69c2b1816c1bf1e5b20369392b3b1085fc7`.
- Guest artifact: [`emit-twelve.malbolge`](emit-twelve.malbolge), SHA-256
  `5bc03bb8ce1d9ab95a9aad99d387d4752f148c5be30dcab7919ffd53fbc52a34`.
- Target: `malbolge-2026`, current 15-trit profile, in an extended
  `.malbolge` `MALBCAP1` capsule, not classic raw Malbolge source.
- Compiler: repository `c2malbolge.py` pipeline, LLVM 22.1.8 native C
  frontend, `c2malbolge_json` and `malbolge_layout` Rust executables.
  Generated on 2026-11-04 against source commit `b65aa07dd`;
  local binary provenance is not independently attested. Recompilation
  verifies bytes.
- Input: none. Guest output: bytes `51 37 34 38 fb ce 9f 98 b8 b4 83 cd`,
  no newline. The eight high-bit values must not be decoded as UTF-8 text.
- Guest execution: 27 VM steps; stderr `malbolge-steps-v1:27`.

Twelve distinct C `putchar` calls yield eleven CrazyData effects and one
RotateData effect on disjoint guest words. This is real binary output
verified by the normative profile VM, not host C execution or a general
byte-stream API.

## Reproduce from the repository root

Build the repository-pinned frontend and debug compiler/VM executables using
[CLI build instructions][cli-build]. Use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-twelve-v1 --capsule \
  --output .temp/emit-twelve-v1-check.malbolge \
  docs/technical/examples/corpus/emit-twelve.c
sha256sum .temp/emit-twelve-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-twelve.malbolge \
  .temp/emit-twelve-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-twelve.malbolge \
  --report-steps | od -An -tx1
```

For unframed graphical source, omit `--capsule` and select the modern target
profile explicitly when running it:

```sh
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-twelve-v1 \
  --output .temp/emit-twelve-v1-raw.malbolge \
  docs/technical/examples/corpus/emit-twelve.c
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools .temp/emit-twelve-v1-raw.malbolge \
  --raw-profile malbolge-2026 --report-steps | od -An -tx1
```

The artifact is `1263` bytes, with the SHA-256 digest above.
Matching output alone does not establish byte-identical compiler reproduction.
The VM must emit `51 37 34 38 fb ce 9f 98 b8 b4 83 cd` with the 27-step
stderr receipt. The automated `tests/test_versioned_example_corpus.py`
checks stored hashes, VM behavior and source-to-capsule recompilation with
pinned local tools.

This teaching pair is not the required parametric challenge instance.
General C lowering, cross-backend hashing, and arbitrary binary streams remain
unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
