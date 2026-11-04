# Emit 6, >, 5, STX, T, US, CAN — version 1

## Identity and scope

- Example ID: `emit-seven-v1` (fixed teaching example, not a generated
  challenge).
- Source: [`emit-seven.c`](emit-seven.c), SHA-256
  `1bf0848c18f712c2e7b87e0305563a73cb9299aa45cc74d463e4f6098db19140`.
- Guest artifact: [`emit-seven.malbolge`](emit-seven.malbolge), SHA-256
  `4f0c732c3b55dd48b12795044f106989ffc84cd7839bcbff1e11c1b9643b99f8`.
- Target: `malbolge-2026`, current 15-trit profile, in an extended
  `.malbolge` `MALBCAP1` capsule, not classic raw Malbolge source.
- Compiler: repository `c2malbolge.py` pipeline, LLVM 22.1.8 native C
  frontend, `c2malbolge_json` and `malbolge_layout` Rust executables.
  Generated on 2026-11-04 against source commit `8d419391c`; local binary
  provenance is not independently attested. Recompilation verifies bytes.
- Input: none. Guest output: bytes `36 3e 35 02 54 1f 18`, no newline.
  `02`, `1f`, and `18` are STX, US, and CAN control codes.
- Guest execution: 21 VM steps; stderr `malbolge-steps-v1:21`.

Seven distinct C `putchar` calls yield seven separately computed Malbolge
CrazyData effects. This is real guest binary output verified by the normative
profile VM, not host C execution or general-purpose byte-stream support.

## Reproduce from the repository root

Build the repository-pinned frontend and debug compiler/VM executables using
the [CLI build instructions][cli-build]. Use an output path not already present:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-seven-v1 --capsule \
  --output .temp/emit-seven-v1-check.malbolge \
  docs/technical/examples/corpus/emit-seven.c
sha256sum .temp/emit-seven-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-seven.malbolge \
  .temp/emit-seven-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-seven.malbolge \
  --report-steps | od -An -tx1
```

The artifact is 1,215 bytes, with the SHA-256 digest above. Matching output
alone does not establish byte-identical compiler reproduction. The VM must
emit `36 3e 35 02 54 1f 18` with the 21-step stderr receipt. The automated
`tests/test_versioned_example_corpus.py` checks stored hashes, VM behavior,
and real source-to-capsule recompilation with available pinned local tools.

This teaching pair is not the required parametric challenge instance.
General C lowering, cross-backend hashing, and arbitrary binary streams remain
unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
