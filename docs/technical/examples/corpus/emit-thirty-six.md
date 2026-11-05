# Emit thirty-six distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-thirty-six-v1` (teaching example, not a challenge).
- Source: [`emit-thirty-six.c`](emit-thirty-six.c), SHA-256
  `f265c7d119f22fb8feb203b93f314d12ad97c6dd77d3d1cd43389819f1c0172d`.
- Guest artifact: [`emit-thirty-six.malbolge`](emit-thirty-six.malbolge),
  SHA-256 `3a86aea76aeb2fc166a137cf54697b8bb70df85b7fb21bf42f75e183521f6cd0`.
- Target: `malbolge-2026`, current 15-trit `MALBCAP1` capsule.
- Compiler: repository `c2malbolge.py` with LLVM 22.1.8 frontend,
  `c2malbolge_json` and `malbolge_layout` binaries; exact 36-byte source
  admission was introduced in commit `f94f4c813` on 2026-11-05.
  Local binary provenance is not independently attested; deterministic
  recompilation is checked by the corpus regression.
- Input: none; guest output: 36 bytes, hex
  `39 a8 07 bb 02 b6 0c b1 30 0d 4b 34 4f 23 5c 93 e0 9f`
  followed by `e4 aa d5 ae 09 d4 ac e1 9e e2 ab 0b d6 9c e3 a0 d2 ad`, no newline.
  7 bytes are printable ASCII, 6 are controls and
  23 have the high bit set.

Thirty-six exact source-proven `putchar` calls lower to 31 `CrazyData`
updates and five `RotateData` updates at byte indices 1, 8, 15, 22, 29.
Twenty-two no-ops precede data-pointer relocation; one reached no-op
precedes byte index ten. All 36 writes target distinct cells 113..131
and 134..184 (step two), beyond the 97-cell program source. The real VM
computes every output and consumes no input. This is not general C output.

## Reproduce from the repository root

Build the pinned compiler tools as described in
[CLI build instructions][cli-build], then use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-thirty-six-v1 --capsule \
  --output .temp/emit-thirty-six-v1-check.malbolge \
  docs/technical/examples/corpus/emit-thirty-six.c
sha256sum .temp/emit-thirty-six-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-thirty-six.malbolge \
  .temp/emit-thirty-six-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-thirty-six.malbolge \
  --report-steps | od -An -tx1
```

The capsule is 1823 bytes. The normative VM must emit the exact 36-byte
sequence and `malbolge-steps-v1:97` on stderr. The corpus tests separately
check both SHA-256 hashes, real VM output and byte-identical recompilation.
Equal guest output alone does not prove target artifact identity.

This teaching pair is not a parametric challenge instance. General source
lowering, cross-backend hashing and arbitrary output remain unfinished.

[cli-build]: ../../../../src/interface/command-line/README.md
