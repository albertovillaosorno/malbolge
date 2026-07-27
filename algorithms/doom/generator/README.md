# DOOM Algorithm Recipes

This directory contains thin DOOM-specific recipes that configure generic
generators. A recipe declares **what** source/oracle pair and policy to use; it
does not implement the diff algorithm itself.

`quality.py` is the first consumer. It configures `algorithms/diff` to learn the
quality transformation from the local root `doom/` source and the ignored manual
oracle under `algorithms/doom/quality/in/doom/`. Its output is
`algorithms/doom/quality/main.rs`.

`doom.py` now owns the Linux DOOM C/H identity adapter. It selects only the
`linuxdoom-1.10` C/header subtree, excludes WAD/IPX surfaces from source identity,
and emits a framed C preprocessing-token view that ignores comments and ordinary
formatting without erasing token boundaries or preprocessor line termination.
The domain facade now also exposes the first executable behavior program.
`behavior_probes.py` defines a Windows x86-64 / pinned LLVM 22.1.8 fixed-point
identity probe. It compiles the candidate mirror's real `m_fixed.c` with a
repository-owned freestanding harness, links a no-CRT PE, executes it, and records
the exit code as behavior evidence. The harness and header shims contain no copied
DOOM source. Additional compatibility/bug probes stay in the DOOM domain. Generic
matching, probe execution, source binding, reconstruction, and Rust emission remain
under `algorithms/diff/`.

`amalgamate.py` reserves the second consumer. It remains intentionally
unconfigured until normalized quality output and a semantically accepted local
single-file oracle exist. At that point the same generic engine can generate
`amalgamate/main.rs` without teaching `algorithms/diff` anything about DOOM.

The intended invocation is from the repository root:

```text
python -m algorithms.doom.generator.quality
```

`algorithms/diff` now implements exact authoring, source-span reuse, canonical
identity primitives, stable anchors, tree admission, behavior evaluation, portable
process probes, threshold key unlock, RFC 8439 payload protection, and protected
exact-plan materialization, and deterministic std-only Rust emission for the exact
baseline. `write_algorithm()` still fails closed without replacing `quality/main.rs` because the DOOM recipe now explicitly requests
`TransformMode.COMPATIBLE`; that runtime still needs consumer identity/admission and
broader compatibility/bug coverage. The generic public API can already emit
`EXACT_BASELINE` transforms without changing this product-level choice.
