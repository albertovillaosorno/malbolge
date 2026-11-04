# Emit Q, quote, ESC, 7, 9 — version 1

## Identity and scope

- Example ID: `emit-qesc79-v1` (fixed teaching example; not a generated
  challenge).
- Source: [`emit-qesc79.c`](emit-qesc79.c), SHA-256
  `5a753a10b51b5211022694a2b3f9c45fe4afb92cd8e0ebf7f9cc37876953688d`.
- Guest artifact: [`emit-qesc79.malbolge`](emit-qesc79.malbolge), SHA-256
  `09be18cd3358663cf7c8434f4b4c910f9ae2a87f0e6b799238372d2110fae2b6`.
- Target: `malbolge-2026`, current 15-trit profile, in an extended
  `.malbolge` `MALBCAP1` capsule. This is **not** a classic Malbolge source.
- Compiler: repository `c2malbolge.py` pipeline, pinned LLVM 22.1.8 native
  C frontend, `c2malbolge_json`, and `malbolge_layout` Rust executables.
  The observed output was generated on 2026-11-04 with locally built
  compiler tools; the exact binary revision is not attested by this example.
  Regeneration instead compares the final bytes.
- Input: none. Guest output: raw bytes `51 22 1b 37 39`, no newline.
  The middle `1b` is ASCII ESC, not literal backslash-escape text.
- Guest execution: 23 steps; actual VM stderr `malbolge-steps-v1:23`.

The source uses five distinct literal `putchar` calls and all five values are
computed through actual guest CrazyData writes. This is verified **guest
binary output**, not host simulation or arbitrary stream support.

## Reproduce from the repository root

Build the repository-pinned native frontend and debug compiler/VM executables
using the [CLI build instructions][cli-build] first. Use a fresh output name;
the compiler intentionally refuses to overwrite existing files.

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-qesc79-v1 --capsule \
  --output .temp/emit-qesc79-v1-check.malbolge \
  docs/technical/examples/corpus/emit-qesc79.c
sha256sum .temp/emit-qesc79-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-qesc79.malbolge \
  .temp/emit-qesc79-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-qesc79.malbolge \
  --report-steps | od -An -tx1
```

The artifact is 1,231 bytes. Its digest is pinned above; byte comparison is
necessary because the same guest output alone cannot prove artifact identity.
The VM must print `51 22 1b 37 39` in hexadecimal with a 23-step receipt.
`tests/test_versioned_example_corpus.py` verifies retained SHA-256 hashes,
actual VM execution, and regeneration with the available pinned local binaries.

The wider corpus remains incomplete. This teaching pair is not the required
fixed parametric challenge instance, and cross-backend deterministic hashing
and general C lowering are still open tasks.

[cli-build]: ../../../../src/interface/command-line/README.md
