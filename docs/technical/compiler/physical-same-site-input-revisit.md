# Physical Same-Site Input Reentry

## Status

Bounded current-N15 guest control evidence, 2026-11-21. This is a raw
graphical Malbolge source, **not** a compiled C23 EOF loop. The original
mutable-C EOF checksum remains unlinked and its guest artifact unpublished.

## Frozen Guest Witness

The 120-byte source in
`tests/compiler/fixtures/same-site-four-read.malbolge` has SHA-256:

`968b4d94067bb6b38ded18aac9db77d4814d271625961cb45a34a35e038dc0a5`

It uses the canonical `malbolge-2026` profile, the normative
`ProfileMachine`, a fixed 83-step execution ceiling, and six inputs:

- Empty input.
- One NUL byte.
- One high byte `ff`.
- `01 02 03 04 05`, preserving an unread fifth byte.
- `80 00 00 ff`, including a NUL third byte.
- `01 02 ff 00`, proving the third input can emit a high byte.

There are four *physical* `/` input instructions at the same C47 code
cell, reached at zero-based steps 47, 56, 68 and 80. EOF attempts are
distinguished from successful reads. The code position is visited seven
times at steps 47, 50, 56, 62, 68, 74 and 80. Its fetched word
alternates 70, 74, 70, 74, 70, 74, 70; the corresponding decoded
instructions alternate `/` and inert `P`, and real post-step XLAT2
encryption changes the fetched cell after every visit.

The first guest-controlled C49 `i` returns directly to C47. The
second C49 `i` transfers to C73-C75 and then returns to C47. Later
C49 `i` transfers reach C44 and execute C44-C49 repeatedly.
This is a genuine bounded
**code-site** recurrence, with no host-directed state injection.
The source's M113=43 and M119=43 placement provides a first C44
return and loader-expanded M125/M131/M137=43 return operands. C45
performs a genuine `p` store into M115 at step 60. A reached C46
`<` emits the third input's low byte at step 73, or the N15 EOF
sentinel's low byte `6a` when only zero to two bytes are present.
The fourth input is consumed later, at step 80. All six streams
produce the same expected code path, with exact I/O event sites,
source-bound operand values and memory effects.

The 83-step result is **budget exhaustion**, not termination. The
machine is *not* required to halt on EOF, maintain canonical C32
locals, execute C23 arithmetic or phi transfers, nor stop at the
fourth read. In particular, a repeated code site whose live D
advances into expanding memory is not a verified reusable runtime
block or parametric C loop. Nothing here satisfies P2's requirement
to execute the complete source-C checksum.

## Negative Control and Reproduction

One legal graphical source mutation sets M113 back to 115. It
redirects the reached C49 `i` to the original C116 halt path:
exactly two actual reads occur and the VM halts at step 60. This
distinguishes a physically reached third/fourth read from a host-
fabricated input trace.

The root test `tests/compiler_same_site_three_read_guest.rs`
independently checks all 120 loader positions, the exact 83-code-site
execution path, each XLAT2 phase, source-loaded guest reads and
output, the reached store, and the negative mutation. Reproduce with
a repository-local temporary directory and the pinned Rust toolchain:

```sh
export TMPDIR="$PWD/.temp"
.dependencies/rust/1.98.1/bin/cargo.bin test \
  --test compiler_same_site_three_read_guest
PYTHONPATH=src/automation/repository/composition \
  .dependencies/python/3.14.7/bin/python3.14 -B -m unittest \
  tests.test_eof_checksum_pipeline -v
```

The second command tests the *separate* full-C23 source oracle and
its explicit compiler refusal; it is not evidence that the raw guest
fixture implements that C source. The next P2 compiler gate remains
signed EOF normalization, canonical guest C32 storage, physical
arithmetic and phi state, source-level conditional control and
correct checksum output with EOF loop termination.
