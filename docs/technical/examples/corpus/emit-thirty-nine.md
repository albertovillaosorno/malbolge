# Emit thirty-nine distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-thirty-nine-v1` (teaching example, not a challenge).
- Source: [`emit-thirty-nine.c`](emit-thirty-nine.c), SHA-256
  `a2b0c3c514ce0af1568fa4b97c57efb1e5b23cfaa952dcf98f65ce645bb0871d`.
- Guest artifact: [`emit-thirty-nine.malbolge`](emit-thirty-nine.malbolge),
  SHA-256 `20bca04da87da684d1c61b3d1a0f3d8b80feb4c28dd37347249e332fa198f816`.
- Target: `malbolge-2026`, current 15-trit `MALBCAP1` capsule.
- Compiler: repository `c2malbolge.py` with LLVM 22.1.8 frontend,
  `c2malbolge_json` and `malbolge_layout` binaries; exact 39-byte source
  admission was introduced in commit `285186c79` on 2026-11-05.
  Local binary provenance is not independently attested; deterministic
  recompilation is checked by the corpus regression.
- Input: none; guest output: 39 bytes, hex
  `5c 32 26 a8 07 bb 02 b6 0c b1 30 0d 3c 11 2c 14 39 a6 46`
  followed by `42 44 2f 50 36 09 d4 ac e1 9e e2 ab 0b d6 9c e3`
  and `a0 d2 ad 93`, no newline.
  13 bytes are printable ASCII, 8 are controls and
  18 have the high bit set.

Thirty-nine exact source-proven `putchar` calls lower to 33 `CrazyData`
updates and six `RotateData` updates at byte indices 3, 10, 17, 24, 31,
and 38. Fifteen no-ops precede data-pointer relocation; reached no-ops
precede byte indices 2 and 18. All 39 writes target distinct cells
120, 122, 125..155 (step two), and 158..198 (step two), beyond the
97-cell program source. The real VM computes every output and consumes
no input. This is not general C output.

## Reproduce from the repository root

Build the pinned compiler tools as described in
[CLI build instructions][cli-build], then use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-thirty-nine-v1 --capsule \
  --output .temp/emit-thirty-nine-v1-check.malbolge \
  docs/technical/examples/corpus/emit-thirty-nine.c
sha256sum .temp/emit-thirty-nine-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-thirty-nine.malbolge \
  .temp/emit-thirty-nine-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-thirty-nine.malbolge \
  --report-steps | od -An -tx1
```

The capsule is 1823 bytes. The normative VM must emit the exact 39-byte
sequence and `malbolge-steps-v1:97` on stderr. The corpus tests separately
check both SHA-256 hashes, real VM output and byte-identical recompilation.
Equal guest output alone does not prove target artifact identity.

This teaching pair is not a parametric challenge instance. General source
lowering, cross-backend hashing and arbitrary output remain unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
