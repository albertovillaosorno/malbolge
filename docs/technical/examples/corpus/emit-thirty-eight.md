# Emit thirty-eight distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-thirty-eight-v1` (teaching example, not a challenge).
- Source: [`emit-thirty-eight.c`](emit-thirty-eight.c), SHA-256
  `3e1e3f7dd3def1b13e617f6e4f356aba3c5cfe7343b2fcc8677fbe6a6dd09e22`.
- Guest artifact: [`emit-thirty-eight.malbolge`](emit-thirty-eight.malbolge),
  SHA-256 `f4acddf3964d448b763f8d92278818fd77ddaa16b24d88409bd76c8f79b2ee7d`.
- Target: `malbolge-2026`, current 15-trit `MALBCAP1` capsule.
- Compiler: repository `c2malbolge.py` with LLVM 22.1.8 frontend,
  `c2malbolge_json` and `malbolge_layout` binaries; exact 38-byte source
  admission was introduced in commit `27645317f` on 2026-11-05.
  Local binary provenance is not independently attested; deterministic
  recompilation is checked by the corpus regression.
- Input: none; guest output: 38 bytes, hex
  `41 17 32 30 0d 3c 11 2c 14 39 a6 46 42 44 2f 50 36 09`
  followed by `d4 ac e1 9e e2 ab 0b d6 9c e3 a0 d2 ad 93`
  and `e0 9f e4 aa d5 ae`, no newline.
  12 bytes are printable ASCII, 6 are controls and
  20 have the high bit set.

Thirty-eight exact source-proven `putchar` calls lower to 33 `CrazyData`
updates and five `RotateData` updates at byte indices 3, 10, 17, 24, 31.
Eighteen no-ops precede data-pointer relocation; one reached no-op
precedes byte index eleven. All 38 writes target distinct cells 117..137
and 140..192 (step two), beyond the 97-cell program source. The real VM
computes every output and consumes no input. This is not general C output.

## Reproduce from the repository root

Build the pinned compiler tools as described in
[CLI build instructions][cli-build], then use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-thirty-eight-v1 --capsule \
  --output .temp/emit-thirty-eight-v1-check.malbolge \
  docs/technical/examples/corpus/emit-thirty-eight.c
sha256sum .temp/emit-thirty-eight-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-thirty-eight.malbolge \
  .temp/emit-thirty-eight-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-thirty-eight.malbolge \
  --report-steps | od -An -tx1
```

The capsule is 1823 bytes. The normative VM must emit the exact 38-byte
sequence and `malbolge-steps-v1:97` on stderr. The corpus tests separately
check both SHA-256 hashes, real VM output and byte-identical recompilation.
Equal guest output alone does not prove target artifact identity.

This teaching pair is not a parametric challenge instance. General source
lowering, cross-backend hashing and arbitrary output remain unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
