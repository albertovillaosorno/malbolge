# Emit forty-four distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-forty-four-v1` (teaching example, not a challenge).
- Source: [`emit-forty-four.c`](emit-forty-four.c), SHA-256
  `b1e1ab93c254b6c9d79d76088b2d3354725f1e5ceca11923de5666af6f119529`.
- Guest artifact: [`emit-forty-four.malbolge`](emit-forty-four.malbolge),
  SHA-256 `a93046a8e9530ece4425c60326751e5c5e7374b8e5e4423bd55fc86f8611b43d`.
- Target: `malbolge-2026`, current 15-trit `MALBCAP1` capsule.
- Compiler: repository `c2malbolge.py` with pinned LLVM 22.1.8 frontend,
  `c2malbolge_json` and `malbolge_layout`; this finite C44 lowering was
  introduced in DCO commit `5dfc829ba` on 2026-11-05. Local binary
  provenance is not independently attested; rebuild and compare the retained
  artifact byte-for-byte.
- Input: none; guest output: exactly 44 distinct bytes (hexadecimal):
  `5a 26 47 0b 3e 09 2d 13 34 a5 06 af f3 a8 2f 11`
  `41 0f 30 19 37 08 4d 32 4e 1f 57 29 44 0a d4 99`
  `dd a0 cc aa d3 07 d5 91 de a1 dc ab`
  No trailing newline is emitted.

Forty-four source-ordered `putchar` calls lower to 38 `CrazyData`
updates and six `RotateData` updates at output indices 9, 13, 14, 29,
37 and 39. Eleven reached no-ops precede data-pointer relocation; two
additional no-ops precede output indices 3 and 22. All 44 guest data
writes are on distinct cells beyond the 103-cell code. The normative
VM executes exactly 103 steps, computes each byte in the guest, and
consumes no input. This remains one finite witness, not arbitrary C or
`putchar` lowering.

## Reproduce from the repository root

```sh
CARGO_TARGET_DIR=.cache/rust/target cargo build --locked --workspace --bins
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-forty-four-v1 --capsule \
  --output .temp/emit-forty-four-v1-check.malbolge \
  docs/technical/examples/corpus/emit-forty-four.c
sha256sum .temp/emit-forty-four-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-forty-four.malbolge \
  .temp/emit-forty-four-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-forty-four.malbolge \
  --report-steps | od -An -tx1
```

The capsule has 1871 bytes. The normative VM must emit
exactly the 44 bytes listed above and `malbolge-steps-v1:103` on stderr.
SHA-256 checks protect artifact identity separately from guest output.
The pinned C regression
`tests/test_c2malbolge_distinct_literal_forty_four.py` verifies raw and
capsule execution, wrong-byte and strict-prefix refusal, existing C43
and `Q.` compatibility, and no-clobber behavior.

General C-to-Malbolge compilation and arbitrary byte streams remain
outside this bounded example.
