# Compiler Challenges

This directory owns deterministic parametric challenge families and fixed
challenge manifests used to compare compiler, optimizer, verifier, and execution
algorithms across increasing difficulty.

Generated run output belongs in the executing algorithm's `out/` directory or a
local benchmark output directory, not in the versioned challenge definition.

## Active families

`generate.py` implements five active families: `arithmetic-dag/v1`,
`linear-mix/v1`, `branch-mix/v1`, `memory-walk/v1`, and `call-chain/v1`.
Their identity is the
tuple of family,
version, unsigned 64-bit seed, canonical target profile plus fingerprint, and
positive node count. The generator uses a
version-stable deterministic mixing stream to choose a live dependency spine,
additional source-order DAG edges, and `uint32_t` add, xor, multiply, and rotate
operations. Every generated node therefore contributes to the final entry value;
warning-clean native compilation is regression evidence against dead nodes.

`linear-mix/v1` uses a family-domain-separated deterministic stream and a strict
predecessor chain, so it isolates dependency depth from the DAG family’s extra
source-order fan-in. `branch-mix/v1` emits one live `if`/`else` diamond per node
from its own domain-separated stream, exercising normalized frontend control
flow while retaining an exact Python oracle. `memory-walk/v1` uses a fixed
eight-cell local `uint32_t` array and adds deterministic indexed read/write/read
steps while carrying one live scalar value between nodes. `call-chain/v1`
threads that live value through one pure three-argument helper call per node.

Each generated directory contains `program.c`, `oracle.bin`, and
`manifest.json`. The manifest binds source and oracle SHA-256 digests. The C
source exposes `uint32_t malbolge_challenge(void)`; `oracle.bin` is the exact
little-endian return value of that entry. The standalone `main` keeps only the
low 31 bits for a portable process status and is explicitly not oracle
authority.

Example:

```text
python benchmarks/challenges/generate.py arithmetic-dag \
  --version 1 --seed 7 --profile malbolge-2026 \
  --nodes 64 --output .cache/challenge-7-64
```

Publication is fail-closed: an unrelated output path, linked output ancestor,
or staging collision is preserved rather than followed or overwritten. Staging
ownership begins only after the atomic directory claim succeeds, so a writer
that loses a race cannot clean another writer's staged payload. Final directory
publication is no-replace: Windows uses `rename`, Linux uses
`renameat2(RENAME_NOREPLACE)`, and an unimplemented host fails closed rather
than silently replacing unrelated state. Linked-ancestor rejection runs before
replay
recognition, and replay also requires all three artifact leaves to be ordinary
files rather than symlinks or junctions. Byte-identical external state therefore
cannot make a redirected output admissible. Repeating an identical identity at
an already-published ordinary directory is an idempotent replay. Generated C
is required to pass the current repository C ABI/libc preflight; all five
families deliberately use no unavailable guest libc routine. The published
`arithmetic-dag/v1` replay vector is hash-locked across family extensions.

This is implementation substrate, not completion of the planning objective.
Data-dependent memory/pointer and larger-stress families plus an end-to-end
generated/executed Malbolge fixture remain open.
