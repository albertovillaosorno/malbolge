# Emit thirty distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-thirty-v1` (fixed teaching example, not a generated
  challenge).
- Source: [`emit-thirty.c`](emit-thirty.c), SHA-256
  `163cc08af89a4a5aff7d26791b2a3639e2b2f37f164025bd04d26a4d85131625`.
- Guest artifact: [`emit-thirty.malbolge`](emit-thirty.malbolge),
  SHA-256
  `778fc6a678185dddff20772d58641335a1131af08cd28403fa364952286506f9`.
- Target: `malbolge-2026`, current 15-trit profile, in an extended
  `.malbolge` `MALBCAP1` capsule, not classic raw Malbolge source.
- Compiler: repository `c2malbolge.py` pipeline, LLVM 22.1.8 native C
  frontend, `c2malbolge_json` and `malbolge_layout` Rust executables.
  Generated on 2026-11-05 against compiler source commit `93469f625`;
  local binary provenance is not independently attested. Recompilation
  verifies bytes.
- Input: none. Guest output: bytes
  `39 a8 07 da 99 dd a3 cf a7 d9 09 d4 ac e1 9e e2` followed by
  `ab 0b d6 9c e3 a0 d2 ad 93 e0 9f e4 aa d5`, no newline.
  One byte is printable ASCII, three are controls and 26 have their high
  bit set.

Thirty source-proven C `putchar` calls yield 26 disjoint guest `CrazyData`
writes and four `RotateData` writes at zero-based arithmetic indices 1,
10, 17 and 24. Thirty-four leading no-ops place the data relocation;
one reached no-op precedes the fourth arithmetic pair. The 97-step
normative VM writes only to disjoint data cells beyond the 97-cell
source. The real guest independently computes all thirty binary outputs,
not host C execution or a general byte-stream API.

## Reproduce from the repository root

Build pinned frontend and debug compiler/VM executables using
[CLI build instructions][cli-build]. Use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-thirty-v1 --capsule \
  --output .temp/emit-thirty-v1-check.malbolge \
  docs/technical/examples/corpus/emit-thirty.c
sha256sum .temp/emit-thirty-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-thirty.malbolge \
  .temp/emit-thirty-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-thirty.malbolge \
  --report-steps | od -An -tx1
```

For unframed graphical source, omit `--capsule` and select the modern
profile explicitly when running it:

```sh
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-thirty-v1 \
  --output .temp/emit-thirty-v1-raw.malbolge \
  docs/technical/examples/corpus/emit-thirty.c
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools .temp/emit-thirty-v1-raw.malbolge \
  --raw-profile malbolge-2026 --report-steps | od -An -tx1
```

The capsule is `1823` bytes, with the SHA-256 digest above.
Matching output alone does not establish byte-identical compiler reproduction.
The normative VM must emit the exact 30-byte sequence above and a 97-step
stderr receipt. `tests/test_versioned_example_corpus.py` verifies hashes,
VM output and byte-identical regeneration with pinned compiler tools.

This teaching pair is not the required parametric challenge instance.
General C lowering, cross-backend hashing, and arbitrary binary streams
remain unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
