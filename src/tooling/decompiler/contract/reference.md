# Malbolge decompiler

## Purpose

`tools/decompile/` owns reverse engineering from an explicitly selected Malbolge
profile into readable representations. Production representations include a
typed initial-state analysis report and executable C23.

The tool is a decompiler/transcompiler, not a source-recovery oracle. Arbitrary
self-modifying Malbolge does not retain enough information to reconstruct the
original C program that may have produced it.

## Initial analysis

`--representation analysis` reports the selected profile identity and one typed
annotation per initially loaded source cell: decoded opcode, accumulator/data
effects, control-flow class, and post-step self-encryption. Indirect targets are
unresolved by design, and the report states that later self-modification
invalidates static decode assumptions.

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

The pinned Linux Clang execution suite differentially compares generated C
against the normative VM across the full memory image and `A`/`C`/`D`
registers, not only observed output. Historical-profile fixtures cover
rotate/crazy/indirect-jump post-encryption and binary input/EOF. A separate
current-profile fixture verifies the larger 15-trit geometry and EOF
low-byte output without assuming the historical 10-trit sentinel. Both
profiles also reject an indirect jump to a non-graphical encryption target
atomically, preserving the pre-step memory and registers. Rejected rotate and
crazy instructions that would overwrite their own executing code cell with a
non-graphical word likewise leave all memory and registers unchanged. A
source-admitted indirect jump into a non-graphical successor proves that the
historical profile continues without progress while the current profile
terminates. These checks compare complete states, not only status codes, but
do not establish correctness for arbitrary programs or untested profiles.

## CLI

```text
cargo run --bin malbolge_decompile -- \
  --profile malbolge-1998 --representation c input.malbolge --output output.c
```

Omitting `--output` writes the selected representation to stdout. Profile,
representation, and output selection are exact, reject duplicate options, and
have no fallback. Input is read from one opened regular file with a 1 MiB
byte ceiling (including whitespace), rejecting nonregular sources and
post-open growth beyond the ceiling before rendering. The opened source and
its pathname are rechecked after reading for stable inode, size, and write/
change timestamps, rejecting even same-length file replacement before any
rendering. Linux additionally binds the opened descriptor's canonical dentry
to the selected path before and after reading, preventing an equivalent-inode
hardlink swap through a changed parent alias. On Linux and Android,
nonblocking acquisition ensures a FIFO cannot stall the CLI waiting for a
writer. `analysis` and `c` share the same admitted profile-bound initial
model without redefining decompilation as source recovery.

## Historical conversion

Historical specimens use the general `malbolge_decompile` CLI with an explicit
`malbolge-1998` profile and C representation. The tool performs no acquisition,
redistribution, or implicit profile selection.
