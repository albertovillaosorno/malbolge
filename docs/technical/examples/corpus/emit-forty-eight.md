# Emit forty-eight distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-forty-eight-v1` (teaching example, not a challenge).
- Source: [`emit-forty-eight.c`](emit-forty-eight.c), SHA-256
  `216401da8db1a4f275c6584f94d207a611be93028fb12682c0f2c1352a729e60`.
- Guest artifact: [`emit-forty-eight.malbolge`](emit-forty-eight.malbolge),
  SHA-256 `5c5892d0f601e8cd44ad7ffe152d91bc48b3a53d5ec71d08c8de0502313c6bdc`.
- Target: `malbolge-2026`, current 15-trit `MALBCAP1` capsule.
- Compiler: repository `c2malbolge.py` with pinned LLVM 22.1.8 frontend,
  `c2malbolge_json` and `malbolge_layout`; this exact source-bound C48
  lowering was introduced in DCO commit `8a1b9aea2` on 2026-11-05.
  Local binary provenance is not independently attested; rebuild and
  compare the artifact byte-for-byte.
- Input: none; guest output: exactly 48 distinct bytes (hexadecimal):
  `51 37 34 38 fb ce 9f 98 b8 b4 83 cd 04 ca 1c 1b`
  `2e 4f 8b cf a7 a2 95 d6 96 a1 af c5 ba e0 9d e1`
  `b9 41 47 5c 2a 44 29 0e 32 4e 31 18 1f 4c 20 17`
  No trailing newline is emitted.

Forty-eight source-ordered `putchar` calls lower to 44 `CrazyData`
updates and four `RotateData` updates at output indices 4, 12, 18 and
33. Thirteen reached no-ops precede data-pointer relocation; ten
additional no-ops precede output indices 13, 14, 16, 18, 20, 22,
27, 37, 40 and 44. The 48 guest data writes occupy disjoint cells
beyond the 121-cell code. The normative VM executes exactly 121 steps,
computes each byte inside the guest and consumes no input. This finite
witness does not establish arbitrary C or `putchar` lowering.

## Reproduce from the repository root

```sh
CARGO_TARGET_DIR=.cache/rust/target cargo build --locked --workspace --bins
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-forty-eight-v1 --capsule \
  --output .temp/emit-forty-eight-v1-check.malbolge \
  docs/technical/examples/corpus/emit-forty-eight.c
sha256sum .temp/emit-forty-eight-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-forty-eight.malbolge \
  .temp/emit-forty-eight-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-forty-eight.malbolge \
  --report-steps | od -An -tx1
```

The capsule has 2,015 bytes. The normative VM must emit exactly the 48
bytes above and `malbolge-steps-v1:121` on stderr. SHA-256 protects
artifact identity separately from guest output. The pinned regression
`tests/test_c2malbolge_distinct_literal_forty_eight.py` checks raw and
capsule VM execution, forged and strict-prefix refusals, C47/C46 and
`Q.` compatibility, and no-clobber behavior. The retained-corpus
regression checks both hashes, exact VM output with and without binary
stdin, and byte-identical rebuild.
