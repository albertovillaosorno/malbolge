# Decompiler

## Purpose

Decompiler and museum conversion tooling.

## Ownership

This boundary is owned by `function:decompiler`.

## Prohibitions

It must not bypass another function or architectural kind boundary.

## Navigation

- [`contract/reference.md`](contract/reference.md): detailed
  pre-migration reference.
- `application/`: governed `application` parts.
- `composition/`: governed `composition` parts.
- `contract/`: governed `contract` parts.
- `domain/`: typed initial-state reverse-engineering analysis.

## Annotated reverse-engineering view

The explicit `annotated` representation emits canonical executable bytes with
full-line initial-state comments. The source is admitted under the selected
profile before rendering. Indirect jumps and future self-modification remain
unresolved; the comments are never VM semantics. Use the annotated frontend
when loading this output, not the raw `.malbolge` source loader.

```sh
cargo run --bin malbolge_decompile -- \
  --profile malbolge-1998 --representation annotated \
  input.malbolge --output input.annotated.malbolge
```

The view wraps source at most every 64 canonical bytes and also breaks after
initial halt or indirect-control cells. `canonicalize_annotated_source()`
recovers the exact original loaded bytes and gives a position-to-line map.

To inspect an annotated view, select the input format explicitly:

```sh
cargo run --bin malbolge_decompile -- \
  --profile malbolge-1998 --source-format annotated \
  --representation analysis input.annotated.malbolge
```

The default remains `--source-format raw`; the decompiler never infers
comment semantics from a filename or retries invalid raw source as annotated.
The existing 1 MiB source-file read cap applies to both input formats.
