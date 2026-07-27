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
Future DOOM-specific probe construction and compatibility policy stay in the same
domain module. Generic matching, source binding, reconstruction, and Rust emission
remain under `algorithms/diff/`.

`amalgamate.py` reserves the second consumer. It remains intentionally
unconfigured until normalized quality output and a semantically accepted local
single-file oracle exist. At that point the same generic engine can generate
`amalgamate/main.rs` without teaching `algorithms/diff` anything about DOOM.

The intended invocation is from the repository root:

```text
python -m algorithms.doom.generator.quality
```

`algorithms/diff` now implements exact authoring, source-span reuse, canonical
identity primitives, stable anchors, and tree admission. `write_algorithm()` still
fails closed without writing `quality/main.rs` until behavior admission, source
binding, and Rust emission are implemented.
