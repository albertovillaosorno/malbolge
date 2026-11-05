# Emit forty-six distinct binary bytes — version 1

## Identity and scope

- Example ID: `emit-forty-six-v1` (teaching example, not a challenge).
- Source: [`emit-forty-six.c`](emit-forty-six.c), SHA-256
  `5618619ba65ddb2917d1716e5c7fe629a408798e1037241f2832e46f29d79b2f`.
- Guest artifact: [`emit-forty-six.malbolge`](emit-forty-six.malbolge),
  SHA-256 `5a11922ef7e50e8b6c5612938c8fffb3228afd9d0272a7c254a377483fcbf4b5`.
- Target: `malbolge-2026`, current 15-trit `MALBCAP1` capsule.
- Compiler: repository `c2malbolge.py` with pinned LLVM 22.1.8 frontend,
  `c2malbolge_json` and `malbolge_layout`; this exact source-bound C46
  lowering was introduced in DCO commit `b1cb83368` on 2026-11-05.
  Local binary provenance is not independently attested; rebuild and
  compare the artifact byte-for-byte.
- Input: none; guest output: exactly 46 distinct bytes (hexadecimal):
  `54 22 4f 23 53 1e 09 08 e2 ab dd 7e c0 7d ba 81`
  `bc 7b 2a 10 30 0e 2f 11 2d a3 ff a7 00 a2 01 a6`
  `fc cf a5 ce 9f d2 a1 cc 90 e3 ae e1 ad e4`
  No trailing newline is emitted.

Forty-six source-ordered `putchar` calls lower to forty `CrazyData`
updates and six `RotateData` updates at output indices 6, 7, 18, 25,
29 and 40. Ten reached no-ops precede data-pointer relocation; two
additional no-ops precede output indices 11 and 33. The 46 guest data
writes occupy disjoint cells beyond the 106-cell code. The normative VM
executes exactly 106 steps, computes each byte inside the guest and
consumes no input. This finite witness does not establish arbitrary C
or `putchar` lowering.

## Reproduce from the repository root

```sh
CARGO_TARGET_DIR=.cache/rust/target cargo build --locked --workspace --bins
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-forty-six-v1 --capsule \
  --output .temp/emit-forty-six-v1-check.malbolge \
  docs/technical/examples/corpus/emit-forty-six.c
sha256sum .temp/emit-forty-six-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-forty-six.malbolge \
  .temp/emit-forty-six-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-forty-six.malbolge \
  --report-steps | od -An -tx1
```

The capsule has 1895 bytes. The normative VM must emit exactly the 46
bytes above and `malbolge-steps-v1:106` on stderr. SHA-256 protects
artifact identity separately from guest output. The pinned regression
`tests/test_c2malbolge_distinct_literal_forty_six.py` checks raw and
capsule VM execution, forged and strict-prefix refusals, C45 and `Q.`
compatibility, and no-clobber behavior. The retained-corpus regression
also checks both hashes, the exact VM output and byte-identical rebuild.
