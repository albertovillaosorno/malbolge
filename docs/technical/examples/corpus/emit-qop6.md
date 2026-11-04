# Emit Q, FS, O, GS, P, ESC — version 1

## Identity and scope

- Example ID: `emit-qop6-v1` (fixed teaching example; not a generated
  challenge).
- Source: [`emit-qop6.c`](emit-qop6.c), SHA-256
  `91f7d5bdcb226014082d80e3d15a944811366506d5ecd0ce24441699235f434e`.
- Guest artifact: [`emit-qop6.malbolge`](emit-qop6.malbolge), SHA-256
  `bcf659b66b69e7dac57505ac70a516451b60393bc9a2510d6fd6a59d897b7a76`.
- Target: `malbolge-2026`, current 15-trit profile, in an extended
  `.malbolge` `MALBCAP1` capsule. It is **not** classic Malbolge source.
- Compiler: repository `c2malbolge.py` pipeline, pinned LLVM 22.1.8 native
  C frontend, `c2malbolge_json`, and `malbolge_layout` Rust executables.
  The output was generated on 2026-11-04 with locally built compiler tools;
  the exact compiler binary revision is not attested by this example.
  Regeneration compares the actual capsule bytes.
- Input: none. Guest output: raw bytes `51 1c 4f 1d 50 1b`, no newline.
  `1c`, `1d` and `1b` are FS, GS and ESC; they are not printed ASCII digits.
- Guest execution: 15 steps; actual VM stderr `malbolge-steps-v1:15`.

Six independent C `putchar` calls produce six distinct guest-computed bytes.
The current-profile VM verifies actual CrazyData writes and execution, not host
string formatting, while arbitrary binary streams remain unsupported.

## Reproduce from the repository root

Build the repository-pinned frontend and debug compiler/VM executables using
the [CLI build instructions][cli-build] first. Use a new output filename:

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-qop6-v1 --capsule \
  --output .temp/emit-qop6-v1-check.malbolge \
  docs/technical/examples/corpus/emit-qop6.c
sha256sum .temp/emit-qop6-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-qop6.malbolge \
  .temp/emit-qop6-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-qop6.malbolge \
  --report-steps | od -An -tx1
```

The artifact is 1,167 bytes. Its SHA-256 digest is pinned above. Compare exact
bytes: matching printed output alone does not prove artifact identity. The
normative VM must emit the six raw bytes and the 15-step stderr receipt.
`tests/test_versioned_example_corpus.py` verifies retained hashes, actual
normative VM execution, and compiler byte-exact reconstruction with the
available pinned local binaries.

The broader versioned corpus remains incomplete: this pair is not the required
fixed parametric challenge identity. Cross-backend deterministic hashing and
general C lowering are still open tasks.

[cli-build]: ../../../../src/interface/command-line/README.md
