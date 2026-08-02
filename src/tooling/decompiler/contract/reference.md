# Malbolge decompiler

## Purpose

`tools/decompile/` owns reverse engineering from an explicitly selected Malbolge
profile into readable representations. The first production backend emits C23.

The tool is a decompiler/transcompiler, not a source-recovery oracle. Arbitrary
self-modifying Malbolge does not retain enough information to reconstruct the
original C program that may have produced it.

## C backend

The emitted C is a source-specialized deterministic machine with:

- explicit `A`, `C`, and `D` registers;
- caller-owned memory, input, and output buffers;
- profile-width crazy/rotate operations;
- position-dependent decode;
- atomic post-instruction self-encryption, including the post-jump target rule;
- explicit halt, non-graphical termination, invalid-encryption rejection, and
  budget exhaustion;
- an initial normalized decode listing for human inspection.

It deliberately does not call `malloc`, `getchar`, `putchar`, threads, or host
services. A caller chooses how to supply buffers and I/O.

## CLI

```text
cargo run --bin malbolge_decompile -- \
  --profile malbolge-1998 --representation c input.malbolge --output output.c
```

Omitting `--output` writes the selected representation to stdout. Profile and
representation selection are both exact and have no fallback. `c` is the first
implemented representation; the CLI is intentionally shaped for additional
readable representations without redefining decompilation as C-only.

## Museum helper

`museum_convert` is intentionally smaller and separate. It always selects the
frozen `malbolge-1998` profile and converts a locally supplied historical file to
a local C view. It does not download museum artifacts and does not add generated
C to `examples/museum/`.
