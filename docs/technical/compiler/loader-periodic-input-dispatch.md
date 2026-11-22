# Loader-periodic indexed input routing

## Result and strict boundary

On 2026-11-21, one 27-cell graphical `malbolge-2026` source reads a real
input word, writes the *exact raw word* with two actual `p` instructions,
reloads it through a live `j`, and uses a further reached `j` to read
`M[(input + 1) mod 14,348,907]`. This is an input-dependent data-pointer
transfer in the normative guest VM, not host-selected output or a source-C
branch. The six-periodic virgin-loader region provides an exact high-byte
**parity partition of the resulting data pointer**, but it does not
implement the source C23 `(current & 1)` branch or a checksum loop.

The original seven-block mutable EOF-checksum C23 program still refuses
physical publication. Its signed C32 result, dynamic arithmetic/phi writes,
branch destinations and repeatable EOF loop remain unlinked.

## Frozen source and physical trace

- Source: `DCBA@?>=<;:98hx/v-210/pon%H` (27 printable bytes).
- SHA-256:
  `90294cbe5e2f3e6fc7f8fffd9becfcba9192699ccbe06d68fea814cd3d0b06f2`.
- C13 executes `/`; C15 writes the first input-dependent intermediate to
  M121; C17 writes the *exact* input or raw N15 EOF to M73.
- C22 reads virgin M78=72 and returns D to M73. C23 reads the now-written
  M73 and sets D to `(raw input + 1) mod 14,348,907`.
- C24 executes a genuine `j` from graphical byte `n`, reads the indexed
  *live* memory word and relocates D again. Its previous `v` was the only
  changed decoded operation in the first 25 code cells. C25/C26 remain
  unexecuted graphical loader-seed bytes `%H`.
- The checked window is exactly 25 steps, deliberately ending before a
  possible next instruction; a step-budget stop is **not a guest halt**.

A separate scalar base-three recurrence starts with `(37, 72)` and
produces the following first six loader words from M27:

| Address | Value |
| --- | ---: |
| M27 | 7,174,489 |
| M28 | 36 |
| M29 | 7,174,489 |
| M30 | 72 |
| M31 | 7,174,453 |
| M32 | 72 |

The next six generated words repeat this exact sequence. It is important
that the initial source tail `(37, 72)` need **not** itself be the periodic
state: the periodicity begins at M27. Confusing these two states produced
an incorrect first test assertion, which was corrected before acceptance.

For the complete high-byte range `128..=255`, the reached C24 operand
address is `129..=256`. No earlier executed code or data write changes
that region. Therefore the actual indexed read equals the virgin-loader
recurrence. If the input byte is even, its word is either 7,174,489 or
7,174,453; if odd, it is 36 or 72. The reached `j` then sets D to the
read word plus one, keeping the two parity classes disjoint. This is a
**data-pointer partition**, not a reached `i` code-pointer branch.

## Aliasing prevents a total parity contract

The same proof **cannot** be extended blindly to low bytes:

- Input `0x48` (72) indexes M73. C17 has already overwritten that exact
  word with 72, so C24 sees 72 rather than the virgin 7,174,453.
- Input `0x78` (120) indexes M121, already written by the first `p`.
  Its actual value differs from the virgin all-one operand.
- Earlier input values can index already-encrypted code cells, source
  bytes or initial pointer-setup cells; a source loader recurrence is
  not a substitute for the *live* machine-memory version.
- True EOF is the full-width raw word 14,348,906, not a byte value.
  Its C23 signed result is not obtained by interpreting pointer zero as
  signed `-1` or as an ordinary parity class.

A production table-indexing linker must record the true input-write
footprint, code XLAT2 events and reached indexed reads. It must either
prove that every admitted index remains untouched or model the actual
live value per entry; treating source-derived addresses as immutable ROM
would be unsound. An `i` transfer would additionally need valid code
landing pads and source-C branch equivalence for all 257 byte/EOF
classes. None is established here.

## Whole-byte scalar census (not whole-byte guest parity)

A closed 256-byte scalar audit of this **same** source accounts for all
25 sequential fetched code-cell XLAT2 writes, the two original source
tail bytes, the two live `p` data writes, and the rest of the generated
loader. Reading the indexed cell and comparing its word to one million
would partition 242 of 256 bytes by parity, but **14 bytes disagree**:

- Bytes `0, 2, 4, ..., 24` index encrypted graphical code (M1..M25,
  where M25 is the untouched source tail); all 13 are even but their
  indexed operand is a small graphical word.
- Byte `72` is even but indexes input-overwritten M73=72, not the
  original loader all-one word. M121 is also mutable but its collision
  for byte `120` remains in the large-value parity class.

The auditor's 256 index classes cover 24 encrypted-code positions,
two source-tail positions, 228 virgin loader positions, and two live
store aliases. The 128 high-byte VM tests and two alias-specific VM
traces confirm the reachable physical read paths. This audit is a
**necessary negative result** for treating this fixed indexed lookup
as a total C parity primitive, not proof of a physically executing
conditional branch for the other 242 cases. EOF is a separate raw
profile sentinel and cannot be counted as a successful C byte.

## Finite verification and next capability

`tests/compiler_loader_periodic_dispatch_guest.rs` independently derives
the six-word recurrence from the crazy-trit table and executes **131**
source-loaded N15 guest cases (128 high bytes, the two alias witnesses,
and EOF), each through 25 real instruction traces. It checks both actual
stores, reentry, indexed read, input consumption, absence of host output
substitution, and exact D. A graphical C24 `j`-to-`o` mutation removes the
routing on two opposite-parity bytes. The first 25-step guest prefix is
input-independent in its fetched code positions and two data-write
addresses; only the raw values differ. The six physical input-residue
classes and the independent full six-cycle calculation establish the
bounded high-byte partition. The same suite also closes the 256-case
scalar alias census and explicitly refuses all 14 failing byte classes.

This experiment is finite and positive only for the stated pointer
transfer. It does not warrant acceptance of any C expression or guest
arithmetic operation. The next real compiler step is to compose an
all-byte plus EOF-safe branch with physically verified mutable C32 state,
then link arithmetic, phi transfers and a repeatable input loop for the
*same* frozen P2 source-C checksum.
