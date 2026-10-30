# Source-Selected HALT/ECHO Dispatch (Research Pilot v8)

## Falsifiable question

Can **one unchanged native Malbolge code island** select two different
complete echo workloads from a separate loaded graphical operation,
without rewriting the source-bound CEB2 descriptor? If guest output,
actual indirect-jump operands, physical memory writes, or host admission
fail for either workload, the design is invalid even as a bounded pilot.

## Exact candidate design

Both candidates use the current `malbolge-2026` profile, the same 227-cell
loader-addressed source layout, and an independently SHA-256-source-bound
38-byte CEB2 descriptor packed into **102 actual graphical code/data cells**
at positions 125–226. Source cells 0–123 are byte-identical for the two
original canonical echo programs. Their native guest instructions are:

| Guest source cell | Purpose |
| --- | --- |
| 0 | Reached `j` relocates D to 41 |
| 1–80 | Reached `o` advances D to 121 |
| 81 | Reached `i` reads first opcode `M[121]=90` |
| 88 | Fixed native `v` HALT handler |
| 91–93 | Fixed `/`, `<`, `i` input, output, second dispatch |
| 105–107 | Fixed `/`, `<`, `v` second echo handler |
| 121 | First source data opcode, graphical 90 |
| 124 | Second source data opcode, graphical **87 or 104** |
| 125–226 | Source/profile-bound 102-cell CEB2 payload |

After `i@81`, C becomes 91. The first `/` and `<` each advance D, so the
second `i@93` reads the **actual physical** source byte at `M[124]`.

- `M[124]=87` is loader-valid and makes C=88, so the guest executes the
  shared `v@88` HALT handler after just one byte echo.
- `M[124]=104` is loader-valid and makes C=105, so the same native code
  island executes `/@105`, `<@106`, `v@107` for two byte echoes.

Both jump operands target *code* cells for mandatory XLAT2 mutation
(90 then 87/104); neither alters its source opcode or CEB2 data. The
host verifies that the second opcode agrees with the independently
reconstructed source-bound count. An unbound one-byte change must reject,
**even though the changed guest still branches to the other handler**.

## Recorded acceptance and limitations

The exact two-way experiment is pinned in `pilot-v8.toml` and independently
replayed by `tests/compact_guest_conditional_dispatch.rs` using the
normative VM and actual general Malbolge CLI. Direct compiler output
is a separate reference program, not produced by this dispatcher.

Observed normative VM traces verify *both* real `i` reads and physical
source-word writes. Successful input `[0,255]` and `[128,129]` matches
separately compiled direct source in stdout and consumed input on both
variants. The direct 3/5-step programs are smaller than the two guest
variants, which require **86/88 guest steps and 227 source cells**.
Independent external general CLI capsules report the same output and
steps. A loader-valid opcode-only mutation changes real guest output
from one byte to two, while failing host admission. Other invalid original
counts, alternate legal glyphs, changed code or descriptor data, wrong
source identities and malformed extents all reject at the host boundary.

A second native VM regression restores each code image from an independently
validated complete initial memory state, then compares guest and direct
behavior across six input streams for **both** original pair counts: EOF,
single byte, exact two bytes, and trailing surplus input. All 12 cases
agree in stdout, consumed bytes, termination and exact step counts while
preserving every CEB2 cell. Empty input does not consume a missing byte;
extra input is left unread. This is bounded I/O evidence, not a proof for
all possible byte streams or arbitrary source operations.

This is still an *unrolled* program with one explicit branch, not an
arbitrary bytecode interpreter: the guest does not calculate three-bit
ranks, read the CEB2 count, maintain an instruction pointer, repeat a
shared handler, loop, or compute its own SHA-256 source authentication.
The guest code is constant, but the two data fields and the CEB2 tail
change with the bound source program. Any source count outside 1 or 2
is deliberately unsupported. No code-size, step-count, compilation-time,
resident-memory, or verifier-complexity advantage is claimed for general C.
