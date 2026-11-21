# First-input memory reentry after a second physical read

## Evidence status

Bounded, source-loaded N15 guest evidence (2026-11-21). The 63-cell program
**does not** compile the original C23 mutable EOF checksum: no signed C32
normalization, source-bound arithmetic, branches, phi copies or EOF loop are
linked. The unchanged seven-block checksum still fails closed at the physical
linker. This experiment isolates a necessary stateful primitive: the first
input can remain in guest memory after a second `/` overwrites the accumulator,
and a later physically executed `j` can actually read that stored first value.

## Source and physical dataflow

`build_byte_exact_two_input_reentry_source` extends the existing source-loaded
27-cell exact-raw-input store/reentry primitive. Both sources use the current
N15 profile with 14,348,907 15-trit words, not forged VM registers or
host-preloaded data. The new program places a reached halt at C60 and two
**unreached** graphical loader-tail bytes `%H` at C61/C62. This phase preserves
virgin M121 and M73 = 7,174,453 (all trits one), and M78 = 72. Graphical
code bytes are generated with the existing position-sensitive encoder.

Its relevant reached physical operations are:

| Code site | Actual opcode | Physical requirement or consequence |
| --- | --- | --- |
| C13 | `/` | First guest input, or true N15 EOF word 14,348,906 |
| C15/C17 | `p` | Two guest crazy writes; first raw input into M73 |
| C22 | `j` | Virgin M78=72 resets D to 73 for continuation |
| C23 | `o` | Advances D without destroying the stored first word |
| C24 | `<` | Outputs the first input's low byte |
| C25 | `/` | **Second** input overwrites A, but not M73 |
| C26 | `<` | Outputs the second input's low byte |
| C28 | `j` | Re-reads untouched M78=72 and resets D to 73 |
| C29 | `j` | Reads saved first input M73; D becomes raw + 1 mod N15 |
| C60 | `v` | Halts after the fixed finite continuation |

After C29, A still holds the second physical input, while D depends on the
first. This is distinct from a mere raw echo or a host-selected branch:
the normative trace includes the C17 data-write and C29 physical data-read
at identical M73. For a first true EOF, D wraps to zero; for a byte `x`,
D becomes `x+1`. No further data instruction consumes D in this program,
so this is not a compiled conditional or arithmetic operation. EOF is not
treated as the C23 `int` value -1; low-byte echo of raw N15 EOF is 0x6a.

## Verification and negative controls

`tests/compiler_signed_eof_first_storage_guest.rs` starts from an actual
source-expanded VM image, then independently runs fresh real VM states with
unmodified source-derived memory. Every trial checks two reached input steps
at the authenticated C13/C25 code addresses, two output steps at C24/C26,
physical data read and write values, the saved first input's one M73 write,
its later C29 read, final registers, consumed bytes, and exact halt.

The finite domain includes true first EOF, 12 selected first-byte classes
paired with varied second bytes, six cases
with true second EOF, and four longer streams with unread input suffixes
(23 streams in total). The VM step ceiling is 61 transitions per stream. These
paths
sample EOF/byte boundaries and varied two-read states; they are
**not** an exhaustive 257×257 two-input Cartesian product.

One-cell negative controls replace C17 `p`, C28 `j`, or C29 `j` with graphical
`o`. The C17 mutation destroys both the exact saved value and the first echo;
the C28 and C29 mutations **retain both output bytes** on the selected stream,
but destroy the saved-word reentry. Matching output alone therefore cannot
substitute for the memory/control proof.

Reproduce with:

```sh
.dependencies/rust/1.98.1/bin/cargo.bin test --locked \
  --test compiler_signed_eof_first_storage_guest
.dependencies/python/3.14.7/bin/python3.14 -B -m unittest \
  tests.test_eof_checksum_pipeline -v
```

## Remaining physical-linking obligations

This finite helper neither stores the two-word signed `getchar()` result in
source-reserved C32 SSA cells nor checks C phi/branch semantics. To progress
toward the original C23 EOF checksum, a real linker must route the retained
raw word into full-width source state, combine it with the next input in
genuine guest arithmetic, implement the signed EOF guard and conditional
checksum update, restore live code/data/register state across an actual loop
backedge, and match all five native oracle streams before publication.
EOF-terminating the two-read helper is not itself proof of an arbitrary-byte
loop or source-C compilation.
