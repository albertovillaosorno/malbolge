# Emit forty distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-forty-v1` (teaching example, not a challenge).
- Source: [`emit-forty.c`](emit-forty.c), SHA-256
  `20fe0bd02f9d640daf57156d4734aaa9544204418c99eaa0e473929735993360`.
- Guest artifact: [`emit-forty.malbolge`](emit-forty.malbolge),
  SHA-256 `0e990005bbdc9b2b3b1a956df09a68582e4fb6ab3c529fb1a52b492ad59c34e6`.
- Target: `malbolge-2026`, current 15-trit `MALBCAP1` capsule.
- Compiler: repository `c2malbolge.py` with LLVM 22.1.8 frontend,
  `c2malbolge_json` and `malbolge_layout` binaries; exact 40-byte source
  admission was introduced in commit `b39d57ab5` on 2026-11-05.
  Local binary provenance is not independently attested; deterministic
  recompilation is checked by the corpus regression.
- Input: none; guest output: 40 bytes, hex
  `a8 07 bb 02 b6 0c b1 30 0d 3c 11 2c 14 39 a6 46`
  followed by `42 44 2f 50 36 09 d4 ac e1 9e e2 ab 0b d6 9c e3`
  and `a0 d2 ad 93 e0 9f e4 aa`, no newline.
  10 bytes are printable ASCII, 8 are controls and
  22 have the high bit set.

Forty exact source-proven `putchar` calls lower to 34 `CrazyData` updates
and six `RotateData` updates at byte indices 0, 7, 14, 21, 28 and 35.
Fourteen no-ops precede data-pointer relocation; one reached no-op
precedes byte index 15. All 40 writes target distinct cells 121..149
(step two) and 152..200 (step two), beyond the 97-cell program source.
The real VM computes every output and consumes no input. This is not
arbitrary C output or an input-stream runtime.

## Reproduce from the repository root

Build the pinned compiler tools as described in
[CLI build instructions][cli-build], then use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-forty-v1 --capsule \
  --output .temp/emit-forty-v1-check.malbolge \
  docs/technical/examples/corpus/emit-forty.c
sha256sum .temp/emit-forty-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-forty.malbolge \
  .temp/emit-forty-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-forty.malbolge \
  --report-steps | od -An -tx1
```

The capsule is 1823 bytes. The normative VM must emit the exact 40-byte
sequence and `malbolge-steps-v1:97` on stderr. The corpus tests separately
check both SHA-256 hashes, real VM output and byte-identical recompilation.
Equal guest output alone does not prove target artifact identity.

This teaching pair is not a parametric challenge instance. General source
lowering, cross-backend hashing and arbitrary output remain unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
