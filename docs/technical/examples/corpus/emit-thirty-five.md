# Emit thirty-five distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-thirty-five-v1` (teaching example, not a challenge).
- Source: [`emit-thirty-five.c`](emit-thirty-five.c), SHA-256
  `2f93cff11c619933cca4d6b92543cefc1ca2b433ef0550ea5d8de6bf6f36cbdc`.
- Guest artifact: [`emit-thirty-five.malbolge`](emit-thirty-five.malbolge),
  SHA-256 `766476813c35af5b6e3830292a71fa1d8c22fd7b9866e0a5b3e2c74e8530513e`.
- Target: `malbolge-2026`, current 15-trit `MALBCAP1` capsule.
- Compiler: repository `c2malbolge.py` with LLVM 22.1.8 frontend,
  `c2malbolge_json` and `malbolge_layout` binaries; exact 35-byte source
  admission was introduced in commit `a67bfbb3b` on 2026-11-05.
  Local binary provenance is not independently attested; deterministic
  recompilation is checked by the corpus regression.
- Input: none; guest output: 35 bytes, hex
  `30 0d 3c 11 2c 14 39 a6 46 42 44 2f 50 36 09 d4 ac e1`
  followed by `9e e2 ab 0b d6 9c e3 a0 d2 ad 93 e0 9f e4 aa d5 ae`, no newline.
  10 bytes are printable ASCII, 5 are controls and
  20 have the high bit set.

Thirty-five exact source-proven `putchar` calls lower to 30 `CrazyData`
updates and five `RotateData` updates at byte indices 0, 7, 14, 21, 28.
Twenty-four no-ops precede data-pointer relocation; one reached no-op
precedes byte index eight. All 35 writes target distinct cells 111..125
and 128..180 (step two), beyond the 97-cell program source. The real VM
computes every output and consumes no input. This is not general C output.

## Reproduce from the repository root

Build the pinned compiler tools as described in
[CLI build instructions][cli-build], then use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-thirty-five-v1 --capsule \
  --output .temp/emit-thirty-five-v1-check.malbolge \
  docs/technical/examples/corpus/emit-thirty-five.c
sha256sum .temp/emit-thirty-five-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-thirty-five.malbolge \
  .temp/emit-thirty-five-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-thirty-five.malbolge \
  --report-steps | od -An -tx1
```

The capsule is 1823 bytes. The normative VM must emit the exact 35-byte
sequence and `malbolge-steps-v1:97` on stderr. The corpus tests separately
check both SHA-256 hashes, real VM output and byte-identical recompilation.
Equal guest output alone does not prove target artifact identity.

This teaching pair is not a parametric challenge instance. General source
lowering, cross-backend hashing and arbitrary output remain unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
