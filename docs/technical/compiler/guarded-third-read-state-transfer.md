# Guarded Third Read: Physical Pointer Reset and Return Limit

## Status

Bounded negative N15 compiler-layout experiment, 2026-11-21. The original
source-C mutable EOF checksum remains unlinked; no C23 guest artifact was
published. The executable witness is
`tests/compiler_guarded_third_state_transfer.rs`.

## Actual Guest Experiment

The starting point is the source-loaded 132-cell guarded third-input program
from `build_two_input_class_state_with_guarded_third_read_source`. It already
performs real C53 and C63 signed reads, conditionally reads C101 on success
of the second read, and writes input-derived class and EOF scratch words.

Three independently source-encodable changes attempt the missing guest
continuation. At C71, first-pass `<` encrypts into second-pass `j`;
first-pass C104 `o` avoids the original second-pass `v` halt; first-pass
C112 `p` avoids an otherwise reached second-pass `i`. The six-period
loader source tail stays the original `-}` at C130 and C131.

The normative N15 VM confirms the second-pass C71 `j` changes the actual
D register from 7,174,359 to **135**. On byte stream `03 04 05`, the
physical reads are C53, C63, C101, and output is `03 86 9a`. The
third-byte accumulator A reaches **5** at second-pass C114 `i`, but its
attempted transfer requires encrypting non-graphical M134=7,174,449.
The VM correctly returns `InvalidEncryptionTarget`, not a fabricated loop.
On the truncated input `03`, only C53 and C63 read; the EOF arm emits
`03 79 86` and halts after 119 steps. It never executes the C71 reset.

This is a genuine control/data-pointer transition while preserving the
third input event. It does not establish output of the third byte, a
repeatable state relation, source-C C32 state or the checksum loop.

## Independent Loader-Tail Bound

The same test independently enumerates the 8 source-valid graphical
opcodes at each of C130 and C131: exactly 64 two-byte tails. For each
pair, an independent 15-trit crazy table computes the first six
loader-expanded words. The untouched M7,174,402 is in recurrence phase 4
and is **never graphical** under this grammar. Real source loading
cross-checks the original `-}` and one modified tail, while the scalar
enumeration checks all 64 candidates.

Thus simply replacing the terminal two source bytes cannot make this
particular phase-4 operand an executable graphical code target. This
necessary-condition failure is limited to untouched generated memory,
this source length and these source-valid tails. Guest data instructions,
other pointer paths, different source layouts or independent verified
code blocks remain open.

## Reproduction and Exit Condition

Run `cargo test --test compiler_guarded_third_state_transfer` with the
repository-pinned Rust compiler, and independently run
`tests.test_eof_checksum_pipeline` with the pinned Python 3.14 host.
The two new tests must check the physical N15 trace, byte/EOF read
chronology and exact pointer/error values, plus the 64-case recurrence.
Neither a bounded failed transfer nor a correct compiler refusal retires
P2. The exit condition is still the original complete C23 mutable
EOF checksum executing on the normative guest with native-oracle parity.

## Guarded Third-Read Continuation Search (2026-11-21)

The follow-up witness `tests/compiler_third_return_search.rs` freezes the
same 132-cell N15 source, with C71 first-pass output, C104 first-pass no-op,
and C112 first-pass crazy write, plus the binary stream `03 04 05`. It
runs the normative VM with a **240-step ceiling per candidate**. A real third
input requires observed read sites C53, C63, C101 in that order. Both
searches reject a merely terminating path unless it can sustain the required
guest behavior.

**Loader-tail search:** Exhaust all 8 source-valid graphical instructions
at C130 times all 8 at C131: 64 pairs. An independent 15-trit crazy
recurrence reconstructs the six-period loader-expanded memory. Every
surviving three-read candidate is also reconstructed through the actual
strict VM loader, with all memory cells compared. Only three tails reach
the third read:

- `(45,125)`: real output `03 86 9a`;
- `(63,125)`: real output `03 47 a6`;
- `(126,125)`: real output `03 86 9a`.

All three subsequently fail with `InvalidEncryptionTarget`. The other
61 tails fail to preserve the three-read chronology. This is not evidence
against other source lengths, data writes, or alternative code layouts.

**Single-code-cell search:** Keep the original `-}` tail and fixed C71,
C104, C112 changes. For every position C65..C75 and C102..C114,
substitute each of the seven *different* loader-valid decoded opcodes:
168 candidates. Of these, 54 preserve all three real reads. Only two
avoid `InvalidEncryptionTarget` after the third read:

- C70 `j`: terminates at a non-graphical cell after 147 guest steps,
  output `03 86`;
- C104 `*`: halts after 175 guest steps, output `03 86 9a`.

Neither emits the third input byte or establishes a reusable return
state. The other 52 three-read candidates fail at an invalid encryption
target. This search covers one additional code-cell edit in exactly
these 24 positions, not simultaneous edits, guest data-written opcodes
or a different runtime architecture.

Run both bounded tests with
`cargo test --test compiler_third_return_search` and the pinned
repository Rust toolchain. Source-C checksum acceptance remains under
`tests.test_eof_checksum_pipeline`: its O0/O2 C23 parity and correct
unlinked-target refusal are not target-execution success. Next work must
seek a different verified, repeatable physical control-and-state
contract rather than enlarging this finite candidate search by default.
