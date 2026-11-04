# Emit T=4> — version 1

## Identity and scope

- Example ID: `emit-t4-v1` (fixed teaching example; not a generated challenge).
- Source: [`emit-t4.c`](emit-t4.c), SHA-256
  `34d1144628330399658b36bfe57e2d34cf71f40ad46645ec075a6390ea45fb1a`.
- Guest artifact: [`emit-t4.malbolge`](emit-t4.malbolge), SHA-256
  `9ee602682624425da80c13786df338c80df15a65e1df083613c37100ed81f72d`.
- Target: `malbolge-2026`, current 15-trit profile, in an extended
  `.malbolge` `MALBCAP1` capsule. This is **not** a classic Malbolge source.
- Compiler: repository `c2malbolge.py` pipeline, pinned LLVM 22.1.8 native
  C frontend, `c2malbolge_json`, and `malbolge_layout` Rust executables.
  The observed output was generated on 2026-11-04 with the repository's
  locally built compiler tools; the exact compiler binary revision is not
  attested by this example. Regeneration compares the final bytes instead.
- Input: none. Guest output: ASCII bytes `54 3d 34 3e` (`T=4>`), no newline.
- Guest execution: 21 steps; actual VM stderr `malbolge-steps-v1:21`.

This source uses only the currently witnessed four-distinct-byte `putchar`
subset. It demonstrates **real guest execution**, not host-side simulation;
it does not claim that arbitrary C programs, strings, or streams compile.

## Reproduce from the repository root

Build the repository-pinned native frontend and debug compiler/VM executables
using the [CLI build instructions][cli-build] first. For a fresh output
filename (the compiler intentionally refuses to overwrite existing files):

```sh
mkdir -p .temp
src/interface/command-line/composition/scripts/c2malbolge \
  --repository-tools --source-id corpus/emit-t4-v1 --capsule \
  --output .temp/emit-t4-v1-check.malbolge \
  docs/technical/examples/corpus/emit-t4.c
sha256sum .temp/emit-t4-v1-check.malbolge
cmp docs/technical/examples/corpus/emit-t4.malbolge \
  .temp/emit-t4-v1-check.malbolge
src/interface/command-line/composition/scripts/malbolge \
  --repository-tools docs/technical/examples/corpus/emit-t4.malbolge \
  --report-steps
```

The artifact is 1,215 bytes. Its digest is the pinned SHA-256 above; compare
exact bytes, not only the VM's stdout. Execution of this checked-in artifact
must emit `T=4>` with the 21-step receipt. The separately checked-in regression
`tests/test_versioned_example_corpus.py` checks the retained hashes, VM
execution, and reconstruction using the available pinned local binaries.

The broader versioned corpus remains incomplete: this teaching pair is not
the required fixed identity from the parametric challenge generator, and
cross-backend deterministic hashing and general C lowering remain open tasks.

[cli-build]: ../../../../src/interface/command-line/README.md
