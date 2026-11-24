# Source-Loadable Indirect Guest Continuation

## Status (2026-11-24)

Bounded physical pre-link capability, **not** C23 source compilation.
The unchanged seven-block mutable EOF checksum still refuses guest target
lowering, and P2 remains open.

## Exact problem

In the current 15-trit profile, Malbolge `i` reads `M[D]` as its new
code pointer; the step then increments that pointer before fetching the next
instruction. A source-contained pointer word must itself be an ASCII
graphical byte that decodes to a **legal loader instruction at the pointer
cell's own position**. A proposed target address alone cannot prove that
its pointer word survives source admission. Already-executed code, live
pointer data, and future code cells must also remain disjoint from patches.

`plan_source_loaded_indirect_suffix` makes one narrow preparation reusable:

- It accepts an already source-admitted N15 graphical program and one
  source-resident, candidate pointer-cell position.
- It explores a finite code window in increasing landing-address order,
  with a bounded terminal straight-line suffix of `o`, `/`, `<` and final
  `v`. No jump, crazy, rotate or recursive branch is placed in this leaf.
- It requires `landing - 1` to be a printable graphical source byte **and**
  decode to a valid opcode at the exact pointer-cell position. It refuses
  protected and out-of-bounds code positions and re-admits the entire
  patched graphical source.
- It returns only a candidate source, operand word and target address. It
  never asserts that an `i` is reachable, points D to that word, or executes
  an unmodified, unencrypted code leaf. The caller must independently prove
  those conditions in normative VM traces before any target publication.

Bounds: at most **4,096 source cells**, **32 leaf opcodes**, one finite
landing interval, and **94** possible graphical pointer byte values.
The candidate is deterministic; it does not search arbitrary guest state.

## Physical witness after an actual stateful fold

The reproducible existing 135-cell N15 source starts with the original
C10 input and output, writes a first-input-dependent word at M106 via C30
`p`, reads a second word at C82, and folds both genuine input words using
C87 `p` into M106. C88 outputs the fold's low byte. An actual C94 `i`
reads an unmodified, source-resident M111 operand. Previously that operand
was 81 and jumped to the encrypted C82 halt.

The initial proposal to set M111 to 111 (for C112) **failed** source
admission: byte 111 at position 111 decodes to a forbidden opcode. The
finite placer instead picks **M111=116**, which decodes as `*` when loaded
at C111. The already-reached guest `i` at C94 physically reads that word,
encrypts code cell C116 and continues at **C117**. Unreached C117/C118/C119
can independently encode `/`, `<`, `v`, respectively. No intermediate pointer
word, prior code cell or first/second input fold instruction is modified.

The normative VM executes exactly **98 steps**, reads input at C10, C82
and C117, outputs at C11, C88 and C118, and halts at C119. C30 and C87
still write their original guest-computed values, and M106 remains intact
after the third read. A separate fifteen-trit digit-table oracle verifies:

- `first = byte0` or raw N15 EOF;
- `saved = crazy(121, first)`;
- `fold = crazy(saved, byte1_or_EOF)`;
- output is the three low bytes of `first`, `fold`, `byte2_or_EOF`.

The physical test checks nine differing streams, including empty, truncated,
high-bit, NUL, and unread-suffix inputs. Another **257-case** bounded guest
matrix fixes the first two bytes and varies every third byte plus real EOF;
it checks the same 98-step halt, input consumption, output and preserved M106.
A different leaf `<;v` uses the **same placement function** to output the
existing fold without a third read and halts in 97 steps.

Negative controls show that forcing the desired but loader-invalid C112
pointer fails, protected windows and malformed sources refuse, an alternate
source-valid landing is selected when the first is protected, and mutations
to the actual pointer cell or landed input opcode remove the third-read
witness. The guest paths are not inferred from the scalar oracle.

## What is still missing

This is a successful **physical continuation placement** of a bounded
source-loaded computation, not source-C input-loop lowering. `crazy` of
two raw N15 input words is not C23 unsigned XOR/add or signed `getchar()`
normalization. The suffix is a linear guest I/O leaf, not a phi pad, loop
backedge, variable-layout branch or final checksum. Its source-level
operation and data dependencies remain unlinked to the original C program.

The next P2 linker must prove the complete source-locked operation graph:
source SSA frame writes, typed arithmetic, parallel predecessor copies,
signed EOF comparison, conditional code transfer, a live backedge and the
final checksum byte, with the normative VM and the unchanged five native
C23 `-O0`/`-O2` input controls. A successful bounded leaf alone cannot
retire any of those obligations.

## Reproduction

```sh
.dependencies/rust/1.98.1/bin/cargo.bin test --test compiler_indirect_source_suffix
.dependencies/python/3.14.7/bin/python3.14 -B -m unittest \
  tests.test_eof_checksum_pipeline -v
```

The second command tests the intentional original-checksum refusal and
non-publication, **not** an accepted complete compiler target.
