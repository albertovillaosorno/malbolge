# Emit forty-three distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-forty-three-v1` (teaching example, not a challenge).
- Source: [`emit-forty-three.c`](emit-forty-three.c), SHA-256
  `d5ba0666f730819d740d1259285cd2f098cb12d281ba109b965e46926a3aa3d3`.
- Guest artifact: [`emit-forty-three.malbolge`](emit-forty-three.malbolge),
  SHA-256 `c7d7c83c966fc46d6558ce05e0db5cffbe0b580fe73b98c6dfdc4bd166d33206`.
- Target: `malbolge-2026`, current 15-trit `MALBCAP1` capsule.
- Compiler: repository `c2malbolge.py` with pinned LLVM 22.1.8 frontend,
  `c2malbolge_json` and `malbolge_layout`; the exact source-bound 43-byte
  lowering was introduced in DCO commit `d740b3274` on 2026-11-05.
  Local binary provenance is not independently attested; reproduce and
  compare the retained artifact byte-for-byte.
- Input: none; guest output: exactly 43 distinct bytes (hexadecimal):
  `51 2e 4f 1d 1a 2f 1b 1c 24 26 11 a7 05 b8 fc b6`
  `40 2d 49 34 38 3e 92 e4 a4 e2 ae da ac 08 d5 ab`
  `dd a2 de aa 0b d9 9c e3 a3 d2 ad`
  No trailing newline is emitted.

Forty-three source-ordered `putchar` calls lower to 39 `CrazyData`
updates and four `RotateData` updates at output indices 11, 22, 29
and 36. Ten reached no-ops precede data-pointer relocation; two more
no-ops precede output indices 4 and 16. All 43 guest data writes are
on distinct cells beyond the 100-cell code. The independent normative
VM executes 100 steps, computes each byte inside the guest, and consumes
no input. This remains one finite witness, not arbitrary C or `putchar`
lowering.

## Reproduce from the repository root

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-forty-three-v1 --capsule \
  --output .temp/emit-forty-three-v1-check.malbolge \
  docs/technical/examples/corpus/emit-forty-three.c
sha256sum .temp/emit-forty-three-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-forty-three.malbolge \
  .temp/emit-forty-three-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-forty-three.malbolge \
  --report-steps | od -An -tx1
```

The capsule has 1847 bytes. The normative VM must emit the 43 bytes
listed above and `malbolge-steps-v1:100` on stderr. SHA-256 checks
protect artifact identity independently of guest output. The pinned
C regression `tests/test_c2malbolge_distinct_literal_forty_three.py`
verifies raw and capsule execution, wrong-byte and prefix refusal,
existing C42 and `Q.` compatibility, and no-clobber behavior.

General C-to-Malbolge compilation and arbitrary byte streams remain
outside this bounded example.
