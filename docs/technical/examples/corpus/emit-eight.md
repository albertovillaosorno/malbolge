# Emit S, space, ETB, <, 6, SOH, R, ACK — version 1

## Identity and scope

- Example ID: `emit-eight-v1` (fixed teaching example, not a generated
  challenge).
- Source: [`emit-eight.c`](emit-eight.c), SHA-256
  `5971c3577e8087ed2a895790fefc2a8b3b4c931445c03a7d06de451e3e1fa711`.
- Guest artifact: [`emit-eight.malbolge`](emit-eight.malbolge), SHA-256
  `59106439d2b0c203a6f934952adcd10b1d0dae7049df62fb708da48203e8a578`.
- Target: `malbolge-2026`, current 15-trit profile, in an extended
  `.malbolge` `MALBCAP1` capsule, not classic raw Malbolge source.
- Compiler: repository `c2malbolge.py` pipeline, LLVM 22.1.8 native C
  frontend, `c2malbolge_json` and `malbolge_layout` Rust executables.
  Generated on 2026-11-04 against source commit `de1bcd762`;
  local binary provenance is not independently attested. Recompilation
  verifies bytes.
- Input: none. Guest output: bytes `53 20 17 3c 36 01 52 06`, no newline.
  `17`, `01`, and `06` are ETB, SOH, and ACK control codes; `20` is a space.
- Guest execution: 21 VM steps; stderr `malbolge-steps-v1:21`.

Eight distinct C `putchar` calls yield seven separately computed Malbolge
CrazyData effects and one RotateData effect. This is real binary output
verified by the normative profile VM, not host C execution or a general
byte-stream API.

## Reproduce from the repository root

Build the repository-pinned frontend and debug compiler/VM executables using
the [CLI build instructions][cli-build]. Use an output path not already present:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-eight-v1 --capsule \
  --output .temp/emit-eight-v1-check.malbolge \
  docs/technical/examples/corpus/emit-eight.c
sha256sum .temp/emit-eight-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-eight.malbolge \
  .temp/emit-eight-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-eight.malbolge \
  --report-steps | od -An -tx1
```

The artifact is `1215` bytes, with the SHA-256 digest above.
Matching output alone does not establish byte-identical compiler reproduction.
The VM must emit `53 20 17 3c 36 01 52 06` with the 21-step stderr receipt.
The automated `tests/test_versioned_example_corpus.py` checks stored hashes,
VM behavior, and source-to-capsule recompilation with pinned local tools.

This teaching pair is not the required parametric challenge instance.
General C lowering, cross-backend hashing, and arbitrary binary streams remain
unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
