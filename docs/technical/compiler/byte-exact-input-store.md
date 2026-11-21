# Source-loaded byte-exact N15 input store

## Status and boundary

On 2026-11-21, one 15-cell graphical `malbolge-2026` guest executed a
real `/; j; p; j; p; v` chain after seven inert code cells. It stores the
entire raw input word without alteration at its second `p` destination.
This is **guest execution**, not just a symbolic source projection. The
original seven-block mutable EOF-checksum C23 program still **refuses**
publication because its signed C32 state, arithmetic, phi, branch and loop
remain unlinked.

## Frozen source and loader-derived operands

- Decoded instructions: `o` x 7, `/`, `j`, `p`, `j`, `p`, `v`.
- Physical source: `DCBA@?>n~5|3Ex6` (15 printable bytes).
- SHA-256:
  `0959164392adf70f4c597d621bee304456e79653a26505a349b4423c5f48efd9`.
- Input site: C7; data-pointer relocations: C8 and C10.
- Actual `p` sites: C9 writing M127, C11 writing M55.
- Virgin loader values: M127 = M55 = 7,174,453;
  M128 = 54. Neither data word is host-initialized.
- Search grammar: up to 94 inert prefixes, two valid graphical tail bytes,
  and the fixed six decoded instructions. Exhaustion is finite, at most
  `94 * 94 * 94` tail/phase candidates, with early decode rejection.

The first `j` reads its graphical source byte at M8 = 126 and places D at
127. The first `p` operates on virgin M127 and writes its result. The next
`j` reads M128 = 54, so the next `p` operates on virgin M55. All source
code is fetched at the same physical positions, with normative XLAT2.

The 15-trit all-one operand is `(3^15 - 1) / 2 = 7,174,453`. At each
ternary position, `crazy(1, x)` exchanges digits 0 and 1 while leaving
2 unchanged. Therefore two such operations yield exact identity for
**every** 15-trit raw value, not merely a 256-sample heuristic:

```text
crazy(ones, crazy(ones, x)) == x
```

The VM performs both writes, even when the first or second write is
idempotent. Normative `memory_delta.data` reports changed cells only;
the checker therefore uses decoded `p`, D, operand read, A and final
memory instead of falsely requiring a nonempty delta for every write.

## Reproducible bounded evidence

`tests/compiler_byte_exact_input_guest.rs` checks 256 successful byte
values, actual EOF, and two unread-suffix controls on source-loaded N15
memory. Each trace executes exactly 13 guest steps and attempts one real
input. The independent scalar trit truth table establishes the full-width
identity. A mutation of the second `p` to graphical `o` leaves M55 as the
untouched all-one loader word rather than zero, proving the final store
is essential. The current test returns in a finite budget; it does not
attempt an unbounded guest loop.

For any successful input byte, M55 is now exactly the canonical **low**
word of a C32 `getchar` result, not merely an invertible encoding. On real
EOF, M55 is the N15 sentinel `14,348,906`, **not** the required signed
C32 low/high pair `[4,644,102, 299]`. The guest does not store the
second C32 word, distinguish EOF in control flow, use mutable checksum
state, execute the C arithmetic/phi edges or repeat the read. This result
is a useful physical state-write ingredient, not P2 acceptance.

## Next integration boundary

A verified source-linked consumer must preserve this second data cell,
normalize the true EOF sentinel into the canonical two-word C32 result,
and choose the source C loop continuation from actual guest state. Merely
adding an output opcode, identifying a repeated code address or projecting
the raw sentinel as signed `-1` would not satisfy the C23 checksum.
