# Emit forty-two distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-forty-two-v1` (teaching example, not a challenge).
- Source: [`emit-forty-two.c`](emit-forty-two.c), SHA-256
  `117d1eeb3a74f69c75897d23beaf5a5f298494037f0151722449a96f8fcc6fc9`.
- Guest artifact: [`emit-forty-two.malbolge`](emit-forty-two.malbolge),
  SHA-256 `c88ee1dc8e6bd0acfd1c1ea08c20231767c1a5288140ffea157e02c031816951`.
- Target: `malbolge-2026`, current 15-trit `MALBCAP1` capsule.
- Compiler: repository `c2malbolge.py` with pinned LLVM 22.1.8 frontend,
  `c2malbolge_json` and `malbolge_layout` binaries; exact 42-byte source
  admission was introduced in commit `dd70b3367` on 2026-11-05.
  Local binary provenance is not independently attested; deterministic
  recompilation is verified by the retained corpus regression.
- Input: none; guest output: exactly 42 bytes, hexadecimal:
  `a8 07 bb 02 b6 0c b1 30 0d 3c 11 2c 14 39 a6 46`
  `42 44 2f 50 36 09 d4 ac e1 9e e2 ab 0b d6 9c e3`
  `a0 d2 ad 93 e0 9f e4 aa d5 ae`
  Ten bytes are printable ASCII, eight are control bytes, and 24 have
  the high bit set. There is no trailing newline.

Forty-two source-ordered `putchar` calls lower to 36 `CrazyData` updates
and six `RotateData` updates at byte indices 0, 7, 14, 21, 28 and 35.
Nine reached no-ops precede data-pointer relocation; reached no-ops also
precede output indices 0 and 15. All 42 guest writes target distinct
cells beyond the 97-cell program, from address 127 through address 210.
The normative VM computes all bytes and consumes no input. This is a
single exact witness, not arbitrary C byte output or guest libc linkage.

## Reproduce from the repository root

Build the pinned compiler tools as described in
[CLI build instructions][cli-build], then use a fresh output path:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-forty-two-v1 --capsule \
  --output .temp/emit-forty-two-v1-check.malbolge \
  docs/technical/examples/corpus/emit-forty-two.c
sha256sum .temp/emit-forty-two-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-forty-two.malbolge \
  .temp/emit-forty-two-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-forty-two.malbolge \
  --report-steps | od -An -tx1
```

The capsule has 1823 bytes. The normative VM emits exactly 42 bytes and
`malbolge-steps-v1:97` on stderr. The corpus regression separately verifies
both SHA-256 digests, guest output and byte-identical recompilation.
Matching output alone does not establish artifact identity.

The fixed parametric challenge corpus, general C lowering and arbitrary
byte streams remain outside this bounded example.

[cli-build]: ../../../../src/interface/command-line/README.md
