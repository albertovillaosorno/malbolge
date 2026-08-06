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
- profile-declared input/output instruction bytes and non-graphical behavior;
- position-dependent decode;
- atomic post-instruction self-encryption, including the post-jump target rule;
- explicit halt, non-graphical termination, invalid-encryption rejection,
  output-capacity exhaustion, and budget exhaustion;
- an initial normalized decode listing for human inspection.

It deliberately does not call `malloc`, `getchar`, `putchar`, threads, or host
services. A caller chooses how to supply buffers and I/O. Output capacity is
checked only when an instruction emits a byte; it is not required to equal the
step budget, and exhaustion rejects that transition before encryption, pointer,
or output mutation commits.

## CLI

```text
cargo run --bin malbolge_decompile -- \
  --profile malbolge-1998 --representation c input.malbolge --output output.c
```

Omitting `--output` writes the selected representation to stdout. Profile,
representation, and output selection are exact, reject duplicate options, and
have no fallback. `c` is the first
implemented representation; the CLI is intentionally shaped for additional
readable representations without redefining decompilation as C-only.

## Historical conversion

Historical specimens use the general `malbolge_decompile` CLI with an explicit
`malbolge-1998` profile and C representation. The tool performs no acquisition,
redistribution, or implicit profile selection.
