# Emit forty-seven distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-forty-seven-v1` (teaching example, not a challenge).
- Source: [`emit-forty-seven.c`](emit-forty-seven.c), SHA-256
  `e82395c60195edf52bb418420e1ea54c0dd908e779c9e57e69f993600b712d11`.
- Guest artifact: [`emit-forty-seven.malbolge`](emit-forty-seven.malbolge),
  SHA-256 `3130215c9ba054edc462792a37cfe3e304132b51498c6185b0e35ce8576b8488`.
- Target: `malbolge-2026`, current 15-trit `MALBCAP1` capsule.
- Compiler: repository `c2malbolge.py` with pinned LLVM 22.1.8 frontend,
  `c2malbolge_json` and `malbolge_layout`; this exact source-bound C47
  lowering was introduced in DCO commit `09d864f70` on 2026-11-05.
  Local binary provenance is not independently attested; rebuild and
  compare the artifact byte-for-byte.
- Input: none; guest output: exactly 47 distinct bytes (hexadecimal):
  `05 fc cd a7 d8 c2 bb c3 d7 40 41 59 24 5a 1c 1b`
  `2e 4f 2f 1a 48 b9 fd d3 17 9d 33 b7 b0 3b af 37`
  `51 1d 50 38 36 4a 35 14 2c 3f 2d 0a 46 26 11`
  No trailing newline is emitted.

Forty-seven source-ordered `putchar` calls lower to 42 `CrazyData`
updates and five `RotateData` updates at output indices 0, 1, 9, 21
and 28. Sixteen reached no-ops precede data-pointer relocation; six
additional no-ops precede output indices 3, 14, 16, 31, 37 and 40.
The 47 guest data writes occupy disjoint cells beyond the 118-cell code.
The normative VM executes exactly 118 steps, computes each byte inside
the guest and consumes no input. This finite witness does not establish
arbitrary C or `putchar` lowering.

## Reproduce from the repository root

```sh
CARGO_TARGET_DIR=.cache/rust/target cargo build --locked --workspace --bins
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-forty-seven-v1 --capsule \
  --output .temp/emit-forty-seven-v1-check.malbolge \
  docs/technical/examples/corpus/emit-forty-seven.c
sha256sum .temp/emit-forty-seven-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-forty-seven.malbolge \
  .temp/emit-forty-seven-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-forty-seven.malbolge \
  --report-steps | od -An -tx1
```

The capsule has 1,991 bytes. The normative VM must emit exactly the 47
bytes above and `malbolge-steps-v1:118` on stderr. SHA-256 protects
artifact identity separately from guest output. The pinned regression
`tests/test_c2malbolge_distinct_literal_forty_seven.py` checks raw and
capsule VM execution, forged and strict-prefix refusals, C46 and `Q.`
compatibility, and no-clobber behavior. The retained-corpus regression
also checks both hashes, the exact VM output and byte-identical rebuild.
