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
registers, not only observed output. Both historical and current profile
fixtures cover arithmetic, rotate/crazy and indirect-jump post-encryption;
historical and current fixtures also cover binary input and atomic output
capacity refusal. An all-profile regression refuses the second output after
one byte commits, preserving the first output and full machine state from a
two-step baseline. Frozen 2026.1/.2/.3 profiles exercise their selected input/
output instructions, EOF words, and 10-/14-trit geometry through the same C-vs-
VM binary I/O check. A separate all-profile, 513-instruction differential
replays all 256 binary values in order as actual guest input/output, crossing
position-dependent decode phases repeatedly. The executable C result must
match the normative VM's entire output and input cursor, the final `A`/`C`/`D`
registers, and all 513 reached (post-encryption) source cells. The same
all-profile harness then restricts output to 255 bytes, verifies 255 committed
outputs, rejects the 256th without overwriting its guard byte, and compares
all reached code cells and registers with the VM's 511-step prefix. A third
run exhausts input only on the 256th read and verifies the profile-specific EOF
low byte and complete post-encryption code/register state against the VM. These
are bounded stream, late-EOF and atomic refusal results, not arbitrary program
equivalence.
Current-profile fixtures verify the larger 15-trit
geometry and EOF low-byte output without assuming the historical 10-trit
sentinel. Both profiles also reject an indirect jump to a non-graphical
encryption target atomically, preserving the pre-step memory and registers.
Rejected rotate and crazy instructions that would overwrite their own
executing code cell with a non-graphical word likewise leave all memory
and registers unchanged. A source-admitted indirect jump into a non-graphical
successor proves that the
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
post-open growth beyond the ceiling before rendering. A reader must report
exactly the number of bytes collected, even when the source inode and bytes are
otherwise unchanged. The opened source and its pathname are rechecked after
reading for stable inode, size, and write/change timestamps, rejecting even
same-length file replacement before any rendering. Linux additionally binds
the opened descriptor's canonical dentry to the selected path before and after reading, preventing an equivalent-inode
hardlink swap through a changed parent alias. On Linux and Android,
nonblocking acquisition ensures a FIFO cannot stall the CLI waiting for a
writer. `analysis` and `c` share the same admitted profile-bound initial
model without redefining decompilation as source recovery.

## Historical conversion

Historical specimens use the general `malbolge_decompile` CLI with an explicit
`malbolge-1998` profile and C representation. The tool performs no acquisition,
redistribution, or implicit profile selection.
