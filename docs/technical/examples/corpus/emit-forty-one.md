# Emit forty-one distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-forty-one-v1` (teaching example, not a challenge).
- Source: [`emit-forty-one.c`](emit-forty-one.c), SHA-256
  `16973e6e709b07c044ccf158464bbd93a390ab299c1abfd4837ba31ae1774b53`.
- Guest artifact: [`emit-forty-one.malbolge`](emit-forty-one.malbolge),
  SHA-256 `af079783ce7479c86540f95f4854ef9e081e7f56ca9147a9af2aaec40e5722f0`.
- Target: `malbolge-2026`, current 15-trit `MALBCAP1` capsule.
- Compiler: repository `c2malbolge.py` with pinned LLVM 22.1.8 frontend,
  `c2malbolge_json` and `malbolge_layout` binaries; exact 41-byte source
  admission was introduced in commit `f5c573afd` on 2026-11-05.
  Local binary provenance is not independently attested; deterministic
  recompilation is verified by the retained corpus regression.
- Input: none; guest output: exactly 41 bytes, hexadecimal:
  `5a a8 07 bb 02 b6 0c b1 30 0d 3c 11 2c 14 39 a6`
  `46 42 44 2f 50 36 09 d4 ac e1 9e e2 ab 0b d6 9c`
  `e3 a0 d2 ad 93 e0 9f e4 aa`.
  Eleven bytes are printable ASCII, eight are control bytes, and 22 have
  the high bit set. There is no trailing newline.

Forty-one source-ordered `putchar` calls lower to 35 `CrazyData` updates and
six `RotateData` updates at byte indices 1, 8, 15, 22, 29, and 36.
Eleven reached no-ops precede data-pointer relocation; reached no-ops
also precede output indices 1 and 16. All 41 guest writes target distinct
cells beyond the 97-cell program, from address 124 through address 206.
The normative VM computes all bytes and consumes no input. This is a
single exact witness, not arbitrary C byte output or guest libc linkage.

## Reproduce from the repository root

Build the pinned compiler tools as described in
[CLI build instructions][cli-build], then use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-forty-one-v1 --capsule \
  --output .temp/emit-forty-one-v1-check.malbolge \
  docs/technical/examples/corpus/emit-forty-one.c
sha256sum .temp/emit-forty-one-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-forty-one.malbolge \
  .temp/emit-forty-one-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-forty-one.malbolge \
  --report-steps | od -An -tx1
```

The capsule has 1823 bytes. The normative VM emits exactly 41 bytes and
`malbolge-steps-v1:97` on stderr. The corpus regression separately verifies
both SHA-256 digests, guest output and byte-identical recompilation.
Matching output alone does not establish artifact identity.

The fixed parametric challenge corpus, general C lowering and arbitrary
byte streams remain outside this bounded example.

[cli-build]: ../../../../src/interface/command-line/README.md
