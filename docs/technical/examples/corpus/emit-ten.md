# Emit Q, quote, and eight high-bit bytes — version 1

## Identity and scope

- Example ID: `emit-ten-v1` (fixed teaching example, not a generated
  challenge).
- Source: [`emit-ten.c`](emit-ten.c), SHA-256
  `eeacae21350d6c88dbfbd8be4b1d1294e04be60868324463b8a97e24a5553675`.
- Guest artifact: [`emit-ten.malbolge`](emit-ten.malbolge), SHA-256
  `7befd3c590d03e94889bc93348bb37c51358f4b719dc2f371e07f918130386b0`.
- Target: `malbolge-2026`, current 15-trit profile, in an extended
  `.malbolge` `MALBCAP1` capsule, not classic raw Malbolge source.
- Compiler: repository `c2malbolge.py` pipeline, LLVM 22.1.8 native C
  frontend, `c2malbolge_json` and `malbolge_layout` Rust executables.
  Generated on 2026-11-04 against source commit `142fb9bbc`;
  local binary provenance is not independently attested. Recompilation
  verifies bytes.
- Input: none. Guest output: bytes `51 22 fd ce a5 98 ba b6 87 cb`, no newline.
  Eight bytes have the high bit set; they must not be decoded as UTF-8 text.
- Guest execution: 23 VM steps; stderr `malbolge-steps-v1:23`.

Ten distinct C `putchar` calls yield nine CrazyData effects and one
RotateData effect on disjoint guest words. This is real binary
output verified by the normative profile VM, not host C execution or a
general byte-stream API.

## Reproduce from the repository root

Build the repository-pinned frontend and debug compiler/VM executables using
the [CLI build instructions][cli-build]. Use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-ten-v1 --capsule \
  --output .temp/emit-ten-v1-check.malbolge \
  docs/technical/examples/corpus/emit-ten.c
sha256sum .temp/emit-ten-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-ten.malbolge \
  .temp/emit-ten-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-ten.malbolge \
  --report-steps | od -An -tx1
```

For unframed, graphical source, omit `--capsule` and explicitly select
the modern target profile when running it:

```sh
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-ten-v1 \
  --output .temp/emit-ten-v1-raw.malbolge \
  docs/technical/examples/corpus/emit-ten.c
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools .temp/emit-ten-v1-raw.malbolge \
  --raw-profile malbolge-2026 --report-steps | od -An -tx1
```

The artifact is `1231` bytes, with the SHA-256 digest above.
Matching output alone does not establish byte-identical compiler reproduction.
The VM must emit `51 22 fd ce a5 98 ba b6 87 cb` with the 23-step stderr
receipt. The automated `tests/test_versioned_example_corpus.py` checks
stored hashes, VM behavior, and source-to-capsule recompilation with pinned
local tools.

This teaching pair is not the required parametric challenge instance.
General C lowering, cross-backend hashing, and arbitrary binary streams remain
unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
