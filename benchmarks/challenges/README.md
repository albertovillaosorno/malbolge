# Compiler Challenges

This directory owns deterministic parametric challenge families and fixed
challenge manifests used to compare compiler, optimizer, verifier, and execution
algorithms across increasing difficulty.

Generated run output belongs in the executing algorithm's `out/` directory or a
local benchmark output directory, not in the versioned challenge definition.

## Active families

`generate.py` implements thirteen active version-one families:
`arithmetic-dag`, `linear-mix`, `branch-mix`, `memory-walk`, `call-chain`,
`pointer-walk`, `alias-walk`, `stream-state`, `graph-reduce`,
`grid-accumulate`, `layout-chain`, `ternary-fold`, and `nested-state`. Their
identity is the tuple of family, version, unsigned 64-bit seed, canonical target
profile plus fingerprint, and positive node count. Every family keeps generated
work on a live path to the observable `uint32_t` entry result.

The families separate several pressure axes. `arithmetic-dag` and `linear-mix`
contrast source-order fan-in with strict dependency depth; `branch-mix` adds
live diamonds; `memory-walk`, `pointer-walk`, and `alias-walk` add indexed and
potentially aliasing memory; `call-chain` and `layout-chain` add call and code
layout pressure. `stream-state` and `graph-reduce` retain loop/state and graph
lookups, while `ternary-fold` performs explicit base-three work.
`nested-state` uses a fixed four-lane inner loop. In contrast,
`grid-accumulate/v1` emits only O(nodes) token/source data but executes an exact
`nodes * nodes` live nested accumulation, with an independent O(nodes)
closed-form modulo-`2^32` oracle. This separates generated runtime-work growth
from generator/oracle complexity.

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
is required to pass the current repository C ABI/libc preflight; all thirteen
families deliberately use no unavailable guest libc routine. Published v1
replay vectors are hash-locked across later family extensions.

This is implementation substrate, not completion of the planning objective.
Broader workload families plus an end-to-end generated/executed Malbolge
fixture remain open.
