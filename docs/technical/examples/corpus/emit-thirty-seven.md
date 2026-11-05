# Emit thirty-seven distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-thirty-seven-v1` (teaching example, not a challenge).
- Source: [`emit-thirty-seven.c`](emit-thirty-seven.c), SHA-256
  `f4888a38cd96f63b398bb0b3576de2b12dad860a486af3c7fe0f86cfe6d58b46`.
- Guest artifact: [`emit-thirty-seven.malbolge`](emit-thirty-seven.malbolge),
  SHA-256 `2f5344960a12ca10e847339ee466eb4bd22c63d9ff584650938807e2f139b577`.
- Target: `malbolge-2026`, current 15-trit `MALBCAP1` capsule.
- Compiler: repository `c2malbolge.py` with LLVM 22.1.8 frontend,
  `c2malbolge_json` and `malbolge_layout` binaries; exact 37-byte source
  admission was introduced in commit `9f8a6e14f` on 2026-11-05.
  Local binary provenance is not independently attested; deterministic
  recompilation is checked by the corpus regression.
- Input: none; guest output: 37 bytes, hex
  `3f 11 2c a8 07 bb 02 b6 0c b1 30 0d 4b 34 4f 23 5c 93`
  followed by `e0 9f e4 aa d5 ae 09 d4 ac e1 9e e2 ab 0b d6 9c e3 a0 d2`, no newline.
  8 bytes are printable ASCII, 7 are controls and
  22 have the high bit set.

Thirty-seven exact source-proven `putchar` calls lower to 32 `CrazyData`
updates and five `RotateData` updates at byte indices 3, 10, 17, 24, 31.
Twenty no-ops precede data-pointer relocation; one reached no-op
precedes byte index twelve. All 37 writes target distinct cells 115..137
and 140..188 (step two), beyond the 97-cell program source. The real VM
computes every output and consumes no input. This is not general C output.

## Reproduce from the repository root

Build the pinned compiler tools as described in
[CLI build instructions][cli-build], then use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-thirty-seven-v1 --capsule \
  --output .temp/emit-thirty-seven-v1-check.malbolge \
  docs/technical/examples/corpus/emit-thirty-seven.c
sha256sum .temp/emit-thirty-seven-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-thirty-seven.malbolge \
  .temp/emit-thirty-seven-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-thirty-seven.malbolge \
  --report-steps | od -An -tx1
```

The capsule is 1823 bytes. The normative VM must emit the exact 37-byte
sequence and `malbolge-steps-v1:97` on stderr. The corpus tests separately
check both SHA-256 hashes, real VM output and byte-identical recompilation.
Equal guest output alone does not prove target artifact identity.

This teaching pair is not a parametric challenge instance. General source
lowering, cross-backend hashing and arbitrary output remain unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
