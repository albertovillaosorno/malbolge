# Emit Q. — version 1

## Identity and scope

- Example ID: `emit-qp-v1` (fixed teaching example; not a generated challenge).
- Source: [`emit-qp.c`](emit-qp.c), SHA-256
  `9d99117ec1218be5102aef819fc872e098fcfea7f7efede831c765e5104886f3`.
- Guest artifact: [`emit-qp.malbolge`](emit-qp.malbolge), SHA-256
  `4112557f6f320f8827278ff8b623fddba73812c49801569093e815f27a9fa2b8`.
- Target: `malbolge-2026`, current 15-trit profile, in an extended
  `.malbolge` `MALBCAP1` capsule. This is **not** a classic Malbolge source.
- Compiler: repository `c2malbolge.py` pipeline, pinned LLVM 22.1.8 native
  C frontend, `c2malbolge_json`, and `malbolge_layout` Rust executables.
  The observed output was generated on 2026-11-04 with the repository's
  locally built compiler tools; the exact compiler binary revision is not
  attested by this example. Regeneration compares the final bytes instead.
- Input: none. Guest output: ASCII bytes `51 2e` (the text `Q.`), no newline.
- Guest execution: 8 steps; actual VM stderr `malbolge-steps-v1:8`.

This source uses only the currently witnessed two-distinct-byte `putchar`
subset. It demonstrates **real guest execution**, not host-side simulation;
it does not claim that arbitrary C programs, strings, or streams compile.

## Reproduce from the repository root

Build the repository-pinned native frontend and debug compiler/VM executables
using the [CLI build instructions][cli-build] first. For a fresh output
filename (the compiler intentionally refuses to overwrite existing files):

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-qp-v1 --capsule \
  --output .temp/emit-qp-v1-check.malbolge \
  docs/technical/examples/corpus/emit-qp.c
sha256sum .temp/emit-qp-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-qp.malbolge \
  .temp/emit-qp-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-qp.malbolge \
  --report-steps
```

The artifact is 1,111 bytes. Its digest is the pinned SHA-256 above; compare
exact bytes, not only the VM's stdout. Execution of this checked-in artifact
must emit `Q.` with the 8-step receipt. The separately checked-in regression
`tests/test_versioned_example_corpus.py` checks the retained hashes, VM
execution, and reconstruction using the available pinned local binaries.

The broader versioned corpus remains incomplete: this teaching pair is not
the required fixed identity from the parametric challenge generator, and
cross-backend deterministic hashing and general C lowering remain open tasks.

[cli-build]: ../../../../src/interface/command-line/README.md
