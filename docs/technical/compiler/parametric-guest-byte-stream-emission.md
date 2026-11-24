# Parametric guest byte-stream emission

## Status

Partial, scheduled in P2 under the current phase roadmap. One original
complete Fibonacci C program now reaches the guest VM; generalized source-C
and arbitrary byte-stream support are not implemented. References to the old
"P0" priority in the dated experimental evidence below are historical.

## Purpose

**First experiment, then verify.** Try one demanding, complete C program
before increasing output-byte counts or the verification fixture inventory.
Repair the first real compiler gap and rerun the same whole program; only
after success introduce a generated verification matrix and independent
end-to-end oracle. The maximum N is not a product progress metric.

## Scope

The existing corpus is useful regression history and may remain SHA-pinned.
A new example must establish a previously untested semantic boundary.
Increasing the byte count from 48 to 49 without such a boundary is not
an acceptable completion milestone.

The work belongs to the C frontend, typed lowering, layout backend, VM,
and their tests. It does not require a single enormous hand-authored C file
or hundreds of individual documentation pages.

## Current Behavior

### Guest pointer proofs bind the specific input read (2026-11-24)

A bounded source-authenticated pointer verifier now records individual
reached `/` transition indices in the proven M143 pointer lineage. Its
input-site-constrained API accepts the existing single-input C53 branch,
and separately the two-read C63 branch whose second successful byte or EOF
selects the physical C45/C126 continuation. All 256 second-byte classes,
truncated EOF and extra bytes use real N15 guest halts; forged first-input
C53 and unreached C101 provenance refuse. The new exact-origin API also
rejects an extraneous first-read C53 in the claimed set for the C63 branch.
The origin set is conservative physical dataflow, not C predicate equivalence. No C23 local state,
checksum computation or loop has been linked. Evidence:
`docs/technical/compiler/source-indirect-guest-suffix.md` and
`tests/compiler_indirect_source_suffix.rs`.

### Guest-written signed-input EOF branch is physically verified (2026-11-24)

A reusable source-authenticated verifier now accepts *full-width guest-written*
indirect pointers, beyond the prior graphical source-resident suffix case.
The existing strict 132-cell N15 signed-EOF classifier writes its actual
input-derived C45/C126 pointer to M143 at C82, and C114 `i` reads it to
choose the real successful-byte or EOF arm. All 256 byte classes and true
EOF, plus two trailing-input controls, execute the correct normative path
and true halt. An idempotent EOF `p` is retained as a real write even when
the VM reports no changed-value memory delta. The opaque proof records
input, source, actual pointer/write, destination, output and the full trace.
This is finite *physical input-dependent control*, not a linkage of the
original C23 signed comparison, arithmetic or seven-block checksum CFG.
The original complete checksum continues to refuse guest publication.
Evidence: `docs/technical/compiler/source-indirect-guest-suffix.md` and
`tests/compiler_indirect_source_suffix.rs`.

### Fourth cumulative guest fold emits its own fifth byte (2026-11-24)

The previously unobservable fourth cumulative M106 update now has a
source-valid output and true halt. A 135-cell guest adds C60/C61 `j`
rerouting through encrypted C59 and existing M105, compensating for a
source-valid C134 `v` replacement that otherwise breaks an earlier C58
pointer. The original three-input fold survives, and C132 `p` folds a
real fourth input into M106. Reached C133 `<` outputs its low byte,
followed by C134 `v` at **113** normative N15 steps. Input `03 04 05 06`
emits `03 31 05 3a 53`, storing M106=7,174,483.

The independent trit oracle, all 257 fourth byte/EOF classes, all 768
prior-byte marginals, six length/EOF controls, 128 frozen-seed cross-input
streams, exact guest trace and seven altered-source negatives authenticate
this **finite** physical computation and output. The original C23 checksum
was attempted again and still refuses its unlinked seven-block CFG without
publishing a guest target. No C23 signed EOF, arithmetic, dynamic source
branch, phi or guest loop has been linked. Evidence:
`docs/technical/compiler/source-indirect-guest-suffix.md` and
`tests/compiler_indirect_source_suffix.rs`.

### Fourth guest input now accumulates into M106 (2026-11-24)

Another strict 135-cell N15 source uses `/<oooojpp<*/jjopv` and a
source-valid M110=117 to direct C129/C130 `j` through the **encrypted**
C118 output word. C132 `p` then computes
`crazy(prior_three_input_M106, fourth_raw_input)` into the original
M106 state, and a genuine C133 `v` halts in **112** steps. The
independent oracle verifies all 257 fourth byte/EOF classes, all three
256-class prior-input marginals, six truncated/extra vectors, exact VM
traces and five source-valid mutations. The original four outputs stay
unchanged; the fourth cumulative value is stored but **not yet output**.
A terminal `i` variant preserves M106 through a 139-step encrypted-code
return, but its fifth output is constant, not computed from the fold.
This is real four-input cumulative guest storage, still not C23 arithmetic,
EOF normalization, dynamic C flow or the complete source checksum.
Evidence: `docs/technical/compiler/source-indirect-guest-suffix.md`.

### Fourth input performs an observable guest computation (2026-11-24)

The graphical 135-cell indirect suffix now ends `...jojp<i` instead of
`...jojpv`. The reached fourth raw input is folded with encrypted C40
via a real C132 `p`, output at C133 `<`, and returned through the
source-protected C134 `i` into encrypted code at C59 and an authentic
C82 `v` halt. For `03 04 05 06`, output `03 31 05 3a 4d` has a fifth,
**fourth-input-dependent** byte, and the guest halts after 137 steps.
All 257 fourth-byte/EOF classes, 768 prior-byte marginal cases, five
truncation/extra-byte controls and three negative source mutations check
the physical state and independent ternary oracle. The result is
meaningful guest computation and encrypted-code control composition,
not a source-C `getchar()`/EOF loop, signed conversion, source-typed
arithmetic, fourth cumulative M106 fold or published C23 checksum.
Evidence: `docs/technical/compiler/source-indirect-guest-suffix.md` and
`tests/compiler_indirect_source_suffix.rs`.

### Real encrypted-code control return after three guest inputs (2026-11-24)

A source-admitted terminal `i` now extends the genuine 135-cell three-input
N15 fold: C128 physically reads untouched source/data M109=66 and returns
via already encrypted C67..C82 to a real C82 `v` at **123 guest steps**.
The previous input-dependent M105/M106 crazy computation and all four
outputs survive. The normative interpreter and independent fifteen-trit
oracle agree for all 257 third-byte/EOF classes, 256 first-byte cases,
256 second-byte cases and four truncated streams. Source and control
mutations reject counterfeit reentry. The indirect suffix planner now
permits **terminal** `i` as a candidate with a mandatory separate guest
control proof; interior `i` remains refused. This is finite physical
code/data reentry, not a reusable checksum loop or C23 control flow.
Evidence: `docs/technical/compiler/source-indirect-guest-suffix.md` and
`tests/compiler_indirect_source_suffix.rs`. The complete C23 checksum
continues to fail closed without an emitted guest artifact.

A bounded C128 indirect-target census checks all 94 graphical M109
operand candidates: eight source-valid, six eventual guest halts, and
three additional fourth guest reads under 180 steps. Two valid-halt
fourth-read variants produce output **independent** of the fourth input
across five EOF/binary streams. They do not implement mutable C input
processing, arithmetic or a checksum. See the physical-suffix evidence.

### Fourth guest read safely rewrites finished code as data (2026-11-24)

The same genuine 135-cell graphical N15 source admits an alternative
17-opcode continuation at C117..C133. After preserving all three earlier
input effects and their cumulative fold at M106, a real fourth `/` at
C128 reads byte/EOF. Reached `j` instructions at C129 and C131 use
M110=52 and earlier encrypted M54=39 to point D to M40. A reached C132
`p` then folds the **actual earlier encrypted C40 value 63** with the
fourth input, stores the result into finished code cell M40 and halts
at C133 in 112 steps. All 257 fourth-input/EOF classes match a separate
trit oracle; a traced binary case and negative opcode mutations pin the
read/write ordering. M106 and its output are **not** updated by the fourth
input; this proves only late guest scratch state liveness, not C23 source
storage, a repeatable loop or the original checksum. Evidence:
`docs/technical/compiler/source-indirect-guest-suffix.md` and
`tests/compiler_indirect_source_suffix.rs`.

### Three-input guest fold reuses encrypted code as a pointer (2026-11-24)

The original complete seven-block C23 mutable EOF checksum still refuses
publication. A separate genuine 135-cell N15 source now reads three runtime
inputs, retains the first/second crazy fold in M106, then uses its **earlier
encrypted output instruction C118** as data: the reached C123 `j` reads
M118=104 and places D at 105. The physical C124 and C125 `p` instructions
combine the third input with the previously saved fold and overwrite M106.
C126 emits the new result and C128 halts in 107 normative VM steps. Nine
independent binary/EOF streams and all 257 third-input/EOF classes match a
separate fifteen-trit oracle. Two further 256-byte first-/second-input
marginals, plus two genuine truncated-EOF cases, independently verify
prior-state dependence; changed-code negative controls fail.

The bounded suffix placer now supports linear `j`/`p`/`*` data operations
and preserves byte-exact protected source words even when those operands
later execute as code. This is guest ternary arithmetic and phase-sensitive
code/data reuse, **not** C23 unsigned checksum arithmetic, signed EOF
normalization, a repeatable loop or source-locked CFG/phi linkage. Evidence:
`docs/technical/compiler/source-indirect-guest-suffix.md` and
`tests/compiler_indirect_source_suffix.rs`. P2 remains open.

### Second input folds a saved first guest word before a valid halt (2026-11-24)

A new source-valid 135-cell N15 program executes two real guest inputs and
stores the first in M106 via `p`. Four pointer reads, including the physically
encrypted C37 no-op value, redirect the second accumulator through another
actual `p` on the previously saved word. It outputs the crazy-word fold and
follows five further `j` instructions and one `i` into a genuine encrypted
C82 `v` halt at step 96. Two complete 257-class input marginal sweeps,
nine full physical traces and five source-valid negative mutations are
checked against an independent fifteen-trit oracle. No host-derived guest
output is published. This verifies a state-dependent physical arithmetic
continuation that the preceding two-read echo guest did not establish.
It remains neither C23 arithmetic, signed EOF conversion, nor executable
source checksum control flow. Evidence and limits:
`docs/technical/compiler/two-input-fold-reentry-research.md` and
`tests/compiler_c23_saved_input_fold_reentry.rs`.

### Source Boolean promotions before binary and comparison (2026-11-24)

The strict numerical source-operation gate now refuses every direct `_Bool`
binary operation, including numerically plausible bitwise `And`/`Or`/`Xor`,
and direct `_Bool` equality/inequality. The admitted typed IR requires
explicit integer promotion before these operations; a matching one-bit guest
result cannot stand in for the missing source cast. A normative four-step N15
guess trace physically stores Boolean one/one/one: it rejects a direct
Boolean equality but accepts U8 equality as a numerical control (not a
complete source-admitted C comparison); it also rejects a raw Boolean XOR
even when its bits match. All
54 mirrored targeted compiler-verifier cases pass. This is admission
alignment, not a guest C comparison/linker, signed EOF or whole-program
parity result; the seven-block mutable checksum remains unlinked. Evidence:
`tests/compiler/source_computation_trace.rs`.

### Source-typed cast destination category (2026-11-24)

The opt-in numerical source-computation verifier now refuses physically
matching extended integer results when the *destination* signedness violates
the authenticated typed cast. `SignExtend` requires signed source and signed
result; `ZeroExtend` requires non-Boolean unsigned source and unsigned result.
Previously a real guest storing integer one could authorize either wrong
result type, and a Boolean source could be silently zero-extended. A new
four-step normative N15 store trace accepts valid signed/unsigned extension
and rejects all three invalid types even when every guest value matches.
Three mirrored compiler targets pass 51 focused cases. This is a necessary
source-type gate, not proof of physical operand causality or general C23
code generation; the original seven-block mutable EOF checksum still refuses
publication with its unlinked physical CFG. Evidence:
`tests/compiler/source_computation_trace.rs`.

### Two-read EOF-selected encrypted instruction fetch (2026-11-24)

The source-authentic 91-cell two-input guest now has a second, strictly
physical continuation. After C37/C54 have read inputs, M126/M138 have
preserved their distinct raw values, and C50/C62 have echoed each successful
byte, the replacement C63/C64 `j` and C65 `i` reach already encrypted C67.
That cell is source-required to be 125 for the early C42 pointer setup; its
actual `i` takes a second, independently verified code backedge to C35.
The resulting second C45 `p` consumes the **restored second guest input**
and physically rewrites instruction C49 from encrypted value 75. An
independent 15-trit oracle exhausts all 256 successful bytes: every result
is non-graphical (range 7,174,242..7,174,492). True N15 EOF alone gives
word 42, which decodes as a harmless instruction at C49, continues to C57
and emits an additional byte 32 before reaching a non-graphical C60.

The normative VM replays all 257 second-input classes and all 257
first-input classes with second-input EOF. It checks exact input
consumption, both stored input words, two initial outputs, jump
and encryption sites, code-word fetch and terminal outcome. Finite classes
terminate at C49 after 82 steps; EOF terminates at C60 after 93. Changed
C63/C64 pointer transfers no longer select the same EOF path. This is a
**real input-dependent instruction-fetch discriminator** and a bounded
self-modifying code reentry, not an executable C23 `if`/`while`: neither
branch reaches a valid `v` halt, N15 raw EOF is not converted to signed
C23 EOF, and no checksum state or reusable backedge is linked. Evidence:
`build_c23_two_inputs_eof_fetch_probe_source` and
`tests/compiler_c23_two_saved_echo_guest.rs`.

The next repair must give **both** outcomes valid, source-backed control
sites and implement a repeatable EOF loop, without replacing the complete
original seven-block checksum with a fixed probe.

### Bounded local source-suffix halt search (2026-11-24)

A strictly local mutation census tested eight position-sensitive opcodes
on each of the eight formerly inert code sites C51..C53/C56..C60 in the
above two-input EOF-fetch guest: **64** source-loadable N15 candidates.
For concrete streams `03 04` and `03` (second physical read = EOF), only
**14** preserve both original input cursors and both initial outputs.
All 14 still terminate by **non-graphical code fetch** after 82 finite or
93 EOF steps; none reaches `v`. A separate two-site census at (C56,C60)
and (C57,C60), 128 candidates, finds just **two** variants preserving
both output prefixes, neither a valid halt. The slower two-cell regression
is opt-in to avoid charging every ordinary test run for expanded N15
loader setup.

These are exact *two-stream, fixed-location, bounded-grammar* negatives,
not a proof about all guest-control relocation. The immutable C23 checksum
continues to refuse unlinked physical control and phi state. See
`one_cell_eof_halt_census_finds_no_source_valid_repair` and
`two_cell_eof_halt_census_near_rotation_finds_no_repair` in the two-input
Rust test.

### Post-output first-state reentry needs relocated guest control

The two-saved-input guest halts at C63 by design. A separate source-valid
continuation replaces C63..C66 with four no-ops and attempts to use the
unchanged C67 cell to return to the first saved word M126. The early C42
pointer setup **requires** source M67=125, however, so fetching that cell
as code decodes `i`, not `j`. At reached C67, D=M150=121; the attempted
indirect control selects invalid expanded C121=7,174,404 and fails with the
normative VM's exact `InvalidEncryptionTarget` error, rather than quietly
reading M126. Three binary/EOF traces verify the same refusal after both
legitimate output effects. `tests/compiler_c23_two_saved_echo_guest.rs`
contains this negative guest control.

This is only a *local* reentry failure for unchanged source C67 and the
specific C63..C66 fallthrough, not proof that all relocated control routes
are impossible. The next linker must provide a different source-valid
control site or modify the bootstrap pointer chain while retaining true
first-input storage and its original input/EOF identity.

### Static second-crazy operand cannot normalize C23 EOF (2026-11-24)

A finite, independent 15-trit algebraic census now rules out the simplest
attempt to repair EOF in the physical first-input saved-and-echoed guest by
changing only the **second constant** `p` data operand. With its first M126
operand fixed at 121, any second operand that retains all 256 successful
bytes must have seed trit 1 in the five least significant places; the sixth
seed trit may be 0 or 1. In the nine remaining places, seed trits 0 and 1
act identically on the first store's successful-byte and EOF images; only
trit 2 is different. Exhaustively enumerating the resulting 2 × 512
possibilities leaves **14** seed variants that preserve all 256 output bytes.
Their N15 EOF output is always **174 or 46**, never the required C23 255.

`tests/compiler_c23_first_saved_echo_guest.rs` checks this exhaustive
mathematical obstruction separately from the source-loaded VM traces. The
obstruction applies only to the fixed first 121-operand and two constant
crazy writes, not arbitrary guest programs. A source-dependent pointer,
additional live arithmetic, or real EOF branch is required to go further.

### Two independent stored raw inputs and physical outputs (2026-11-24)

The first-store program now has a source-loaded continuation in the **same
91-cell N15 source**. The first C37 `/`, C43/M126 first saved word, C49/M132
restoration and C50 first output remain physically unchanged. C54 `/`
performs a second independent signed input attempt, C55 `p` stores its raw
class injectively at disjoint loader M138=121, and C61 `p` restores its
successful byte using untouched loader M144=121. C62 `<` emits the second
byte and C63 `v` halts after exactly 64 guest transitions, preserving both
M126 and M138. Twelve real VM traces include empty, truncated, binary, high
byte, swapped inputs and an unread suffix. A separate exhaustive scalar
census verifies that each physical first-stage word independently retains
all 257 input/EOF classes; mutations of the second `/` or either second
`p` break the second output without altering the first output.

The source is *unconditional*: two EOF attempts emit two raw N15 low bytes
174. It does not test EOF before reading again, convert it to signed C23,
perform source-C arithmetic, or link the checksum loop. Implementation:
`build_c23_two_inputs_saved_and_echoed_source`; independent regression:
`tests/compiler_c23_two_saved_echo_guest.rs`. This extends physical
compositional input/state/output reachability, not C23 compiler publication.

### First input retained across its physical output (2026-11-24)

The unchanged full seven-block C23 mutable EOF checksum still refuses
publication at unlinked physical control, arithmetic and phi writes. Three
original pipeline acceptance tests pass only their explicit refusal path.
No C23 checksum guest was produced.

An independently loaded **91-cell N15** graphical program now runs a true
C37 input, writes an injective 257-class raw-byte/EOF representation at M126
through C43 `p`, advances D through five reached no-ops, and executes a
second real C49 `p` against untouched loader M132=121. The second crazy
operation restores each successful byte exactly to the guest accumulator
while preserving its earlier M126 storage. C50 `<` emits the restored byte;
C51 `v` halts after 52 physical instructions. This extends the earlier
lossless-first-store source with a **separate input-dependent physical output**
without a second `/` or any host-computed output substitution. Independent
15-trit scalar enumeration proves 257 distinct first-store classes and exact
successful-byte restoration. Ten normative VM traces check storage, second
store, output, source identity, input cursor and halt. Two mutation controls
remove C43 or C49 `p` and break the output contract.

N15 EOF is **not** a C23 signed EOF conversion: its first crazy write is 242,
the second yields 7,174,574, and its emitted byte is 174 rather than 255.
Neither source-C typed local storage, input-driven branch selection, repeated
EOF loop, phi transfers, nor checksum arithmetic has been linked. Evidence:
`build_c23_first_input_saved_and_echoed_source` and
`tests/compiler_c23_first_saved_echo_guest.rs`. P2 remains open.

### Source-loaded two-input physical computation and output (2026-11-24)

The original complete seven-block C23 mutable EOF checksum was rerun through
`malbolge --repository-tools compile` and still refuses publication: 19
source operations, four phi edges, six phi moves and a 43-word guest state
frame are not linked to executable guest control. No checksum artifact was
published.

A separate **26-byte** graphical N15 guest now performs a genuinely
**two-input nonlinear operation**. C2 `/` reads the first raw input and C4
`p` stores its injectively encoded word into source-loaded expanded M38.
After thirteen reached inert instructions, C18 `/` reads the second raw
input (or genuine EOF); C19 `j` uses untouched loader M53=37 to return D to
M38, and C20 `p` reads the actual *first guest store*, combines it with
the second input in the 15-trit crazy operation, and overwrites M38. C22
`<` outputs the computed word modulo 256, and C23 `v` halts at step 24.
Both the M38 seed 7,174,453 and M53 return operand come from the original
graphical source's two `J` tail bytes, not from a host-provided VM state.

`build_live_two_input_fold_source` returns the frozen graphical source and
its exact physical effect sites. `tests/compiler_live_two_input_fold.rs`
checks 14 real normative-VM binary/EOF streams, independent scalar inputs,
source cells, both input sites, read-after-write, output and actual halt.
An independent all-257 raw-input scalar census checks retention by the
first store and nonconstant dependence on either input. A separate reached
C20 no-op guest emits the *unfolded* second byte; skipping C19's pointer
return makes the subsequent `p` read a different cell. These negative
controls distinguish guest computation from host-derived output values.
A further source-loaded negative witness shows that **empty input**
(two genuine EOF observations) and **two NUL bytes** (two genuine successful
reads) both leave the complete 15-trit fold word M38=7,174,453 and emit
byte 53. This is a real reachable collision, not only a low-byte alias:
the fold cannot classify final `getchar` EOF for the source C23 checksum.

This is one finite real guest **binary dataflow and output primitive**,
not signed C23 `getchar`, typed XOR/addition, source-language loop linkage,
EOF-driven control flow or a compileable mutable-C checksum. The P2
source-C end-to-end acceptance remains open.


### Authentic delayed third-input output through finite code reuse (2026-11-24)

The frozen complete C23 mutable EOF checksum still refuses publication at
unlinked physical CFG state, branch and phi operations. A separate
loader-authenticated 261-cell N15 source uses the existing twelve-backedge
input guest and changes
**only C67**, from the second raw-input `p` store to graphical byte 95. It
initially decodes as `o`; twelve true visits under XLAT2 decode inert on
all but the **ninth**, which becomes actual `<` at VM step index 92. The
third guest `/` at C66, reached on step index 73, supplies the accumulator;
the intervening source-code revisits do not replace it. The guest emits
exactly that third raw byte, or the raw N15 EOF byte projection **106** if
fewer than three bytes were available. It still reads five genuine inputs
(including EOF) at step indices 37, 43, 73, 96 and 103, executes twelve
real C68 -> C63 indirect backward jumps, and halts at the self-encrypted
C65 `v` after 115 steps. The first loader-seeded encoded store remains;
the original C67 second store is intentionally absent.

Six binary/EOF streams run through the normative N15 VM with exact output,
input cursor, physical read/output sites, repeated XLAT2 code-cell fetches,
independent ternary first-store values and genuine halt checks. The unmodified
source is a negative control: all twelve jumps remain but it produces no
output. `build_long_source_delayed_input_echo_source` proposes the changed
source via the bounded code-visit encoder; the actual execution comes only
from the normative VM in `tests/compiler_long_source_delayed_input_echo.rs`.
This closes a **finite physical delayed-input-to-output path** without
reusable source-C loop semantics, signed EOF conversion, general arithmetic,
phi transfers or any checksum artifact. P2 remains open.

### Authentic finite input backedge under source self-encryption (2026-11-24)

The full seven-block C23 mutable checksum was reattempted unchanged and
still refuses unlinked physical CFG publication. A separate constructive N15
experiment extends the **source-loaded 261-cell two-read guest** by changing
only C68's first-visit `v` into a real indirect `i`. The fresh code jump
reads twelve *different* untouched expanded-memory operands (all 62), so
its physical C68 -> C63 transfer repeats twelve times while D advances six
words per traversal. The earlier C39 `i` and all twelve C68 `i` instructions
encrypt physical C62 before incrementing to C63; the revisited C63..C67
instructions separately self-encrypt on execution. This distinction matters:
modeling the jumps as encrypting C63 gives a false code schedule.

A normative N15 VM actually runs **115 instructions**, reading at step indices
37, 43, 73, 96, and 103, and terminates with a decoded C65 `v` after its
thirteenth visit. The C65 halt is caused by XLAT2 source-code mutation, not
by input-dependent EOF control. Five binary/EOF streams check exact guest
halt, all twelve backedge sites and operands, stepwise code-cell fetches
against an independent per-address XLAT2 schedule, consumed input cursor,
and preserved initial two injective physical stores. A separate scalar crazy
oracle proves that these first two storage cells can distinguish all 257
raw byte/EOF inputs. The old single-C68 `v` source is the one-cell negative
control: it halts after 46 steps and consumes only two inputs.

This is the first loader-authenticated, repeatably *reentered* input-code
region in this high-memory source family. It is a **finite, self-encryption-
controlled** path, not a repeatable source-C loop body: the later three raw
reads are not linked to C23 SSA storage, the two existing stores are not
signed `getchar` words, and there is no branch on EOF or checksum arithmetic.
The complete source-C checksum still cannot be published. See
`tests/compiler_long_source_input_loop.rs` and
`build_long_source_finite_input_loop_source`.

### Loader-valid expanded-data input continuation (2026-11-24)

The original seven-block C23 mutable checksum still refuses physical CFG
linkage and publishes no artifact. The first 256-cell high-pointer experiment
was **not source-admissible**: byte 35 at code position 41 does not decode to
an allowed N15 source instruction. Its source-level scalar pointer and loader
oracles were not normative guest execution. The prior acceptance claim is
superseded by this red-first loader admission finding.

A corrected **261-cell graphical source** reuses the high-pointer bootstrap
with a loader-valid source initial word 92 at C41. C0 relocates D there,
C1 genuinely writes M41=7,174,454, C18 uses the valid M58=40 operand to
return D to M41, and C19 reads the modified pointer to reach expanded data.
The valid two-cell source tail is 62/62 at C259/C260. C37 executes a true
input and C38 stores the all-ones-seeded, reversible raw input encoding at
M7,174,473. C39 halts. The independent scalar 15-trit oracle proves all 257
N15 byte/EOF words are distinct and invertible; nine complete normative
N15 VM executions verify source admission, mutation, exact 40-step halt,
input consumption and data writes. The prior 256-cell fixture is replaced
rather than left as a false positive.

A second independently verified source variant instead executes C39 as a
real forward code jump, reading untouched loader M7,174,474=62. It lands at
C63 and skips mutated C41 and source operand C58. After three no-ops,
C66 reads a second actual byte/EOF and C67 stores a second reversible
input encoding at M7,174,479. C68 halts at 46 instructions. Five real
binary/EOF N15 guest streams verify both physical writes, actual read
sites, the jump operand and target, exact halt, preserved first word and
unread input suffix. The second store uses the same injective seed but a
separate memory cell; 257 independent scalar raw-word classes are covered
at each position. The source and both data addresses are loader-derived,
not host-seeded VM overrides.

This is a bounded data/control continuation and a correction of an invalid
source artifact. It does **not** normalize raw EOF to the signed two-word
C23 result, link the checksum's 43-cell SSA frame and seven source blocks,
implement arithmetic/phi transfers, prove a reusable loop, or justify
publishing the original checksum. See the paired tests
in tests/compiler_long_source_input_bootstrap.rs and
tests/compiler_long_source_two_input_bootstrap.rs.

### Source-authenticated two-read branch halt and replay (2026-11-24)

The final publisher checks an actual decoded `v` halt reason, not just a
matching step count; termination on non-graphical code is never a valid C
return. This applies to the two-read EOF branch, signed second-byte echo,
byte-trace output and their final source replay. The two-read branch still
executes every second-byte value on the real N15 VM, and now checks 16
selected first-byte boundaries against both second EOF and a successful
second read. Each case checks output, input sites, consumed cursor and exact
branch steps. This is finite marginal coverage, not the 65,536-pair product
or a complete C23 mutable checksum.

The two-read branch and signed-second-echo replay now occur once at their
final publication gates, instead of repeating the same VM and full-memory
reconstruction during candidate construction. An independent exhaustive
512 first-byte/branch regression paths check both second-EOF and successful
second-read control over all 256 first octets, without adding that expensive
matrix to every publication. The original seven-block mutable C23
EOF checksum still refuses physical linkage and publishes no guest artifact.

### Published second-read EOF branch verifies every byte (2026-11-24)

The existing source-authenticated C23 two-read EOF branch still emits a real
N15 guest and checks the same graphical source under the normative VM before
publication. The publisher previously replayed only fourteen selected binary
streams. It now also replays all 256 successful **second** `getchar` byte
values with a fixed first byte and unread suffix. The existing vectors
separately retain true first/second EOF, first-byte boundaries and guarded
third-read behavior. Each real branch output, I/O instruction site, consumed
byte count and halt step must agree with the admitted typed-source witness.
This is a finite validation strengthening for an **already linked** two-read
slice; it neither generalizes the fixed source grammar nor executes mutable
checksum arithmetic, loop phi copies or the original seven-block C23 program.
The replay now forks one validated source-loaded VM checkpoint with fresh
unread input, retaining its exact physical source image without repeating a
full-domain memory validation for each branch case. The runtime rejects
changed already-consumed prefixes, and the real VM still executes all cases.

### Bounded EOF-zero predicate operand reentry refusal (2026-11-23)

After retrying the complete seven-block mutable C23 checksum, the real
compiler still refuses to link its physical CFG or publish a guest artifact.
The latest N15 raw-input-preserving C54 `p` predicate can be reached on true
EOF in 55 normative VM steps, with A=0, D=128 and the physically consumed
M127=0. The C14/C17 zero-initialized C32 pair still holds raw EOF in its low
word and zero in its high word. C54's EOF write is **idempotent**: its
executed `p` is visible in the trace's data read and accumulator result,
while the memory-delta field is absent because M127 was already zero.

A fixed, exhaustive **negative** continuation search in
`tests/compiler_c23_eof_zero_branch.rs` starts from that genuine 55-step
state. It explores every 1- through 6-opcode continuation over
`{j, o, *, p}` (5,460 paths), using independent ternary arithmetic and a
per-path guest-memory-write overlay. No path restores D=127 to let a
subsequent real `i` consume the C54 result within the original 62-source-
cell envelope. The search deliberately allows arbitrary per-path writes,
including destructive rewrites of the original input pair, and ignores
actual code/encryption encodability. Thus it excludes even those relaxed
six-opcode routes, not all longer layouts, revised loader seeds, other
opcode sequences or other conditional guest techniques.

This makes the **physical operand reentry** obstruction explicit rather than
mistaking a reached zero accumulator, a self-contained EOF marker or a raw
pointer jump for executable source-C control. It does not establish a C23
signed EOF pair, guest arithmetic/phi execution, a reusable EOF loop or the
whole C23 checksum. The next attempt needs a different predicate-placement
or longer source-backed state/operand route, with normative replay and
independent C23 parity before any target publication.

### Fixed N15 EOF source tail rejects a silent code jump (2026-11-23)

The 62-cell raw-input/EOF-zero source already ends with a real C60 `<`
(output) and C61 `i` (code transfer). They are not free instruction
slots: the two bytes `b"'%"` seed the untouched loader recurrence.
A second independent 15-trit scalar test enumerates all 8,836 printable
C60/C61 pairs against the exact four initial words at M86, M126, M127,
and M128 required by the raw input return and EOF-zero construction.
Exactly **20 tails** reproduce all four loader words. However, of those
20 only the original pair is accepted by the actual N15 graphical source
admission rule: the other 19 decode to invalid C60 instructions.
Therefore, simply replacing C60's premature output with a no-op while
preserving those four loader operands cannot expose the existing C61 `i`
for a complete C23 checksum. This is a **fixed seed-equivalence and
source-admission** result, not a prohibition on other loader layouts,
reallocated operands, code-cell revisits or longer guest programs.
See `only_source_valid_eof_seed_tail_keeps_output_before_code_jump`.

The follow-up `extending_original_eof_source_cannot_preserve_its_loader_seeds`
checks every 63- through 86-cell source length and every printable pair
at its new tail (24 x 8,836 pairs). Odd lengths have **no** pair preserving
all four loader words. Each even length has 20 such pairs, but none has
both bytes decoding to a source-admitted instruction at the new positions.
At lengths 87 and above, M86 itself would be a graphical source cell, not
the mandatory 7,174,416 pointer. Therefore, simply growing this original
code envelope cannot preserve its four exact physical loader seeds. This
is not a negative result for a **relocated** loader or different data cells.

### Source-loaded lossless input with an EOF-only physical output marker (2026-11-23)

The compiler now exposes
`build_adjacent_c32_zero_c37_raw_eof_marker_source` for a 56-step graphical
N15 guest continuing the **same** C14 high-zero / C17 low-zero initializer,
C37 real `/` and C43 lossless raw input store. C47 `j` selects exactly D0
on true EOF or D1..D256 for a successful byte. C48/C49 execute two more
actual pointer jumps, C50..C52 advance without changing the original data
pair, C53 `*` rotates the physically selected operand, C54 `<` emits its
low byte, and C55 halts. Unlike the naive C48 `*`, the delayed selected write
never violates the VM's code-cell self-encryption rule. The output is **0x6a
for actual N15 EOF and never 0x6a for a successful byte**; successful-byte
outputs need not be unique and are not echoes of the input. The original
raw 15-trit input word at D7,174,417 and adjacent high zero survive all
classes. EOF remains raw 14,348,906, not a signed C23 `-1` pair.

The independent source constructor is compared against a separately patched
canonical graphical source in `tests/compiler_c23_zero_input_store.rs`. The
normative VM checks the reached C48..C55 instructions, exact output bytes,
raw-data preservation and read count on 15 adversarial input streams.
An opt-in (`--ignored`) exhaustive 257-class **actual normative VM** test
also passes, including all 256 successful byte inputs and true EOF with the
same 56-step halt, a noncolliding marker, and preserved original low/high
words. A real one-opcode negative control replaces C53 `*` with inert `o`:
then successful input byte 106 emits the same 0x6a as EOF, proving the new
physical rotation is necessary to separate these two boundary cases.

This is a real **data-dependent physical observation**, not source-C23 signed
`getchar` conversion or executable source-C control flow. C54 currently
outputs an experimental marker rather than performing a branch, and no
verified target code-pointer `i`, C32 signed upper word, checksum arithmetic,
phi copy/loop or complete seven-block checksum linkage is created. P2 remains
open; the original whole-program gate still fails closed without an artifact.

### Input-preserving full-word EOF-zero data effect (2026-11-23)

The original C14/C17 adjacent-zero initializer, C37 real input and C43
lossless raw-input store now extend through a reached C54 crazy operation.
C47 still selects the data pointer from the physical input; C48/C49 return
through real loader operands and C53 rotates the input-selected word. C54
then physically reads its next data operand and writes a **full 15-trit
word equal to zero exactly on true N15 EOF**, not merely a unique marker
byte. C55 emits its low byte and C56 halts in 57 normative VM steps.
All successful inputs produce a nonzero full word and a nonzero output byte.
The original low input word and adjacent high zero remain untouched.

`build_adjacent_c32_zero_c37_raw_eof_zero_source` checks the exact current
profile and graphical source geometry. Its source matches an independently
patched original; a separate 15-trit ternary oracle checks the actual data
read and accumulator result. Twelve representative binary/EOF VM streams,
a missing-`p` negative control and the explicit opt-in 257-case exhaustive
normative VM gate live in `tests/compiler_c23_zero_input_store.rs`. This
establishes a physical **zero-if-EOF data value**, not normalized signed C23
`getchar`, guest `i` code branching, an unbounded loop or publication of the
complete seven-block mutable checksum. P2 remains open.

A deliberately naive reached C55 `j` / C56 `i` continuation proves why the
zero data value is **not yet a code branch**. The jump reads a different
loader word rather than returning D to the new C54 predicate: on true EOF,
the `i` still consumes raw MLOW=14,348,906 and rejects a non-graphical
post-jump encryption target. Successful input byte 2 likewise rejects at
M118. The paired source and normative VM negative control prevent treating
this partial control transfer as linked guest CFG execution.

### Authentic raw EOF-dependent data-pointer selection (2026-11-23)

A 49-step extension (`build_adjacent_c32_zero_c37_raw_pointer_source`)
returns to the physically saved raw input with C44..C46 `j` and executes
C47 `j` using that actual source-loaded word. The resulting D is exactly
`raw + 1` modulo 14,348,907: successful input bytes select D1..D256 and
true N15 EOF alone selects D0. C48 halts without dereferencing the selected
cell. Independent 257-class arithmetic and sampled normative VM traces in
`tests/compiler_c23_zero_input_store.rs` establish the dynamic selection.
This is a **data-pointer effect only**, not a guest code-pointer branch,
source-C23 signed EOF predicate, loop backedge or checksum publication.

### Lossless raw input into the original initialized C32 pair (2026-11-23)

A stronger, independently verified 45-step graphical N15 source now continues
**the same** C14 high-zero / C17 low-zero initializer into C37 `/` and a
**lossless raw N15 input write to the original low cell**. This is not the
earlier separate raw-pair initializer and does not replace the memory image.
The compiler exposes
`build_adjacent_c32_zero_c37_raw_input_pair_source` and validates its
loader operands and the fixed current-profile code/encryption geometry.

The source first revisits the low zero cell with genuine C18..C20 jumps;
C21 `p` primes the low word to ternary all-ones. C22 `j`, sequential no-ops,
and C36 `j` through the actually encrypted C14 prepare the C37 input to
reach the previously source-written all-ones M126. C39 `p` performs the first
invertible data write, C40..C42 `j` return to the original low cell, and C43
`p` physically decodes and writes its **exact raw 15-trit input word**.
C44 halts. The adjacent high word remains zero throughout. The independent
oracle verifies all 256 byte values and the distinct N15 EOF word through
the two-crazy involution, with representative 45-step normative VM traces,
loader/classic-encryption checks, unread-suffix coverage and a negative
priming-mutation witness in `tests/compiler_c23_zero_input_store.rs`.

This removes the lossy 40-image limitation of the earlier low-cell fold for
successful bytes. **It still cannot be admitted as a signed C23 `getchar()`
store:** N15 raw EOF is 14,348,906 instead of C23 -1, the upper C32 word
remains zero rather than sign-extended, and no source-C checksum arithmetic,
phi transfer, conditional/loop backedge, or full guest publication is linked.
The next physical gap is EOF-safe C23 conversion and a complete typed store
without breaking the authentic pointer and loader history.

### Real first input-dependent zero-low overwrite (2026-11-23)

A real 43-step graphical N15 source now continues the original first C23
checksum prefix: C14 writes adjacent high zero, C17 writes low zero, and C37
performs `/`. C39 executes `p` on a virgin source-loader word at M7,174,439,
C40 performs a real `j` through M7,174,440 to the previously written low
word at M7,174,417, and C41 performs a **second input-dependent data write**
to that word while preserving the adjacent high zero. C42 halts. The
construction is available as
`build_adjacent_c32_zero_c37_input_low_fold_source`; the independent frozen
source and normative 43-step guest traces are checked by
`tests/compiler_c23_zero_input_store.rs`, including EOF, NUL, 0xff and an
unread suffix.

An independent exhaustive 257-class scalar oracle establishes that the low
word has **only 40 distinct images**, though true EOF is distinct from
all successful-byte images. This is a real physical input-dependent state
update and reuse of the original C32 zero initializer, **not** a C23
signed `getchar` result, complete two-word input SSA store, or dynamic EOF
branch/loop. The original seven-block mutable checksum still refuses guest
artifact publication. A correct, full-width 257-state store and subsequent
source-C arithmetic/control linkage remain necessary.

### High-first adjacent C32 constant initialization reservations (2026-11-23)

The unchanged complete source-C23 EOF-checksum compilation was retried through
its pinned compiler and still failed closed before publication: seven typed
blocks, 19 operations, four phi edges, 43 state words and a 71-cell minimum
*unlinked* code bound. No target guest artifact was created. The first real
missing stage is still executable physical code and CFG control, not source
admission.

A narrower source-CFG placement refusal was repaired without weakening that
publication gate. The independent loader-backed N15 adjacent-C32 zero
initializer executes two `p` writes in **high-before-low** order: the high
zero cell at C14, followed by the low zero cell at C17 after physical reentry
(`tests/compiler_adjacent_zero_source.rs`). The original checksum's first
`unsigned checksum = 0U` produces two independently materializable constant
word effects. Previously source-locked placement required low-before-high,
rejecting the physically demonstrated order before a linker could even
attempt it. Its sparse binder and automatic code planner now accept a pair of
**explicitly anchored** two-word integer literal writes in either order,
while retaining their exact canonical source-index and destination identity.
The checksum regression reserves its first C block entry at C0, high word at
C14 and low word at C17, with four separate phi pads. No other original
checksum operation is elided.

The exception is deliberately narrow: reversed signed `getchar` input-result
stores, unmatched or duplicated indices, inconsistent source bindings and
code collisions still refuse. Unanchored literal effects retain the existing
low-before-high order, and computations, I/O and phi writes never acquire an
ordering exception. A follow-on **real 39-step N15 guest** now composes those same source-loaded
C14/C17 zero writes with 19 reached no-ops and a genuine C37 `/`, followed
by a C38 halt. The original loader-tail bytes and all prior physical words
are preserved; EOF, NUL, `0xff` and unread-suffix streams are checked in the
normative VM. The input still remains raw in A, with **no** signed C23
conversion or source-SSA store (`tests/compiler_adjacent_zero_source.rs`).
The 62-cell physical guest and the 256-cell checksum reservation do not yet
form one source-verified linked artifact with all 43 frame words, operand
preparation, phi pads or branch paths. This is source-authenticated geometry only, not a C23
checksum, signed EOF conversion or successful P2 guest parity. Regression:
`tests/compiler/source_dynamic_checksum.rs`.

### Source-function entry before the first physical operation (2026-11-23)

A complete C23 EOF-checksum compile was retried through the pinned frontend
and target adapter. It still refuses at the same unlinked seven-block CFG:
19 typed operations, four phi edges, 43 guest-state cells and a 71-cell
minimum code bound; no guest artifact was published. The first byte-exact
physical source entry is therefore **not** proved by this change.

The sparse source-CFG planner now has an optional *function entry anchor*
checked against the canonical function's actual entry block. Previously a
first `getchar` pinned at C37 forced the compiler to infer the minimum prefix
near C35, even when the target's real program counter begins at C0. The
new source-locked reservation can begin the entry block at C0, leave
C0..C33 for unverified initial guest setup, reserve the entry literal's
first write at C34, then preserve the signed `/` at C37, its word writes
at C40/C42 and the second read/word writes at C66/C69/C71. The block's
control remains pinned at C60. This plan composes with the original
checksum backedge's separate phi-pad entry C80, eight ordered copies at
C90..C150 and successor transfer C170, plus all seven original blocks and
four predecessor-owned phi pads. No host-side branch is selected.

Unanchored callers retain their previous placement. Duplicate, foreign,
non-entry, late and out-of-source function entry proposals fail closed, as
do source-block and phi-pad collisions. This closes an **address reservation**
gap only: the proposed C0 instruction, literal writes, full-width arithmetic,
physical branches, signed EOF and loop have not been linked or verified as
Malbolge. The original five-vector P2 guest parity gate remains open.
Regression: `tests/compiler/source_dynamic_checksum.rs`.

### Source-owned phi pad entry setup reservations (2026-11-23)

The source-locked CFG planner now accepts a proposed **phi-pad entry site**
for a fully anchored predecessor-specific edge. Previously the automatic pad
always began on its first snapshot, leaving no room for guest pointer setup
*before* that snapshot. An exact entry may now precede the first write; the
planned source control edge enters there, while all source-bound snapshot,
commit and successor-exit sites remain unchanged. Entry/exit setup intervals
are reserved together, disjoint from other source blocks and phi pads.

The original seven-block C23 mutable EOF checksum reserves the 5-to-1
backedge at C80..C171: entry C80, eight exact snapshot/commit sites at
C90/C97/C105/C114/C123/C131/C140/C150, and exit C170. Legacy callers
still obtain C90 as the entry when none is proposed. Duplicate, foreign,
copy-skipping, missing-copy and overlapping entry sites fail closed. A
separate pre-existing normative N15 guest test proves the **bounded physical
possibility** of a pre-snapshot `j` pointer setup at C3 and genuine phi
copies at C4/C6, but does not execute this checksum. These are only code
reservations: no full C23 arithmetic, EOF loop or final artifact is linked.
P2 remains open. Regressions: `tests/compiler/source_dynamic_checksum.rs`
and `tests/compiler/source_phi_copy_trace.rs`.

### Sparse predecessor-specific phi exit transfer anchors (2026-11-23)

The automatic source-CFG phi planner now accepts an **optional exact exit
transfer site** for a fully source-anchored phi edge. The final commit may be
followed by guest pointer setup before its source-specific `i` successor
jump. Previously, automatic placement always forced the transfer immediately
after the last phi write, although the existing strict binder and normative
VM test already admitted post-commit setup.

The red-first original mutable C23 checksum test now pins all eight loop
backedge writes at C90/C97/C105/C114/C123/C131/C140/C150 and the eventual
successor transfer at C170. The checked pad occupies C90..C171, retaining
all seven blocks and four distinct phi pads. The existing API still ends
at C151; an exit before the final copy, duplicate/foreign edge, missing
snapshot/commit list, overflow, or collision with another source block
refuses. An earlier bounded real-VM test independently proved that post-
commit setup is possible. Neither test links this full C23 checksum: the
pinned positions do not assert that matching `p` or `i` opcodes exist.
The original program still refuses target publication. Regression:
`tests/compiler/source_dynamic_checksum.rs`.

### Source-word effects without explicit operation anchors (2026-11-23)

The general source-locked CFG auto planner can now reserve exact **word
store effects** before the physical start of their source instruction has
been identified. From the earliest source-ordered effect anchor, it derives
the minimum preceding typed-operation and within-operation effect prefix.
The existing strict binder rechecks every complete source operation, effect
index, destination and source-block interval; separately anchored controls
and phi pads remain disjoint. The narrower input-only API still requires
its explicit input operation anchor.

A red-first regression of the original seven-block C23 EOF checksum now
places four signed result-word sites at C40/C42 and C69/C71 and two
arithmetic result-word sites at C180/C190 with **no operation anchors**.
Both genuine C23 reads and the earlier literal/computation operations are
retained in the plan, while unknown effect indices and reversed word sites
refuse. The earlier unnecessary `InvalidCodePlacement` refusal is repaired.
These positions remain hypothetical reservations, not executable Malbolge
stores or a linked EOF branch. The complete C23 checksum still refuses
publication; P2 remains open. Regression:
`tests/compiler/source_dynamic_checksum.rs`.

### Sparse automatic source-phi pad reservations (2026-11-23)

The source-locked CFG planner now accepts **source-identified sparse phi
snapshot and commit anchors** without requiring the caller to hand-place
all seven source blocks and predecessor-specific landing pads. An anchored
pad starts at its first actual proposed copy, preserves the source-derived
snapshot-before-commit order through all exact copy indices, and reserves a
final successor-transfer cell. It is protected before first-fit placement
of other CFG blocks or phi pads. The existing independent binder still
rederives every phi source, destination and width from the original typed
C23 checksum. Unanchored edges retain compact deterministic pads.

The red-first regression pins all eight C23 backedge snapshot/commit sites
at C90, C97, C105, C114, C123, C131, C140 and C150. The automatic plan
now reserves C90..C151 for the 5-to-1 pad while keeping all seven typed
blocks and all four phi pads disjoint in a 256-cell hypothetical source.
A second regression composes that pad with C37/C66 signed input, four
word stores and C60/C75/C201/C224 source control obligations. Missing,
duplicate, reordered, forged or colliding anchors refuse. No Malbolge
source bytes at those sites are authenticated or emitted, and no executable
EOF loop exists; the original full C23 program still refuses publication.
A follow-on original-C23 multi-predecessor case pins both separate
loop-header incoming edges (0-to-1 and 5-to-1), each with four snapshots
and four commits. The first edge occupies C88..C102; the second uses
C120..C182. Their exact source-derived copies stay distinct after sorting
caller proposals, while overlapping edges and foreign identities refuse.
This tests *predecessor isolation*, not merely one correctly placed pad.

This is a placement capability only, not P2 acceptance. See
`tests/compiler/source_dynamic_checksum.rs`.

### Sparse source control-suffix reservations (2026-11-23)

The source-typed automatic CFG code planner also accepts explicit physical
control-suffix anchors for source jumps, conditional branches or returns.
When a block has sparse operation sites, its control site must follow every
source-derived effect; for a control-only anchored block, the planner places
its complete minimum operation prefix before the fixed control address.
Checks independently rebind all source control edges and retain disjoint
code intervals and predecessor-specific phi pads.

A red-first **original C23 EOF checksum** regression binds two signed input
sites, four signed-word effects and separate source control obligations at
C60, C75, C201 and C224, including the Return block with no pinned data
operations. Foreign, duplicate, out-of-order, overlapping and source-
capacity-exceeding control proposals refuse. No branch/jump/return opcode
has been encoded at these sites; the proposed geometry still cannot
execute the full mutable-C program, and P2 remains open. Regression:
`tests/compiler/source_dynamic_checksum.rs`.

### Sparse source-operation code reservations beyond input (2026-11-23)

The source-locked CFG planner now accepts sparse **operation anchors** for
any canonical typed instruction, not only `getchar`/byte input. The first
anchor fixes that block's minimum source-prefix position, later anchors
preserve source order with physical setup gaps, and unanchored blocks plus
predecessor-specific phi pads are packed into disjoint code intervals.
The original input-only interface still rejects non-input anchors; both
paths rebind every typed effect and source control edge independently.

The original complete seven-block C23 checksum now has a checked *proposal*
for a first entry-block literal at C0, the first signed read at C37, both
word effects at C40/C42, the second signed read at C66 with C69/C71 word
sites, and an independent computation in block 3 at C180. Wrong ordering,
overlapping blocks, duplicate identities and foreign ordinals all refuse.
This fixes a code-placement capability gap for source operations preceding
physical input setup and blocks containing arithmetic but no reads. It does
**not** prove those positions execute the prescribed guest instructions,
link conditional jumps or form an EOF loop. The exact same full C23 source
still refuses target publication; P2 acceptance is open. The red-first
regression is `tests/compiler/source_dynamic_checksum.rs`.

### Source-typed signed input per-word effect reservations (2026-11-23)

The source-locked automatic code planner also accepts distinct sparse
**effect anchors within** each authenticated C23 `getchar`. A read and its
signed low/high destination stores may each require physical setup before
the next effect. A new opt-in input-plus-effect placement derives canonical
word identities from the original typed C, reserves these code gaps, and
uses the existing strict effect binder to reject mismatched read sites,
duplicates, wrong effect indices, overlaps and insufficient capacity.

Red-first tests verify both original-C23 `getchar` results in one block,
then the **original seven-block mutable EOF-checksum CFG** with two pinned
read sites and four proposed signed-store positions. All seven source
blocks and four phi pads remain disjoint inside the 91-cell code budget.
These are still *code-cell reservations*, not physical N15 instructions:
no signed-EOF result has been materialized at those four proposed writes,
no source phi edge has been executed and the complete checksum continues
to fail closed before guest publication. See
`plan_source_locked_cfg_with_input_and_effect_anchors` and the corresponding
`tests/compiler/source_dynamic_checksum.rs` regressions.

### Source-locked same-block input setup gaps (2026-11-23)

The canonical typed-CFG input planner now preserves two real `/` sites in
one original C23 basic block with an extra physical code cell between
them. Previously the source-locked planner required every input
site to equal the strict minimum immediately after its predecessor, even
though its lower-level operation binder already admitted sparse positions.
A red-first source-backed test now accepts C0 and C4 reads in an eight-step,
fully loader-valid N15 guest for EOF, NUL, high-byte and two-byte streams.
The second site remains at C4; overlapping, repeated, non-input and
out-of-bounds proposals still refuse. No output or source-C32 result
stores are present in this probe, and the original mutable seven-block
EOF checksum still fails closed before target publication. Regression:
`tests/compiler/source_dynamic_checksum.rs`.

### Finite loader-seed bound for signed EOF conversion (2026-11-23)

An independent N15 scalar enumeration freezes a **two-crazy operand**
grammar: two graphical seeds in `[33, 126]` (8,836 ordered pairs), six
recurrence phases for the first and second operand (36 ordered choices),
and 0 through 14 right-trit rotations of the **first** operand only.
The second operand remains a virgin recurrence word. Each proposal must
produce every raw byte 0..255 unchanged modulo 256 and map the target's
true signed EOF word 14,348,906 to C23 output byte 255. A fixed seven-byte
filter precedes complete 256-byte checking; false positives cannot pass.
The complete finite search has exactly **12 accepted tuples**, all at
**nine rotations**, all with second seed and final operand 121. The
known `Iy` (`73,121`) seed, first recurrence phase, ninth rotation to
7,138,732 and final phase 121 are one accepted tuple. Zero through eight
rotations cannot solve this *specified* two-crazy loader grammar; the
ninth rotation is not a universal lower bound for all possible guest
algorithms or operand sequences.

This is a reproducible scalar negative bound, not target source-loadability:
graphical seeds are not independently authenticated as code at a chosen
position and the search never executes a source-C program or links guest
control. The real source-loaded eight-rotation prefix still cannot reach
the ninth rotation and then a correct EOF loop. The complete seven-block
C23 checksum still fails closed without a target artifact. Regression:
`tests/test_c23_loader_seed_rotation_bound.py`.

### Signed C23 input-store word causality (2026-11-23)

A follow-on finite-byte regression also refuses an unrelated successful
`getchar` **low** result even if the guest writes the numerically correct
constant-zero high word through an input-dependent operation. The first C23
word must depend on its own input in every case; the high word may stay
constant only for successful bytes. A red-first synthetic store-accounting
case previously accepted this swapped dependence and now rejects it, while
normal input-dependent low/constant-high behavior still passes. This added
check does not by itself prove a complete physical source-C read/return.

The opt-in physical input-store verifier now refuses a **numerically correct**
signed C23 EOF store unless the real EOF input affects both C32 result words.
A successful finite `getchar` may still write its constant-zero high word
without data dependence, provided its low word carries this read. At EOF,
allowing only one dependent word would authenticate an unrelated high-word
constant even though the source operation promised a signed `-1` result.

A red-first four-step **real N15 VM** trace executes `/`, `p`, `*`, `v`
with deliberately seeded frame operands. The genuine EOF and `p` write
M70=4,644,102, while an independent `*` rotates M71=897 into exactly
299. Both are the correct C23 EOF encoding, but the high word never
receives EOF data or control influence. The former checker accepted this
trace; the stronger checker refuses `InputResultUnrelatedToInput`. Separate
synthetic accounting controls accept two EOF-dependent writes and preserve
successful-byte constant-high behavior. The guest's seeded data words are
not a source-loaded C compiler artifact, and the original seven-block
mutable EOF checksum still refuses physical layout and publication.
Regression: `tests/compiler/source_input_store.rs`.

### One-read physical input-to-pointer after nine rotations (2026-11-23)

A modified **fully source-loaded** 91-cell `Iy` guest now makes its first
signed `/` at C37 the **only** input attempt through C67. Its real C38 `p`
stores `crazy(M97, raw)` into M97, while nine physical `*` writes prepare
the original C23 operand M95=7,138,732 without touching that saved word.
C66 is changed from `/` to `o`; C67 then executes a real `j` and reads the
**guest-written M97**, selecting a data pointer derived from the first
input, rather than a loader constant. Five bounded 68-step normative N15
traces (EOF, NUL, one with unread suffix, high byte, `0xff`) check the
exact input count, C38 physical write and C67 real memory read/indirect
pointer. A no-store C38 `o` mutation leaves the original M97 loader seed
at that pointer read. An independent 15-trit crazy oracle confirms that
the saved word separates true EOF from successful bytes.

**This storage is lossy:** all 256 successful bytes collapse to only 36
stored words, while EOF produces one distinct additional word. The guest
prefix neither reproduces a full signed C23 `int` nor completes the later
physical output/linkage; execution is deliberately bounded before the
unlinked remainder. It cannot provide the mutable EOF checksum's arithmetic,
phi writes, conditional branch or repeatable loop, and no C guest artifact
is published. The original full checksum continues to refuse target
publication (three end-to-end gate tests green). Regression:
`tests/compiler_one_read_bootstrap_route.rs`.

### One-read signed-EOF output with seeded guest data (2026-11-23)

The already proven exact N15 two-crazy operands `[87844, 2551]` now
execute in the **normative guest VM**, not just the scalar algebraic oracle.
A five-step positional `/, p, p, <, v` graphical source consumes exactly
one physical signed input, reads and writes M100 and M101 in order, and
emits the C23-converted output on six independent guest runs (NUL, one,
ASCII, high-bit, `0xff`, and real EOF). Its two writes are independently
checked against the frozen 15-trit crazy table; the existing exhaustive
scalar test still checks all 256 byte values and signed EOF. This validates
that the VM's data-pointer increment and actual crazy/output operations can
realize the arithmetic prerequisite without a second `getchar`.

**This is not source-loadable C23 code:** the data words are deliberately
injected into `ProfileMachine::from_state`, and the initial D register is
also seeded. Both operand words exceed graphical source bytes, so a real
linker must materialize their values in guest memory, construct their
addresses from loader-valid code and prove source-C operation provenance.
The original mutable EOF checksum still refuses before backend publication:
this test does not implement its seven-block loop, 43-word frame, phi copies,
conditional branches or data-dependent arithmetic. Regression:
`tests/compiler_eof_byte_conversion.rs`.

### Opt-in physical Boolean-to-control dependency (2026-11-23)

The strongest source computation plus physical CFG verifier now requires
reached conditional edges to carry the **latest guest-written Boolean SSA
version** into their actual code-pointer selection. Its trace-local token
tracks real `p`/`*` data writes and both pointer operations: `j` derives `D`
from `M[D]`, and `i` derives `C` from `M[D]`. Earlier writes at the same SSA
address cannot authenticate a later version. Ordinary CFG arm-value checks
remain separately available; the new necessary condition applies only to the
opt-in `verify_with_source_computations` gate.

A real N15 six-step `*, p, p, j, i, v` guest maps source Boolean zero and
one to separate C7/C8 halts through two physical crazy writes and the
indirect jump. Both traced arms pass the stricter control-data-path test.
An independent three-step `*, i, v` guest writes the same Boolean and
selects its numerically correct arm using a loader-seeded pointer: the
existing value-only gate accepted it, but the strict gate now refuses
`MissingBranchControlProvenance`. The test uses finite source-loaded memory
and a seeded Boolean; it does not prove that a guest computed the Boolean
from a C expression. The check can conservatively reject valid optimized
control that relies on untracked mutation or eliminated operands. Neither
physical C23 conditional lowering nor the original seven-block mutable EOF
checksum is linked. The full checksum still refuses target publication,
with its three bounded pipeline tests passing only that explicit refusal.
Regression: `tests/compiler/source_phi_copy_trace.rs`.

### Strict computation operand-data provenance (2026-11-23)

The opt-in `SourcePhiCopyProbe::verify_with_source_computations` now
requires a physical `p`/`*` data path from **each latest source SSA operand
word** into the reached result stores, in addition to exact typed numeric
agreement, block/phi linkage and the input-result store check. A trace-local
token names a particular guest frame write, not merely its address or word
value. Both operands of a binary operation, every word of a C32 operand, and
the single source of a cast must appear in the union of actual data inputs to
the result `p`/`*` writes. Guest loader seeds or an obsolete equal-valued SSA
write cannot create those tokens. A missing data path refuses as
`MissingComputationProvenance`.

A three-step N15 cast witness writes byte 1 at M70, then writes
the same byte 1 at M71 by rotating unrelated M71 data. Exact source numeric
replay accepts that forged identity; the new provenance check rejects it.
Replacing the second real `*` with a real `p` carries the latest M70 write
through A and passes the dependency check, but separately fails the numeric
cast gate. A four-step real N15 guest also writes 1, 2 and their exact
XOR result 3 through three independent rotations: typed numeric replay
accepts but the two-operand source data-path gate rejects. Both checks are
required and neither fabricates target execution.
This is a conservative **necessary data-dependency test**: it can reject
legitimate operand-eliding optimizations without additional proof and does not
prove the correct guest arithmetic, dynamic C branching, or that a complete
C23 EOF checksum is linked. The original seven-block checksum still refuses
publication. Regression: `tests/compiler/source_phi_copy_trace.rs`.

### Lossless one-read C23 bootstrap state (2026-11-23)

A source-loaded 91-cell N15 guest reuses the original Iy converter bootstrap
and executes its first five physical M95 rotations before a genuine C37 `/`.
Replacing the never-reached source C67 with graphical 125 (valid `i` at its
own phase) causes the already-reached C42 `j` to read M67=125 and select the
virgin M126=121 operand. C43 `p` then writes `crazy(121, input)` to M126.
An independent 15-trit scalar oracle proves this mapping has 257 distinct
images across all 256 input bytes plus true EOF. Five real 45-step guest
traces (EOF, NUL, 1, 128 and 255) prove the actual M126 write, unchanged
prepared M95=4,281,052 and M96=121, no extra input, and C44 halt. A real
no-store mutation leaves the virgin M126 word unchanged. See
`tests/compiler_c23_first_read_indirect_store.rs` and
`build_c23_first_input_lossless_store_source`.

This fixes the **lossy first-read state** of the prior C38/M97 probe under a
**different, fixed physical prefix**, not the C23 checksum. The new C43 store
advances D to M127, whose loader pointer enters a fixed point far from M95;
C44 therefore halts rather than performing the sixth through ninth rotations.
There is no verified return to the converter, C32 normalization, selected
branch or output; the original complete seven-block mutable EOF checksum
still refuses physical target linkage. The local state-preservation witness
must not be confused with full source-C publication.

An extended variant, `build_c23_first_input_saved_eight_rotations_source`,
uses a real C44 `p` scratch write to M127 and three independent loader-return
chains, restoring D to M95 for genuine C50, C57 and C64 rotations. The
first signed C37 value remains saved in M126 throughout. Five further
independent N15 guest executions (EOF, 0, 1, 128, 255) terminate at C65
after exactly 66 steps, with M95=7,067,290 (eight physical rotations),
M96=121 intact, M126 input-dependent, no second read and no output.
The checked C65 halt intentionally avoids reaching the original C66 `/`
and source-required C67 `i`; linking the ninth rotation and returning to
the correctly signed converter are still unsolved. The regression checks
each physical M95 rotation and each final pointer reset against an independent
15-trit scalar rotation oracle, not a host-created memory snapshot.

A separate necessary, **fixed-prefix-only** C48 code mutation census keeps
source C67=125 as the earlier M126 pointer: using a physical `*` at C48
would rotate M67 to 9,565,979, invalid when fetched as C67 code. Using `p`
would make C67 invalid for 256 of the 257 input/EOF classes, with only one
class producing opcode `p`. Thus neither one-cell C48 mutation supplies a
uniform ninth-rotation continuation. This does not rule out a relocated
assembler or a different code/data pointer chain.

### Source-loaded first-read two-crazy byte roundtrip (2026-11-23)

A different **one-read, source-valid** 91-cell N15 continuation now produces
the exact original output byte for every finite input, without the existing
second `getchar` and without host-produced guest output. Five genuine M95
rotations still precede C37 `/`. The source-preserving C42 `j` reads the
graphical C67=67 pointer, and six real C43..C48 `j` operations follow
M68=65, M66=68, M69=64, M65=69, M70=63 and M64=70 to reach the
unexecuted, loader-valid source words M71=M72=121. C49/C50 execute two
actual `p` writes. The 15-trit crazy involution
`crazy(121, crazy(121, byte))` recovers **all 256 finite bytes**; C51
outputs the result and C52 halts.

The independent scalar oracle checks 257 distinct full-width final words:
bytes 0..255 recover themselves, while the true signed EOF word recovers
**7,174,574** and emits **0xae**, not C23's required **0xff**.
Six independent normative N15 guest traces (EOF, NUL, 1, 128, 174 and 255)
terminate after 53 steps, authenticate the exact two M71/M72 data writes,
the pointer chain, the single input attempt, the output and the untouched
M95/M96 operands. The route is a positive physical byte echo, **not** a
signed C23 `getchar` conversion: the EOF output aliases the finite byte
174 at the low-byte output boundary, although their full words differ.
The original seven-block mutable EOF checksum still refuses physical
linkage and never publishes a target artifact. See
`build_c23_first_input_two_crazy_byte_echo_source` and
`tests/compiler_c23_first_read_indirect_store.rs`.

### Width-aware typed shift-result checks (2026-11-23)

The strict opt-in source-computation verifier now interprets integer
`ShiftLeft`, `ShiftRightLogical` and `ShiftRightArithmetic`, instead of
refusing even numerically valid source-placed guest results. It checks the
original typed 8-, 16- or 32-bit width and refuses shift counts outside
that width (including negative signed counts), signed negative left
operands and signed left-result overflow. Unsigned left shift wraps at the
declared width; logical right shift is unsigned and arithmetic right shift
uses the explicit signed IR operation. Boolean shifts and mismatched right
shift signedness remain unsupported.

A red-first real four-step N15 guest initially failed the valid shift
result with `UnsupportedComputation`. Five distinct executed VM store
journals now cover defined positive shifts, unsigned wrapping, a signed
negative arithmetic right shift, wrong right-shift semantics and invalid
counts/negative left operands. Independent canonical two-word C32 controls
check the high bit, signed overflow, 32-bit count boundary and negative
right shifts. Additionally, two seven-step N15 guests physically write both
words of a C32 left operand, count and result; the checker accepts unsigned
`1 << 31`, refuses the same signed overflow and rejects a corrupted high
result word even when the low word matches. These are **numerical checks of
seeded physical writes**, not causal Malbolge computation of C shifts. The unchanged original C23
EOF checksum still refuses its unlinked CFG without publication, and P2
remains open. Regression: `tests/compiler/source_computation_trace.rs`.

### Defined integer division and remainder result checks (2026-11-23)

The strongest opt-in numerical source-computation verifier now accepts
signed and unsigned integer `Divide`/`Remainder` only when every source
operand was physically written and the guest result equals exact typed
arithmetic. Unsigned quotient/remainder use the declared scalar width;
signed operations truncate quotient toward zero and retain the dividend's
remainder sign. Division by zero and signed minimum / -1 refuse with
`InvalidComputationValue` rather than accepting a coincident guest word.
Mismatched signedness and unsupported floating division still refuse.

Red-first actual N15 four-step guests show the old unsupported valid 6/2
result, and now accept finite positive quotient/remainder and negative
signed paths, reject an incorrect signed remainder, zero divisor and narrow
signed overflow. Independent two-word C32 controls check the same rules,
including signed `INT_MIN / -1`. Physical guest arithmetic dependence,
source-C loop branching, signed EOF conversion and complete mutable checksum
publication are **not** provided by this necessary numeric gate.
Regression: `tests/compiler/source_computation_trace.rs`.

### Signed source arithmetic overflow refusal (2026-11-23)

The strongest opt-in source-computation result checker no longer accepts
numerically wrapped signed `Add`, `Subtract` or `Multiply` as though C23
signed overflow were defined. Earlier source-placed VM stores must carry
canonical typed operands, and the computed signed value must fit its original
8-, 16- or 32-bit type before its guest result word can be accepted. Unsigned
addition retains its exact modulo-width behavior. This repair does **not**
materialize the arithmetic or establish causal guest operand reads.

A red-first real four-step N15 `*, *, *, v` guest physically stores i8
`127`, `1` and `128`. Its earlier strict checker accepted the wrapped result
of `127 + 1`; the corrected checker refuses `InvalidComputationValue`.
Independent real VM inputs also distinguish defined `126 + 1`, signed
subtraction/multiplication overflow, and valid unsigned `255 + 1 -> 0`.
Canonical two-cell C32 and i16 boundary checks reject signed overflow while
preserving defined negative results and u32 wrapping. The full seven-block
C23 checksum remains unlinked and no executable source-C guest is published.
Regression: `tests/compiler/source_computation_trace.rs`.

### Strict CFG input-state composition (2026-11-23)

The strongest `SourcePhiCopyProbe::verify_with_source_computations`
now composes the existing independent, source-locked input-result store gate
**when its authenticated physical plan contains a source input effect**.
That stage already proves each real `/` occurs at the source-required site,
checks signed C23 two-cell EOF conversion or unsigned-byte input semantics,
and replays real `p`/`*` stores at the exact effect anchors with guest
input-dependence. A full CFG trace cannot promote an input opcode alone into
a source-C value. The narrower CFG-only and phi-copy studies retain their
explicitly limited contracts.

A red-first current-N15 13-step byte-input/store/return guest previously
passed the strongest numerical/CFG gate even with **empty input**: raw N15
EOF was treated as a valid source `ByteInput` event. The strict gate now
refuses `InvalidSourceInputResult(SourceInputUnreachable)`. The exact same
source-placed physical bytes still pass the composed gate for byte 0 and
byte 255, with a genuine input-dependent M55 result write. Source input
path/stored-result verification is reused, not reimplemented or inferred
from matching output. This does **not** prove arithmetic operand provenance,
produce a linked C23 EOF checksum, or publish any guest artifact.
Regression: `tests/compiler/source_input_cfg_order.rs`.

### Opt-in source computation result authentication (2026-11-23)

`SourcePhiCopyProbe::verify_with_source_computations` extends the strongest
physical source-CFG and phi verification with a **strict, numerical** typed
computation check. Only source-authorized VM `p`/`*` writes or completed
source-bound phi copies can materialize operands; loader-seeded cells never
authorize a computation. At a reached source-placed result Store, the actual
post-step accumulator must equal the typed operation applied to the earlier
physical source operand words. Multiword C32 values are decoded canonically
and both result words must match. The checker supports exact bitwise/additive
integer operations, integer comparisons, and selected integer casts. Unknown
operations refuse as `UnsupportedComputation` rather than passing silently.

An actual four-step N15 `*, *, *, v` guest writes `1`, `2` and `3` from
separately seeded data cells; the strict XOR result check admits `1 ^ 2 = 3`,
but the otherwise identical guest writing `2` at the result site refuses
`InvalidComputationValue`. The same VM trace also rejects a forged AND
operation, an unwritten source operand and an unsupported divide. A separate
four-step real guest carries a two-word zero-extended value and rejects a
wrong high word even when its low word agrees. Independent C32 arithmetic,
comparison and truncation checks exercise typed 32-bit boundaries.

This check is a **necessary value consistency condition**, not proof that a
guest opcode's accumulator causally depended on each source operand. Guest
arithmetic synthesis and operand-read provenance remain unfinished, along
with signed C23 input conversion, source CFG target linkage and the original
mutable EOF checksum. The checksum's complete five-vector regression still
passes only its **explicit refusal/no guest artifact** contract; P2 remains
open. See `src/compiler/malbolge-layout/composition/source_computation_trace.rs`
and `tests/compiler/source_computation_trace.rs`.

### Source-typed numerical opcode validity (2026-11-24)

The opt-in **numeric** computation verifier now refuses an operation whose
explicit typed opcode contradicts the source scalar. `SignExtend` requires a
signed integer source, `ZeroExtend` cannot reinterpret a negative signed
source as a positive value, and a one-bit `Truncate` cannot stand in for C
nonzero-to-Boolean conversion. `BoolToSigned`, `IntegerToBool`,
`IntegerBitcast` and width-changing casts also require the corresponding
source and result kinds and genuine width relation. A former forged
unsigned-byte sign extension produced `0xff80` for source U8 `0x80` where
C unsigned extension requires `0x0080`. A real four-step N15 store of
`1, 2, 0` previously certified a forged byte-to-Boolean truncate although
C23 `(bool)2` is one. Both now refuse with `UnsupportedComputation`, while
valid signed/unsigned extensions and C nonzero conversion still pass.

Integer-order comparisons now require matching operand signedness: an
unsigned U8 `255 < 1` is false and a signed I8 `-1 < 1` is true, so neither
may be checked using the opposite signed-order opcode. Paired normative
four-step N15 guests physically store `255`, `1` and the opposing Boolean
result to demonstrate prior false acceptance and corrected refusal. The
verifier also refuses one-bit `Add`, `Subtract` and `Multiply` on `_Bool`
operands: C promotes those operands to integer before arithmetic, and
`(bool)(true + true)` is one, not the wrapped one-bit sum zero. A real
four-step N15 `1, 1, 0` guest now refuses such forged addition but still
passes a matching typed Boolean XOR. The same gate checks every result
operand's **physical word count**: a Boolean, byte or I16 result occupies
one guest word, whereas C32 takes two. The actual four-step N15 `1, 2, 3`
XOR guest previously passed with a forged two-word U8 result despite only
one reached result store; it now refuses `InvalidSourcePlacement`. Direct
positive and negative controls cover C32 low/high words and narrow scalar
result placements. Regression: `tests/compiler/source_computation_trace.rs`.

These are defensive **typed numeric acceptance conditions** over seeded,
real VM stores; they do not synthesize guest arithmetic or prove the real
physical operand dependencies. The original full seven-block mutable C23
EOF checksum remains unlinked at guest CFG, phi transfers, signed EOF
conversion and guest arithmetic. Its three pipeline tests still pass only
explicit refusal without publishing a target. P2 remains open.

### Physically sourced phi-copy dataflow (2026-11-23)

The linked-CFG physical phi transfer gate now requires the *latest*
source-authenticated SSA word's provenance in the actual guest accumulator
before accepting each reached snapshot and commit. A matching written word
alone cannot establish a data path from the declared copy source. The same
versioned `p`/`*` provenance shadow is used by the stronger source branch
and output checks, and successful copies mint new SSA versions only after
this path check. The intentionally narrower copy-only gate still verifies
word values and ordered physical writes without asserting causality.

A paired seven-step current-N15 VM witness writes EOF into M70 at C0,
then copies it at C3 and C4 before a real C5 control jump and C8 halt.
Replacing the inert C1 with a real `*` on independent M71 preserves all
three identical source/phi words but severs the accumulator's M70 path.
The older value-only gate admits both, while linked-CFG and source-branch
checks now refuse the disconnected version with `MissingPhiProvenance`.
This is a **necessary dataflow condition**, not a proof of exact C arithmetic
or actual checksum loop linkage. The full source C23 checksum still refuses
its unlinked seven-block CFG without publishing a guest artifact.
Regression: `tests/compiler/source_phi_copy_trace.rs`.

### Versioned source-output data provenance (2026-11-23)

The strongest opt-in source CFG output check now authenticates a data path
from the **latest physical write** to its source U8 SSA operand. Source
provenance is tagged with the actual bounded VM trace index, not only the
cell address. A later source-authorized write supersedes the prior version
for output verification, even if both versions have the same numeric value.
The forward shadow still conservatively propagates possible dependencies
through physical `p`/`*` and cannot prove exact arithmetic or control.

A red-first real 11-step N15 guest writes zero into source M70 at C0,
propagates that first version through two `p` operations to M76, rewrites
M70 with zero at C5, then reloads M76 with `*` at C8 and emits zero at
C9. Both source Stores and Output, full-width values and guest I/O match.
The address-only shadow incorrectly accepted this obsolete dependency;
versioned provenance refuses `MissingOutputProvenance`. The paired real
guest uses `o` at C8 to retain the *new* C5 accumulator and passes at
identical source sites, with the same output byte. This is a bounded
physical-output necessary condition, not an executable C23 checksum. The
unchanged full mutable EOF checksum still fails closed at the seven-block
source CFG target linker without publishing a `.malbolge` artifact.
Regression: `tests/compiler/source_phi_copy_trace.rs`.

### Physical output accumulator data provenance (2026-11-23)

The strongest opt-in source CFG verifier now requires a reached `<` not
only to equal its latest source-placed U8 SSA word, but also to carry an
actual guest **data path** from that word's authenticated physical write.
The forward shadow starts empty, mints source-cell provenance only on
source-placed `p`/`*` frame writes, propagates possible dependencies through
real `p`/`*` data writes and reads, preserves A across non-data opcodes,
and clears it at a new `/`. Untouched loader cells and numeric coincidence
cannot invent a provenance edge. The shadow is deliberately conservative:
`p` can carry both input dependencies, so this is a necessary condition,
not a proof of exact C arithmetic or causal byte-stream semantics.

A red-first four-step N15 `*, *, <, v` guest physically writes M70=1,
then independently writes M71=1 before emitting byte 1. Its declared
Output operand is M70. Both Store sites and the full-width output value
match, and the prior equality-only checker accepted this wrong data path.
The updated gate refuses `MissingOutputProvenance` because the second `*`
loads A from unrelated M71. The paired `*, o, <, v` guest keeps A from
M70 and passes. No C23 checksum arithmetic, EOF loop or source-C artifact
is linked or published. Regression: `tests/compiler/source_phi_copy_trace.rs`.

### Phi-free source control paths in physical CFG verification (2026-11-23)

The strongest opt-in source CFG check no longer demands a reached phi copy
on a physical path that never enters a phi-bearing edge. Its predecessor,
source-operation, branch, return, and reached-pad checks remain mandatory.
The narrow `verify`/copy-only study still refuses `NoReachedPhiCopy` when
there is no actual copy to verify. Exit/ingress/whole-CFG policies instead
validate **every entered pad** and can return a proof with zero completed
pads if none was entered. Previously a valid path that returned through an
entirely phi-free branch could never satisfy the strongest CFG verifier.

A real three-step N15 `o, o, v` guest reaches a source-positioned Return
control suffix without visiting the separately reserved phi pad. The
independently checked block exit, entry, effect, return, predecessor-phi,
and branch gates all pass. The transfer verifier now accepts zero copies,
while the unchanged copy-only gate rejects the identical genuine trace.
A second five-step normative guest enters a real phi pad then halts before
its first required snapshot. The stronger transfer gate still refuses
`InvalidPhiOrder` even with zero observations; an earlier 16/14-step
pair also continues to reject a second pad that skips its copies.
This corrects a false refusal; it does not link the seven-block C23 checksum,
prove source-C arithmetic or make a source CFG candidate executable.
Regression: `tests/compiler/source_phi_copy_trace.rs`.

### Source-operand output equality in physical CFG traces (2026-11-23)

The opt-in strongest source CFG trace gate now checks a reached `<` against
both the exact current 15-trit accumulator and the previously guest-written
value of its source-authenticated U8 SSA operand. Earlier source-placed
`p`/`*` writes and independently checked phi copies supply the temporal
frame journal; loader-seeded cells and unplaced writes cannot satisfy it.
The value must be representable as U8, not merely congruent modulo 256.
A real N15 four-step `*, o, <, v` guest rotates M70=3 into the word 1 and
outputs 1, passing the physical source store/output checks. Pointing the
same source Output at unwritten M71 refuses `MissingOutputMaterialization`.
Replacing C1 with a second `*` rotates M71=6 to 2; the resulting real
output 2 is source-placed and both stores execute, yet the declared output
operand still holds 1. It now refuses `InvalidOutputValue`. With
M71=771 instead, C1 produces word 257: the actual output byte is again 1,
but the full accumulator fails the same operand-equality gate. This proves
physical value equality, not how the accumulator loaded the operand or
whether source-C arithmetic and branches are correct. The complete C23
checksum still refuses before target publication. Regression:
`tests/compiler/source_phi_copy_trace.rs`.

### Exact source-effect counts across physical revisits (2026-11-23)

The opt-in strongest source CFG trace gate now partitions physical code
visits at declared control-suffix self-backedges, not only changes to a
different block interval. Every reached visit must execute each ordered,
source-authenticated effect site **exactly once**. Returning to a setup
position inside the block is not a source iteration: repeating an effect
site there refuses `RepeatedBlockEffect` rather than borrowing an earlier
occurrence. This preserves the distinction between a source CFG iteration
and an untrusted guest instruction loop.

Two real N15 observations isolate the previously admitted gaps. A
four-step terminating `o, o, o, v` guest executes both declared Compute
anchors once and passes. A six-step terminating guest executes
C0, C1, C2, C1, C2, C10, with real indirect jumps at both C2 visits and
the source site at C1 reached twice without leaving the block. It now
refuses the duplicate C1 anchor. A separate four-step `o, o, i, o`
bounded prefix jumps from C2 back to its block's C0 entry, starting an
incomplete second visit and refusing the missing C1 effect. Only that
second negative is a **bounded VM prefix**; a full run is still required
by the public strongest gate. These are operation-site provenance checks,
not C arithmetic, source return or a complete guest checksum. The
unchanged C23 source still refuses unlinked physical operations, parallel
phi writes, branching and EOF loop.
Regression: `tests/compiler/source_phi_copy_trace.rs`.

### Source CFG self-backedge control authentication (2026-11-23)

The strongest opt-in physical source CFG exit, entry and branch checks now
recognize a source block's **own control suffix** returning to its canonical
entry as a real source CFG self-backedge. Previously all same-block movement
was exempt, so an undeclared control-suffix `i` could reenter C0 without a
source edge. Ordinary setup movement between cells within the same block
remains exempt; only an actual control-to-start transfer requires the source
edge and, where applicable, its materialized Boolean branch selection.

A three-step source-loaded N15 prefix executes a genuine C0 `p`, C1 `i`,
then fetches the self-encrypted C0 again. Its pointer destination is seeded
at the last guest memory word and wraps precisely to C0. Before the repair,
source exit/entry/branch checks admitted this transfer with no source edge;
all three now refuse it, while the source-declared C0 self-edge passes.
This is finite loop **control provenance**, not an unbounded working loop,
correct repeated effect execution, signed EOF handling or C23 checksum.
Regression: `tests/compiler/source_phi_copy_trace.rs`.

### Extra physical I/O outside source effect sites (2026-11-23)

The opt-in strongest source-CFG trace gate now refuses **every** real `/`
input or `<` output that executes outside its exact source-authenticated
operation-effect address, including setup gaps, phi pads and unreserved code.
Previously, reaching every declared operation site was sufficient even when
additional guest I/O happened at an unrelated instruction. The new check
runs on the same normative VM trace before source-block effect visitation;
copy-only and ingress-only phi probes keep their narrower contracts.

A five-step source-loaded N15 guest executes its required C0 Store and C2
Compute sites, but replacing the otherwise inert C1 setup instruction with
`/` or `<` introduces extra input/EOF or output and now refuses. Each actual
opcode is accepted when the C1 effect is explicitly source-placed as the
matching input or output. This is physical event provenance, **not** proof
of input conversion, operand values, C arithmetic, output parity, or the
complete EOF checksum. The whole source C23 compile was retried unchanged:
it still refuses seven unlinked blocks, 19 operations, four phi edges and
43 reserved guest words without publishing a `.malbolge` program. Regression:
`tests/compiler/source_phi_copy_trace.rs`.

### Physical source return control (2026-11-23)

The strongest opt-in physical CFG check now requires the final real guest
`v` instruction to occur in the source-bound control suffix of a Return
block. A valid source-block exit, complete operation effects or successful
phi copies cannot authorize a halt somewhere else in the code image.
The return's canonical block/function and reserved control start must
match the source-locked addressed plan; this gate verifies terminal code
provenance, not the function's returned scalar or preceding C computation.

A five-step N15 `p, o, o, o, v` trace reaches source Return block C4.
A separate real four-step `p, o, o, v` trace executes the same required
operation effects but halts at C3 in its predecessor's control suffix.
The older physical block exit and operation-effect checks admit both;
the return control gate now refuses the early halt and accepts C4.
The original seven-block mutable EOF checksum remains physically unlinked,
so no source-C guest artifact or parity is claimed. See
`tests/compiler/source_phi_copy_trace.rs`.

### Physical phi-pad completion on every visit (2026-11-23)

The stronger opt-in physical phi transfer/ingress/CFG gates now account for
**every entered phi pad** in the normative guest trace, even if no declared
copy site executes during that visit. Entering a second pad after one valid
transfer cannot borrow the earlier pad's completion count. The guest must
perform all required snapshot and commit sites in order exactly once per
visit before leaving; missing copies or repeated completed copies refuse
`InvalidPhiOrder`. The original copy-only gate intentionally retains its
narrower reached-copy claim.

A paired source-loaded N15 witness uses the same two source-positioned phi
pads. Its 16-step path physically performs both snapshot/commit pairs and
reaches the second declared successor. Its 14-step path performs the first
pair, but physically jumps over *both* copy sites in the second pad before
reaching the identical successor. Block exits, block entries, predecessor
phi ingress and the older copy-only gate all accepted the second path;
the stronger copy-transfer gate previously accepted it too. It now refuses,
while the complete two-pad guest passes. This is still a necessary bounded
CFG transfer obligation, **not** proof of source arithmetic, branch
computation, source C23 checksum output or a generated full program. See
`tests/compiler/source_phi_copy_trace.rs`.

### Reached source-block effect order and physical opcodes (2026-11-23)

The strongest opt-in physical CFG verifier now checks **every visit** to a
source-reserved code block against its canonical operation-effect sites.
All required sites must actually execute, in source order, before the
block exits or halts. Setup loops are allowed between sites, but a real
intra-block jump that skips one source effect must refuse even if its later
block exit and successor entry are correctly placed. Repeated visits must
satisfy the same obligations independently.

A reached effect site must also decode as a real `/` input, `<` output, or
`p`/`*` Store with the exact destination guest cell and any source-locked
literal word. The generic Compute site remains an **occurrence-only** check;
this verifier does not authenticate C arithmetic, register dependence,
input conversion, operand reads or whole-program output parity. On a real
N15 guest, a complete five-step `p, o, o, o, v` block visit passes; a real
four-step `p, i, o, v` trace skips its required C2 site despite matching
control exits and refuses. A guest `o` forged as a Store, a wrong Store
address, a wrongly labeled output opcode and reversed source effect order
also refuse. The original C23 EOF checksum remains unlinked and cannot
publish guest code. Regression: `tests/compiler/source_phi_copy_trace.rs`.

### Source-locked physical CFG block ingress (2026-11-23)

The opt-in `SourcePhiCopyProbe::verify_with_cfg_phi_copy_anchors` also
checks each reached **arrival** into a source-reserved code block. A fresh
arrival must land at the block's canonical start. The initial reached
source block must be the source-identified function entry; subsequent
arrivals must come from a canonical predecessor's reserved control suffix
for a phi-free edge, or the exact source-placed `i` exit of an edge-local
phi pad. A correct outgoing target alone cannot authorize an arbitrary
incoming jump, a middle-of-block landing, or a foreign predecessor. This
reuses the same normative guest trace as the outgoing-edge and phi checks.

A real three-step N15 `*`, `i`, `v` guest enters either source successor C2
or C4 from C1, while a truncated trace that begins inside the successor,
a forged predecessor, and a mid-block target refuse. A separate real
nine-step N15 phi guest accepts C7 `i` -> successor C10, but refuses a
forged pad exit C6. This is a finite necessary block-entry condition;
source operation execution order, branch condition computation, C return,
and the unlinked C23 checksum remain separate open obligations. Regression:
`tests/compiler/source_phi_copy_trace.rs`.

### Physically materialized Boolean branch-arm consistency (2026-11-23)

The opt-in source-locked `verify_with_cfg_phi_copy_anchors` now also checks
that every reached conditional source-block departure agrees with the most
recent **real guest-written** Boolean value at the canonical one-word SSA
condition cell. Frame write sites are checked first; the branch checker does
not trust loader-seeded data, a future store, an unrelated frame write, or a
non-Boolean value outside `0`/`1`. A source branch's true/false outcome must
match the selected canonical edge. A common successor with two distinct
source edge identities remains indistinguishable by code address alone; the
branch checker can only require one matching outcome at that address.
Unconditional control edges are unaffected. The same finite normative VM
trace supplies the frame chronology, block exits, phi ingress and phi copies.

A three-step seeded N15 guest executes real `*`, `i`, `v`: C0 rotates M70
from 0 to 0 or 3 to 1; C1 takes the physical false C2 or true C4 edge.
Matching values/edges pass; both reversed targets, a word-2 Boolean, a
truncated trace that omits the prior write, and an unapproved effect site
refuse. A separately seeded pointer selects the target in these witnesses:
this proves **consistency**, not that the guest computed the C condition
correctly or that its branch depends on that computed Boolean. The seven-
block mutable C23 EOF checksum still refuses unlinked target lowering,
with no published guest artifact. Regression:
`tests/compiler/source_phi_copy_trace.rs`.

### Source-bound physical exits from CFG blocks (2026-11-23)

The opt-in `SourcePhiCopyProbe::verify_with_cfg_phi_copy_anchors` now
checks every reached physical **departure** from a reserved source block,
including phi-free edges. If the next real VM instruction falls outside
that source block, the leaving instruction must be inside its reserved
control suffix, and the reached code address must be one of that canonical
predecessor's source-bound edge entries. This runs on the same finite VM
trace as phi-pad ingress, actual two-phase copies, and successor exits.
A source return's terminal action remains a separate proof obligation;
this check neither proves branch-condition truth nor implements guest C.

A real nine-step current-N15 guest exits the C0-C2 source block at C2
and enters its phi pad at C3. A physically executed C1 `i` instead exits
too early into that same pad; changing only the proposed edge target also
refuses. A separate real five-step N15 source witnesses the adjacent
phi-free C1 -> C2 edge, while the forged C1 -> C3 target refuses. These
are bounded necessary physical control/placement checks; the seven-block
C23 checksum still refuses before target publication.

### Source-locked physical predecessor-to-phi ingress (2026-11-23)

The opt-in `SourcePhiCopyProbe::verify_with_predecessor_phi_copy_anchors`
now replays every reached phi-pad **entry** against the source-authenticated
predecessor block's reserved control suffix. The immediately preceding real
VM transition must originate between that block's control start and its end,
and its actual post-step C must equal the first cell of the edge-local pad.
A jump into the middle of a pad, or a landing from a foreign control site,
refuses `InvalidPhiEntry`. The existing snapshot/commit word-copy and
reserved successor-`i` checks are still required in the **same** finite
normative guest trace. The earlier copy-only and exit-only public gates
remain separately available with their narrower guarantees.

A nine-step current-N15 seeded guest physically executes C0 `p`, C1/C2
`o`, C3 `j`, C4 `p`, C5 `j`, C6 `p`, C7 `i`, then C10 `v`. Its source control
C2 falls through into the C3 phi pad, copies the prior frame word through
M101 into M120, and transfers from C7 to the successor C10. An eight-step
negative instead uses a **real C1 `i`** to bypass the source control C2,
but still reaches C3, performs both identical physical copies and the same
C7 -> C10 successor jump. The old copy-plus-exit check accepts both;
the predecessor check accepts only the actual C2 ingress. Mid-pad and
foreign source-control negatives also refuse. The seeded machine state
is a finite physical transfer witness, not an emitted whole-C program.

This necessary control-**origin** check does not establish the truth of a
conditional branch, guest arithmetic, an unbounded loop or source-C output
parity. The original seven-block mutable C23 EOF checksum still refuses
unlinked target lowering and publishes no `.malbolge` artifact. Regression:
`tests/compiler/source_phi_copy_trace.rs`.

### Source-locked phi successor-transfer replay (2026-11-23)

The opt-in `SourcePhiCopyProbe::verify_with_linked_phi_copy_anchors`
checks the final physical `i` instruction of each **reached** phi pad after
all guest-written snapshots and commits. A completed pad must stay inside
its own code interval, execute the reserved exit cell and land at the exact
source-placed successor code address; a missing exit, wrong target or early
halt refuses. The original copy-only gate still reports its narrower value
and ordering evidence without silently upgrading it to a control proof.

A frozen seven-step, seeded-state N15 guest executes physical
`p, j, p, j, p, i, v`, copying M70 to M101 and M101 to M120 before jumping
from C5 to the successor halt at C8. Source-backed copy site models and the
normative guest trace agree on the two written words and the reached `i`.
Changing only the exit into `o` still leaves identical copy values but
refuses the new transfer gate; jumping to C9 or ending after the commit
also refuses. A second eight-step N15 trace inserts `o` at C5 after the
commit, then takes the reserved C6 `i` to C8: the gate accepts harmless
pad-local setup but refuses a jump at C5 that bypasses the declared exit. This establishes a **bounded, one-edge necessary condition**,
not proof of predecessor branch selection, complete source arithmetic,
repeatable CFG execution, or source-C checksum publication. The original
seven-block C23 checksum still explicitly refuses at unlinked target
lowering, with no guest artifact. Regression:
`tests/compiler/source_phi_copy_trace.rs`.

### Sparse source-locked physical phi-copy sites (2026-11-23)

Source-backed physical CFG placement now optionally binds every snapshot and
commit in one predecessor-owned phi pad to an individually named effect site.
These `GuestCodePhiCopyAnchor` positions are re-identified against the
canonical source and must remain strictly increasing, unique, complete,
inside the correct disjoint edge pad and before its successor-transfer cell.
Unanchored pads retain the old compact suffix. Explicit sites allow guest
pointer routing or operand setup **between** writes, not just before the
first snapshot. This is a code-placement obligation, not emitted source.

The bounded `SourcePhiCopyProbe` replays those placements in the normative
N15 VM and allows non-copy instructions only while an in-flight pad stays
inside its own physical interval. A real six-step N15 trace uses `p, j, p,
j, p, v`: its snapshot at C2 and commit at C4 are separated by a real
pointer-routing instruction that moves D from M102 to remote M120. Both
copy words are checked against earlier guest frame writes. Replacing the C3
setup with a real `p` on a reserved source frame
refuses as an unaccounted store. A second physical negative executes an
*idempotent* `p`: with the EOF accumulator and M102=0, `crazy(0, EOF)=0`,
so the guest writes M102 with no changed-cell delta. The verifier still
refuses the unauthorized store. A real `i` from C3 to C5 also refuses
because it skips the required C4 commit and halts mid-pad. For the
original C23 checksum's 5->1
backedge, a source-locked 8-copy proposal accepts sparse physical positions
and rejects incomplete, swapped, duplicate, off-pad, forged-edge and
successor-transfer aliases. These are separate bounded placement and guest
witnesses; no checksum phi pad has yet been physically linked and executed
from source C. Branch selection, source arithmetic, input-dependent EOF
termination and the original five-stream C23 guest remain unresolved.

### Temporal source-output operand materialization (2026-11-23)

The opt-in combined source-output/input-store verifier now checks each reached
physical `<` against the **current, previously guest-written** value of its
exact source-authenticated U8 SSA operand. Every candidate operand value must
come from an earlier normative-VM `p`/`*` write at a source-placed Store or
phi-copy site, not from loader data, a future write, or an unrelated cell.
The existing whole-frame effect-site check still rejects foreign writes and
frame XLAT2 aliasing. It uses the same bounded VM trace; no additional replay
is required. Exact U8 constants are now evaluated by the source-known output
path, enabling the independent guest to expose wrong SSA operand linkage.

A real 61-step N15 guest emits byte 37 and stores its input in M73. Its
single-byte input/output source is accepted, but a different source whose
`ByteOutput` instead reads a constant-37 SSA cell M74 is rejected despite the
identical real output and matching input store: no guest instruction ever
materialized M74. This verifies a temporal *necessary condition*, not that the
VM accumulator actually loaded the operand, reproduced source arithmetic, or
executed correct CFG branches. The original C23 checksum remains unlinked.
See `tests/compiler/source_input_cfg_order.rs` and
`src/compiler/malbolge-layout/composition/source_input_state_trace.rs`.

### Source-wide physical frame-store site checks (2026-11-23)

The opt-in combined source input/output/store verifier now reuses the already
captured normative VM input-store trace to inspect **every** reached `p`/`*`
whose destination belongs to any source-reserved SSA frame or phi scratch
cell. Such a write must occur at the exact `(code address, data address)` of
a source-authenticated `Store` effect or edge-local phi snapshot/commit.
A source literal store must also leave its specified full-width word in the
real accumulator, including an idempotent write without a memory delta.
Guest instruction fetches or XLAT2 target accesses into source data frames
refuse as code/data aliasing. A real indirect `i` at C1 whose off-site XLAT2
target is M73 verifies that a source frame need not be fetched as code to
trigger this refusal; non-frame M74 remains allowed in the same one-step VM
trace.

The 5-step real N15 guest with a physical idempotent `p` at C3 targeting
M57 rejects a missing/foreign site and an incorrect literal value, while
accepting the exact physical site and literal. The previously established
63-cell live input/store/output guest now also passes an isolated
61-step combined source-anchored byte-37 read/store/output case. Its original
multi-vector negative matrix remains a separate, more costly regression.
Frame-wide site admission is **not** a source operation-count
journal for non-input stores, a phi value-copy proof, or runtime C32 arithmetic
and branch verification. The original C23 EOF checksum remains unlinked.
See `tests/compiler/source_input_store.rs` and the source-state verifier.

### Complete source input-store effect chronology (2026-11-23)

The opt-in physical source input-store gate now checks **exactly one**
real `p`/`*` frame write per source-authenticated input-result Store effect,
ordered by the actual normative VM trace index. Valid source-loop revisits
retain a distinct write for every newly reached input definition; signed C23
high/low words may be written in either physical order. Additional writes at
**the same authorized code address and frame address** now refuse as
`UnattributedGuestStore`, even when the extra store is idempotent or is
followed by a matching final value. A write at an unauthorized location still
receives the more specific `UnexpectedGuestStoreSite` refusal.

This sharpens the finite source/store authenticity check without proving a
linked mutable C23 checksum, guest arithmetic, phi transfers or repeatable
source control flow. The regression uses synthetic trace-journal mutation;
the existing actual 63-cell N15 input/store/output guest still independently
proves the positive physical path and off-site store refusal. See
`tests/compiler/source_input_store.rs` and
`tests/compiler/source_input_cfg_order.rs`.

### Authenticated output-operation identity (2026-11-23)

The opt-in output trace now records each real VM output's source-bound
`(function, block, ordinal)`, code address, byte and step index. A
source-return path must match the **ordered source operations**, not only
identical output bytes emitted at some reserved output address. The original
byte I/O event sequence remains unchanged; physical site observations are
separate and present only for explicitly anchored output verification.

A real 63-cell current-N15 guest reads at C13 and outputs the same byte at
C24 and C26. NUL, `0x25` and `0xff` streams prove two individually reached
source-placed output instructions. A typed two-output path whose operation
identities are reversed refuses despite byte-for-byte equality. This closes
one finite trace-authentication gap, **not** physical source-C arithmetic,
C23 signed EOF stores, CFG transfer or the checksum loop. Regression:
`tests/compiler/source_input_cfg_order.rs`.

### Source frame write chronology and return integrity (2026-11-23)

The opt-in source input-store verifier now retains the exact chronological
journal of **every** reached `p`/`*` write to a reserved input-result frame
word, including unchanged (idempotent) writes and overwritten values. The
source-effect gate matches every such physical `(code address, frame address)`
to an authenticated typed store effect, not just the first successful input
store. The current source value must remain correct at bounded return; a
jump-target XLAT2 into a reserved frame is also rejected as code/data aliasing.
These checks are in addition to the existing source-compatible output and
real input-dependence conditions.

For the same 63-cell source-loaded N15 byte input/store/output guest, changing
C29 from `j` to `*` produces an extra real M73 write **after** C17's genuine
store and C24's output. With NUL input, the extra rotation is idempotent:
physical output, stored byte and termination are preserved, yet the stricter
effect gate refuses `UnexpectedGuestStoreSite` because only C17 was authorized.
With byte `0x25`, the extra rotation corrupts the stored result, so final
state verification independently refuses `InputResultMismatch`. This closes
a physical-frame provenance hole without implementing source-C arithmetic,
C23 EOF normalization, phi transfers or a guest checksum loop.
Regression: `tests/compiler/source_input_cfg_order.rs` and
`tests/compiler/source_input_store.rs`.

### Combined source output and physical input-store gate (2026-11-23)

The opt-in `verify_output_and_stored_with_effect_anchors` gate now requires
both source-known byte output at the authenticated physical `<` address and
input-dependent writes to every source-reserved guest result word at its
individually anchored physical `p`/`*` instruction site. The two separate
normative VM replays use the same graphical source, binary input and finite
step budget; the store replay must agree on termination, input consumption
and output. Neither source-output equality alone nor matching guest memory
without a reached source store site can satisfy this combined contract.

A frozen, source-loaded 63-cell N15 guest executes `/` at C13, a genuine
byte-dependent `p` store into M73 at C17 and `<` at C24 before halting at
C60. The one-byte typed source function contains `ByteInput` followed by
`ByteOutput` of that SSA value. NUL, `0xff` and `0x49` pass with exact byte
output and independently verified store word; extra supplied input is left
unread. Relocating only the store effect anchor to C16 rejects with
`UnexpectedGuestStoreSite`. Shifting the physical output from C24 to C23
preserves the input-dependent state store and byte output, but the combined
gate rejects `UnexpectedGuestOutput`. Removing C24's output entirely refuses
`SourceOutputNotProven`; real EOF on the U8 source refuses
`SourceInputUnreachable`. This extends the real guest witness
from separated I/O and state obligations to their conjunction, not source
operand-use authentication, signed C23 EOF conversion, guest arithmetic,
phi transfer, reusable loops or original mutable checksum publication.
Regression: `tests/compiler/source_input_cfg_order.rs`.

### Source-authenticated sparse input/store effects (2026-11-23)

The source-locked physical planner can now bind individual required guest
instruction effects to `GuestCodeEffectAnchor` addresses in an expanded
code block. For a source `ByteInput`, this permits real setup code between
its `/` and later `p`/`*` store; signed C23 `Getchar` can similarly reserve
separate locations for both required C32 word stores. Canonical type,
operation/effect order, code/block bounds and non-overlap still decide
admission. Duplicate, foreign, reordered or inconsistent anchors refuse;
old operation-only callers retain their adjacent minimum effect sites.

The opt-in `verify_stored_with_effect_anchors` gate independently executes
the original physical source in the normative VM, verifies input-dependent
result words and checks that every completing data-write instruction ran at
its source-placed store address. A real 13-step N15 guest executes `/` at
C7, an intermediate `p` at C9, and a byte-exact `p` at C11 writing M55.
The typed U8 source admits NUL and high-byte streams, but moving the
otherwise identical store obligation to C10 or leaving it at the old
adjacent C8 is rejected with `UnexpectedGuestStoreSite`. True EOF is
rejected at the U8 source path, not silently converted into a byte.

This proves a small real guest byte-input store, not signed C23 EOF
normalization or stores, full checksum state, guest arithmetic, physical
CFG/phi transfers, a reusable loop or a published checksum artifact.
Regression: `tests/compiler/source_input_cfg_order.rs`.

### Reached output-site provenance for source-placed I/O (2026-11-23)

The explicit-operation `SourceInputProbe` output gate now requires each
reached physical `<` to run at an authenticated `ByteOutput` effect address
in the original typed-CFG placement. Matching output bytes and I/O order
without the addressed effect is no longer sufficient: such a guest refuses
with `UnexpectedGuestOutput`. This check reuses the source-validated block
placements and operation anchors, not a caller-provided list of arbitrary
output addresses. The input-only and return-only gates remain independent.

A six-cell source-loaded N15 witness executes two genuine `/` reads at
C0 and C2 and outputs the second successful byte at source-placed C4.
Relocating only that physical output to C3 preserves the input stream,
output byte and source-compatible read/return path, but the stronger
output-site gate rejects it. The original 132-cell signed EOF classifier
also fails this new placement condition: its output is not a source-placed
checksum `ByteOutput`. These are **necessary** instruction-address checks,
not proof of real SSA result stores, C23 signed EOF conversion, guest
arithmetic, physical CFG/phi transfers or the full checksum program.
The original checksum still refuses before artifact publication.
Regression: `tests/compiler/source_input_cfg_order.rs`.

### Source-locked physical operation anchors (2026-11-22)

`GuestCodeOperationAnchor` supplies a source-identified proposed position for
an instruction's **first physical effect**. The source-locked CFG linker
planner can now leave checked setup gaps in an expanded code block rather
than forcing every SSA operation's minimum effect cells to start at the
block's first address. It preserves canonical source identity, instruction
order, full-width input/store effect obligations, unselected branch edges,
addressed phi landing pads, and disjoint code/data reservations. Duplicate,
foreign, out-of-order, overlapping or out-of-range anchors refuse. Later
effects of a single operation occupy consecutive *minimum* cells in
this operation-only path; the newer effect-anchor path above can reserve
setup gaps but still cannot synthesize the pointer routing itself.

An explicit-proposals option on the public `SourceInputProbe` now checks the
real normative VM's input steps against those source anchors, rather than
accepting only the earliest automatically packed code cells. The unchanged
132-cell signed EOF branch physically reads at C53 and conditionally C101:
empty input performs one EOF read in 119 steps, while `00` and `ff 00 2c`
perform two reads in 175 steps. The source-locked checksum's corresponding
input operations can be placed at those addresses with disjoint minimum
CFG reservations. The stricter output/return check **rejects** the same
physical helper: its marker output is not the source checksum, and its
byte-byte path halts before the next required source loop input.

The explicit-placement path now also supports the existing input-result
state checker. It requires a source-compatible return, then independently
replays the same original guest to demand genuine input-dependent `p`/`*`
writes to **both** allocated C23 result cells. The 132-cell branch fails
with `MissingInputResultStore` for empty, NUL and `ff` first reads. This
rejects the tempting but false inference that a real signed input opcode
by itself materializes a C32 source local. Its read-only and output-only
checks remain available independently of this stronger state gate.

This is an input-site and code-placement **necessary-condition witness**,
not guest code synthesis, successful typed C32 input storage, arithmetic,
phi writes, reusable loop control, or a whole-program translation certificate. The
original `mutable_eof_checksum.c` continues to refuse before publication.
Regression sources: `tests/compiler/source_dynamic_checksum.rs` and
`tests/compiler/source_input_cfg_order.rs`.

### Source-modified future input opcode (2026-11-21)

A physically executed 81-cell N15 guest now demonstrates an actual code/data
alias: C56 `j` sends D to M79, C57 `*` rotates original M79=114 into 38,
changing the not-yet-fetched C79 `<` to `/`. Four byte/EOF streams execute
C79's **real input** and C80's halt; replacing only C57 with `o` instead
executes the original `<`, outputs a zero byte, and consumes no input.
The code-cell phase planner now admits ordered full-width guest data writes
(including a pre-fetch write), checks their exact memory versions and
rejects forged writes, invalid words and non-graphical fetch/XLAT2.
Source-loaded execution proves the concrete 81-step case, not arbitrary
input code synthesis. Full C23 checksum state, EOF branch and loop remain
physically unlinked. See `tests/compiler_code_data_alias_guest.rs` and
`docs/technical/compiler/physical-code-data-aliasing.md`.

### Source-bound code-cell mutation scheduling (2026-11-21)

A bounded physical-linker prerequisite now checks ordered graphical
code-cell fetches and off-site `i` target encryption separately. A repeated
`i` does **not** self-encrypt, whereas an `i` on another site may encrypt a
cell without fetching it. The source-loaded four-read N15 fixture verifies
seven stable C49 `i` visits, seven encrypted C47 visits, C43 external
XLAT2 and exact final code words on five byte/EOF streams; deleting one
actual C43 target-encryption event gives the wrong final memory word.
The enumerating and source-checking planners do not prove that proposed
jumps or source arithmetic execute. See
`docs/technical/compiler/physical-code-cell-schedule.md` and
`tests/compiler_code_cell_schedule.rs`. The original mutable C23 checksum
still refuses at the physical linker, not at this local phase schedule.

### Live-dependency-bound physical reentry (2026-11-21)

The 132-cell C71 return analyzer now projects each reached interval through
the existing portable v6 effect-IR checker. Memory values read before the
first write, and registers read before the first overwrite, are retained as
explicit live-ins. This distinguishes a changed but dead guest cell from a
changed code/data/register value that the next traversal needs. A separate
source-loaded normative trace projection agrees on the live-in memory and
register masks, and full memory snapshots check the entry values. The
`live_entry_restored` and `fixed_input_replay_preconditions` predicates
fail for the current signed-third-read return; no parametric C23 cycle or
guest checksum has been linked.

### Exact physical reentry state contract (2026-11-21)

A normative N15 trace-journal checker now compares **all changed guest
memory**, A/C/D registers, byte consumption, output and XLAT2 effects across
genuine repeated physical code entries. A source-loaded 132-cell signed
third-read candidate visits C71 at steps 71 and 141, but its live D changes
from 141 to 7,174,359, A changes from 134 to 4,783,015, and 78 memory
words differ; 8 genuine data-write instructions and 70 XLAT2 changes are
recorded. A second real VM replay compares the journal to two full
14,348,907-word memory snapshots and finds exact agreement. Chronological
guest data-read and `p`/`*` write-target footprints are now checked against
another independent normative trace, including idempotent stores. Three binary
streams pass; EOF early exits and a rejected third reentry fail closed.

This exposes missing physical state restoration without pretending a
code-pointer return is a reusable C loop. It is a finite, source-loaded
necessary-condition check, not an arbitrary-input loop, linked C23 locals,
or checksum publication. See
`docs/technical/compiler/physical-reentry-state-contract.md` and
`tests/compiler_physical_reentry.rs`.

### Post-flag graphical code-transfer bound (2026-11-21)

The original seven-block mutable C23 EOF checksum was again run through the
pinned frontend/adapter and native C23 `-O0`/`-O2` controls on all five
binary inputs. The native oracles agree, while real C-to-Malbolge publication
still **refuses** the unlinked dynamic CFG. No guest checksum was emitted.

`tests/compiler_eof_flag_forwarding_guest.rs` now freezes an additional
**physical code-transfer search**, not another literal-output witness. It
starts with the existing 33-character current-N15 EOF-flag source. Each of
257 independently run, 27-step normative VM prefixes (all 256 byte values
and actual EOF) leaves A=0 for bytes or A=15 for EOF. Importantly, its live
D is still byte-dependent even though A has the desired class value. The
trace checks that C27..C30 are never read, fetched or written during that
prefix, so changing those future source bytes cannot alter the entry state.

The frozen local grammar has 85 candidates: every length-zero-through-three
sequence over `o`, `j`, `p`, `*`, followed by a single `i` at C27..C30.
Each replacement instruction has a graphical source encoding at its actual
address; C31..C32, which fix the loader recurrence, are not changed. An
independent 15-trit crazy/rotate oracle evaluates the exact observed VM
memory and registers, overlays prospective data writes, and checks whether
the proposed `i` target can undergo the required post-jump encryption. The
search's **necessary** success predicate is a valid graphical target on
*all 256 successful byte inputs* plus a separate valid EOF target; only
after that could distinct destinations establish a two-arm branch.

None of the 85 candidates even has a graphical target on all 256 bytes.
Consequently zero candidates meet the stronger distinct-two-arm predicate.
A separate source-loaded VM replay checks five representative continuation
shapes (empty, `j`, `jo`, `joo`, `p*j`) across EOF, NUL, `01`, `1f` and `ff`:
25 actual N15 traces agree on whether the proposed `i` is admitted and,
when successful, on its exact next code pointer. This independently caught
and corrected the scalar model's initially missing automatic D increment
for `j` before the full 257-class test was accepted.

This is a finite negative result under the frozen source, candidate positions,
loader tails and operation grammar, **not** evidence that arbitrary EOF
control, longer chains, relocated data, a different graphical source, or the
full C23 loop is impossible. A credible next linker experiment must first
supply a bounded, verified data-pointer reset or physically relocate this
branch with live source-C32 state. The already executable 132-cell signed
EOF branch uses a different control scaffold and is not contradicted by
this local rejection.

### Why raw input cannot directly form the first C32 low word (2026-11-21)

`tests/compiler_c32_source_loaded_eof.rs` now exercises two real source-
loaded, five-step N15 guests with reached `/; j; (p|*); p; v`. Each
variant executes on byte `0x02` and on true EOF, reading exactly the two
loader-derived adjacent data words, writing both, and encrypting its reached
instructions. An independent scalar ternary oracle checks the exact guest
arithmetic, not just final values. The source is graphical and independently
loader-initialized; these are not host-supplied data words.

The raw signed input accumulators `2` and `14,348,906` both have units trit
`2`. The first `p` therefore produces the same units trit with any fixed
data-operand units trit; the first `*` is wholly input-independent. But the
required source-C32 low words are respectively `2` (units trit `2`) and
`4,644,102` (units trit `0`). Hence **neither fixed first write can be the
complete low-word store for both input cases**. A second adjacent `p`
cannot repair the already-stored low cell. This is a necessary-condition
counterexample for this exact direct adjacency grammar. Guest-dependent
routing, earlier rotations, different data flow, or revisiting the low cell
remain open; neither a full C23 lowering failure nor an impossibility for
arbitrary Malbolge code is claimed. The whole checksum remains unpublished.

### Physical input-store causal precondition (2026-11-21)

`verify_source_input_site_stored_results` now also tracks a bounded,
conservative data/control influence shadow along the **real** N15 VM trace.
Each `/` introduces an independently identified input event. Reached `p`
propagates input influence from the accumulator and actual data word; `*`
replaces the accumulator from the data word without inheriting unrelated
previous accumulator influence. Actual `j`/`i`, data-pointer locations,
mutable code fetches and encrypted code may propagate possible influence.
The checker refuses a complete, numerically correct source SSA store when
**none** of its physical writes can depend on its **own** observed input.
This has its own `InputResultUnrelatedToInput` diagnostic, distinct from
missing and incorrect C32 words.

The low C32 word may be input-dependent while the high word is a legitimate
fixed constant, so only one source-frame cell needs influence; every word
still requires an actual exact physical data instruction and correct value.
A synthetic matching constant pair is now rejected. Three graphical
`/; j; (p|*); (p|*); v` guests were independently executed on byte `02`,
`ff` and true EOF: direct `p` retains input influence, a fresh `*`
forgets it. An existing 91-cell guest also proves physical writes at
C43 depend on read C39 and at C51 on **both** reads C39/C47. The shadow
only establishes a **necessary possible-dependence condition**: it can
conservatively retain influence across feasible but unproven target
branches, cannot certify algebraic sensitivity of an individual trit,
and does not prove source operation mapping, branch correctness, SSA use,
phi arithmetic or an executable checksum. The complete C23 source still
refuses publication at the physical linker.

### Why the Iy converter cannot directly store signed EOF with more p

A second source-locked test exercises the **real 91-cell Iy converter** on
successful second byte `0x02` and on actual second-read EOF. C78 writes
M96=`2` or `62,207` respectively, confirmed by the normative 82-step
trace, while the canonical C32 signed results would be `[2, 0]` and
`[4,644,102, 299]`. The two *physical converter words* have the same
units trit `2`, yet both desired C32 result words differ in their units
trit between byte `0x02` and EOF. Crazy `p` is trit-local for every one
of the three possible data-operand units trits. Inductively, no finite
sequence of **constant-operand crazy operations alone** can transform
these two cases into either required C32 result word. The next physical
linker needs guest-controlled EOF-specific routing, trit-moving rotation,
or an independently valid alternative conversion; adding more unchanged
constant crazy folds cannot solve this input-store obligation. This is a
restricted obstruction, not an impossibility proof for Malbolge or C23.
See `tests/compiler_c23_store_nonlocality.rs`.

### One-rotation C32 signed-store locality limit (2026-11-21)

A separate independent 257-class finite ternary oracle now checks all
15 whole-word rotations of the actual Iy converter's output domain:
successful bytes `0..255` remain unchanged, while true EOF is the
**different** encoded word `62,207`. Each exact signed C32 destination
is either `[byte, 0]` or `[4,644,102, 299]` at EOF. A fixed-operand
`p` chain operates separately on ternary coordinates; one `*` can only
permute those coordinates. Therefore, with **at most one rotation**
and any number of fixed crazy operations, each result digit can only
be a unary function of one source digit. The checker allows arbitrary
unary trit maps (more than Malbolge supports), then looks for pairs
of successful bytes/EOF with the same source digit but contradictory
target digits.

No rotation count 0..14 gives a consistent unary map for **either**
complete C32 cell. Even the best rotation leaves at least ten
conflicting low-word trits, or one conflicting high-word trit. The
proof rules out this narrow accumulator-data transform grammar, **not**
real guest programs with two or more rotations, variable operands,
guest branch selection, or other nonlocal state movement. The physical
checksum remains unlinked; see
`tests/compiler_c23_store_nonlocality.rs`.

### Physical C23 input-result word writes (2026-11-20)

The opt-in `verify_source_input_site_stored_results` strengthens the
actual-N15 source input/return check with a second, deterministic VM replay.
It observes real `p` or `*` data-word write attempts at the exact
source-allocated SSA destination, tracks actual profile-memory deltas and
requires the complete C result to be present together after those writes.
A correct loader-initialized word alone is not a write. Reaching the same
source read again before the preceding value was ever materialized refuses.

For signed C23 `getchar`, both 15-trit result cells must be written.
A successful `0xff` is `[255, 0]`; true EOF is the distinct C32
`-1` representation `[4,644,102, 299]`. An optional byte-only input
requires one cell and rejects EOF. Accepted observations preserve exact
guest trace steps and word addresses, not a host-synthesized C store.
Missing data writes and incorrect stored values have distinct errors.

The unchanged source checksum still passes its independent native C23
checks and the existing C53/C101 conditional-input witness still reaches
source-valid EOF return paths. It now **also refuses** the new physical
frame-write gate on empty, NUL and `ff` input: the candidate reads but
does not write either canonical C32 input result to its allocated frame.
Independent state-accounting tests reject loader-only equality, partial
low-word writes, wrong EOF high words and premature acceptance. A store
snapshot is only a necessary condition: future code may overwrite it,
and this gate does not prove source-level dataflow, all intermediate C
operations, phi transfer, guest branch edges or output correctness. No C
artifact has been published and P2 remains open. See
`tests/compiler/source_input_store.rs` and
`tests/compiler_source_input_site_guest.rs`.

### Source-known checksum output parity gate (2026-11-20)

The opt-in `verify_source_input_site_output_compatible` first requires real
N15 execution with authenticated physical read sites and a complete possible
source-CFG return. It then walks the exact original typed checksum CFG to
compare the guest's actual *ordered input/output event sequence* and
complete output bytes with values
established from source-known C32 unsigned wrapping add/subtract, bitwise
operations, signed EOF comparison, casts and parallel edge phis. Unknown
output scalars and unsupported arithmetic cannot certify any guessed byte;
a finite search-budget refusal remains distinct from a source mismatch.
This checks source I/O **effect order**, but not elapsed instruction timings,
physical C32 memory writes, opcode semantics for source arithmetic, phi
copies or branch equivalence.

The original seven-block checksum source produces the independently calculated
one-byte checksum on empty, NUL, `ff` and two multibyte binary streams.
Forged one-byte results, missing/extra output, unsupported multiplication,
and full-width unsigned-add overflow are covered by source-CFG tests. The
132-cell C53/C101 guarded physical guest passes necessary read and return
checks for first EOF and byte-then-EOF, but is correctly rejected by this
output gate: it emits a fixed EOF/byte marker instead of the checksum. Its
real VM I/O stream is `read C53 → marker output → read C101` after a
successful first byte, whereas the C checksum must output *after* the
last read returns EOF. The previously unchecked early emission is now an
independent source/guest chronology mismatch.
Two successful input bytes fail at source return first, as the C loop would
require another read. Nothing is published from this bounded verifier.

### Disjoint guarded-input anchors and source-return check (2026-11-20)

The existing 132-cell physical *first*-EOF branch actually reads at C53,
then reaches the second C101 input only if the first read was a successful
byte. Unlike the second-read EOF classifier at C53/C63, these two read
addresses are far enough apart for the unchanged C23 checksum's source-
locked minimum block intervals to be disjoint. The independent placement
planner accepts both authenticated input anchors without reducing any
full-width operand, C23 normalization or phi/control reservation.

The normative N15 VM completes in 119 steps for first EOF and 175 after a
successful first byte. Four real input streams prove first EOF skips C101,
and distinguish NUL, `0xff`, and a successful second byte from true EOF.
The source-CFG input-prefix verifier admits exactly these reached reads.

The new opt-in `verify_source_input_site_return_compatible` additionally
requires one *possible* source CFG return with exactly the observed read
events, even when both physical source anchors executed. First EOF and a
successful byte followed by true EOF pass; two successful bytes, including
second `0xff`, refuse because the original C loop must read again. A
174-step ceiling refuses a 175-step physical path. This is a stronger
necessary condition for a future complete source-linked guest, not proof
that the physical guest executes the source branches or writes source data.
The classifier emits its marker rather than the C checksum, so there is no
source-C guest parity or published checksum artifact. See
`tests/compiler_source_input_site_guest.rs`.

### Real EOF-branch guest versus disjoint source block placements (2026-11-20)

The independent, existing 132-cell physical second-input EOF classifier
executes real `/` operations at C53 and C63. Four bounded normative N15
runs confirm both input effects and the 119-step true-EOF branch versus
the 175-step successful-byte branch. However its two physical reads cannot
be directly assigned to the original checksum's disjoint minimum code
blocks: canonical C23 block 0 reserves 16 cells, so an anchored C53 input
forces an interval overlapping the later C63 loop-input block. The canonical
source-locked placement planner refuses `InvalidCodePlacement`; input-site
verification accordingly refuses `InvalidSourcePlacement` for every path.

The real physical EOF branch is valuable input/control evidence, but not a
validly linked instance of this specific C CFG. A future linker must relocate
those physical input sites or realize complete source operation and control
code in disjoint intervals without relaxing the frame/code integrity check.
No checksum output or whole-program target artifact is claimed. The
regression is `physical_second_eof_branch_refuses_overlapping_checksum_blocks`
in `tests/compiler_source_input_site_guest.rs`. P2 remains open.

### Source-verified early EOF without a second physical read (2026-11-20)

The source input-site prefix verifier now distinguishes an unexecuted input
anchor from a missing **mandatory** source read. When an anchored read never
executes, it searches the original canonical C23 CFG for a complete source
return after **exactly** the observed physical input events, without any
further source input. The 16,384-state bound still returns an explicit
incomplete-search error on exhaustion; unknown scalar computations may keep
both CFG arms feasible rather than supply an invented guest predicate. This
source-path condition remains necessary but not sufficient for translation.

A red-first real N15 91-cell probe replaces the converter's second C66 `/`
with a graphical `o` while preserving its original first C37 `/`. The
physical input-only trace on empty stdin reads true EOF exactly once and
halts within 82 steps. This now passes the source input path gate because
the unchanged checksum must return after the first C23 EOF. The same guest
probe with a successful first byte rejects `UnreachedSourceInput`, because
source control then requires the second read. Six source-CFG cases also
check true first EOF, a non-EOF first read, an EOF after the loop read,
skipped earlier input, and a one-state search exhaustion. This does **not**
verify guest stdout, C23 EOF conversion, physical branching, mutable locals,
checksum arithmetic, output or the full EOF loop. The real source-C guest
compiler remains fail-closed and P2 open.

### Source-CFG-bound physical loop input revisits (2026-11-20)

The original complete seven-block C23 mutable EOF checksum still passes its
independent native `-O0`/`-O2` controls and refuses guest publication. A
red-first source input-site regression caught the verifier rejecting repeated
physical reads at the *same* code address before checking the authenticated
source CFG. A 117-cell normative N15 guest now physically reads at C3, then
reuses C47 twice after the intervening inert visit and two code encryptions.
The 60-step trace binds C3 to the original source's first `getchar`, and both
C47 inputs to its loop `getchar`. Four finite binary vectors check actual
input effects, precise trace indices, byte consumption, true EOF and `0xff`.
Two early-EOF paths refuse via source-known C23 control, and a 59-step guest
budget refuses. The source-input verifier retains the one-anchor-per-typed-
input contract and validates the *entire observed prefix* through the original
CFG (including loop backedges), instead of enforcing a false global ordinal
monotonicity or prohibiting repeated physical input cells. A separate
same-block two-input loop witness proves `0,1,0,1` source ordering is legal
but `0,0`, `1,0` and `0,1,1` are impossible without the relevant CFG edges.

This remains a **finite unconditional guest** with three raw input events,
no branch or output. The verified source-CFG prefix is only a necessary input
path, not physical C23 EOF normalization, dynamic guest conditionals, C32
stores, arithmetic, phi transfer, whole-program guest output or a repeatable
EOF-controlled loop. The checksum remains unlinked and P2 open. See
`tests/compiler_source_input_site_guest.rs` and
`tests/compiler/source_input_cfg_order.rs`.

### Physical two-read same-site N15 guest (2026-11-20)

A new 117-cell, loadable guest witness physically re-enters **the same C47
input code address** three times. Its evolving XLAT2 values are 70 (`/`),
74 (`P`, inert), and 70 (`/`) again; hence it performs **two separate real
input reads from one source cell**. Four real `i` transfers (at C49 three
times and C75 once) use evolving data words to reach C47, C73, C47 and C116.
The intermediate C73/C74 `j` data resets address M91=65, M66=109 and
M110=46; the earlier C48 reset reads M48=86 and the final C49 transfer
reads M113=115. Source-loaded operands remain loader-valid graphical bytes,
not invented memory contents. Current and historical normative N15 VMs both
halt after exactly 60 steps on five streams: empty, NUL, `80`, `ff`, and
`01 02 03`. They perform the expected two input events (including EOF
attempts, preserving the third unread byte), exact C/D paths, code-cell
self-encryption, and no output. This overcomes the naive one-visit input
obstruction for a **fixed two-read finite guest**. It is still unconditional:
there is no EOF-conditional exit, C23 signed-local storage, source-C link,
third successful read or mutable checksum. See
`tests/compiler_same_site_two_read_guest.rs`.

### Physical same-site input revisit obstruction (2026-11-20)

A separate all-94-phase XLAT1/XLAT2 enumeration now proves a narrow but
important guest loop constraint: a graphical source cell initially decoding
as `/` **cannot decode as `/` on the next execution of that same address**
after its automatic encryption, assuming no intervening guest data write to
that code cell. After a second encryption, only phases 43 and 47 would again
decode as `/`, and both have a harmless intermediate no-op decode (`$` and
`P`, respectively). The real current/historical profile VMs execute one
physical `/` at C47 on empty, NUL and `ff` streams, prove its XLAT2 write
(70 to 74), and halt after 49 steps. The two candidate three-visit patterns
are **only opcode recurrences**, not executable backedges, input loops, C
normalization or source-compiler linkage. A valid dynamic EOF checksum loop
must place and verify its complete return path, all intervening instructions,
and code/data pointer state, or choose a different physically justified
implementation. See `tests/compiler_input_revisit_phase.rs`.

### Source-known cast and comparison branch feasibility (2026-11-20)

The source-input prefix verifier now preserves exactly known C23 `getchar`
values through 32-bit signed/unsigned bitcasts, exact U8 truncation, Boolean
conversions, equality, signed and unsigned less-than checks, plus total bitwise
AND/OR/XOR operations. It distinguishes raw N15 EOF from C23 `-1` before
truncation and correctly maps that C23 `-1` to unsigned byte `255` afterward.
Red-first source-CFG tests reject input effects on the wrong successors for
zero, `0x7f`, `0x80`, `0xff`, and true EOF, including the signed-versus-
unsigned ordering difference. Unknown or unimplemented arithmetic remains
unknown. These tests constrain only possible source paths after independently
observed input; they do not validate guest-side casts, comparisons, branches,
mutable variables, emitted checksum bytes, or a source-C artifact. The original
complete mutable EOF checksum still refuses guest publication.

### Source-CFG prefix reachability for physical input sites (2026-11-20)

The bounded source-input trace checker now checks more than each basic block's
local ordinal order. It independently re-lowers the canonical typed wire to
its authenticated symbolic CFG and searches for a path from function entry
whose input operations form the exact observed physical read prefix. The path
cannot skip another source input, enter a block before its mandatory prior
read, or move between blocks without a source CFG edge. The unchanged checksum
accepts the block-0 first read followed by block-5's loop read and rejects the
reverse order or a block-5-only prefix. Both signed reads remain anchored to
real N15 `/` transitions in the separate 91-cell converter. A malformed typed
source or a nonexistent source input ordinal also refuses.

The checker now also propagates **known source scalar values** across exact
constant materializations, input results, selected comparisons and bitwise
AND, plus simultaneous phi assignments. A known Boolean guard constrains
its source CFG successor; an unknown guard retains both possibilities. In
particular, true first-read EOF must exit the source checksum before the
second read, whereas byte `0xff` is a successful read and may continue.
Normative N15 input-only runs still physically attempt both reads even on
empty stdin, so this additional checker correctly **refuses** those paths.
A finite 16,384-state ceiling bounds the path search; exhausting that
ceiling returns a distinct incomplete-search diagnostic rather than a false
claim that no source path exists. Neither result can become an unbounded
source-language equivalence claim.

This is source-path feasibility, **not guest control verification**. Neither
physical guest branch destinations nor runtime C23 EOF normalization,
scalar stores, mutable checksum arithmetic, parallel phi copies or the
repeatable backedge are proved. Unmodeled source calculations retain
unknown values rather than being guessed. The complete checksum still
refuses guest publication.

### Real C same-block signed input reservations (2026-11-20)

The source-locked physical input-site planner now admits **distinct** input
operations within the **same** source basic block when their independent
anchors imply exactly the same code interval. Previously its block map
rejected the second anchor unconditionally. A typed U8 two-read block
requires two physical input addresses separated by its first input/store
minimum; duplicate ordinal, conflicting interval, non-input ordinal and
short source proposals still reject. Reordered consistent anchors yield the
same deterministic placement.

A separate source-authenticated real C23 function, `void emit(void)` with
two discarded `getchar()` calls in one basic block, now provides an N15
physical input-only demonstration: the canonical typed instructions each
require a two-word signed `int` destination, while seven graphical guest
instructions execute `/` at C0 and C3 and halt at C6. Five finite real VM
streams check raw byte/EOF values, exact two input events, consumed length
and no output, including an unread third byte. The physical no-ops do
**not** write the required C32 result cells, and there is no code-generation
handoff or source-C artifact publication. This closes a concrete necessary
same-block placement refusal, not source state storage or the P2 checksum.

The bounded physical input-site verifier also rejects a trace that reads
source operations in reverse order **within the same function and basic
block**. Its new source-local ordinal check does not infer the order of
different blocks, which still requires real CFG linkage, and keeps block
identity function-qualified. A focused negative regression reverses two
observation ordinals and rejects them while accepting independent block
and function sequences. It does not demonstrate a compiled conditional.

### Source-typed input sites checked in the real guest (2026-11-20)

The original seven-block mutable C23 checksum still has no executable
source-C guest artifact. A separate input-only verification stage now
rederives both `getchar` operation sites from the canonical source-locked
typed CFG and runs a candidate 91-cell `Iy` converter in the normative
N15 VM. It checks actual decoded `/` instructions at C37/C66, their raw
accumulator values, full-width typed destination identities, signed EOF
obligations, execution order and physical step indices. Six finite streams
exercise zero, one and two consumed bytes, NUL, the high-bit boundary,
`0xff`, true EOF and an unread suffix. Exact 82-step halts are retained.

The verifier refuses absent or forged input-site bindings, an 81-step
incomplete execution, a corrupted canonical typed source, and a physically
executed *third* `/` at the unassigned C80, and a missing real
`/` at C66. This is positive evidence
that the proposed source input addresses coincide with real guest input
transitions, **not** evidence that the converter implements source-C block
entry, C32 result stores, signed EOF normalization, arithmetic, branches,
phi transfers or the EOF checksum loop. In particular the converter output
is not claimed to match the original checksum output. P2 remains open.

### Frozen C23 loader-tail and bootstrap obstruction (2026-11-20)

The original seven-block C23 mutable EOF checksum was retried through its
native `-O0`/`-O2` controls and source-locked compiler entry. It still
refuses target publication at the unresolved physical CFG stage, without
creating a guest artifact. The separately executable 91-cell two-input
C23 converter was used to test a potential first-read storage repair.

An independent 15-trit finite oracle enumerates all **8,836** ASCII
source-tail pairs at C89/C90, expanding the loader through M122. Exactly
four tails preserve M96=121, M98=M122=157, the nine M95 rotations, and
full signed-C23 output parity for all 256 second-input bytes and EOF:
`Hy`, `Iy`, `Ky`, and `Ly`. All four yield the same initial M97 word
7,174,404 and only **37 distinct first-input encodings** across those
257 classes. The same four tails initialize M102=121, which is
injective across 257 classes. The enumeration is a necessary **fixed
pointer/operand grammar** check, not a claim that all four candidates
pass the graphical source loader or that no other linker geometry works.

The tempting relocation of the first input `p` from C38/M97 toward
M102 via C38..C42 no-ops fails in the *real* normative guest. C41's
original graphical byte 93 is also data read by the initial C1 `j`:
C1 must advance from M41 to M94. Replacing C41 by graphical `o`
changes M41 to 121, so C1 jumps to M122 instead. A 2-byte VM run of
the modified source still executes both real `/` instructions, but
its C43 `p` reaches M7,174,412 rather than M102 and emits `0x49`
instead of the original correct converted `0x02`. Both source traces
and independent oracle are pinned in a bounded regression. A further
16-case exact pointer simulation begins from the normative post-C37 VM
memory, holds C41=93 fixed, and enumerates all `o`/`j` choices at
C38/C39/C40/C42, including code encryption after each instruction.
Those paths reach only eight distinct C43 pointer addresses
(37, 38, 67, 68, 159, 7,174,370, 7,174,405 and 7,174,406), never M102.
This is another **restricted early-operation bound**, not a general
inability to reach M102 after redesigned code or data initialization.

These results reject only a direct fixed-layout seed swap and this
specific naive relocation. They do not implement C32 locals, signed EOF
normalization for the source checksum, arithmetic/XOR, phi transfer,
branch/backedge linkage, or a guest-executed whole C program. P2 stays open.

### Source-bound C23 signed input code-site obligation (2026-11-20)

The unchanged complete seven-block mutable C23 checksum still passes all
five native `-O0`/`-O2` binary controls and fails closed before physical
publication. Its **addressed code-placement stage** now distinguishes an
unsigned byte read from a signed C23 `getchar`. Each of the two canonical
`getchar` operations binds its exact two-word I32 destination and the
required N15 raw-EOF-to-C23 normalization contract: raw N15 EOF is
14,348,906, whereas C23 `-1` must occupy guest cells `[4,644,102, 299]`.
The destination write sites stay distinct from the raw `/` instruction,
and the full-width result cannot be silently treated as a U8 read. A
red-first source-locked regression verifies both effects in the original
checksum's proposed seven-block layout; all 197 frontend-adapter library
tests pass.

This is a **physical linker obligation**, not a VM-executed normalization
routine or proof that the proposed code cells contain Malbolge opcodes.
The following address-binding guards additionally reject forged input
SSA identities, widths, signedness, extra input operands, and output sites
that read a different source SSA value or a multiword non-U8 value. A
red-first test exercises both input kinds and the checksum-style final
byte output. Code-site literal stores additionally recheck the original
source integer bits using the same canonical N15 word encoder as typed
placement; forged literal values, result identities, out-of-memory words,
and zero-width targets all fail closed. Computed operation sites also
recheck each source SSA operand in original order, result identity, full
scalar width and current-profile address range. Only source integer
constants may supply literal writes: a forged same-address literal for
an unsigned XOR, comparison or narrowing cast cannot stand in for guest
arithmetic. Red-first adversarial tests cover these three operation kinds,
including reordered reads and truncated U32 operands. The addressed
code-site handoff now also retains explicit **unexecuted** typed binary,
comparison and cast operations with original operation kind and ordered,
full-width source/result cells. The original seven-block checksum binds all
five bitwise/arithmetic, both Boolean comparison and its integer-conversion
obligations; no host arithmetic has selected a guest value or branch. These
are necessary code-linker invariants, not an executable. The two input
conversions, unsigned arithmetic/XOR, conditional branches, parallel phi
copies and live EOF backedge still lack a unified verified executable
linker. No checksum guest artifact is emitted; P2 remains open.

### First signed C23 read cannot be erased by one opcode (2026-11-20)

The original seven-block mutable checksum was rerun unchanged through
native C23 `-O0`/`-O2` and its source-authenticated compiler boundary.
Five binary controls still refuse any guest artifact at physical
operation, phi, branch and EOF-backedge linkage. Separately, the
already-executed 91-cell `Iy` C23 signed converter was tested as a
possible *single*-read `putchar(getchar())` building block.

The existing converter uses a first `/` at C37 and converts the second
`/` at C66 with two real `p` operations and a C79 byte output.
Although the first value never appears in the output, C37's initial
source byte 80 participates in early physical pointer routing, and its
post-execution encryption to 66 is reused by later `j` resets. All
**seven** alternative admitted graphical opcodes at the *same* C37
cell (`o`, `i`, `j`, `p`, `*`, `<`, `v`) were exhaustively checked
against the actual N15 VM on a successful input byte `0x02` and true
EOF. The only three replacements that still reach the C66 read and
C79 output (`o`, `j`, `p`) emit respectively 1, 0, 1 for input 2,
and 89, 173, 89 for EOF, versus required C23 2 and 255. The
remaining four do not complete the required guest input/output path.
The unmodified two-read source still emits its correct second byte
in 81 physical steps, and the new focused real-VM regression passes.

This is a **one-cell replacement bound**, not proof that a
single-read C23 converter is impossible. It identifies the first
instruction/loader coupling a real general physical linker must
relocate or replace. It adds no source-C acceptance mode, no checksum
arithmetic, no parallel phi copy, and no dynamic EOF backedge. P2
remains open and the original checksum publishes no guest artifact.

### First signed read cannot be saved by one C38/M97 crazy (2026-11-20)

The 91-cell signed-C23 converter's first `/` at C37 leaves D pointing
at M97=7,174,404. A physical `p` at the immediately following C38 is
therefore a plausible one-cell attempt to save the first signed input
before the nine loader rotations overwrite the accumulator. It is **not
lossless**: the independent 15-trit `crazy(M97, raw)` table has only 37
distinct results for the 256 successful bytes plus true raw N15 EOF.
Bytes `0x01` and `0x02` already collide.

An exact graphical C38 `p` substitution is admitted by the real VM.
Both independent input paths execute the original signed C37 `/`, then
the same physical C38 `p` at D=M97, and reach the 39-step bounded
checkpoint with **identical stored M97 words** despite consuming
different bytes. The regression checks the read events, source loader
seed, data reads, exact `p` deltas and independent ternary result. No
later computation can reconstruct which of these bytes was read from
that one saved word. This rules out **only this single-p save using
M97's existing seed**, not a relocated lossless store, a modified seed,
a different data address or a general single-read C23 converter. For
comparison, the same exact `Iy` loader initializes M102=121, and
`crazy(121, raw)` is **injective across all 257 input classes**. A
future verified pointer relocation would have to reach that distinct
cell without losing the original accumulator or corrupting subsequent
control. No C38-to-M102 guest path has been executed or admitted.
The P2 checksum remains unlinked and produces no guest artifact.

### Early signed-read relocation with real `p`/`*` (2026-11-23)

The unchanged 91-cell `Iy` signed-C23 converter was reexamined as a
possible one-read building block for the complete mutable checksum.
Its first genuine `/` at C37 leaves D=M97. M102=121 would make a
single `p` lossless across all 256 bytes plus EOF, whereas M97 loses
input identity. A proposed five-instruction route C38..C42 must
reach D=M102 before such a C43 `p` could use it.

The prior fixed-bootstrap, four-choice-site `o`/`j` experiment has now
been extended to **256** positional graphical choices: each of C38,
C39, C40 and C42 may be `o`, `j`, `*` or `p`, while C41 retains its
bootstrap-critical original `j` source byte. An independent bounded
five-step interpreter uses the actual normative post-C37 N15 memory,
reached data words, accumulator, data writes, source-cell encryption
and positional opcode decoding. For the necessary **NUL input** case,
all 256 routes produce exactly eight terminal D values:
`37, 38, 67, 68, 159, 7174370, 7174405, 7174406`. None is 102.
The control separately verifies the original 38-step input trace had
no data read from the four edited code cells before C37. Four mixed
`p`/`*`/`j`/`o` choices were also run as genuine source-loaded 43-step
N15 guests, with matching post-C42 D and A.

This rejects a **C43 lossless-M102 save only in the frozen five-cell
and four-opcode grammar**, even if arithmetic writes are admitted.
It does not rule out a modified bootstrap, different code/data layout,
longer pointer route, different lossless operand or completed C23
single-read converter. No checksum arithmetic, branch/phi linkage or
EOF loop is delivered; the original full C23 checksum still refuses
guest artifact publication. Regression:
`tests/compiler_c23_first_read_storage_route.rs`.

### Exact third signed-word recovery after guest storage (2026-11-20)

The exact same 91-cell three-input N15 source admits a second physical
continuation with an **invertible** stored signed word, including raw
EOF. M103 and the untouched loader M109 both begin as 7,174,453, the
15-trit all-ones word. For each trit, Malbolge's `crazy(1, x)` exchanges
0 and 1 and fixes 2; applying it twice recovers the original trit.
The source's C59 third `/` and C62/M103 `p` first save an injected
encoding. Five reached inert instructions advance D to virgin M109,
where C68 `p` folds the saved encoding with the all-ones seed and
physically writes the **exact original N15 guest input word**. C69
outputs its low byte and C70 halts after 71 steps. The earlier two
signed saves at M95/M97 and first-two-word C57 `crazy` fold remain
unmodified. The roundtrip continuation is separate from the 72-step
three-way fold, not a claim that both outputs are emitted together.

An independent 257-value trit truth table proves exact inversion for
all 256 possible input bytes and true raw N15 EOF. Ten complete
normative VM paths compare the recovered M109 word, distinct M103
encoding, first-two input state, five reached physical `p` writes,
three read events, emitted low byte, consumed input and 71-step halt.
A second independent compiler-path verifier now accepts six exact
source-identical 71-step complete witnesses, checking independently
constructed loader-rotation and `crazy` writes, three signed read
attempts, final raw M109 store, and output. Its adversarial controls
distinguish an **invalid N15 out-of-range EOF-forge** from an in-range
but wrong physical store; they also reject a forged output byte.
This is a real lossless guest decoder for the profile's raw input
word, **not** C23 `int` normalization, an EOF branch, source-bound
assignment, a dynamic checksum loop or checksum guest-output parity.
P2 remains open.

### Lossless third signed input and true three-word crazy fold (2026-11-20)

A stronger 91-cell N15 continuation now saves three independently read
signed inputs before a **real third-input-dependent cross-word fold**.
After C43/M95 and C53/M97 preserve the first two 257-class encodings,
C57/M95 folds those two full words. C58 resets D to M73, C59 performs
an independent third `/`, and C60 follows a new virgin C74=101 pointer.
C61 advances to M103, where source-mandated C62=94 executes `p`
against the untouched 7,174,453 loader seed. An independent ternary
truth table proves this third M103 encoding distinguishes **all 256
bytes plus true EOF**; notably 1 and 2 no longer alias.

The final arithmetic linkage must follow *post-encryption* control.
After C62 encrypts its own 94 source constant to 57, C63..C66 jump
through M104=72, M73=61, encrypted M62=57 and encrypted M58=79,
landing at D80. C67 advances to virgin M81=94 and C68 `j` restores
D95. The reached C69 `p` then calculates the full-width
`crazy(crazy(saved_first, saved_second), saved_third)` in M95;
M97 and M103 still retain the independent second/third encoded words.
C70 outputs its low byte, and C71 halts.

Ten fixed complete normative VM streams (including empty, truncated,
NUL, high bytes, multiple third bytes and an unread suffix) agree with
an independently implemented 15-trit `crazy` oracle. Every case checks
three physical read sites, all five physical `p` writes, seven jump
sites, the two deliberate `o` increments, untouched pointer constants,
retained data words, single output and **exact 72-step halt**. This is
real guest ternary arithmetic across three signed input encodings,
**not** C23 unsigned add/XOR, decoded C locals, conditional EOF, a
source-bound compiler path or the original checksum. P2 remains open.

### Third signed input after a real cross-word fold (2026-11-20)

A 91-cell N15 candidate extends the verified independent dual-storage
layout. C39 and C47 read signed guest values, C43/M95 and C53/M97 retain
them with lossless byte-plus-EOF encoding, and C57/M95 physically computes
`crazy(first_saved, second_saved)`. Three loader-derived jumps at
C58..C60 restore D from M96=72 through M73=61 and M62=94 to M95.
C61 then reads a **third independent signed input**; the unchanged
source byte 94 at C62 decodes as `p`, writes `crazy(72, third)` to M96,
and C63 emits the resulting encoded low byte before C64 halts.

Eight finite normative VM paths check true EOF, NUL, high bytes, trailing
unread input, exact read sites, all four physical `p` writes, preserved
first-two cross-fold state M95 and untouched saved second word M97, single
output and 65-step halt. An additional independent 15-trit oracle groups
all 256 possible third-input bytes into exactly **36 encoded classes**:
third inputs 1 and 2 collide, while the true N15 EOF sentinel is outside
all 36 byte-derived classes. Thirty-six representative bytes and the
separate true EOF case each execute a complete 65-step normative VM path
with exact read locations, three saved state cells, output and bounded
input consumption. This
is three genuine guest reads and a later distinct state update, **not**
full-width third-byte storage, C23 arithmetic, conditional input control,
phi copies or the original checksum EOF loop. P2 remains open.

### Fixed guarded-third-output continuation: one-cell bound (2026-11-20)

The source-valid 132-cell second-EOF branch already executes a conditional
third signed guest read at C101. A previously rejected four-cell tail
changes C104 to `o`, C112 to `p` and reserves C115/C116 for output/halt;
its successful-second-byte arm reaches an invalid second-pass C114 `i`.
A new finite enumeration examines every source-loadable graphical opcode
at each C102..C114, altering **exactly one** cell after those four edits.
There are 104 candidates. The same 15-trit loader expansion applies to
all candidates because none changes the two tail seed cells.

For the fixed stream `03 04 05`, all 104 candidates execute in the
normative VM under a 220-step ceiling. Only C104=`123` and C114=`97`
halt after consuming three bytes, but they emit `03 9a` and `03 05`,
respectively, rather than `03 9a 05`. No candidate supplies the exact
C53/C63/C101 read sites, third-byte output, bounded halt and a correctly
terminated true-second-EOF arm together. This rejects the **specified
one-cell repair grammar only**; multiple changes, code relocation,
source-C signed conversion, and the full mutable EOF checksum are not
solved. The independent original checksum still refuses to publish a
guest artifact, as required while its physical CFG remains unlinked.

### Cross-word guest arithmetic after two retained inputs (2026-11-20)

The earlier 91-cell dual-storage geometry now performs a real binary
Malbolge `p` operation on both independently read and saved values.
After C43 stores the first signed input at M95 and C53 stores the
second at M97, three physical jumps at C54..C56 follow loader words
M98=72, M73=61 and M62=94 to return to M95. C57 computes
`crazy(saved_first, saved_second)` in guest memory; C58 emits the
result's low byte and C59 halts at 60 normative VM steps. M97 retains
the separately encoded second input. The first saved value is an
actual memory operand, not a host-provided argument or output lookup.

An independent 15-trit truth table proves the two pre-fold storage
seeds separately represent all 256 byte classes plus EOF without
aliases. A predeclared 29-stream normative guest witness includes
empty input, one-sided EOF, NUL, high bytes, sign boundaries, and an
unread suffix. Every trace checks C39/C47 reads, three `p` operations,
pointer restoration, exact memory words, output and termination. The
test observes reached `p` instructions even when a fold leaves memory
unchanged. The separate bounded compiler-path verifier now also accepts
six independently constructed complete 60-step traces for this exact
same physical source and profile, checking all nine seed rotations,
all three physical crazy writes, two signed reads, output and memory
mutations. Its explicit negative controls reject a forged final
arithmetic-result word and a forged output byte. This establishes a
source-identical reusable *physical-path witness*, not source-C linkage.
The initial exhaustive 515-stream VM attempt exceeded its 100-second
subprocess budget and is not claimed as a pass.

This demonstrates guest **cross-word** arithmetic that depends on two
previously saved signed inputs. It does not decode C23 integers, supply
C add/XOR, source-variable SSA, a runtime EOF branch, or the checksum
backedge. The original full mutable source still refuses publication.

### Two independently lossless signed input words (2026-11-20)

A second 91-cell physical layout uses the graphical `IH` loader tail to
prepare **two separate guest storage cells**. M95 starts at 7,174,489;
its nine genuine N15 rotations yield seed 7,200,697. Independent loader
M97 starts at 7,174,453. Both seeds have their lowest six trits equal
to one. The independent ternary oracle proves each seed maps every one
of 256 bytes injectively, with a separately encoded signed EOF word.

C39 reads and C43 physically folds the first signed value into M95.
C47 reads the second signed value, C48..C50 reset D, and C51/C52 advance
to the untouched M97, which C53 physically folds with that second value.
C54 emits the *encoded* second low byte and C55 halts in 56 steps.
The first cell survives unchanged, so two independent byte-or-EOF inputs
occupy two distinct readable guest words, rather than one lossy fold.

The 268 bounded real-VM traces cover all 256 second input bytes with first
byte 42, true EOF, ten truncated-first-value cases, and an unread suffix.
Each compares both memory words to the independent trit oracle, verifies
two actual `/` sites, distinct `p` stores, single encoded output, and
exact halt. This proves lossless *encoding of each signed input*, not
C23 signed decoding, source-local storage, checksum add/xor, phi copies,
EOF branch, or dynamic loop. The original P2 checksum remains unlinked.

### Lossless first signed word across a second guest input (2026-11-20)

An independent positive N15 physical layout avoids the frozen 132-cell EOF
skeleton entirely. The existing 91-cell loader with tail `,H` writes nine
real `*` rotations to M95 before C39 reads a signed first word. Its seed
`7,177,369` has six low trits equal to one, so the C43 `p` operation
`crazy(7,177,369, input)` distinguishes **all 256 byte inputs plus the
distinct EOF word**. An independent 15-trit oracle proves the 257 classes;
this is encoded lossless guest storage, not a native C23 `int` value.

The new `build_seeded_preserved_first_input_source` keeps the physical
C44..C46 reset and C47 second `/`, then replaces the C51 state-overwriting
`p` with inert `o`. C52 emits the *second* input's actual low byte, C53
halts, and first-input M95 remains intact. All 274 bounded real-VM streams
(257 first-byte/EOF classes with truncated second read, sixteen input pairs,
and one unread-suffix case) check saved M95 against the independent oracle,
physical read positions, output, no later M95 writes, and exact 54-step halt.

A separate `build_seeded_delayed_first_output_source` composes a second
three-`j` reset after outputting the second word at C51. Its C55 `*` reloads
the encoded first value from M95, and C56 emits the rotated encoding's low
byte. Fifteen additional real-VM streams cover both EOF attempts, NUL, high
bytes, value 242, successful second reads and an unread suffix; they check
two actual read sites, both output sites, the saved word before reload, the
bijectively rotated word afterward, and exact 58-step halt. A changed first
input thus affects an output *after* the second read without host I/O.

This is a reusable physical input-state capability, **not** completion of
the seven-block mutable-C checksum. It still lacks a C23 signed `int`
decoder, source-bound mutable variables, checksum add/xor, conditional
branching, phi moves, and a dynamic EOF backedge. The checksum remains
an explicit no-artifact compiler refusal and P2 remains open.

### Source-backed second signed byte echo before its EOF arm (2026-11-20)

A complete SHA-locked C23 `emit` function now calls `getchar()` twice,
emits the first result with explicit EOF-to-106 conversion, and emits
the second low byte or 106 at EOF **before** its second-input EOF/byte
marker (30 or 154). The pinned Clang 22.1.8 normalized AST and exact
source SHA `38b68cab604142ec1f08ec9972b2a585b42f02f671840044f982f079cf10d738`
are authenticated to the typed six-block source CFG. The layout backend
independently checks the typed operations and emits the actual 132-cell
second-EOF classifier with C62 signed input, C63 output, and the physical
C64 control fold. It does not synthesize or choose the second byte on
its host side.

Two public publication tests pass. Nine pinned binary/EOF streams agree
with independently computed C23 output, native Clang `-O0` and `-O2` with
UBSan, and the normative guest process. Exact EOF and byte arms halt at
119 and 175 guest steps, respectively; additional forged Clang/source
controls refuse publication. This is source-backed runtime second-word
output and physical EOF branching, not dynamic C32 mutable storage,
checksum arithmetic, phi copying or a repeatable EOF loop. P2 remains open.

### Lossless first-input seed conflicts with the frozen jump chain (2026-11-20)

The complete mutable EOF checksum was retried with its five independent
C23 native/oracle cases and an explicit no-publication guest refusal. The
real C32 state, arithmetic, phi, and EOF backedge linker is still missing.
A new finite guest-storage experiment examines the already-executed 132-cell
second-input EOF skeleton, rather than treating a saved discriminator as a
lossless `int` local. The independent 15-trit oracle exhausts all 243
choices of `o`, `p`, or `*` at C9..C13, with the original graphical tail and
a C14 `p` preseed. Even allowing code edits that would invalidate the EOF
arm, the best M132 fold distinguishes only 175 of 256 successful bytes.

Across all 8,836 graphical C130/C131 tails, C14's single preseed yields
1,763 distinct tails whose M132 fold is injective over all 256 input bytes
and true EOF. Not one of these tails preserves the existing C18/C19
loader-derived two-jump restoration of D=135 at C20. In a concrete real-VM
counterexample, replacing tail `-}` with `b}` gives an injective
mathematical seed, but the reached C20 data pointer is 122, not 135, and
the original 119-step second-EOF halt is lost. The three focused Rust
checks in `tests/compiler_full_width_input_state.rs` distinguish those
non-executable seeds from real guest effects.

This only excludes the frozen five-cell preseed grammar and the unmodified
two-jump continuation, not redesigned pointer restoration, other code/data
layouts, or general C32 guest storage. No lossless first-input operation,
source-C checksum artifact, or runtime-loop parity is established; P2 remains
open.

### Rejected byte-injective seed with broken physical EOF control (2026-11-20)

An independent 15-trit oracle finds a mathematically injective first-input
encoding: changing the 132-cell source tail from `-}` to `a}` and executing
`p` at C10, C12 and C13 prepares M131=7,174,453 before C53's signed read.
The low six trits are all ones, so C61 `crazy(M131, input)` distinguishes
all 256 successful bytes and the distinct true EOF word. This is not yet an
executable guest local. The changed tail shifts loader-derived M132 from
7,174,350 to 7,174,337, and C10 also mutates code cell M128. The normative
N15 guest on empty input does **not** reach the original 119-step EOF halt;
at that bound it is still executing at C69. The candidate is rejected.

A separate finite source-preservation bound keeps C9..C11 inert to protect
reached EOF-arm code C127..C129, and requires the original M132 word for
its existing pointer-chain proof. Among all graphical C130/C131 pairs, only
`-}` and `~}` preserve that word. All 18 combinations of C12/C13 from
`o`, `p` and `*` then fail to produce an injective first-input fold.
This excludes only the stated fixed-source repair grammar, not a relocated
layout, a redesigned pointer chain, or general C23 byte storage. No C32
checksum opcode or source-to-guest artifact is admitted; P2 remains open.

### Two physical guest state writes before signed EOF control (2026-11-20)

A follow-up physical variant changes only C61 from inert to `p` in the
preseeded N15 guest. Before C63's real second signed input, C61 now
folds the first live input into M131, then C62 folds the resulting guest
accumulator into the independently preseeded M132. The two data writes
use distinct physical guest cells; both happen before the second input
overwrites A. On byte-arm revisits C61 is encrypted to inert `A`, while
C62 is inert `t`. Six real N15 streams preserve both exact EOF branches,
119/175-step halts, read sites C53/C63 and output sites C54/C57/C128.

This is **not** lossless guest byte storage: for example, first bytes 0
and 1 alias in C61's `crazy(125, input)`, so the later M132 fold cannot
recover their difference. The original mutable C32 checksum needs a
lossless state update, dynamic arithmetic, phi copies and backedge
linkage before it can produce any guest artifact. P2 remains open.

### Pre-input guest preseed improves retained signed state (2026-11-20)

A source-valid 132-cell N15 variant performs a new real C14 `p` while
D=132 and A=0, before reading the first signed guest input at C53.
This writes `crazy(7,174,350, 0) = 7,174,462` into loader-derived M132;
the existing C62 `p` then folds the **live** first input into that
preseeded word before C63 reads and classifies the second signed input.
The original loader tail `-}` and control skeleton remain unchanged.

An independently transcribed 15-trit truth table enumerates all 256
input bytes and true EOF: the earlier M132 fold distinguished 36 byte
classes plus EOF (37 total), whereas preseeded M132 distinguishes 171
byte classes plus EOF (172 total). The byte fold remains **lossy**,
so this does not represent a C32 local or implement the checksum.
The bounded 10-stream normative VM witness checks exact writes at C14
and C62, input events at C53/C63, output events at C54 and the selected
C57/C128 marker, a single encrypted C62 revisit on successful second
bytes, unread suffixes, and the exact 119/175-step halts. A NUL first
byte writes the same word at C62 and therefore produces no memory delta;
the trace independently checks the reached `p` opcode and resulting A.
No arbitrary guest control, arithmetic, phi copying, or repeatable EOF
loop is linked. P2 remains open.

### Source-C guarded third signed input after second EOF check (2026-11-20)

A complete C23 `emit` function now reads `first` and `second` as signed
`getchar` results, outputs the first low byte (106 for EOF), and uses a
real guest second-input EOF branch to output 30 or 154. Only the byte arm
executes a third discarded `getchar()`. The strict normalized Clang 22.1.8
adapter authenticates the exact source SHA
`65c93f567b3460dfaa2588a1a4355312abfc469fa519b1d3bc697319a26ecd14`,
45 source-derived AST nodes and the extra typed input operation on the
successful branch. The layout backend independently rederives the typed
CFG and selects the existing 132-cell physical C101 encrypted `p`-then-`/`
third-read builder, never a host-selected input or output.

The public compile command emits a 2,103-byte `malbolge-2026` capsule,
SHA-256 `86b3703b6d0a7fd36bad42e4a76fb587a9f7fcbe866cf3fdf920d11e58e36c57`.
Nine pinned binary streams, including empty/one-byte EOF, NUL, second
bytes 31 and 255, high bytes, third EOF and an unread fourth byte, agree
with native Clang C23 `-O0` and `-O2` with UBSan and with the normative
Malbolge VM. Both arms halt after 119/175 guest steps, respectively.
Backend admission also validates actual input events at C53/C63 and,
only for non-EOF second inputs, C101; forged Clang input metadata and
changed C source refuse artifact publication. The focused Python
publication tests pass (two cases, nine independent guest vectors).

This is a new **source-backed conditional guest input effect**. The third
input is intentionally discarded; it is not echoed, used in C arithmetic,
or C32 state. The original seven-block mutable EOF checksum still has
no executable operation/phi/backedge linker. P2 remains open.

### No safe single-cell output on the guarded revisit (2026-11-20)

The original guarded third-read guest executes C102..C113 once before
and once after the C101 conditional read. Exhaustive enumeration of all
94 graphical bytes at each of those twelve positions found exactly one
valid first-pass opcode that encrypts into output `<`: source byte `C`
at C108 first executes halt `v`. A real guest run replacing that one
cell halts at C108 with only C53/C63 reads, before the third read or
success-arm output. Therefore, simply changing one twice-visited
cell to emit the third accumulator cannot preserve this particular
132-cell layout. A relocated path, different prefix or multi-cell
construction remains untested by this exhaustive local bound.

### Rejected late third-output tail after guarded read (2026-11-20)

The source-valid 132-cell guarded third-read guest can revisit C101 and
consume a third input without confusing second-byte values 31 or 255 with
EOF. A separate four-cell continuation experiment changes C104 from `*`
to inert `o`, C112 from `o` to `p` (avoiding its encrypted `i`), and adds
an output/halt at C115/C116. Real N15 guest execution preserves the
119-step second-EOF arm and its two physical input events. However, on
successful second inputs 4, 31 and 255, the guest executes its third
physical read at C101 and then revisits the **unmodified C114 `i`** with
high-memory D. The instruction attempts to encrypt a non-graphical
C=7,174,350 target and fails before the new output, even when the third
read itself sees EOF. The focused regression freezes exact read sites,
stdout, source-cell mutations and rejected continuation. This is a
bounded failed physical relocation, not a source-C third-byte echo,
proof of impossibility, or P2 checksum acceptance. Correctly routing
past C114 still requires a genuine branch-layout change.

### Failed three-cell EOF/third-output repair (2026-11-20)

A physical branch variant changes C62 into first-pass `j` / second-pass
`/`, C66 into `j` / `<`, and adds a first-pass `j` at C93. For input
`03 04 05`, the normative N15 VM executes three signed reads, emits
`03 04 05` and halts after 172 steps. Second EOF instead halts after
119 steps with output `03 1e`. This looks like a complete third-byte
conditional echo, but is **not** valid C23 input control: successful
second inputs `0x1f` and `0xff` also take the 119-step arm and never read
the third byte. Eight bounded VM traces in
`tests/compiler_guarded_third_output_guest.rs` pin input code pointers,
output bytes, consumed input and halts, while an independent C23 control
oracle requires the third read for those non-EOF bytes. A separate finite
204-candidate one-cell relocation search found no repair for selected
0/31/255/EOF classes; this does not rule out a different layout or a
multi-cell construction. The candidate is rejected, not integrated as a
source-C compiler mode. The original mutable checksum remains unlinked.

### Two echoed words followed by conditional third guest read (2026-11-20)

A follow-up 132-cell source composes the verified C62 `/` and C63 `<`
second-word echo with C101's first-pass `p`, encrypted to `/` for the
success-arm revisit. The real guest echoes first and second low bytes,
then selects EOF/byte using that same second accumulator. The EOF arm
halts in 119 steps with only two signed input attempts; the byte arm
attempts a third input at code pointer 101, then halts at 175 steps.
Neither branch emits the third word, and both emit exactly three output
bytes including their fixed class marker. No host-supplied I/O is used.

Seven complete real VM streams check empty, high-byte, successful and
truncated EOF behavior. Seven separately derived nonlinear whole-path
proofs check ordered effects, source-dependent `p` writes, encrypted
revisits and isolation of the proposed checksum frame. Forged third
input, read position and C101 data are refused. This is not yet a C23
source program or a repeatable loop: full-width mutable storage,
signed EOF conversion, phi copies and C32 arithmetic remain unlinked.
P2 remains open.

### Second input is echoed before physical EOF control (2026-11-20)

A new 132-cell N15 guest variant reads the first signed word at C53 and
emits its low byte at C54. Unlike the existing classifier, the second
signed read occurs at C62, followed immediately by a real C63 `<` output.
The unchanged first classifier `p` at C64 then consumes **that same second
input word**, selecting the EOF arm or successful-byte arm. On the byte arm,
C62 and C63 are revisited after XLAT2 has changed them from `/` and `<`
to inert `l` and `Z`: no third input is consumed and no byte is repeated.
The executable path still halts after 119/175 steps, respectively, with
three guest output bytes: first low byte, second low byte, then the selected
`0x1e`/`0x9a` marker.

A 35-stream normative VM matrix covers empty input, NUL, high bytes, both
second-input outcomes, and unread suffixes. Seven independent whole-path
admissions derive data writes from the literal ternary truth table, match
both complete ordered I/O traces and self-modified code revisits, and verify
isolation of the proposed checksum frame. Three forged output/input/IO-event
witnesses refuse acceptance. This is an actual two-word guest dataflow and
branching primitive, **not** general source-C translation: a true N15 EOF
word echoes low byte 106 rather than the C23 unsigned conversion 255.
Full-width mutable state, C arithmetic, phi copies, dynamic EOF loop and
the original seven-block checksum remain physically unlinked. P2 remains open.

### Published two-read guest parity matrix (2026-11-20)

The exact two-read C23 EOF source, already published through the real compiler,
now has a frozen 46-case seeded binary matrix. A separately computed C23
oracle agrees with pinned Clang -O0/-O2 UBSan on all inputs; 12 fixed cases
also execute as real N15 guest processes and match both output bytes and
119/175-step halt boundaries. The remaining native-only cases are not claimed
as guest observations. This is a bounded fixed source grammar, not generalized
C branching, full-width mutable storage or the original P2 EOF checksum.

### First-word EOF discriminator survives a second read (2026-11-20)

A new bounded 132-cell N15 source variant changes C62 from inert code to
an actual `p` after the C53 signed read/C54 echo and before the second
signed C63 read. The real guest writes M132 as
`crazy(7,174,350, first_word)` while A still holds the first input, then
C63 replaces A with its own input word. Both second-read EOF/byte arms still
halt at 119/175 steps, with unchanged source-backed 2-byte stdout and only
two signed input events; a successful-byte arm revisits encrypted C62 as
inert `t` without repeating the data write. Eight complete normative VM
paths check the data write, C62 revisit, input/output order and unread suffix.
Three further negative controls show that removing C62's store can leave
stdout and termination unchanged while the true saved memory word differs.
An independent 15-trit truth table enumerates all 257 first-input outcomes:
first EOF maps to 14,348,673, disjoint from the 36 byte-derived classes.
But the fold is **not injective** (`1` and `2` collide), so it is only a
saved EOF discriminator and emphatically **not** C32 scalar storage. No
conditional *use* of the saved value, independent mutable C local, arithmetic,
loop or original checksum source-to-guest parity is claimed. P2 remains open.

## Failed third-byte echo relocation (2026-11-20)

A complete physical `second-input-EOF` branch was experimentally modified
at C62/C66: two graphical cells first execute `j`/`j`, then encrypt into
`/`/`<` when the byte arm revisits them. With successful second input, the
normative N15 guest actually reads a third byte at C62 and emits it at C66.
A bounded four-byte-class regression pins input `03 04 XX`, output
`03 9d XX`, all three real reads, and an explicit non-graphical termination
at 170 steps (not a source-level halt).

The same two-cell change **is not safe** on second EOF. C62's initial jump
changes the physical D chain feeding the C64..C67 classifier: the EOF case
instead follows the byte arm and C114 indirect transfer refuses an invalid
high-memory encryption target. The added test preserves this failed complete
input/EOF program rather than publishing a success-only artifact. These two
revisited cells are a negative physical-linkage experiment, **not** a
compiler operation or P2 checksum progress. A candidate must restore EOF
control and an admissible halt before it can be composed into source-C I/O.


### Addressed typed operation effects retain physical obligations (2026-11-20)

The unchanged seven-block C23 checksum now has a proposed source-address
**effect** for each minimal code reservation, not only a block/operation
interval. The original 19 typed instructions keep their canonical function,
block and ordinal identities. Each signed `getchar` binds a distinct input
site **before** two ordered, full-width frame-word store sites. Every typed
result reserves an individually addressed destination-word store; constants
also retain their exact target literal word. The sole byte output binds the
source scalar cell whose runtime value must be emitted. Effect-free work
retains an explicit minimal compute site. All sites remain source-ordered,
nonoverlapping and outside the final block-control reservation, even when
caller-supplied block and phi-pad proposals are reversed.

A red-first regression first failed because none of these code effect sites
existed; the source-authenticated test now checks the ordered cells, typed
source operands, two independent input effects, the byte-output source and
all destination/literal addresses. The separate physical first-read
suppression probe also failed: changing C37 from `/` into an inert source
byte breaks the loader-dependent pointer chain needed for nine correct
C23 rotations. Neither experiment has produced executable C32 arithmetic,
actual frame writes, encoded branch/phi copies, a repeatable EOF loop or a
compiled checksum. Every effect address is an **unverified reservation**;
P2 guest-output parity remains open.

### Addressed source operations acquire minimum code sites (2026-11-20)

The unchanged seven-block source-authenticated C23 checksum now assigns
physical *minimum reservation sites* to all 19 ordered typed operations.
Each site is tied to its canonical function, block and instruction ordinal.
The shared admission bound reserves a separate actual input instruction
before both N15 words of a signed getchar, charges every destination word
and constant-materialization write, and reserves at least one cell for each
other typed instruction. Across the seven original blocks the necessary
precontrol totals remain 15/1/3/4/4/7/2. The proposed operation intervals
are disjoint, ordered and strictly before their block's control site.
Reordering caller-supplied blocks does not change the authenticated binding.

A red-first original-source test failed because no operation code sites
existed; the same source-bound check now passes. These are lower-bound
address obligations only. The cells contain no actual Malbolge opcodes or
execution proof, and the unused code space may be necessary for C32
arithmetic, pointer motion and address-sensitive encryption. The original
checksum still refuses target publication; guest parity remains open.

### Physical C23 signed-byte conversion now emits output (2026-11-20)

`build_c23_nine_rotated_signed_output_source` produces a 91-cell `Iy` N15
program with nine actual M95 `*` rotations. The original C37 `/` still
consumes a first input; moving the second read to C66 leaves space for
C67/C69 and C70..C76 to repair D through encrypted and loader-expanded
pointer values. C77 `p` reads prepared M95=7,138,732, C78 `p` reads M96=121,
and C79 `<` emits the resulting byte before C80 `v` halts. The fixed
source-required C81=94 no longer prevents the converted output.

An independent 15-trit truth-table oracle and the normative profile VM agree
for every one of 256 second-input bytes, EOF, initial EOF, and an unread
suffix (259 complete 81-step traces). Every trace checks both signed input
events, nine rotations, all late jump data reads, both `p` writes, output
order, and termination. Target EOF correctly yields `0xff`, rather than the
raw profile sentinel's low byte. This is **not** source-C `getchar`: the
C37 input is discarded and only the second input is converted. The original
seven-block mutable checksum still cannot lower its C32 arithmetic, phi
copies, dynamic backedge or output to this physical source. No C artifact
has been published and P2 remains open.

### Second-input-dependent *third* read after a physical branch (2026-11-20)

The 132-cell N15 classifier now has an additional source-built variant
that **executes a third physical `/` only when its second input is a
successful byte**. The first C53 `/` is echoed at C54, the second C63
`/` selects the original branch through C64..C114, and the successful
arm revisits C101. At first execution C101 is a real `p`, writing
M[7,174,353] from the loader's 134 using the C82 accumulator; XLAT2
then turns this same code cell into `/` for the successful-arm revisit.
On second-input EOF, that revisit never occurs. A successful second
input followed by truncated third input still attempts the final `/`
and reports true guest EOF without consuming a byte. The original fixed
branch markers are unchanged. Both complete arms still halt in
119/175 instructions; no host callback supplies guest I/O.

Seven separately constructed exact-path witnesses independently derive
all physical writes from the fifteen-trit truth table and bind full
input/output event order, encryption phase, frame isolation, and source
identity. Forged C101 data, third-read event, and I/O position refuse.
A separate 48-case NUL/high/binary/truncated/unread-suffix matrix runs
the actual profile VM and checks the conditional input effect.
The original C23 mutable checksum was reattempted after this addition:
native -O0/-O2 outputs agree with the five independent controls, while
target lowering still explicitly rejects its unlinked seven-block CFG.
This physical primitive does not carry the third word into source-C
storage, normalize signed C23 EOF, or implement the checksum's runtime
arithmetic, phi movement, or repeatable EOF loop. P2 remains incomplete.

### Second-input-dependent EOF branch after the first echo (2026-11-20)

A new 132-cell graphical N15 candidate moves the existing four-`p` EOF
classifier's input from its first real `/` to a *second* `/` at C63. C53
consumes an earlier signed word and C54 emits its raw low byte. C63 then
replaces A before the C64 classifier: an absent second input takes the EOF
arm **even after a successful first byte**. A successful second read takes
the other arm, which revisits C63 only after self-encryption has changed
`/` into inert `x`, so it cannot accidentally consume a third byte. Both
arms halt after 119/175 guest steps, respectively.

Seven independently constructed whole-path nonlinear admissions verify
physical input and output events, source-locked code paths, trit-derived
guest writes and frame isolation. Forged output, input event and I/O
position are refused. Thirty-two further normative VM paths cross sixteen
binary boundaries on the second read, with first-byte variation, truncated
EOF and unread third-byte suffixes. The physical output is the first raw
input word followed by class marker `0x1e` on second EOF or `0x9a` on a
second byte. Initial EOF echoes the N15 low byte `0x6a`, not C23's cast
of signed `EOF`; neither branch implements C23 signed normalization. The
original seven-block checksum still cannot link arithmetic, phi copies
or its repeatable EOF loop, and no whole-source guest artifact exists.

### Source-block operations reserve physical cells before control (2026-11-20)

The seven-block original C23 checksum's addressed CFG now rejects a proposed
terminator that starts before the block's complete typed instruction sequence
can fit. Each ordered runtime operation requires at least one separate guest
instruction cell, and a 32-bit constant with two addressed literal writes
requires at least two. An original-source red-first regression first exposed
acceptance of a control site at block 2's first cell, despite its 32-bit AND
and Boolean comparison, then checked the exactly-short and minimally admitted
control starts independently for every one of the seven source blocks.

The lower bound now also counts each destination's distinct frame words:
C32 arithmetic/casts must reserve at least two guest memory stores, and a
signed `getchar` additionally reserves a real `/` instruction before its
two frame writes. The seven original blocks require respectively at least
15, 1, 3, 4, 4, 7 and 2 precontrol code cells. A second red-first case
previously accepted a 14-cell entry block; it now refuses that proposal.

This is a **necessary** lower bound on proposed code space, not a guest
implementation: C32 arithmetic and casts may need many more cells, and no
actual constant store, operation, conditional branch or EOF loop is linked.
The full source still refuses publication of an executable checksum; the
native -O0/-O2 input oracle remains the only whole-program parity evidence.

### Phi-copy pads bind successor jump sites (2026-11-20)

The addressed source-locked CFG now carries `pad_exit_address` for every
edge with phi snapshots/commits. The address is the last reserved code
cell in that predecessor-specific pad. The canonical checksum's four
unselected edges bind exit sites C279, C303, C327 and C375, respectively;
its four phi-free branch arms carry no pad exit. A source-backed,
reordered-input regression validates each exit against its original edge
identity, rather than selecting a runtime branch on the host.

This is only an address obligation: no target `i` instruction, physical
copy, conditional control or checksum is synthesized or verified.

### Phi-copy pads reserve their final transfer (2026-11-20)

The original source-authenticated seven-block C23 checksum still has four
unselected phi edges. Each physical landing pad must reserve one code cell
for each distinct snapshot/commit write **and one additional transfer** to
its canonical successor. Eight copy writes cannot both fit into eight
physical instruction cells and then execute the required jump. A red-first
original-source regression now refuses eight-cell pads on both the initial
phi edge and the loop backedge, while admitting nine-cell reservations.

This is a necessary code-space check only: it does not prove the jump,
execute the copies, implement dynamic C23 arithmetic or build the guest
checksum. All proposed code and data addresses remain unlinked. The five
native C23 input controls still pass and source compilation refuses target
publication as before.

### Source-typed input anchors with disjoint physical reservations (2026-11-20)

The unmodified seven-block C23 checksum now has an automatic minimum physical
code plan rather than requiring hand-authored source block and phi-pad
coordinates. Its 19 typed operations need 36 effect cells; seven terminating
control sites and four predecessor-specific pads of 9, 5, 5 and 9 cells
bring the minimum to **71 code cells**. All 43 guest-state words stay outside
the proposed source interval. A compiler diagnostic reports this exact source-
derived lower bound but still rejects target publication.

A separate source-locked input-anchor planner takes proposed instruction
addresses and verifies each against a genuine `Getchar`/`ByteInput` operation
ordinal and all preceding per-operation reservations. For the original checksum,
placing its first signed input at C37 and its loop input at C66 yields disjoint
block intervals C35..C51 and C62..C70. First-fit planning places the other
five blocks and four complete phi pads within C0..C91 (the last pad ends at
C79). All branch arms remain unselected; no host-side input chooses an edge.
Duplicate, non-input, overlapping, out-of-source and corrupted-wire anchors
are rejected. The first-fit policy is a deterministic feasible *proposal*,
not a completeness claim for all possible layouts.

C37 and C66 come from a separately executed 91-cell guest conversion probe.
Matching two address obligations does **not** validate that probe as this C
program: the proposed C function entry at C35 is not linked from the guest's
actual C0 entry, and its bytes do not implement the checksum's SSA stores,
C32 arithmetic, branch decisions, phi copies or EOF loop. The complete
five-vector guest parity gate remains blocked pending independent physical
instruction linkage and normative VM acceptance.

### EOF-classified two-input guest output (2026-11-20)

A new source-built 132-cell N15 guest composes two actual signed `/`
inputs (C53/C99), two accumulator-dependent `<` echoes (C54/C100), and
the pre-existing first-input EOF/byte branch into a *single executable
path*. The normative VM halts after 119 steps for initial EOF, emitting
`6a 6a 1e`; a successful first input takes 175 steps and emits the
first two input words' low bytes followed by `9a`. A missing second byte
emits the N15 EOF low byte `6a`; this is not C23 EOF normalization.

Seven independently constructed whole-path/physical-write oracles and 256
additional all-first-byte normative VM executions establish real input
consumption, three ordered writes, both branch arms and halt. Forged event
provenance or outputs refuse bounded path admission. This integrates two
guest outputs with genuinely dynamic control, but does **not** implement
the source-locked checksum's arithmetic, phi transfers, C23 EOF mapping
or repeatable loop; the complete C source still refuses guest publication.

### Source-locked phi pad capacity refuses impossible writes (2026-11-20)

The original seven-block C23 checksum's four proposed predecessor-specific
phi pads now have a **necessary physical capacity bound**. Each snapshot
and commit is a distinct guest-memory write, so the admitted pad width
must be at least their combined word count. Previously the addressed CFG
accepted a seven-cell pad carrying four snapshots and four commits, even
though eight separate target writes were owed. A red-first original-source
regression now refuses seven cells on both the entry phi edge and backedge;
an exactly eight-cell reservation remains admitted. The original wider pads
and all 197 frontend-adapter library tests pass.

The bound proves only that the interval is not *too short*. It does not
synthesize any physical copy, Malbolge opcode, branch or executable checksum.
The unchanged full C23 source still refuses physical target linkage and
publishes no guest artifact. P2 remains open.

### Indirect live-byte arithmetic reaches real output (2026-11-20)

A 91-cell, source-admitted `Iy` guest now retains nine real M95 rotations
and two signed input attempts, then crosses the fixed C81 halt with C79
`i`. C84 reads the *encrypted* M82=66 to reset D=67. C85 executes a
real input-dependent `p` against previously encrypted M67=85; C86 emits
that calculated low byte. The source-required C87=69 executes a second
`p` against M69=123 before C88 halts. Eight bounded, 86-step normative
paths cover EOF, NUL, 0x01, 0x7f, 0x80, 0xff, and an unread suffix.
An independent fifteen-trit truth-table oracle checks both crazy results,
all output bytes, read ordering, pointer state and final memory.

The output is *not* the signed C23 byte: its first crazy operand is 85,
not 7,138,732, and the second crazy occurs **after** the output. Earlier
C23 source-code and memory operands remain intact but are not consumed in
this branch. A genuine input-dependent guest arithmetic/output continuation
is now verified; the original seven-block mutable EOF checksum still
refuses linkage and has no guest parity evidence.

The adjacent short-route search also excludes a fixed two-jump C84/C85
return to M95. For all eight loader-admitted C82 bytes, the C79 indirect
jump encrypts M82 and C84 follows it to one of eight candidate words;
none contains the 94 needed to reset D to M95 in the next jump. This
excludes only the frozen prefix and indirect branch, not reordered guest
arithmetic, relocated source constants or longer dynamic control.


### C23 indirect tail cannot reset D with one graphical jump (2026-11-20)

The reached C79 `i` bypasses C81 but encrypts M82 before executing C83,
which is source-fixed to `o` by the earlier M83=79 pointer read. Its next
C84 `j` would need encrypted M82=94 to reset D directly to M95. The only
source byte with encryption image 94 is 83; at C82 that byte decodes to
unrecognized opcode `7` and cannot pass the strict source loader. All eight
loader-admitted graphical C82 opcodes are excluded by an exact table proof.
A bounded regression also checks that substituting 83 is refused before
publication. This rules out only the **one-jump C84** return in the fixed
91-cell `Iy` indirect layout, not longer routes or a relocated converter.
The full source-C checksum still refuses physical guest linking.

### Indirect C23 code-pointer bypass is physically executable (2026-11-19)

A new 91-cell `Iy` guest source runs the same nine operand rotations and
both C37/C69 signed input attempts, then replaces the unreachable direct
C81 output path with a genuine C79 `i` code-pointer jump. C78 reads source
M83=79, C79 reads M80=82 and transfers execution to C83 while encrypting
M82 from 80 to 66. C83 executes `o` and C84 cleanly halts. The independent
normative VM executes 259 complete 82-step paths over every successful
second input, first/second EOF and an unread suffix, checking the exact
input count, indirect pointer, target self-encryption, halt and retained
M95=7,138,732/M96=121 operands. The historical profile is rejected.

This is a physical **indirect control-transfer** primitive, not C23 byte
conversion or source-C control flow. A tempting path that instead reads
M82=80 after the `i` is invalid: `i` has already encrypted it to 66,
redirecting the subsequent data-pointer jump into an executable code cell.
No guest converted output, EOF loop, checksum artifact or native parity is
claimed. The P2 end-to-end witness remains open.

### Fixed C23 tail has no one-jump-shorter output return (2026-11-19)

The exact 91-cell `Iy` signed converter now has a bounded graph-search
regression anchored to the normative VM's first 74 real instructions.
The trace confirms M95=7,138,732, M96=121, the next D=86, and a prior
read of source M81=94 (which later decodes as the C81 halt). The search
independently admits every graphical source byte at the still-virgin
C82..C88 cells, including consistent repeated references. It also models
source-encoded control instructions at C74..C80.

The original four-jump C75..C78 route remains reachable as a positive
control. **Neither** a three-jump C75..C77 return **nor** an early C74
plus C75..C77 four-jump return reaches M95 in time for C78/C79 `p` and
C80 `<`. Changing C81 itself would invalidate an already consumed
pointer operand. This is a finite *fixed-prefix, fixed-loader* negative
result, not an impossibility theorem for a relocated source, different
reset graph or longer guest program. The converted accumulator still
cannot reach C23 `putchar`; the unchanged seven-block checksum remains
unlinked and its original five guest acceptance traces remain missing.

### Raw input checkpoint before correct C23 conversion (2026-11-19)

The original 91-cell `Iy` loader now has a separate, source-valid physical
candidate that changes **only C74** from `o` to `<`. Nine genuine rotations
prepare M95=7,138,732 and the second `/` at C69 loads a signed guest input.
The new C74 `<` emits that input's *raw N15 low byte*, preserving A and D;
the following C79/C80 `p` writes still consume the exact prepared M95/M96
operands and leave the mathematically correct C23 conversion in memory.

A new **259-path normative VM witness** covers second-input bytes 0..255,
second EOF, initial EOF, and an unread suffix, all with an independent
fifteen-trit conversion oracle, exact read/output/write ordering and a
82-step halt. It also proves the new source differs from the original
converter by only one byte and refuses historical profiles. This is a
concrete live-I/O-to-conversion boundary: output does not clobber later
input-dependent physical arithmetic. It is **not** a C23 `putchar` result:
EOF's raw N15 byte is not C23's converted `0xff`, and the correct converted
accumulator is not emitted because C81 remains a required `v`/pointer
constant. C37 still consumes an earlier input attempt; no source-C branch,
checksum loop, checksum guest or parity claim follows. P2 remains open.

### Relocated guest reset with an output checkpoint (2026-11-19)

A different, source-admitted 91-cell N15 loader tail yields M96=66. The
physical pointer-reset chain can therefore use M67=67 and M68=94, preserving
M62 for executable guest code instead of the earlier M96=72, M73=61,
M62=94 chain. The existing eight-tail M96=72 source constructors and their
admission policy are unchanged; this relocation is only used by the new
three-input checkpoint builder.

The physical path completes nine actual loader rotations, then consumes
three independent signed guest `/` attempts at C39/C51/C59. All three `p`
operations at C43/C55/C63 read and overwrite the same M95 word. C47 emits
the first state **before** the second and third input, while C64 emits the
final state and C65 halts after exactly **66 real VM steps**. The middle
input changes stored state without generating a byte. All seven three-`j`
resets read M96=66, M67=67 and M68=94. In particular C62 really executes
as `j` without encrypting a reset operand, unlike the older M62 chain.

**46 normative guest paths** across two source seeds (five EOF/truncation
streams and six boundary values at each of three input positions per seed)
match an independent fifteen-trit oracle for the two output bytes, each
read, write, pointer return, final memory state and exact input consumption.
Non-current profiles and incompatible/unloadable tails refuse before any
artifact is returned. This proves source/data reset relocation and live
state across an output checkpoint, **not** source-C arithmetic, signed C23
normalization, a runtime Boolean branch, or the original EOF checksum. P2
still lacks a full source-locked guest artifact and its five parity traces.

### Guest-visible state-prefix streaming (2026-11-19)

The bounded 91-cell N15 prefix-fold helper now performs two genuine guest
`/` attempts, writes the same M95 cell twice with `p`, and emits **both**
updated states with separate reached `<` instructions. After the first write,
a three-`j` reset places D at M95 before output; the output then advances D
to M96, allowing another verified reset and input. The reached events are
C39 read, C43 update, C47 output, C51 read, C55 update and C56 output;
C57 halts after exactly **58 normative VM steps**.

Two graphical loader seeds and **78 bounded VM input paths** include empty,
truncated, NUL, high-byte, both input-position sweeps and unread suffixes.
Another **30 real VM paths** check the six other graphical tails with the
required M96=72 pointer-reset seed, yielding all eight admissible tails and
108 paths total. An independent fifteen-trit truth-table oracle checks both
output bytes, raw EOF, state-write provenance, exact pointer resets on the
first two seeds and final M95 contents on all eight.
Unlike an output-after-final-state-only probe, this exposes a stored prefix
*before* the next independent guest read. It does not implement source-C
arithmetic, C23 EOF conversion, runtime branching, or the full checksum; P2
remains open. The three-input final-output helper remains byte-identical.

### Sequential physical guest input folds (2026-11-19)

The source-generated, 91-cell N15 `,H`/`CH` loader now supports one, two,
or three **real signed input attempts** followed by repeated guest `p` writes
to the same M95 state cell. Nine reached `*` rotations prepare the loader
word; each following input crosses the actual three-`j` pointer-reset
chain, reads another stdin word, then updates M95 from its previous value.
The source emits the final state's low byte and halts in exactly 46, 54,
or 62 normative VM steps for one, two, or three inputs respectively.

The parameterized constructor preserves the preexisting two-input byte-exact
layout and refuses input counts outside 1..3, historical profiles and
loader tails without the required M96 reset seed. A new independent
fifteen-trit oracle checks all nine rotations, every read/reset/write,
actual input consumption, the emitted byte and the final state for **138**
bounded VM paths over two source seeds and binary, EOF, truncated and unread
suffix streams. A separate 18-case guest regression confirms that changing
the third input changes the resulting stored state and output. The earlier
39-path two-input regression still passes unchanged.

This is a reusable **physical Malbolge state-fold primitive**, not C23
integer addition, signed EOF-to-`0xff` conversion, a dynamic byte stream
loop, or source-locked CFG execution. A fourth event would traverse source
cell 62, which the current pointer reset also needs as unencrypted data;
that unsupported continuation correctly refuses. The original seven-block
mutable EOF checksum still cannot publish guest code, and P2 stays open.

### Source-locked function and terminating-control entry proposals

The unchanged seven-block C23 EOF checksum now exposes one proposed **function
entry** (block 0 at code address 64) and one **return site** (block 6 at
address 239) alongside all eight original unselected CFG control edges.
Every proposed block interval additionally reserves a source-contained
`control_start` for its terminating control sequence. Each branch arm carries
the same **original addressed Boolean operand** and predecessor control entry;
ordinary jumps carry no Boolean, while the separate return record preserves
its optional typed result. The original four predecessor-specific phi pads and
two-phase word-copy obligations remain unchanged. Relocation independently
binds function entries to the canonical CFG, not to caller order, and refuses
terminator addresses outside their corresponding block intervals.

These are source-backed **address obligations only**: no actual graphical
instruction decodes at these proposed sites, no binary branch or dynamic loop
runs, and no C32 checksum arithmetic or source-language return has been linked.
The full five-vector native C23 test still expects physical-linkage refusal
without a published guest artifact. P2 guest parity remains open.

### CFG phi edges now reserve predecessor-specific code entry pads

The original seven-block mutable C23 EOF checksum still refuses physical
publication. Its source-locked CFG now requires **four disjoint, edge-specific
code landing pad reservations** in addition to seven proposed source blocks.
Each of eight original control arms carries a proposed `entry_address`: ordinary
edges enter the successor directly, while phi-bearing edges first enter the
reserved predecessor-specific pad. The shared successor's `target_address`
remains distinct. Thus the four-word parallel backedge cannot accidentally
bypass its snapshots and commits through the proposed control handoff.

The binder independently rederives required phi edges from canonical source
and refuses a missing, duplicated, spurious, wrong-arm, wrong-predecessor,
empty, overlapping or out-of-source pad. Reordering valid code and pad
proposals retains canonical control order; adjacent intervals are admitted.
This is an **untrusted physical address plan**, not emitted Malbolge: pads
contain no decoded instructions or verified copy writes, and jumps, arithmetic,
EOF termination, mutable control and the five native-C/VM parity paths remain
unlinked. The unchanged P2 source continues to refuse guest publication.

### Source-locked CFG edges now have checked candidate code entry points

The original complete C23 mutable EOF checksum still refuses physical target
linkage. Its canonical seven-block CFG and 43-word N15 data frame can now
be paired with **proposed** nonoverlapping code-block intervals within the
same source-length boundary. The checked `GuestAddressedCfgPlan` binds the
original two branches' true/false arms and four jumps to eight exact
successor code entries; every edge carries its own addressed phi snapshot
and commit obligations. The four-word backedge is still parallel, and
no host-selected branch or source-specific computed output is substituted.

An explicit invalid-placement error rejects absent, duplicated, foreign,
empty, overlapping and out-of-source block intervals before producing any
addressed plan. Reordering a valid set of proposed intervals preserves the
canonical control-edge order. The source-controlled regression covers all
seven blocks and eight paths with positive and forged-placement cases, and
the existing native -O0/-O2 five-vector gate still confirms guest refusal.
**These code addresses are untrusted suggestions**, not position-sensitive
Malbolge opcodes: no instruction bytes, branch encoding, self-modification
proof, guest phi writes, C arithmetic, EOF loop or five guest parity traces
exist. P2 remains open.

### Typed relocation retains complete scalar operands (2026-11-19)

The source-locked checksum's located instruction handoff now carries the
original typed operation and source span with **full-width**, typed, SSA-
identified operands. Every read, result, branch condition and return use
retains its checked contiguous N15 address range; a 32-bit scalar cannot
silently collapse to its low 15-trit cell at the physical linker boundary.
The exact literal-write obligations and addressed phi-edge transfer order
are unchanged. A red-first compiler regression caught the previous loss of
operand width, typed operation and source provenance; it now checks all 19
checksum instructions and their exact source-relative addresses.

This gives future physical operation encoding the identity and number of
words that it must really read and write. It does **not** create any guest
instructions, normalize target EOF, execute the checksum or turn the
source-locked 43-word reservation into initialized guest memory. All five
original native C23 input witnesses still require real VM parity, and P2
remains open.

### Edge-specific addressed control handoff (2026-11-19)

The complete source-locked seven-block checksum CFG now binds each placed
block's symbolic `Jump`, `Branch` (both arms), or `Return` to its own
predecessor-sensitive phi-copy obligations. Each reachable successor has
an exact block identity; phi-bearing edges carry first all physical N15
scratch snapshots, then all destination commits, with no host-selected
branch arm. The relocator independently checks the CFG's phi-bearing
successors and refuses missing, duplicated, or orphaned transfers rather
than silently substituting an empty edge. A red-first whole-source test
covers two branches, four jumps, one return and the four-cell EOF backedge;
194 frontend tests and the three native-C/checksum refusal tests pass.

This is a more concrete **data-only linker handoff**, not emitted code.
No guest branch, phi store, checksum arithmetic, EOF loop, or guest checksum
output exists yet. The unchanged compiler still refuses publication before
target layout; P2 acceptance remains open.

### Source-locked dynamic checksum now reports precise prelink obligations

The unchanged C23 mutable EOF checksum passes canonical typed IR, the complete
symbolic seven-block CFG, 19 ordered runtime operations, four predecessor-
sensitive phi edges with six parallel assignments, and 43 frame-relative
15-trit guest words. The `c2malbolge_json` boundary now derives these counts
from the actual authenticated prelink instead of reporting phi **storage** as
unsupported, even though the symbolic frame allocation already exists.

The same five native C23 `-O0`/`-O2` vectors still reach an explicit target
refusal before the layout backend: physical operation encodings, parallel phi
**writes**, dynamic branches, and an EOF backedge remain unlinked. The
regression requires both the exact prelink accounting and the absence of any
published guest artifact. This is a diagnostic correction and usable linker
handoff, not a C compiler execution milestone or P2 acceptance.

### Bounded C23 converter tail limits (2026-11-19)

The nine-rotation `Iy` probe still performs both required live `p` writes
but halts at C81 before output. An attempted earlier return through a new
C74 `j` was checked over **all eight** graphical source values for its
virgin M86 operand. A fixed `Iy` loader, strict source admission and eight
82-step normative VM traces show that C74 reads M86 and C75 reads each
resulting word, but no option restores D to M95 at C76 for the first `p`.
The closest M86=47 follows encrypted M48=95 and lands on **M96**, one
word too far. The original nine rotations and both input events remain
identical across this bounded substitution. Other modified code/data
paths and larger layouts are not excluded.

A separate single-operation obstruction covers more than loader-derived
constants. For any N15 data word W, `crazy(W, 1) - crazy(W, 0)` is either
-1 or 0: only the low input trit changes, and the three possible data
trits yield low output differences -1, -1 or 0. A lone `p` followed
by `<` therefore cannot echo both bytes 0 and 1, whose outputs would
need to differ by +1 modulo 256. This rules out dropping the second `p`
from a raw signed-input-to-byte identity converter, not other multi-step
synthesis or the original checksum program. P2 remains open.

### Strict C23 probe admission and a second failed output return (2026-11-19)

The physically converted two-crazy C23 value still reaches M[96] at C80,
then source-required M[81]=94 halts at C81 without output. Trying to save
one pointer-reset step by replacing virgin M[82] with 94 would let C77
return directly to M[95], but source byte 94 at position 82 does **not**
decode to an admitted graphical instruction. The normative loader rejects
this candidate, just as it rejects the M[87]=94 direct shortcut. Neither
candidate proves an alternate layout impossible; the C checksum remains
unlinked.

The public probe-source checker now enforces the same two-word minimum and
N15 memory-size ceiling as the normative graphical loader, in addition to
per-position opcode admission. An empty or one-word source previously
passed the checker despite failing in the actual VM. A focused regression
also checks both rejected pointer shortcuts. This corrects pre-execution
admission only and does not claim guest output or C23 program translation.

### Stateful guest data across two separate input events (2026-11-19)

The bounded 91-cell `,H` source now completes nine physical rotations
of M95, then two separate `/` reads and two `p` writes to the **same**
M95 data word. The first `p` stores a function of the first raw input;
the second reads that exact stored word and incorporates the second raw
input before a real `<` and halt. Thirty-nine independently computed
binary/EOF cases match all 54 normative guest steps, memory reads and
writes, input consumption, and output. Both inputs influence the result.
This closes one previously missing *physical* state-retention link, but
not the source-C CFG or signed C23 `getchar` conversion. The frozen
five-vector checksum still refuses to publish guest output.

### Strict-loader obstacle to direct C23 output relocation (2026-11-19)

A direct source-validity experiment tried to shorten the final signed
conversion pointer return: write M87=94, so the reached C75 `j` could
jump directly to M95 and leave time for `p`, `p` and `<` before the
mandatory C81 halt. This fails **before execution**: graphical byte 94
at source position 87 does not decode to a valid loader instruction.
The short-route candidate must not be published or counted as C23 output.

The C23 probe builders now independently reject invalid graphical source
cells with a typed position/byte error before returning source. A focused
regression checks the exact attempted M87=94 placement and the VM loader's
own rejection. This is source-admission hardening, not a solution to the
remaining M81=94 execution trap or a proof that other relocations fail.
The five native C23 checksum vectors still refuse at dynamic CFG linkage;
no guest checksum artifacts or output parity are claimed.

### Nine-rotation physical C23 conversion without output (2026-11-19)

A 91-cell, strict-loader-admitted `Iy` source now executes nine real
rotations of M95 to 7,138,732, reads the second signed input at C69,
then uses actual pointer relocation through encrypted M70 and M67 to
reach M95 and M96=121. Two reached `p` instructions at C79/C80
compute the exact C23 signed input-to-byte result, including EOF, in
the guest accumulator and memory. An independent scalar oracle agrees
with 259 complete normative VM traces; the first C37 input is consumed
during the rotation precursor. C81 must retain source value 94 to
support earlier pointer resets, so its reached `v` halts after 82
steps **without output**. The source is not a C compiler artifact.
Relocating emission, retaining mutable locals and linking the original
five-vector EOF checksum are outstanding P2 work.

### Finite adjacent-loader EOF conversion rotation bound (2026-11-18)

An independent exhaustive scalar check now screens all 94-by-94 printable
source tails, all 12 phases of the adjacent loader recurrence, and all
15 cyclic rotations of *each* of two consecutive operand words. Of the
23,857,200 candidate pairs, only eight survive a four-input filter and
all 257 exact C23 output checks: each requires nine rotations of the first
word and none of the second. The eight cases use tail first byte 72, 73,
75, or 76, tail second byte 121, and phase four or ten. Every case yields
final operands `[7_138_732, 121]`. Source-position admission still limits
which tails can be loaded; the existing graphical `Iy` tail at positions
89 and 90 works for physical data words 95 and 96.

This is a **finite restriction of one candidate operand family**, not a
minimum operation count for arbitrary guest programs. No guest has executed
the required nine same-cell rotations, restored its data pointer, or applied
both `p` instructions to the live input. The independently established
physical two-read echoes still produce the target EOF low byte `0x6a`, so
the original complete C checksum cannot be published and P2 stays open.

### Two independent physical input-word echoes (2026-11-18)

A separate bounded 132-cell N15 source now executes two *unconditional*
physical signed reads and echoes each input word through actual guest `<`
instructions. It outputs at steps 54 and 114 immediately after the real
reads at steps 53 and 104. Six complete binary/EOF streams pass source-
and profile-bound normative VM admission, independent trit/store controls,
exact ordered I/O traces, and negative forgery tests. An additional
256-case normative VM pass pairs every first-byte class with a varied second
byte and checks exact ordered input and output events. Every path halts in
130 steps; only the first two successful bytes are consumed and trailing
bytes stay unread. The target's EOF low byte is `0x6a` rather than C23's
`0xff` conversion; this primitive cannot implement `putchar(getchar())`
without a separate signed conversion proof.

The new source also changes the physical data footprint: its forward C=127
rotation writes M[156], which collides with the previous checksum scratch-
free frame `[153,196)`. The isolation test explicitly rejects reusing that
placement. The earlier source-locked placement and the original input-
dependent EOF checksum guest **do not** inherit this source's admission.
There is no linked mutable C state, runtime arithmetic on C locals,
conditional loop or checksum guest artifact. The complete C source still
refuses at dynamic guest CFG lowering, and P2 remains open.

### First physically input-dependent output with guarded continuation

A distinct 132-cell graphical N15 source now emits the actual first signed
input word's low byte at C=54 before the classifier overwrites the
accumulator. The first-pass `<` self-encrypts into an inactive instruction
on the successful-byte revisit. Empty input emits the target's real EOF
sentinel low byte `0x6a` and the fixed EOF marker `0x1e`, with one input
attempt and a 119-step halt. Any first successful byte `b` emits
`[b, 0x9a]`, then performs the guarded second physical input attempt at
C=101 and halts after 175 steps. The second input is not echoed.

Six independent byte/EOF traces admit the exact output and I/O order,
code path, full `p`/`*` writes, and isolation of the future 43-word
checksum frame. An additional exhaustive 256-case normative VM run pairs
each possible first byte with a separately varied second input byte and
verifies the exact first-byte echo, second physical input event, and
175-step halt for every first-byte class. Wrong first output and
shifted effect timing refuse.
This is a real data-dependent **guest** stdout byte, not host-simulated
C semantics. EOF is not normalized to signed C23 `-1`, the output includes
non-C markers, and there is still no linked C state, arithmetic, backedge
or checksum-output parity. The changed source requires fresh source-bound
state placement if it is ever linked to typed checksum operations. P2
remains open.

### Independently admitted guarded two-read guest paths (2026-11-18)

The 132-cell physical signed EOF source now has six complete, separately
constructed nonlinear guest-path oracles: empty, NUL, high byte, two
mixed-byte streams and a repeated high byte. Each witness fixes the exact
119/175-step code sequence, real input events, first-arm output, source
identity, and all reached `p`/`*` effects. The extra first-pass `p` at C=101
writes the independent `crazy(134, A)` result into M[7,174,353] before that
source cell encrypts into the second-pass `/`. The oracle derives `A` from
the earlier step-82 crazy result, without reading expected values from the
normative VM. A second input at step 171 is admitted only on the byte arm,
after its fixed output marker. An initial EOF has no second input event.

The VM-independent path admission and complete instruction-write checks
pass all six streams. Forged second-byte/EOF provenance, shifted or missing
second input effects, and an altered physical `p` result fail closed. The
43-word future checksum frame `[153,196)` remains isolated from every
admitted helper access. The two-pass source encoder also refuses a first
opcode that the strict graphical loader cannot admit, even if its encrypted
successor decodes to a useful instruction. At C=103 an apparent encrypted
`<` echo needs such an invalid first opcode, so it is not a usable guest
output mechanism. This is not the original checksum, guest arithmetic on
C locals, a third read, or a repeatable EOF loop; P2 remains open.

### Conditional second signed read on physical byte arm (2026-11-18)

A 132-cell N15 guest now conditionally performs a *second* physical `/`
after the first successful signed input. C=101 decodes as `p` during
the common forward traversal, then self-encrypts into `/` only on the
byte arm's C=45..104 revisit. A first EOF takes the C=126..129 arm
and halts in 119 steps after one input event and marker `0x1e`.
All 256 successful first-byte values instead halt in 175 steps, after
the original C=53 input and a second real `/` at C=101; an absent
second byte produces the actual target EOF event, not a host sentinel.
The byte arm emits `0x9a` at C=57. Seven additional finite streams
cover NUL, high bytes, second-byte EOF and unread binary suffixes.

This is a genuine input-dependent *read count*, unlike the earlier
unconditional two-read source. The output is still a fixed branch
marker, no source-C state is materialized, no third loop iteration
exists, and the original mutable EOF checksum still refuses
publication. The guest's EOF sentinel is not the signed C23 `-1`.

### Two real signed input reads on one physical guest path (2026-11-18)

A new bounded N15 experiment keeps the same 132-cell graphical EOF helper
but changes its reached C=104 rotation to a second `/` input, and changes
C=114's conditional jump to `<` output. The normative guest now executes
130 complete steps, two input instructions at C=53 and C=104, output at
C=114 and C=128, and a halt at C=129. Six independent streams exercise
empty input, NUL, a high byte, multiple bytes and EOF on the second read.
The observed output is the second input's low byte (the target EOF word's
low byte `0x6a` when absent), followed by the fixed marker `0x9a`.

The direct attempt to retain C=114's conditional jump after the new read
failed in the actual VM at step 183: the second traversal executes an `i`
at C=112 and tries to encrypt nongraphical M[7,174,341]=134. The
regression preserves this failed path and proves the forward two-read
candidate halts cleanly instead. Neither version checks EOF *before* the
second read, updates the C checksum, or links typed operations to guest
state. It is finite physical I/O evidence, not C semantics or P2 closure.

### Source-bound physical instruction-write effects (2026-11-18)

The independent nonlinear guest-path boundary now preserves *every* reached
`p`/`*` instruction's decoded opcode, step, operand address, operand word and
pre-encryption result. Changed-memory deltas alone lose valid effects: the
real EOF helper executes an idempotent `p` at step 82 (M[143] stays 125),
while a separate 36-step N15 guest rotates graphical code M[34] from 99 to
33 before XLAT2 encrypts that same address. Both cases are actual normative
VM executions, not host-produced target outputs.

`verify_bounded_guest_instruction_writes` compares a complete ordered
physical write sequence with an independent oracle, refusing missing
idempotent writes, altered opcodes/results, unsorted steps and out-of-range
words. The original checksum's five source/profile-identical helper paths
match a separately computed trit arithmetic/write oracle; the protected
43-word C frame remains untouched. This supplies a physical write-effects
boundary for a future typed-operation linker, **not** a guest C-state write,
phi transfer, arithmetic backedge or emitted checksum. P2 remains open.

### Distinct physical path provenance (2026-11-18)

Physical guest-path admission now retains the exact binary input in each
immutable normative path witness, including any suffix left unread at halt.
When the source-bound checksum placer joins paths, it rejects repeated input
streams rather than counting one replayed path as multiple evidence cases.
The returned candidate preserves the exact admitted input streams in sorted
order; reversed witness order yields the same candidate and identity record.

A red-first regression demonstrated the former duplicate-path acceptance,
then proved the refusal with the original five C23 checksum input cases.
The existing 257-class normative input test also now checks that the
five-path allocated C frame `[153,196)` is never fetched, encrypted, read or
written by any reached byte/EOF helper step. All 257 first-input classes
passed under the existing finite guest-step bound; this does not establish
arbitrary multi-byte or loop behavior.

This is an evidence-integrity correction, not executable C-state linking.
Five distinct inputs do not prove general stdin behavior. The physical helper
still only emits fixed byte/EOF markers, and no checksum guest trace exists.

### Physical-source-bound checksum data placement (2026-11-18)

The existing 132-cell signed byte/EOF helper now has a *joint* data-placement
witness for the source-authenticated original C23 mutable checksum. A checked
request supplies its exact graphical helper source, five independently
admitted normative VM paths, complete helper scratch intervals, a target
profile, and the checksum's already-authenticated canonical typed wire.
The linker boundary verifies path/source/profile identity instead of reusing
traces of another helper. It derives the complete frame width from the typed
CFG, checks the helper's reached accesses and all declared scratch, then
relocates 19 typed operations, branch conditions, literal-word obligations
and four staged phi edges into one physically isolated 43-word state frame.
Unlike the earlier assumed 2,048-cell length, the relocation uses the real
132-cell source length and the exact first-fit state base.

A source-bound red-first Rust regression loads the canonical checksum wire
from its source-checked frozen snapshot and independently admits EOF, NUL,
255, mixed three-byte input and 128 through the real N15 VM. It verifies
that each relocated scalar or phi-copy address lies in the isolated frame.
Reordered paths reproduce the result; changed graphical bytes, missing
scratch, a foreign target profile and corrupt typed IR refuse.

**This does not compile or execute the checksum.** The helper still outputs
only fixed EOF/byte markers. It never initializes or updates a C SSA word,
performs a checksum arithmetic operation, copies any loop phi or executes a
C backedge. The provided wire must already be authenticated against source C
upstream, and any later physical-source edit requires fresh normative path
admission and relocation. The five required checksum-output guest traces are
still absent and P2 remains open.


### Declared-helper scratch excluded from future C state (2026-11-18)

The five-path physical-state placer now **requires the helper's declared
scratch intervals** rather than inferring available state memory solely from
the cells touched by those five paths. Each interval is source-external,
ordered and within the current N15 profile's memory; together they must cover
every reached mutating instruction target without a code/encryption collision.
The helper and future state frame share one 4,096-word reservation ceiling.

A deliberate extra scratch reservation beyond the reached writes shifts the
first-fit 43-word state frame. Missing remote helper scratch, scrambled
intervals and over-budget reservations fail closed. The actual five-path
guest test independently checks that each smaller frame candidate conflicts
with either reached VM accesses or declared scratch, even when the scratch
word was not visited in these inputs. Source/profile identity still binds
all five paths.

This closes a *planning alias hazard*, not a C execution gap: the helper's
declared unused scratch may be needed by a later code path. The 43-word frame
remains uninitialized; no guest checksum operations, state write, phi copy or
runtime loop is linked. The original source-locked checksum still refuses
publication, and the five checksum-output VM traces remain missing.

### Read-safe candidate placement of the checksum state frame (2026-11-18)

The nonlinear physical-path admission now retains **actual data-cell reads**
from the normative VM, distinct from its data-pointer register. A checked
isolation gate prevents a proposed mutable C state frame from aliasing any
reached helper data read, `p`/`*` write (including an idempotent write),
code fetch, or encryption address. This closes a real dependency hazard:
the 132-cell signed EOF classifier reads virgin M[148] while resetting its
data pointer; a state frame covering 148 could alter later control behavior
even if the helper never wrote that address.

For the five independently admitted EOF/byte helper paths, a bounded
source- and profile-identity-checked first-fit placement now derives one
43-cell *unused* state region from the union of real physical accesses. It
also refuses malformed or oversized requests and is deterministic under case
reordering. The 43-cell width comes from the independently tested original
source-authenticated checksum SSA/phi plan. An independent per-path verifier
rejects every smaller source-external placement because of a reached helper
access or declared helper scratch. Full typed-operation and phi address
relocation remains separately
verified with a hypothetical code length, not this physical source candidate.

**This is an isolated address candidate, not a linked checksum:** the
132-cell helper still emits only EOF/byte markers, does not initialize or
modify a single checksum SSA cell, and does not execute a checksum branch or
loop. The path evidence is finite, not a proof for arbitrary inputs or a
future modified source. C-source target publication remains refused and the
five required checksum-output VM oracles are still absent. P2 stays open.

### Admitted physical scratch regions for source-bound guest paths (2026-11-18)

The existing one-read N15 EOF/byte control source physically writes near its
132-cell source and at remote addresses around 7.17 million. The nonlinear
path verifier now retains every actually reached `p` and `*` destination,
including writes that happen to leave the memory value unchanged. Its new
`verify_bounded_guest_data_regions` gate checks small, ordered, disjoint,
source-external data intervals against normative path fetches, encryption
addresses and all mutating instruction destinations. It uses the verified
profile memory bound, not a caller-supplied memory capacity.

For five independently admitted physical paths (empty, NUL, high byte, mixed
three-byte input and another byte), the executable control helper's writes
fit `[132,146)` and `[7,174,344,7,174,386)`. Dropping the remote interval,
allowing source/data overlap, or forging over-budget/out-of-range intervals
fails closed. The test had an initial red compile before the API existed.
The intervals identify **helper scratch**, not mapped C SSA values; they do
not provide literal initialization, guest arithmetic, phi copies, a live
checksum loop, or any of the five required checksum-output VM traces.

### Checked absolute checksum data relocation (2026-11-18)

A new source-locked `state_relocation` stage re-derives the original
canonical typed CFG and binds **all data-side addresses** of its seven
blocks to one proposed N15 frame base. The address plan includes every
runtime instruction operand and result, full-width literal-cell write
obligation, both Boolean branch conditions, return slots, and each
source-to-scratch and scratch-to-phi copy on all four incoming edges.
Neither the C source nor its SSA values are evaluated by the host.

For a hypothetical **final** graphical source length of 2,048 cells and
frame base 4,096, the 43-word checksum frame occupies addresses
4,096 through 4,138 inclusive. The stage checks the frame against the
source interval, validates each complete typed slot and both ends of
all copies, rejects an overrun of the 14,348,907-word N15 memory, and
recomputes deterministic bindings from the canonical source instead of
accepting a caller-forged prelink plan. Red-first tests verify the entire
address ledger, invalid source identity, source overlap, and exact
end-of-memory placement.

**The 2,048-cell code length is a test assumption, not an emitted source.**
No actual source length, instruction encoding, initialized writable data,
conditional or backward jump, arithmetic or phi transfer is physically
linked here. The real source-C compiler still refuses any checksum guest
artifact before calling a target backend. The five-stream normative VM
parity acceptance is unresolved; P2 remains open.

### Source-locked dynamic checksum operand bindings (2026-11-18)

The prelink `state_operations` stage now binds **every instruction and
terminator of the unchanged C23 checksum** to the previously verified
function-local SSA frame. Its seven ordered blocks carry 19 original typed
instructions, exact source spans, 32-bit operand/destination cell ranges,
signed `getchar` input destinations, one `putchar` source and both Boolean
branch-condition slots. Constants carry explicit per-cell 15-trit values
computed from the canonical typed integer bytes; a 32-bit value is never
silently truncated into one N15 word. The source-to-slot map is produced by
`prepare_canonical_dynamic_cfg`, not a caller-supplied lowering fixture.

The binding checker regenerates the canonical SSA reservation and refuses
substituted function IDs, missing or altered value slots, changed scalar
widths, and malformed Boolean/input/output operand categories. The focused
source-locked regression checks exact typed instruction and operand order,
constant reconstruction, branch inputs, deterministic re-planning, and
forged-frame refusal. It preserves the separate phi scratch-copy plan.

**These bindings are obligations for a future physical linker**, not guest
memory contents or executable Malbolge instructions. Runtime arithmetic,
constant materialization, guest cell-copy instructions, conditional/backward
jump relocation, and independent five-stream VM parity are still missing.
The source-C driver still refuses artifact publication, and P2 remains open.

### Relocatable checksum SSA frame and safe phi staging (2026-11-18)

The source-authenticated prelink path now computes **guest-word-relative
storage reservations**, rather than stopping at unscheduled symbolic phi
assignments. Its `state_storage` stage walks the independently validated
canonical typed CFG, reserves disjoint value intervals and computes scratch
space sufficient for the largest predecessor-specific parallel phi edge.

In the current 15-trit N15 profile, Boolean and unsigned byte values reserve
one word, while complete signed/unsigned 32-bit words reserve two; no
`getchar` EOF bits are narrowed to a successful byte. An exact C32 word is
split into two profile words by quotient/remainder with base
`3^15 = 14,348,907`. Reconstruction rejects noncanonical or out-of-range
cells rather than silently truncating. These are **frame offsets**, not guest
addresses.

For the frozen complete EOF checksum, the authenticated seven-block CFG
contains **21** distinct SSA value definitions occupying **39** 15-trit data
cells. Its four predecessor-specific phi edges require a maximum **four**
snapshot cells, for a **43-cell** frame-relative plan. Each edge schedules
*all* source-to-scratch cell copies before *any* scratch-to-destination
commits, preserving loop-carried value swaps and simultaneous phi semantics.

The plan retains all source/function/block/SSA identities and rejects forged
IDs, type-width mismatches, duplicate targets, overlapping slots and
undersized scratch capacity. Tests cover signed EOF preservation, exact
reproducibility, synthetic cross-swaps and invalid frame/edge inputs.

An optional relocation check accepts a caller-supplied **final source
length** and a proposed frame base; it proves the entire 43-cell interval is
disjoint from graphical source code and inside N15 memory, without
wraparound. It rejects placements one cell below the source boundary or one
cell beyond the VM's last address. This is an address-range validator, not a
source-aware linker or a guest data initialization method.

No complete physical code/data layout or executable placement of these 43
cells exists yet. The planner does not simulate runtime branches or modify
values on the host; future guest instructions must implement the staged
copies and arithmetic and relocate real conditional/backward jumps.
Production `c2malbolge_json` continues to **refuse** publication *before*
launching its layout backend; the five-vector native C23 `-O0`/`-O2` oracle
and rejection gate still pass. This stage does **not** satisfy P2 guest-VM
parity or produce an MCTR-v1 program.

### Source-authenticated typed-to-ternary CFG composition (2026-11-18)

The actual `c2malbolge_json` executable now consumes the whole original
source-locked checksum's validated canonical MCTI and invokes
`lower_canonical_dynamic_cfg`. This compiler-owned adapter independently
decodes canonical typed IR and copies full function, block, SSA instruction,
terminator, phi incoming-edge, scalar type and source-span records into the
existing strict dynamic CFG lowerer. No test-supplied phi binding, host input
value, branch selection or source identity is used. The new source-to-plan
regression admits all seven blocks, three phi merges, signed `getchar()`
effects and output, rejects malformed typed bytes, and repeats identically.

The next prelink preparation now records the full incoming phi transfers on
every static predecessor edge, without evaluating a runtime branch. For the
original checksum the canonical graph yields four predecessor-specific edge
sets and six source-typed **simultaneous assignments**: two on entry, two on
the loop backedge, and one on each arm of the checksum merge. The subsequent
frame-relative planner now reserves disjoint guest-word slots and a scratch
bank for two-phase copies; these are still not placed or realized guest
instructions.

The source-C driver now reaches this **unlinked pre-layout plan** before
explicitly refusing publication, rather than refusing at the older typed
target stage. The explicit-backend boundary also now has an adversarial test: it feeds
the full normalized source-locked checksum to `c2malbolge_json` with a
nonexistent layout backend. The compiler still reaches its prelink stage,
refuses the unlinked CFG, and creates no target artifact; no backend process
is required to reject the unsupported guest state.

The original C23 `-O0`/`-O2` five-vector oracle and the
no-artifact refusal regression still pass. The next missing stage is **real
physical guest code/data placement and realized state/phi copy instructions**
with control/backedge relocation, followed by actual guest integer
arithmetic and five-stream normative VM parity.
Neither an MCTR-v1 image nor a runnable checksum has been produced; P2
remains open.

### Source-locked dynamic ternary CFG before guest linking (2026-11-18)

The full original mutable C23 EOF checksum now passes a **separate symbolic
ternary-CFG lowering** test. A frozen 1,572-byte canonical typed-IR wire is
derived from the accepted original Clang JSON and source witness, not a
hand-authored branch table. `lower_dynamic_typed_cfg` preserves seven
reachable blocks, all three SSA phi merges across two blocks, the exact two
signed `getchar()` effects, arithmetic, nested input-dependent branches and
final byte output. Its result retains original typed source provenance and
remains deterministic under re-lowering. Predecessors and incoming phi-edge
values are validated, SSA definitions must dominate ordinary and edge uses,
and forged CFG/source coordinates are rejected.

This new **unlinked `TernaryCfgPlan` is intentionally not MCTR-v1 and cannot
be submitted to the existing byte-trace target publisher**. It has no guest
instruction addresses, physical mutable-value allocation, backward jump
relocations, complete integer arithmetic realization or actual VM parity.
The old linear `lower_typed_ir` still refuses the checksum rather than
treating this symbolic graph as an executable artifact. The later compiler
composition now supplies the authenticated projection described above;
target control/phi realization and five-stream VM proof remain missing.
P2 remains open.

### Source-stage EOF branch candidate and independent admission (2026-11-18)

The previously test-only two-arm physical N15 branch is now assembled by
`build_signed_eof_branch_source` in the layout responsibility. It returns an
exactly position-encoded 132-cell graphical **candidate** for the current
profile, refusing foreign profile descriptors; it does not publish a C guest.
The existing 257-class traced VM regression (256 byte values, empty input,
and two additional multibyte streams) passes against the generated source.

A second bounded check supplies independent scalar 15-trit write oracles,
exact code paths and input/output events to the nonlinear layout verifier.
It admits EOF, NUL, `0x03 0x04 0x05`, and `0xff` with 119/175 steps and
correct branch markers/consumption. The original revisiting-only verifier
cannot accept the forward-only EOF arm, so the layout now exposes a
`admit_bounded_guest_path` entrypoint with identical strict guest checks
except for the mandatory revisit. The old API still rejects that EOF path
as `NotRevisiting`. Neither API simulates C state, accepts an unbounded
input language or bypasses independently checked guest execution.

The frozen complete C23 EOF checksum has been retried with its native
`-O0`/`-O2` oracle and still refuses at target lowering for phi-carried
mutable state and dynamic loops. There is no guest checksum or general
loop backedge; P2 remains open.

### One-read executable byte/EOF branch (2026-11-18)

The 132-cell N15 guest now executes **both branches without consuming a
second input**. An alternate virgin loader operand M[137]=125 lets the
fourth physical `p` move from C=69 to C=67. For all 256 successful
input bytes, its written control is 134; for EOF it is 377. The real
rotation moves from C=78 to C=76, following the unchanged C=72/73
pointer-reset pair. Two more actual `p` instructions read virgin
M[140]=7,174,341 and M[143]=125, collapsing both input classes to
final controls **44** (bytes) and **125** (EOF). The reached C=114 `i`
therefore branches to C=45 and C=126, respectively.

On the backward byte arm, C=57 emits `0x9a` and the already-encrypted
C=104 halts in 175 steps. C=69 is now a true source `o`, so its
second visit does **not** perform the unwanted `/` instruction. EOF
enters C=126 and emits `0x1e` before halting in 119 steps. A red-first
one-read regression failed against the earlier two-read layout, then
passed with the relocated fourth write. All 256 byte values, empty
stdin, and two three-byte streams ran in the normative profile VM,
starting from freshly validated states. The 257-class traced test
passed in 89.33 seconds under 176-step and 150-second ceilings; every
input executes exactly one physical `/` at C=53. The independently
computed trit oracle agrees with the two final jump controls.

**This is a single-decision guest classifier, not a byte-stream loop.**
The untouched suffix of each multi-byte stream remains available only
within that terminated guest execution; there is no next guest read,
mutable source-C checksum state, dynamic loop, or source-C lowering.
The frozen P2 checksum still refuses target lowering. The guest's
fixed branch marker bytes are not the checksum's oracle outputs, so
P2 remains open.

### Earlier two-read dual-arm relocation witness (superseded, 2026-11-18)

The earlier 132-cell physical signed-EOF branch handled **all 257 input
classes in the normative N15 VM**: empty stdin takes its own branch to
C=126, emits `0x1e` and halts at C=129 after 119 instructions. Every
single-byte input (`0x00` through `0xff`) takes a different real `i`
branch to C=45, emits `0x9a` and halts on the encrypted C=104 after
175 instructions. The frozen independent trit oracle continues to
predict controls 125 and 44, respectively. Each execution starts with
a fresh VM-validated state cloned from one complete loaded image;
257 traced runs completed in 90.98 seconds under a 150-second test
budget, with no per-case instruction count above 175.

This repairs the *previously physical* byte `0x03` failure, not merely
its mathematical oracle. After two extra real `p` writes, C=83/84
relocates through M[144]=7,174,350 and M[7,174,351]=134.
C=98 instead reads untouched M[148]=7,174,350 and advances through
loader cells to C=104, which rotates M[7,174,356] without disturbing
the subsequent C=105 reset via M[7,174,357]=134. The pointer then
advances to the written M[143] control at the reached C=114 `i`.
No reset reads the modified M[135]. The exhaustive test checks
physical data reads, selected branch, output, halt and input count.

**This layout was not a lossless byte-stream classifier.** The byte
arm re-entered already encrypted C=69 as `/` and attempted another
input read: two distinct three-byte vectors confirm it consumes their
first **two** bytes before halting. The later C=67/M[137] relocation
corrects this defect; this paragraph preserves its counterexample.
The code is hand-built guest evidence, not source-C lowering. The frozen
mutable EOF checksum still refuses in the real target backend: no C loop, mutable checksum state,
second-read continuation, or general C guest parity is established.

### Physical dynamic rotation after four crazy writes (2026-11-18)

For the `-}` 132-cell seed, the third arithmetic write has trit 5
(place 243) equal to 2 for every successful input and 0 for EOF.
The independent crazy table proves that **no possible fourth `p`
operand** can leave both classes with control words below 243, so
both branch destinations cannot fit within this 132-cell source.
This is a bound on the present four-write scheme, not on arbitrary
Malbolge branches or longer layouts.

A genuine N15 follow-on guest keeps the same four real `p` writes,
then reaches `*` with `D=139` and rotates the written control word.
The memory mutation yields 9,565,979 for every successful byte and
9,566,060 for EOF, shifting their difference from place 243 to 81.
The guest then executes `<` and `v`: empty, NUL, 1, 128 and 255
produce actual output `0x6c`, `0x1b`, `0x1b`, `0x1b`, `0x1b`,
respectively, in 81 normative steps each. It does not jump to either
rotated control word; both are well outside source memory and are
not valid branch destinations without further placement and reduction.
The independent digit oracle and reached `*` memory reads are checked
in `compiler_eof_short_branch_guest`. No mutable-C checksum guest
or complete executable EOF branch is claimed.

An independent two-`p` arithmetic proposal after that physical rotation
uses operands `[4,782,969, 0]`. A complete 257-input scalar oracle
collapses every byte to control word 40 and EOF to 121, which would
make hypothetical `i` entries C=41 and C=122 inside the 132-cell
source. One extra `p` alone cannot do this: rotated trit 13 is zero
in both classes and any crazy operand maps a zero accumulator trit
only to 1 or 2, leaving the result above 1,594,323. The two proposed
operands have **not** been prepared or read in a physical guest, and
C=41 is already traversed and encrypted by the present prologue.
The next experiment needs real operand synthesis, pointer relocation,
and a safe source skip/entry layout for both code arms.

### Earlier bounded two-arm counterexample (superseded, 2026-11-18)

The earlier 132-cell N15 byte/EOF experiment had a **separate physical**
post-rotation continuation. Its real `*`, two additional `p` writes,
`j` relocation chain and reached `i` at C=114 can enter two distinct
source arms. The independent 257-input scalar oracle uses virgin loader
operands M[140]=7,174,341 and M[143]=125 to predict control 44
for bytes and 125 for signed EOF. Actual guest traces confirm the
branch to C=45 for input bytes 0, 1, 2 and 255, and to C=126 for
EOF. The success arm revisits already encrypted C=104, which has
become `v`; it emits `0x9a` and halts after 175 steps. The EOF arm
executes its own `*`, `<` and `v`, emitting `0x1e` in 119 steps.

**This earlier source was not a 257-case guest discriminator.** The first
four-`p` classifier has mutated M[135]; the additional `j` loop
revisits that input-dependent cell. Input `0x03` causes the actual
normative VM to reject a non-graphical encryption destination at
7,174,350, even though the independent scalar control would be 44.
The counterexample is retained explicitly. Moreover, the successful
byte arm revisits an encrypted `/` at C=69 and **consumes a second
input** if present. A three-byte input verifies this unwanted effect.
No C source is lowered to these instructions; the frozen checksum
still refuses dynamic target lowering. P2 remains open until the
operand relocation is byte-independent, the second read is avoided,
and the complete C EOF loop obtains independent guest parity.

### One executable successful-input arm, EOF still unplaced (2026-11-18)

A separate **132-cell graphical N15 guest** adds a fourth physical `p`
operation ahead of an input-dependent `i`. An independent 257-case
15-trit oracle proves that operands `[7,174,341, 3,618, 7,174,350, 134]`
collapse every successful C23 `getchar()` byte to control word **125**
while signed EOF becomes **368**. Both are smaller than the previous
multi-million-word jump, but only one destination is yet executable.

Twelve genuine `*` rotations prepare M[135]=3,618. A reached `/`, a
`j` rewind through M[137]=125, and fixed no-ops position four real
`p` writes at M[134], M[135], M[136], and M[139]. A second genuine
`j` pair resets `D` to M[139] for the input-dependent `i` at C=78.
All 256 input bytes execute the real `i`, encrypt graphical M[125],
then enter a placed `<` at C=126 and `v` at C=127. Each guest emits
**`0x7d` in 81 normative VM steps** with one input byte consumed.
The test now runs 256 complete byte executions against one loaded N15
image through fresh validated VM states, rather than trusting only the
independent arithmetic oracle. Its focused Rust test passed in 87.44 s.

EOF also prepares word 368 at M[139], but the normative VM **rejects**
the attempted `i` transition: its self-encryption target M[368] is
non-graphical (7,174,341). This is an explicit error before the jump
commits, **not** a second executable arm or successful EOF handling.
`tests/compiler_eof_short_branch_guest.rs` checks all 257 physical
input paths, actual pointer and arithmetic operand reads, and an
independent 257-value digit oracle. No compiler-generated source-C branch,
mutable checksum loop, full binary-stream parity, or P2 acceptance is
claimed. The next
integration task is to arrange a safe executable EOF arm without
invalidating the loader seed or the reached byte arm, then lower the
frozen checksum CFG through the real compiler.

### Reached EOF-dependent guest jump, with unplaced arms (2026-11-18)

A new 132-cell graphical N15 program extends the physically executed
three-`p` EOF classifier with two genuine `j` data-pointer relocations.
After the last arithmetic write to M[137], the first `j` reads
M[138]=7,174,350; the second reads M[7,174,351]=134. Two reached
no-ops then advance `D` to 137. A real `i` at C=63 reads the **written**
M[137], selecting C=7,174,224 for every successful `getchar()` byte
or C=378 for EOF. An independent 257-case digitwise oracle proves the
control words; five normative 65-step VM traces establish signed input,
three arithmetic reads, both pointer resets, the reached branch and the
actual code-pointer change. `compiler_eof_prepared_branch_guest` owns the
regression, introduced in DCO commit `ea8dd932b`.

**Both destinations are unplaced**: each contains non-graphical loader
word 7,174,350, and the VM terminates with `NonGraphicalCell` immediately
after the branch. This proves a real, input-dependent `i`, not an
executable success or EOF arm, output, source-C CFG lowering, mutable
runtime state or the frozen checksum. P2 remains active until both arms
are laid out and real C parity passes.

The same source has now completed **257 normative VM executions** (all
256 input byte values plus empty input), each with 65 traced transitions,
the actual signed `/` input observation, physical `p` and `j` data reads,
a reached `i`, and the correct distinct unplaced destination. An
independent 257-case trit oracle checks the control word for each input.

The test loads the full 15-trit image once, then copies it into a fresh
*validated* VM state per input; it does not replace guest execution with a
host arithmetic simulation. The focused test completed in **94.38 s**
under a 100 s command budget on 2026-11-18. This expands finite coverage,
not the compiler's supported C surface or either executable branch arm.

### Physical all-byte versus EOF guest classifier (2026-11-18)

A new **132-cell graphical N15 guest** realizes a complete arithmetic
signed-EOF discriminator in the normative VM, using a distinct three-`p`
plan rather than the rotation-impossible two-`p` operand 728. The `-}`
source tail seeds loader-expanded memory at addresses 135..137 with
`134`, `7,174,350`, and `125`. Twelve real `*` writes to the first word
are followed by two actual `j` relocations per round, returning `D=135`.

The rotated first word is `3,618`. A genuine signed `/` and three reached
`p` instructions then read `[3,618, 7,174,350, 125]` in order.

An independent 15-trit truth-table oracle proves every successful C23
`getchar()` byte `0..255` maps to accumulator word `7,174,223`, while the
N15 EOF sentinel maps to `377`. The guest emits their low bytes `0x4f`
versus `0x79` and halts in **61 real VM instructions**. Five normative VM
runs (empty, NUL, `0x01`, `0x80`, `0xff`) check actual loader data, twelve
rotation reads, relocation operands, three `p` reads and writes, consumed
input and output. The witness lives in `compiler_eof_guest_control`.

This is a genuine guest arithmetic **output classifier**, not a reached
input-dependent `i`: both input classes take the same instruction path.
It is neither generated from source C nor integrated with the mutable
checksum's guest branches, runtime state or EOF loop. P2 remains open;
the next integration must relocate to a written discriminator word,
prove both `i` destinations and lower the frozen checksum's typed CFG.

A companion top-trit regression also rules out a **single** extra
`p` as a direct nearby branch-target converter: successful output word
`7,174,223` has top trit 1 while EOF word `377` has top trit 0. For
any possible additional operand digit, at least one next word retains
a nonzero top trit, hence is at least `3^14 = 4,782,969`. Longer
arithmetic synthesis and a physical control jump remain necessary.

### Loader-seed obstruction for a real EOF branch (2026-11-18)

The required physical operands cannot simply be read out of an untouched
N15 loader image. Every graphical source byte is at most 126, so trit index
5 (place 243) begins zero in both source-tail seeds. The loader recurrence
on that digit closes on 0 and 1: `crazy(0,0)=1`,
`crazy(0,1)=0`, `crazy(1,0)=1`. No unmodified source or expanded loader
cell can contain a 2 in this digit, regardless of source length or address.

This is also a *general* lower bound on any two-`p` arithmetic discriminator
that collapses all 256 successful bytes to one word. Byte 0 and byte 243
differ only at trit 5. A first operand trit 0 or 1 maps those values to
trits 1 and 0; the second `p` can make those equal only with operand trit
2. Alternatively, the first operand already has trit 2. Thus **at least
one operand needs an actual guest mutation** before the two `p` reads;
for the accepted `[14,348,906, 486]` candidate, both operands need it.
`mandatory_runtime_operand_writes` exposes these per-word necessary flags
without claiming a write plan, a source, a reachable `i`, or guest parity.
An independent 94-by-94 graphical-seed recurrence and the digit-table proof
exercise this barrier; the five-vector complete checksum still refuses at
real target lowering. Next work must synthesize operand state through real
`*`/`p` memory writes, then independently verify relocation and a branch.

### One-write EOF candidate with one real operand (2026-11-18)

A second exhaustive mathematical pair `[7,174,332, 728]` maps all successful
bytes to 728 and EOF to 485. Its necessary operand-write flags are
`[false, true]`. The first operand can actually come from `Q}` loader
seeds at source positions 36 and 37. A 38-cell N15 guest performs real
signed input, relocation, and an input-dependent `p` reading expanded
address 38; normative traces establish the read and resulting write on
EOF/NUL/128/255. No second operand or dynamic jump is placed, and the
complete mutable checksum still refuses target lowering. The next stage
must synthesize 728 in a safe guest cell and then prove both jump paths.

### Physical synthesis of the reduced plan's second operand (2026-11-18)

A new 91-cell graphical N15 guest **does** write `728` through a real
`p`, closing the earlier rotation-only preparation obstruction for a
*different* loader seed. Source-tail bytes `44/72` expand to
`M[95]=7,174,457`, `M[96]=72`, and `M[97]=7,174,493`.
An initial pair of `j` instructions relocates `D` from 1 to 40 to 95.
Eleven reached `*` instructions rotate `M[95]` to `7,174,777`;
ten sets of three real `j` instructions reset `D` through
`96 -> 73 -> 62 -> 95`, using source values `61` and `94` at the
intermediate cells. A no-op advances `D` to 97 and a reached
`p` computes `crazy(7,174,493, 7,174,777) = 728`.
The normative VM executes **48 instructions**, emits `0xd8`
(the prepared operand modulo 256) and consumes no input under
empty, NUL and high-byte stdin. The regression checks every operand
read and reset, the original and final memory cells, and a separate
digit-table arithmetic oracle.

This is a physical pre-read operand **preparation** milestone, not a
complete two-`p` EOF discriminator. Its `44/72` seed is distinct from
`Q}` (`81/125`), which directly supplies the required *first*
word `7,174,332` of the reduced `[7,174,332, 728]` plan. A new
independent arithmetic path shows the same `44/72` loader seed can
*also* yield that first operand: rotate its `7,174,493` word
fourteen times to `7,174,573`, compute
`crazy(7,174,493, 7,174,573) = 203`, and then
`crazy(36, 203) = 7,174,332`. A 257-case oracle verifies that the
resulting pair would distinguish all bytes from EOF. **These extra
operations are not scheduled or physically executed in one guest.**
A shared-source operand plan, input-dependent `p` writes, relocation
and a conditional `i` remain unsolved.
The frozen C checksum still refuses target lowering; P2 stays open.

### Both EOF operands prepared in one physical guest (2026-11-18)

A second 91-cell graphical source uses the same `44/72` loader tail to
prepare **both** reduced-plan operands in one normative N15 execution.
Eleven real `*` rotations and one `p` first write `728` at M[97].
A further rotation at M[95] and four reached `p` writes then leave
`7,174,332` at M[95], with the original `728` still intact at M[97].
The intermediate writes are `108` at M[95], `7,174,408` at M[102],
and `125` at M[103]; the final `p` writes `7,174,332` at M[95].

An 82-step normative guest trace verifies these exact addresses, reads,
mutations, and the `j` relocation chain after source cell M[62] is
encrypted. Four empty/nonempty input cases produce the same output
`0xbc` and consume **no input**. The independent 257-case scalar
plan proves the prepared words *could* classify bytes versus EOF;
**no signed read, two data-dependent `p` writes, or conditional `i`
is reached in this source**. The frozen mutable-C checksum still
refuses target lowering. Joint preparation is not a guest branch and
P2 remains open.

### Rotation-only synthesis cannot produce the second EOF operand

The reduced one-write pair also has a stronger, position-independent
obstruction. Its second operand 728 is six consecutive base-three 2 digits.
Every graphical source byte (33..126) has at most four 2 digits. In all
higher digit positions (4 through 14), graphical source cells contain only
0/1 and the loader `crazy` recurrence preserves that 0/1 set forever.
Consequently every untouched loader word has at most four 2 digits, while
`*` rotation can only permute digits. **No number of rotations of any
virgin source or expanded loader cell can become 728.** The finite
94-by-94 source-tail regression checks the invariant through eight loader
phases and all fifteen rotations. This excludes rotation-only preparation,
not actual guest `p` synthesis or other candidate operand pairs. A real
pre-read arithmetic write remains necessary for this candidate.

### Input-dependent guest branch with two physical crazy writes (2026-11-18)

A separate 136-cell N15 instruction-level experiment now executes an actual
input-dependent `i`, rather than stopping at the scalar branch proposal. An
initial `i` skips source cells 7/8 and 98 while encrypting cell 98, then a
real `/` consumes one byte. Two real `j` relocations reach the encrypted
source operands 81 and 43; consecutive `p` writes at passed code addresses
98/99 produce control words 6 (NUL) or 7 (byte `01`). A third `j` reads a
known scratch word 98 and repositions `D` on the newly written result. The
normative `i` consequently visits code address 7 (outputs `06`, then halts)
or address 8 (halts directly). Exact normative outputs are `00 06` and `00`
in 40 and 39 guest steps; both cases consume one byte.

This is genuine **dynamic guest branching**, including input-dependent data
writes, post-instruction encryption, a backward jump to previously skipped
code and two distinguishable output paths. It is deliberately **not** the
all-257-case signed EOF predicate: the operands are 81 and 43, not the
proposed 7,174,332 and 728, and other byte inputs/EOF are unsupported by
this finite witness. The complete mutable checksum still refuses target
lowering. `compiler_eof_guest_control` verifies the physical reads, control
addresses, paths, step counts and outputs without C-host simulation.

### Exhaustive EOF control-word algebra, not a guest (2026-11-18)

The *unchanged* complete mutable EOF checksum still reaches the seven-block
typed CFG but explicitly refuses at target lowering; the native C23 `-O0`
and `-O2`/no-publication two-test gate remains green. A focused N15
arithmetic experiment identified a potential **runtime EOF distinction**:
two successive `crazy` operations with data words `14,348,906` and `486`
map each of the 256 successful `getchar()` words to `243`, but the exact
signed EOF sentinel to `486`. The independently checked hypothetical
`i` continuation addresses are 244 and 487. The new
`admit_c23_eof_control_word_plan` checker proves all 257 cases with
explicit invalid-profile, operand, target, byte and EOF rejections; a
separate digit-table oracle agrees with the normative primitive.

This is **not** executable Malbolge branching. Neither operand has been
placed in live guest memory, and the final accumulator value has not been
written to the future `i` data cell. No reachable source, jump destinations,
parity branch, loop-carried state, mutable checksum arithmetic or guest
output is proved. Next P2 work must realize and independently trace the
physical `p` data writes, `D` relocation and conditional `i` before it can
use these words in the unchanged complete C program. The finite algebraic
proof does not change P2 status.

### Complete EOF checksum now reaches dynamic typed CFG (2026-11-17)

The *unchanged* frozen P2 C23 checksum (source SHA-256
`9ae147a9d0e824bafb9322ee4787cdc8a7f45cb84c3f8691ad74f9eef32553c7`)
originally refused the first `unsigned checksum` declaration at `29:5`.
The pinned Clang 22.1.8 normalized source has 58 preorder nodes. A new,
deliberately narrow original-C/source-SHA/complete-Clang-tree proof admits
this source's genuine **seven-block typed-IR CFG**, including signed
`getchar()`/EOF `-1`, two loop-carried phi values (`current`, `checksum`),
two different parity branches, runtime `u32` XOR/add, `+3` and `&255`, a
second signed read on the backedge, and one final byte output. No input
value is collapsed into a constant byte. The 1,572-byte MCTI record
re-admits under the independent typed validator.

A test-only interpreter of the *serialized typed instructions* checks those
branches and evolving values against an independently written checksum
oracle on the five frozen input vectors (empty, NUL, high, mixed, truncated
EOF), including input consumption. Clang UBSan C23 at both `-O0`/`-O2`
passes the same five input controls; twelve forged AST-node changes and
source omissions/edits refuse typed publication. The frontend suite passes
127 tests, including four new focused checks, and the frozen two-test
source/native-or-guest harness passes.

The real `c2malbolge.py --repository-tools --capsule` pipeline now **refuses
later**, with `guest layout rejected: dynamic EOF checksum control and state
unsupported`; it still creates **no** `.malbolge` artifact. The missing
capability is dynamic ternary/guest control flow and mutable arithmetic/storage,
not basic typed CFG syntax. The test-only interpreter and native C are
**not** a substitute for a real normative-Malbolge VM trace. P2 stays open;
this closed proof is one source/CFG witness, not a general C implementation.

### Structural signed-guard AST authentication (2026-11-17)

A red-first regression showed that the bounded signed EOF-safe reflexive
guard accepted forged normalized Clang metadata on its three compound
statements and the enclosing `if`. Although the original C source still
matched, inserted declaration, inline or storage metadata reached the
backend instead of causing a typed refusal. The source/Clang projector
now requires those structural nodes to have no nonstructural metadata.
All four new forged cases refuse without publication; the 123 adapter
Rust tests and the five dedicated signed C23 guest/source tests pass.
This is a verifier boundary repair, not guest-dependent branching,
mutable state or execution of the frozen EOF checksum at `29:5`.

### Signed EOF-safe algebraic C guard (2026-11-17)

A complete C23 `void emit(void)` reads one signed `int` from `getchar()`,
then selects different `putchar` literals through a checked `if/else` on
`(current - current) == 0`. The normalized Clang 26-node source, original
byte spans, same-local signed SSA identity, both side-effectful output
arms, and literal values are revalidated before a static arm is selected.
Both signed subtraction `x - x` and XOR `x ^ x` equal zero, including for
C23 `EOF == -1`; either `== 0` or `!= 0` can select the proved arm.
There is no runtime guest branch, evaluation of stdin on the host, or
false conversion of EOF to a successful input byte.

A real 15-trit Malbolge guest retains the signed `getchar` machine input,
then emits source-proved byte `0b` and halts. A second complete
`(current ^ current) != 0` source emits the opposite byte `05` in the
real guest. Each guest passes five binary/EOF streams, matching independent
UBSan C23 `-O0`/`-O2` executions. Four arithmetic/comparison
combinations preserve typed admission and two possible C byte results;
changed operands, conditions, nested effects, signed output aliases and
forged source identity refuse without publication. Nine separate forged Clang
operand, operation, effect, literal and ancestry fields also refuse before
calling the layout backend. This is a new bounded
symbolic-branch source capability, not general guest-dependent CFG control,
local storage or the still-refused mutable EOF checksum at `29:5`.

### Interleaved signed reads and unsigned updates (2026-11-17)

A complete C23 source declares an unsigned checksum and two independent
signed `getchar()` locals, with `checksum += 5U` between the reads and
`checksum ^= 7U` after the second read. The exact original source and all
27 pinned Clang nodes are authenticated before the typed adapter admits
the program. The source-local accumulator is computed in lexical order,
but both signed inputs remain distinct `GetcharI32` guest effects. The
source is SHA-256
`5b394b2594d443796dbe4469b7e5b9e7a4561678349b9b961cfc3459c6fbc908`.
The backend emitted a real 1,095-byte 15-trit Malbolge capsule that
performs both reads and outputs `0b` in six VM steps, including EOF
and five binary stdin vectors. Independently compiled UBSan C23 Clang
`-O0` and `-O2` output the same byte for all five vectors. An earlier
adapter run refused the program at its first `29:5` declaration, so
this is a new source-order/effect-preservation capability, not a
pre-existing accepted fixture.

The bounded gate permits one or two signed reads, one or two checked
literal-only unsigned `+=`/`^=` updates, and one independent byte
output. A second read may occur between the two updates, with complete
original-source body and Clang identity checks. Dynamic operands,
observable signed EOF conversions, additional input effects, extra
updates, forged AST identity and unproved operations must refuse
without guest publication. No local input value influences the
accumulator: this is **not** guest mutable storage, dynamic arithmetic,
EOF branching, or completion of the original P2 checksum. That source
still refuses declaration `29:5`.

### Ordered constant-only mutable updates with a real signed read

A C23 source now initializes an unsigned local to `7U`, performs an actual
signed `getchar()` and then executes source-ordered `+= 5U` and `^= 7U`
updates before `putchar((int)checksum)`. The checked result is `11`, whereas
commuting the updates would give `5`. The existing one-update source remains
supported by the same Clang/source-bound path. The new admission iterates
one or two pinned `u32` compound assignments, validates every original C
span and exact Clang subtree, uses `u32` wrapping semantics, and refuses
unimplemented operators, dynamic operands, extra effects and results above
`255`. The signed read is preserved as `GetcharI32`, not byte-projected.

Pinned native C23 `-O0`/`-O2` and the independently replayed normative
15-trit VM produce byte `0b` on EOF, NUL, high-bit and mixed stdin. The
1,087-byte guest halts in five steps; its byte is compiled from checked C
constant flow, not from host stdout. Mutations feeding the signed read to
arithmetic or output must refuse without publication. This is deliberately
**constant-only** source evaluation and still does not execute mutable
arithmetic in guest memory, handle a dynamic EOF branch or compile the
whole checksum. That frozen source still refuses declaration `29:5`.


### Two signed discarded reads before a constant (2026-11-17)

The complete source-C function `getchar(); getchar(); putchar(11);`
now preserves both independent C23 signed read effects through source-
authenticated Clang JSON, canonical typed and ternary IR, a six-step
graphical Malbolge guest, and normative VM replay. Pinned native C23
`-O0`/`-O2` parity is established on exhausted and binary stdin.
The source-identical `putchar(223)` program remains unsupported and
publishes no guest; the negative C23 oracle remains byte `df`.

The bridge no longer assumes that only byte 11 can be synthesized after
two reads. A finite search of 94 graphical no-op phases derives the exact
source-dependent loader word and identifies 36 distinct candidate output
bytes, not all 256. Bytes 4 and 157 have separately replayed actual
Malbolge guests with both signed input effects and EOF/short/long stdin.
The bridge still independently admits the exact positional source and
replays every accepted candidate in the normative VM before publication.
This expands a bounded independent-output effect, not C runtime arithmetic,
signed EOF-to-byte conversion, mutable storage, or checksum execution.
The full mutable P2 checksum remains refused at declaration `29:5`.

### Source-checked discarded input followed by an independent byte (2026-11-17)

A new closed mixed-effect C23 slice admits the complete source form
`void emit(void) { getchar(); putchar(11); }` with the original C bytes and
nine-node Clang preorder authenticated. The discarded signed `getchar()` is
lowered as `GetcharI32`, never as successful `ByteInput`; its result does not
flow into output. An independent typed `u8` literal reaches a target-level
`InputWord`, data relocation, loader-word rotation, `OutputByte`, and halt.
The layout is admitted from graphical source, checked against its loader
recurrence, and replayed by the normative VM on EOF/NUL/high-bit stdin before
publication. The full C frontend emitted a 1,087-byte five-step capsule.
Pinned native C23 `-O0` and `-O2` and the real Malbolge VM each emit `0b`
on empty, NUL, `ff`, and `0080ff` input. Missing or altered source and
forged call metadata reject before publishing an artifact.

This deliberately **does not** implement reading signed EOF for branching,
turning `getchar` into an output byte, general mixed I/O statements, or
mutable C storage. The frozen complete EOF checksum still rejects its first
mutable declaration at `29:5`; that P2 work remains open.

### Conditional signed C23 EOF output fails closed (2026-11-17)

A complete four-trip C23 source with `int current = getchar()` and parity-
selected arithmetic in two `putchar` arms published an actual 1,119-byte
nine-step guest emitting `6a6a6a6a` on empty stdin, whereas pinned UBSan
Clang `-O0` and `-O2` emit `ffffffff`. Nested guards and switch arms also
published the wrong EOF suffix. A successful-byte 256-case identity proof
is insufficient: C23 `getchar()` is an `int` that can return `-1` on EOF,
while raw Malbolge input leaves its profile's low EOF residue `0x6a`.

The normalized frontend now traces the Clang identity of a signed loop-local
`getchar` result through any descendant output expression, then follows the
output call back through conditional, compound and nested call ancestry to
that same loop body. It refuses signed EOF publication before the byte-only
projection and target writer. The same gate detects nested `for`-body
signed locals; five previously accepted double/triple-loop witnesses now
refuse instead of publishing an EOF-unsound guest. Two previously accepted
function-scope signed-input aliases feeding induction-selected outputs are
also refused: their apparent byte identities cannot prove EOF. A later
red-first test isolated two alias-only output variants: replacing the last
`putchar(first)` with `putchar(alias)` or `putchar(localcopy)` evaded the
direct binding gate and reached the layout backend. Native UBSan C23
`-O0`/`-O2` still writes `0xff` at empty stdin. The frontend now follows
Clang-anchored initializer reads through lexical `int` aliases and refuses
both variants before layout; five binary inputs and no-artifact checks pass.
This remains conservative taint refusal, not signed EOF conversion. Former
positive Rust source variants require explicit `Unsupported`;
all 123 frontend Rust tests pass. Five complete C23 programs exercise empty,
NUL, high-bit, `0xff` and mixed input with native `-O0`/`-O2` oracles and
either real guest parity or typed refusal without an artifact.

This **fail-closed gate only** covers source-authenticated signed locals
declared in an inspected `for` body (including nested loops) or directly
in the function body and used by an output call. It does not establish
all alias, predicate-only or otherwise indirect source forms are EOF-correct,
nor implement signed EOF-to-byte
conversion. The complete mutable EOF checksum still refuses its first
unsupported declaration at `29:5`. Earlier dated positive successful-input
examples below are historical evidence, not current EOF-safe capabilities.

### Nested signed `getchar` local in counted C loops (2026-11-17)

A source-authenticated two-trip C23 loop containing
`int current = getchar(); putchar(putchar(current));` reached the real N15
VM as a 1,103-byte guest that halted in seven steps but emitted `6a6a6a6a`
on empty input instead of C23's `ffffffff`. The counted-loop signed-local
preflight checked only the immediate `putchar` argument cast. Nested
`putchar`, arithmetic identities such as `current + 0`, and a direct
unsigned-char cast could bypass it and publish a wrong EOF byte. A
five-case C23 regression now checks these paths and a counter-selected nested
call against five binary streams, independent UBSan Clang `-O0`/`-O2`, and
either real-guest parity or typed refusal with no artifact.

The bounded Clang ancestry refusal now follows a signed loop-local reference
to an enclosing output call, refusing a direct loop-body output or nested
`putchar` composition even when a cast or expression intervenes. The old
five-output modular arithmetic fixture also correctly fails closed: its
successful-byte identity does not prove C23 signed EOF conversion. This is
one more **soundness gate**, not execution of a C EOF conversion or general
conditional arithmetic. Dynamic signed EOF output and the frozen mutable
checksum declaration at `29:5` remain unsupported.

### Direct signed `getchar` local in counted loops (2026-11-17)

A complete C23 one-trip `for` loop with `int current = getchar();`
followed by unconditional `putchar(current);` previously compiled to a
1,071-byte, three-step N15 guest. The real VM emitted `6a` on empty stdin;
pinned Clang C23 UBSan at `-O0` and `-O2` emitted `ff`. A two-trip variant
published a 1,087-byte, five-step guest emitting `6a6a` instead of `ffff`.
The new red-first test checks both loop lengths against five binary inputs
and independent native controls.

The source/Clang-anchored counted-loop signed-local gate now also refuses
direct outputs inside the loop body, not only outputs selected by a static
counter `if` statement. A preflight refusal produces no `.malbolge` file.
The historical successful-input-only unsigned bitwise and short-circuit
examples containing this direct output now also refuse rather than publish
an EOF-unsound guest; their typed tests and native C23 controls were
updated. All 123 normalized frontend Rust tests and the focused C23 Python
regressions pass. General guest signed EOF conversion, mutable C storage,
and the full EOF checksum (still refused at `29:5`) remain unfinished.

### Repeated guest writes followed by live ternary I/O (2026-11-17)

A complete 29-cell N15 graphical source with terminal loader tail `Z(`
retains the same expanded-memory pair at D=41/42 as the earlier `p(`
23-cell witness: initial data words `7174413` and `40`. After an initial
`j`, nine actual `*; j` pairs rotate the same data word and restore D=41;
the longer reached suffix performs genuine `/; p; <` guest instructions,
then halts in exactly 27 normative-VM steps. The real input goes into A,
`p` updates both A and D=42 using the independently checked ternary crazy
operation with operand `40`, and `<` emits the resulting accumulator byte.

The manual encoder and fixed-seed automatic planner produce byte-identical
source and source maps. Seven binary/EOF input cases across both regressions
cover empty stdin, low ternary digits, NUL, the high-bit byte, `0xff`, and
a multi-byte stream, with independent scalar trit, pointer, write, input-
consumption and output checks. This proves composition of repeated guest
memory writes with **input-dependent guest arithmetic**. The result of
`crazy(40, input)` does **not** implement C23 signed `getchar` conversion;
no mutable-C EOF checksum or general guest loop is emitted. The frozen
checksum still refuses declaration `29:5` without publication.


### Executable repeated loader-memory rotations (2026-11-17)

A source-loadable 23-cell N15 guest with terminal graphical tail `p(`
(ASCII `112, 40`) has loader words `7174413` at D=41 and `40` at
D=42. One source-encoded `j` moves D to 41; nine successive pairs of
`*; j` genuinely rotate D=41 and reset it through the untouched D=42
operand. The normative VM halts in 21 steps, and the exact before/after
values of all nine writes are independently checked for empty and binary
stdin. No input is consumed and no output is emitted.

The manual forward encoder already admitted this program. The automatic
planner wrongly rejected it because it required every future step to be a
literal instruction before previewing the fixed graphical loader tail.
Its narrowly scoped preview now admits future `AutoRelocate` steps only when
the final two physical steps are explicit post-halt `SkippedDataByte` seeds,
with no intervening `Jump` and with full independent final-source admission.
The two real-VM regressions compare automatic and manual artifacts exactly.
This is a genuine repeated guest data-write prerequisite, **not** the
previous C23 signed-EOF conversion pair, not compiled mutable-C storage, and
not P2 checksum acceptance: the frozen source still refuses declaration
`29:5` without publishing a guest.

### Non-unit counted-loop signed EOF publication (2026-11-17)

An accepted C23 `unsigned_stride_conditional_live_input.c` combines a
four-trip, step-two unsigned `for` loop, a local signed `getchar()` per
iteration, and counter-dependent one/two `putchar(current)` effects. The
actual 1,127-byte, ten-step N15 guest emitted `6a6a6a6a6a` on empty input;
native C23 `-O0`/`-O2` with UBSan requires `ffffffffff`. Four short binary
streams also expose the incorrect EOF suffix. The new complete native/guest
five-vector regression was red before the repair.

The source/Clang-backed counted-loop signed-local refusal no longer requires
unit `++` induction, because static loop finiteness cannot prove every
signed `getchar()` succeeds. Its expanded soundness gate also refuses six
older source-proven induction/branch shapes, including assigned, descending,
radix, remainder and selected-break loops that used to admit successful-byte
output but would publish incorrect EOF results. All 123 frontend Rust tests
and the two focused native/guest-or-refusal Python regressions pass.
This is deliberately scoped fail-closed behavior, not an implementation of
guest `putchar(-1)` conversion or the mutable EOF checksum (still refused).

### Direct counted-loop signed EOF publication (2026-11-17)

The previously accepted complete C23 `input_unsigned_loop.c` unrolls four
`putchar(getchar())` calls. On empty stdin its genuine 9-step N15 guest
published `6a6a6a6a`, while native C23 `-O0`/`-O2` requires `ffffffff`;
short streams exhibit the same wrong EOF residue. The red-first five-vector
regression records normative guest execution and two UBSan native oracles.

The adapter now recognizes a signed `getchar` nested inside a `putchar` with
a source/Clang-proven `for` ancestor, including conditional and unbraced
bodies. It refuses before successful-byte-only lowering, without guest
publication. The frozen golden source remains historical successful-byte
evidence, **not** proof that arbitrary stdin conforms to C23. This is a
scoped soundness fix, not a guest signed EOF conversion or general mutable
C support; the P2 checksum still refuses declaration `29:5`.

### Single-output signed EOF inside counted C loops (2026-11-17)

One complete C23 source now demonstrates that a **single** output of a signed
`int current = getchar()` inside `if (i == 1U)` in a bounded three-trip
`for` loop is not safe on an exhausted stream. The previously published
1,087-byte capsule executed five actual guest steps and emitted `6a`
for empty or one-byte stdin. Pinned native C23 `-O0` and `-O2` with UBSan
require `ff` there; the three-byte guest input produces the correctly
selected middle byte `80`. The earlier loop-local refusal erroneously
required two output calls in the same counter-selected arm.

The source/Clang-backed adapter now refuses the **first** matching
counter-selected signed-local output before any guest publication.
`tests/test_single_c23_loop_eof_publication.py` pins five byte streams,
independent native controls, a real guest check on successful compilation
and no artifact on typed refusal. All 123 adapter unit tests and the prior
four-read signed EOF publication regression pass. This repairs one unsound
bounded loop shape; it does not implement signed EOF conversion, general
mutable C locals or the frozen EOF checksum (still refused at `29:5`).

### Exhausted adjacent loader-only nine-rotation reset (2026-11-17)

The 257-case signed-EOF operand proof yields four source-tail candidates:
`Hy`, `Iy`, `Ky`, and `Ly`. Their first derived operand needs nine real
rotations while its adjacent untouched word is `121`. A `j` reading that
second word sets the post-instruction data pointer to **122**. Thus the
simple two-instruction `*; j` reset could revisit its first word only if
that word lives at address 122. For this particular adjacent-loader class,
phase alignment then requires source lengths `4, 10, ..., 118` (20 lengths).
All 80 candidate tail/length combinations fail actual 94-phase XLAT1 source
admission; the position-aware selector independently refuses all 20 lengths.
The result closes this **unmodified-seed, direct-reset geometry only**.

A genuine 91-cell `Iy` guest instead performs `j; *; j; j; j` at source
positions 40..44. The normative 15-trit VM traces D as
`40 -> 95 -> 96 -> 122 -> 158 -> 158`; its one `*` really rotates memory
address 95 and no other arithmetic cell. Unmodified loader values at
addresses 96, 122 and 158 are `121`, `157` and `157`, respectively.
The final `j` is a data-pointer fixed point rather than a reset to 95.
`tests/compiler/layout/eof_reset_geometry.rs` pins the 80 positional
refusals and 89-step real guest. Guest arithmetic that **writes a new
control operand**, a different conversion algorithm, or a more general
layout remains open. No nine-write guest or whole-C EOF checksum is claimed.

### Checked loader-tail selection and rejected pointer reset (2026-11-17)

The backend now exposes `select_rotated_loader_seed` for finite, position-
checked data placement. Given a physical source length, expanded operand
address, a bounded first-word rotation count and two exact resulting words,
it searches at most 8,836 graphical suffix pairs. Unlike an algebra-only
candidate search, the bytes must decode to loader-valid instructions at
their *actual* source addresses. It recomputes the selected profile's real
loader recurrence and never reports a hypothetical rotation as guest work.

The selector reproduces `Iy` for N15 length 91, address 95, nine rotations
and required adjacent words `(7138732, 121)`. Independent forward-layout
admission and normative VM checks retain exactly one actual rotation. A
potential reset loop at N15 source length 118, operand address 122 would
consume data word 121 to reset `D` back to 122 after `*`. However the only
candidate suffixes for that pair end in byte `y`, which decodes as invalid
`)` at source position 117; the bounded search rejects that geometry.
Both canonical profiles also pass exact unrotated source-tail data checks.
This is a concrete negative executable-placement result, not a guest EOF
converter or the missing mutable C checksum implementation.

### Graphical-loader-derived rotated EOF conversion operands (2026-11-17)

The negative result below applies only to **untouched** loader words. A new
constructive, independently verified candidate requires guest-side preparation:
a 91-cell source with 89 position-encoded graphical `o` instructions and the
graphical tail `Iy` passes the normative N15 loader. The two final source
cells are integers 73 and 121 at code addresses 89 and 90, with valid
position-dependent instruction decodes. Loader expansion at address 91 is
`7174404`, and at address 96 is `121`; each word agrees with a separate
digitwise three-valued crazy recurrence.

Rotating the word at address 91 **nine** trits to the right yields
`7138732`. Two consecutive `p` operations reading the derived pair
`(7138732, 121)` would preserve all 256 successful `getchar()` byte values
and map the profile's signed EOF accumulator to the required `0xff`.
`tests/compiler_eof_byte_conversion.rs` checks the normative source loader
and decode, all intermediate rotations against the independent trit formula,
all 257 scalar crazy outputs, the pure C23 admission checker, and an extra
rotation mutation that must fail. This is a source-derived *operand* witness,
not a generated instruction trace: the compiler cannot yet revisit the
first expanded word to execute those nine `*` writes, restore the data
pointer, or execute the two `p` operations with both words unmodified.

The four-read C23 loop therefore still has the same known guest EOF
mispublication, and the frozen mutable-EOF checksum still refuses its
first declaration at `29:5`. Neither source-C observable signed EOF
conversion nor the P2 stateful checksum has been implemented.

### Planned post-halt loader seeds (2026-11-17)

The automatic forward-padding layout can now take the exact two graphical
loader-seed bytes **separately** from a reached logical operation sequence.
`encode_auto_padded_forward_layout_with_loader_seed` preserves these source
cells after the final halt and marks their origins as `LoaderSeed`, without
adding fictitious logical instructions or confusing them with jump padding.
The original 91-cell `Iy` witness is reproduced exactly by an explicit `j`
and by `AutoRelocate`, with an independent VM execution and negative seed,
path and halt checks. This removes a source-mapping obstacle to later
operand construction; it still performs one rotation, not the nine required
for the tested adjacent two-`p` signed EOF operand pair. The complete C
checksum still refuses its first unsigned declaration, so P2 remains open.

### Exact post-halt loader-seed admission (2026-11-17)

A source-loadable backend increment now admits two exact graphical
loader-seed bytes **after** the reached final halt, without executing those
bytes. An independently admitted 91-cell `Iy` source performs one genuine
`j` relocation to expanded address 95 and one `*` write there. The
normative N15 VM traces 89 steps, source memory and the adjacent unchanged
word at 96 for empty and binary input. The algebraically valid adjacent
two-`p` operand pair is `(7138732, 121)`: the first operand starts as
`7174404` at loader phase four (address 95) and needs nine rotations,
while phase five (address 96) already contains `121`. The emitted guest
executes only **one** rotation, not nine; returning D for eight more writes,
followed by live signed-EOF input/p/p/output, is unimplemented. The
source-C checksum still fails at its first mutable declaration.

### Exhausted passive-loader signed EOF operands (2026-11-17)

The frozen mutable-EOF checksum still explicitly refuses its first observed
`unsigned checksum` local at `29:5`; independently compiled native C23
`-O0` and `-O2` controls remain the acceptance oracle. The previously
observed signed output bug in the four-read C23 loop was still active at
this study's completion. The later bounded refusal below stops publishing
this witness, but does not implement a valid `p`/`p` guest conversion.

A finite, broader passive-loader study now rules out a tempting short-cut for
that conversion. For each of all **8,836** graphical final-source-word pairs
(ASCII 33..126), the 15-trit loader recurrence is independently calculated
from its scalar crazy table. Each trit-pair transition has a transient of at
most one step and a period of two or three. Every expanded-word phase then
repeats within six transitions; checking 12 starts from positions 2..13
covers two full periods of *untouched adjacent loader operand streams*,
regardless of how far the code would have advanced.

`tests/compiler_eof_byte_conversion.rs` now exhausts these starts and every
chain length from **2 to 12** consecutive `p` operations: 1,166,352
seed/phase/length candidates. Four necessary observations (0, 1, 255 and
EOF) leave 64 candidates (16 each at lengths 4, 6, 10, 12), but all 64
fail the full independent 257-case C23 output oracle. No candidate converts
all successful bytes and signed EOF. The test also verifies the 12-word
recurrence directly for each seed. This is a **negative result only for
passive, unwritten consecutive loader words and the stated length budget**;
it says nothing about guest-constructed words, operand relocation,
non-consecutive addresses, or longer arithmetic programs. A real compiler
must still generate and independently validate those code/data effects, not
just assert that `87844` and `2551` are correct operand values.

### Source-ordered, unobserved signed local overwrites (2026-11-17)

A real compiler/guest regression now covers four complete C23 source forms
that initialize a signed `int` from `getchar()` and overwrite it with one or
more later `getchar()` calls **on the same source line**, optionally
interleaving another independently declared local or a final `return;`.
Previously the source-checked reassignment gate refused these forms because
it demanded a strictly *later line*, even though their exact byte spans,
Clang reference identities, source spelling and statement order prove the
assignment occurs after the initializer. The guard now allows the same line
without weakening those independent checks.

`tests/test_unused_getchar_local_guest.py` first reproduced all four
refusals, then validated the corrected pipeline: pinned C23 Clang UBSan
`-O0`/`-O2` over five binary inputs per source, real N15 guest capsules
with two or three signed `GetcharI32` effects, exact three/four VM steps,
and empty/high-byte stdin parity. The values are never observed; no C local
storage or EOF-dependent output is synthesized. Three companion full C23
programs that `putchar` the last signed local or a fresh unguarded signed
`getchar()` now return typed `Unsupported` with **no** guest published,
while independent native EOF output is `ff`. The fresh-output form was
first caught as a real 1,087-byte mispublication and repaired before the
byte-only projection. The frozen mutable EOF checksum continues to refuse its
first declaration at `29:5`; it requires *observable* runtime storage,
branching, arithmetic and EOF termination. This is bounded real guest
execution progress, not P2 completion.

### Exact N15 signed EOF-to-byte word plan (2026-11-17)

The existing accepted four-read C23 source
`unsigned_conditional_live_input.c` was compiled through the pinned Clang,
JSON adapter and layout into a 1,127-byte `malbolge-2026` capsule. The
normative VM ran ten steps on empty stdin and emitted `6a6a6a6a6a`, while
native C23 `-O0` and `-O2` both emit `ffffffffff`. Its unsigned loop counter
is statically bounded, but each `int current = getchar()` is still signed;
on early EOF, the source's five `putchar(current)` effects must convert `-1`
to an unsigned byte. Earlier direct/local EOF refusals did not cover this
nested loop. The source/Clang-backed frontend now rejects a bounded
unit-increment loop whose induction-equality branch repeats a signed
`getchar()` local in direct `putchar` calls. The formerly expected-failure
`tests/test_bounded_c23_eof_publication.py` is now a passing native C23
`-O0`/`-O2` and no-publication regression across five binary inputs.
This is a **scoped fail-closed repair**, not general signed EOF conversion:
other unguarded loop output shapes still require soundness work. Full-input
byte parity alone does not establish whole-source C23 correctness.

A constructive target-arithmetic prerequisite is now available separately:
for the exact current 15-trit profile, `p` with data word `87844` followed
by `p` with data word `2551` preserves the low byte of all 256 successful
input words and maps the profile EOF word (`14348906`) to `0xff`. The pure
`admit_c23_signed_output_word_plan` checker replays exactly 257 states
through the normative crazy primitive, refuses foreign profiles, invalid
operands and changed byte/EOF results, and returns only an **operand plan**.
`tests/compiler_eof_byte_conversion.rs` exhausts those 257 states against
an independent digitwise three-valued scalar oracle and rejects four
altered operand candidates. This implements neither host-computed guest
output nor a general C `getchar()` interpreter.

The crucial remaining step is **guest data placement**: those two large
operand words must exist at consecutive *reachable and unmodified* data
addresses when the VM executes two actual `p` instructions, despite loader
recurrence, data-pointer movement, and `p` writes. A search of all 8,836
pairs of printable loader seed cells found no suitable pair in any adjacent
positions of their first six derived 15-trit words, even when trying two
through six consecutive loader-word `p` operations. Therefore a directly
appended `input/p/p/output` trace cannot simply assume these operands were
provided by the loader. The existing layout checker still does not emit or
publish this conversion, and general runtime EOF branches, mutable local
state and the frozen checksum's input-dependent loop remain unsupported.

### Signed local `getchar` output at EOF (2026-11-17)

An additional complete C23 source exposed another **real guest miscompile**:

```c
void emit(void) {
    int current = getchar();
    putchar(current);
}
```

The pinned frontend and adapter previously published a 1,071-byte capsule
whose normative VM executed three instructions and emitted hex `6a` on
empty stdin. Native C23 outputs `ff`: the stored signed `getchar` result
is `-1` at EOF and `putchar` converts its argument to `unsigned char`.
The accumulator-only successful-byte backend cannot reproduce that result.
Storing a signed input in a C local does not remove its EOF behavior.

The source/Clang-checked adapter now refuses a bounded, straight-line
`int local = getchar();` followed by one or more output calls using that
local, with an optional source-authenticated `int alias = local;` and final
`return;`. Up to 128 discarded, source-ordered `getchar();` calls may also
precede the signed local without weakening this refusal. A discarded read
cannot turn a later C `-1` into a successful unsigned byte. The check
executes **before** the byte-only projection and
before other fallback adapters; it never treats a negative result as
permission to compile a different grammar. Other source forms not proved
by this checker retain existing compiler behavior and need independent
EOF audits; this is not general signed-local soundness or conversion.

`tests/test_signed_getchar_local_publication.py` pins nine complete
sources (direct, copied, repeated, discarded-read suffix, and three
pre-declaration read forms and two signed-local reassignments) and four
binary stdin vectors. Independent pinned Clang C23 `-O0` and `-O2` with
UBSan must match the explicit expected bytes; the guest either matches the same
oracle or the compiler returns typed `Unsupported` without publishing a
file. The frontend unit suite has 123 passing tests. The original mutable
EOF checksum still refuses its first declaration at `29:5`; this change
closes an unsound publication, not the P2 guest runtime gap.

### Signed discarded `getchar` guest execution and safe EOF refusal (2026-11-17)

A red-first public source-C test now compiles `void emit(void) { getchar(); }`
and two consecutive discarded calls through pinned Clang, source-authenticated
MCTI `Getchar` (`i32`), canonical MCTR `GetcharI32`, and a real
`InputWord`/`Halt` Malbolge layout. These are **real guest reads**, not
host-time input projection. The returned word is deliberately discarded:
EOF may leave the profile's signed sentinel in A because neither C nor the
published guest observes the value. The independent source SHA-256 is
recomputed, rather than trusting the normalized Clang digest assertion.

Both one- and two-read source programs publish target capsules, execute in
two and three real guest steps respectively, produce no bytes on empty,
`ff`, NUL and mixed input, and halt after EOF without needing a successful
input. The layout publisher independently checks the complete source and
read count under a certified adaptive VM geometry; it never assumes a
minimum stdin length. Rust admission tests reject changed C and forged
Clang call ancestry. The new Python publication suite checks both paths
with pinned native C EOF and the normative guest VM.

The independent C23 `-O0`/`-O2` oracle for direct
`void emit(void) { putchar(getchar()); }` still outputs `ff` on empty
stdin: C `getchar` returns `EOF == -1`, then `putchar` converts its
argument to `unsigned char`. The former successful-u8 bridge published a
1,071-byte capsule with output `6a`, the profile sentinel's low byte.
That **unsound publication has been closed** for the exact standalone
Clang/source shape: the source frontend now returns typed `Unsupported`,
and the regression is a passing fail-closed assertion, not an expected
failure. Other successful-byte trace modes still require successful input
and must not be interpreted as C signed-EOF semantics.

A subsequent red-first C23 experiment exposed incorrect real-guest `6a`
EOF output for `putchar((getchar()))` and discarded `getchar()` calls
before or after `putchar(getchar())`. Independent Clang `-O0`/`-O2`
output is `ff` in all cases. The source-authenticated refusal now also
recognizes up to 128 discarded reads before or after the one direct output,
and up to three enclosing parentheses on its signed `getchar()` argument.
Five complete C shapes, five binary vectors apiece, both pinned native
optimization modes, and no-artifact refusal are checked by
`tests/test_getchar_eof_publication.py`. This bounded refusal is not guest
EOF-to-byte conversion; dynamic-control semantics remain unfinished.

A further red-first native/guest comparison found two real EOF miscompiles:
`putchar(getchar()); return;` and `putchar(getchar() + 0);` produced the
profile EOF word's low byte (`6a`) rather than C's `ff`. In the first case
an inert terminal return had escaped the narrow refusal. In the second, a
semantically neutral C arithmetic wrapper escaped it. The bounded gate now
examines the normalized Clang subtree of one direct, source-ordered
`putchar` call to detect a nested signed `getchar` without assuming a
particular parenthesis or expression width; discarded reads and an optional
terminal return remain covered. This is conservative *refusal only*, not
runtime EOF lowering or a claim about arbitrarily nested controls.

Twelve source forms across five finite input vectors now independently
check
native C23 `-O0`/`-O2` output versus guest execution or explicit typed
`Unsupported` without publication. The failing `6a` guest output was
reproduced before the fix. The full checksum gate and all six focused Python
checks continue to pass, with the checksum still explicitly unsupported.

The complete mutable EOF checksum remains the P2 acceptance gate; its first
local declaration still refuses at `29:5` without publishing a guest.
There is no general signed EOF-to-unsigned-char output lowering, guest C
mutable storage, input-driven branches or dynamic EOF loop yet.

### Repeated signed C input-to-output at EOF (2026-11-17)

The same compiler/source-C pipeline incorrectly published a real 1,087-byte
five-step capsule for two adjacent `putchar(getchar())` calls. At empty
stdin, the normative guest emitted hex `6a6a` (the profile EOF word's low
byte) while separately compiled Clang C23 `-O0` and `-O2` emitted `ffff`
(C's specified `putchar(-1)` conversion to `unsigned char`). Three calls
similarly emitted `6a6a6a` rather than `ffffff`; an explicit terminal
`return;` did not repair the two-call mismatch. These were actual emitted
guest programs, not hypothetical or byte-array-only comparisons.

The source/Clang-bound refusal now recognizes up to 128 direct signed
`getchar`-to-`putchar` outputs, with bounded discarded reads before,
between, or after them and an optional terminal return. This rejects
instead of silently projecting signed `i32` EOF as a successful `u8`.
A red-first Python regression checks five complete sources across five
binary inputs against the independent pinned native C23 `-O0`/`-O2`
oracles, accepting only exact real-VM parity or typed `Unsupported`
without artifact publication. An older public source-C test that only
exercised full-length input was corrected to expect refusal for one,
three, and sixteen unguarded calls; an input-specific successful-byte
bridge remains a separate contract, not portable C EOF behavior.

The front-end's 123 Rust unit tests and both focused Python refusal tests
pass. This is a bounded **soundness repair**, not implementation of
signed EOF output conversion or guest-side branching. The frozen mutable
EOF checksum still fails at its first declaration; P2 remains open.

### Typed representation of EOF-aware C input (2026-11-16)

The portable version-one typed-IR now distinguishes
`Getchar { result, type_id }`
from the existing successful-only `ByteInput` operation. The new typed-IR
operation represents C's signed `i32` result: `0..255` after a successful
byte and `-1` on EOF. It has a separate canonical MCTI opcode (12), exact
`i32` admission, deterministic decoding, and negative tests for wrong result
types, unknown wire tags, and accidental publication by the successful-byte
Malbolge echo adapter. Existing `ByteInput` remains strictly `u8`; a
profile-specific EOF word must not be truncated into a fabricated C result.

The ternary pre-layout stage also preserves this distinction as
`GetcharI32 { result, span }` in canonical MCTR opcode 85. A validated
typed-IR `Getchar` is projected as a signed `i32`, its source coordinates
and SSA identity are retained, and invalid type projections or duplicate
SSA definitions are rejected. The raw/capsule artifact CLI rejects an
otherwise valid MCTR `GetcharI32` program before publication; it never
silently substitutes the successful-byte echo bridge. The independent
runtime C conformance exercises all 256 input bytes plus the EOF word,
invalid words, and unchanged caller state after invalid inputs. Source-bound
checkpoint restoration also refuses to replace `GetcharI32` with a valid
constant `i32` whose source coordinates, SSA and provenance still match.

The new discarded-result source slice above now executes the real guest
input operation even at EOF. General **observable** signed `getchar` results,
local storage, runtime branching and EOF-driven looping remain unimplemented.
The complete P2 checksum still fails before guest publication; no host
computation is substituted for guest semantics.

### Frozen mutable-C EOF checksum acceptance witness (2026-11-16)

`tests/compiler/c-frontend/accepted/mutable_eof_checksum.c` is the single
source-controlled P2 whole-program target, SHA-256
`9ae147a9d0e824bafb9322ee4787cdc8a7f45cb84c3f8691ad74f9eef32553c7`.
It performs runtime `getchar` until `EOF`, updates a mutable unsigned
checksum through guest-dependent parity branches, and emits one final byte.
The independent Python oracle in `tests/test_eof_checksum_pipeline.py` and
pinned C23 Clang UBSan `-O0`/`-O2` agree on five frozen inputs: empty =>
`00`, NUL => `03`, `ff` => `02`, `01 00 80 fe` => `8b`, and the
prematurely terminated `05 00 81` => `8d`. Native runs have a 10-second
per-process bound. The compiler has a 75-second per-process bound; any
future guest publication must pass every vector through the normative VM,
with at most 100,000 steps and 15 seconds per execution.

At the initial frozen acceptance probe, the pinned frontend accepted this
exact source, but the compiled JSON adapter refused at `29:5`, node 3,
with `Unsupported` and `unlowered C declaration-statement`. The newer
seven-block typed-CFG proof described above advances beyond that refusal,
but target lowering still fails closed without an artifact.
This is a **non-pass** for P2 until real VM parity is proved. It does not
establish guest EOF, storage or arithmetic. The test deliberately changes
from an exact
unsupported-stage assertion to guest VM parity if the compiler begins to
publish successfully. This frozen witness supersedes ad hoc rotating EOF
checksum probes; later work must repair the actual compiler gap rather than
switch to another static-byte echo variant.

### Source-proven switch case/default byte domains (2026-11-16)

A complete C23 EOF-driven checksum with mutable unsigned state, parity
arithmetic and an input-dependent `while` still refuses its first local
declaration. It publishes no guest artifact. A separate complete four-read
source program exposed a new structured-control gap: a `switch (current & 1)`
with `case 0` and `default` writes the input through `current & -2` and
`current | 1`, respectively. Neither output expression is a global byte
identity, but each is identical to the resident input on its C case domain.
The pinned frontend accepted this C23 program and the old adapter rejected
the source `for` statement before guest publication.

The typed adapter now admits one source-authenticated case/default switch
with a pure byte-domain expression, one `putchar` per label and explicit
`break` statements. Its verifier checks the complete original C spelling,
normalized Clang nodes, label integer and all source positions. It evaluates
the predicate over all 256 *possible* successful input bytes, checks both
output expressions only on their reachable case domains, and retains the
actual guest input and output rather than a host-predicted byte. Fallthrough,
extra effects, forged parent/position/label metadata and nonidentical outputs
refuse before artifact publication.

A 1,119-byte `malbolge-2026` capsule executes four actual VM reads and four
writes in nine steps. Twenty-nine seeded binary VM vectors agree with an
independent identity oracle. Pinned C23 UBSan `-O0` and `-O2` agree for
all 29 vectors of the accepted source and both nonidentity changed-output
and changed-label controls (174 native executions). The compiler refuses
both changed sources and a removed-`break` control without publishing an
artifact. This is neither general executable C `switch` nor arbitrary
runtime C arithmetic, mutable guest storage or EOF iteration. P0 remains
**pending**.

### Source-proven unsigned-byte conversion on guarded live input (2026-11-16)

The complete EOF-driven checksum with mutable state, input-dependent control,
and integer arithmetic still refuses at the first C declaration; no guest
artifact is published. A distinct complete four-read C23 program isolated a
valid output conversion absent from the source-to-typed adapter: the odd C
branch writes `(unsigned char)(current + 256)` and the even branch writes
`(unsigned char)(current - 256)`. Both offset expressions are defined signed
`int` arithmetic for every successful `getchar` byte, and C unsigned-char
conversion reduces either value modulo 256 to the original input byte.

The new bounded proof authenticates both exact Clang cast nodes, the original
`(unsigned char)` spelling, the nested pure signed arithmetic and each guarded
branch's 256-byte active domain. It retains four real VM input instructions
and four corresponding output instructions instead of substituting host data.
An independently verified 1,119-byte capsule executes nine normative guest
steps. All 29 deterministic binary guest inputs, including zero and high-bit
bytes, match the independent byte oracle. Pinned C23 UBSan `-O0` and `-O2`
confirm both the accepted source and a valid changed-offset negative source
across the same 29 vectors. The changed source and forged Clang narrowing
refuse without publishing a guest artifact. This is a finite byte-equivalence
proof, not runtime guest arithmetic, general integer conversions, mutable
storage, dynamic guest branching or EOF iteration. P0 remains pending.

### Multiple ordered guarded C outputs (2026-11-16)

A complete mutable, EOF-driven checksum still refuses its first C local;
no guest is published. A separate complete four-read C23 program exposed
another bounded but real compiler gap: two successive `putchar` calls in
each of two byte-guarded `if` arms. The odd C path writes `current | 1`
twice, and the even path writes `current & -2` twice. Neither expression
is a byte identity for all possible inputs, but each is an identity on
its source-proven active path. The initial adapter refused the enclosing
`for` because it only allowed the final guarded output in an arm.

The verified proof now allows multiple source-ordered writes only when
all earlier statements in the arm were pure writes of the resident byte.
Every original call, Clang node, semicolon, indentation gap and 256-value
guard-domain identity must independently verify. New input, assignments,
control exits and hidden effects cannot be erased under this exception.
The 1,151-byte capsule executes four real guest reads, eight writes and
thirteen VM steps. All 29 seeded binary input vectors matched the
independent two-copies-per-byte oracle; pinned C23 UBSan O0/O2 accepted
and second-write changed-byte negative controls matched separately for
29 vectors each. The changed C refuses guest publication. This is not
runtime guest branching, mutable storage or EOF control. P0 is pending.

### Authenticated multiline `else if` byte domains (2026-11-16)

The full source-C EOF checksum, with mutable `unsigned` state, a `while`
and parity-dependent arithmetic, again stopped at its first declaration
without publishing a guest artifact. A separate complete four-read C23
program exposed a source statement-form gap: chained `if` / `else if` /
`else` conditions branch over disjoint low-bit input domains. The three
unbraced C expressions (`current | 1`, `current | 2`, `current & -4`)
preserve their resident input only on their own reachable branches.

The Clang `else if` child starts five columns after the indentation of
`else`; its child `putchar` and terminal `else` align with the outer
conditional, not the child `if` token. The source-bound verifier now
checks this exact byte/column geometry and carries each 256-byte active
domain through the entire chain before proving output equivalence. The
normative VM executes four real reads and four writes in nine steps from
a 1,119-byte capsule. Twenty-nine seeded binary guest vectors match the
independent identity oracle, and pinned C23 UBSan `-O0`/`-O2` verifies
the admitted source and two changed-byte rejected controls over those
29 inputs each. This remains source-proven removal of equivalent arms,
not runtime guest C branching, storage, arithmetic or EOF iteration. The
P0 contract stays pending.

### Unbraced C guard-domain output (2026-11-16)

The complete EOF-driven checksum program still refuses its first mutable
`unsigned` local without publishing a guest. A separate complete four-read
C23 experiment exposed a source statement-form gap: when the odd input arm
writes `current | 1` and the even arm writes `current & -2`, neither
expression preserves all possible bytes, but each preserves the byte on its
own authenticated path. The initial compiler refused the whole `for` loop
solely because neither output arm used braces.

The finite source/Clang proof now admits these direct `putchar` calls, checks
all 256 successful input values for definedness, and restricts byte identity
to the source-proven branch domain. Both same-line `if`/`else` and canonical
four-space-indented multiline C arms retain actual guest I/O. Multiline
separators are verified against exact original source bytes: the predicate's
`)`, a newline, the statement indentation, the first call's semicolon, and
the independently indented `else` and second call. The enclosing compound
statement must distinguish an unbraced call's semicolon from a braced `if`
terminator; otherwise its next-statement geometry is wrong.

Both admitted programs emit four real reads and four writes in nine guest VM
steps, preserving NUL and high-bit bytes rather than assuming host stdin.
Both source forms passed 29 seeded binary guest vectors each and independent
pinned C23 UBSan `-O0`/`-O2` parity checks for accepted and rejected
changed-byte C programs. This is source-proven elimination of output-
equivalent branches, not general executable guest arithmetic, storage, EOF,
or input-dependent branching, and P0 remains **pending**.

### Nested C byte-guard intersections (2026-11-16)

A complete EOF-driven checksum with mutable unsigned locals, an input-driven
`while` loop and parity-selected arithmetic still refuses at its first
`unsigned checksum = 0U` declaration. No guest artifact is published.
The next red-first complete C experiment isolates an additional boundary:
a four-read finite `for` loop with two nested input-dependent `if` statements.
The inner true arm preserves the input only where its low two bits are `11`;
the false arm preserves it only where they are `01`. The outer false arm
preserves every even byte. These three arithmetic expressions are not all
identities outside their individually reachable source-C paths.

The source/Clang-authenticated proof now intersects each verified C guard's
complete 256-value truth set with its ancestors' active input domain.
Nested statement arms inherit those constraints, and each reachable pure
`putchar` expression must return the original byte modulo 256 on its active
set. Undefined C arithmetic still refuses even on inactive branches;
additional reads, writes and mutations cannot be erased by this proof.

The pinned frontend, typed lowering, layout emitter and normative guest VM
admit a 1,119-byte capsule with four actual reads, four writes and nine VM
steps. A reproducible 29-vector binary guest suite passes, including NUL and
high-bit inputs. Native C23 Clang UBSan at `-O0` and `-O2` independently
agrees for all 29 vectors. A valid-C single-arm mutation changes the byte
where the low two bits are `11`, matches both native controls, and is
rejected before guest publication. Modified source and normalized Clang
operators also refuse. This proves only byte-preserving output identities;
execution of general runtime C branches, arithmetic, storage and EOF loops
remain unsupported, so P0 is still pending.

### Path-sensitive C output byte identities (2026-11-16)

A complete four-read C23 program uses `if (current & 1)` to choose signed
arithmetic output expressions that each preserve the live input byte **only
within the branch where the C expression executes**. The previous
source-to-typed adapter refused the complete source `for` body. The revised
projection authenticates the pinned Clang predicate and both pure output
expressions against the original C bytes, retains the exact truth set over
all 256 successful input values, and checks defined integer arithmetic
throughout that domain. Byte equality is proved separately for each active
arm. Only after the two source-proven branches have identical single-byte
effects does the compiler erase their dynamic control; four real guest
reads and four guest writes remain.

The pinned frontend, typed adapter, layout publisher and normative VM now
emit and execute a 1,119-byte capsule in nine guest instructions. A fixed
29-vector binary-input suite matches an independent four-byte oracle,
including NUL and high-bit bytes. The same source and its valid-C control
that changes every even input byte match separately compiled C23 UBSan
`-O0` and `-O2` oracles for all 29 vectors. The nonidentity C control,
modified source/Clang operator evidence, and unsupported effects refuse
rather than publishing a guest. This is a total-domain proof of
byte-preserving *output* in existing finite I/O loops, not general
runtime C arithmetic, execution of input-dependent C branches, persistent
guest locals or EOF-dependent loops. P0 remains pending.

### Source-authenticated modulo-256 C output (2026-11-16)

A fresh complete C23 checksum source with mutable locals, an EOF-driven
`while`, parity-selected output and arithmetic still stops at its first
`unsigned checksum = 0U` declaration. No artifact is published. A
separate bounded four-read C23 program exposed a different admitted-byte
semantics gap: reachable pure `putchar` arguments can differ as signed
integers but write the same unsigned byte as the current guest input.

The adapter now reuses its source/Clang-authenticated total byte expression
proof at the output boundary. It checks all 256 successful input values,
rejects any undefined arithmetic or different byte after conversion modulo
256, and retains only the actual guest input/output effects. This supports
examples including `(current + 256) & 255`, `0 + current`,
`current ^ 256`, `current - 256`, and `current * 257`, with no guest byte
prediction and no hidden calls or assignments. Unlike unreachable-arm
elimination, these are actually executed source-C output expressions.

The pinned C-to-Malbolge pipeline emits a 25-byte raw guest program with
four live reads, twenty exact writes and 25 VM steps. Twenty-nine seeded
binary-input VM vectors plus the suite's canonical-width boundary match an
independent per-byte oracle; two C23 Clang UBSan optimization levels match
all 29 vectors each. Forged Clang operator, type, literal and local binding
metadata reject, as do changed-byte C output and signed-overflow controls;
failed compilation publishes nothing. This is an output-conversion proof,
not executable guest arithmetic, general mutable C locals, runtime branches,
or EOF-driven iteration. P0 remains pending.

### Source-proven dead integer arithmetic (2026-11-16)

A full EOF-driven checksum C program with mutable unsigned state, a dynamic
parity branch, arithmetic, and output was attempted first. Its initial
`unsigned total = 0U` declaration still refuses before typed lowering, and
no Malbolge guest is published. General dynamic state, EOF loops, and guest
branching remain outstanding.

A separate four-read C program exposed a narrower supported-behavior gap:
inside a proven unreachable arm it called
`putchar((current + 1) * 2)`. Previously this pure arithmetic expression
stopped the frontend's finite-loop proof. The source-authenticated lowerer
now reconstructs the exact pinned-Clang integer expression, verifies every
operand and result across all 256 successful guest input bytes, and drops
only the unreachable effect. It does not evaluate reachable C arithmetic in
the host or synthesize a guest arithmetic instruction.

The 1,183-byte capsule produces twelve exact guest output bytes in 17 VM
steps. Twenty-nine seeded binary guest vectors plus a canonical-width
boundary match an independent oracle, including NUL and high-bit bytes.
Pinned C23 Clang at `-O0` and `-O2` with UBSan independently matches both
the older dead-literal and new dead-arithmetic sources on 29 vectors each.
Modified C operators, operand values, and normalized AST ancestry refuse;
the equivalent C programs with a reachable or input-dependent arithmetic
arm also refuse publication. The P0 remains pending on general guest state,
input-dependent control flow, and EOF-driven iteration.

### Reflexive live guest SSA predicates (2026-11-16)

A complete four-trip source-C probe with a live `getchar()` and a self-
comparison was attempted before typed-IR changes. A source branch whose
unselected arm calls `putchar(0)` still fails normalization at its enclosing
`for` (a reduced no-loop source fails at the local declaration), and no guest
artifact is published. The same source with independently authenticated,
identical byte-output arms compiled to 1,119 guest bytes and produced four
correct outputs in nine normative VM steps for three binary vectors, including
NUL and high-bit input. That C success uses existing pure-arm equivalence,
not the new typed-IR proof.

The typed CFG lowerer now proves signed and unsigned 32-bit comparisons of
**the same live SSA word** to itself: `==` and `<=` select true, `!=` and `<`
select false. Eight positive typed-IR cases preserve a guest byte read,
conversion and comparison operations, canonical typed/ternary wires, selected
output effects, and source-bound checkpoint identity. Eight independently
read, well-typed operand pairs still refuse effect-divergent control; they are
not assumed equal even if some input vectors happen to match. Runtime guest
branches, source-C dead-arm constant emission, persistent mutable locals and
EOF loops remain outside this proof. P0 stays pending.

### Source-authenticated live-byte algebra (2026-11-16)

The complete `unsigned_byte_algebra_live_input.c` program combines XOR
cancellation, signed 32-bit arithmetic, logical AND and two sequential C
branches inside a four-trip unsigned induction loop. Each predicate is
source- and Clang-bound and is total across all 256 successful input byte
values. The compiler preserves four real reads and twelve writes instead of
predicting an input value. The 1,183-byte capsule produces three copies of
each byte in 17 normative VM steps for both ASCII and mixed NUL/high-bit
inputs. Source and normalized-AST operator forgeries are rejected.

A fresh 29-vector replay passed actual guest output and 17-step counts with
trusted adaptive-width selection. Eight vectors separately passed the
canonical-width guest VM, including NUL and `0xff` boundaries. The source
identity matches its pinned C23 golden, and Clang `-O0`/`-O2` UBSan agrees
with the independent oracle across all 29 vectors for both the admitted
source and its rejected input-dependent control. The 13-source canonical
matrix has not completed; these are bounded stream proofs, not EOF support.

A paired valid C23 control replaces one cancellation identity with an
input-dependent parity test. The frontend can normalize that C, but typed
projection refuses rather than publishing a guest program. This is
compile-time proof of invariant output effects, not runtime guest control.
The broader seeded binary VM matrix is tracked separately from these
bounded witness executions.

### C23 radix threshold boundary and exact guest I/O (2026-11-16)

The whole `unsigned_hex_threshold_live_input.c` source contains four live
successful `getchar()` calls guarded by `current < 0x100`. Its authenticated
signed-C23 hexadecimal literal is greater than every possible successful
byte, so all four trips take the two-output arm without predicting stdin.
The pinned compiler emits 1,151 bytes of guest code. Twenty seeded input
vectors, including all-zero, all-`0xff` and mixed high-bit bytes, produce
eight correctly duplicated output bytes in thirteen normative VM steps.
A same-width source mutation to `0x0FF` makes the arm genuinely dependent
on the byte value: compiler publication refuses, while independent pinned
Clang C23 UBSan at `-O0` and `-O2` produces seven bytes for an input
containing `0xff`. The parity harness now asserts fixture uniqueness and
refuses unknown stems instead of silently applying a different oracle.
These checks do not establish runtime guest-dependent branches or EOF loops.

### Nested C alias identity and accumulator invalidation (2026-11-16)

A complete two-level unsigned C program carries one successful `getchar()`
through outer names and a loop-local identity copy. Both original and copied
names produce the same guest SSA byte: one actual read, four outputs, six
normative VM steps (`A` becomes `AAAA`). A paired nested-control program
executes four fresh reads after an unused initial read and writes only the
new bytes: five input effects, four output effects, ten VM steps (`ABCDE`
becomes `BCDE`). Source/C23 AST identities bind each use to its declaration.

The paired negative remains valid native C but tries to write the original
byte after those fresh reads; compilation refuses without publishing a guest
artifact rather than inventing persistent C local storage. Independent
pinned Clang 22.1.8 C23 O0/O2 UBSan oracles match 29 binary vectors for
all three original programs. Both accepted programs match 29 more actual
Malbolge VM executions each, including NUL and high-bit bytes. Source-token
and normalized declaration-reference mutations refuse typed projection.
Runtime guest-dependent control, independent mutable locals, EOF loops and
arbitrary byte streams remain outside the admitted slice; P0 remains open.

### Three-level source-authenticated induction with live I/O (2026-11-15)

A complete C23 program uses three nested unsigned loops, a live `getchar()`
local and a three-counter Boolean branch. The pinned frontend initially
refused its outer `for` statement because the bounded induction proof supported
at most two nested loops. A red-first pinned-Clang regression captured the
missing scope; the typed adapter now retains two source-authenticated ancestor
counters, each with its own Clang declaration binding, type and current value.
Every predicate leaf is proven against the matching counter, and forged source
operators or Clang ancestor bindings refuse admission.

`triple_induction_live_input.c` reads eight live guest bytes and writes nine,
duplicating only the sixth. Its real `malbolge-2026` VM trace is 18 steps:
`ABCDEFGH` becomes `ABCDEFFGH`. Pinned Clang 22.1.8 C23 UBSan at both O0
and O2 matches the actual guest on ASCII and binary bytes, including NUL and
high-bit inputs. A seeded 29-vector actual guest replay compares the entire
stream to an independent per-trip oracle. Its formerly six-byte fixed binary
boundary was corrected to cover longer input counts without implicit EOF.
The implementation remains bounded to three finite nested
loops and 16 trips per loop; it neither guesses guest stdin nor implements
runtime C branch conditions or arbitrary streams. P0 remains open.

### Nested unsigned counter predicates with live guest I/O (2026-11-15)

A complete six-read C program with nested unsigned `for` loops initially
compiled when an inner `if` tested its own induction counter, but rejected
when the same branch tested the still-in-scope enclosing `row` counter.
A red-first pinned-Clang regression exposed the missing source-time counter
scope. The finite induction proof now carries the immediately enclosing
counter through a nested loop and re-authenticates its exact source name,
Clang declaration reference, type and predicate before selecting output.
A second red-first whole program required both counters in the same Boolean
expression, `row == 2U && col == 1U`. The recursive predicate walker now
proves each comparison against its own counter instead of assuming all
leaves refer to the nearest loop.

`nested_outer_induction_live_input.c` reads six actual guest bytes and writes
eight, duplicating the third and fourth bytes. Its real Malbolge program
executes fifteen VM steps; `ABCDEF` becomes `ABCCDDEF`. The mixed-counter
program reads six and writes seven, duplicating only the third byte; its
guest requires fourteen steps and produces `ABCCDEF`. Both behaviors depend
on source-time finite induction selection, not guest-input prediction.
Pinned Clang 22.1.8 C23 UBSan at O0 and O2 agrees on the binary input
`00 ff 80 01 7f 32`. The six-source seeded integration suite recompiles
pinned C and passes 174 actual VM input vectors, each against an independent
oracle; its reachable-undefined-arithmetic negative also refuses publication.
Source operator and Clang counter-identity forgeries refuse before guest
publication. These checks extend only the already bounded two-level finite
loop grammar. Guest-dependent branch selection, EOF and general runtime C
state remain unimplemented; the P0 stays open.

The follow-up `triple_control_live_input.c` exercises a selected
`continue` in the deepest loop and a later inner `break` without terminating
its two enclosing loops. Seven actual reads produce eight writes in 16
normative VM steps: `ABCDEFG` becomes `ABCCDEFG`. A separate seeded 29-vector
replay agrees with a per-trip oracle; pinned C23 Clang 22.1.8 UBSan at O0/O2
agrees on ASCII and binary input. Forging the original `break` keyword to a
same-width `false` refuses. This is existing finite control selection, not a
new guest runtime loop implementation.

### Unsigned arithmetic predicates with live guest bytes (2026-11-15)

The complete five-trip C program
`tests/compiler/c-frontend/accepted/unsigned_modulo_live_input.c` combines an
unsigned induction counter, a new runtime `getchar()` byte on each trip,
`i % 2U == 0U`, double `putchar()` on even trips, `continue` and a selected
final `break`. The pinned Clang frontend initially rejected its `for` node;
a simpler signed-style comparison with the same control effects succeeded.
A red-first normalized regression isolated the missing `u32` arithmetic
predicate proof. The adapter now checks unsigned operation/cast/reference
ancestry, the exact `U`-suffixed decimal operand and original C tokens before
selecting output effects. These are source-time counter calculations, not
host-time folding of the live input byte.

The unsigned intermediate remains an exact 32-bit value for `+`, `-`, `*`,
`/` and `%`; addition, subtraction and multiplication use C's unsigned
modulo-2^32 semantics, and division/remainder by zero never supply a value.
The second whole C program
`tests/compiler/c-frontend/accepted/unsigned_wrapping_predicate_live_input.c`
proves `i - 2U > 99U` at `i == 1U`: `1U - 2U` is `UINT_MAX`, so the first
live byte is doubled. Signed arithmetic would choose the wrong guest trace.
Source and pinned-Clang operator, literal, binding and type forgeries refuse.

The real `malbolge-2026` VM emits `ABBCDDE` for `ABCDE` in 13 steps and
`AABCD` for `ABCD` in 10 steps; binary witnesses `00 ff 80 01 7f` and
`00 ff 80 01` respectively emit `00 ff ff 80 01 01 7f` and
`00 00 ff 80 01`. C23 Clang 22.1.8 with UBSan at O0 and O2 independently
agrees. An automated, seeded 29-vector input matrix per source recompiles the
original C through all pinned stages and compares real VM stdout with an
independent modulo-2^32 C oracle, including NUL and high-bit bytes.
Unsuccessful reads, input-dependent branch effects, arbitrary streams and
general guest runtime C arithmetic/control remain unsupported; P0 is open.

An additional source-proven unsigned short-circuit probe validates that
`i == 1U || i / 0U == 1U` skips its undefined divisor, then a selected
`break` ends the loop before any later evaluation. The real guest VM emits
one live byte in three steps. The counterpart `i == 2U || i / 0U == 1U`
would evaluate a zero divisor and is rejected without a guest artifact.
Clang/source forgeries inside the skipped arithmetic subtree also refuse.
The seeded matrix includes this third C program and a negative publication
check, for 87 real guest input vectors across three programs.

### C23 unsigned radix literals with live guest I/O (2026-11-15)

A complete five-trip input/branch/loop C program initially refused when its
unsigned initializer, bound, non-unit-capable compound step, remainder operand
and equality guards used source C23 binary, octal or hexadecimal integer
spelling instead of normalized decimal tokens. The new source-backed proof
compares Clang's canonical `u32` value with the original bounded integer
literal using the shared C23 token parser. It authenticates the exact `u`/`U`
suffix, source coordinates, type and AST ancestry before selecting effects;
changes to a source digit, prefix or normalized value refuse admission.

The pinned Clang 22.1.8 frontend, typed IR, verified layout and normative
`malbolge-2026` VM now replay `unsigned_radix_live_input.c` with five live
reads and seven actual writes: `ABCDE` becomes `ABBCDDE` in 13 VM steps.
Binary input `00 ff 80 01 7f` becomes `00 ff ff 80 01 01 7f`; native
C23 Clang 22.1.8 UBSan at O0 and O2 independently agrees on both vectors.
The seeded real-guest matrix now covers 116 input vectors across four whole
C programs, including NUL and high-bit bytes. This extends a bounded
source-time unsigned counter proof, not dynamic guest C arithmetic, variable
byte-dependent branches, EOF or arbitrary-length streams. P0 remains open.

### Source-proven early unsigned exits before wrap (2026-11-15)

A demanding source-C probe combines unsigned `9U; i > 0U; i -= 2U`,
a live `getchar()` local, a counter-selected duplication branch and a
`break` when `i == 1U`. The pinned Clang/JSON adapter originally refused
its `for` statement because the mathematical fifth post-body decrement
would underflow, even though C does not execute an update after `break`.
A red-first normalized regression now moves the unsigned-wrap check after
source-proven body-exit selection. A normal trip or `continue` still checks
the update, including the final trip; `break` and `return` skip it.

The related inclusive-zero source `for (unsigned i = 4U; i >= 0U; i--)`
was also initially refused despite a selected break at zero. The new proof
accepts this finite case but continues to reject its `continue` counterpart,
which would execute the underflowing decrement and leave the guard true.
A second red-first regression detected that a source-backed Clang `break`
node could be admitted when the five original C keyword bytes were changed
to `false`. The control-exit proof now authenticates `break`, `continue`,
and `return` source tokens before selecting their effects.

Both positive complete C programs compile through the pinned native Clang
22.1.8 frontend and checked JSON, typed IR, layout, and publication stages
to independently verified 1,143-byte `malbolge-2026` capsules. The
normative VM executes 12 instructions, consuming five real guest bytes
and emitting six: `41 42 43 44 5a` yields `41 42 43 43 44 5a`, while
`00 ff 80 01 7f` yields `00 ff 80 80 01 7f`. Independent native C23
Clang 22.1.8 with UBSan at O0 and O2 matches both guest input vectors
for both programs. No host I/O substitutes for guest effects. Runtime
C branching on input bytes, EOF and arbitrary-length streams remain
unimplemented, so P0 is still pending.

### Non-unit unsigned induction with live guest I/O (2026-11-15)

A complete C parity-branch program with `for (unsigned i = 0U; i < 4U;
++i)` still refuses when it branches on the parity of the live guest byte.
No guest runtime C conditional evaluation has been implemented.

The source-authenticated counter capability now also admits the real C forms
`i += 2U` and `i = i + 2U` in a four-trip unsigned loop with a selected
`if (i == 4U)` branch. The bounded proof authenticates pinned Clang `u32`
assignment/arithmetic ancestry, complete original C step spelling, exact `U`
suffix and the descending post-body update before selecting guest effects.
Two-digit strides are supported, including an ascending `10U` and descending
`10U` case with four actual guest reads. An unsigned `9U; i > 0U; i -= 2U`
loop refuses: its final decrement wraps to `UINT_MAX`, not a false guard.

The pinned C frontend and JSON-to-typed bridge accepted both ascending forms
and the descending source, with independently verified 1,127-byte Malbolge
capsules. The normative VM emitted `ABCCD` from `ABCD` for ascending compound
and descending loops; both ascending compiler forms emitted binary
`00 ff 80 80 01` from `00 ff 80 01`, consuming four real input bytes in
10 guest steps. Normalized positive/negative fixtures and Rust regressions
also check forged types, arithmetic bindings, operators and step literals.

This remains compile-time induction and branch selection with guest runtime
I/O, not guest-dependent control flow, guest arithmetic, EOF or arbitrary C
streams. P0 remains pending.

### Source-checked unsigned byte-branch selection (2026-11-15)

A whole four-trip C function reads each byte into an automatic `int`, then
uses an unsigned loop counter to choose a distinct output effect: the third
input is written twice. The signed-counter counterpart worked, but the
unsigned `if (i == 2U)` version initially refused at `for-statement`
admission. The full live-input Fibonacci experiment still refuses its
earlier mixed unsigned-state declaration.

A red-first pinned Clang regression now retains the induction counter
signedness in the source-aware predicate proof. Unsigned comparisons use
exact `u32` variable/cast nodes, a source-authenticated `U` literal suffix,
exact operator bytes, and checked declaration ancestry before choosing a
compile-time loop branch. Changed C source or forged equal-width `!=`
operator metadata refuses typed admission. The rebuilt native pipeline
emits a 1,127-byte Malbolge capsule whose normative VM consumes four real
input bytes and emits five in ten steps; binary `00 ff 80 01` becomes
`00 ff 80 80 01`, and `ABCD` becomes `ABCCD`. A source-C guard on the
live byte is deliberately unsupported.

This is statically proven C counter control with dynamic guest I/O, not
guest-side conditional execution, general unsigned arithmetic or EOF.
The P0 generalization remains open.

### Source-checked unsigned guest-input induction (2026-11-14)

The complete Fibonacci-with-live-input C probe still refuses its first
compile-time `unsigned` local declaration, so source-C runtime recurrence
and dynamic C branching remain unsupported. A smaller actual source-C
program exposed a separate capability gap: `for (unsigned i = 0U;
i < 4U; ++i) { putchar(getchar()); }` was refused even though the same
bounded loop with a signed counter emitted genuine guest input/output.

The source-checked finite-loop projector now admits Clang `u32` induction
only when the original C spells `unsigned`, each initial/bound literal
has an exact authenticated `U` suffix, and the variable references,
C positions, and step are unchanged. Unsigned counters are restricted
to unary increments or decrements and existing small iteration bounds;
compound/assigned unsigned steps are still refused rather than guessed.
An independently normalized negative fixture proves that `unsigned i >=
0U` with `--i` must refuse: an unsigned zero decrements to a wrapped
value and cannot be treated as loop termination.

The pinned LLVM 22.1.8 Clang JSON/source fixtures, positive and negative
source mutations, and three focused Rust tests pass. The unmodified
accepted C file compiled with pinned native frontend, source-aware typed
bridge, and independently verifying layout to a 1,119-byte current-profile
Malbolge capsule. Normative VM replay with explicit `--input-stdin` emits
`41 42 43 44`, `31 32 33 34`, `78 79 7a 57`, and `00 ff 80 01` for the
four corresponding four-byte inputs, respectively, in nine steps each.
The VM requires `--input-stdin` to receive piped input; without it, the
runner intentionally supplies empty stdin and cannot prove input parity.
The direct driver experiment used host Python 3.15 because repository-
pinned Python 3.14 is missing; the native Clang and Rust guest stages are
repository-built. This is real guest I/O parity for a bounded loop, not
general C guest-side arithmetic/control, EOF handling, or unrestricted
input streams. The P0 task remains open.

### Source-bound C scalar token verification (2026-11-14)

A second complete C probe with a live `getchar()` byte, unsigned Fibonacci
recurrence, and conditional `putchar` first refused a mixed runtime-input
and compile-time-state declaration. Dynamic guest C state and branching are
still unimplemented; no output was published for that program.

Independently, a red-first pinned-Clang JSON mutation changed an unsigned
`60U` source literal to normalized `61` without changing the original C
witness. The unguarded compiler accepted the forgery and the normative VM
emitted `40` instead of source-correct `41`. A same-width `+` to `-`
operation forgery also passed typed admission. A common source-backed
scalar-token gate now checks original C integer spelling, normalized values,
and binary/compound assignment operators before any projection fallback.
AST-only projection remains a separate compatibility contract. Four focused
source-bound tests pass, including alternate C23 integer spellings and
source mutation; the current pinned Clang fixture hashes exactly to its C
source. The original twelve-iteration Fibonacci guest still emits
`02 59 5f 08 57 4f 22 6d 03 90 b3 23` in 117 VM steps with the
guarded adapter, preserving bounded full-C parity.

This repairs source authentication, **not** dynamic C guest control flow,
EOF, arbitrary byte-stream generation or the outstanding P0 contract.

### Original complete C-to-Malbolge parity (2026-11-14)

The repository-local LLVM 22.1.8 runtime was imported from the exact-version
host tools using the documented bootstrap with `/usr/bin` first in `PATH`;
the matching development kit was provisioned with verified RPM identities,
and the native normalized frontend was built with the repository build gate.
No compiled frontend binary or private toolchain state was checked into Git.

The **unmodified** `tests/compiler/c-frontend/accepted/conditional_fibonacci.c`
(SHA-256
`b9e3e143d44d187f0569c4ef1809c373256f1795172eb1a43086fdfcae5a94c0`)
then compiled through the pinned Clang frontend, source-bound JSON adapter,
typed/ternary bridge and independently verifying layout publisher. The
compiler emitted a 2,767-byte current-profile capsule. The normative VM
executed 117 steps and emitted exactly the independently calculated twelve
bytes `02 59 5f 08 57 4f 22 6d 03 90 b3 23`, both with empty input and with
binary stdin `00 ff 80 01`. This finally supplies complete source-C-to-guest
parity evidence for the original compound program, rather than only typed
publisher parity or a host C oracle.

The C locals, loop and branch are still source-proven and folded **at compile
time**; Malbolge executes the admitted low-level arithmetic and output trace,
not a dynamic C control-flow machine. EOF, dynamic C guest arithmetic/control,
other arbitrary byte streams and the broad seeded semantic matrix remain
outside this bounded result. The P0 generalized compiler work is not closed.

### Authenticated static C induction subtrees (2026-11-14)

The production CLI retried the complete conditional Fibonacci C source but
stopped at missing repository-local pinned LLVM 22 frontend preflight without
publishing a guest. Separately, red-first synthetic normalized AST proofs
exposed an unsound source-backed induction predicate: a constant-only
subexpression could retain the Clang `1` while the original C spelled `0`,
or swap `==` for `!=`. A fallback from failed induction authentication to
AST-only constant evaluation then restored the forged branch decision.

Static subtree proof now compares every literal, unary, binary and grouping
token against source bytes; source-backed failure cannot bypass those checks.
Four new regressions and the five prior induction-lazy tests pass,
including an authenticated constant-logical fallback that preserves valid
source expressions. This does not establish pinned frontend parity, dynamic
C branches, EOF or general guest byte streams. The P0 task remains open.

### Source-bound lazy C induction arithmetic (2026-11-14)

The production CLI retried the complete conditional Fibonacci source and a
separate two-trip signed-C induction/branch/putchar program. Both refused at
repository-pinned LLVM 22 frontend preflight because the executable is absent;
no guest artifact was emitted. Host C23 at O0 and O2, with undefined-behavior
sanitization, independently executed the smaller source and emitted `41 42`.
This is a host oracle, **not** guest execution or frontend admission evidence.

A red-first source/Clang-preorder proof found that source-time induction
predicates eagerly evaluated both operands of `&&`/`||` and both arms of `?:`.
For `i != 0 || i + 2147483647 == 2147483647` at `i = 1`, C skips an
otherwise overflowing pure right operand, but the adapter rejected the valid
predicate. The bounded adapter now requires actual definedness only for the
selected operand. For a skipped subtree it still proves purity and exact
source/Clang shape using defined witness induction values `0`, `1`, or `-1`;
those substituted truth values are discarded and cannot select guest effects.
If no witness proves the subtree, admission still refuses conservatively.

Four focused synthetic-AST tests cover both logical operators, both ternary
arm positions, defined/executed overflow, forged local references, changed
arithmetic, and same-width logical/conditional source operator forgeries.
The unchanged eleven normalized-loop integration tests and workspace all-target
Rust check pass. The broad adapter library suite fails seventeen unrelated
inspector-transport tests because the pinned Python inspector is absent; its
seventeen remaining tests pass. Neither these synthetic ASTs nor host Clang
replace pinned normalized ASTs or normative guest VM parity. P0 guest dynamic
state/control, arbitrary byte streams, EOF and the original full C proof
remain unfinished.

A second red-first source-authentication regression found that the same
induction proof checked AST/spans but not the actual `!` or `(`/`)` C source
bytes. A valid same-width unary `+` could impersonate a normalized `!` and
reverse a branch decision. Both the prefix token and closing grouping token
are now checked against original source; equal-span forgeries refuse. Five
focused source-backed synthetic AST tests pass, including these punctuation
mutations. The limitations above on pinned frontend and guest execution are
unchanged.

### Definedness of lazy live-byte predicates (2026-11-14)

The complete conditional Fibonacci C source was retried through the production
CLI, but repository-pinned LLVM 22 frontend preflight refused it without
publishing a guest artifact. A separate red-first source/AST predicate
regression exposed an over-conservative proof: `1 || 1 / 0`,
`0 && 1 / 0`, and a selected ternary arm were refused because the checker
attempted to evaluate pure but unexecuted operands.

The bounded C `i32` predicate evaluator now carries definedness separately
for all 256 successful input bytes. Source and Clang node structure are still
checked for every subtree. `&&`, `||`, and `?:` consume only their actually
selected operand values; each reachable zero divisor, undefined arithmetic,
impure subtree, altered source spelling, or forged live-local reference still
refuses. A live-byte tautology `current == 0 || current / current == 1`
and a zero-safe ternary are proven across the complete 256-byte domain.
Eight focused synthetic preorder-node tests and eleven existing normalized
loop regressions pass. These synthetic nodes are **not** pinned Clang golden
artifacts: no frontend-to-guest or normative VM parity has been established
for this newly admitted expression. Dynamic guest branching/arithmetic,
EOF, arbitrary streams, and the original full C P0 remain unfinished.

### Late graphical source-scratch output completion (2026-11-14)

The fixed forward-jump graphical source-scratch solver could spend its four
independent-admission checks at source lengths 101-102, before any later
source phase emitted the final output. A red-first completion callback
reproduces this with one actual zero-byte guest effect. The solver still
checks three early candidates, but reserves its final check for a later
completed phase, preferring a just-emitted output over padding when tied.
The selected graphical source is independently encoded and runs in the
normative VM with the intended zero byte under empty and binary input.
All prior step/history caps and source write/positional/VM proof rules remain.
The complete conditional Fibonacci C program was retried but stopped at
missing pinned LLVM 22 frontend preflight, so dynamic C arithmetic/control,
EOF and arbitrary byte streams remain unsupported.

### Late source-phase completion after bounded verification (2026-11-14)

The straight-through and repeated-relocation proposal grammars could consume
all four independent-admission checks on early complete paths. A later body
cell may emit the final byte with a different positional source phase, but
that candidate was never checked. Two red-first callbacks reproduce this
false negative in callback admission for the last source body cell with
one and two live data relocations, respectively.

Both searches now try up to three early completions and reserve the fourth
check for the latest viable source phase, favoring a newly emitted final
byte over a padded complete trace at the same position. The same four-check
cap, exact accumulator state, source-write restrictions, positional encoder
and two-input normative VM admission remain in force. A separate 16-step
source-independent guest emits its zero byte at the final body cell; the
recovered encoding matches the independently admitted source and runs in
the normative VM. The original complete conditional Fibonacci C again fails
before lowering because the pinned LLVM 22 frontend executable is absent.
Guest runtime C state and generalized byte-stream synthesis remain open.

### Dense output-beam total capacity (2026-11-14)

The source-independent output search first retained minimum, maximum, and
up-to-four-step-reachable full accumulator words per output-progress/byte
class. Each class obeyed its local representative bound, but twelve distinct
progress counts across 256 byte classes could still retain **16,442**
proposals, beyond the **16,384** global source-position cap. The search then
refused the entire geometry despite having bounded, viable proposal subsets.

A red-first 552,960-state synthetic frontier reproduces this overflow with
real current-profile crazy transitions and loader-word lookahead. A second,
progress-balanced beam pass now enforces the global cap after the reachability
hints, retaining representatives for every active output count and appending
reconstruction links only for survivors. All accepted proposals continue
through independent positional, source-write, and normative VM verification.
This repairs a bounded search false negative, not guest-side C execution or
arbitrary stream completeness. The pinned C frontend remains unavailable.

### Variable source-scratch late-geometry admission (2026-11-14)

The complete twelve-trip conditional Fibonacci C program was attempted again,
but the repository-pinned LLVM 22 frontend executable is absent. Its source
still cannot pass the production frontend preflight, and no artifact was
published. The matching system Clang version is not a replacement for the
pinned normalized frontend binary.

The variable source-scratch proposal previously exhausted all four independent
verification slots on the shortest completed source lengths. If those
positional proposals failed, a later graphical source phase could not be
checked even when the bounded search had already discovered it. A red-first
two-byte guest regression selects only a later completion; the solver now
checks the three earliest candidates and reserves the fourth slot for the
longest completed source. The source still requires the unchanged positional
encoder, disjoint source-write policy, and normative VM checks before
publication. Both bridge entrypoints pass the late-candidate regression, and
the selected longer guest actually emits two zero bytes under binary stdin.
The prior rejected-first/accepted-second and all-rejected four-check tests
remain active. This is finite search coverage, not general guest streams,
dynamic source-C state/control, or proof of full P0 acceptance.

### Verified variable source-scratch completion retries (2026-11-14)

The variable-operand forward-jump search had a related false negative:
after building all complete progress states, it reconstructed only the
shortest state and discarded the entire jump geometry if the positional
encoder, write-footprint checker or normative VM rejected that candidate.
The solver now checks up to four deterministic complete paths without
changing its bounded five-step-per-byte proposal grammar or source proof.
Accepted code still passes the same two-input independent guest replay.

Two red-first callback regressions prove rejection followed by a distinct
completion and the four-check all-rejected limit. The 14 source-scratch
bridge tests pass, including the real twelve-byte masked Fibonacci guest.
This does not prove search completeness, source-C runtime state, or general
byte-stream emission. The pinned C frontend remains absent.

### Verified forward-jump source-scratch completion retries (2026-11-14)

A complete 12-trip conditional Fibonacci C program was retried through the
production CLI. It again stopped before compilation because the repository-
pinned LLVM 22 C frontend is absent; no guest artifact was published.

The separate forward-jump source-scratch solver stopped on its first complete
accumulator/output path even when the positional encoder or normative VM
rejected that path. It now proposes multiple full-word completions or later
source-length candidates under a fixed four-check budget. Each candidate
still passes the original independent positional encoding, source-disjoint
write checks and empty/binary-input normative VM replays before acceptance.

Two red-first tests establish rejected-first/accepted-next proposal handling
and the all-rejected four-check cap. Existing real source-scratch Fibonacci
and skipped-source-byte guest tests continue to pass. These tests prove
bounded search recovery and refusal behavior, not generalized guest C
arithmetic, storage, dynamic control flow, or arbitrary stream synthesis.

### Verified completion retries after multiple guest relocations (2026-11-14)

The production two-, three-, and four-relocation search previously returned
its first complete output proposal before independent positional decoding and
normative VM replay. A rejected proposal silently abandoned other complete
paths in the same geometry, unlike the straight-line search. The search now
checks each candidate through the same independent publisher and retries
later full-width accumulator paths or padded completions. At most four
checks per geometry bound verification effort; rejected output cannot publish.
A red-first two-live-`j` regression checks rejected-first, accepted-second,
and exact all-rejected bounds; existing multi-relocation VM witnesses still
execute. The original source-C conditional Fibonacci probe stops at
repository-pinned LLVM 22 frontend preflight because that executable is
absent. This repair is bounded proposal coverage, not guest-side runtime C
arithmetic/control/storage, EOF, or arbitrary byte-stream synthesis.

### Verified retry of complete output proposals (2026-11-14)

The straight-line guest search previously stopped at the first state with
all requested outputs, before checking whether its positional encoding could
pass independent layout admission. If that proposal failed, the rest of the
same source geometry was discarded even though subsequent source cells and
different accumulator paths might yield a valid guest.

The completion callback now checks each proposal before search success, and
continues after rejection with at most four completion checks per geometry.
A focused two-entrypoint regression verifies a rejected first completion,
accepted later completion, and the hard all-rejected budget. The unchanged
alternate no-op terminal guest still passes real VM replay in both
entrypoints. This is bounded search coverage, not a completeness proof or
implementation of guest-side C runtime arithmetic and branching. The
pinned C frontend executable is unavailable locally.

### Completed source-revisit progress after bounded pruning (2026-11-14)

A dense source-revisit frontier formerly discarded states whose output count
already equaled the requested byte count. The search tests a complete trace at
each source position, but an unsuccessful early positional encoding does not
prove a valid halt cannot follow additional no-op source cells. Dropping the
completed state after that unsuccessful attempt prevented all later retries.

The beam now retains completed output counts along with incomplete progress,
under the same 16,384-state limit and full-accumulator keys. A red-first
28,672-candidate regression proves both completed high-word diversity and
two-layer reconstruction linkage in both bridge entrypoints. The independent
twelve-byte original Fibonacci guest still executes on the normative profile
VM with empty and binary input. The pinned Clang 22 frontend executable is
absent locally, so the complete source-C pipeline remains unverified.
This is a bounded proposal-search correction, not generalized dynamic C
arithmetic/control, arbitrary guest streams, or P0 acceptance.

### Retained-only source-revisit reconstruction history (2026-11-14)

The bounded source-revisit search formerly allocated permanent predecessor
records for every speculative successor, even when a 16,384-state beam
discarded thousands of them at each source cell. The successor map now
temporarily stores complete links and appends only retained paths to history;
the full accumulator keys, progress-balanced beam, exact sparse behavior,
independent positional verification, and normative VM admission are unchanged.

A two-layer dense regression constructs 24,576 initial candidates and proves
the first layer retains exactly 16,384 links, with all second-layer parents
pointing into that retained layer. The original twelve-output Fibonacci guest
and its canonical typed trace still reproduce
`02 59 5f 08 57 4f 22 6d 03 90 b3 23` on the normative VM with no input
consumption. The pinned LLVM 22 source-C frontend is absent on this host,
so these runs do not establish end-to-end source-C compilation. Guest runtime
C state, arbitrary byte-stream synthesis, and P0 acceptance remain open.

### Source-revisit progress quotas and twelve-byte typed trace (2026-11-14)

A source-revisit beam with six populated output counts had been spending
all capacity beyond per-byte extremes on its most advanced counts. A new
red-first dense regression identifies an intermediate full accumulator
word at an earlier count with a genuine crazy-operation continuation.
The search now apportions its bounded capacity across active counts before
redistributing unused slots toward advanced paths. Exact sparse search,
full-word keys and independent layout/VM acceptance remain unchanged.

The original complete twelve-byte unsigned Fibonacci output has an
existing **test-only** real guest witness via the source-revisit search;
its original `HEAD` implementation and the balanced version both pass
the normative VM replay. The typed canonical publisher can also admit
that full byte stream, so its obsolete negative expectation is updated.
This does not prove the pinned C source compilation: the native frontend
was missing locally, and the three original C-pipeline tests skipped.
Dynamic runtime C operations, general synthesis and P0 remain open.

### Wider finite C steps and protected-counter arithmetic (2026-11-13)

A complete C source with a named `position` counter, two-digit
`position += 12` induction, real binary `getchar`, nested conditional,
`continue` and trailing fresh read originally refused at normalized
lowering. Exact 1–99 decimal source/Clang-backed stride geometry now
admits the three-trip loop and a reverse `position -= 12` loop. Both
execute genuine binary guest I/O, emitting four copies of the initial
byte and a fresh byte in eight normative VM steps. Assigned strides,
zero-trip and boundary forms reach isolated layout admission; skipped
`!=` endpoints, divergent steps and forged source/AST fail closed.

A separate complete C program first refused its protected-counter
`position / 12 == 1` predicate. Bounded signed `i32` induction
arithmetic now proves source- and Clang-authenticated `+`, `-`, `*`,
`/`, and `%` with a positive denominator for division/remainder and
checked overflow for all operators. The program's second-trip `break`
changes its guest effect trace: it emits three real copies of the
initial input and a fresh second byte in seven VM steps, not the five
bytes/eight steps of the unbroken loop. Multiplication selects the
same guest-visible exit; other operations reach frontend admission.
Same-width source comparator and number forgeries (including direct
counter comparisons), altered operators/AST ancestry, zero divisors
and reachable overflow refuse before guest publication. These proofs
replay bounded source-local C induction only; guest runtime arithmetic,
branching, storage, EOF, and generalized streams remain unsupported.

### Source-authenticated named C induction counters (2026-11-13)

A complete C program with a live `getchar` local, a step-by-two finite
`for` loop, a nested input-dependent branch, induction-selected `continue`,
and trailing fresh I/O first failed in the JSON adapter when the counter was
spelled `index` instead of `i`. The induction proof now binds an ASCII C
identifier of 1–32 bytes to the pinned Clang declaration reference and exact
source tokens in the declaration, condition, increment and all proven body
predicates. It derives expression geometry from the identifier width rather
than assuming one-byte counter names. Longer names and absent original source
for non-`i` names remain unsupported and fail closed.

The unchanged complete program emits four copies of its actual first guest
input byte followed by the next input byte in eight normative VM steps,
across binary boundaries and seeded inputs. A descending `position -= 2`
program, and a direct `index == 2` conditional, also emit exact independent
byte oracles. Nine further name/step/predicate shapes reach layout admission
under an intentionally rejecting backend stub. Forged source token prefixes,
header bindings, Clang declaration names and step operators refuse without
publishing a guest artifact. All induction values remain bounded C
compile-time replay, not guest runtime C control, arithmetic, storage or EOF.
The unmasked twelve-output Fibonacci layout and P0 remain pending.

### Proven single-digit non-unit induction with live guest bytes (2026-11-13)

A whole source-C program with an initial guest input, counted `for` loop,
induction-dependent `continue`, nested integer guard, and trailing fresh
read first refused `for (int i = 0; i != 6; i += 2)` at normalized
lowering. The frontend projector now accepts source- and Clang-authenticated
positive single-digit strides (1–9) for compound `i += N`/`i -= N` and
assignment `i = i + N`/`i = i - N` with exact original spelling. The
signed `i32` comparator and initializer/bound leaves remain checked.

Ordered `<`, `<=`, `>` and `>=` use source-time stepped trip counts;
`!=` additionally requires the bound to be *exactly reachable*. All
branches require the step direction to match the comparison, at most
sixteen trips, a bounded initializer, and no change to guest effect
ordering. Skipped or overshot inequalities never become a guessed finite
trace. The adapter refuses zero/two-digit strides, divergent directions,
more than sixteen trips, and forged Clang stride values or ancestry.

The original ascending and a descending complete C program now emit four
actual copies of the first binary input byte plus one fresh second input
through the normative Malbolge VM. The ordered and zero-trip forms reach
layout admission under an isolated rejecting stub. This proves finite
*compile-time* induction over source-authenticated C, not guest runtime
C arithmetic, storage, EOF, arbitrary strides or dynamic C control.
The unmasked twelve-output Fibonacci layout and P0 remain pending.

### Source-authenticated finite inequality loops (2026-11-13)

A complete source-C program with an initial `getchar` local, counted loop,
remainder-selected `continue`, a nested signed-unary guard, and trailing
fresh input first refused `for (int i = 0; i != 3; ++i)` at normalized
lowering. The static induction proof now admits source-spelled `!=` for
canonical unit steps in either direction, but only if the exact bound is
reachable within sixteen trips or initially equal (zero trips). The original
C comparator, decimal initializer/bound, and prefix/postfix/compound/assigned
unit-step spellings are checked against source bytes as well as pinned Clang
parent/span/type/operator ancestry. Opposite-direction and oversized loops,
and same-width Clang comparator, literal and step forgeries, refuse.

The original complete program emits four copies of its actual first byte
and a second fresh input in eight normative Malbolge VM steps on boundary
and seeded binary streams. A descending branch/`continue` loop emits three
fresh bytes in seven steps; zero-trip execution still emits its two trailing
bytes in five steps. Seven further increment forms reach frontend layout
admission without spending guest-search budgets. This is source-proven static
induction, not general runtime C control, arithmetic, storage, EOF or failed
output; the P0 remains pending.

### Signed unary C arithmetic in source-proven live-byte guards (2026-11-13)

A full counted C source program with local state, remainder-selected
`continue`, a nested conditional, and two actual input bytes first rejected
`((~current) ^ current) == -1` at normalized lowering. The source- and
pinned-Clang-authenticated finite proof now composes unary `+`, checked
signed `-`, and bitwise `~` with exact `i32` results across all 256 possible
successful guest bytes. Clang's constant annotation for a literal `-1` is
accepted only when it matches every independently proven value; that
annotation never predicts the guest input or authorizes a side effect.

The original C program emits four copies of its actual first input and a
fresh second byte in eight steps of the normative Malbolge VM across
binary boundaries, strata and deterministic seeded streams. Pure negative
arithmetic forms and a byte-dependent equivalent-output guard also pass
real guest execution. Signed-negation overflow, implementation-defined
negative right shifts, effectful operands, unequal arms and forged Clang
parent/operator/type/span/constant evidence refuse without an artifact.
No guest runtime integer arithmetic, unequal dynamic branching, storage,
EOF or failed output is implemented; the P0 remains pending.

### Checked arithmetic for pure live-byte C guards (2026-11-13)

A complete three-trip source-C program with local state, induction,
remainder-selected `continue`, a nested conditional, and two real guest reads
first refused `((current * 3 + 1) % 3) == 1` at normalized lowering. The
source-/pinned-Clang-authenticated 256-value `i32` proof now composes pure
binary `+`, `-`, `*`, `/`, `%`, `<<`, `>>` and general comparisons in addition
to Boolean/bitwise operators. Checked signed overflow, division by zero,
negative or out-of-range shifts, and nonrepresentable signed left shifts
reject; there is no wrapping or guessed guest input. All operands require
exact original-source spelling, Clang parent IDs, spans and integer types.

The original C program now executes in the normative guest VM with four
copies of its first actual input followed by a new input, in eight guest
steps. A guest-dependent modulus guard with independently equivalent
output-only arms also preserves genuine binary I/O. Bounded boundary,
stratified and seeded oracle streams, additional arithmetic admission
shapes, effectful/unequal branches, undefined arithmetic and forged AST
all have regression coverage. Arithmetic is proven only to decide whether
C branch effects are invariant over successful byte reads: guest-side
arithmetic, dynamic unequal-arm branching, EOF, storage and failed output
remain unsupported. The P0 contract is still pending.

### Exact non-Boolean integer predicate values (2026-11-13)

A complete counted C stream with a live binary input, local state,
remainder-selected `continue`, nested conditional, and a trailing read
first refused `((current & 2) ^ (current & 2)) == 0`. The source- and
pinned-Clang-authenticated predicate proof previously stored only a
256-bit truth set with an exact-Boolean flag. That could not distinguish
different nonzero integer mask values, so XOR/AND had to refuse.

The proof now carries 256 exact `i32` values: direct resident-byte
identities, pure literal/masked/comparison leaves, grouping, negation,
zero comparisons, logical and bitwise operators, and pure conditional
expressions retain C's integer semantics. A predicate arm may be
selected only when all 256 values agree on zero/nonzero; otherwise
both complete output-only effect traces must independently agree.
This still cannot guess runtime input, erase guest reads or writes,
or implement general dynamic guest C branching.

Two full one-trip counted C programs exercise XOR cancellation
and disjoint-mask `&` false selection. A third executes a
byte-dependent non-Boolean XOR guard with equal output effects.
All three run under the normative guest VM with binary boundary
inputs and output `current, current, next` in six instructions.
Three further total guards pass the source-authentication stage
without repeating equivalent guest layout synthesis. Forged Clang
ancestors, operators, spans and type, effectful operands, unsupported
integer expressions and unequal arms fail without publication.
EOF, failed I/O, guest-side arithmetic/storage and general runtime
branching remain unsupported. The original three-trip source has not
yet completed layout, so P0 remains pending.

### Integer bitwise OR truth over successful guest bytes (2026-11-13)

A complete source-C stream with a local guest input, counted induction,
remainder-selected `continue`, a byte-dependent `if`, and two real guest
reads initially refused `(current & 2) | (current & 4)` at normalized
lowering. C integer bitwise OR is zero exactly when both operands are zero,
regardless of their nonzero bit patterns. The bounded source-/pinned-Clang
proof now composes each pure operand's finite successful-byte truth set
under `|`, without falsely treating either integer mask as an exact 0/1
Boolean. This older truth-only implementation has been superseded by the
exact-integer value proof above, including XOR and AND. Dynamic branches
can still be erased only when proven total or both complete source-proven
output traces are identical. Three original bitmask, zero-test and
logical-OR variants each match 15 independent binary streams in the
normative VM, with five output bytes and eight steps per run. Hidden
effects, unequal arms and forged Clang ancestry still refuse without
publishing an artifact. This does
not add guest arithmetic, guest-dependent control flow, EOF, or failed I/O.


### Bitwise Boolean partitions over live bytes (2026-11-13)

A complete source-C stream with local state, a counted loop, a remainder
branch, `continue`, nested `if` and two real binary reads initially refused
`((current & 1) != 0) ^ ((current & 2) != 0)` at normalized lowering.
The bounded predicate proof now distinguishes an exact C result of `0` or
`1` from a merely truthy integer. It authenticates all operands against
original source bytes and pinned Clang ancestry, then composes `^`, `&`,
and `|` as bitwise truth sets only when both operands are proven Boolean.
A nested equality/inequality with literal zero can convert a source-proven
mask into a Boolean, without treating `current & 2` as `0` or `1`.

The original compound program reaches real guest execution and matches an
independent binary-stream oracle in eight VM steps across boundary inputs.
The proof cannot predict the guest byte or implement a runtime branch:
dependent guards are erased only when both full source-proven output traces
are equivalent. General arithmetic and guest control flow, EOF, and failed
I/O remain unsupported; P0 stays pending.

### Byte-dependent ternary statement guards (2026-11-13)

An original C program with binary `getchar`, three-trip induction, a static
remainder/`continue` branch, nested `if` and trailing output first refused
`(current & 1) ? (current >= 0) : (current <= 255)` during normalized
lowering. The source-/Clang-authenticated adapter now composes a pure
conditional expression's three truth sets over **all** successful bytes,
including both branches that C would skip for a particular runtime byte.
The selector chooses one arm's truth independently at each byte; only a
complete/empty result or equivalent nonempty output-only statement effects
can eliminate the guard without predicting the actual guest byte. Source-
checked canonical nonnegative `i32` literal arms, including zero, compose
with the same proof.

Whole C programs with true, false, nested and dependent guards execute on
the normative guest VM with independent binary-input oracles and explicit
step counts. Inactive effects, live input in a predicate, unequal effects,
forged Clang ancestry/spans/operators/literals and changed source reject
without publication. The 256-value proof excludes EOF and failed I/O and
does not implement runtime guest branching, arbitrary state or arithmetic.


### Grouping, negation, and direct-byte Boolean partitions (2026-11-13)

A full C program with live binary input, counted induction, `continue`, and
trailing I/O initially refused an input-dependent `!(current & 1)` guard
although both arms independently write the same byte. The bounded adapter
now recursively authenticates parentheses and unary logical negation in a
256-value truth set. Both source spellings and pinned Clang parentage must
match exactly; `!` complements the bitmap and parentheses preserve it.

A second red-first program refused `current || !current`. A proven pure
resident byte now contributes the truth set for all nonzero successful
bytes, while its source-checked zero test contributes the singleton zero
set. `&&` and `||` compose these without computing the runtime byte. Both
arms are authenticated, including short-circuited operands. Non-total
guards only pass if both arms have identical nonempty output-only effects.

Six source C streams execute in the normative Malbolge VM: 17 independent
binary streams for the negated dependent guard, four for grouped true/false
partitions, and nine for direct-byte tautologies and contradictions. Their
expected output is an independent function of the binary inputs, with no
extra reads and exactly six or eight VM steps. Effectful guards, unequal
arms and forged source/AST refuse without an artifact. This is a proof of
successful-byte static effects, not guest-dependent runtime branching,
EOF, failed output, general arithmetic or storage. P0 remains pending.

### Source-proven equivalent effects across dependent C arms (2026-11-13)

A complete original C program with a live input local, induction, branch,
`continue` and trailing I/O initially refused `if (current & 1)` even
though both arms independently output the identical resident guest byte.
The bounded adapter now proves a pure guard against original source and
pinned Clang, including all short-circuited operands. If its Boolean truth
set varies across `[0, 255]`, both authenticated arms must have the same
nonempty output-only effect trace, with no read, assignment or loop exit
in either arm. Different C spellings of byte-preserving expressions may
therefore eliminate the branch, without predicting a guest byte or host
simulation of the branch.

The original C program executes in the normative VM with five outputs and
eight steps for five binary boundaries, 16 seeded pairs and 16 stratified
first bytes. A two-output-per-arm C variant emits four bytes in seven steps
across both guard polarities; zero-trip behavior emits two bytes in five
steps. Unequal/effectful arms, impure guards, AST parent/operator/literal
and span mutations, changed original source and absent witness refuse
without publication. This establishes only successful-byte output trace
equivalence, not general guest-dependent C branching, storage, arithmetic,
EOF or failed output. P0 remains pending.

### Boolean-complete guest-byte partitions (2026-11-13)

A complete C program with input, three-trip induction, static `continue`,
nested `if` and trailing byte I/O first refused a pure dynamic partition:
`if (current == 0 || current != 0)`. A bounded source-/Clang-authenticated
proof now enumerates the 256 successful input bytes into four `u64` words.
It composes exact comparison and bit-mask truth sets with set intersection
for `&&` and union for `||`. Only an empty or complete final truth set can
select a whole statement arm. A dependent leaf is therefore admissible if
its logical combination is byte-total. The proof authenticates all leaves,
including inactive short-circuit operands, and does not evaluate real guest
input or introduce runtime branching. Non-total/effectful forms reject.
Two full counted programs pass 17 binary input pairs each in the
normative Malbolge VM, producing five bytes in eight steps for both
true and false partitions. Three more guards reach layout admission;
six dependent/effectful guards and five source/Clang forgeries refuse.

Successful `getchar()` bytes exclude EOF; general guest-dependent branches,
storage, arithmetic and failed I/O remain outside the supported slice.

### Pure compound successful-byte predicates select C arms

An original C program with an input local, three-trip induction loop,
remainder branch, `continue`, nested C `if` and trailing real guest I/O
first refused `if (current >= 0 && current <= 255)` at the normalized
adapter. The bounded proof now authenticates the original C bytes,
pinned Clang `i32` logical `&&`/`||` parents, operand trees and spans.
Each leaf must have one truth value across successful bytes `[0, 255]`;
the combined result is independent of the actual runtime input. Both
operands must be pure, including those skipped by C short-circuiting.

Three two-operand and two mixed-precedence complete streams execute in
the normative VM with four genuine copies of the first input followed
by the second, in eight guest steps. Boundary and seeded binary cases
match an independent byte oracle. A separate false compound `if`
without `else` skips an input effect and emits two copies of the first
byte followed by the second in six steps. Eight inconclusive/effectful
guards and six source/Clang integrity cases refuse without an artifact.
Dynamic C branching, EOF, failed writes, general storage and arithmetic
remain unsupported.

### Total successful-byte predicates select a whole C statement arm

An original full C stream combines a live `getchar()` local, a three-trip
induction loop, a static remainder branch and `continue`, a nested C `if`
and trailing binary input/output. The adapter initially refused the live
`if (current < 256)` comparison. It now proves one pure, pinned-Clang
comparison against exact original C text, selects an arm only if its truth
value agrees at zero and across all positive successful bytes `[1, 255]`,
and authenticates both complete C arms before emitting the selected effects.
It never evaluates the actual byte on the host or invents guest branching.

The normative VM reads two real bytes and emits five: four copies of the
first and one fresh second byte, in eight guest steps across four boundaries
and twelve seeded binary pairs. A reversed always-false threshold also
matches. Nine byte-dependent/side-effectful guards, changed Clang nodes,
forged source SHA and an absent original C witness refuse without an artifact.
No arbitrary guest-dependent `if`, EOF, failed output, arithmetic or memory
is implemented; this P0 remains pending.

### Total wide-integer range tests over a live input byte (2026-11-13)

A complete C program combining a live binary input, a four-trip induction
loop, selected `continue`, source-local state and nested arithmetic first
failed normalized projection on `current < 256 ? ((current ^ 0) & 255) : 0`.
The new interval proof authenticates a nonnegative signed C decimal literal
and each pinned Clang node against the original C source. Comparisons are
selected when all positive successful bytes in `[1, 255]` agree; at
zero both arms yield zero. An incompatible mask is proven false when
no low byte bits can overlap. Both arms are source-proven separately,
and the inactive one must be a literal zero.
No guest input value is fabricated or host-evaluated.

The actual Malbolge VM emits the first input byte five times and the
second once, in nine steps over four boundaries and sixteen deterministic
seeded pairs. A false-guard program and a zero-trip program also pass
two-input parity. A second whole-C zero-exception comparison,
`current >= 1 ? ((current ^ 0) & 255) : 0`, now emits its first
byte four times then the second in eight real VM steps across fifteen
binary pairs. Fourteen other threshold/mask forms reach layout;
inconclusive comparisons, forged literals, changed source, effects and
out-of-range signed literals refuse. Dynamic C branching, arithmetic,
storage, EOF and failed I/O remain P0 gaps.


### Proven successful-byte range conditions (2026-11-13)

The original complete source-C four-trip induction/continue program first
failed at normalized lowering on a pure range conditional with unequal arms:
`current <= 255 ? ((current ^ 0) & 255) : 0`. The repair authenticates the
original C bytes and every normalized Clang expression, including the guard,
selected pure byte identity, inactive zero literal and complete ternary span.
For successful `getchar()` byte values only, comparisons with the two exact
range endpoints and `& 0` have invariant truth values. Reusing the genuine
guest SSA byte is sound without host input evaluation or a fabricated branch.

The source now emits five copies of its first input byte and then the second,
from two genuine guest reads and six writes, in nine normative VM steps on
four boundary and sixteen seeded binary pairs, plus 32 stratified
successful first-byte values. Two alternative polarity and
zero-trip programs also match the VM. Negative examples, every affected
Clang line-six node parent/span, forged literal fields, SHA-updated changed
source and missing source fail closed. This proof does not support EOF,
failed output, dependent control, nonidentity arithmetic or arbitrary storage;
the general P0 obligation remains pending.

### Equivalent pure conditional arms over a live guest byte (2026-11-13)

An original source-C program with a live binary `getchar()` result, three-trip
induction, a selected `continue` branch and trailing guest input initially
refused `putchar(current > 127 ? (current + 0) : (current & 255))` at
normalized lowering. The adapter now authenticates pure comparisons (`<`,
`<=`, `>`, `>=`, `==`, `!=`) and a bitmask test (`&`) of a successful byte
against a decimal constant in `[0, 255]`, including exact pinned Clang
parentage, i32 types, source coordinates, operands and literal values.
The branches must each independently prove a pure identity of that same
resident byte; thus either runtime outcome produces the same byte, without
host evaluation or invented guest control flow. Existing zero guards also
support two identity arms.

The original complete C source emits four copies of its first binary byte
and the second in eight normative VM steps across four comparison boundaries
and sixteen seeded pairs. A parity-mask variant and a zero-trip variant
also execute in the real VM. Nine further guard/identity forms pass the
source admission gate; unequal or effectful arms, input/output guards,
unsupported operations, forged Clang nodes, changed original C and absent
source fail closed without guest artifacts. This is not general C branching,
arithmetic, storage, EOF or failed output; P0 remains pending.

### Zero-dependent C conditional byte identities (2026-11-13)

An original complete C stream with a live binary `getchar()` byte, three-trip
induction, a remainder-selected `continue` branch and a trailing guest input
first refused `current ? (current + 0) : 0` at normalized lowering. The
repaired proof authenticates the full source-C spelling and every pinned
Clang child, parent, span, type, operator and literal. Its only admitted
runtime-dependent predicates are a pure, successful resident byte, that
byte's zero equality or inequality, and its logical negation. The two
branches are restricted to source-proven pure byte identities and literal
zero in the matching order. Since either arm selects the identical runtime
byte, typed IR reuses the existing guest SSA identity without host-time
prediction, another input or invented guest control flow.

The original stream emits five correct bytes from two real inputs in eight
normative VM steps, verified on two binary boundaries and sixteen seeded
streams. Three reversed/zero-comparison guards, nested arithmetic composition,
zero-trip behavior, invalid expressions, altered source and forged normalized
Clang evidence have independent tests. General guest-dependent branches,
nonidentity arithmetic, memory, EOF and failed I/O remain outside this
bounded proof; P0 remains pending.

### Effectful identities compose genuine guest I/O (2026-11-13)

An original C program combined a source-local binary input, a three-trip
induction loop, a remainder-selected `continue`, and the effectful expression
`putchar((putchar(getchar()) + 0) ^ 0)`. Pinned Clang accepted the entire
program; normalized lowering initially refused it because the prior
identity proof could only begin from a resident C local. The repaired
recursive proof accepts an exact source/Clang-authenticated `getchar()` or
nested successful `putchar` return at the leaf, retaining all real guest
read/write effects in order. Only the ten exact identity operators compose
on top; neither guest data nor C arithmetic is evaluated on the host.

The original program now writes three copies of its first binary byte and
two of its second in eight actual normative VM steps. Two boundary and
twelve seeded binary streams match an independent oracle. Direct input
identities, two-deep nested output returns, a zero-trip loop, unsupported
nonidentities, hidden effects, forged Clang ancestry, changed SHA-adjusted
source and missing source have dedicated regressions. This does not establish
guest-dependent branching, arbitrary guest C arithmetic, storage, EOF or
failed output; the generalized P0 remains pending.


### Composed C integer identities of a live guest byte (2026-11-13)

An original C stream combining a `getchar()` local, counted induction,
remainder-selected `continue`, subsequent input and nested arithmetic first
failed normalized lowering at `putchar((current + 0) ^ 0)`. The adapter now
proves recursive compositions of the ten exact existing byte identities.
Only a source-authenticated left operand containing the same live local,
matching literal right operands, exact Clang ancestry/types/spans and an
unmodified C witness can reuse the guest SSA byte. Identity subexpressions
may be parenthesized and remain bounded in depth and total source length.
No runtime arithmetic is evaluated by the compiler.

The original C program now compiles through actual layout and emits four
copies of its first binary input plus its second in eight normative VM steps.
Two boundary and twelve seeded streams match an independent oracle. Three
additional compositions spanning masks, modulo, arithmetic and bit shifts
also compile and match the VM. Zero-trip, nonidentity, hidden-effect,
forged-AST, changed-source and missing-source cases fail safely. This is
byte-preserving expression composition, not guest-dependent control,
general arithmetic, memory, EOF handling or output failure. P0 remains open.

### Exact integer identities preserve successful runtime bytes (2026-11-13)

A full C source with a live `getchar()` local, counted induction/remainder
branch, `continue`, and binary guest I/O first rejected `putchar(current &
255)` at normalized lowering. A separate guest-dependent parity/bitwise
branch experiment also rejected; dynamic guest control is still unsupported.

The bounded source-and-Clang proof now admits `putchar(NAME OP CONSTANT)`
for ten exact integer identities on successful guest bytes in `[0, 255]`:
`& 255`, `% 256`, `| 0`, `^ 0`, `+ 0`, `- 0`, `* 1`, `/ 1`, `<< 0`, and
`>> 0`. Every literal, operator, local reference, C source byte, Clang
parent, type and span is checked. No host evaluation or fresh guest input
is substituted for the real byte, and other arithmetic fails closed.

The original complete loop now produces four copies of its first binary input
and one of its second in eight normative VM steps, matching zero/255 and
12 deterministic seeded streams. Four additional full C/VM variants for
modulo, XOR, multiplication and right shift match independent boundary
oracles. The pinned frontend and adapter admit all ten operator shapes; the
admission-only test deliberately fails the layout stage, so it does not claim
VM evidence for those other shapes. Twelve nonidentity/unsupported expressions,
changed Clang parent/span evidence, absent source and SHA-adjusted source
spoofs refuse without a guest artifact. General C arithmetic, memory,
EOF, output failure and guest-dependent branches remain P0 blockers.

### Successful output return can rebind an already-live byte (2026-11-13)

A complete C source with a live input local, a counted induction loop,
remainder-selected branch, `continue`, and nested output expressions first
failed at normalized lowering on
`putchar((current = putchar(current), current));`. Its fresh-input-free
assignment is now source-proven against the pinned Clang call, declaration,
operator, parent and span ancestry and exact original C bytes. Each successful
`putchar` writes the currently resident guest byte, while the assignment
retains that value under the authenticated C local without a new guest input.
One to sixteen nested output calls and a final comma assignment are supported.

The normative VM matches an independent binary oracle for the full three-trip
program: two actual guest reads, seven output bytes, ten steps. A two-deep
return writes nine bytes in twelve steps. A fresh `getchar()` assignment
followed by an output-return reassignment inside the comma expression yields
four reads, seven outputs, twelve steps; a zero-trip loop emits only its
post-loop I/O. Invalid C, stale local reads after an unrelated input, forged
Clang ancestry and modified SHA-matched source must refuse publication.
This is resident single-byte reuse, not general guest C storage, arithmetic,
EOF, output failure or runtime-dependent control. P0 stays pending.

### A comma output operand can assign the fresh guest byte (2026-11-13)

An original complete C program with a live local, counted induction,
remainder-selected branch, `continue`, and real binary input/output tried
`putchar((current = getchar(), putchar(current = getchar()), current));`.
Pinned Clang admitted the source but normalized lowering originally refused
the program. A bounded proof now authenticates the nested output's assignment,
Clang parent/type/span sequence, the exact original C tokens, and the comma
separator. That nested effect performs one real guest read and output while
rebinding the only resident C byte for later comma operands. The same proof
admits a final nested output operand followed by the closing parenthesis.

The original entire source now emits seven bytes from six binary reads in
fourteen normative guest steps, matching two boundary and twelve seeded
independent streams. Source and normalized-node forgery regressions remain
fail-closed. This does not implement general C expression values, EOF,
failed output, guest-dependent branching, or arbitrary storage; P0 remains
open.


### Rebinding a comma operand from a successful output return (2026-11-13)

An original complete C program with a local, counted remainder branch,
selected continue and real input/output initially failed normalized
lowering on a comma operand assigning the result of
putchar(getchar()) to the live local. The source-/Clang-authenticated
reassignment proof now retains that successful returned guest byte,
accounts for its nested outputs in order and permits a later comma
operand to read the rebound name. The final comma operand may itself
be the assignment when followed by the proven closing parenthesis.
No previously clobbered C alias is reconstructed.

Actual normative guest VM execution agrees with independent binary
oracles for two boundary and twelve seeded six-input streams: six reads,
seven writes and fourteen steps. A nested two-output-return form produces
six reads, nine writes and sixteen steps; a final-operand assignment
preserves the same seven-write oracle. A zero-trip loop executes only
two reads and two writes in five steps. Unsupported C expressions,
forged pinned Clang parents/spans and SHA-adjusted original C operators
or names refuse without guest publication. This remains successful
single-byte replay, not general runtime C storage, arithmetic, EOF,
output failure or dependent control flow.


### A comma assignment can feed subsequent guest effects (2026-11-13)

A complete original C program declares a live input local, enters a three-trip
induction-remainder branch with `continue`, and uses a comma-valued `putchar`
argument to assign a fresh input before reading the rebound name multiple
times. The pinned Clang frontend accepted the original source, but normalized
lowering refused it before guest emission. The comma-tree proof now counts only
actual comma operators, admits a source-checked five-node assignment operand,
and carries the assigned byte through later pure reads or nested successful
`putchar(current)` calls. A new read without a proven assignment invalidates
the C binding; original-C identifiers must match their Clang references.

The normative guest matches two boundary and sixteen seeded binary streams at
four real reads, five outputs and ten VM steps for repeated pure references.
An effectful middle `putchar(current)` matches two boundary and twelve seeded
streams at four reads, seven writes and twelve VM steps. A zero-trip variant
leaves the original byte live. Five regression methods cover independent guest
oracles, stale/unsupported expressions, mutated Clang ancestry, missing source,
and SHA-adjusted original-C expression and identifier spoofs. Guest-dependent
conditions, arithmetic, general C storage, EOF and output failure still block
P0 completion; this is successful-byte residence only.

### Comma-output argument can rebind and reread one C local (2026-11-13)

A complete C program with a live input local, three-trip induction loop,
remainder-selected `continue`, and final guest input tried
`putchar((current = getchar(), current));`. Pinned Clang accepted the entire
program, but the normalized JSON-to-typed stage initially refused it.
The source-authenticated proof now reuses the existing five-node C input
assignment proof inside the exact twelve-node comma/output ancestry. It
verifies C token spelling and Clang spans, then reads one actual guest byte,
rebinds only the assigned local, and outputs the freshly assigned value.

The normative guest VM matches two boundary and sixteen seeded independent
binary oracles with five reads, eight writes and fourteen steps. Selected
and skipped branches preserve the right C byte, while a zero-trip loop
skips all effects. A stale top-level local may be rebound after an unrelated
read; old aliases remain inaccessible. Unsupported expressions, forged
Clang ancestry, absent original source and SHA-adjusted source changes
refuse. This is bounded successful-byte identity, not general C memory,
EOF, I/O failure, arithmetic or runtime-dependent branch execution.

### Loop-local effects rebind an outer C local (2026-11-13)

A complete original C source declares a live local, then reassigns it in
each iteration of a two-trip induction loop with a comma expression:
`current = (putchar(getchar()), getchar());`. A remainder-selected
`continue` branch consumes that newly bound byte. The pinned Clang
frontend accepted the full program, while normalized lowering initially
refused the outer declaration because discarded reads lacked direct
reassignment targets.

The source- and Clang-authenticated finite-loop proof now follows each
ordered input/output effect. A discarded fresh input may temporarily
invalidate the outer byte, but output of that C local is admitted only
after a proven assignment restores its identity. This rule also handles
a selected inner branch; skipped branches preserve their prior byte.
The normative guest VM matches 18 binary-input oracle streams at six
reads, five writes and twelve steps. Selected/skipped rebinding and
zero-trip proofs match four reads/four writes/nine steps and two
reads/one write/four steps. Stale intervening reads, unsupported
operands, changed Clang ancestry and source spoofing refuse. This does
not implement general C storage, EOF or runtime guest-dependent control.

### Ordered C comma-valued assignment into a proven local (2026-11-13)

A complete source-C byte stream assigned a parenthesized comma expression
to an existing C local in a selected if branch before a counted loop with
a remainder-selected continue. The pinned Clang frontend accepted the
whole program, but normalized lowering initially refused the assignment.
A bounded proof now authenticates assignment/destination/comma ancestry,
every nested byte-effect call, complete same-line extents and exact
SHA-checked original C token spelling. Earlier reads and writes execute in
order in the guest; the final successful byte alone rebinds the destination.

The normative guest VM matches an independent oracle on boundary and twelve
seeded binary streams: four actual inputs, six outputs and eleven steps.
A skipped branch preserves its original local with two reads and four writes
in seven steps. A stale top-level destination with three comma operands
matches six reads, four writes and eleven steps. Unsupported arithmetic,
stale C value operands, forged AST ancestry, absent source and SHA-adjusted
spoofed C source all refuse without publication. A later bounded,
source-proven loop-local reassignment proof is documented above. EOF,
failed putchar, general C storage and guest-dependent conditions remain
P0 blockers.


### Ordered source-C comma initializers (2026-11-13)

A complete C program used `int seen = (putchar(getchar()), getchar());`
then a three-trip `for` loop with an induction remainder branch and `continue`,
followed by another real guest read/write. Pinned Clang accepted it, but the
JSON adapter initially rejected the first declaration. A new bounded source
proof admits two to sixteen comma operands with fresh `getchar()` effects,
each optionally wrapped in nested successful `putchar()` calls.

It checks pinned Clang call/binary/parenthesis ancestry, source coordinates and
the SHA-verified original C bytes. Guest instructions execute all reads and
writes in C order and bind only the final input/return to the new local.

The original program now emits five independently predicted bytes from three
actual binary inputs in nine normative VM steps over boundary and sixteen
seeded streams. A selected branch and counted loop emit seven bytes from eight
reads in sixteen steps; the skipped branch emits six bytes from six reads in
thirteen steps. Scopes cannot export local bindings, and noncanonical C,
forged normalized nodes, missing source and SHA-adjusted spoofing refuse.
General C comma operands, arbitrary storage, EOF, output failure and dynamic
C conditions remain unsupported; P0 stays pending.

### Successful output-call returns initialize source-C locals (2026-11-13)

The pinned Clang frontend accepts a complete branch/continue C loop whose
first declaration is int current = putchar(getchar()), but normalized
lowering previously refused the declaration. The new bounded source proof
checks the exact original C declaration, local binding, every nested
successful output call, its Clang parent/cast/reference/span and one real
getchar. Each putchar forwards the same guest byte, and the newly bound C
local can be reused or reassigned without inventing a host value.

This is also admitted for block-local declarations in statically selected
branches and bounded counted loops; declarations do not export bindings
outside their lexical block. The original four-trip program emits seven
copies of the first binary input and two copies of a subsequent input,
with 12 normative VM steps. EOF, output failure, guest-dependent control,
general storage and arithmetic remain unsupported.

### Output returns on both sides of a local assignment (2026-11-13)

The original complete C source with
`putchar(putchar(current = putchar(getchar())));` in selected arms of
a three-trip remainder-branch/`continue` loop initially failed at
normalized JSON lowering. The repaired proof authenticates all pinned
Clang call, cast, reference, parent and same-line spans for both
output-call chains, plus the exact SHA-checked source spelling and
existing local destination. The single guest input is written once
per actual successful `putchar` in innermost-to-outermost C order;
only the authenticated local can read the returned byte afterward.
Between two and sixteen output calls can straddle the assignment.

The actual normative Malbolge VM emits eleven oracle bytes for four
binary inputs in sixteen steps on zero/255 boundaries and sixteen
seeded streams. A top-level mix of one- and two-call chains on each
side emits nine bytes from four inputs in fourteen steps, and the
zero-trip loop skips the nested effects. Six tests cover whole-C
guest parity, source/AST refusal, stale aliases and zero trips;
sixteen altered Clang fields, ten shifted spans and a SHA-adjusted
operator spoof are rejected without publication. This is successful
byte identity, not EOF, failed `putchar`, general C storage,
arithmetic or runtime-dependent control. P0 remains pending.

### Nested successful output returns rebind one C local (2026-11-13)

A complete original C program uses a three-trip remainder-selected loop
with `current = putchar(putchar(getchar()));`, followed by a read of
`current` and `continue`. Pinned Clang accepts it, but the earlier
normalized adapter refused the output-return assignment. The source-checked
projector now proves each nested `putchar` call, function-pointer cast,
reference, parent ID and byte span against the SHA-checked original C.
The single real guest input is output innermost-first and rebound only to
the authenticated C destination. The exact grammar supports 1–16 nested
successful output calls, not general C call-result storage.

The original entire C stream reads four binary bytes and writes nine
independently predicted bytes in fourteen normative VM steps on two
boundary and twelve seeded streams. A three-deep top-level assignment
to a stale local writes five bytes from four inputs in ten steps; a
zero-trip proof skips all loop effects. Six focused regression methods
cover guest parity, six invalid C programs, sixteen forged Clang
fields, eight shifted spans, missing source evidence and a SHA-adjusted
C operator spoof. Older aliases remain stale after the fresh input.
Failed output, EOF, dynamic C control, arithmetic and arbitrary guest
memory remain P0 blockers.


### Successful output-call return assigned to a C local (2026-11-13)

A complete original C program first reads a runtime byte and writes it,
then runs a three-trip induction-remainder branch/continue loop whose
selected arms assign `current = putchar(getchar());` and output the rebound
`current`. The pinned frontend accepted the program, but the normalized
projector initially rejected the new assignment. A new eight-node proof
authenticates the enclosing C assignment, destination identity, nested
`putchar(getchar())` call, all Clang spans and the exact SHA-checked C
spelling. Its guest effects are an actual input and actual output, and
the successful output return rebinds only the proven C name. No host
substitution, old-value recovery or general C call-result computation
is involved.

The normative VM matches an independently computed seven-byte output
from four runtime reads in twelve steps under boundary and twelve seeded
binary streams. A stale top-level destination rebinds after a new input;
a zero-trip loop proves but skips the assignment. Seven focused methods
cover six unlowered expressions, eighteen forged AST/span mutations,
missing and SHA-adjusted source witnesses, and old-alias rejection.
Guest EOF, failed output, arbitrary C storage, arithmetic and
guest-dependent control remain unsupported, so P0 stays pending.

### Nested assignment-valued source-C byte output (2026-11-13)

A complete original C stream used
`putchar(putchar(current = getchar()));` inside a
remainder-selected `continue` arm of a counted loop, followed by reads of
the rebound C name. The pinned Clang frontend accepted the program but
the normalized adapter refused it before guest emission. The bounded
projector now source-authenticates every enclosing `putchar` call, its
parentage, function-pointer cast, span, and final assignment/read subtree,
including the exact SHA-checked original C expression and semicolon.
The one real guest input is written by each nested successful call in
inner-to-outer order, and only the proven destination becomes resident;
previous C aliases stay invalid after a new read.

The complete branch/loop program produces nine independent-oracle bytes
from four genuine guest reads in fourteen normative VM steps, under
boundary and seeded binary input. A top-level nested assignment and a
three-deep selected branch with a zero-trip loop each emit six bytes
from three reads in ten guest steps. Seven focused regression methods
cover these cases, five unsupported C expressions, fifteen altered
Clang nodes/spans, absent source proof, SHA-adjusted C operator spoofing,
and a stale alias. Dynamic C arithmetic, mutable storage, EOF and
guest-dependent control flow still have no general lowering; P0 remains
open.

### Assignment-valued output retains C byte identity (2026-11-13)

A complete original C program used `putchar(current = getchar())` in a
source-selected `continue` branch of a counted loop, then read `current` in
later trips and after loop exit. Pinned Clang parsed the whole C program, but
the normalized adapter initially refused the first declaration. The bounded
byte projector now authenticates all eight nested Clang expression nodes and
the exact `putchar(NAME = getchar());` token sequence from SHA-checked C
source. Each call consumes one real guest input, outputs that byte, and
rebinds only the proven C destination; older aliases cannot be resurrected.

The original selected-loop program emits six independent-oracle bytes from
four binary guest inputs in eleven normative VM steps. A second complete C
program with scoped assignments, static branch selection, a three-trip
counted loop and source-selected `continue` consumes ten guest inputs and
emits eleven independent-oracle bytes in 22 steps. The separate selected
branch, zero-trip loop and boundary/seeded streams also reach VM parity.
Unlowered arithmetic, stale aliases, ten AST mutations, forged source
operators and missing source witnesses are refused without publication.
Ordinary short scoped output calls remain admissible when the optional
eight-node assignment proof does not fit the remaining Clang nodes.
Borrowed-loop inputs are permitted only when every fresh read explicitly
rebinds that same authenticated outer C local. This is accumulator-resident
source-C identity, not dynamic C storage or general assignment expressions.

### Source-proven outer C byte across counted output loops (2026-11-13)

A complete C stream reads a runtime byte, copies it into a block-local
alias in a selected branch, and emits it through a four-trip induction
loop with alternating selected `continue` paths. Pinned Clang accepted
the full program, but the normalized adapter refused the loop's outer
C binding. The adapter now reuses the resident guest byte through
input-free, fully authenticated finite loops and nested counted loops;
it also accepts a previously proven equivalent top-level C alias.
The original C output loop runs in the normative VM under boundary and
seeded binary input: two guest reads, eight writes, eleven steps.
Zero-trip, nested and equivalent-alias variants emit four, six and five
bytes respectively with no synthesized reads.

The fallback requires the SHA-checked original source, validates the
spelling of every loop-local C and external identifier reference, and
prohibits any selected guest input while borrowing an outer binding.
An input-producing loop uses the existing independent replay path and
invalidates old aliases. Missing source, a same-length forged C source
with a different live local, stale reads and unsupported arithmetic
refuse without an output artifact. This is source-time bounded replay,
not general guest control, arithmetic, storage or EOF. P0 stays open.


### Multiple original-C scoped reads in one branch or loop (2026-11-13)

A complete C stream placed three distinct `getchar()`-initialized locals in
one statically selected `if` arm, interleaved a source-proven alias and outputs,
then ran a three-trip induction-selected `continue` loop. Pinned Clang accepted
it, but the normalized adapter previously refused the second scoped read.
The branch proof now accepts successive independently source-authenticated
scoped declarations, overwriting only the resident guest accumulator value;
stale C locals are not restored. Every scoped read, including the first local
in a counted loop without an outer binding, must match the SHA-checked
original-C spelling, not merely Clang-shaped JSON.

The full selected C stream consumes nine binary guest reads and emits nine
independently predicted bytes in nineteen normative VM steps. Its skipped-arm
variant keeps the original local live and emits six bytes from five reads in
twelve steps. A separate whole C loop with two new scoped reads per trip
consumes seven bytes, emits four independently predicted bytes, and halts in
twelve steps. Each program matches both boundary and seeded binary oracles;
six malformed or stale C variants, six forged Clang nodes, absent source proof
and forged C initializers refuse. This is still finite source-time control,
not guest-dependent branching, general C storage, arithmetic or EOF.

### Lexically scoped C byte aliases and fresh shadows (2026-11-13)

An original complete C program copied a live `getchar()` value into a
block-local `int scoped = current;` inside a source-selected top-level `if`,
then emitted through both names and ran a three-trip loop with fresh input,
induction-selected output and `continue`. The pinned Clang frontend accepted
it, but the source JSON adapter rejected the entire program because top-level
branches were forbidden from introducing scoped aliases. The bounded branch
proof now admits a source-authenticated identity declaration in either arm
without exporting its C name or synthesizing another guest read. The normative
VM consumes five bytes, emits seven independent oracle bytes and halts after
thirteen steps; the skipped-branch variant emits six in twelve steps.

A second whole C program declared a new `int current = getchar();` inside a
selected `if`, shadowing an outer live local. The branch proof now permits one
fresh, source-witnessed nested input per lexical block, invalidating the
older guest byte rather than assuming C memory can recover it. The normative
VM consumes seven binary bytes and emits six source-predicted bytes in
fourteen steps. The unselected shadow preserves the outer value and emits
five bytes in eleven steps. Boundary and seeded binary streams, unsupported
source expressions, forged Clang ancestry, a forged C constant masquerading
as an input initializer, absent source proof and stale outer-byte reads
all refuse or match as appropriate. This is finite source-C branch replay,
not dynamic guest C scope, mutable storage, arbitrary arithmetic or EOF.
The P0 remains open.

### Selected C branch retains authenticated guest input (2026-11-13)

An original C program initializes and aliases a live guest byte, assigns a
fresh `getchar()` to that same alias inside a compile-time-selected `if`,
then reads the reassigned name **after** the branch and runs a three-trip
counted loop with conditional output, `continue` and final input. The
pinned Clang frontend accepted it; the normalized adapter previously
discarded the updated local identity after the branch. The exact source
and five Clang assignment nodes already proved the new read. A selected
branch now exports that checked C binding to its outer scope; nonassignment
input effects and scoped declarations still erase or cannot export aliases.

The actual Malbolge VM reads seven binary bytes and emits six
independently predicted bytes in fourteen steps on a boundary stream
and a seeded stream. An unselected assignment keeps the original live
name; unsupported C edits, stale aliases, six forged AST mutations and
missing source evidence refuse. Guest-dependent conditions, EOF,
general mutable storage and runtime arithmetic remain unsupported.
The P0 remains open.

### Fresh guest input can overwrite a stale C local (2026-11-13)

An original complete C stream alternated `saved = getchar();` and
`current = getchar();` after both names had been proven, then copied the
current input back into an older local before running a three-trip
induction-selected branch/`continue` loop. The pinned Clang frontend
accepted the C source; the JSON adapter rejected its first attempt to
reassign a stale local. Fresh `getchar()` never needs the prior C value:
the adapter now authenticates the destination against any previously
validated top-level local declaration and proves the exact five-node
Clang assignment plus SHA-checked source bytes. It emits a genuine guest
read, makes that destination the sole live SSA byte, and invalidates all
other guest aliases. No retained stale byte is synthesized.

The complete program consumes eight independent binary bytes and emits
seven source-predicted bytes in sixteen normative VM steps on both boundary
and reproducible seeded input. Negative source variants, forged assignment
nodes, absent source witness, and stale value reads still refuse without
an artifact. This is byte-input rebinding, not general guest memory, EOF
handling, guest arithmetic or dynamic C control; the P0 remains open.

### Source-proven C byte aliases and identity rebinding (2026-11-13)

A whole C stream first failed after `int saved = current;` when it emitted
`putchar(current)`: the normalized projector remembered only the newest
alias to the resident guest byte. It now retains all independently
source-authenticated aliases of the *same* current guest SSA input, so
both original and copied names may be read. A new runtime `getchar()`
invalidates previous equivalents. The fixed source also runs three
induction-selected iterations with a per-trip byte alias, conditional
output, `continue` and a final guest read. The real Malbolge VM reads
five independent binary inputs, emits six independently expected bytes,
and halts in twelve steps across two binary input oracles.

A second original C program copies a newly read byte back into a stale
top-level local with `saved = getchar(); current = saved;`, then emits
through either live name and continues into the same bounded loop. A
four-node Clang assignment proof binds the destination to a previously
validated C declaration and the source to the **currently resident**
byte; exact `DEST = LIVE;` bytes come from the SHA-checked original C.
The copy produces no extra guest operation. The six-read guest emits six
independently predicted bytes and halts in thirteen steps on two binary
streams. Rebound aliases may be copied again while they stay live.

Unproven arithmetic or casting, stale reads or assignments, noncanonical
source spelling, forged normalized type/parent/reference/span fields and
missing source witness refuse without publishing output. The compile-time
loop proof only reuses old aliases for checked output calls, not for
unproved stores. There is still no general guest C storage, dynamic
control, arithmetic or EOF; this does not retire the wider P0.

### Source-witnessed live C local reassignment (2026-11-13)

A complete source-C stream reads `current`, reassigns it with
`current = getchar();`, then runs three induction-selected loop trips
with their own `byte = getchar();` reassignments, `continue` and a final
guest read. Pinned Clang accepted the program, but the normalized compiler
originally rejected its assignment. The repair authenticates the five
Clang assignment/destination/input nodes, their IDs, parentage, types,
declaration identity and source geometry, plus exact `NAME = getchar();`
spelling from the SHA-256-checked original source. Each assignment emits a
fresh guest input and replaces the current SSA byte for later `putchar`
calls; a dead loop body is authenticated without emitting input.

The 1,167-byte guest capsule consumes nine runtime bytes, emits the
independently expected five bytes and halts in fifteen normative VM steps.
Two binary input streams, six rejected source changes and eight forged
Clang-node variants plus a missing source witness verify the narrow slice.
Only an already live accumulator-local `int` can be reassigned; arbitrary
stores, stale locals, arithmetic, guest-dependent control and EOF remain
unsupported. The P0 remains open.

### Source-witnessed live C local copies (2026-11-13)

A complete C program reads `getchar()` into `current`, copies the live
byte through `int snapshot = current;`, emits it, then runs a four-trip
induction-branch loop with fresh input locals, selected `continue` and a
final guest read. The pinned frontend accepted the source but normalized
lowering initially refused the new declaration. The repair authenticates
all four Clang alias nodes, declaration/reference identity, source spans,
and exact `int NAME = LIVE;` spelling from the driver-checked original C
file. A copy rebinds the current guest SSA byte without adding a second
input instruction or substituting a host-provided byte. Chained top-level
copies, per-iteration loop copies, scoped selected-branch copies and
zero-trip dead-body proof use the same bound source witness.

The full guest executes six independent byte reads and six writes in
thirteen normative VM steps. Eight binary VM comparisons, including zero,
128 and 255, match independent byte-stream oracles. Twelve unsupported
sources, eight forged normalized nodes and a missing-source witness refuse
publication. This is accumulator-resident identity copying, not general
mutable C storage, arbitrary expressions, guest-dependent control or EOF.
The P0 remains open.

### Source-witnessed unsigned-byte casts in finite C streams (2026-11-13)

A complete four-trip source-C program reads fresh `getchar()` locals,
branches on authenticated induction remainders, emits
`putchar((unsigned char)current)`, selects `continue` and writes a final
runtime input. The pinned frontend accepted the program, but normalized
loop admission initially rejected the unsigned narrowing. The compiler now
checks both `integral-cast` nodes, all declaration-reference ancestry,
source coordinates and the exact `(unsigned char)` bytes at the cast span.
The driver supplies the original C file to the JSON adapter after SHA-256
identity checks; JSON-only callers cannot assert this cast without a source
witness. Signed narrowing, hidden arithmetic and forged equal-width signed
cast metadata fail closed, without a guest artifact.

Under successful byte input, narrowing to unsigned char and promoting back
to int preserve each 0–255 value; the emitted Malbolge still executes all
five independent input and output effects. Two binary VM oracle streams
(including zero, 128 and 255) match in eleven steps. This is not dynamic C
arithmetic, arbitrary casts, EOF behavior or guest-dependent control.

### Source-authenticated early C return in live guest streams (2026-11-12)

A complete C program reads fresh runtime bytes inside a four-trip `for`,
uses an induction-dependent `if` to emit nested output then `return;`,
and leaves a final input/output statement after the loop. Pinned Clang
accepted the program, but the normalized adapter initially refused its
containing `for`. The repair authenticates the exact six-byte Clang
`return-statement` span, ID, parent and empty metadata. Its selected
control exit propagates across any bounded nested loops to terminate the
function rather than only the innermost iteration.

The original guest reads three independent binary bytes, writes four
oracle bytes and halts in eight normative VM steps. The unselected-return
variant preserves four iterations plus its trailing read; a shadowed
nested-loop variant returns through both loops. Unreachable suffix
statements are still source-authenticated without emitting their effects;
unsupported dead arithmetic, guest-dependent predicates and forged
return nodes refuse publication. Five regression methods exercise
live binary streams, top-level return shapes, six invalid source
variants and nine forged fields.

This is source-time selection over proven finite C state. Dynamic guest
control, general arithmetic and storage, and EOF remain unimplemented.
The P0 remains open.


### Pure C conditional operator in finite guest byte loops (2026-11-12)

A complete C stream uses `for (int i = 12; i >= 8; i--)`, fresh guest
`getchar()` locals, `if (i % 2 == 0 ? i == 12 : i == 11)`, nested output,
selected `continue`, later `break`, and a final runtime read. The pinned
frontend accepted the source but the normalized adapter refused the
containing `for` statement. The finite source predicate evaluator now
authenticates the pinned Clang three-child `conditional-expression`: each
pure condition and both arms must separately prove their exact counter
binding, parent IDs, types, positions, and canonical ` ? ` / ` : ` gaps.
Only the protected induction value is evaluated at compile time; selected
`getchar`/`putchar` remain real guest effects. Nesting is bounded by the
existing expression depth/node limits. This is not a guest-side C ternary.

The original source's six live guest reads produce seven binary-oracle
bytes in fourteen normative VM steps. The regression verifies grouped,
logical and nested ternaries, zero-trip body proof and shadowed counters;
unsupported byte-dependent arms and forged Clang nodes fail closed.
Division predicates remain deliberately unsupported: normalized JSON has
no independent token witness to disambiguate a forged equal-width `/`
from the existing `%` proof. Dynamic guest C control, mutable storage,
EOF and arbitrary byte arithmetic remain P0 gaps.

### Source-proven remainder predicates in finite C loops (2026-11-12)

A complete descending `for (int i = 12; i >= 8; i -= 1)` C program reads
fresh `getchar` bytes, selects a nested output and `continue` using
`i % 2 == 0`, takes a later `break` on `i % 3 == 0`, and performs one
trailing guest read. Pinned Clang accepted the program; the normalized
adapter initially rejected its `for` statement. The corrected source-time
predicate proof authenticates the entire `i % N` subtree: the protected
induction declaration, `i32` lvalue cast, canonical nonzero decimal
literal, operation, parent IDs, types, and source coordinates.

A remainder may select a Boolean arm directly, under `!` or parentheses,
or when compared with a canonical decimal integer using an existing
comparison operator. These expressions can be combined with the already
bounded logical predicate proof. Each admitted source-time branch still
emits real guest input and output, and all unselected Clang descendants
must authenticate. The original source emits a 1,159-byte capsule; its
normative VM consumes six runtime bytes and outputs the independent
`00 00 ff 80 01 01 09` oracle in fourteen steps. Nested shadowed
induction retains the correct lexical declaration, and false-entry loops
validate the unreachable remainder body without guest effects.
Six complete predicate shapes match twelve binary VM oracles, and nested
shadowing plus zero-trip execution match four additional VM oracles.
Eleven unsupported source changes and eleven forged Clang node mutations
refuse guest artifact publication.

This is not guest-side modulo execution or runtime C control. Divisor zero,
noncanonical/signed source literals, guest-dependent operands and
unrecognized arithmetic fail without an artifact. The P0 remains open.


### Two-digit finite induction starts (2026-11-12)

The exact pinned Clang `for (int i = N; ...)` proof now derives the
initializer's source width from a canonical one- or two-digit decimal literal.
All declaration, condition and bound spans advance together; each node remains
independently checked before guest instructions are emitted. The admissible
source-time starts are 0–99 ascending and 1–99 descending, with at most
16 finite trips in either direction, including zero-trip loops.

This capability preserves actual guest input and output, nested counter
shadowing, selected `continue` and `break`, and source-proven direction-matched
unit steps. A complete descending program starting at 12 first failed at
normalized `for` admission, then produced a 1,135-byte capsule whose normative
VM emitted the independent `00 ff 80 80 07` oracle in 11 steps.
Five two-digit loop shapes match ten independent binary guest oracles, and
nested shadowed induction matches two more. Six unsupported C sources and
seven forged Clang node changes refuse publication. Three-digit starts,
signed or noncanonical initializers, non-unit strides, guest-dependent
predicates, general mutable storage and EOF remain outside this slice.


### Nonzero ascending finite C induction (2026-11-12)

The source-authenticated finite `for` proof now accepts ascending starts
from 0 through 9, rather than only zero or one. Descending starts remain
1 through 9. The initial signed comparison determines zero trips and the
exact induction value for every selected trip; only 0–16 iterations may
execute. Pinned Clang integer literals, one-character source geometry and
counter ancestry remain mandatory, so two-digit starts, non-unit steps,
and dynamic input-dependent conditions still refuse guest publication.

A whole ascending stream starting at 2 combines a `getchar()` local,
branch-selected nested output, `continue`, `break` and a trailing runtime
read. Four start/condition/step shapes match eight binary VM oracles;
a shadowed mixed-direction nested stream matches two more. Five source
refusals and five forged initial-node variants reject without artifacts.
The guest executes all selected I/O; C storage, dynamic arithmetic,
runtime branch conditions and EOF remain unsupported.

### Assignment-form unit steps with live guest streams (2026-11-12)

A complete four-trip source-C loop with `int current = getchar();`,
branch-selected nested `putchar` output, `continue`, a later `break`,
and a final live input initially failed at `for-statement` admission
when its step was `i = i + 1`. The adapter now authenticates the entire
pinned Clang assignment subtree, including the protected induction
reference, `i32` read cast, direction-matched `+` / `-`, the exact literal
one, IDs, parentage and source coordinates. Both `i = i + 1` and
`i = i - 1` support source-time forward/reverse finite loops; actual
guest inputs stay runtime values.

Five original program variants (including inclusive bounds and zero trips)
match two independent binary guest VM oracles each. Eight invalid source
steps and nine independently forged AST changes refuse output publication.
This is finite source-time induction proof, not guest-side C arithmetic,
mutable state, dynamic loop conditions or EOF. The P0 remains pending.

### Proven zero-trip C loops with authenticated dead bodies (2026-11-12)

A complete source-C byte stream begins with a false-entry counted loop
containing a fresh `getchar()` local, nested output, a branch and
`continue`; an executed three-trip loop then performs live input,
branch-selected nested output, `continue`, `break` and final I/O.
Pinned Clang accepted the source, but normalized admission refused its
first `for-statement`. Both strict and inclusive increasing conditions
and strict decreasing conditions can now prove zero trips by their actual
signed initial comparison, without inventing a guest read or output.

The body and every nested Clang node are independently authenticated once
even though the execution trace contains no effects from that loop. This
is not a permissive dead-code omission: unrecognized source statements
and forged normalized ancestry still fail before publication. Finite
source-time iteration now admits 0–16 trips; selected zero-trip bodies
cannot substitute host effects for guest execution. Runtime-dependent
C loops, arbitrary guest arithmetic, general storage and EOF behavior
remain outside this proof; P0 remains pending.

### Finite descending C induction with live byte streams (2026-11-12)

A complete descending `for (int i = 4; i >= 1; i--)` program captures
fresh `getchar()` locals, selects nested output and `continue` at `i == 3`
or `i == 2`, breaks at `i == 1`, and emits one final live read. The pinned
frontend accepted its source, but the normalized compiler first refused the
`for-statement`. The source proof now admits `>` and `>=` only with canonical
`--i`, `i--` or `i -= 1`, authenticates the bounded induction ancestry,
and uses the actual decreasing value on every statically proven trip. The
one-digit initial value is limited to 1–9 and loops to 1–16 nonempty trips.
Runtime guest input remains independent of source-time control.

The original program emits seven independently computed output bytes from
six real binary guest reads in fourteen normative VM steps. Seven loop
shapes match fourteen binary guest oracles; a mixed forward/reverse nested
loop matches two seven-byte input/output oracles in fifteen steps.
Thirteen invalid C sources and ten individually forged Clang mutations
refuse target publication. Mutable C state, runtime guest-dependent
control, guest arithmetic and EOF remain unsupported; P0 stays open.

### One-based and inclusive finite C byte loops (2026-11-12)

A complete C byte stream with `for (int i = 1; i <= 4; i++)`, fresh
`getchar()` locals, `i == 2 || i == 3` selecting nested output and
`continue`, an `i == 4` break, and final live input originally refused at
normalized `for-statement` admission. Its source proof now checks a canonical
zero- or one-based initial `int i`, either strict `<` or inclusive `<=`,
the comparison's exact column and byte geometry, a unit-increasing step,
and the correct C induction value on every source-time trip. Only 1–16
nonempty trips are admitted; guest input bytes remain runtime values.

The original emits seven independently expected binary bytes from six
actual guest reads in fourteen normative VM steps. Six loop shapes,
including zero-based `<= 0` and one-based `<= 16`, match twelve binary
VM oracles. Nine unsupported C sources and ten forged normalized changes
fail without artifact publication. Equal-width `!=` is deliberately refused:
without a source-token witness a forged `!=` cannot be distinguished from
`<=` using normalized Clang spans alone. Runtime guest-dependent C control,
arithmetic, EOF, and general mutable guest storage remain outside the
bounded proof; P0 stays pending.

### Canonical increment spellings in bounded C byte streams (2026-11-12)

A full C stream used fresh `getchar()` locals, a source-proven `i &&
!(i == 3)` predicate, nested output, selected `continue`, a later
`break`, and a trailing guest read. Pinned Clang accepted `i++` and
`i += 1` as the counted-loop step, but the JSON adapter initially
refused both complete programs. The source proof now admits those two
canonical increment spellings alongside `++i`. The first two authenticate
exact unary operand spans; the compound step additionally proves the
single direct literal `i32` operand is exactly decimal `1`, with matching
Clang parent, IDs, metadata, and source coordinates. Induction values stay
bounded (1–16 trips) and protected from unverified mutation.

For the four-trip program, the real guest reads six independent binary
bytes, emits seven independent oracle bytes, and halts in fourteen
normative VM steps. Four postfix loop bounds and two compound bounds
have two seeded input comparisons each; a shadowed two-by-three loop
using compound outer and postfix inner steps also matches two nine-byte
binary VM oracles in nineteen steps. Ten postfix and ten compound
forged-node mutations reject, as do five unsupported compound source
steps. No runtime C branch, guest arithmetic, general C storage or EOF
behavior is claimed. The P0 remains pending.

### Source-proven scalar induction truth (2026-11-12)

A complete four-trip C stream selected `if (i && !(i == 3))`, emitted
nested outputs and `continue` on two trips, selected a later `break`, and
read a final guest input. Pinned Clang accepted the source, but the typed
adapter initially refused its `for-statement`. A red-first regression led
to exact proof for `i` as a Boolean scalar: only the current, protected
induction declaration's `i32` lvalue-to-rvalue cast may select a branch.
Both Clang nodes, their binding, metadata, parentage and source coordinates
must match; runtime input locals do not qualify.

The complete source produces seven oracle bytes from six runtime binary
reads and halts in fourteen normative VM steps. Direct `i`, `!i`, and
`i && i < 3` also pass on two binary streams each, for four shapes and
eight guest VM comparisons total. Eight unsupported source mutations and
eight forged Clang nodes refuse without target publication.

This only strengthens finite source-time loop selection. Runtime C control,
general C storage, guest arithmetic and EOF remain unsupported here; the
P0 is not retired.

### Grouped and negated induction predicates (2026-11-12)

A complete C program with a four-trip loop, fresh input locals, a nested
`!(i == 1 || (i >= 3 && i < 4))` branch, selected `continue`, later
`break`, and a final live guest read originally refused its normalized
`for-statement`. A red-first regression reproduced the refusal. The bounded
induction predicate proof now validates `!` and parenthesized children of
source-proven comparisons and logical trees, with exact Clang IDs, parents,
types, metadata, extents, and lexical token positions. Each prefix operand
is independently authenticated before the induction value selects effects.

The original program emits seven independently expected binary bytes after
six real guest reads and halts in fourteen normative VM steps on two input
streams. Four further Boolean shapes, including double negation and grouped
nested comparisons, pass eight seeded binary VM cases. Eight unsupported
source mutations and twelve forged normalized nodes reject publication.

This remains source-time proof over a finite induction counter. No runtime
C control over guest bytes, general storage, arithmetic or EOF is claimed.
The P0 remains open.


### Pure compound predicates over C induction values (2026-11-12)

A complete four-trip C function with a live `getchar()` local originally
failed normalized `for-statement` admission when `if (i >= 1 && i < 3)`
selected two nested outputs and `continue`, followed by a separate
`if (i == 3)` break and a trailing independent guest read. The predicate
proof now recursively checks bounded same-line `&&` / `||` trees whose leaves
are either canonical comparisons against the exact induction declaration or
already-proven pure `i32` constants. Each Clang parent, node ID, type,
reference, child span and token gap is checked; both operands are proven
regardless of the selected short-circuit result. No guest input can be used
to decide C control at compilation time.

The original 1,159-byte capsule consumes six binary guest inputs, emits seven
independent oracle bytes `00 ff 80 80 01 01 09`, and halts after fourteen
normative VM steps. The regression covers two input streams for each of
five conjunction, disjunction, nested-precedence, pure-operand and short
loop shapes, alongside seven source refusals and ten forged-tree refusals.
This is source-time branch replay over finite induction, not dynamic guest
C conditions, general C storage, EOF semantics or guest-side loop execution.
The wider P0 remains pending.

### Iteration-dependent branches in bounded source-C for loops (2026-11-12)

A complete four-trip C program captures fresh input into `current`, selects
`if (i == 1)` to emit twice and `continue`, selects `if (i == 3)` to `break`,
and otherwise outputs the captured byte followed by another runtime read.
An independent final read still executes after the early break. Pinned Clang
accepted the whole source, but the adapter initially refused its outer
`for-statement`. The bounded source proof now validates the exact `i` binding,
checked decimal comparison operand, Clang parentage, reference and extents,
then reevaluates each canonical loop body against its own compile-time
induction value. It preserves lexical body authentication even after a
selected exit and emits the resulting ordered *guest* input/output trace.

The original source compiles to a 1,167-byte capsule, consumes seven
independent binary inputs and emits `00 ff 80 80 01 2a 7f` in 15 normative
Malbolge VM steps. Bounds 1/2/4/5 and shadowed two-level induction loops
have binary VM parity regressions. Six relational operators have a seeded
independent-oracle test, with explicit source/forged-AST rejection coverage.
This is source-time induction selection, not runtime C predicate evaluation,
mutable guest C locals, arbitrary arithmetic or EOF support. P0 remains open.

### Source-proven continue in finite C byte loops (2026-11-12)

A complete three-iteration C loop captures one fresh `getchar()` byte on
any pass, writes it twice, selects a constant `continue` branch, skips a
separately authenticated `else` read and the remaining body read, and
then executes a final read outside the loop. Pinned Clang accepted the
source, but normalized admission refused the outer `for-statement`.

The adapter now authenticates `continue` as an exact eight-byte Clang
statement with the right loop ancestry and no additional metadata.
Every statement after the exit is still independently source-proven;
only the executed prefix is emitted. Unlike `break`, `continue` repeats
the fixed induction and performs a new guest read on each later trip.
A typed loop-exit marker keeps the two source-control meanings distinct.

The original program now compiles to a 1,143-byte capsule. For binary
stdin `00 ff 80 01`, the normative Malbolge VM emits precisely
`00 00 ff ff 80 80 01` and halts after 12 steps. The regression
includes counts 1/3/4, a nested two-by-two loop where `continue` exits
only the inner body, an inactive exit branch, six unsupported sources
and six forged-Clang mutations, each checked for non-publication.
C dynamic conditions, runtime-dependent loops, EOF and general guest
storage remain unsupported. The P0 remains pending.

### Source-verified early break in finite C loops (2026-11-12)

A complete source-C program has a counted `for`, a new `getchar()` local,
nested `putchar` returns, an `if (1) { break; } else` with guest input,
unreachable trailing loop I/O, and a final input/output after the loop.
Pinned Clang admitted the C source but the normalized adapter refused the
outer `for-statement`. The adapter now authenticates the exact five-byte
`break` Clang node (parent, ID, location, metadata) within a bounded loop.
It proves *all* lexical body effects, including inactive branches and
statements after the break, before truncating the executed trace. A selected
break exits the immediately enclosing finite loop after the current pass;
no skipped input is pre-consumed or synthesized by the host.

The original complete C program compiles to a real 1,095-byte capsule. The
normative VM reads two binary bytes, emits the first byte twice followed by
the second byte, and halts in six steps. Dynamic conditions, `continue`,
EOF-dependent behavior and generalized guest storage remain unsupported.
This is bounded source-C loop replay, not runtime guest control. P0 remains
open.

### Source-C counted loops selected by enclosing constant branches (2026-11-12)

A complete source-C program selects a nested two-by-two `for` matrix from
an enclosing `if (1)`, declares a fresh `getchar()` local for each inner
iteration, emits its successful-byte return twice, and reads another guest
byte at each outer boundary and at the end. The inactive `else` contains a
separately authenticated counted loop. The pinned Clang JSON originally
reached normalized source proof but failed at the outer `if-statement`:
its selected typed-IR replay attempted to resolve nested loop-local bytes
through only the enclosing-scope local cache. The corrected replay carries
a latest guest SSA identity inside the selected effect trace and updates
it at every runtime input, without reusing a previous iteration's byte.

The real guest VM consumes seven independent binary bytes, emits eleven
oracle bytes and halts in nineteen steps. The complete suite verifies six
binary VM oracles over one-by-one, two-by-two and skipped-branch loop
shapes. A second source program selects an `else` loop after an outer-local
read: two binary oracles verify four inputs, five outputs and ten steps.
Four source mutations, four forged Clang ancestry changes and a stale
outer-local use fail closed before guest publication. No dynamic C branch,
runtime-dependent induction, general guest storage or EOF is supported.
P0 remains open.

### Nested counted C loops with independent guest input (2026-11-12)

A complete two-level source-C matrix stream combines nested `for` induction,
per-inner-iteration `int current = getchar();`, selected and skipped constant
`if/else` branches, nested successful `putchar` returns and a distinct read
at the end of each outer iteration. Its pinned Clang JSON was initially
rejected at the outer `for-statement` rather than producing a guest artifact.
The extended source proof authenticates both inductions independently against
Clang parent IDs, variable identities, exact source spans and canonical loop
geometry. Each inner counted body is expanded in C execution order before
its containing counted loop; guest `ByteInput` and `ByteOutput` remain real
runtime effects with independent SSA identities for every read.

The original two-by-three program now compiles into a 1,231-byte binary
Malbolge capsule. The normative VM reads eight binary input bytes and emits
fourteen oracle bytes in twenty-three steps, including `00`, `ff` and `80`.
Three loop shapes (1x1, 3x2 and 2x3) match six independently constructed
binary guest-output and exact step oracles. Seven unsupported source shapes
and seven forged Clang node mutations refuse target publication.
Nesting is limited to two lexical counted loops, positive decimal bounds
1–16, and at most sixteen expanded effects inside each compound statement.
The 128-read/256-write total trace caps remain in force. Runtime-dependent
loop conditions, byte arithmetic, EOF and general C storage are not implemented.
P0 remains open.

### Lexically scoped input locals in counted C branches (2026-11-12)

One complete counted C loop now places `int chosen = getchar();` inside
its selected `if (1)` block, uses its successful-byte return through two
nested output calls, then reads and outputs another guest byte. A second
whole loop declares distinct locals in both arms of `if (0) ... else ...`:
the selected `else` emits its own input twice, while inactive-arm input
and outputs have no guest effects. Both compile to actual Malbolge and
match two binary VM oracles each: five reads, seven outputs, thirteen
steps. Source-verified declaration ancestry, exact compound coordinates
and literal-branch selection are required at every depth. Forged local
parent/reference changes and a stale read after a selected input reject.

The allowance propagates only inside the already authenticated counted
loop body, never through arbitrary top-level control or dynamic conditions.
Guest C block storage, input-dependent control and EOF remain unsupported.

### Counted loops with fresh local byte aliases (2026-11-12)

A whole C `for (int i = 0; i < 3; ++i)` program with a source-local
`int current = getchar();`, repeated and nested `putchar(current)` returns
previously refused normalized Clang admission despite its bounded induction.
The loop-body proof now authenticates the five-node declaration as a child of
the loop compound, including original variable identity and byte/line/column
spans. Each unrolled iteration allocates a new guest input SSA value and
repeats the real input instruction; source-local returns only reuse that byte
until a later read invalidates it. Successive distinct locals in a loop body
are permitted only in latest-live order. Source-constant nested `if/else`
arms can select outputs of that same live byte.

Counts 1, 3 and 4 pass six independent binary VM-oracle executions (three
outputs per loop input plus one trailing input/output, `4 * count + 3`
steps). A second complete two-iteration C program with two fresh locals per
iteration, selected nested output returns and skipped reads matches two
binary oracles: five real inputs, nine outputs and fifteen executed steps.
Negative source and forged-Clang ancestry tests reject stale local uses,
mutations and unsupported induction/body effects without guest publication.
This is not runtime C loop control, general storage, dynamic predicates,
arithmetic over guest bytes or EOF behavior. P0 remains open.

### Finite source-C counted loop with actual guest I/O (2026-11-12)

A full C program combining a counted `for (int i = 0; i < 3; ++i)` loop,
increment arithmetic, a literal `if/else` branch, discarded reads and
nested successful `putchar` returns initially failed normalized Clang JSON
admission at its `for-statement`. The adapter now authenticates the complete
pinned-Clang induction subtree, its automatic local identity, exact prefix
increment, positive decimal bound through 16 and all child byte-effect
statements before unrolling the **fixed** loop body to typed guest I/O.
Inputs are never supplied by the host: each iteration executes the actual
normative VM input and output instructions.

The original whole C program consumes ten binary input bytes and emits ten
independently expected bytes in 21 guest steps. Counts one and four agree
with independent oracles, as does a second program with a nested constant
branch followed by another loop-body output (seven bytes in fifteen steps).
Fifteen rejected C shapes and ten forged Clang mutations refuse publication.
Source geometry for multiline nested `if` statements now accounts for
nested indentation and brace-ending statements. General guest loops,
input-dependent branches, mutable locals, EOF and dynamic arithmetic still
refuse; P0 remains pending.

### Source-authenticated pure logical C byte-stream conditions (2026-11-12)

The pinned C frontend accepts a complete source program with a live input
local, `if (!(1 == 2) && (3 > 1))`, selected nested byte outputs, an inactive
input arm, and a trailing read. The JSON adapter initially refused this
source even though its condition is fully pure and constant. Its bounded
recursive proof now admits canonical parentheses, logical negation,
`&&` / `||`, decimal literals and existing relational/equality operators.
The proof checks each normalized Clang ancestor, source coordinate, full
parenthesized extent, and folded `i32` result. Both logical operands are
proved even if one short-circuits. The limit is eight lexical expression
levels or 31 predicate nodes; neither dynamic calls nor hidden effects can
be skipped as constant.

The real Malbolge VM matches `00 ff ff 80` in eight steps for the original
condition and a distinct parenthesized true condition. A false logical
condition reads the branch's two input bytes and emits `80 01` in seven
steps. Focused invalid-source and forged-metadata checks refuse without a
guest artifact. Full matrix runtime validation is resource-limited; this
work does not implement runtime guest C predicates, arithmetic, EOF or
mutable C storage. The P0 remains open.

### Source-proven decimal C comparisons around guest I/O (2026-11-12)

A complete C stream captures a live `getchar` byte, selects a multiline
`if (2 == 2)` branch with local reuse and nested successful `putchar`
returns, authenticates an inactive arm, and reads another guest byte.
The pinned C frontend accepted the source, but the JSON adapter initially
refused its first declaration. Its static predicate proof now covers
`==`, `!=`, `<`, `<=`, `>` and `>=` between two canonical nonnegative
decimal `i32` literals. The operator, operand ancestry and exact source
coordinates, comparison type and Clang folded truth value must all agree.
Branch effects remain source-proven in both arms before the compiler
selects either arm; a later input invalidates the current live local.

The normative VM reads binary `00 ff 80` and emits `00 ff ff 80` in eight
real steps from this complete C program. Focused invalid-source and forged
comparison-node checks reject without guest publication. The comparison
replay matrix is deliberately finite due to profiled VM memory cost; it
does not establish input-dependent C predicates, arithmetic, EOF handling,
mutable guest C storage or dynamic guest control flow. The P0 remains open.

### Canonical decimal C truthiness in constant byte-stream arms (2026-11-12)

A complete C source captured a guest input local, selected a multiline
`if (23)` block containing local reuse and nested `putchar` returns, skipped
its independently checked `else` branch, then selected the `else` of
`if (0)`. The pinned frontend accepted the source but normalized admission
initially refused it, even though the corresponding `if (1)` program worked.
The repaired byte adapter proves canonical, nonnegative decimal `i32`
conditions from `0` through `2147483647`, including literal width,
Clang type/value metadata, branch ancestry, and actual multiline opening,
body, and closing coordinates. Any nonzero literal selects the true arm;
zero selects the false arm. This is compile-time C truthiness only.

The actual 1,111-byte Malbolge guest reads `00 ff 80`, emits
`00 ff ff 80`, and halts after eight VM steps. The boundary tests cover
one-, two-, and ten-digit nonzero predicates, seeded binary stream parity,
unsupported expression spellings, and forged Clang metadata. Arithmetic,
negative or nondecimal predicates, EOF and runtime-dependent control flow
still refuse. The original input-dependent `while` / parity C experiment
was rerun and still refuses normalized admission without a guest artifact.

### Nested constant C conditions and else-if chains (2026-11-12)

A complete source-C function combines a live input local, an unbraced nested
`if (1) if (0) ... else ...`, comma-return output, an inactive nested arm,
and later independent reads. The pinned Clang frontend admitted the source,
but normalized JSON-to-typed-IR projection initially refused it. The source
proof now admits up to four nested literal `if (0)` / `if (1)` levels, including
`else if` chains and nested statements within canonical multiline compound
arms. Every selected and skipped child must match its direct Clang parent,
preorder ID, exact literal, byte extent and line/column coordinates; unknown
or nonliteral branch effects still refuse target publication.

The actual Malbolge guest reads three binary bytes and emits the four-byte
independent oracle in eight normative VM steps for twelve boundary and seeded
streams. A multiline nested-arm source matches three independent three-byte
oracles in seven steps, an inactive nested-arm source reads only the following
byte in three steps, and a selected `else if` source matches four binary
oracles in five steps. Four lexical nesting levels execute while five reject
without an artifact. Six unsupported C sources and seventeen forged Clang
metadata changes fail closed. This remains compile-time literal branch
selection and accumulator-only successful-byte I/O, not runtime guest C
conditions, EOF handling, general storage, arithmetic or loops. P0 stays open.

### Standalone comma effects in constant C arms (2026-11-12)

A complete source-C function uses a multiline `if (1)` block with
standalone comma output and mixed input/output statements, plus a skipped
`else` comma input chain. Pinned Clang accepted the source but the normalized
adapter initially refused. The existing direct comma verifier now accepts
literal-branch parent identity and projects every comma operand in order,
without adding the outer `putchar` write reserved for comma arguments. The
common effect projection reuses live locals until a new guest input replaces
the accumulator, and proves the entire skipped comma arm independently.

The normative VM emits three byte outputs from three guest inputs in seven
steps, matching eight seeded and boundary binary oracles. Forged comma parent,
operation and span metadata and an unsupported skipped-arm output reject
without publishing guest code. Guest-side dynamic C branches, arithmetic,
loops, durable storage and EOF handling are still outside the contract.

### Comma-result evaluation inside constant C branches (2026-11-12)

A complete C program captures a live input local, enters a multiline `if (1)`
arm, writes the return byte of `putchar((putchar(first), first))`, then
executes a distinct `putchar((getchar(), putchar(getchar())))` comma chain.
An inactive `else` arm contains an independently proven two-read comma output.
The pinned Clang frontend accepted the source, but the JSON adapter initially
refused the first declaration. The existing call/comma source proof now accepts
an explicit `if`-arm parent and expands every comma operand into ordered guest
read/write effects, placing the outer output last. Selected new reads still
invalidate an earlier live local. The skipped arm must also authenticate its
entire expression tree and cannot hide unsupported I/O or arithmetic.

The actual Malbolge capsule reads three binary bytes, emits four independent
oracle bytes, and halts in eight VM steps, as demonstrated across ten seeded
and boundary inputs. Ten unsupported C forms and twelve forged Clang AST
variations fail without publishing target artifacts. This is bounded,
compile-time constant-arm selection under successful-byte I/O; runtime input
conditions, EOF, arithmetic, mutable C state, and loops remain unsupported.
The original input-dependent loop/parity/arithmetic C experiment still fails
closed at normalized JSON admission. P0 remains open.

### Canonical multiline constant C arms (2026-11-12)

A complete C source with two multiline `if (1)` / `if (0)` blocks, both
with an `else` arm, initially failed at normalized JSON adapter admission.
The proven source-C projection now authenticates one-call-per-line compound
blocks with canonical indentation, exactly one newline per statement, exact
semicolon and brace byte gaps, and Clang byte/line/column, ancestry, and ID
coordinates. Every statement in both arms is proven, including the skipped
arm. Calls inside a selected arm preserve input and output order; a fresh
read invalidates a previous input-local alias. Existing single-line block
admission is unchanged.

The pinned C-to-Malbolge pipeline emits a real capsule performing three guest
byte inputs and four outputs in eight normative VM steps. Eight independent
boundary and seeded binary streams agree with an explicit C-order oracle.
Multiline blocks of 1, 2 and 16 `getchar()` statements execute at their exact
step counts; a 17th call refuses. Twelve unsupported C variants and 21
forged Clang AST alterations fail without target publication. This is
compile-time constant branch selection, not runtime guest C conditions,
loop arithmetic, EOF handling, failed I/O or general C storage. The original
input-dependent `while` / parity-branch program still rejects safely at the
JSON adapter and the P0 is pending.

### Single-line C compound arms around runtime guest I/O (2026-11-12)

A complete C program first failed normalized frontend admission when two
constant `if/else` branches used braced, ordered calls instead of one
unbraced call per arm. The source-checked byte adapter now admits a bounded
one-line `{ call(); call(); }` grammar with up to sixteen direct `getchar`,
`putchar(getchar())`, nested successful `putchar` returns, and live-local
`putchar` calls. It authenticates every Clang compound ancestor, both branch
arms, call identity, byte/line/column extent, and the exact statement gaps.
Only the selected arm performs guest effects; selected new input invalidates
the preceding accumulator-only local alias. Neither arm can hide an unknown
source effect, including an unreachable arm.

The original compound C witness emits three genuine guest reads and four
independently expected output bytes in eight VM instructions. Runtime C
conditions, multiline blocks, arbitrary expressions, local mutations,
EOF, failed I/O and general guest C loop or branch execution still refuse.
The full Fibonacci-style input-dependent control experiment continues to
reject at the normalized C adapter, without publishing an artifact.

### Constant C if/else arms around live guest bytes (2026-11-12)

A complete source-C function interleaves a live input local with literal
`if (0)` / `if (1)` arms, including skipped input, repeated-local output,
and direct guest I/O. Pinned Clang initially admitted the program, but the
JSON adapter rejected the input declaration. Exact AST parent, source
coordinate, literal and called-function proofs now select a single unbraced
statement and drop every skipped effect. An optional unbraced `else` arm is
also checked before selection; it does not reread stdin or produce output
when it is inactive.

The normative VM matches three selected binary input bytes and three output
bytes in seven instructions for the single-arm case. In a separate whole C
program with three `if/else` statements, ten binary guest input samples match
four oracle outputs in eight VM steps. Nested `putchar` return values,
standalone reads and captured-local returns work in selected arms. Eight
unsupported C forms and 18 condition/else AST forgeries refuse publication.
Runtime-dependent conditions, nonzero/nonone literals, braced arms and
arithmetic remain unimplemented. This is compile-time branch selection,
**not** dynamic guest C branching; the original C input/loop/arithmetic
experiment still cannot lower.

### Pure latest-local comma operands (2026-11-12)

A complete C function captures one byte with `int first = getchar();`,
then evaluates a plain `first` operand on either side of an inner comma in
three different `putchar` calls. Pinned Clang accepted the source with
unused-value warnings, but the JSON adapter originally rejected it at the
first declaration. The bounded projector now verifies both `lvalue-to-rvalue`
and local-reference AST nodes, their original parent and source coordinates,
and the identity of the latest live input. Reading a local for its C value
has no additional guest I/O effect, including when that value is discarded.

The emitted Malbolge source performs one real guest input and five outputs,
matching twelve seeded/boundary one-byte oracles in seven normative VM
instructions. Six invalid C variants and ten forged AST mutations reject
publication. This does not enable stale local reads after newer input,
mutating locals, arbitrary comma arithmetic, EOF or guest runtime C storage.

### Independent input declarations before nested local uses (2026-11-12)

A complete C function captures two successive `getchar` bytes into distinct
`int` locals, but deliberately uses each local **first** as the inner value
of `putchar((putchar(local), putchar(local)))`. A separate standalone comma
statement then combines a direct local output and a nested successful
`putchar` return. The pinned Clang source initially refused at the first
`declaration-statement`, because the projector coupled each local
initialization to a following direct output call.

The source-checked projector now emits a declaration's real guest `ByteInput`
independently of its eventual consumer. The established parent, reference,
source-span and call proofs then reuse the live SSA byte when the first
consumer is a nested or comma expression, with no hidden extra reads. In the
normative Malbolge VM, sixteen seeded/boundary two-byte inputs each produce
twelve independently expected outputs in fifteen instructions. Seven invalid
C source variants and thirteen forged Clang node changes refuse target
publication. Local values remain available only while their exact input is
the current guest accumulator; a newer read invalidates them.

This is successful-byte I/O and bounded source-authenticated straight-line
C, not general C storage, arbitrary expression evaluation, EOF handling,
failed output or dynamic guest control flow. The P0 remains pending.

### Live source-C input locals in comma return expressions (2026-11-12)

A complete C program captures two successive `getchar` bytes in distinct
`int` locals, repeats each byte through ordinary outputs, and then passes
`putchar(local), putchar(local)` as an enclosing `putchar` comma argument.
The existing source-C pipeline initially refused the first declaration.
The repaired Clang ancestry proof now accepts a bounded comma operand made
of one or more nested `putchar` calls around the current live local, with
source coordinates, parent identity, reference and cast metadata checked.
Every write executes in the actual guest VM using the original live SSA byte;
no operand secretly consumes another input. The proof also admits a local
operand before a fresh `getchar`, but refuses a stale local after a newer read.

The compiled guest reads exactly two binary inputs and emits nine independently
expected output bytes in twelve VM steps. Fifteen seeded/boundary streams
match the oracle, as do four additional live-local/mixed-input forms with
exact step counts. Two stale-local source variants and fifteen forged Clang
metadata mutations refuse publication. This remains accumulator-only guest
I/O under successful-read/write assumptions: EOF, runtime C storage,
arithmetic and dynamic C control flow remain unsupported.

## Nested successful-byte returns inside comma effects (2026-11-12)

A complete C function combines a runtime input local, a repeated nested
`putchar` return, a comma expression whose final operand writes twice,
a standalone comma statement with another nested write, and a final nested
call. It originally failed at normalized JSON admission. The shared pinned
Clang nested-call proof now accepts a comma-parent context and returns every
verified output ancestor instead of assuming one write per operand. The
adapter emits all writes in C inner-to-outer order, reusing the latest guest
input value without replaying host input.

Seven guest reads produce nine oracle writes in seventeen normative VM steps.
The bounded grammar accepts up to sixteen nested `putchar` calls per comma
operand, preserving the sixteen-operand comma-chain limit. Each call, cast,
function reference, source coordinate and ancestry must match; unsupported
arithmetic, extra casts, parentheses, EOF and failed output still refuse.

## Comma-result byte propagation in guest output (2026-11-12)

A whole C function with `putchar((getchar(), putchar(getchar())))`
and `putchar((putchar(getchar()), getchar()))` initially failed at
source-JSON projection. The repaired projection reuses the exact source
proof for each comma operand under a parenthesized output argument and
preserves all input and output effects in order. The final operand's
successful C return byte feeds the outer `putchar` without an extra read.

Four guest input bytes yield four independent oracle output bytes in nine
normative VM steps for twelve binary streams. A seventeen-operand argument,
nine unsupported C expressions and sixteen forged AST changes refuse guest
publication. The original two-input comma output remains admitted. This is
a bounded single-line successful-byte grammar: general expression trees,
EOF, failed output, C arithmetic and dynamic guest control remain open.

## Ordered mixed comma effects in guest C (2026-11-12)

A complete C program first failed at the JSON adapter when a standalone
left-associative comma statement mixed `getchar()` and
`putchar(getchar())`, after a local capture and nested output and before
another nested output. The source-checked projection now authenticates
all comma ancestors and each operand's exact Clang call, cast, reference,
source coordinates and lexical bounds. It emits each guest `ByteInput`,
including discarded reads, and each successful `ByteOutput`, including
writes whose return values are discarded.

The complete program reads five runtime bytes and writes the independently
computed five-byte oracle in 11 normative VM steps for 12 seeded/boundary
binary streams. Standalone two-, four- and sixteen-operand chains preserve
alternating reads and outputs with exact step counts; a seventeenth operand,
ten invalid source expressions and 17 forged Clang mutations refuse target
publication. The grammar supports only unparenthesized one-line comma chains
whose operands are direct `getchar()` or `putchar(getchar())`. C EOF,
failed I/O, parenthesized/general comma expression trees, guest-side
arithmetic, loops, branches and durable locals are still unimplemented.

## Standalone comma input sequencing (2026-11-12)

A whole source-C program now composes one automatic input local, nested
`putchar` return-value outputs, a three-call standalone comma chain,
`putchar((getchar(), getchar()))`, and another local-return chain. The
previously rejected comma expression is a real statement with three
successive guest input effects, even though C discards every result. The
pinned Clang preorder proves each left-associative binary comma ancestor,
source byte/line/column span, input call and external function identity.
The selected successful bytes execute inside the normative Malbolge VM:
seven reads produce five oracle output bytes in thirteen steps under twelve
independent binary streams. An input-only three-read chain emits no bytes
and halts in four steps; 2-to-16 comma reads are admitted and 17 refuse.

This remains a bounded, single-line straight-line comma expression with
only direct `getchar` operands. Comma chains containing `putchar`, arithmetic,
casts, parenthesized expressions, or extra effects refuse publication.
C EOF, output failures, guest-side C branch/loop evaluation and persistent
local storage are unimplemented. This fixes a real ordered guest-effect
semantic gap, not arbitrary C comma expressions or general I/O lowering.

### Source-sequenced discarded byte reads (2026-11-12)

A complete C source interleaves automatic `getchar` locals, a standalone
`getchar();` whose return is unused, nested `putchar` return values, and
repeated reads of the most recent local. The pinned Clang normalized source
previously rejected the entire function; the source-checked projector now
preserves the unused `getchar` as a real `ByteInput` effect, invalidates the
old accumulator-local alias, and continues the source-order trace. The guest
reads four bytes but emits only five, in ten normative VM steps. Fourteen
boundary and seeded binary input samples match an independent byte oracle.

A second complete C function passes `(getchar(), getchar())` as the argument
to `putchar`, then outputs a separately captured byte through nested calls.
The left operand must consume a guest input even though its value is
unobserved; the comma result is the right operand's actual byte. Both call
ancestors, the `i32` comma expression, parentheses, binary operator, lexical
bounds and source coordinates are authenticated against Clang. The normative
VM reads four bytes and emits four in nine steps, matching ten independent
binary oracles. A separate input-only C function executes two VM input steps
and one halt step with no output. Unsupported C mutations and forged Clang
metadata reject without target publication.

The admitted grammar is bounded and straight-line, with exact pinned Clang
subtrees. All guest reads must succeed with bytes; EOF remains unimplemented,
as do mutable C storage, nontrivial arithmetic, output failures, branches,
loops and arbitrary comma expressions. No input is synthesized on the host.

### Composed live local and nested call-return guest I/O (2026-11-12)

A complete C source captures two `getchar` results in automatic `int` locals,
passes each value through nested `putchar` return calls, repeats the same
local afterward, and interleaves a directly nested runtime `getchar` call.
Previously, the pinned Clang preorder was admitted but the JSON adapter
refused the first local declaration. The source-checked local projector now
proves each nested call/cast/reference trio, final local lvalue read,
identical live declaration reference, and every exact byte/line/column
endpoint. A new runtime input still invalidates the preceding local.

The actual guest reads three bytes and writes nine in C evaluation order,
without rereading successful input for nested or repeated outputs. A second
complete C program mixes a direct nested call with two nested reads of the
same later local. Binary boundary inputs and twelve seeded binary streams
per program match an independent return-byte oracle and exact normative
VM steps.

A separate sixteen-level local-return chain emits sixteen repeated
bytes in eighteen VM steps for zero and 255 input. Six unsupported source
variants and fifteen forged normalized AST/position changes refuse
publication. This is accumulator-only guest dataflow under successful I/O
assumptions; mutable C locals, EOF, failed output, arithmetic, branches and
general C control flow remain unsupported.

### Nested source-C call return values in a real guest (2026-11-12)

The complete C source `putchar(putchar(getchar()));` previously passed pinned
Clang but failed closed at normalized JSON admission. A source-checked
projector now authenticates up to sixteen nested `putchar` calls, their
function-to-pointer conversions, one innermost `getchar`, exact ancestor IDs
and all byte/line/column source endpoints. Under explicitly successful byte
input and output, each inner `putchar` returns its written byte. The guest
executes one input followed by the nested number of outputs, in C evaluation
order, using the existing latest-read accumulator-only backend.

Four full C programs (including three-level, sixteen-level and mixed
statement nesting) reach the normative VM. Two independent binary inputs
per program match the source-derived return-byte oracle and exact guest
step counts. Eight unsupported C mutations and sixteen adversarial normalized
AST/source-span mutations reject without target publication. The result does
not claim C EOF, output failure, general C function returns, mutable storage
or guest-side control flow; the P0 generalization is still incomplete.

### Dynamic source-C byte echo under successful input (2026-11-12)

The next complete source-C experiment uses three runtime `getchar`
results: one automatic `int` is output twice, a direct call is output
once, and a second automatic `int` is output twice. The pinned Clang
frontend admitted it, but the existing ten-node adjacent-local projector
initially refused the later output, before guest publication. The repaired
source proof authenticates each repeated five-node output, ties it to the
same local declaration and emits multiple guest outputs without rereading
stdin. The compiler selects the independently verified latest-successful-
read layout mode instead of weakening the strict echo mode.

The normative guest VM emits the independent five-byte oracle for both
`00 ff 80` and `41 0a fe` input, taking exactly nine VM steps. Eight
unsupported stale/effectful or over-limit C programs and thirteen forged
later-output AST/span changes reject without guest artifacts. This is
genuine guest
runtime value retention only in the accumulator; it is not mutable C
storage, general I/O flow, EOF semantics or guest C branching. The P0
remains open.

An additional complete source-C experiment now captures each successful
`getchar()` result in an automatic `int` local before passing that local
to `putchar`. The pinned frontend previously refused the first declaration.
The repaired Clang projection checks the ten-node declaration, initializer,
value-read and call ancestry and ties the exact local declaration reference
to the output argument. Adjacent direct calls can be mixed with local-forward
pairs, up to 128 total live reads. Every pair becomes a distinct runtime
`ByteInput`/`ByteOutput` SSA effect; the automatic local is only elided
after proof that no intervening use or mutation is present.

Two complete sources (a three-read mixed call/local trace and sixteen
distinct automatic locals) now produce real guest VM byte parity under
binary input. Eight unsupported source mutations and twenty-five forged
normalized AST node/span variants refuse before target publication. This is
source-local identity forwarding, not guest storage, input arithmetic,
reordering, C EOF behavior or runtime C control flow. The P0 remains open.

A demanding four-iteration C program with `getchar`, EOF checks,
stateful parity and conditional input transformations first exposed the
source-JSON projection gap: its first local declaration still refuses.
An independently useful narrower experiment now authenticates straight-line
C `putchar(getchar());` source calls. The pinned Clang preorder lowers
one to 128 adjacent read/write pairs into distinct typed SSA byte inputs
and outputs. Unlike bounded compiler-time Fibonacci replay, each output
here depends on a byte actually supplied to the running Malbolge guest.

The real C-to-guest pipeline produces normative guest code for 1, 3 and
16 successive pairs. A seeded test exercises every binary input byte
from 0 through 255 plus deterministic nontrivial binary streams; guest
stdout matches each submitted byte exactly. Separate mutated C sources
and forged Clang AST metadata reject before publishing artifacts. The
existing adjacent-echo layout checks its own guest VM witness.

This is a conditional **successful-byte** effect equivalence only; C EOF
returns -1 while the Malbolge VM has a different EOF accumulator word.
C `getchar` EOF, I/O failures, input computation, dynamic state, C loops,
control flow and the independent guest ABI remain unsupported. The P0
work item stays open, and source-C general byte-stream emission still
requires full semantics rather than a host-side output projection.

### Complete original unmasked Fibonacci guest (2026-11-12)

The pinned, complete twelve-trip `conditional_fibonacci.c` source now passes
Clang admission, bounded source-state replay, ternary lowering, layout
publication and normative Malbolge execution. An independent unsigned
recurrence calculates `02 59 5f 08 57 4f 22 6d 03 90 b3 23`; the emitted
guest produces all twelve bytes under both EOF and binary stdin, without
consuming input. The Python integration test compiles the original source,
checks guest artifact publication and independently executes the VM.

The extended search starts with a proved guest-written graphical source word,
revisits it after a real `j`, then uses a second real `j` to reposition D
behind executing code. A bounded state search tracks full accumulator words,
output prefixes, fixed memory operands and admissible graphical operands.
The independent positional layout checker and CLI publisher then validate
all code, D and write positions, the required first repeated rotation, guest
termination and two complete normative VM replays. This witness has more
than one repeated write address; the old exactly-one-repeat requirement was
valid only for the three/four-byte prefix grammar.

This is a finite, source-revisited output synthesis for one admitted complete
C trace, not general guest execution of C loops, conditionals or arithmetic.
The C control/state is still replayed at compile time. General source-C
lowering, arbitrary output streams and a seeded verification matrix remain
open under P0. The dated sections below document earlier bounded stages;
their then-current unmasked-layout refusals were superseded by this proof.

### Revisited guest source continues to a fourth byte (2026-11-12)

The original unsigned C Fibonacci source emits `02 59 5f 08` in four
iterations. Its three-byte prefix already needs a real rotated source word
revisited after a guest `j`; pristine graphical operands cannot reproduce
that prefix under the existing narrow grammar. A new bounded proposal extends
that guest-evolved prefix using checked data-pointer strides and a fourth
rotation of a fresh graphical source cell. The focused Rust test proves the
full four-byte guest output under EOF and binary stdin, with exactly one
repeated write, source-behind-code safety, and independent normative VM replay.
This does not generalize to the original twelve-byte Fibonacci trace or
establish guest-side C control flow. The complete pinned C-to-guest regression
remains a separate publication check.

### A `while` body directly contains a second `while` (2026-11-12)

The original full twelve-trip unmasked Fibonacci C source still refuses at
`Layout(UnsupportedEffectTrace)`. A separate complete masked recurrence then
exposed a normalized-C gap: an outer `while` with an unbraced inner `while`
body was rejected after pinned Clang admission. Both loops mutate separate
unsigned counters; the inner loop selects a real parity branch and writes
its mask before output. A bounded source proof now checks the outer predicate,
exact nested parentage, next-line indentation and identical body endpoint.
It replays both loops without introducing guest-side C state or control.

The independent unsigned recurrence and normative guest VM agree on all
12 bytes `02 19 1f 08 17 0f 02 0d 03 10 13 03`, 47 steps, under EOF
and binary stdin. An independently calculated two-trip inner-loop variant
with idempotent mask writes reaches the same real guest output. Seven
negative complete C variants and nine forged AST
nodes refuse before publication. Unmasked guest synthesis and dynamic
C control remain unsupported; P0 stays pending.

### A selected `do` break skips a lexical output (2026-11-12)

A complete twelve-trip unsigned Fibonacci C program now executes an inner
`do` loop per recurrence term. The selected odd branch emits its masked
byte, then executes `break` before a following lexical `putchar`; even
terms instead execute that very same following output. The post-test
predicate contains division by zero only in its odd arm, which the selected
break must not evaluate. Pinned Clang accepted this complete source, but the
normalized adapter initially refused its first local declaration.

The bounded source replay now accepts one source-authenticated unreachable
`putchar` following a selected loop-local `break`, just as it already does
for `continue`. The skipped statement has no published guest effect; when
control reaches it normally, the same statement executes and emits its
byte. This proof does not introduce runtime guest branching or arbitrary
unreachable C statements. Unknown calls, extra dead siblings, and
unsupported selected arithmetic remain explicit refusals. The independently
computed unsigned recurrence produces twelve masked bytes
`02 19 1f 08 17 0f 02 0d 03 10 13 03` under the normative guest VM
in 47 steps. The original unmasked Fibonacci layout and dynamic guest C
control remain unimplemented, so P0 is still open.

### A selected conditional `continue` skips the following C output (2026-11-11)

A complete twelve-trip unsigned Fibonacci C loop emits in its odd branch
before `continue`; its next lexical statement is the even-branch `putchar`.
Pinned Clang accepts the whole source, but the normalized C replay previously
rejected the first declaration because the selected exit left an unproven
sibling output in the enclosing compound loop body.

The bounded replay now authenticates exactly one source-backed `putchar` after
selected `continue` without applying that unreachable output effect. The
non-continued iteration still executes that same lexical output normally.
Additional siblings, unknown calls, writes, and selected undefined arithmetic
remain unsupported. Both branch polarities produce the independently computed
12-byte masked recurrence in the normative VM with empty and binary input,
47 guest steps each. Forged normalized output metadata and unsupported C
mutations must refuse without publishing a guest.

This proves ordered source-state selection, not dynamic C branch/loop lowering.
The original unmasked Fibonacci stream still refuses at guest layout, so P0
remains pending.

### Directly parented conditional `while` arms (2026-11-11)

A complete twelve-trip unsigned Fibonacci C program now selects one of two
unbraced `while` statements from `if/else`. The chosen loop iterates once
or twice, changing an unsigned mask before the next `putchar` call. Both
branches execute in the complete source, and each loop has a distinct
state-changing body; this is not a constant folded `if` with empty arms.
Pinned Clang admitted the source, while the JSON adapter initially refused
the first function-body declaration because the branch arm was a loop.

The bounded replay now independently verifies each loop against its own
source-checked Clang parentage and canonical multiline indentation, then
keeps only the selected local writes. Separate source negatives reject
nonterminating steps, hidden `getchar`, and protected counter writes.
The independent unsigned recurrence oracle and normative Malbolge VM agree
on `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps with EOF
and binary stdin for both the original and the inverted dispatch variant.
Seven invalid complete C sources and fifteen forged Clang nodes refuse
without publishing a guest, including an initially accepted end-column
forgery repaired by exact branch-to-arm endpoint checks.
This is compile-time C state replay, not general guest-side branching or
loops. The original unmasked Fibonacci output is still unsupported, and
P0 remains pending.


### `do` / `while` break skips a pure undefined predicate (2026-11-11)

A full twelve-iteration unsigned Fibonacci C program branches inside a
`do` body. Odd recurrence terms select `break` before testing a post-test
ternary; its unselected condition contains `1U / 0U`, which must not be
evaluated by C. Even terms do not break and evaluate the safe zero arm.
The pinned Clang frontend admitted the program, but the normalized adapter
previously evaluated the skipped condition and refused the source.

The bounded replay now authenticates a skipped pure `do` condition without
evaluating it after selected `break` or `return`; normal exit and selected
`continue` still use strict evaluation. The independent unsigned recurrence
and normative Malbolge VM agree on twelve masked bytes
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps under EOF and
binary input. Seven unsupported C variants and eleven forged ASTs refuse
publication, including a byte/column endpoint forgery closed by the shared
binary-expression span proof. A valid unconditional-break variant also
reaches the normative guest VM. This remains bounded source replay, not
guest-side dynamic C control; unmasked Fibonacci layout remains unsupported.

### An unbraced inner `while` as a C `do` body (2026-11-11)

A complete unsigned Fibonacci C program places a directly parented,
unbraced `while` inside an outer post-test `do`. Every inner trip advances
the recurrence and writes a selected output byte; a source-proven conditional
`break` exits only the inner `while`. Its changed state and completed-trip
counter drive the outer `do` predicate. Pinned Clang accepted the source, but
the normalized JSON adapter initially refused the first declaration.

The bounded replay now admits that exact two-line `do` / `while` ancestry
with checked byte, line and column placement, and requires the nested
braced `while` endpoint to match its enclosing Clang span. A forged
comparison operator exposed an existing source-authenticity gap; same-line
unsigned comparisons now check both operator width and byte/column gaps.
All fifteen forged AST variants and six unsupported C mutations refuse
before guest publication.

Two complete variants use two outputs across six outer trips or four
outputs across three trips. Both agree with the independent unsigned-C
oracle and actual Malbolge VM on twelve masked bytes
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps, under EOF
and binary stdin. This is bounded source-state replay, not guest-side C
loop execution or an unmasked Fibonacci layout; P0 remains open.

### Nested switch continuation with case-local recurrence writes (2026-11-11)

A full twelve-iteration Fibonacci C source selects two switch levels and
emits from the innermost case before updating both recurrence locals.
The even inner case continues the enclosing `for`, while the odd case
breaks both switches. Pinned Clang admitted the complete source, but
normalized source replay initially refused its first declaration.
The bounded projector now isolates an inner selected `continue` from all
alternate outer switch arms, then carries its checked state and output
through the outer dispatch. The only allowed unreachable outer suffix is
a source-checked switch-local `break`; hidden writes and I/O still refuse.

The independent unsigned-C oracle and normative VM agree on twelve
masked bytes `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps under
EOF and binary stdin. A second full program continues from each inner
default instead. Negative source mutations and forged Clang continuations
and outer breaks refuse publication. Three nested switches, general
guest-side C control and unmasked Fibonacci remain unsupported; P0 is open.

### `continue` from a C switch into its enclosing loop (2026-11-11)

A full twelve-iteration unsigned Fibonacci source moves recurrence updates
before a `switch` whose even case emits a byte and continues the enclosing
`for` loop, while its default arm emits and breaks the switch. Pinned Clang
accepted the complete program, but the source-state adapter initially refused
its declaration. The bounded replay now authenticates direct switch-local
`continue` with its exact Clang keyword span and retains the exit only for
the selected arm, after checking the other cases. The inverse variant
continues from the default arm. Both reach real Malbolge VM execution with
twelve independent masked-oracle bytes in 47 steps under empty/binary input.
Unsupported C mutations and forged normalized continuations reject publication.
Nested-switch continues, guest dynamic C branching and the original unmasked
Fibonacci guest layout remain unimplemented; P0 stays pending.

### Skipped pure unsigned unary arithmetic (2026-11-11)

A complete twelve-trip unsigned C Fibonacci recurrence evaluates a
short-circuit `&&` before a bitwise unary `~` applied to division. On the
first even term the division would be undefined if executed, so the
normalized frontend previously rejected the entire program. The
source-proof path now authenticates skipped `~`, unary `+`, and unary `-`
using the exact selected-unary source grammar without evaluating their
operands. The pinned C frontend and normative Malbolge VM produce the
independent masked recurrence `02 19 1f 08 17 0f 02 0d 03 10 13 03`
in 47 steps under EOF and binary stdin. Six invalid C variants and ten
forged normalized nodes reject without a published guest. The bounded
expression-depth limit, general guest-side C execution and original
unmasked Fibonacci layout remain unresolved; P0 stays pending.

### Nested pure arithmetic in an unexecuted C operand (2026-11-11)

A complete twelve-iteration unsigned Fibonacci C program puts additions,
subtractions, divisions and remainders inside both arms of a ternary
protected by an outer C short-circuit guard. Even terms skip the
entire ternary; evaluating either nested division or remainder would
divide by zero. The pinned C frontend admitted the source, but the
normalized adapter originally refused the whole program.

Bounded source replay now authenticates recursively every child of a
skipped pure unsigned arithmetic expression, including multiple undefined
operations, without materializing an arithmetic result. Selected
operands continue through strict checked evaluation. The two full C
variants choose opposite ternary branches on odd terms. The normative
Malbolge VM and separate unsigned-C recurrence oracle agree on twelve
bytes with EOF and binary stdin (43 and 41 steps, respectively). Six
unsupported source mutations and forged normalized operators/metadata
refuse before artifact publication. This is finite source projection,
not guest-side C control flow or arbitrary byte-stream synthesis; the
original unmasked Fibonacci layout is still unsupported.

### Skipped ternary inside a logical guard (2026-11-11)

A complete twelve-trip unsigned Fibonacci C program uses a source-proven
`&&` guard whose skipped right operand is a `?:` selecting unsigned
division or remainder. When the term is even, both would divide by zero,
so neither may be evaluated; odd terms execute the selected arm. A red-first
normalized-frontend refusal was repaired by authenticating both pure ternary
arms without evaluating a skipped one. The selected path still refuses
undefined arithmetic and unsupported effects. A forged Clang column on the
ternary previously reached expensive guest layout; exact start/end byte,
line and column agreement now fails closed.

The real VM emits an independently calculated twelve-byte recurrence for
the alternating division/remainder source. The original unmasked Fibonacci
byte stream still refuses at guest layout; dynamic C control and arbitrary
byte-stream emission are not implemented. The P0 remains open.


### Short-circuit C logical guards (2026-11-11)

A complete twelve-trip unsigned Fibonacci C program guards division with
`&&`; the pinned Clang frontend accepts it but the normalized adapter
initially rejected it because the RHS divided by zero on even terms.
The bounded source replay now checks the entire skipped pure Boolean RHS
without evaluating its division, preserving C evaluation order. The same
full program with `||` and opposite branch selection also compiles. Both
variants match the independent unsigned-C oracle on the real normative
VM: `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps, with
EOF and binary stdin. Selected zero division, hidden input/output, and
forged source nodes still reject before guest publication.

This is finite source proof with bounded expression depth, not general
guest-side short-circuit branching. Complex nested arithmetic can still
exceed the expression-depth bound; unmasked Fibonacci and arbitrary C
control flow remain unimplemented.

### Non-evaluated C ternary arithmetic (2026-11-11)

The complete twelve-iteration masked unsigned Fibonacci program now guards
`/` using a source-proven C conditional expression. An even term causes
its unselected numerator/denominator subtree to include division by zero;
the old eager JSON evaluator rejected the first declaration even though C
would not evaluate that operand. The bounded replay now authenticates the
skipped pure `u32` division/remainder and its parentheses without demanding
an arithmetic result, while selected operands still use checked evaluation.
Only the exact pure subtree with a zero divisor gains this exception.

A second whole-C variant has division in one alternative and remainder in
the other: each becomes undefined if evaluated on the opposite selection.
Both valid selections occur over twelve iterations. The separate unsigned-C
oracle and normative Malbolge VM agree on the twelve masked bytes
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps, under EOF and
binary input. Selected zero division, unselected side effects/input, and
four forged Clang arithmetic nodes reject without guest publication.
The original unmasked Fibonacci still rejects at
`Layout(UnsupportedEffectTrace)`; dynamic guest branching and general C
short-circuit evaluation remain unimplemented. P0 stays pending.

### Conditional C switch arms (2026-11-11)

A complete twelve-trip unsigned Fibonacci C program places a bounded
`switch` inside both braced `if/else` arms. The pinned Clang frontend
admitted the complete source but the adapter initially refused this
control-flow composition. The selected switch now carries its checked
local writes or `putchar` effects out of the conditional without leaking
effects from the unselected arm. A second complete program moves its
only output into the selected switch case.

The independent unsigned C oracle and normative guest VM both emit
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps. Five invalid C
mutations and 24 forged ASTs refuse publication. The source proof now
checks full arm end spans and exact opening byte/column gaps, rejecting
previously accepted forged brace coordinates. Dynamic guest control and
the original unmasked Fibonacci output remain unsupported; P0 stays open.


### Scalar induction truth guards in complete C (2026-11-11)

The full source-backed unsigned recurrence now uses a descending C loop
with `for (unsigned i = 12U; i; --i)` rather than an explicit comparison.
Pinned Clang admitted the complete program, but normalized local replay
originally rejected its first declaration. The compiler now accepts only
the exact protected unsigned induction variable as a pure scalar guard,
with checked Clang source spans, canonical separator geometry, a virtual
zero bound, and source-proven descending steps. Its finite proof refuses
overflowing or nondecreasing increments, unrelated local reads, and
effectful conditions.

An independently computed unsigned-C oracle matches the real normative
guest VM on twelve masked Fibonacci bytes
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps with empty or binary
stdin. Pinned Clang also normalizes postfix, compound and assignment
decrement spellings. The complete guest parity evidence is limited to
the prefix spelling; four unsupported C changes and eight forged AST
variants reject without publication. This does not implement dynamic guest C
loops or the original unmasked Fibonacci layout. P0 remains pending.

### Ordered C state writes between selected switch outputs (2026-11-11)

The complete `local_interleaved_switch_fibonacci.c` program performs six
bounded recurrence trips. Two levels of `switch` select four distinct arms;
each chosen arm emits one source-proven `putchar`, changes the unsigned local
`y` using `y ^= 1U`, then emits a second `putchar` from the changed value.
That second expression cancels the local bit change, so ignoring the write
would alter the emitted byte. The pinned Clang frontend accepted the whole
source, but the JSON adapter initially refused the first declaration and
published no guest because it forbade a local write after an output.

The bounded switch replay now admits precisely checked unsigned assignments
between ordered selected outputs, while retaining the two-output ceiling,
source ancestry, case-local `break` and separation of unselected effects.
Whole-assignment Clang spans must equal their left and right endpoint spans
in both byte and column coordinates; independently forged assignment columns
were previously accepted by the narrower geometry check. The independently
computed unsigned-C oracle and normative Malbolge VM match all twelve bytes
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps under EOF and binary
stdin. Five unsupported source mutations and 24 forged assignment ASTs
refuse guest publication. General C runtime control, arbitrary guest state
and the original unmasked Fibonacci byte stream remain unsupported.

### Paired effects in switch-local C conditionals (2026-11-11)

The complete `local_conditional_dual_nested_switch_fibonacci.c`
source places two real guest `putchar` calls in each selected branch
of four conditional statements nested within two-level switch arms.
Each C branch computes different compensation; incorrect selection
changes observable bytes. The pinned frontend, bounded JSON state
replay, typed lowering and verified guest layout admit the source.
The independent unsigned recurrence oracle and normative Malbolge VM
match twelve masked bytes `02 19 1f 08 17 0f 02 0d 03 10 13 03`
in 47 steps, both with EOF and binary stdin. Three complete-C
unproved-effect mutations and 24 forged Clang `if` nodes fail closed,
without guest publication. Guest dynamic switching and unmasked
Fibonacci layout remain unresolved under the P0.

### Two source-ordered outputs per nested switch arm (2026-11-11)

The complete `local_dual_nested_switch_fibonacci.c` C program runs
six source-proven bounded `for` trips. Each computes two consecutive
unsigned Fibonacci terms and selects one of four two-level switch
paths. Each innermost case emits both checked masked terms from two
separate `putchar` calls, with all four selector pairs reached.

The pinned Clang frontend admitted this program, but the JSON adapter
initially refused the second call in each case. A bounded two-output
vector now survives nested switch replay; unselected calls never
escape, outputs cannot be followed by other state writes, and an
effectful fallthrough or third output refuses. The independent C oracle
and normative Malbolge VM match the ordered twelve-byte stream
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 VM steps under EOF and
binary stdin. Six complete-C negative mutations and 48 forged Clang
output-call nodes reject without publication.

This is finite source-state replay, not general dynamic C switching or
an arbitrary byte-stream synthesizer. The original unmasked Fibonacci
trace still lacks a proved guest layout; the P0 remains open.

### Conditional C state inside nested switch cases (2026-11-11)

A complete twelve-trip unsigned Fibonacci C program now uses four inner
`switch` cases, each with a source-ordered `if/else` selecting a different
low-order mask before a compound XOR compensation and a real `putchar`.
The selected branch changes a low bit, so ignoring that decision would
change output even though the proved compensation restores the original
masked Fibonacci stream. Pinned Clang admitted the whole C source; before
the repair, the JSON adapter refused the first local declaration.

The bounded adapter now replays both conditional branches against the same
source state, captures at most one selected output per switch arm and
restores state before proving each unselected case. For switch-local
conditionals it also checks the exact opening `if (` byte/column spacing,
the closing branch span and forbids selected function/loop exits.
An independent unsigned-C oracle and the normative guest VM agree on all
twelve bytes `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps with
EOF or binary input. Seven unsupported C variants and 24 forged conditional
ASTs refuse without publishing a guest. A second complete C source
moves all twelve outputs inside the selected conditional branches; the
normative VM independently confirms the same twelve bytes and 47 steps.
This adds finite C control replay, not guest-side dynamic branching. The
original unmasked Fibonacci byte stream still fails layout synthesis, and
the P0 remains pending.

### Nested source-proven switch output effects (2026-11-11)

The original two-level switch Fibonacci source now has a second complete
C variant where each inner case/default both sets the local mask and
emits its own `putchar`; there is no output after the enclosing switch.
Pinned Clang accepts the whole source, but the pre-repair JSON projector
refused nested guest output effects. The bounded projector now captures
the inner switch's one selected output before replaying the outer switch's
other case/default paths, preventing unselected effects from leaking.
All four selector combinations occur. Source-bound Clang call spans must
also match closing byte and column geometry; an initially admitted forged
column exposed that separate validation gap.

The independently computed unsigned-C oracle matches the real Malbolge
VM on twelve bytes `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps
under EOF and binary input. Seven unsupported C mutations and 24 forged
output-call AST variants refuse guest publication. A third active switch,
multiple I/O effects along a nested path, unbounded runtime C switching
and the unmasked twelve-byte Fibonacci byte stream remain unsupported.
The P0 is not complete; this is bounded source-state replay.

### Nested `switch` state selection within a bounded C loop (2026-11-11)

A full unsigned-local Fibonacci C recurrence nests one `switch` in each
selected arm of an enclosing `switch` inside twelve bounded `for` trips. A
nested switch chooses one of four distinct unsigned masks (`0`, `32`,
`26`, `58`); the two switch-local `break` statements do not exit the for.
Pinned Clang admitted the program, but the normalized C adapter first
rejected nested source-state selection. The finite projector now checks at
most two active switch levels, source-ordered and span-checked Clang children,
and carries the selected inner
branch's local state into the outer switch without leaking another case.

A separate unsigned-C oracle covers all four selector combinations. The
normative Malbolge VM emits the twelve masked bytes
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps on both EOF and binary
stdin. Eight C mutations and 22 independently forged Clang ASTs refuse
before guest publication, including output effects on selected or unselected
inner switch arms. The bounded projection excludes three nested switches,
nested byte I/O, unbounded guest switches and the original unmasked Fibonacci
layout. The general P0 output-stream milestone remains open.

### Unbraced C `do…while` directly inside `for` (2026-11-11)

The full Fibonacci recurrence also uses
`for (unsigned i = 0U; i < 6U; ++i) do { ... } while (phase != 0U);`.
Each protected for trip executes two mandatory-first inner iterations,
updates the recurrence, emits two branch-selected bytes and resets phase.
Pinned Clang accepts the direct do child, which the adapter previously
rejected for lack of a synthetic compound body. Source-backed replay now
checks the direct do ancestry, full byte/column endpoint, protected outer
counter and the do's post-body condition.

The independent unsigned-C oracle and normative guest VM both emit the
same twelve masked Fibonacci bytes as the nested-while variant in 47
steps, under EOF and binary stdin. Four invalid C programs and three
forged ASTs reject without publishing a guest. Dynamic guest loops and
general unmasked output layouts are not supported; P0 remains open.

### Unbraced C `while` directly inside `for` (2026-11-11)

The complete `local_unbraced_while_for_fibonacci.c` source uses a six-trip
`for (unsigned i = 2U; i <= 12U; i += 2U)` whose entire unbraced body is
`while (phase < i) { ... }`. The inner loop increments `phase` toward the
changing outer induction limit, computes Fibonacci state, branches on the
next term, and emits two masked bytes per outer iteration. The pinned C
frontend accepted the full source; the JSON adapter initially refused the
direct `while` child before any guest artifact was published.

Finite replay now authenticates direct Clang ancestry and matching full
endpoints for outer `for` and inner `while`, retains the protected induction
symbol, rechecks the inner condition after every C state update and respects
nearest-loop `break`/`continue` exits. The complete natural-exit, explicit
inner-break and inner-continue programs each match the independent unsigned-C
oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03` in exactly 47 normative
VM steps with EOF and binary stdin. Six unsupported source mutations and
eight forged normalized ASTs reject without guest publication.

This is source-proven bounded compile-time C replay, not guest runtime loop
execution. Unmasked twelve-byte Fibonacci output still fails the verified
layout search as `Layout(UnsupportedEffectTrace)`; general P0 remains open.

### Unbraced C `do…while` directly inside `while` (2026-11-11)

The complete Fibonacci source `local_unbraced_do_while_fibonacci.c` uses
`while (remaining > 0U) do { ... } while (phase != 0U);` without braces
around the outer body. The inner do toggles `phase`, changes both recurrence
locals, decrements `remaining` twice, and emits branch-selected masked bytes.
The outer predicate is re-evaluated against those updated locals after each
inner do, for six outer trips and twelve output effects. Pinned Clang
accepts the source; the JSON adapter initially refused the direct do child.

The repaired source replay checks exact Clang ancestry and full source-span
endpoints, including both byte and column geometry. It does not synthesize
a hidden compound scope or move do's mandatory first iteration. A separate
unsigned-C oracle and the normative Malbolge VM agree on twelve bytes
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps, both under EOF and
binary stdin. Six invalid C variants and nine forged AST variants refuse
publication. Two forged closing columns exposed a byte-only endpoint check;
that check now rejects both independently tampered columns.

This is bounded compile-time C-state replay, not guest runtime C loops.
The original unmasked twelve-byte Fibonacci layout remains unsupported;
P0 stays open.

### Unbraced C `for` directly inside `while` (2026-11-11)

A complete twelve-output Fibonacci C program now uses an unbraced
`while (remaining > 0U) for (unsigned j = 0U; j < 2U; ++j) { ... }`.
Each inner trip updates recurrence locals and the outer `remaining`
variable, so the outer condition depends on updated state. Pinned
Clang accepted the source, but the adapter initially rejected the
nested `for` before guest publication. The source-backed replay now
checks direct Clang ancestry and the full statement endpoint, retains
inner counter scope and re-evaluates the outer condition after `for`.

An independent unsigned-C oracle and the actual normative Malbolge VM
agree on twelve masked bytes `02 19 1f 08 17 0f 02 0d 03 10 13 03`
in 47 steps under EOF and binary stdin. Six invalid C sources and
eight forged Clang ASTs reject with no published guest. This is bounded
compile-time C-state replay, not dynamic guest loops. The original
unmasked twelve-byte layout remains unsupported.

### Three source-proven mixed C while/do levels (2026-11-11)

The complete twelve-output C source
`local_three_level_while_do_fibonacci.c` nests a two-trip
`do/while` inside a two-trip `while` inside another two-trip `while`,
with an enclosing bounded `for`. The pinned Clang frontend accepted the
source, but the JSON adapter initially refused the third active while/do
body. Finite source-state replay now permits three total active while/do
levels while retaining the existing twelve-trip cap, checked source
ancestry, lexical local lifetimes and protected for induction.

A real encoded Malbolge guest emits the independent masked unsigned-C
Fibonacci bytes `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps.
The original unmasked twelve-byte layout remains unavailable, as do
dynamic guest loops and general runtime C state.

### Mixed two-level C `while`/`do` nesting (2026-11-11)

A complete twelve-output Fibonacci C source
`local_nested_while_do_fibonacci.c` places a two-trip `do/while` inside
an outer two-trip `while`, itself inside a bounded `for`. Pinned Clang
accepted it, but the JSON adapter originally refused the inner `do`
before guest publication. The repaired finite projector tracks active
`while` and `do` depths separately, enforcing a combined two-level cap.
It replays each inner predicate against updated locals, drops local
`pass` declarations on scope exit, and preserves the enclosing `for`
counter and nearest-loop `break`/`continue` targets.

Six complete source variants prove inner `break`, inner `continue`, outer
`break`, and all three loop nestings: `while/do`, `do/while`, and `do/do`.
The independent unsigned-C oracle and actual Malbolge VM agree on twelve
bytes `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 guest steps on EOF
and binary stdin in each case. Seven invalid C sources and eleven forged
Clang trees fail without publishing guest code. Three active `while/do`
levels, unbounded loops, effectful predicates, forged ancestry and writes
to protected induction remain unsupported. These are compile-time C-state
proofs, not dynamic guest loops; unmasked Fibonacci output remains blocked
by byte-stream layout.

### Two source-checked nested C `while` loops (2026-11-11)

The complete twelve-iteration Fibonacci C source
`local_nested_while_while_fibonacci.c` adds a two-trip inner `while` to an
existing two-trip `while` inside a bounded `for`. Pinned Clang admits the
source, while the pre-repair normalized JSON adapter refused the second
loop. The bounded projector now uses active `while` depth rather than a
single Boolean, proving both predicates with source-checked Clang ancestry
and rechecking all local writes. It preserves lexical `pass` lifetimes,
nearest-loop exits and the protected outer induction symbol.

The source-derived unsigned-C oracle emits
`02 19 1f 08 17 0f 02 0d 03 10 13 03`; the real Malbolge VM matches
under EOF and binary stdin in 47 steps. Third-level `while/do` nesting,
effectful conditions, unbounded loops and fabricated Clang node ancestry
remain rejected before guest publication. This is bounded compile-time
source-state replay, not dynamic guest looping.
The original unmasked twelve-byte Fibonacci layout remains P0 work.

### Bounded C `do/while` nested in a stateful `for` (2026-11-11)

A complete twelve-iteration Fibonacci C source now computes its next
unsigned term in a two-trip, mandatory-first `do/while` directly inside
an enclosing bounded `for`. The pinned Clang frontend accepted the full
program, but the JSON adapter originally rejected the inner loop before
guest publication. The bounded source-state replay now admits this inner
form while preserving the protected outer induction counter, source order,
lexical local lifetimes and the do-loop's post-body predicate.

Independent source variants select `continue` during the first inner trip
and `break` on the second trip. The first still evaluates the trailing
condition; the second exits only the inner loop. All three complete
compiled C programs emit `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47
real normative VM steps under EOF and binary stdin, matching a separately
computed unsigned-C oracle. Five unsupported C variants and eight forged
Clang trees refuse before publication; a regression additionally requires
the closing brace's same-line byte and column offsets to agree.

This is finite compile-time source-state projection, not dynamic guest
C control flow. A separately proven two-level mixed while/do family is
now admitted; three active while/do bodies remain refused.
The original unmasked twelve-byte Fibonacci stream still fails layout;
general synthesis and runtime C state remain P0 work.

### Bounded C `while` nested in a stateful `for` (2026-11-11)

A complete twelve-iteration Fibonacci C source now computes each recurrence
term in a two-trip `while` nested directly in its enclosing `for`. The first
inner trip assigns the sum of the current unsigned locals; the second masks
it to a defined byte before a source-checked outer branch selects guest
`putchar` output. Pinned Clang accepted the entire program, but the JSON
adapter originally rejected the inner `while` before publishing a guest.

The finite replay now admits one source-proven `while` inside a bounded `for`,
with no third-level active `while/do` body. Inner
`break` exits only the inner loop: a second complete C variant proves an
explicit break on trip two does not cut short the enclosing twelve-trip
`for`. The proof re-evaluates the inner condition and source-local effects
on each trip and retains the already enforced limits on loop depth, source
spans and induction mutations. An independently computed unsigned-C oracle
and the normative guest VM both emit twelve bytes
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps under EOF and binary
stdin for both C variants. Five invalid sources and eight forged Clang ASTs
refuse publication, including a hidden input effect, induction mutation and
wrong inner-loop ancestry. This remains bounded compile-time C replay, not
runtime guest loop control. The original unmasked Fibonacci guest layout
remains blocked and P0 stays open.

### Source-local disjunctive `for` guard (2026-11-11)

A complete Fibonacci C recurrence uses `limit > i || b < 20U` with a
mutable unsigned stride and checked local state. Pinned Clang accepted the
whole program, but the normalized JSON adapter initially rejected the
source because it admitted only `&&` guards following an induction bound.

The repaired bounded proof preserves a first induction comparison and up
to two source-ordered `&&`/`||` pure right operands, recomputing the entire
Boolean condition after each iteration and increment. OR may keep the loop
alive after its first comparison becomes false; an unbounded true guard
still fails at the twelve-trip ceiling without publishing a guest.

An independent C oracle proves six trips: `i` reaches 10, `a` reaches 13,
and `b` reaches 21, while the initial bound of 2 is crossed after the
second output. The normative guest VM emits the exact six bytes
`02 19 1f 08 17 0f` in 97 steps under EOF and binary stdin. Five invalid
C source variants and seven forged Clang AST variants refuse publication.
This is bounded compile-time C-state replay, not dynamic guest C loops or
unmasked twelve-byte stream synthesis. P0 remains open.

### Source-order-independent `for` induction (2026-11-11)

The complete Fibonacci C recurrence now uses the equivalent source condition
`limit > i && b < 20U` with a changing unsigned `stride` and source-local
state. The pinned Clang frontend accepted this program but the normalized
adapter initially refused because its checked induction variable had to be
on the left. The repaired proof authenticates the original Clang operand
order, counter identity, pure right- or left-hand bound, token spacing,
source positions, and comparison direction. It re-evaluates the bound and
Boolean guard after each body and increment, without confusing `>` with
descending counter motion.

The independent C oracle stops after six iterations at `b == 21`, with
`i == 10`; the actual normative VM emits `02 19 1f 08 17 0f` in 97 steps
under EOF and binary stdin. Four invalid source programs and six forged ASTs
refuse guest publication. The original unmasked twelve-byte Fibonacci
program still refuses at guest layout. This repair is bounded compile-time
C-state replay, not dynamic guest C loops or general byte synthesis.

### Rechecked chained `for` conditions (2026-11-11)

A complete C Fibonacci program now combines source-local bound and stride,
changing recurrence locals, a branch, guest `putchar` effects and a
left-associated three-way `for` condition:
`i < limit && a < 40U && b < 20U`. Pinned Clang accepted this source,
but the normalized adapter originally rejected the nested conjunction.
A bounded proof now retains the induction condition at the left and checks
up to two additional pure `&&` guards, in source order, against the exact
Clang ancestry, type, token spacing and byte/column endpoints. Every guard
is re-evaluated against live C locals after the body and induction update.

The independent C oracle proves that `b < 20U` alone ends the loop at six
iterations, while the other two predicates are still true. The actual
normative VM emits `02 19 1f 08 17 0f` in 97 steps under EOF and binary
stdin. Nine unsupported C sources and nine forged AST variations refuse
without guest publication, including a newly exposed end-column forgery.
The five-output version stops at the separate guest-layout stage, and the
original twelve-output unmasked Fibonacci program remains unsynthesized.
This is bounded compile-time C-state replay, not dynamic guest execution
of general C control flow; P0 remains open.

### First complex C experiment

The following compact function uses local state, a bounded loop, a branch,
integer arithmetic, and observable guest output. It was intentionally tried
as a single complete program before creating any additional small cases.

```c
#include <stdio.h>

void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    for (unsigned i = 0U; i < 12U; ++i) {
        unsigned next = (a + b) & 255U;
        if ((next & 1U) == 0U) {
            putchar((int)next);
        } else {
            putchar((int)(next ^ 0x5AU));
        }
        a = b;
        b = next;
    }
}
```

An independently derived reference returns these twelve bytes:
`02 59 5f 08 57 4f 22 6d 03 90 b3 23`. The pinned compiler attempt on
2026-11-05 failed at `c2malbolge_json` with the diagnostic `Malformed`,
before publication of a guest program. This is a real failed
experiment, not proof that the compiler supports general C.

The first adapter defect was confirmed and fixed in DCO commit
`e5773e312`: the Clang schema already defined `storage_duration`, but the
closed JSON adapter had omitted it. The adapter now admits the specified
`automatic`, `static`, and `thread` values as metadata while still rejecting
unknown fields and values. Its supported effect-free and literal-output
paths reject that extra metadata instead of silently discarding state.

With the same program and updated adapter, the real pinned pipeline now
reports `Unsupported; unlowered C declaration-statement` at the first local
variable, with the C source line and column, and publishes no guest. The
tracked experiment is
`tests/compiler/c-frontend/accepted/conditional_fibonacci.c`, replayed by
`tests/test_compound_c_pipeline.py`; its oracle is independently calculated.
That test requires explicit failure while state semantics are unsupported
and will require actual normative guest-VM parity if compilation succeeds.
This is a repaired **schema/diagnostic** gap, not completed C lowering.

### Rechecked source-local Boolean `for` guard (2026-11-11)

The complete source `local_guarded_for_fibonacci.c` was attempted with
`i < limit && a < 9U`, a local bound of twenty, a mutable stride, and
Fibonacci locals updated every trip. Pinned Clang accepted the source, but
the closed JSON adapter initially rejected its additional `&&` guard.
The bounded induction proof now admits one exact source-ordered pure right
condition after the original checked unsigned counter bound. The right
condition is independently checked for type, ancestry, span, operator and
canonical token separation, and is re-evaluated against the updated source
locals after each executed body and induction step. A logical OR cannot
replace the left induction proof. A changed or effectful guard is refused.

Six actual trips produce independent source oracle `02 19 1f 08 17 0f`,
with the stride changing from one to two and the Fibonacci guard stopping
before the twenty-step bound. The normative guest VM emits exactly those
six bytes in 97 steps under EOF and binary stdin. Source mutations and
forged AST variants refuse without artifact publication. This remains
compile-time bounded C-state replay, not runtime guest loop control or a
solution to the original unmasked Fibonacci output layout blocker.

### Re-evaluated source-local `for` increment (2026-11-11)

The full masked Fibonacci program now selects a source-local unsigned
stride and changes it from 1 to 2 after its third output. Pinned Clang
accepted the complete C, but the closed JSON adapter originally rejected
its `i += stride` induction without a guest artifact. The bounded proof
now retains the exact pure typed increment subtree, re-evaluates it after
each selected loop body, and only then updates the protected counter and
rechecks the condition. The equivalent `i = i + stride` spelling shares
this source-backed replay. Each actual stride must be between 1 and 12;
unknown effects, unproved AST shapes and an execution beyond twelve trips
refuse without publication. In a loop bounded by 10, the changing stride
produces six iterations instead of the ten that a frozen increment would
produce. The actual Malbolge VM emitted the independently computed six
masked bytes `02 19 1f 08 17 0f` in 97 steps under EOF and binary stdin.
This finite C-state replay does not implement runtime guest `for` loops;
the original unmasked twelve-byte program still refuses at guest layout.

### Re-evaluated source-local `for` bound (2026-11-11)

The first complete masked Fibonacci C source used `unsigned limit = 12U;`
and `for (unsigned i = 0U; i < limit; ++i)`. It initially refused at
normalized JSON admission, without publishing guest code, because the
closed induction projector required a literal bound. The repaired proof
accepts a pure unsigned expression bound, preserving the exact pinned-Clang
comparison, source token geometry and bound subtree. It re-evaluates that
subtree after every body and induction update, so writes to source-local
bounds change the next condition as required by C. Unprovable effects,
overwide bounds, and executions exceeding twelve trips still fail closed.

The full source emits an independently calculated twelve-byte oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 real normative VM steps.
A second full C source starts `limit` at 3 and increments it for the first
three trips; the independent six-byte oracle `02 19 1f 08 17 0f` reaches
the actual Malbolge VM in 97 steps. Both accept EOF and binary stdin.
Five unsupported C variants and six forged AST mutations refuse without
a guest artifact. The original unmasked output stream is still blocked
by the layout backend and dynamic guest loops remain unsupported.

### Dependent comma initialization in a function body (2026-11-10)

The complete masked Fibonacci source now initializes two zeroed locals with
`a = 1U, b = a;` directly inside the function body, before its twelve-trip
loop. It is one source-ordered comma statement with dependent state, not two
independent assignments. The pinned Clang frontend accepted the complete C
source while the normalized JSON adapter originally refused the function
statement without publication. The same bounded comma projector now applies
to function-body writes; a child must match its source parent and the comma
node's begin and end locations must match the first and last complete child
spans, including columns. This closes a forged-AST end-column drift found
by the new negative tests.

The real normative guest emits the independent masked twelve-byte Fibonacci
oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps under empty and
binary stdin. Five invalid C variants and six forged AST variants reject
without publishing a guest artifact. The entire proof remains bounded
compile-time source-state replay; the original unmasked output stream still
fails at layout, not at C source admission.

### Unbraced conditional arms with ordered C comma writes (2026-11-10)

The complete twelve-step masked Fibonacci C source now uses two unbraced
`if`/`else` arms, each containing `selected ^= N, a = b;` as one comma
expression. The unselected arm must still be completely source-proven; the
selected arm must apply the first local write before the second, and its
updated recurrence state must survive to the next `for` iteration. Pinned
Clang accepted the whole C source while the JSON adapter initially refused
its direct conditional arm, without publishing a guest. The adapter now
reuses the existing bounded left-to-right local-write proof for unbraced
conditional expressions as well as for braced loop effects. It checks
exact Clang parents, full source spans, symbol identity, unsigned types and
the canonical same-line separator. At most four writes are admitted in a
single comma tree; calls, reads used as statements and unproved operators
still refuse.

The real normative Malbolge VM emitted the independently computed twelve
bytes `02 19 1f 08 17 0f 02 0d 03 10 13 03` in exactly 47 guest steps
under EOF and binary stdin. Eight invalid C variants and seven forged
Clang AST variants refuse without guest publication. This remains bounded
compile-time replay, not guest runtime sequencing or a solution to the
original unmasked Fibonacci layout failure. Generalized P0 remains open.

### Sequenced unsigned local writes in C comma expressions (2026-11-10)

The full twelve-iteration masked Fibonacci C source now uses
`a = b, b = next;` to update the recurrence in one C expression statement.
Pinned Clang accepts it, but the JSON adapter originally refused before
publishing guest code. A closed projector now replays each assignment in
C's required left-to-right order, checking the complete Clang subtree,
unsigned types, local symbols, source spans, and the exact same-line comma
separator. Nested comma groups are bounded to at most four assignments;
call effects, read-only operands and unproved shapes remain unsupported.
The entire C program reaches the independently derived masked twelve-byte
oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 normative guest steps
under empty and binary stdin. Nested three- and four-write replay remains
a separate timeboxed validation; five writes are outside the bounded proof.
Five invalid sources and five forged ASTs refuse without publication.
This is finite source-state replay, not dynamic guest sequencing or a
solution to the unmasked Fibonacci layout blocker.

### Bounded long switch fallthrough chain (2026-11-10)

The complete twelve-step masked Fibonacci C source now carries unsigned
locals through `case 0U`, `case 2U`, `case 1U` and a final `default`.
The original source failed at JSON admission without a guest artifact:
its three consecutive source-ordered fallthrough edges exceeded the previous
two-edge proof. An exact pinned-Clang replay now maintains the independent
entry state for each preceding case, checks every consumed node and break
against the direct-entry path, and caps replay at eight distinct case labels.
A source expansion exercises eight cases followed by default, including paths
with eight consecutive edges. The normative Malbolge VM emits the independent
12-byte oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03` in exactly 47 steps
under both empty and binary stdin, with no host output substitution.
A ninth case, output-before-fallthrough, effectful input, and forged later
case ancestry/spans/operators refuse without publishing guest code. The
original unmasked twelve-byte output still fails at guest layout, and
runtime guest C switching remains unsupported; generalized P0 is open.

### Source-ordered middle `default` C switch (2026-11-10)

The complete twelve-trip masked Fibonacci program
`tests/compiler/c-frontend/accepted/local_mid_switch_default_fibonacci.c`
places `default` between `case 0U` and later `case 2U`/`case 1U`. All four
selector values occur. An independent source-level recurrence computes the
same oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03` as the existing masked
program, but each arm now writes a shared local before the sole post-switch
output. The pinned Clang frontend accepts it; the JSON adapter initially
refused the complete program without publishing a guest.

The closed source-flow projector now admits one direct-child middle default,
provided it follows an earlier case, has a checked unsigned write or pure
output, ends at a source-checked switch-local `break`, and is followed by
at least one ordinary `case`. Later cases must also prove the exact final
break and compound closure. No effectful fallthrough into or out of this
middle default is admitted. Every arm replays from independent pre-switch
local state, and the chosen case takes precedence over default regardless
of the labels' textual order. The real normative VM emits the twelve-byte
oracle in 47 steps under EOF and binary stdin. Six invalid C mutations and
eight forged Clang nodes refuse without publishing a guest artifact.
This remains bounded source-state projection: unmasked Fibonacci still
refuses at guest layout, and runtime guest C switching is not implemented.

### Source-proven switch fallthrough into default (2026-11-10)

The complete masked Fibonacci source
`tests/compiler/c-frontend/accepted/local_default_fallthrough_fibonacci.c`
was first rejected by the JSON adapter. Its `case 2U` modifies a `carry`
local and falls into a final `default` body; dispatch values 1 and 3 enter
that same body directly. The two entry classes require different values of
`carry`, and all four dispatch values occur in the twelve-step program.

The closed projector now permits a non-output case effect to reach a final,
source-ordered direct-child `default`. It independently replays the entire
default subtree from pre-switch locals and from every pending carried state,
checking exact Clang source-node extent, ancestry, effect order and the same
switch-local break. This still admits no more than two consecutive fallthrough
edges; effects before fallthrough, effectful input, extra body effects and
forged normalized trees refuse without publishing a guest.

The actual normative Malbolge VM emits the independently calculated masked
Fibonacci oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps with
empty and binary stdin. The separate complete source
`tests/compiler/c-frontend/accepted/local_chained_default_fibonacci.c`
also traverses two consecutive nonempty edges, `case 0U` to `case 2U` to
`default`, and reaches the same guest parity with separate direct dispatch
into both receiving labels. Five unsupported C mutations, seven forged
Clang trees, and an additional valid-C third-edge variant reject without
publication. The original unmasked twelve-output Fibonacci still refuses at
`Layout(UnsupportedEffectTrace)`; source-state replay is not dynamic guest
C switching or generalized byte-stream synthesis. P0 remains open.

### Two consecutive source-proven switch fallthrough edges (2026-11-10)

A complete twelve-iteration masked Fibonacci recurrence was first retried
alongside the unchanged unmasked source. The latter still refused at
`Layout(UnsupportedEffectTrace)` with no guest artifact. The new C source,
`tests/compiler/c-frontend/accepted/local_chained_switch_fibonacci.c`,
then refused at normalized JSON admission. Its switch uses three explicit
case labels in source order `0U`, `2U`, `1U`; direct entry into each case
must read different local state from entry via the previous label. The
case-zero path traverses **two consecutive nonempty fallthrough edges**,
whereas case two traverses one and case one none. Case three takes default.

The repaired closed projector replays each label subtree from pre-switch
locals for direct entry and separately from every pending carried path.
All replays must consume the same complete Clang nodes, end at the same
source position and agree on the switch-local `break` or next label.
Only the selected path's local state survives. At most two consecutive
edges are admitted, with no preceding output, no fallthrough to default,
and no relaxation of the four-effects-per-arm proof. The complete C loop
reaches independent masked oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03`
from real guest Malbolge in 47 steps under empty and binary stdin. Five
invalid C mutations and eight forged Clang trees refuse without an
artifact. This is finite compile-time source-state replay, not runtime
guest C switching, generalized byte layout, or acceptance of the original
unmasked Fibonacci target. The generalized P0 remains pending.

### Source-checked nonempty `switch` fallthrough (2026-11-10)

A complete twelve-iteration masked Fibonacci C source now uses real C
fallthrough from `case 0U:` into the next distinct `case 2U:` while
`case 2U:` also receives direct dispatch. Before repair, pinned Clang
accepted the complete source but JSON admission refused it without guest
publication. Clang parents each label's first `^=` expression directly
to that label, and later statements and `break` to the switch compound.
The projector checks exact label/source order, two complete entry paths,
source-backed local reads, at most four effects per receiving arm, and one
following break. It independently replays the receiving case from both
pre-switch state (direct entry) and the immediately preceding case's final
local state (fallthrough), requiring both traversals to consume the same
complete normalized subtree. Only the selected path's state is retained.

The source initializes `selected` with an extra `7` for dispatch value 2,
then uses a real `carry` write at dispatch 0 to cancel that factor before
falling into the same receiving code. The two entry states are deliberately
different: losing the carried state would change observed output. All four
dispatch values appear. The independently derived twelve-byte oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` matches the actual normative
Malbolge VM in 47 steps under EOF and binary stdin. Five unsupported
source mutations and six forged normalized AST variants refuse with no
guest artifact. Chained fallthrough, fallthrough to `default`, output
before another label, effectful input, unbounded body effects, dynamic
guest switching and the original unmasked guest layout are unsupported.
This is bounded source-state C selection, not a general runtime branch.

### C switch without default in the complete recurrence (2026-11-10)

The original unmasked twelve-iteration Fibonacci source still refuses at
`Layout(UnsupportedEffectTrace)` without a guest artifact. A separate entire
masked recurrence then attempted ordinary C `switch (next & 3U)` with
`case 0U` and `case 2U` but **no `default`**. It initialized `selected`
before the switch, assigned the even output in its matched arms and emitted
the post-switch local. All four selector values occur in twelve iterations;
1 and 3 must retain the incoming fallback local instead of selecting an
invented default. The pinned Clang frontend accepted the source, but the
JSON adapter initially refused it without publication.

The bounded projector now checks each source-ordered case arm and break,
requires the final break directly before the closing switch brace, and
restores the pre-switch state on an unmatched dispatch. Separate cases and
adjacent grouped `case 0U: case 2U:` both use this no-default behavior.
The complete source emits the independent masked twelve-byte oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` on the normative VM in 47 steps,
under empty and binary stdin. Three unsupported source variants and six
forged Clang trees refuse without publication. This is only finite
compile-time C-state projection: dynamic guest switching and the original
unmasked stream remain unsupported; P0 stays open.

### Ordered switch-arm C local transfers (2026-11-10)

The unmasked twelve-trip Fibonacci program was reattempted in full and still
fails at the independent guest layout with `Layout(UnsupportedEffectTrace)`;
no guest is published. A second complete four-way masked recurrence then
used two dependent local writes in every ordinary C `case`/`default` arm:
`selected = ...; transferred = selected ^ 0U; break;` followed by one
post-switch `putchar((int)transferred)`. Pinned Clang accepts the C but
originally the JSON adapter refused the switch's extra direct child.

Clang parents only the first statement to its case/default label; later
statements are siblings under the enclosing switch compound. The checked
projector now admits up to three extra ordered, source-bound unsigned writes
or one terminal pure output after that first effect, all before the required
switch-local break. Every arm is checked from the same pre-switch locals;
only the selected arm's final state and at most one output survive. Extra
calls, writes after output, uninitialized reads, fallthrough, effectful input,
more than four arm effects and forged ancestry/spans remain unsupported.
All three full-source variants (separate arms with shared output, grouped
case/default arms and a terminal arm-local `putchar`) emit the independent
masked oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03` in exactly 47
normative VM steps under empty and binary stdin. Six unsupported C source
mutations and seven forged Clang ASTs fail without a guest artifact.
This extends finite source-level C-state replay, not runtime guest switching.

### Switch-selected C local state in a complete recurrence (2026-11-10)

The complete masked Fibonacci source first refused when a four-way C switch
assigned an uninitialized local `unsigned selected` in each arm and performed
a single `putchar((int)selected)` afterward. Pinned Clang accepted the source,
but the JSON adapter refused at the loop's first declaration and did not
publish a guest. Each source-checked arm now proves exactly one unsigned
assignment or pure output, followed by its own switch-local `break`.
The projector snapshots the same incoming local state before every arm,
verifies even unselected operations, and commits only the chosen arm's writes
or output. This is required for compound `^=` arms that read initialized
state; sequentially replaying the arms would change the selected result.

Three complete source variants exercise direct initialization, compound XOR
state updates, and nested grouped `case`/`default` assignments. All four
switch dispatch values occur in the independent twelve-step Fibonacci
oracle. Each normative guest execution emits
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 VM steps with empty and
binary stdin. Four effectful/fallthrough source mutations and six forged
Clang trees refuse without publication. The bound remains one effect per
arm, at most eight distinct labels and one final default. This is bounded
compile-time C state replay, not runtime switching or general source C.
The original unmasked Fibonacci guest layout is still unsupported, so the
P0 remains pending.

### Bounded C switch selection in a complete recurrence (2026-11-10)

A full twelve-step masked Fibonacci source first refused at the normalized
JSON adapter after replacing its `if/else` output with ordinary C
`switch (next & 1U)`, `case 0U`, `default`, and explicit `break` statements.
The pinned Clang tree places each case's one `putchar` directly under its
label while parenting both `break` statements to the switch's compound
body. A source-bound proof now checks this exact shape, both pure output
arguments, the constant label, dispatch expression, ancestry, complete
spans, fallthrough barriers and source order before choosing one effect.
The switch-local `break` does not exit the surrounding bounded C loop.

The full C program emits the independently computed masked oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 normative guest steps
under empty and binary input. A second whole-program variant exchanges
which parity reaches the explicit case versus `default`; it emits the
same oracle. Three valid-but-unsupported C mutations (fallthrough,
effectful dispatch and an additional case) and eight forged normalized AST
variants reject without a guest artifact. This proves finite compile-time
C control selection, **not** runtime guest switch or input-dependent C
state. The original unmasked Fibonacci output remains unsupported at
layout, so P0 stays pending.

### Shared C case/default output in full Fibonacci (2026-11-10)

The entire twelve-step masked recurrence was rerun with two C switch label
groups: `case 0U: case 2U:` sharing one output and `case 1U: default:`
sharing the other. Pinned Clang nests `default` below its preceding
case label; before the repair, the JSON adapter rejected the valid whole
C source and published no guest. The closed projector now checks this
final nested default's direct parent, complete shared extent, source
order, effect-free label body, single pure output and switch-local break.
The default must remain the last label. An earlier effect, earlier break,
trailing case, or forged normalized tree still refuses. No general
fallthrough or runtime guest switch is implied.

All four switch destinations occur in the independent twelve-trip oracle.
The normative VM emits `02 19 1f 08 17 0f 02 0d 03 10 13 03` in
47 steps under empty and binary stdin. Three unsupported C mutations and
six forged Clang AST variants refuse without publication. The original
unmasked stream still fails at guest layout; P0 remains open.

### Grouped C switch labels in the complete recurrence (2026-11-10)

The full twelve-step masked Fibonacci source was retried with ordinary
`case 0U: case 2U:` labels sharing one pure `putchar` and a single
switch-local `break`. Pinned Clang nests the second case beneath the first;
the former direct-call-only projection refused the whole program without
publishing a guest. The source-state projector now recognizes this exact
consecutive empty-label nesting, checks both labels and the shared final
call against one source extent, and selects the group when either label
matches. The eight-unique-label ceiling still applies across all groups.
An intervening effect or break is not an empty-label group and still
refuses; neither runtime switch nor general fallthrough is implemented.

All four dispatch values occur in the independent twelve-trip C oracle.
The actual normative guest emits `02 19 1f 08 17 0f 02 0d 03 10 13 03`
in 47 steps under EOF and binary stdin. Two valid but unsupported
fallthrough sources and six forged Clang case-group trees refuse with no
guest artifact. Original unmasked Fibonacci and dynamic guest branching
remain P0 work.

### Multiway C switch selection in the full recurrence (2026-11-10)

A separate complete twelve-step masked Fibonacci C source replaced the
`if/else` output with `switch (next & 3U)` containing three explicit
`case` labels (0U, 1U and 2U), a final `default`, and one pure
`putchar` and switch-local `break` per arm. Its first pinned Clang-to-
JSON-to-guest attempt refused at the adapter with `Unsupported` and no
artifact. The source-state projector now checks up to eight distinct,
source-ordered unsigned case labels, each direct Clang output child and
separate break, followed by exactly one final default. It rejects duplicate
labels, fallthrough, hidden effects, forged case ancestry/value/geometry,
missing or misplaced breaks and an out-of-order default.

The full four-way program reaches all four arms over its twelve Fibonacci
iterations. Its independently calculated output is
`02 19 1f 08 17 0f 02 0d 03 10 13 03`; the normative current-profile
VM emits these exact bytes in 47 steps under empty and binary stdin.
Four unsupported C variants and nine forged middle-case Clang trees
refuse without publication. This widens only finite source-state switch
selection, not runtime guest branching or arbitrary output-stream layout;
the original unmasked Fibonacci program remains blocked at guest layout.

### Unbraced C branch effects in complete recurrences (2026-11-10)

The full twelve-step masked Fibonacci program was retried after replacing
both braced `if`/`else` output arms with ordinary single-statement `putchar`
arms. Pinned Clang accepted the whole C source, but the JSON adapter first
refused its local-flow projection without publishing a guest. Its normalized
AST directly parents each `call-expression` to the `if-statement`, rather
than inserting implicit compound blocks.

The bounded branch replay now accepts either a source-checked compound arm,
one direct pure-argument `putchar` call, or one checked unsigned local write
per arm. The selected state and output effects are committed only after both
alternatives are proved against the same incoming state. Source order, direct
parentage, complete spans, local bindings, pure expressions, nesting and
effect limits remain checked; unsupported effects and forged AST ancestry or
fields refuse without publishing a guest.

The original masked recurrence with unbraced output calls emits the independent
oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 normative guest VM
steps under empty and binary stdin. Two invalid source variants and six forged
Clang trees reject before guest publication. A second whole-source variant
replaces both branch calls with direct assignments to an initially
uninitialized `unsigned selected` and emits it with `putchar` after the
`if`/`else`. It also produces the same independent twelve-byte oracle in 47
normative guest VM steps with both inputs. Two uninitialized/incorrect-write
source variants and five forged AST bindings or operations reject without
guest publication. This is finite source-C state projection, not runtime
guest branches or locals. The original unmasked Fibonacci output remains
unsupported at layout; P0 is still pending.

### Lexical function-body blocks and C shadowing (2026-11-10)

A complete twelve-step masked Fibonacci recurrence was retried with an
additional function-body scope: an initialized outer `unsigned b = 77U`
is shadowed by an inner `unsigned b = 1U`, and the inner block contains the
entire bounded loop, branch and source-selected byte outputs. Pinned Clang
accepted the C source but the JSON adapter first rejected the block at the
initial declaration; no guest program was published.

The finite local-flow projector now reuses its source-checked lexical block
replay at function-body depth. It preserves enclosing writes and accumulated
output effects, resolves active same-name locals by their exact Clang symbol,
and drops only the inner declarations at the closing scope. Depth, ordered
source spans, parentage, automatic unsigned local types and effect limits
remain bounded. The complete real guest capsule is 2,207 bytes, executes
in 47 normative VM steps and emits the independent twelve-byte oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` under empty and binary stdin.
Invalid inner initialization, unknown effects and forged source/scope/symbol
metadata refuse with no guest artifact. A separate complete C source
proves the post-block binding: an inner `b = 90U` expires before the final
`putchar((int)b)` reads outer `b = 65U`. The normative VM emits `41` in
31 steps from a 1,295-byte capsule under both inputs; forging that final
read to the expired inner symbol refuses before publication. This extends
compile-time C-state proof, not guest runtime local storage or the original
unmasked Fibonacci layout. P0 remains open.

### Source-ordered unsigned declarator lists (2026-11-10)

A complete twelve-iteration masked Fibonacci program was retried after
combining its first two locals as `unsigned a = 1U, b = a;`. Pinned Clang
accepted the source, but the JSON adapter rejected its first
`declaration-statement` before guest publication. A red-first regression
now passes: the closed local-state proof consumes consecutive Clang
`variable-declaration` children in source order, carrying each proven
initializer into the next declarator. Bare declarators remain unreadable
until a selected later plain assignment proves their values.

A second complete source also proves a three-declarator group,
`unsigned a = 1U, b = a, later;`, followed by `later = b;` before the
loop. Its first use of `later` is a source-checked write, not a fabricated
zero initializer.

The bounded proof admits only automatic `u32` declarators, up to the
existing eight-local limit. For multi-declarations it checks the shared
`unsigned ` prefix, exact comma-and-space source offsets, source span and
column agreement, canonical symbols, a single final semicolon, and no
hidden initializer effects. In the full pipeline, the normative guest VM
emits the independently calculated twelve-byte masked oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps under empty and
binary stdin for both two- and three-declarator whole-source variants.
Three invalid C variants and eight forged normalized AST variants reject
without publishing a guest artifact. This does not add
runtime guest locals, arbitrary C declarations, or original unmasked
Fibonacci layout; P0 stays open.

### Ordinary `int` literals in full unsigned C recurrence (2026-11-10)

The full twelve-step masked Fibonacci C program was attempted with the
conventional unsuffixed integer constants `unsigned a = 1;`,
`for (unsigned i = 0; i < 12; ++i)`, `& 255`, and the ordinary literals in
both output branches. Pinned Clang accepted this complete source, but the
JSON adapter first rejected its initial unsigned declaration and published
no guest. Clang's source-normalized tree represents these constants as
`i32` integer leaves wrapped in implicit `integral-cast` nodes carrying
their evaluated unsigned result.

The closed local-flow proof now accepts the bounded **nonnegative** `i32`
leaf only when its value agrees exactly with the enclosing `u32` cast,
its source span is identical and neither node carries hidden metadata.
The same proof retains byte limits for finite `for` bounds and strides,
while all other local arithmetic remains checked `u32`. The complete
program emits `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps from
the actual current-profile Malbolge VM with both empty and nonempty binary
stdin, exactly matching an independently evaluated unsigned-C recurrence.
Six unsupported C-source variants and eight forged Clang-node mutations
refuse without publishing guest code. Explicit casts, negative signed
constants and signed arithmetic remain outside this proven topology.

This repairs an everyday C-source conversion boundary; it does **not**
execute dynamic C locals in Malbolge. The original unmasked twelve-byte
Fibonacci source still requires generalized guest layout and arithmetic;
P0 remains pending.

### Source-proven unsigned locals assigned after declaration (2026-11-10)

The original unmasked twelve-step Fibonacci C program was rerun and still
refused at `Layout(UnsupportedEffectTrace)`, without publishing a guest.
An independent complete masked Fibonacci C variant declared `unsigned next;`
inside its bounded loop and subsequently assigned `(a + b) & 255U` before
the conditional `putchar` arms. The adapter previously refused this ordinary
C declaration at the first local, before any target artifact was written.

A local now carries `None` until a source-backed plain assignment proves
its first value. The uninitialized declaration requires exact pinned-Clang
name and semicolon geometry, automatic `u32` storage and no initializer
children. A local read, compound assignment or prefix/postfix step before
its first selected write rejects. Branches prove both arms on shadow state
and commit only the selected state; an unselected write does not initialize
a variable. The bounded `for` induction still requires its initialized
counter. Normalized JSON cannot recover the literal token contents;
source authenticity rests on the pinned frontend and source digest.

Both direct and selected-branch assignment variants compiled into 2,207-byte
Malbolge capsules. The normative guest emitted the independently computed
oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps per replay.
Negative uninitialized-use sources and forged AST metadata reject without
guest publication. This remains compile-time state folding rather than
runtime guest C variables; the unmasked P0 byte stream remains unsupported.

### Unsigned unary signs over full C locals (2026-11-10)

The complete twelve-step masked Fibonacci recurrence was retried with a
full-width intermediate `unsigned wide = -(a + b);` and a subsequent
`unsigned next = (+(0U - wide)) & 255U;`. The typed adapter first refused
both ordinary C unary signs, even though subtraction and unsigned wraparound
were already proven for binary expressions. The closed local-state projector
now admits unary `-` as wrapping 32-bit negation and unary `+` as identity,
only for adjacent parenthesized expression operands. The previously supported
`~next` complement remains accepted, but changing its normalized operator
to a sign without matching operand topology now refuses before guest layout.

The pinned frontend and typed/backend compiler emit a 2,207-byte current-profile
Malbolge capsule. Both empty and binary stdin replays of the normative VM
produce the independent masked Fibonacci oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps each. Five invalid source
variants cover unparenthesized or spaced signs, hidden state mutation,
undefined division, and a signed cast; six AST mutations cover operator,
type, parent, unrecognized metadata and operand topology. All refuse before
guest publication. Normalized AST metadata is still a bounded proof input,
not a complete raw-source token attestation. Dynamic C state and the original
unmasked twelve-byte output remain unsupported at guest layout; P0 stays open.

### Full unsigned C locals across the complete recurrence (2026-11-10)

Replaying the entire twelve-output masked Fibonacci C program with
`unsigned wide = a + b + 65536U; unsigned next = wide % 256U;` first
refused at the typed JSON adapter and published no guest: its bounded
constant-flow projector still narrowed **every automatic `unsigned` local**
to a byte, although the previous change already supported full unsigned
expression intermediates. Local declarations, references, ordinary and
compound assignments, and standalone `++`/`--` now retain the complete
source-checked `u32` value (including C unsigned wraparound). The separate
bounded `for` induction proof still requires byte-range counters, and
a direct `putchar((int)local)` still requires an exactly representable
byte; the original simple one-local projector is not broadened.

The full twelve-iteration C recurrence with an intervening wide local now
reaches a real current-profile Malbolge capsule. On empty stdin the normative
VM emits `02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps, matching
the independent unsigned-C recurrence oracle. Full-program regression
variants also exercise a compound wide local write, wrapping at 2^32, and
standalone wide-local increment under empty and binary stdin. Invalid C
width, undefined remainder, out-of-byte guest output, and forged Clang
literal metadata are explicitly rejected without guest publication.

This remains **closed compile-time C-state evaluation**: neither C local
state nor its arithmetic executes dynamically inside the guest. The
original unmasked Fibonacci byte stream `02 59 5f ...` still fails at
layout; a bounded forward-jump scratch search cannot synthesize its early
`5f` under its current operand/geometry limits. No general byte-stream
synthesis or dynamic C control-flow capability is claimed; P0 stays open.

### Full unsigned-C intermediates in a bounded recurrence (2026-11-10)

A complete twelve-step masked Fibonacci C program was rerun with a normal
`% 256U` recurrence instead of the previous `& 255U` mask, and again with
`((a + b) + 65536U) % 256U`. Both whole programs initially refused at the
typed adapter before publishing a guest because its source-backed local
projector accepted only `0..255` integer leaves. The shared Clang-literal
proof now retains the entire normalized `u32` value for closed expression
arithmetic, including unsigned C wraparound, while the original simpler
byte-only projector and (at the time of this experiment) every local
store/output required a byte.

A third whole-source variant using
`((a + b) + 4294967295U + 1U) % 256U` also proves C `u32` wraparound
and reaches the same real guest output. All three complete programs emit
the independent twelve-byte oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` on the actual normative guest
VM under empty and nonempty binary stdin, in 47 steps per execution.
Malformed Clang literal metadata, out-of-range intermediate types,
undefined division, and attempts to store a non-byte still reject without
guest publication. This improves genuine C expression coverage, not dynamic
guest arithmetic. The original unmasked Fibonacci layout remains unsupported
and P0 is still pending.

### Source-proven `else if` chains in full C control flow (2026-11-09)

The complete twelve-iteration masked Fibonacci C recurrence was retried with
three source-level output arms, using an ordinary `else if` condition between
the original even and odd cases. The pinned Clang frontend represented the
second condition as an `if-statement` directly parented to the first; the
typed adapter initially refused the program at its first declaration and
published no guest artifact.

The closed C-state projector now proves a nested `else if` as a source-ordered
Clang child of its enclosing `if`, with bounded conditional depth and exact
parent and end-span agreement. Each arm is replayed against the same incoming
local state; only the selected branch commits its writes, exit and byte
effects. Unselected arms and conditions must still be pure and defined.

All three output arms are selected by the complete recurrence. The resulting
Malbolge guest emits the independent twelve-byte masked Fibonacci oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` under both empty and nonempty
binary stdin. Four negative whole-C cases (undefined arithmetic in a third
arm or provably skipped `else if`, an unbraced arm, and excess chain depth)
and four forged normalized-AST cases refuse without guest publication. The
compiler still folds finite local state at compile time, not in the guest;
the unchanged unmasked Fibonacci output remains unsupported at guest layout.

### Assignment-form `for` induction in a complete C program (2026-11-09)

The twelve-output five-bit masked Fibonacci recurrence was first retried with
`for (...; i < 12U; i = i + 1U)`. The pinned frontend normalized the ordinary
C assignment into an `=` node with a nested unsigned `+` read, but the typed
adapter refused it at the first local declaration without guest publication.
The bounded projector now checks the entire source-backed step tree: exact
assignment and arithmetic tokens, both matching induction references, the
Clang lvalue-to-rvalue cast, typed positive literal stride, and guard direction.
A second complete recurrence uses `i = 24U; i > 0U; i = i - 2U`. Both forms
are limited to at most twelve proven trips and preserve the existing checked
byte-range state updates; they do not introduce guest-side loop execution.

Both complete C sources compiled through the pinned compiler and emitted the
independent twelve-byte oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03`
from the actual normative guest VM, each under empty and nonempty binary
stdin (163.855 seconds for the combined replay). Eight source negatives
(including zero/large stride, wrong direction or source symbol, different
operator, nested expression, unproved spacing and an extra effect) and eight
forged AST negatives all refused without guest output publication. The
original unmasked Fibonacci guest layout remains unsupported; compile-time
state replay is still bounded and does not satisfy the general P0 objective.

### Standalone unsigned local steps in bounded C loops (2026-11-09)

The whole twelve-output masked Fibonacci C program was retried with a
`while` loop and a standalone `++i;` replacing its earlier `for` induction.
The pinned Clang frontend accepted the source, but the typed adapter refused
at the first local declaration, without guest publication. The repaired
bounded projector now admits discarded source-contiguous `++i;`, `i++;`,
`--i;` and `i--;` writes to the active automatic unsigned local. It proves
Clang ancestry, exact identifier width, prefix/postfix two-character token
position, no extra metadata, and a byte-representable result before each
store. The protected `for` induction variable cannot be mutated this way.

All four complete ascending or descending `while` variants compiled to
actual Malbolge. The normative VM emitted the independent twelve-byte
Fibonacci oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03` under empty and
nonempty stdin. A source underflow, separated prefix token, forged AST
parent, operator, target, extent or metadata refused without guest
publication. The JSON-only proof cannot authenticate equal-width source
spellings or `++` versus `--` independently of the pinned frontend and the
driver's source digest. This remains compile-time C-state replay with a
12-trip ceiling, not dynamic guest `while` execution; the original unmasked
Fibonacci output still lacks a general layout witness.

### Conditional branch-local lexical scopes (2026-11-09)

The complete twelve-iteration masked Fibonacci C program was retried with a
source-declared `unsigned selected` inside each conditional branch, and with
an additional nested lexical brace around the even branch's temporary. The
pinned Clang frontend accepted the whole C source, but the typed JSON adapter
initially refused its first declaration statement without publishing guest
output. The repaired source-backed projector now proves declarations in both
branches, source order, nested brace ancestry and all expression effects. It
drops branch-local names at the end of each arm while retaining enclosing
Fibonacci writes and only selected guest outputs. The same local name in the
disjoint branches is permitted only after the first arm's scope closes.

The actual `malbolge-2026` VM emitted the twelve-byte independent oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` with both empty and nonempty stdin;
an initial variant took 47 guest steps. A zero-trip variant emits only a later
`0x41`, and a division by zero in its skipped nested conditional, excessive
brace nesting, forged branch parentage and extraneous metadata all refuse
without a guest artifact. The accepted projection is finite C-state folding;
this does not implement runtime guest C scopes, branching or arithmetic. The
original unmasked stream remains blocked at layout.

### Bounded C `for` exit statements (2026-11-09)

The full twelve-iteration masked Fibonacci C source was retried with an
explicit `if (i == 6U) { break; }` after the recurrence transfer. The pinned
Clang frontend accepted the whole source but the typed adapter initially
refused the first declaration and published no guest output. A bounded
source-backed exit proof now admits `break` and `continue` only within a
canonical `for` loop, checks Clang parentage, metadata and exact keyword span,
and keeps the selected exit separate from the unselected conditional arm.
`break` terminates replay without advancing the induction counter; `continue`
advances the counter through the original checked step. An exit must be the
last effect within its lexical block, or the whole source refuses rather than
silently discarding an unchecked dead suffix. Arbitrary post-exit C
statements remain unsupported.

For a break selected after iteration 6, the independent C oracle is the first
seven bytes `02 19 1f 08 17 0f 02`; a `continue` at the same iteration
preserves all twelve masked Fibonacci bytes
`02 19 1f 08 17 0f 02 0d 03 10 13 03`.
The focused whole-source test checks both artifacts under empty and nonempty
VM stdin, rejects unreachable effects after the selected exit, and exercises
forged break ancestry, keyword identity and metadata. This is closed bounded
C-state replay with actual Malbolge byte output, not runtime C branching or
loop control; the original unmasked guest-layout blocker remains.

### Bounded C `while` loop exits (2026-11-09)

A complete five-bit masked Fibonacci C recurrence was retried with a
source-declared unsigned counter, a pure `while` comparison and an `if`
selecting `break` or `continue` after the counter update. The pinned Clang
frontend accepted the whole source, but the typed adapter originally refused
its first declaration without publishing guest code. The closed projector
now binds exit keywords to the active `while` body as well as the existing
bounded `for` body. A selected `break` preserves earlier byte effects and
ends replay before rechecking the guard; a selected `continue` rechecks the
original source-proven guard. An exit may not hide later effects in its
lexical block, and malformed keyword parentage or metadata still refuses.

A 13-bound `while` with a selected break after its twelfth iteration emits
the independently calculated twelve masked Fibonacci bytes through the
normative guest VM under empty and nonempty stdin. Separately, a three-bound
`while` exits after its second iteration and the guest emits the
independently verified `Q.` pair, proving a genuine early break rather than
just a final iteration limit. A bound-12 `while` with selected `continue`
emits all
twelve oracle bytes. A zero-trip while proves a selected break in shadow state,
discards speculative effects and emits only a later source-derived `A`; an
undefined divisor within that skipped body is rejected. Exact Clang keyword,
parent and metadata mutations also refuse without publication. This remains
bounded compile-time C-state replay, not runtime guest C control flow. The
original unmasked stream and arbitrary seven-byte layout remain unsupported.

### Selected `do…while` exits in a full C recurrence (2026-11-09)

A complete twelve-output masked Fibonacci C program with a body-first
`do { ... } while (i < 13U);` and source-selected `break` initially
refused at the JSON-to-typed adapter, publishing no guest artifact. The
finite projector now allows selected `break` and `continue` in the
source-proven `do` body. As in C, an executed `break` terminates after
preserving preceding body outputs, while `continue` reaches the trailing
predicate. The remaining condition subtree is still required to be pure
and source-proven even when the executed break skips its value; unsupported
or undefined unexecuted conditions fail closed rather than being assumed
safe. Source-checked lexical bounds, iteration-local lifetimes and the
12-trip ceiling are retained.

Both complete variants emit the independent twelve-byte masked Fibonacci
oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03` on the actual normative
Malbolge VM with empty and nonempty stdin. A three-bound `do` with break
after its second iteration emits only `Q.` instead of a third byte,
proving genuine early exit even while its trailing predicate would remain
true. Post-exit statements and forged Clang keyword, parent or metadata
refuse without publication. This is bounded compile-time C selection, not
runtime guest C control flow; the original unmasked twelve-byte stream
and generalized guest layout remain unsupported.

### Checked compound C assignments in a full recurrence (2026-11-09)

The entire twelve-iteration masked Fibonacci source was rerun with its
`b = next;` state transfer replaced by each of `b ^= b ^ next;`,
`b += next - b;`, and `b -= b - next;`. The pinned Clang frontend accepted
these complete C programs; before the fix, the typed adapter rejected the
first declaration because it could not prove the later compound assignment.
The bounded projector now proves the old local value, the complete pure
right-hand expression, the canonical two-character operator geometry, and
the unsigned `u32` operation before updating one active local. The result
was initially byte-bounded; `+=`, `-=`, and `^=` were the first admitted
compound local writes. Loop induction retains its separate strict contract.

All three full variants emitted the independent twelve masked Fibonacci
bytes through the normative guest VM under empty and nonempty stdin in a
260.944-second complete replay. Unrecognized compound operators, undefined
arithmetic, incompatible-width destination symbols, forged ancestry or
metadata, and broken source span geometry refuse without publishing a guest
artifact. The JSON-only adapter does not independently recover the original
operator characters or distinguish forged same-width identifier spellings;
source authenticity remains part of the pinned frontend trust boundary.
This is finite C-state folding, not guest runtime state or general C
compound-assignment support. The original unmasked
Fibonacci stream still refuses at guest layout.

### Full-width unsigned compound local writes (2026-11-10)

Two more complete twelve-iteration, branch-selecting masked Fibonacci C
sources were attempted before changing the typed adapter. Both initially
failed at the first unlowered declaration, without guest publication. The
first replaces the recurrence transfer with `b |= next; b &= next;`;
unsigned bitwise OR then AND must write `next`, not leave the prior value.
The second uses `unsigned wide = next + 65536U;`, then `wide %= 256U;`,
`wide <<= 1U;`, `wide >>= 1U;`, `b *= 0U;`, `b += wide;`, and `b /= 1U;`.
This exercises actual wide-state narrowing, both shift widths, zeroing and
restoration of C recurrence state. Independently computed scalar oracles
confirm twelve expected masked Fibonacci bytes.

The closed local-flow proof now admits ordinary unsigned `&=`, `|=`,
`*=`, `/=`, `%=`, `<<=` and `>>=` along with the earlier `+=`, `-=` and
`^=`. Each reads its prior local value and evaluates a source-proven pure
right-hand expression under exact unsigned 32-bit semantics. A contiguous
same-line token gap must match the two- or three-character operator; zero
division/remainder and shift counts above 31 refuse. C loop induction and
unsupported effects remain outside this wider local-store contract.

Both complete programs compile to real 2,207-byte modern Malbolge capsules.
The normative VM emits `02 19 1f 08 17 0f 02 0d 03 10 13 03` after
47 steps under both empty and binary stdin. Seven invalid source variants
and six forged AST variants reject without publication, including undefined
arithmetic, broken operator geometry, inconsistent parentage and extra
metadata. Normalized JSON does not authenticate same-width operator spelling
independently of the pinned frontend and driver's source-digest proof.
The original unmasked twelve-byte Fibonacci C stream still fails at layout;
this is bounded compile-time unsigned-C evaluation, not dynamic guest C state
or generalized arbitrary guest output. P0 remains open.

### Stored unsigned Boolean predicates in a full recurrence (2026-11-10)

A new complete twelve-iteration Fibonacci C experiment replaces the direct
`if ((next & 1U) == 0U)` branch with an automatic `unsigned even` initialized
by the same comparison and `if (even)`. The first pinned compiler attempt
refused at the JSON-to-typed adapter, without emitting a guest. A second and
third variant use `!((next & 1U) != 0U)` and `(next & 1U) < 1U` respectively.
All three retain source-defined loop state, arithmetic, both output arms,
and twelve distinct ordered byte effects.

The closed evaluator now admits the pinned Clang implicit `int` to `unsigned`
conversion only when its `u32` `integral-cast` node has the exact span of a
complete checked `i32` Boolean subtree. Existing pure source-backed
comparisons, logical operators and negation prove a result of zero or one.
Signed casts, side effects, undefined division, calls, and seven separately
forged AST changes reject without publication. In particular a claimed
`i32` result cannot be treated as an arbitrary unsigned value.

All three full programs compile to genuine guest capsules, then emit the
independent masked Fibonacci oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03`
on the normative VM under empty and binary input. The full positive
regression took 223 seconds on the local host. This is *compile-time* C
predicate evaluation and verified guest output, not live guest Boolean
state. The unmasked original `02 59 5f ...` stream still lacks a layout
witness; P0 remains pending.

### Source-proven lexical shadowing in a complete recurrence (2026-11-09)

A full twelve-iteration masked Fibonacci C source introduced a nested loop
block declaring a new `unsigned b`, while its enclosing recurrence already
had a distinct `b`. The inner `b` supplies selected `putchar` arguments,
but the next recurrence transfer must read and update the enclosing `b`.
The pinned Clang stage accepted the complete C program, but the bounded
typed adapter initially refused at its first declaration statement without
publishing guest output. The projector now admits distinct same-name locals
only across source-proven lexical scopes, selecting the innermost visible
symbol for both reads and writes. Same-scope aliases remain unsupported.

Two complete C variants independently reach the normative `malbolge-2026`
VM: the shadowed local is initialized to its output value directly, or is
initialized differently and then explicitly reassigned before output.
Both emit the twelve oracle bytes `02 19 1f 08 17 0f 02 0d 03 10 13 03`
under empty and nonempty stdin, while the enclosing recurrence state stays
unchanged by the shadowed writes. Forging a Clang inner read or assignment
target to refer to the still-active outer symbol now refuses, as do forged
declaration parentage, metadata and invalid source arithmetic; no failed
case publishes a guest artifact. These are finite source-proven C state
projections, not dynamic C lexical environments or runtime C variable
storage in the guest. Original unmasked Fibonacci still lacks a guest
layout witness.

### Conditional void return in bounded whole-program C (2026-11-09)

A complete twelve-output masked Fibonacci program with a `for` bound of
thirteen and a source-selected `return;` after iteration twelve initially
refused at the typed adapter, with no guest artifact. The closed projector now
proves an exact six-character Clang void-return statement and propagates a
selected function exit through bounded loop replay, distinct from an inner
`break`. Both conditional arms remain source-checked, and an unselected
return is discarded along with its speculative state. A selected return is
accepted only when no subsequent statement or unproved effect remains, even
outside the enclosing loop; malformed return parentage, keyword, metadata and
source extent refuse without publishing an artifact.

The full C source reaches the actual normative guest VM and emits the twelve
independently computed bytes `02 19 1f 08 17 0f 02 0d 03 10 13 03` on both
empty and nonempty stdin. The thirteenth would have been executed without the
source-selected return. A second complete C recurrence emits the independent
`Q.` pair on an early selected `for`, `while` or `do…while` return, as well as
when the `for` return arm is never selected. All four forms are checked through
the actual VM on both stdin modes. These are checked, finite C-state
projections, not runtime guest stack unwinding or general C function-call
support. The original unmasked Fibonacci output remains blocked by guest
layout.

### Source-expression metamorphic parity (2026-11-09)

The complete 12-iteration five-bit masked Fibonacci C program has a bounded
metamorphic matrix that inserts either `0x20` or `0x40` XOR into **both**
conditional output arguments before the `& 31U` truncation. The independently
checked C identity `(value ^ high_bit) & 31U == value & 31U` holds for each
selected high bit, including input boundary values. Both entire changed C
sources pass pinned Clang, the closed JSON adapter, typed lowering, and layout.
The actual `malbolge-2026` VM emits the same `02 19 1f 08 17 0f 02 0d 03 10
13 03` twelve-byte stream with empty and nonempty stdin; a tested witness
executes 47 guest steps. `tests/test_compound_c_pipeline.py` owns the
replayable two-seed acceptance test. This exercises new source expression
ancestry and constant propagation without adding any emit-N fixture.

The unmodified, unmasked Fibonacci C source still refuses with
`Layout(UnsupportedEffectTrace)`. A bounded follow-up experiment could not
produce its first `02 59 5f` three-byte prefix by increasing graphical
source-scratch depth from five to twelve operations, nor by combining verified
two-output source-scratch prefixes with a relocation to loader-expanded data.
These were proposal-search failures, not a semantic impossibility proof; no
unverified guest proposal was admitted or retained. The stop condition for the
new metamorphic matrix is two independent high-bit seeds, both stdin modes,
exact whole-stream parity and explicit recognition that runtime C state and
the unmasked byte-stream target remain unsupported.

### Postfix `for` induction in a complete C recurrence (2026-11-09)

The full 12-iteration five-bit masked Fibonacci C program was retried with
`i++` instead of `++i` in its `for` step. The pinned frontend accepted the
source, but the strict local-state projection initially refused its first
`declaration-statement`, without publishing a guest. The adapter now admits
the source-proven **postfix** unary increment alongside the established
prefix form, only where the expression result is unused as a `for` induction
step. The Clang operator, counter symbol, exact parentage and two-character
postfix source extent must agree; decrement, compound assignment and forged
increment metadata fail closed. The independent twelve-byte C oracle is
`02 19 1f 08 17 0f 02 0d 03 10 13 03`. The actual current-profile guest
reproduces it in 47 VM steps. Both stdin modes and negative-source/AST
mutations are replayed in `tests/test_compound_c_pipeline.py`.

This is a new complete-source loop syntax admitted by compile-time static
state projection, not a guest runtime increment or general C loop execution.
The original unmasked Fibonacci stream remains unsupported at layout.

### First source-bound automatic-local output

A separate pinned-Clang source now exercises a real automatic `unsigned`
local initialized to `65U`, then read by `putchar(value)`. The closed JSON
adapter admits the exact single-definition/single-use AST, connects the
source-bound declaration to its read, and promotes this unmodified constant
local to a typed byte SSA value. Its `0..255` admission range preserves the
unsigned-to-signed call conversion and low-byte output for this slice.

The existing byte backend independently checks its selected guest witness.
The compiled capsule emitted `0x41` under the normative profile VM in
31 steps on 2026-11-05. The tracked regression is
`tests/compiler/c-frontend/accepted/local_initialized_output.c`, with native
process/VM acceptance and tampered-node rejection tests. The declaration
and its use must carry the same canonical Clang symbol reference.

This is source-bound constant propagation for one immutable local, **not**
general automatic storage, mutable variable assignment, or guest integer
computation. An out-of-range or nonliteral initializer, additional effect,
branch, loop, or unsupported symbol relationship must reject without
publishing an artifact.

### Ordered literal writes to an automatic local

The pinned Clang experiment `local_reassigned_output.c` initializes one
`unsigned` local with `0U`, then writes `66U` and `65U`, and outputs the local.
Before the repair, the adapter refused the whole source at the first local
statement and published nothing. The repaired adapter admits at most eight
consecutive `=` assignments of source-backed `u32` literals in `0..255`.
It checks their exact AST ancestry, spans, order, and matching symbol before
eliminating the unobservable dead stores. Only the final literal is emitted as
a source-attributed typed byte SSA value, with one real guest output effect.
The actual current-profile VM emits `41` (hex) in 31 steps. Arithmetic
involving the prior local value was unsupported at this stage.

This is bounded dead-store elimination, not a guest implementation of general
mutable storage. Neither runtime arithmetic nor aliases, multiple variables,
conditional execution, or loops are supported by this projection. The original
Fibonacci program still refuses at its first declaration and remains the P0
end-to-end acceptance target.

### Bounded prior-value arithmetic writes

The pinned C fixture `local_arithmetic_output.c` contains one automatic
unsigned local initialized with `60U`. It then computes `value + 8U`,
`value ^ 3U`, and `value - 6U` through three source-bound assignments.
The initial value and three operators are checked against the complete
Clang AST, including exact symbol references, types, node ancestry and
nonoverlapping source spans. The adapter reads the previous proven value
for each operation and admits only results in `0..255`; it rejects
multiplication, unbounded or wrapping intermediate arithmetic, aliases,
foreign reads and extra effects. The live typed SSA constant receives the
last arithmetic expression's source span rather than an invented literal.

The independently verified guest output is `41` (hex), produced by the
existing Malbolge byte-output witness in 31 normative VM steps. The guest
performs **output**, not the arithmetic: this route is source-constant
propagation and dead-store elimination, not a runtime arithmetic backend.
General state, multiple locals, branches and loops still need actual
ternary and layout lowering. The original Fibonacci target remains blocked.

### Cross-local, source-proven constant flow

A new whole-source experiment `local_multi_output.c` declares three separate
`unsigned` locals, initializes `a` and `b` to `60U` and `8U`, initializes
`result` from their sum, then applies XOR `3U` and subtraction `6U` before
`putchar(result)`. The original pinned Clang-to-guest pipeline refused its
first declaration and published no guest artifact. The repaired JSON adapter
proves ordered, symbol-matched reads across distinct locals, exact AST
ancestry and spans, and every intermediate result within `0..255`. It accepts
up to eight distinct automatic unsigned locals, 16 straight-line writes and
bounded expression depth, with one final output call. Undeclared reads,
aliases, unchecked overflow, extra effects, control flow and other calls fail
closed. The live source expression anchors the final typed byte definition.

The actual emitted `.malbolge` capsule outputs `0x41` in 31 normative VM
steps. `tests/test_compound_c_pipeline.py` compares the real guest output
against `(60 + 8) ^ 3 - 6`, and the pinned JSON mutation regression proves
foreign symbols and unsupported effects refuse admission. Arithmetic remains
compile-time constant propagation; the guest performs only the witnessed byte
output. General locals, runtime arithmetic and loops are **not** implemented.
The original Fibonacci target continues to reject at its first declaration.

### Bounded source-proven conditional selection

A new demanding C branch experiment uses three initialized unsigned locals,
computes a cross-local sum, and selects one of two updates under
`if ((result & 1U) == 0U)`. The pinned frontend first rejected this whole
source at its first declaration without publishing any guest program. The
repaired multi-local projection checks the `i32` equality, nested unsigned
AND, all symbol references, exact source ancestry and spans, and one
side-effect-closed assignment in **each** brace-delimited arm. It evaluates
both arm shapes against the same proven incoming constants and retains
only the selected successor state before the final `putchar`.

Two source-backed variants exercise opposite outcomes: `60 + 6` selects
`result ^ 3U`, while `60 + 7` selects `result ^ 2U`. Typed-IR assertions
confirm that the live definition comes from the correct C line in each
variant. Both actual capsules output `41` (hex) in 31 normative VM steps.
Foreign reads, wrong operators, missing or nested arms, extra effects and
malformed metadata reject. At most 16 bounded writes are admitted,
counting both branch arms, and every intermediate arithmetic value must
fit `u8`. This is compile-time constant propagation, not an executable
guest branch or generalized mutable state. The original twelve-output
Fibonacci program still refuses at its first declaration; runtime loops,
variable-dependent output, and guest control flow remain pending.

### Conditional expression-derived output

The tracked pinned Clang source `local_expression_output.c` now selects a
proven branch update across three `unsigned` locals, then outputs the
**expression** `(int)(result ^ 3U)` instead of outputting a bare local. A
closed argument walker checks the explicit conversion, C parentheses, nested
unsigned arithmetic and source-bound local reference; any unconsumed effect
or mismatched Clang ancestry refuses publication. A red-first Rust regression
and mutated-node tests establish that the byte's SSA origin is the actual
call argument rather than an earlier variable write.

Two real native C-to-Malbolge compiler runs select different branch outcomes:
the first produces guest byte `0x41` in 31 VM steps; the second changes the
branch and argument constant and produces `0x42` in 69 VM steps. Independent
C arithmetic gives those values, and `tests/test_compound_c_pipeline.py`
checks actual guest output and rejects multiplication without an artifact.
A distinct `0x40` experiment reached the layout backend but was refused as
`UnsupportedEffectTrace`: the current positional single-byte guest witness
table does not contain that byte. The compiler did not fabricate guest output.
All arithmetic and control flow in the admitted case is still evaluated at
compile time; guest runtime computation, general loops and multi-byte dynamic
output remain unimplemented. The original Fibonacci acceptance is pending.

### Nonbyte unsigned intermediates with source-proven masking

The original Fibonacci loop computes `next = (a + b) & 255U`, which may
have a nonbyte sum even when the stored result is a byte. A pinned Clang
probe with `a = 233U` and `b = 144U` initially refused in the multi-local
adapter because the expression walker did not admit its nested parentheses.
The revised bounded evaluator retains the **checked `u32`** value 377 through
the inner addition, applies `& 255U`, and only then proves the byte 121
assigned to `next`. Source-proven Clang parentheses and an explicit
`putchar((int)next)` cast are now admitted while unknown operations, symbols,
AST mutations and extra effects still refuse. The leaf literals and each
materialized local remain byte-bounded; this is neither arbitrary 32-bit
C lowering nor guest runtime computation.

In a complete loop-free branch probe, the odd condition selects XOR 56,
producing `0x41` in 31 normative VM steps. An independent second C variant
uses `232 + 144`, selects the even condition with XOR 58, and produces
`0x42` in 69 normative VM steps. Both real guest capsules were compared
against independent C arithmetic and a pinned JSON regression verifies the
actual typed source span. The original twelve-byte Fibonacci experiment
still refuses its first declaration: its stateful `for`, repeated output,
and guest control flow remain missing and P0 stays open.

### Closed, statically evaluated C for-loop state

A new pinned Clang experiment
`tests/compiler/c-frontend/accepted/local_static_loop_output.c` reuses
Fibonacci-like unsigned locals in `for (unsigned i = 0U; i < 8U; ++i)`.
Its body declares an iteration-local `next`, computes a masked sum, selects
one of two source-proven assignments with `if/else`, and transfers the state
into `a` and `b`. A single `putchar` after the loop reads the final state.
The original full source was attempted first and still rejects because it
emits *inside* its loop.

The bounded adapter now proves an exact Clang `for-statement` declaration,
`u32` counter read, `i32` less-than comparison against a byte literal,
`++` increment, brace-delimited body and matching symbol/span ancestry.
It accepts only a zero-initialized, private `unsigned` counter with a bound
from 1 through 12. Each iteration replays the **same checked AST** against
proven local values, disposes of loop-body locals on scope exit and advances
the counter. Assignments to the counter, nested loops, effects inside the
loop, unsupported operations, and out-of-budget iteration bounds reject.
The body may contain bounded local declarations, assignments, and the
previously proven closed conditional assignments. All materialized locals
stay byte-sized; wider checked unsigned intermediates require masking.
The result is one constant-SSA byte with a real guest output, **not** a
Malbolge loop or guest runtime arithmetic.

Independent unsigned-C arithmetic yields `a=26`, `b=42` after eight
iterations and `42 ^ 107 = 65`. The real source-to-Malbolge pipeline emits
`0x41` in 31 normative VM steps, with a source variant at seven iterations
also producing `0x41` after independent oracle adjustment. Tests assert
changed counter identities, loop controls, branches and added effects refuse
publication. The complete twelve-byte Fibonacci program remains blocked by
loop-body output and dynamic guest control-flow realization.

The remaining first semantic gap for the original complete program is the
**general runtime** local-variable declaration, initialization, read/write
and provenance needed through typed IR and ternary lowering. The same
program additionally needs arithmetic, bounded loops, conditional branches,
and value-dependent `putchar`; the active
`docs/todo/open/compiler/ternary-machine-lowering.mdc` and
`docs/todo/open/compiler/malbolge-layout-and-encoding-backend.mdc` own the
subsequent executable target and control-flow realization. Re-run the **same**
complete program after each meaningful capability correction; retire this P0
only when its actual guest VM output matches the independent reference.

Do not substitute a host output transcript for guest execution or retreat
to another 49-byte literal-output demonstration to avoid this failure.

### Bounded branch-selected output inside a source-proven loop

The full twelve-iteration, branch-selected-output Fibonacci program was
retried. Before this change it still failed at the first local declaration.
A source-close variant, `local_loop_branch_output.c`, retains the same
three-state updates, masked sum, conditional and `putchar` inside the loop,
but proves zero using `next ^ next` in the even arm and `next - next` in
the odd arm. The pinned Clang AST is consumed completely for both arms on
every iteration; only the selected call is added to the ordered typed
output effects. Its `u32` state and loop counter are still **evaluated by
the compiler**, not by Malbolge.

The selected calls produce twelve verified zero bytes, with four even and
eight odd arms. The canonical typed IR contains one zero-valued SSA
constant and twelve distinct `ByteOutput` effects. The existing
zero-output backend generates a real guest capsule, and the normative VM
emits `00` twelve times in thirteen steps; a seven-iteration variant
emits seven zero bytes in eight steps. Tests refuse an unknown callee,
altered predicate, extra effects and a nonzero stream without publishing
a guest artifact. This is a new observable control-flow effect boundary,
not a fixed literal-count fixture.

The original compound program still requires **arbitrary nonzero output
sequences**: its reference is `02 59 5f 08 57 4f 22 6d 03 90 b3 23`.
The finite witnessed backend cannot yet realize that ordered sequence,
and the adapter explicitly rejects the unverified trace. General guest
state, dynamic loop execution and P0 completion remain pending.

### Source-proven, heterogeneous output from a bounded C loop

The original twelve-iteration Fibonacci C program was retried after the
selected-output loop proof. The next failure was the projection's assumption
that all selected output effects shared one byte. The generalized projection
now materializes a **distinct typed `u8` SSA constant for every selected
nonidentical output**, retaining the actual source expression and call spans
for each iteration. It selects an existing backend mode by the trace length
(up to twelve folded iterations) and leaves every byte value for the
independent typed/ternary/VM verifier to admit or reject. Uniform zero or
nonzero streams still use the existing one-SSA paths.

A complete source-backed two-iteration branch-and-loop experiment,
`local_loop_distinct_output.c`, evaluates the same Fibonacci-like state
transfers. Its even arm emits `2 ^ 83 = 81` (`Q`), and its odd arm emits
`3 ^ 45 = 46` (`.`). This is the independently witnessed guest pair `Q.`:
the real Clang-to-Malbolge capsule runs under the normative VM and emits
those two bytes. The pinned JSON regression checks distinct SSA IDs, exact
C call spans, both branch proofs, and foreign-symbol/operator rejection.
A C mutation changing `83U` to `82U` yields an unwitnessed pair and refuses
at the backend without publishing a guest artifact.

The **original full twelve-byte** C program now passes this bounded C
projection and the structural typed-byte adapter, which checks all twelve
source-backed `u8` definitions and SSA uses without choosing output values.
The canonical ternary bridge then reaches `--distinct-literal-twelve`, whose
independently witnessed guest layout is for a *different* fixed sequence.
It rejects with `Layout(UnsupportedEffectTrace)` and publishes no artifact.
The two-byte adapter similarly retains distinct nonzero SSA and delegates
which pairs are executable to the verified guest layout. An unwitnessed pair
now fails at that boundary, not while decoding the typed source. Neither
change synthesizes arbitrary bytes, adds runtime C state, or completes P0;
verified general guest byte-stream lowering remains the blocker.

### Bounded verified two-byte layout search

The distinct-pair guest bridge no longer chooses only three hard-coded byte
pairs. For the canonical current profile, it enumerates 94 graphical prefix
phases and both `p`/`*` arithmetic choices at each of two output positions.
A disposable loader/accumulator preview discards nonmatches before invoking
independent positional layout admission. Two external guest writes must be
distinct, and empty-input and nonempty-input normative VM runs must agree
with the source-proven bytes. The artifact publisher separately decodes and
admits the actual graphical source against exactly this two-write grammar
before its own VM replay; it does not trust the bridge's preview or a fixed
pair table.

The tracked two-iteration Fibonacci-style conditional C program, changed to
select `2 ^ 0 = 0x02` and `3 ^ 204 = 0xcf`, now produces `02 cf` from a
published capsule executed by the normative guest VM. This is a new binary
pair with mixed `*` and `p`, not an extra emit-N source fixture. The old
`Y/`, `Y$` and `Q.` guests remain exact. Unwitnessed streams still refuse
without a published file. The original twelve-iteration Fibonacci oracle
`02 59 5f 08 57 4f 22 6d 03 90 b3 23` remains unsupported by the
finite twelve-byte layout; P0 and dynamic guest state remain pending.

### Composed two-byte arithmetic from the original C experiment

The original conditional Fibonacci C program was reduced to two iterations
with the odd-arm XOR changed to `54U`, preserving its local state, bounded
loop, masked unsigned addition, conditional and source-proven output effects.
Its independent result is `02 35` in hexadecimal: the first value is 2 and
the second is `3 ^ 54 = 53`. The pinned Clang frontend, typed adapter,
ternary lowering and Malbolge layout now produce a real guest capsule that
the normative VM replays to exactly those bytes. This expands the earlier
two-write pair grammar to one extra arithmetic write, with bounded no-op
strides and three distinct out-of-source guest memory writes.

The candidate preview caches positional graphical encodings instead of
rescanning all printable characters for each candidate. The cache has no
acceptance authority: the layout is independently decoded, checked for
self-modification geometry and replayed on empty and nonempty input before
publication. An expanded negative regression now treats `QZ` as an admitted
VM-replayed pair rather than incorrectly expecting its refusal. Equal
output bytes were historically rejected by the distinct-pair bridge and the
independent publisher; the source-bound repeated-pair extension below now
admits witnessed equal pairs with distinct SSA identities and genuine guest
outputs. This is a bounded guest layout, **not** general runtime arithmetic,
looping or twelve-byte Fibonacci acceptance. P0 remains open.

### Source-proven triple output through bounded mixed guest arithmetic

The full twelve-iteration Fibonacci compiler experiment still fails closed at
its twelve-output layout boundary. Its independently computed first three
bytes, `02 59 5f`, likewise have no witness under the newly expanded bounded
three-output grammar. Neither failure publishes a guest artifact.

The three-output compiler backend now proposes an independently checked
combination of `p` and `*` at each of three output positions, across all 94
canonical graphical prefix phases. A finite additional search admits up to
eight no-op data strides before and between writes within twelve short prefix
phases. Cached graphical decoding and a disposable accumulator model accelerate
only candidate selection. The layout encoder must still prove three distinct
out-of-source data writes; the publisher separately re-decodes and admits the
actual staged guest and replays it under the normative VM with empty and
nonempty input. C source and typed adapters preserve three distinct output
SSA identities and delegate candidate-byte acceptance to this boundary.

Two native C-to-capsule-to-normative-VM probes establish new exact outputs:
`5a 0a de` in eight steps using three guest arithmetic writes and `51 2e 5a`
in 33 steps with nonzero data-pointer strides. Both have source-backed typed
outputs and full guest stdout parity; neither claims runtime C state or
arbitrary bytes. Previously admitted positional triple witnesses remain
byte-identical. This is a partial capability, not P0 completion.

### Checked product in a source-proven C recurrence

A complete three-iteration C recurrence now checks a distinct arithmetic
construct: `unsigned next = (a * b) & 255U`. Starting from `a=3`, `b=5`,
the product and parity-selected assignment update the local state through
`next = 15, 210, 22`; the final `putchar((int)(a ^ 86U))` emits `0x41`.
The original pinned pipeline refused this source at its first declaration.
The repaired bounded constant evaluator admits `*` only for `u32` operands
with `checked_mul` and stores only byte-range results. An unmasked product
outside the byte domain, unsigned overflow, division, unrecognized effects,
and forged AST structure remain rejected rather than being silently folded.

The end-to-end regression replays the **actual** Malbolge guest under the
normative VM with empty and nonempty stdin: `0x41` in 31 steps, equal to an
independently computed C oracle. This admits a new C arithmetic construct,
not multiplication, branches, or loops at guest runtime. The original
Fibonacci program is retried separately and remains rejected at
`Layout(UnsupportedEffectTrace)` for its unwitnessed twelve-byte sequence.
P0 is therefore still open; the earlier guest layout synthesis gap remains.

### Later verification matrix

Only after the complete experiment succeeds, use a deterministic corpus
generator to broaden coverage without manually creating one source and
technical document for every output length.

One versioned matrix specification declares a fixed seed, the C output
program template, target profile, resource limits, and oracle encoding.
The generator uses deterministic byte vectors of lengths 0, 1, 2, 3, 7,
8, 16, 32, 48, 64, 128, and 256, plus budgeted seeded lengths.

The vectors cover ASCII, all 32 low control bytes, zero, 0xff, high-bit
bytes, repeated bytes, and distinct-byte permutations. More than 256
positions necessarily permit repeats even when testing all byte values.

## Invariants

- Generate cases from inputs and a seed, not from separate manual fixtures.
- Translate each generated C program through the real compiler frontend,
  typed lowering, layout backend, and published Malbolge artifact.
- Run the actual guest in the normative VM under an explicit step budget.
  Byte output must come from guest behavior, not a host-generated substitute.
- Compare VM output to an independent byte-oracle before accepting a case.
  Record compiler identity, source hash, output hash, steps, and resources.
- One parameterized test runner must replay the whole retained corpus.
  Existing teaching artifacts keep their own source and SHA identities.
- Reject unsupported input, missing tools, timeouts, output drift, and
  incomplete lowering with typed failures rather than fabricated success.
- Test metamorphic relations such as repeated prefixes, concatenation,
  permutation, and equivalent C syntax only when the compiler promises
  the corresponding source semantics and exact output relation.
- Prevent regression masking: one failing case reports its seed, vector,
  source artifact, first byte mismatch, and reproducible command.
- Enforce an explicit wall time, memory, VM-step, and case-count budget.
  A truncated run is incomplete; it cannot publish a green receipt.
- A case that exposes a missing C feature becomes a compiler feature task
  with a red-first regression, not another arbitrary `emit-N` milestone.
- Use coverage of implemented C semantics, control flow, memory safety,
  input/output, and compiler lowering as progress metrics, not the maximum N.

## Failure Behavior

Do not infer support for general C, arbitrary loops, dynamic input, or
unbounded output from a finite sequence of literal `putchar` programs.
A single mega-source that prints 256 constants is also only one witness;
it does not replace the parameterized semantic and metamorphic matrix.

A compiler can pass every retained fixed example while mishandling a
single input-dependent expression. The matrix must detect such defects,
retain the smallest reproducer, and avoid adding repetitive manual pages.

## Verification

Start by running `python3.14 -B -m unittest` on the existing
`tests.test_versioned_example_corpus` matrix. A new generator and
parameterized contract test shall add deterministic seeded cases without
requiring one new test module for every output length.

The mandatory evidence is exact C-to-Malbolge compilation, independent
VM output and trace, source/guest digests, finite budgets, negative cases,
reproducible seed replay, and no dependence on untrusted host output.

Completion means the generalization is tested across the declared matrix,
not merely that the next individual `emit-N` example works. If input or
control-flow lowering is not supported, report that precise gap and leave
the product claim incomplete rather than extending examples forever.

## References

- `docs/technical/examples/versioned-c-malbolge-corpus.md`
- `docs/todo/open/applications/versioned-c-and-malbolge-example-corpus.mdc`
- `docs/todo/open/compiler/malbolge-layout-and-encoding-backend.mdc`
- `docs/todo/open/compiler/ternary-machine-lowering.mdc`
- `docs/todo/open/compiler/compact-guest-bytecode-strategy.mdc`
- `tests/test_versioned_example_corpus.py`

### Repeated byte values from distinct source-bound loop effects

A three-iteration, conditional Fibonacci-style C program now verifies that
**equal observed byte values need not share a source SSA identity**. The
source-backed recurrence evaluates `(a + b) & 255U` at compile time, selects
`next ^ 58U` or `next ^ 59U`, and produces the independent oracle `38 38 3e`
(`88>`). Before repair the typed bridge refused the full program as
`UnsupportedTypedIr`; the layout publisher also rejected its duplicate bytes.

The repaired three-output bridge retains separate source SSA definitions while
allowing a repeated adjacent output of the *live guest accumulator*. A bounded
positional search proposes two arithmetic data writes and three output
instructions, never copies a host-calculated output stream into the guest.
The independent publisher decodes the complete target from actual source
bytes, validates the repeated-output grammar and distinct out-of-source data
writes, then checks exact termination and output under the normative VM with
empty and nonempty input. The real C-to-guest capsule emits `38 38 3e`.
A mutation that introduces unsupported C multiplication must still refuse
without publishing. The original twelve-byte Fibonacci acceptance target
remains unsupported at layout: C state and branches here are statically
projected, not executed dynamically by the guest.

### Source-distinct C branch effects with equal observed bytes

On 2026-11-06, a two-iteration `for` loop with the same masked Fibonacci
state updates as `local_loop_distinct_output.c` selected opposite conditional
`putchar` arms: `2 ^ 58 = 56` and `3 ^ 59 = 56`. The original C-to-guest
pipeline refused `Layout(UnsupportedEffectTrace)` because the bounded Clang
projection coalesced all same-valued outputs into one SSA constant, then
selected a seeded single-byte layout with no matching witness.

The repaired source-aware frontend retains two independent `u8` SSA values
when the two nonzero equal-valued outputs originate from different C call
spans. Same-call repeated loop effects still use the existing shared-SSA
projection. The exact typed pair lowering preserves both SSA identities;
a bounded positional guest search uses one relocated `p`/`*` write followed
by two genuine `<` output instructions that reuse the unchanged accumulator.
The independent publisher re-decodes the emitted graphical source, verifies
out-of-source guest writes, re-admits the layout, and executes the normative
VM on empty and nonempty input before artifact publication.

Red-first regressions verify the exact selected source spans and distinct SSA
IDs, the one-write/two-output guest trace, actual C-to-VM `38 38` parity,
and refusal of an unsupported multiplication mutation with no guest artifact.
The original twelve-byte Fibonacci program still has no generalized guest
byte-stream witness. Compile-time C loop folding is not a claim of runtime
Malbolge branching or a complete C compiler; P0 remains pending.

### Nonadjacent equal source-derived outputs

A complete three-iteration, index-branching Fibonacci C program now projects
three distinct output effects `5a 25 5a` (`Z%Z`), using masked recurrence
state and a source-backed `next - next` expression. Its first and third
outputs match although the middle output differs. The pinned C frontend,
JSON/typed adapters and bounded triple bridge already synthesized a guest
candidate; the independent publisher refused it solely for nonadjacent
repeated values (`distinct-literal triple has nonadjacent repeats`). The
red-first end-to-end test reproduced this refusal with no published artifact.

The publisher now admits this pattern only through the existing three-write
relocated grammar, with three distinct out-of-source arithmetic data writes,
re-decoded staged instruction bytes, canonical layout admission, and exact
normative VM output under both empty and nonempty input. The complete C
pipeline emits `Z%Z` from actual guest instructions; a multiplication
mutation is rejected before publication. No host output substitution,
dynamic guest C state, general loop execution or arbitrary byte-stream
synthesis is claimed. The original twelve-byte Fibonacci target still fails
closed at layout, so the P0 acceptance remains pending.

### Three identical outputs from source-distinct conditional calls

The three-iteration Fibonacci-like C loop from the nonadjacent-repeat probe
was compiled again with both branch expressions changed to
`(next - next) + 56U`. All three loop iterations still prove the C local
state, chosen branch, and actual `putchar` call effect. The independent
arithmetic oracle is `38 38 38`. Before the repair, the frontend merged
all observations into one SSA constant; the finite single-constant
backend refused the trace.
A red-first complete pipeline regression reproduced the missing artifact.

When two or three nonzero equal-valued effects use different C call spans,
the frontend now preserves separate typed `u8` SSA definitions and their
source spans. The three-effect bridge may compute one accumulator through
one or two relocated `p`/`*` data writes, then execute three distinct `<`
output instructions without changing the accumulator. The independent
publisher re-decodes the actual graphical source, proves the bounded
arithmetic/three-output geometry and nonaliasing data writes, then runs the
normative VM with empty and nonempty input. `888` reaches exact real guest
parity; an unsupported multiplication mutation still refuses without a
published capsule. Same-call uniform loop effects retain the shared-SSA
path, not an invented new source identity.

This covers an additional output-identity shape, not arbitrary byte streams,
execution of C loops in the guest, or the full twelve-byte Fibonacci target.
The latter continues to refuse `Layout(UnsupportedEffectTrace)` and this
P0 remains pending.

### Source-proven unsigned remainder in a complete loop

A new red-first whole-source probe, `local_remainder_recurrence_output.c`,
uses two automatic unsigned locals, three stateful `for` iterations, a masked
`u32` product, odd/even conditional assignments, `next % 17U`, and a final
expression-derived `putchar`. It originally refused at the first declaration
because the unsupported remainder prevented the complete constant projection.
No guest artifact was published. The adapter now consumes the exact Clang
`u32` operator and checks nonzero-divisor `checked_rem` before narrowing.
The separately computed recurrence is `15, 210, 190`, finishing at `a = 2`
and output `2 ^ 67 = 65`. The emitted Malbolge produces `0x41` in 31
normative VM steps under empty and nonempty stdin. At the time, division
and zero-divisor mutations did not publish a guest program.

This is finite source-backed compile-time evaluation, **not** Malbolge
remainder arithmetic, dynamic C state or general stream realization. The
original twelve-byte Fibonacci program still fails closed at the independent
guest-layout boundary; the P0 remains pending.

### Source-proven unsigned quotient in a complete recurrence

A three-iteration whole-C program, `local_division_recurrence_output.c`,
combines two automatic `unsigned` locals, a masked product, conditional
assignments, `next / 17U` in the even arm, state transfers and one final
`putchar`. It initially refused at the first declaration because the
full expression walk could not establish `/`; it emitted no guest artifact.
The checked source-bound `u32` evaluator now uses `checked_div` after
validating exact Clang ancestry, operator and operand types. It refuses a
zero divisor rather than folding undefined C behavior.

The independent unsigned oracle visits product values `15, 210, 170`,
finishes with `a = 11`, and derives output `11 ^ 74 = 65`. The complete
pinned Clang-to-typed-to-ternary-to-layout pipeline publishes a real
Malbolge capsule. The normative VM emits exactly `0x41` after 31 steps
under both empty and nonempty input. Source mutations to division by zero
or an unsupported shift refuse without publishing a guest artifact.
This is closed compile-time state projection; guest division, dynamic C
state, and generalized twelve-byte synthesis remain unimplemented. P0 is
still open because the original Fibonacci trace remains unwitnessed.

### Bounded unsigned-shift C recurrence

A complete source-backed three-iteration C experiment now tests masked
multiplication shifted left by two, branch-selected logical right shifts,
state transfers and an expression-derived output. Before the addition,
`c2malbolge_json` refused the first declaration with `Unsupported`; it
published no artifact. The adapter now checks both shift operators against
exact pinned Clang `u32` AST ancestry and operand ranges. Shift counts
outside 0 through 31 reject rather than evaluating undefined C behavior.

The independent C recurrence visits `next = 60, 80, 192`, finishes at
`a = 25`, and expects `25 ^ 88 = 65`. Golden normalized AST tests check the
byte's actual typed SSA definition and refuse altered operators, forged
symbols, operand types, ancestry and shift counts. This bounded constant
projection does not execute C shifts or branches in the guest and cannot
synthesize the original twelve-byte Fibonacci stream. Its P0 remains open.

### Additional guest write for source-proven three-byte Fibonacci loops

A new full three-iteration source experiment uses the original Fibonacci
local-state transfer, bounded loop and conditional output, changing only the
odd-arm XOR constant to `0x3d`. Its independently evaluated byte trace is
`02 3e 38`. The canonical C frontend and typed/ternary bridge admit its
ordered source effects, while the guest executes four separate relocated
`p`/`*` arithmetic writes and three actual output instructions. This
expands the earlier three-write guest grammar by allowing a fourth write
before one of the output sites, without inventing a host output callback.

The proposal filter caches position-encoded source-length-dependent memory
suffixes and checks predicted byte values before asking the independent
layout encoder to admit a candidate. The separate file publisher parses
its exact decoded instruction grammar, requires every guest data write to
be disjoint and out-of-source, and runs the normative VM on empty and
nonempty input. Independent proposal-model comparisons, source-backed
regressions and VM parity are required; cached previews have no authority.
The earlier original three-byte prefix `02 59 5f` still has no admitted
witness in the bounded grammar; the full twelve-byte Fibonacci target and
runtime guest-side C control flow remain pending.

### Source-distinct four-output projection without a guest witness

A complete four-iteration version of the original conditional Fibonacci C
program, using odd-arm XOR `0x3d`, independently computes the ordered bytes
`02 3e 38 08`. The pinned frontend and JSON adapter admit its locals,
loop, branch, arithmetic, and four separately source-anchored `putchar`
effects. The typed stage previously rejected the fourth byte because its
four-output projector required the unrelated hard-coded teaching sequence
`T=4>`, despite the ternary and guest stages being responsible for positional
layout admission.

The three- and four-output typed projections now share an exact ordered
constant/output validator. It preserves every original SSA ID and call span,
requires an eight-bit scalar with a matching output use, and rejects duplicate
IDs, extra effects, foreign types, and malformed instruction order. The same
full C program now reaches `Layout(UnsupportedEffectTrace)` without publishing
an artifact.

The regression uses an independently computed unsigned-C oracle
and will require actual empty/nonempty-input normative guest parity if layout
support is later added. This is an intermediate compiler-boundary repair, not
four-output guest synthesis, dynamic guest C state, or P0 acceptance. The
original twelve-output Fibonacci experiment still lacks a guest witness.

### Four real guest outputs from source-distinct conditional loop effects

The complete four-iteration Fibonacci C probe with odd XOR `0x3d` still
fails closed for `02 3e 38 08`. A separate full four-iteration C experiment
changes the even arm to `putchar((int)(next ^ 26U))` and keeps the odd arm
at `next ^ 61U`. Its independently calculated values of `next` are
`2, 3, 5, 8`, giving four distinct output bytes `18 3e 38 12` (hex).
Before this repair the pinned compiler rejected the complete source at
`Layout(UnsupportedEffectTrace)` and published no guest artifact.

The bridge now searches four independent `p`/`*` arithmetic writes, each
followed by a real guest output instruction, with up to eleven prefix
no-ops and at most eight no-ops before each write. The disposable search
reuses the immutable loader-expanded memory suffix by source length;
it does not authorize a result. The independent publisher re-decodes the
staged source, verifies four distinct out-of-source writes, admits exact
instruction geometry and replays the normative VM with empty and nonempty
input. The complete masked C loop now emits exactly `18 3e 38 12` on both
inputs. A division-by-zero source mutation refuses without publication,
and proposal-preview parity tests compare the cached model with full
source expansion. The historical `T=4>` witness remains admitted.

This realizes a new four-effect semantic boundary, not arbitrary streams.
The original twelve-byte Fibonacci target and dynamic guest-side C state
remain unimplemented. P0 stays open until the original compound C program
(or another accepted complete compound program with comparable runtime
semantics) meets the contract's full guest-parity acceptance criteria.

### Bounded state-space guest output proposals

A complete four-iteration C recurrence with local state, conditional byte
output, multiplication, division and masking now emits `35 c0 09 e3` through
the current-profile normative guest VM. The source is
`tests/compiler/c-frontend/accepted/local_loop_wide_branch_stream.c`.
The independently calculated unsigned-C values are `2, 3, 5, 8` before the
branch-derived output expressions. Both empty input and `ff 00 80` input
produce identical verified guest output. A division-by-zero mutation refuses
before artifact publication.

The first compiler attempt reached the quad publisher and refused its exact
four-write/output-pair grammar. A new deterministic, capped state-space
proposal searches exact 15-trit accumulator states and source-ordered byte
effects with guest `p`, `*`, `<` and no-op instructions. The loader-memory
suffix cache remains advisory: the independent publisher re-decodes every
instruction, requires four outputs and four to 32 disjoint out-of-source
data writes, re-admits the complete linear source and executes the normative
VM twice before publication. A five-write/four-output regression is outside
the older four-write grammar but passes all checks. The historical `T=4>`
source remains admitted.

The original search covered at most 94 source cells, a 30-cell prefix and
explicit state/node limits. A later bounded extension covers up to 104 source
cells, including ten cells after the first 94-phase positional decode cycle.
The `extended_decoder_phase_reconstructs_real_guest` regression starts with a
100-cell relocated guest, recovers its `3e 3f 2c 12` output using actual
15-trit accumulator transitions, and independently re-encodes and replays the
guest twice. A forged expected byte fails verification. The current search
still uses finite per-geometry state/node limits and a 104-cell budget, below
the graphical relocation operand ceiling of 126. This is a source-independent
layout witness; it does not prove that the compiler needs more than 94 cells
to produce that particular output.

Search exhaustion does not establish target-language impossibility. A renewed
real C-to-guest attempt still refuses the unmodified four-output Fibonacci
prefix `02 59 5f 08` at layout without publication, as does the complete
twelve-output program. C state and arithmetic here execute during compilation,
not as runtime guest C operations. P0 remains pending.

### Alternate terminal source geometry

The four-output state-space proposal now also explores code with an extra
no-op immediately before `halt`, moving the fourth real output earlier. That
changes the two graphical words seeding the loader-expanded memory beyond the
source. The proposal cache substitutes the positional no-op cell only when
computing that memory tail; the actual published source is still produced,
independently decoded, checked for out-of-source writes and replayed in the
normative guest VM under empty and nonempty input. The verified four-byte
`5c 3f 11 42` guest is a geometry witness, not evidence of general C state
or unrestricted byte-stream synthesis. The original twelve-output Fibonacci
program and its four-byte prefix still lack guest layouts.

A subsequent experiment now includes two more source terminators: `p; halt`
and `*; halt` after the final byte output. These instructions write one
out-of-source data cell and replace the loader's final pre-halt seed, but
do not emit another output. The bounded search uses each corresponding
positional encoding only in its disposable tail model; the independent
publisher still checks the complete source, every guest data write and
both normative VM input replays. Both terminal variants reconstruct real
four-output guests with five disjoint data writes, and forged expected
output bytes are rejected. After rebuilding the real layout executable,
the original Fibonacci four-byte prefix and full twelve-byte trace still
refuse without publishing an artifact. The additional search shapes are
not a proof of unrestricted byte-stream synthesis or runtime C execution.

### Source-backed unsigned bitwise OR in a complete recurrence

A separate complete three-iteration C experiment uses local state, checked
multiplication, `|`, masking, shifts, both conditional arms and an output
expression. Its pinned Clang projection initially refused the first local
because bitwise OR was not admitted by the bounded `u32` expression walker.
The expression proof now checks the exact source operator and both operands,
then folds unsigned bitwise OR before narrowing to a byte store.

Independent oracles for OR masks `16` and `8` visit `31, 248, 16` and
`15, 120, 152` respectively. Both derive a final output of `0x41`. Each
complete C source produces a real `.malbolge` capsule that emits `0x41` in
31 normative VM steps for both empty and nonempty input. Changing the source
to logical OR, removing its state-width mask or adding a side-effecting
read refuses without an artifact. The new test is
`test_unsigned_or_recurrence_reaches_real_guest` in
`tests/test_compound_c_pipeline.py`.

This is source-proven, bounded constant evaluation, not guest runtime C OR,
loop execution or generalized stream synthesis. The original twelve-byte
Fibonacci program remains rejected at layout, so P0 stays pending.

### Source-backed unsigned relational conditions

A complete three-iteration C program now exercises automatic unsigned locals,
checked multiplication and shifts, a relational `if` inside a `for` loop,
source-derived state transfers and a final `putchar`. The first pinned-Clang
compile refused the initial declaration because the bounded adapter only
admitted `==` in the conditional expression. The revised closed evaluator
preserves the exact unsigned `u32` operands and typed `i32` comparison result,
and selects both source-proven branches with `==`, `!=`, `<`, `<=`,
`>` or `>=`.

The red-first regression derives the branch sequence and final XOR key
independently for all six operators. Every full C source now emits a real
Malbolge capsule that outputs byte `0x41` under the normative VM with empty
and nonempty stdin. The comparison boundary admits only the existing checked
`(unsigned_expression & mask) OP byte_literal` condition shape; unsupported
logical `&&`, a side-effecting increment and a signed cast in that condition
reject without publication. The checked-in source is
`tests/compiler/c-frontend/accepted/local_relational_recurrence_output.c`;
the end-to-end regression is
`test_unsigned_relational_recurrence_reaches_real_guest`.

Comparison, loop state and branch selection still fold during compilation;
the guest executes the independently checked byte output, not runtime C
comparisons. The original 12-byte Fibonacci acceptance still refuses at
unwitnessed guest layout, so the P0 remains open.

### Source-backed pure logical conditions

A complete three-iteration C recurrence now combines checked multiplication,
shifts, two automatic unsigned locals, a loop, a branch selected by C logical
`&&`/`||`, state transfers, and a final output expression. The initial pinned
Clang-to-guest attempt refused the first declaration because the closed
constant-flow projection admitted only one masked unsigned comparison.

The evaluator now consumes a bounded tree of source-ordered `i32` logical
operations over exact source-proven unsigned masked comparisons. It checks
both operands and both assignment arms, including parentheses, canonical
Clang ancestry, types, symbol references, spans and absence of effects.
Both operands are checked before logical selection: this is sound for the
admitted pure, defined subexpressions, but rejects some otherwise-defined
short-circuit C programs whose unexecuted right operand is unsupported.

The source fixture `local_logical_recurrence_output.c` evaluates an AND
condition through three iterations, selecting false, true and false arms.
An OR variant selects false, true and true; a nested AND/OR variant tests
source parenthesization and mixed precedence. An independently calculated
state trace supplies a different final XOR constant to each variant so the
normative Malbolge guest must emit the same byte `0x41` under empty and
nonempty input. Side-effecting increments and calls in a logical operand,
plus unsupported logical-to-bitwise mutations, must refuse before artifact
publication.

No runtime Malbolge Boolean evaluation, general short-circuit effects, dynamic
state or arbitrary byte-stream synthesis is claimed. The original twelve-byte
Fibonacci program still fails closed at guest layout; P0 remains pending.

### Source-backed pure logical negation

A further complete three-iteration C recurrence uses local state, checked
multiplication and shifts, a nested logical predicate inside a loop, both
conditional assignment arms, and an expression-derived final `putchar`. The
first pinned-Clang compiler attempt refused at the first declaration because
the closed Boolean evaluator did not handle the source-proven unary `!` node.
The revised evaluator consumes an `i32` `!` over a fully proven pure predicate,
requires exact Clang parentage and typed expression spans, and reuses the
existing closed unsigned-comparison and `&&`/`||` rules. Both operands of every
logical binary subtree are checked, even if C would short-circuit one.

The tracked source `local_negated_logical_recurrence_output.c` produces the
independently calculated branch trace false/true/true. Double-negation and
nested-negation variants prove other branch traces through the full pinned
pipeline. The resulting actual Malbolge capsules each emit `0x41` in 31
normative VM steps for both empty and nonempty stdin. Source mutations that
introduce an increment, an impure call or bitwise complement fail before
guest publication; separately corrupted unary AST operation, type, parent or
kind metadata are rejected by the canonical adapter. The end-to-end and
adversarial regressions live in `tests/test_compound_c_pipeline.py`.

This is source-backed **compile-time** C constant evaluation, not runtime
Malbolge Boolean execution or short-circuit side effects. The original twelve-
byte Fibonacci stream remains blocked at guest layout, so P0 remains open.

### Computed unsigned operands in source-proven comparisons

A full three-iteration C recurrence now compares **two independently computed
unsigned expressions** within its loop's branch. The condition combines
masked local values on the left with an XOR and addition derived from a second
local on the right. The first pinned C-to-guest run refused the declaration:
the closed Boolean evaluator only admitted one parenthesized masked expression
compared against a byte literal.

The evaluator now proves each complete `u32` comparison operand through the
existing bounded, source-ordered expression walker. It requires exact Clang
parentage and operand spans before computing the `i32` Boolean comparison
result from the two unsigned values. For `>=`, the independent
three-iteration oracle selects true/false/false; for `<`, it selects
false/true/true.

Both complete C variants reach actual Malbolge execution, emitting `0x41`
with empty and nonempty stdin. Side-effecting increments,
a zero-divisor expression, and an unsupported logical-operand mutation refuse
without publication. Forged right-hand AST kind, type and parent also reject.

The checked-in source and regressions are
`local_computed_condition_recurrence_output.c` and
`test_computed_unsigned_comparison_*` in
`tests/test_compound_c_pipeline.py`. This is pure compile-time C folding, not
guest runtime arithmetic, branches or control-flow execution. The original
twelve-byte Fibonacci trace still lacks a positional guest layout witness;
P0 remains pending.

### Source-backed conditional expressions inside unsigned recurrences

A complete three-iteration C recurrence now uses the source-proven
`condition ? then : else` expression to select an unsigned local's next
value inside a loop. The initial pinned Clang-to-guest attempt refused at
the first declaration, because the closed `u32` expression walker did not
admit the `conditional-expression` node. The repaired adapter requires an
exactly typed `u32` result, a fully proven pure `i32` condition, two complete
checked unsigned alternatives and their exact source-ordered Clang spans.
It proves **both** alternatives even though C executes only the selected
one; an unselected side effect or undefined operation is conservatively
rejected, not silently dropped.

The checked-in source `local_conditional_expression_recurrence_output.c`
visits unsigned `next` values `60, 160, 128` and selects the true, false,
false alternatives. The separately computed final state is `a = 127` and
`a ^ 62 = 65`. The complete pinned compiler emits a real current-profile
Malbolge capsule; the normative VM outputs `0x41` under both empty and
nonempty input. Negative source variations with increment side effects,
zero division or unproven conversions refuse without an artifact; forged
conditional node/arm operation, kind, parent or type metadata also reject.
The complete acceptance and mutation regressions live in
`tests/test_compound_c_pipeline.py`.

This is bounded source-constant folding, **not** guest runtime selection,
C control flow or arbitrary byte-stream synthesis. The original twelve-byte
Fibonacci output remains blocked by positional guest layout; P0 is open.

### Verified zero-prefixed guest output before data relocation

A complete four-iteration C recurrence with automatic unsigned state, a
masked Fibonacci update, source-proven `if/else`, pure `?:` expressions, and
four `putchar` effects initially reached the quad layout publisher but
failed at `distinct-literal quad geometry disagrees`. Its independently
computed output is `00 54 b2 3f`; no guest artifact was published.

The bounded state-space proposer now considers one or more real initial-zero
output instructions before the data-pointer relocation. Its source-independent
preview counts those bytes rather than silently omitting them, and still
models all subsequent `p`/`*` writes on loader-expanded guest memory.
The independent quad publisher now re-decodes these prefix effects and
permits an output, no-op, or arithmetic instruction before the final halt.
It still requires exactly four outputs, a single early relocation, at least
one guest arithmetic write, distinct out-of-source data writes, exact
positional source admission, and normative VM replay with both empty and
nonempty input. The maximum prefix, source length, and write count remain
bounded; no unverified byte stream is accepted.

The tracked `local_zero_prefix_conditional_stream.c` program now compiles
through the pinned Clang/JSON/typed/ternary/layout pipeline, and the real
guest emits `00 54 b2 3f` under both input cases. A side-effecting C
comparison mutation fails without publication. The source-independent
seeded-layout regression proves the actual first guest instruction outputs
zero before relocation; a forged preview must not authorize a source.
These are source-constant-folded C values with real guest output, not guest
runtime C arithmetic or general byte-stream synthesis. The original
12-byte Fibonacci acceptance remains unsupported, so P0 remains open.

### Maximum graphical relocation boundary

The bounded state-space quad search now considers source lengths through 126
cells, the maximum relocation operand representable by a graphical ASCII
code cell. In particular, the canonical `j` at source position eight has
encoded byte value 126. A source-independent four-output guest uses that
relocation and 126 source cells, crosses the 94-phase decoder wrap, and
performs real disjoint guest arithmetic writes. The pinned current-profile
VM independently emits `36 14 35 02`; the bounded proposer reconstructs
the program, and independent layout/VM admission accepts the reconstruction
while rejecting a forged final output byte. The verification tests preserve
the full-source length and at least four distinct guest writes.

An additional complete four-iteration C Fibonacci-style loop with unsigned
state, parity selection, nested conditional expressions and four `putchar`
effects was compiled through the pinned Clang/typed/ternary/layout pipeline.
Its independent recurrence oracle was `36 14 35 02`, and its actual capsule
emitted exactly those bytes with empty and nonempty input in 24 VM steps.
That C example chose a *shorter* accepted layout: it proves guest-output
parity, not that the longer search boundary was necessary for that source.
The unmodified original four-byte Fibonacci prefix `02 59 5f 08` still
exhausts the expanded bounded grammar without a verified guest. This
search-space expansion is not generalized byte-stream synthesis, dynamic
C state or runtime control flow; the P0 remains open.

### Source-proven unsigned bitwise complement in a stateful recurrence

A complete three-iteration C recurrence first refused its first declaration
when a conditional expression used `(~next) & 255U` in one branch. The closed
unsigned expression evaluator previously supported binary operators and pure
conditional values, but not unary `~`. It now proves the full Clang-backed
`u32` unary subtree, including operation, type, ancestry, exact operand span
and clean metadata. It computes the complement at the full 32-bit unsigned
width before narrowing with the source-proven mask; a bitwise complement is
not an eight-bit operation until the C expression explicitly makes it one.

The tracked `local_complement_recurrence_output.c` uses checked multiplication,
shifts, automatic state updates, a source-proven loop, both conditional arms,
and one final output. Its independent three-step oracle visits `60, 208, 192`
for `next`, takes true/false/false, ends at `a = 25`, and emits
`25 ^ 88 = 65` (`0x41`). A double-complement source variant checks nested
unary ancestry and unsigned width, visiting `60, 64, 0` and emitting
`1 ^ 64 = 65`.

Both reach actual normative Malbolge guest output under empty and nonempty
input. Side-effecting or undefined operands, signed complement, unsupported
unary minus and forged AST metadata reject without publishing a guest
artifact. Tests cover actual guest stdout and adapter refusal.

This implements **source-backed compile-time** C constant propagation only.
The guest runs the output instructions, not the C multiplication, branching or
bitwise operations. The original twelve-byte Fibonacci output still lacks an
independently verified general layout, so the P0 remains pending.

### Source-proven modulo-2^32 arithmetic in a four-byte C stream

The complete four-iteration source program
`local_wrapping_recurrence_stream.c` exposed another real semantic gap:
`unsigned` subtraction, multiplication, and addition were incorrectly
restricted to nonoverflowing intermediate values. The first pinned Clang
compilation refused the declaration and published no guest. C defines these
operations modulo 2^32 for the pinned `wasm32` unsigned-int target, even when
an intermediate is much larger than a byte. The multi-local expression
checker now proves the original `u32` operand tree, typed operator, Clang
ancestry and source order before applying `wrapping_sub`, `wrapping_mul` or
`wrapping_add`. It still narrows only on source-proven masks/stores and
refuses unsupported conversions, effects and undefined operations.

Each iteration reconstructs a Fibonacci state update using
`((0U - (a + b)) * 255U) & 255U`, then restores the same byte through
`((~next + 1U) + (next * 2U)) & 255U`. The unsigned subtraction wraps for
all four iterations; the product and final addition also exceed 2^32 - 1
before modulo reduction. A separately calculated 32-bit modular arithmetic
oracle yields the state sequence `2, 3, 5, 8` and source-selected output
`35 c0 09 e3`. The full pinned C/JSON/typed/ternary/layout pipeline produces
a real Malbolge capsule whose normative VM emits exactly those four bytes on
both empty and nonempty stdin. Division-by-zero, source increments, and a
signed complement mutation refuse without an artifact.

This is **compile-time** folding of a bounded, fully known C recurrence. It
does not implement runtime C integers or dynamic guest loops, and it does not
solve the original `02 59 5f 08` prefix or the twelve-byte Fibonacci layout.
The generalized byte-stream P0 remains pending.

### Source-proven unsigned zero/nonzero predicates

A complete three-iteration C recurrence with automatic unsigned state,
checked multiplication, left/right shifts, an `if/else` and final output
initially refused at the first declaration for `if ((next & 8U))`. The
pinned Clang AST reports an unsigned scalar expression as the condition,
not an `i32` comparison. The bounded constant-flow proof now consumes a
complete `u32` expression and selects the arm when its evaluated value is
nonzero, following C scalar truth semantics. The existing expression walker
checks Clang ancestry, exact types and spans, and pure defined arithmetic;
side effects and unsupported casts cannot be discarded.

For `next = ((a * b) << 2U) & 255U`, starting from `a=3`, `b=5`,
the independent recurrence visits `60`, `160`, `128`. Masked truth selects
then/else/else, producing final `a=127` and `127 ^ 62 = 65` (`0x41`).
The complete pinned C-to-Malbolge pipeline emitted this byte in 31 real
normative VM steps. The source test also covers direct unsigned-local
truthiness; mutated C side effects, zero division, signed casts and forged
Clang operator/type/ancestry/metadata must refuse without publication.

This is bounded **compile-time** condition selection over already known
unsigned values; it adds neither guest runtime branching nor a general
byte-stream layout. The original twelve-byte Fibonacci P0 remains open.

### Bounded source-backed `while` control flow

A complete C recurrence with automatic unsigned local state, multiplication,
shifts, a conditional with both arms, and a mutable loop counter was first
attempted through the pinned compiler and refused at its first declaration.
The closed JSON adapter now accepts a source-proven `while (condition) { ... }`
when the condition and every executed body effect are completely evaluable
from current local constants. Unlike the earlier fixed-bound `for` proof,
the `while` condition is re-evaluated **after each body execution** against
updated local state. The full canonical Clang subtree, exact source spans,
node ancestry, pure condition and body effects are checked on each replay.
Iteration-local declarations are discarded at the end of each execution.

The evaluator requires at least one executed iteration and an observed false
condition after at most twelve iterations. Zero-trip loops are conservatively
unsupported because the skipped body would not be proved. Infinite loops,
side-effecting or undefined conditions, nested loops and unrecognized effects
fail without publication. Loop evaluation is compile-time only; it does not
claim general C control flow or mutable Malbolge guest state.

`local_while_recurrence_output.c` visits the independent unsigned values
`60, 160, 128`, takes true/false/false branches and derives the final byte
`127 ^ 62 = 65`. The generated current-profile Malbolge capsule emits
`0x41` in 31 normative VM steps. A separate two-iteration `while`-converted
Fibonacci branch program emits two independently derived bytes `Q.` in eight
actual guest steps. The real VM, not the host C program, produces both output
traces. The original twelve-byte Fibonacci P0 still requires generalized
guest byte-stream layout and remains open.

### Bounded source-backed `do…while` control flow

A complete C recurrence with automatic unsigned state, multiplication,
shifts, a two-arm branch, and a mutable counter exposed another missing
control-flow boundary: `do { ... } while (condition);`. The pinned Clang
frontend already emits `do-statement` with the compound body **before** the
trailing condition; the JSON adapter initially refused the first local and
published no guest artifact. The closed evaluator now consumes that exact
node order and checks the whole loop body before the condition on each pass.
It replays both from the same Clang subtree, re-evaluates pure checked
predicates against updated state, and drops iteration-local declarations
before evaluating the trailing predicate. It requires a source-proven false
condition or selected checked break within twelve body executions; neither
nested loops nor unbounded, impure, undefined or unsupported effects are
admitted.

The independent three-iteration trace reaches `60, 160, 128`, takes the
true/false/false branches and produces `127 ^ 62 = 65` (`0x41`). A distinct
source variant starts with `i = 3U` so the test is already false **before**
the first body; C still executes one body and yields `(60 >> 3) ^ 1 = 6`,
then `6 ^ 71 = 65`. A two-iteration converted Fibonacci conditional stream
retains two real guest outputs `Q.`. Tests check actual normative VM stdout
against independent C arithmetic for empty and nonempty guest input.
Unsupported sources and malformed or unsupported AST structures must refuse
without a guest artifact. As elsewhere in the bounded frontend, normalized
Clang input is trusted evidence; its digest is not an independent proof that
an adversarially rewritten but still valid AST operator matches original C.

This is compile-time replay of a proven finite C program, not dynamic guest
control flow. The original twelve-byte Fibonacci P0 remains blocked by
generalized byte-stream layout.

### Source-proven `if` without `else` in bounded C recurrences

A complete three-iteration unsigned C recurrence with a `do…while` loop,
checked multiplication and shifting, mutable state and a conditional update
without an `else` first failed at the JSON adapter and published no guest.
The closed conditional proof formerly required two braced arms. It now admits
an exact source-backed single braced assignment only when that arm ends at
the `if` statement's own end and there are no unconsumed child nodes within
its span. It proves the assignment even when the condition is false, then
retains the prior local state for a skipped arm. A true condition commits the
source-proven assignment. Existing two-arm selection is unchanged.

The independent source oracle visits masked products `60, 160, 0`, takes the
first assignment and skips the remaining two, then derives `6 ^ 71 = 65`.
A second source variant checks an always-false mask and preserves `a = 3`,
so its final `3 ^ 66` also yields `0x41`. Both variants are checked against
actual output from the normative Malbolge VM on empty and nonempty input.
Extra assignments or outputs inside the sole arm, unbraced statements,
undefined division, out-of-budget loops and forged AST nodes are rejected
without publication.

This is bounded compile-time selection of C state, not guest runtime branching
or a general byte-stream emitter. The original twelve-byte Fibonacci layout
remains unsupported and P0 is still pending.

### Source-proven zero-trip `while` with discarded effects

A complete C program combining a `while` that is false at entry, a guarded
state update and `putchar` in that skipped body, and a subsequent three-step
`do…while` recurrence initially refused at the first local declaration. The
bounded evaluator now still proves the entire skipped body against shadow
local state, checks its branch and putchar AST, then discards all speculative
state and output effects. An executed `while` still reuses its previously
proven body and requires a source-proven false exit within twelve iterations.
The admitted zero-trip subset is deliberately conservative: undefined or
unsupported expressions in a skipped body still refuse compilation, even
though C would not evaluate those expressions at runtime.

The independent C oracle verifies that the first loop executes zero times;
the following three iterations visit `60, 160, 128` and derive `127 ^ 62 =
65`. A source variant swaps the unreachable branch selector so both shadow
branch outcomes are exercised. Both complete programs emit only `0x41` in the
normative Malbolge guest VM on empty and nonempty input, with no output from
the skipped `putchar`. Impure guards, unsupported skipped effects, undefined
expressions and tampered loop/body/guard/output AST reject without artifacts.
This proves a finite source-constant C control-flow slice, not runtime guest
state or a general guest byte-stream layout. The original twelve-byte
Fibonacci P0 remains open.

### Source-proven zero-trip `for` with discarded effects

A complete C recurrence also exposed the separate zero-iteration gate for
`for (unsigned j = 0U; j < 0U; ++j)`. Previously the bounded evaluator
required a positive literal bound and refused before the independently
computed final output. The source-backed proof now permits literal zero
provided the entire body can be checked against shadow local state. Every
speculative write and `putchar` effect is discarded, the loop-local counter
leaves scope, and subsequent real C statements see the unchanged outer state.
The existing positive-bound replay and twelve-iteration cap are preserved.

The full input program skips a guarded state update and putchar, then executes
three iterations of a source-proven `do…while` recurrence. The independent
oracle visits `60, 160, 128` and emits `127 ^ 62 = 65`; the current-profile
normative Malbolge VM emits only `0x41` for empty and nonempty input. Skipped
unsupported increments, undefined division, nested loops, foreign counters
and forged Clang AST nodes refuse without guest publication. As with the
zero-trip `while`, even unreachable unsupported C is conservatively refused.
This is compile-time bounded state projection, not dynamic guest C control
flow or a generalized byte-stream emitter; the original twelve-byte
Fibonacci target remains pending.

### Ordered multi-assignment C conditional arms

A complete three-iteration `do…while` C recurrence now exercises a branch that
updates two unsigned locals per arm before the next loop trip. The pinned
adapter previously refused the program's first declaration because its
source-constant conditional proof accepted only one assignment in each braced
arm. The repaired bounded proof consumes every ordered assignment from both
Clang-backed arms, checks its parent, span, symbol and unsigned expression,
then retains only the chosen state. An `if` without `else` keeps the original
state when skipped. A branch cannot hide an extra output, declaration, nested
statement or unsupported side effect, even in an unselected arm.

The independent C oracle for the two-arm program visits `60, 208, 192` with
branch choices true/false/false, finishes at `a = 191`, and derives output
`191 ^ 254 = 65`. The first complete pinned source probe emitted the real
normative guest byte `0x41` in 31 steps. The regression also covers the
false-first, single-arm taken and single-arm skipped state traces against
actual guest execution on empty and nonempty stdin; source and forged-AST
mutations reject without publishing guest artifacts. This finite projection
still executes C branching at compile time, not in the guest. General runtime
state and the original twelve-byte nonzero Fibonacci layout remain open.

### Source-proven mixed branch assignments and guest output effects

A complete two-trip C `while` recurrence now mutates a different automatic
unsigned local in each `if` arm, then calls `putchar` with a value derived
from the loop state. The previous adapter refused at the first declaration:
it could prove either branch-local assignments or branch-local output, but
not their source-ordered combination. The unified bounded arm walker now
proves every assignment and call in both brace-delimited arms against the
same incoming state. It snapshots the then-arm state and output effects,
restores the incoming state for the else-arm proof, and commits only the
selected state and selected guest outputs. Calls remain independently
source-checked, and an unselected arm cannot hide other effects.

The independent C oracle starts with `a = b = 1` and visits `next = 2, 3`.
The first arm updates `a` to 2 and emits `2 ^ 83 = 81` (`Q`); the second
updates `b` to 4 and emits `3 ^ 45 = 46` (`.`). The real pinned C-to-Malbolge
compiler and normative guest VM emit `51 2e` (`Q.`) on empty and nonempty
stdin; a one-trip variant and a two-trip `if` without `else` each emit
only `51`, proving that skipped calls do not leak. Source mutations involving
increments, division by zero, unsupported calls and nested branches, plus
forged Clang node ancestry, refuse without publishing guest artifacts. The
prior output-only conditional proof is subsumed by the same closed arm
traversal, not replaced by unchecked host output. C state and branching
remain compiler-time projections. General Malbolge byte-stream synthesis
and the original twelve-byte Fibonacci P0 acceptance remain pending.


### Source-proven nested conditional guest effects

A complete two-trip unsigned C `while` recurrence with `if` statements
inside both outer conditional arms initially refused at the JSON adapter.
A bounded arm walker now recursively proves nested, braced `if` statements
up to three levels, including both selected and unselected inner arms.
Every inner predicate, write and `putchar` must belong to the exact source-
backed Clang tree; an unselected branch is checked but cannot leak its
state or output. Branch-local effects replay in source order.

The independent oracle starts at `a = b = 1`: the first trip sets `a = 2`
and emits `2 ^ 83 = 81` (`Q`); the second sets `b = 4` and emits
`3 ^ 45 = 46` (`.`). The full pinned C compiler emits actual Malbolge
whose normative VM produces `51 2e` in eight steps, including an empty
input witness. Regressions cover both guest input cases, skipped outer
`else`, inner `if` without `else`, unsupported source effects and forged
nested AST ancestry. Previously negative tests for valid nested branches
were revised to test genuinely unsupported unbraced forms instead.

This remains compiler-time bounded C replay, not dynamic guest branching.
The original twelve-byte Fibonacci layout remains unsupported and P0 is
still pending.

### Bounded zero-prefixed six-byte guest stream

A complete C source with three automatic `unsigned` locals and a two-trip
`while` loop emits three `putchar` effects in each selected `if` arm. The
first arm writes new local values after its three outputs; the second arm
observes those values and emits three more. The independent C oracle is
`00 51 22 1b 37 39` (NUL, `Q`, quote, ESC, `7`, `9`). The old six-effect
pipeline first refused a non-fixed trace at the typed adapter even though
the standalone guest encoder could execute the corresponding positional
Malbolge program.

The six-effect typed projection now reuses the checked generic source-distinct
SSA proof used for shorter streams, without relaxing type, symbol or output
order checks. The previously fixed six-byte bridge retains its exact 15-step
witness, while zero-first candidates use the bounded state-space proposal
solver. Both paths independently re-admit the layout and execute the
normative profile VM on unused empty and nonempty input. The complete C
program produces exactly six bytes in 23 guest steps, with five real
relocated data writes and no input consumption. A source mutation adding a
selected branch output rejects without artifact publication; forged SSA uses
and nonzero unwitnessed prefixes also reject. The six-byte sequence is not
generated by a host stdout callback.

This proves only closed compile-time local-state and branch replay followed by
six physical guest outputs. It does not lower general runtime C control flow
or arbitrary byte streams, and the original nonzero twelve-byte Fibonacci
P0 acceptance target remains unsupported by the bounded layout grammar.

### Nonzero-leading, source-proven six-effect stream

The existing six-effect search rejected any nonhistorical stream beginning
with a nonzero byte, even when its positional guest arithmetic grammar could
reconstruct the exact target. A red-first standalone VM experiment used a
source-independent six-write guest to derive `35 36 35 00 50 1b` (ASCII
`535`, NUL, `P`, ESC). The bridge first rejected its complete source-distinct
SSA projection; removing only the zero-first restriction permitted the
bounded state-space solver to reproduce the guest sequence. Its output and
real out-of-source data writes are independently decoded and VM-verified.

A second full pinned C experiment uses a two-trip `while` loop, branching and
state transfers between three automatic unsigned locals. It emits the first
three source-backed values `53, 54, 53`, updates them to `0, 80, 27`, and
emits the latter three on the next branch. The source-derived reference is
therefore exactly `35 36 35 00 50 1b`, without a host output substitute.
The final publisher no longer demands a leading zero or literal fixture
identity: it still independently reopens the admitted graphical source and
checks normative VM termination, complete bytes and no input consumption on
empty and nonempty input. The result is an actual 19-step Malbolge guest.
An extra selected C output effect is rejected without publication.

This is a new output-identity boundary (nonzero first byte, repeated byte and
interior NUL), not a new byte-count milestone. Compilation still folds C
control flow into checked constants; the guest executes physical arithmetic
and output, not general C storage, branching or loops. The full twelve-byte
Fibonacci acceptance target still fails at the layout witness boundary and
P0 remains pending.

### Source-independent twelve-byte positional search

A complete twelve-call C output experiment demonstrated that its typed
SSA values were valid, but the bridge and publisher accepted only the
historical twelve-byte fixture. A direct attempt to use the larger
state-space solver for the original Fibonacci trace exceeded a 75-second
bound without a guest witness. Search exhaustion is not impossibility.

The new finite twelve-effect search examines at most 94 relocation phases
with one real `p` or `*` arithmetic write immediately before each output.
It prunes partial paths as soon as their accumulator byte differs from
the source-proven expectation. The cached loader tail proposes candidates
only; the existing independent layout admission checks disjoint writes
outside source, and the normative VM checks exact output, termination and
no consumed input on both empty and nonempty stdin before publication.

An independently encoded guest using eleven `p` writes and one `*` write
at output six emits `51 37 34 38 50 8b cf b9 b2 ba ce 9d` in 27 steps.
The pinned Clang C-to-Malbolge pipeline emits that same binary stream
from twelve source-backed `putchar` calls. An extra output effect refuses
without an artifact; the historical 27-step twelve-byte guest remains
unchanged. The original twelve-byte Fibonacci trace remains unsupported
by this bounded search, and P0 is still open. This is a compiler-time
constant byte stream, not dynamic guest execution of C state or branches.

### Interleaved repeated-output guest layout

A nonfixture twelve-effect literal C program initially passed Clang-backed
source admission but refused at `Layout(UnsupportedEffectTrace)`. The stream
`3e 09 0d 0d 28 2e 13 3d 0a 2e 0a 3d` requires a repeated guest output
without another arithmetic write, plus mixed `p` and `*` instructions. A
source-independent 34-instruction seed was independently decoded and run in
the normative VM, then reconstructed by a bounded accumulator-state beam.
The beam preserves one deterministic representative per progress/low-byte
class; this is a proposal heuristic, not a proof of high-word equivalence.
A short (at most 36-cell, at most 12-prefix) search now supplements the
straight-write twelve-byte grammar; every proposal must pass full positional
admission, disjoint-write checks and VM replays before publication.

The complete C-to-Malbolge pipeline emits that exact binary stream in 34
real guest steps under empty and nonempty stdin. An extra selected C output
refuses without an artifact. The original Fibonacci stream
`02 59 5f 08 57 4f 22 6d 03 90 b3 23` still lacks a guest witness,
and neither dynamic C state nor general byte-stream synthesis is implemented.

### Exact capacity pruning for bounded guest search

The interleaved twelve-byte search originally spent significant time on
geometries that could not possibly emit their requested byte effects. Every
source-backed output needs one physical guest `<` instruction, and every
change from the prior accumulator low byte (initially zero) needs at least
one real `p` or `*` instruction. Repeated bytes can share an accumulator
value. These are **necessary** instruction-count bounds, not full synthesis
or a replacement for verification.

For longer traces (at least eight effects), the search now rejects an
impossible source length, relocation prefix, or partial accumulator state
when its remaining body has too few cells for the
unemitted output effects **plus** their unavoidable byte transitions.
Initial zero outputs before relocation count toward the prefix rather than
body; a final output suffix is handled separately. The current terminal
output proposal pads completed body effects only with no-ops, so two final
unequal bytes cannot use that shape. The valid 34-cell interleaved guest has
an eight-cell prefix and precisely 23 body cells for twelve outputs and
eleven byte changes. The following prefix would leave only 22 cells and is
provably impossible within this layout grammar. Shorter streams retain
existing deterministic witness-selection order.

The proposal beam still discards high-word alternatives, and its finite
length, prefix and geometry budgets can miss valid guests. Every accepted
candidate is independently positionally decoded, checked for disjoint
source-external writes, and replayed on the normative VM under empty and
nonempty input. The original twelve-byte Fibonacci target remains open;
no guest runtime implementation of general C state or control flow follows
from this pruning.

### Preserving bounded high-word guest continuations

Reattempting the complete twelve-iteration Fibonacci C program after exact
capacity pruning still reached typed source admission but refused at
`Layout(UnsupportedEffectTrace)`. The long-stream search had a separate
false-negative mechanism: it retained only the smallest fifteen-trit
accumulator word for each `(emitted effects, low output byte)` group, although
`p` uses the full word when computing the next accumulator. A red-first
successor regression shows that words 3 and 259 both emit byte 3 but a
subsequent crazy operation with data word zero yields bytes 50 and 53,
respectively. Discarding 259 loses the latter valid continuation.

For traces of at least eight effects, the proposal beam now retains the
smallest and largest **full accumulator words** per output-progress/low-byte
group. It still enforces finite source, state and work budgets. An additional
red-first test showed that the search previously recorded discarded
predecessors as permanent reconstruction steps (46 records for 16 surviving
successors). It now materializes only the retained predecessor steps,
keeping history growth aligned with live search paths. Shorter traces keep
their established deterministic search behavior.

The known twelve-byte interleaved source-independent witness remains
independently decoded and replayed in the normative guest VM; the complete
Clang-to-Malbolge C regression still emits its exact 34-step binary stream
on empty and nonempty input. The original Fibonacci stream still has no
admitted guest layout. Keeping two extreme words does not prove equivalence
of discarded middle states, and neither static C replay nor this heuristic
search implements arbitrary guest runtime arithmetic or control flow.

### One-step byte-reachable high-word retention

A further red-first successor experiment found that retaining only minimum
and maximum full accumulator words still loses a valid continuation. The
three words 3, 259 and 515 all emit byte 3, but with the *next* data word
zero their subsequent `p` outputs are 50, 53 and 38. Only the discarded
middle word 259 can produce the next requested byte 53 in one write.

For streams of at least eight effects, the bounded proposal now retains
both full-word extremes **and** up to two extremes among states whose next
crazy operation reaches the pending byte. It reads the next guest data word
from the actual relocation/loader-tail geometry, rather than using the
current word or a fabricated constant. A changed next word of 2 gives 55
instead of 53 and must not retain the false continuation. At most four
representatives survive per output-progress/low-byte group, and only
surviving predecessors enter the reconstruction history.

The red-first middle-word regression, next-word negative control, and the
independently decoded twelve-byte interleaved guest pass. The full pinned
Fibonacci C source still refuses at the guest-layout boundary with no
artifact. One-step reachability is only a deterministic beam priority;
longer-term alternative word states, runtime C state, and arbitrary stream
synthesis remain unimplemented. All published layouts still require exact
independent decoder, disjoint-write and normative-VM verification.


### Two-step byte-reachable high-word retention

The complete twelve-iteration Fibonacci program was retried after the
one-step search improvement and still refused at the verified guest-layout
boundary without publication. A separate red-first successor regression
exposed another deterministic beam false negative. Accumulator words 3,
259 and 515 all emit byte 3.

With the next loader word 2, the first `p` opportunity cannot emit the
pending byte 53 from word 259: it yields 55. Yet a guest no-op advances
the data pointer to the following loader word 0, where `p(0, 259)` yields
exactly 53. The minimum and maximum full words yield 50 and 38 there,
so the old beam lost the middle word.

For streams of at least eight effects, the proposal now inspects two
actual consecutive loader-tail words after each successor. Alongside
full-word extremes and immediate-byte-reachable extremes, it retains up
to two additional representatives that can match after one no-op then
one crazy write. This delayed match is considered only when at least
three body instructions remain for the no-op, write and output.

A negative control changes the later word to 2, for which 259 no longer
matches 53; the older immediate-word negative control also excludes a
delayed match. At most six representatives survive per progress/low-byte
group, and discarded candidates consume no reconstruction records.

The independent twelve-byte interleaved search and complete pinned C
pipeline continue to produce actual normatively verified Malbolge on
empty and nonempty input, while the original Fibonacci twelve-byte
stream still refuses at layout. This bounded two-step prioritization is
not a complete beam, arbitrary guest byte-stream synthesis, or runtime
C arithmetic and control flow. Every accepted candidate remains subject
to the existing decoder, disjoint-write and normative VM checks.

### Two-consecutive-write byte reachability

The complete twelve-iteration Fibonacci C program remains source/typed
admitted, but its original `02 59 5f 08 57 4f 22 6d 03 90 b3 23` trace
still has no verified guest layout. A red-first search regression exposed
another false-negative beam equivalence: full words 3, 259 and 515 all
emit byte 3, but only the middle word 259 reaches byte 255 after two
successive real crazy writes with loader words 2 and 0. The first write
produces low byte 55; the second produces 255. The extreme words yield
3 and 14, and neither a single write nor a no-op followed by a write
reaches 255 from the middle word.

The bounded long-stream proposal now retains minimum and maximum full
words reaching the pending output byte by this two-write sequence, in
addition to its existing full-word, immediate-write, and delayed-write
representatives. It reads both actual future loader-tail cells, requires
at least three remaining body instructions for the two writes and output,
and caps retained representatives at eight per progress/low-byte group.
Changing the later loader word from 0 to 2 removes the middle match in
an explicit negative control. Discarded proposals still consume no
reconstruction history.

This is a deterministic pruning improvement, not an arbitrary-stream
solver. The independently decoded and VM-replayed twelve-output
interleaved guest remains accepted; the original Fibonacci trace still
fails closed at layout. Longer write sequences and alternative guest
control flow may require a different search grammar. No proposal is
published without positional, write-disjointness, and normative VM proof.

### Bounded multi-step guest-byte continuation

The original complete Fibonacci C program still reaches typed byte effects but
has no accepted guest layout. A red-first successor experiment then exposed a
more general loss in the long-stream accumulator beam: words 3, 259 and 515
share output byte 3, but with subsequent loader words 1, 2, 2 only word 259
can reach byte 54 within three physical `p` instructions. The prior beam kept
only extrema and fixed immediate, delayed and two-write patterns, so it
discarded that valid middle-word continuation.

The proposal search now looks ahead through up to three **actual** future
loader words, considering `p` and no-op at each position. A rotation erases
prior accumulator identity, so it cannot distinguish grouped full words. For
each pending-byte class the beam keeps full-word extrema plus up to two
representatives for each shortest matching lookahead distance. The output
instruction consumes a further cell; insufficient remaining capacity prevents
false retention. This replaces the separate short-pattern selectors without
increasing the maximum eight retained words per progress/low-byte class.

The red-first three-write path, changed-third-word negative control and
instruction-capacity limit now pass. All sixteen focused bridge search tests,
independent twelve-byte interleaved guest reconstruction, and full pinned C
interleaved guest/VM parity pass. The original twelve-byte Fibonacci program
still refuses with `Layout(UnsupportedEffectTrace)` and no guest artifact.
The beam remains a bounded proposal heuristic: a valid fourth-step path or a
non-extremal full word may still be missed. The independent layout decoder and
normative empty/nonempty-input VM replay remain mandatory for every publication.

### Alternate short-stream terminal seeds

A twelve-output source-independent guest exposed a distinct layout false
negative: the short-stream search modeled only a no-op immediately before
halt. The actual loader derives its expanded memory from the final two
source cells, so replacing that no-op with a genuine `p` or `*` changes
all earlier relocated data words. This is not merely a harmless terminal
padding choice. A red-first complete guest trace ending in `p` reproduced
the omission even though the independent positional encoder and normative
VM admitted its 34-instruction source.

The bounded short-stream search now tries no-op and crazy terminal
shapes, retaining the previous no-op-first choice and the same 36-cell,
12-prefix geometry bounds. Every proposed variant remains subject to
independent positional decoding, source-disjoint write checks and empty/
nonempty-input normative VM replay. A changed-tail control checks that
the original byte trace cannot simply borrow the no-op loader seed.

This closes one source-seed false negative, not general byte-stream
synthesis. The complete original Fibonacci source still lacks an admitted
guest layout; no dynamic guest C loop, arithmetic or branching is inferred
from a source-proven static byte projection. P0 remains pending.

### Rotating short-stream terminal seed

A complete 36-instruction guest, including a bounded interleaving of real
crazy/rotation writes and twelve outputs, exposed another loader-tail
false negative. Its initial relocation and output source decode correctly,
and both empty-input and nonempty-input normative VM executions yield
`88 b0 85 b6 8b bc b6 88 b0 88 c8 88`. The final source instruction
before halt is a rotation (`*`), not a no-op or crazy write. Because the
loader derives its expanded data words from those source cells, neither
of the two previously searched terminal seeds reconstructs this stream
within the 36-cell, 12-prefix short-search bound.

The red-first test first confirmed that the complete source passes the
independent positional and VM checks while the short-search entrypoint
returns no layout. Adding the rotation seed admits a verified proposal
under the same geometric bounds and acceptance checks. A changed expected
byte is rejected against the independently reconstructed source. The full
original Fibonacci C program still refuses at guest layout without
publishing an artifact; this is one real guest search capability, not
runtime C control flow or arbitrary byte-stream synthesis.

### Changed-byte output at the final source instruction

Retrying the original twelve-iteration Fibonacci program still reached the
source-proven twelve-byte effects but refused at guest layout, without an
artifact. A separate red-first, source-independent guest exposed a false
negative in the terminal search: the final body instruction can be a real
crazy-data write, immediately followed by an output instruction and halt.
The preceding output and that terminal output need not have equal bytes.
The search had discarded this entire terminal shape for traces of at least
eight effects, and the production 36-cell short search never considered an
output opcode as the final loader-source seed.

A complete 34-instruction guest with twelve real crazy-data writes and twelve
output instructions produces `59 3f 2c 48 50 1b 59 3f 2c 48 50 1b`. Its
independent positional source encoding, disjoint data writes and normative
VM replay were established before the search fix. The direct terminal search
and the bounded production short search now both reconstruct a verified
layout. The search retains its 36-cell and twelve-prefix bounds, preserves
existing seed precedence and never authorizes publication from cached loader
memory or predicted output bytes alone.

This removes a structural false-negative assumption, not the need for a
witness for any particular C output trace. The original Fibonacci output
`02 59 5f 08 57 4f 22 6d 03 90 b3 23` still lacks an admitted layout;
no guest runtime C arithmetic or dynamic branching is established. A separate
C probe with nested conditional expressions and a loop failed at frontend
admission and produced no guest, so it supplies no additional C coverage.

### Terminal data-pointer relocation seed

The original complete twelve-iteration Fibonacci C program was retried and
still refused at verified guest layout without publishing source. A red-first,
source-independent 35-instruction guest then exposed an additional false
negative in the layout/search boundary. Its 12 real crazy-data writes emit
`3f 0a 2b 14 35 00 3f 0a 2b 14 35 00` in the normative VM, followed by
a second `j` immediately before halt. The previous layout validator rejected
all second data-pointer relocations, even this output-neutral final move.
The final `j` also changes the last loader source seed, which the bounded
output-stream search had not considered.

At that stage, the linear checker admitted **only** a second `j` as the
penultimate source instruction. It reconstructed the unwritten expanded
loader operand from the original final source bytes and proved D's exact
profile-width wraparound. At that stage nonterminal second relocations and
all third relocations rejected; source-aliased arithmetic also rejected.
The bridge preview models the terminal move only, and the source search
tries the new
seed after the established earlier choices. Actual positional encoding,
disjoint-write checks and both empty/nonempty-input normative VM executions
remain mandatory for admission. The independent 35-step guest and the bounded
production search now pass their original red-first regression.

This establishes a narrowly safe extra guest loader seed, not general
relocation or arbitrary byte-stream synthesis. The original Fibonacci
`02 59 5f 08 57 4f 22 6d 03 90 b3 23` still lacks a verified layout,
and runtime C arithmetic and dynamic control flow remain out of scope.

### Sparse guest search frontiers remain exact

A red-first search regression exposed an avoidable loss beyond the beam's
three-loader-word lookahead. Three full accumulator words (`3`, `259`,
`515`) all emit byte `3`. Following an output, a future source data-word
sequence `0, 0, 0, 2` lets the middle word reach byte `1` through guest
crazy operations and no-op strides, but only at the fourth future word.
The previous unconditional min/max and short-lookahead pruning discarded
word `259` even though the frontier had only a few states and therefore
needed no heuristic reduction. This was a genuine proposal false negative,
not a verifier rejection or an unsound guest program.

Search now retains every distinct `(emitted output count, exact accumulator)`
state when its candidate frontier fits the existing 16,384-state cap.
Only an over-budget frontier invokes the existing bounded high-word beam.
A separate dense-frontier test proves that the budget and history-record
limits remain active. A changed fourth guest word cannot produce the same
byte from the retained middle state. The underlying crazy operations and
output matching use the canonical profile helpers; no new source encoding
or bypass of positional decoding, data-write disjointness or normative VM
replay is authorized by this proposal change.

The original source-backed twelve-iteration Fibonacci program still reaches
typed and ternary admission but refuses at guest layout without publishing
a source artifact. The 36-cell short-stream geometry remains bounded; this
search correctness fix does not establish an arbitrary byte-stream backend,
runtime guest C arithmetic, state or dynamic control flow. P0 stays open.

### Leading-zero guest outputs before relocation

The complete twelve-iteration Fibonacci C program was rerun and still refused
at verified guest layout without publishing an artifact. An independent
11-instruction guest exposed a separate bounded-search false negative: seven
real zero-byte outputs can occur **before** the single data-pointer relocation,
followed by a crazy write and a final nonzero output immediately before halt.
The canonical source encoding and normative VM agree on all eight output
instructions with no input consumed, but the old search started at `N + 4`
source cells and limited relocation prefixes to `length - (N + 3)`.
Both exclusions are invalid when initial output effects occupy prefix cells.

For streams of at least eight effects, the search now starts at the necessary
instruction lower bound and permits the longest prefix with at least one body
instruction. Existing per-geometry body-capacity checks still subtract
source-encoded zero outputs, and every accepted candidate passes independent
positional decoding, disjoint-write checks and normative empty/nonempty-input
VM replay. The red-first eleven-cell source now reconstructs an independently
admitted guest; a forged final byte still rejects. This broadens one valid
source geometry, not runtime guest C state or unbounded synthesis. The
original Fibonacci stream remains unsupported and P0 stays open.

### Dense beam lookahead across repeated effects

The original twelve-iteration Fibonacci C source was rerun and still reached
layout admission without a verified guest witness or published artifact. A
red-first dense-frontier regression then exposed another general proposal
false negative: distinct full accumulator words can have the same low byte
`3`, so the next output may repeat `3` without changing state. The previous
beam skipped future-word reachability whenever that immediate expected byte
already matched, discarding accumulator `259` before a later changed output.
For the actual next loader word `0`, a subsequent crazy write from `259`
produces byte `53`; changing the word to `2` removes that short continuation.

The over-budget beam now looks for the next **different** pending output
byte, including beyond repeated output effects, before choosing reachable
full-word representatives. A red-first regression checks retention, the real
repeated-output/crazy/output continuation, the changed-loader-word negative,
and the 16,384-state budget. Below that budget the complete exact frontier
remains unchanged. The lookahead remains a bounded search heuristic: candidate
source publication still requires independent positional decoding, disjoint
guest data writes and normative VM replay under two inputs. This fixes one
pruning false negative, not the full Fibonacci layout or runtime C state.

### Wider bounded source geometry for twelve-byte streams

The complete original Fibonacci C program still reaches the guest layout
stage without a verified twelve-byte source and refuses without publication.
A separate source-independent thirty-nine-instruction guest demonstrated an
avoidable 36-cell search boundary: eight initial no-ops, one relocation,
twelve crazy/rotate data writes separated by five no-op data strides, twelve
real output instructions and a final halt. Its VM output is
`b5 4f 42 3d 33 08 50 23 b4 4d 5d 31` under empty and nonempty input.
The original positional source independently passes disjoint-write and
normative-VM verification, while the previous short search returned no guest.

A separate, effort-capped fallback now searches 37 through 39 source cells
with an output instruction immediately before halt, at most eight prefix
cells and a 2,048-step history stop threshold per geometry. It tries longer
sources and prefixes first to reach a viable witness without traversing
all earlier high-cost geometries. The established 36-cell search retains its
original order and 700,000-step cap; the wider path never overrides its
witnesses. The 39-cell guest is reconstructed and independently re-admitted,
and the pinned C frontend can emit these same twelve source-proven bytes as a
real guest capsule. A forged expected output fails the original guest proof
and an extra thirteenth source output refuses without artifact publication.

This is a finite additional verified source geometry, not arbitrary stream
synthesis, guest runtime arithmetic or completed P0 acceptance. The exact
Fibonacci stream `02 59 5f 08 57 4f 22 6d 03 90 b3 23` remains unsupported.

### Wider source layout with an arithmetic loader tail

The original twelve-iteration Fibonacci C source still reaches layout and
refuses to publish an unwitnessed guest. A source-independent 39-instruction
Malbolge program exposed a separate missed layout: an eight-cell prefix,
relocation, twelve crazy/rotate writes and their outputs, four interleaved
no-op strides, and a **final crazy write before halt**. The final write
changes the loader expansion seed without adding a thirteenth output. Its
normative guest bytes under empty and nonempty input are
`a1 11 2c 0b 28 10 2d 0a a1 ff a3 ff`. The previous 36-cell search and
the 37-to-39-cell **output-terminal-only** fallback both missed that guest.

The wider fallback now considers the crazy-terminal source seed after its
established output-terminal priority, retaining the 37-to-39-cell geometry,
eight-prefix limit and 2,048-history-step cap per geometry. A red-first
source-independent regression proves the source's positional encoding, exact
VM output and disjoint guest data writes; the recovered guest is again
independently decoded and replayed before admission. A forged first output
byte fails verification. This does not establish an arbitrary output stream,
source-level C loop support, guest runtime state or the original Fibonacci
acceptance; P0 remains open.

### Longer rotated loader tail admits a verified twelve-byte stream

An attempted full twelve-iteration Fibonacci C compilation still reaches the
bounded guest layout search and refuses without an artifact. The same search
had a concrete additional false negative: a 39-instruction relocated program
with twelve separate guest outputs, twelve interleaved crazy/rotate writes,
four data-pointer no-op strides and a final output-neutral **rotation** before
halt. The exact normative guest output is
`b1 8a b7 88 b1 8a b4 88 b0 88 b3 82`, with no consumed input. The
existing 36-cell search and the wider output/crazy-tail fallbacks could not
reconstruct it, even though independent positional encoding and normative VM
execution under empty and nonempty inputs proved the complete program.

A red-first test now exercises the missed trace. The 37-to-39-cell fallback
searches the distinct rotated loader seed after its established output and
crazy priorities, with the same eight-prefix and 2,048-history-step caps per
geometry. The recovered source is independently re-decoded and replayed, its
thirteen disjoint writes remain outside the source, and a forged expected
first byte is rejected. The added fallback has observable search cost, so it
is restricted to twelve-effect searches only. This is not a general source C
runtime or a witness for the original Fibonacci outputs; P0 stays open.

- A red-first 39-instruction relocated guest with twelve arithmetic-derived
  outputs and a final output-neutral no-op exposed a missing long-tail loader
  seed. Its normative VM output is `a3 10 30 10 2a 11 2c 11 a2 01 a6 fc`.
  The public 37-to-39-cell fallback previously searched output, crazy and
  rotate terminals but not no-op, and rejected this independently proven
  stream. Adding the no-op seed after the existing priorities recovers the
  full guest with unchanged eight-prefix and 2,048-history caps. Independent
  positional admission, both-input VM replay, forged-output refusal and a
  pinned C-to-Malbolge source with twelve ordered `putchar` effects pass.
  The original conditional Fibonacci C source still fails closed at layout;
  this is bounded guest synthesis, not general runtime C state or P0 closure.

### Live second relocation as a new guest layout capability

A full retry of the twelve-iteration Fibonacci C source still fails safely at
its original unsupported guest output stream; no capsule is published. A
source-independent 13-step real Malbolge program instead exposed a different
layout limitation: after `j`, a second `j` can read a fresh expanded-loader
word, relocate D again, execute a real crazy-data write and emit a byte
before halt. The old linear validator refused this valid sequence solely
because the second `j` was not penultimate. A separate 15-step guest proves
that a live second `j` between two arithmetic/output pairs changes the
actual D path and emits `36 08`, without consuming supplied input. The
unrelocated comparison happens to emit the same two bytes; the proven
semantic difference is the guest's data address, not its output value.

The corrected layout checker permits **at most two** relocations, derives
the fresh operand from the original graphical source's loader-tail recurrence,
refuses operands already written by the guest, and checks source-disjoint
writes and exact profile-memory D-pointer wraparound after either move.
The raw independently encoded guests now match every admitted code,
encryption, D and data-write position during traced normative execution.
A replaced second-j opcode and a third relocation still reject. This
advances address-sensitive guest layout, not the byte-stream proposal search:
the C-to-guest publisher does not yet synthesize this nonterminal shape,
and the original Fibonacci output oracle remains unsupported. P0 stays open.

### Source-bounded repeated relocation with loader checkpoints

The unchanged full twelve-iteration Fibonacci C program remains a guest-layout
refusal, not an emitted guest program. A separate red-first, source-independent
18-step Malbolge experiment instead executes three live `j` operations,
interleaved with crazy/rotate writes and three actual guest byte outputs. The
previous layout checker rejected the graphical program solely because it
permitted no more than two relocations. Both historical and current normative
VMs execute the raw independently reconstructed source; the repaired layout
encoder now emits those identical graphical bytes and matches every traced
code, data-pointer, encryption and write address. A second triple-`j` guest
reads a later operand thousands or millions of words past source and changes
D again; its independent VM trace agrees under both profiles.

The linear admission proof now checks each relocation independently: a later
`j` must read an exact source-shadow or untouched expanded-loader word, and
all following arithmetic
writes must remain disjoint from graphical source, with exact D wraparound.
Sparse 1024-word recurrence checkpoints amortize distant, repeated and
backward operand queries without storing full VM memory. A forged `j` opcode
still rejects at independent source re-admission. This removes an artificial
relocation *count* ceiling, not the proof limits on modified operands,
post-relocation jumps, source aliasing, runtime input-dependent state, or
full source-C synthesis. The P0 acceptance oracle remains unsupported.

### Constant-time untouched loader-tail relocation proof

The original source-backed twelve-iteration Fibonacci C program still needs
a guest layout. A follow-up experiment on repeated live `j` relocation
found that the loader's crazy recurrence has a six-word period starting
with the first expanded memory word. Each of its nine possible pairs of
ternary digits has period dividing six from that point; the independent
word-width components preserve the same property for both historical 10-
and current 15-trit memory.

The exact layout admission helper now computes untouched loader operands
with at most six crazy steps, rather than expanding up to distant source-
memory addresses through 1024-word checkpoints. Tests exhaust the nine
single-trit seeds, check both profile VMs at source-adjacent, middle and
final memory positions with two different graphical terminal seeds, and
retain separate three-live-relocation VM trace checks. Source-overlapping
or guest-written operand reads remain disallowed; this changes verification
cost, not accepted guest semantics or production proposal coverage. The
byte-stream generator still proposes only its original first `j`, and P0
remains pending.

### Bounded second-relocation guest proposal

The longer-stream bridge previously reconstructed only an initial guest `j`,
although the independent layout checker could verify additional moves. A
red-first source-independent guest with two arithmetic/output effects and a
second live `j` emits `36 08` in the normative VM. The bounded byte-stream
proposer now explores two relocation regions separated by actual guest
arithmetic and output effects. The second `j` operand comes from the exact
untouched loader tail, never from a guessed destination.

A second, three-effect guest with two outputs before the later `j` also
reconstructs, with real normative VM byte parity and disjoint data writes.
A forged byte oracle rejects. The new proposer examines up to 33 source
prefix positions, at most twelve bytes, and fixed final output/halt cells.
It runs only after previous finite search shapes fail. The original full
Fibonacci program still has no verified guest layout; this is bounded
synthesis of arithmetic/byte effects, not runtime C state or P0 closure.

### Bounded third-relocation proposal through real source C

An independently constructed 18-instruction Malbolge guest, with three live
`j` relocations separated by crazy/rotate writes and output effects, emits
`51 a2 fe` in the normative current-profile VM. The previous output-stream
proposer supported at most a second relocation even though the standalone
layout verifier could already validate the third one. A red-first test
reproduced that gap. A separate five-output guest with later relocation
splits emits `54 08 a7 b1 bc`, proving the new search is not tied to a
one-effect-per-region split.

The bounded third-relocation proposal enumerates 0 through 32 initial
no-operation cells and two interior splits among 3 through 12 output effects.
Each region contains at least one arithmetic write and an actual byte output.
The proposal derives each fresh `j` operand from untouched loader memory;
it refuses reads of source bytes or guest-written addresses, aliases among
arithmetic writes, and unsafe source overlap. The final output/halt cells
fix the loader seed for this finite straight-line grammar. Every proposed
source is independently re-decoded, checked for exact data addresses and
replayed in the normative VM before acceptance.

The real pinned Clang C pipeline now admits a three-iteration Fibonacci-style
unsigned recurrence with local state, arithmetic, a branch and three `putchar`
effects. Its independently computed reference is `51 a2 fe`, matching actual
VM output with empty and supplied input. The distinct-triple publisher has
its own explicit three-`j` grammar and repeats source-disjoint layout and
VM proofs; it does not trust the bridge's proposal. Source mutation to
unsupported division rejects without artifact publication. This remains
**compile-time** evaluation of bounded C state, not Malbolge runtime C
arithmetic or arbitrary guest byte-stream synthesis. The original twelve-
output Fibonacci acceptance oracle remains unwitnessed; P0 stays open.

### Four live relocations and a nonzero-first five-output C recurrence

An independent source-code experiment first exercised the five-iteration
Fibonacci-style unsigned C recurrence with locally maintained state, an
odd/even branch, checked division and multiplication, and five distinct
`putchar` effects. Its independently calculated output is
`35 08 dc 08 a3`. The existing compiler first rejected the nonzero-first
five-output stream at its bounded bridge, then rejected its actual candidate
at the separate file publisher. Neither stage published a guest artifact.

A generalized deterministic proposal now enumerates the positions of up to
three internal `j` splits among three to twelve output effects, rather than
assuming a particular region length. Each relocation reads an exact untouched
loader operand; every arithmetic write is outside the complete code source
and all guest writes are disjoint. All accepted proposals still undergo
independent positional encoding, source re-admission and normative guest VM
replay with empty and nonempty input. A separate four-output guest emits
`38 17 2a 2a` using four live relocations. A five-output guest with a
later split emits `35 08 dc 08 a3` using four relocations and five genuine
write/output pairs. Forged output is rejected. The generalized three-region
search retains the previously verified three-relocation grammars.

The five-effect publisher now also independently decodes its staged source,
checks the exact four-relocation instruction grammar, reads the precise
profile identity and verifies five separate source-disjoint write addresses
before performing its own normative VM replay. The complete pinned C pipeline
now publishes a genuine capsule for the five-iteration recurrence and the VM
emits exactly `35 08 dc 08 a3` under both empty and nonempty input. A C
division-by-zero mutation refuses without producing a guest file. This
still compiles C recurrence arithmetic and control flow **at compile time**,
not inside the guest; full twelve-output Fibonacci and general guest runtime
C state remain unsupported, so P0 remains pending.

### Independent twelve-byte publication admission

The full twelve-iteration Fibonacci C source was rerun after the four-live-`j`
work and still fails closed at guest layout, with no published capsule. A
separate red-first publication regression exposed a different verifier gap:
a real forward-jump guest that skips inert source cells emits twelve zeros
and halts in the normative VM, yet the twelve-byte publisher previously
accepted that output transcript despite the bridge never proposing `i`
control flow. VM byte parity alone was not a proof of the allowed linear
machine-code shape.

The twelve-byte publisher now independently decodes the entire staged
source, requires one opcode per byte effect, re-admits positional code and
current-profile identity with the linear layout checker, and verifies every
arithmetic write address is unique and outside source. It requires the
reconstructed execution to cover the source in exact step order before
replaying the same real VM byte oracle with empty and nonempty input.
The red-first forward-jump guest now refuses, while an independently encoded
12-output relocated arithmetic guest still passes. This tightens source
publication proof, **not** the range of synthesizable byte sequences; the
original Fibonacci reference and general guest runtime C state remain open.

### Two live relocations without paired output effects

The complete twelve-iteration Fibonacci C program was rerun first and still
refuses safely at guest layout. A separate source-independent real Malbolge
program exposes a wider capability gap: it executes two live `j` relocations,
intersperses no-op data strides, and emits repeated and distinct bytes without
one `p`/`*` write for each output. Its twelve-byte VM transcript is
`36 36 01 fe a2 0e 28 fe b1 85 fe b1`. The prior bounded output search
could not reconstruct that transcript.

The finite search now admits a second relocation at an independently checked
source position, derives the new data pointer from the untouched expanded
loader word, and resumes accumulator/output state search on its new data
region. It rejects overlapping or source-bound data regions before proposing
code and caps both the per-geometry search and the number of geometries.
Every proposal still passes canonical positional layout, disjoint guest write
proof, and normative VM execution with empty and nonempty input. A source-
independent test constructs the original machine code without using the
search under test, checks the real VM bytes, recovers a two-relocation guest,
and rejects forged expected output. This advances general guest synthesis,
not runtime C state or the original Fibonacci target; P0 remains open.

### Three live relocations across non-paired guest byte effects

The original twelve-iteration Fibonacci C program was retried before this
change and still refused safely at guest layout. A separate independently
encoded Malbolge program has three live `j` relocations, repeated output
instructions without intervening writes, and no-op data strides. The
normative current-profile VM executes all 31 source instructions, producing
nine output bytes (`41 41 11 30 17 17 2c 18 35`) with supplied input
left unread.

The bounded split-beam proposal now models one or two subsequent live
relocations after the initial source relocation. It derives each `j` operand
from an untouched expanded loader word and conservatively reserves every
data address, including no-ops and relocation reads. A three-region fallback
explores a small, deterministic set of balanced layouts only after the
previous cheaper proposals fail. The source-independent test checks that the
three-relocation proposal is admitted by the separate positional verifier and
VM replay, and that a forged output transcript refuses admission. The same
nine bytes can also be realized by a simpler one-relocation guest: the test
establishes that three live relocations can be **proposed and verified**, not
that they are necessary for those bytes. This is neither general guest
byte-stream synthesis nor guest-runtime C state; P0 remains open.

A further red-first 33-cell guest exercises the same real three-region
semantics but concentrates two additional no-op data strides before the
second relocation. It emits `35 35 86 af 8f 8f b5 83 c4` in the normative
VM; the previous 29/31-cell balanced search missed this transcript. A
bounded 33-cell, one-position-offset split geometry now reconstructs an
independently admitted 33-cell guest with three live relocations, source-
disjoint data writes, VM parity on two input streams, and forged-output
rejection. The original twelve-iteration Fibonacci program was retried
first and still refuses at layout. This is bounded proposal coverage, not
a general layout solver or guest runtime C-state implementation.

### Source-zero outputs before the first relocated data region

A separate source-independent 34-instruction Malbolge program executes an
initial output while the accumulator is still zero, followed by three live
`j` data relocations and nine more byte effects. Its actual current-profile
VM transcript is `00 3e 3e 2e 0a 3d 3d 10 40 19`. The prior three-region
search could synthesize the same bytes by a different guest program, but
**could not recover an initial zero-output instruction**: it forced every
pre-relocation source position to be a no-op. A red-first regression checks
this missing executable layout behavior rather than falsely claiming the
output transcript was altogether unreachable.

The bounded three-region proposer now considers proven leading zero outputs
in the graphical source prefix before falling back to the old no-op path.
It still derives all later `j` operands from untouched loader memory and
only accepts candidates after independent positional/source-disjoint layout
admission and normative VM replay under empty and nonempty input. The test
checks exactly three live relocations, an actual output instruction at the
first source cell, and forged-output refusal. This improves source-layout
coverage but does not implement arbitrary C state or complete the original
twelve-byte Fibonacci guest; P0 remains open.

### Compact two-region sources with a zero-output prefix

An independently encoded 22-instruction guest emits zero before any `j`,
then executes two live data relocations with both repeated and distinct
outputs. The real VM emits `00 53 53 42 39 38` without consuming stdin.
The earlier two-region search missed this complete source: descending
lengths exhausted its 1,500-geometry attempt cap before reaching shorter
valid layouts, and the searched prefixes excluded initial zero outputs.

A compact-source pass now checks lengths through 28 under a separate
600-geometry limit before the unchanged 1,500-geometry descending scan.
Both passes retain the existing per-beam work cap.
Source-proven leading zero effects can occupy prefix instructions, with the
old no-op prefix retained as a fallback. The red-first test requires a
source no longer than the independent guest, its actual first zero-output
instruction, both live relocations, source-disjoint writes, and VM parity
under empty and nonempty input; a forged byte refuses admission, but the
full twelve-output Fibonacci C acceptance remains unimplemented.

### Compact three-region source with repeated outputs

A separately positionally encoded 27-cell guest outputs an initial zero,
then nine total bytes across three live `j` relocations, six arithmetic
writes, and repeated output effects. The normative current-profile VM emits
`00 38 38 82 ce ce c6 7b 8b` without consuming its supplied input. The
old three-region fallback tested 29, 31 and 33 cells for this nine-byte
stream and missed the valid shorter program even though the independent
layout checker admitted its source and disjoint guest data writes.

An additional bounded `3 * N`-cell geometry now places its two subsequent
relocations at independently offset thirds, retaining all previous search
priorities and work caps. The red-first regression requires a recovered
source of at most 27 cells with a real first zero-output instruction,
three live relocations, source-disjoint writes, normative VM parity on two
input streams, and forged-output refusal. This is one additional finite
proposal shape, not shortest-code optimality, general byte-stream synthesis,
or C guest-runtime arithmetic. The original twelve-output Fibonacci source
remains the P0 acceptance target.

### Uneven compact three-region relocation spacing

The independent 28-cell guest places live `j` instructions at positions 8,
14 and 21, with a no-op data stride before the second region's first write.
Its nine real output effects are `00 50 50 3f 36 36 3f 00 12`. It exercises
both repeated and nonadjacent zero bytes, not nine host-emulated writes.
The existing bounded three-region search missed this source-independent,
positionally admitted guest because its fixed lengths skipped 28 cells.

A parameterized `3 * N + 1` compact geometry now allows the second extra
relocation to shift independently by one cell. The red-first test requires
an equally short or shorter three-`j` guest, the same actual initial zero
instruction, source-disjoint writes, normative VM replay with two input
streams left unread, and forged-byte refusal. Existing geometry priorities
and per-search work limits are preserved. This neither proves shortest-code
optimality nor implements general C runtime state: the original twelve-byte
Fibonacci P0 acceptance remains pending.

### Four live data regions with read-only operand revisits

The complete twelve-iteration Fibonacci C source was rerun first. It still
fails closed at guest layout, without publishing an artifact. A separate,
independently encoded 29-instruction guest then demonstrated four live `j`
relocations, nonpaired writes/outputs, repeated byte effects and a genuine
read-only revisit of an earlier data operand. The normative VM emits
`00 42 42 03 b7 b7 ff b9 a9` without consuming supplied input. Its exact
positional source, data writes and VM execution independently pass the
publisher, while the previous split proposer rejected the layout.

The split proposal now admits three additional relocation operands after
the first `j`, with each later `j` still required to read an untouched
loader word. A data address may be revisited by a later no-op or output:
it need not be reserved as another write. The independent layout verifier
continues to exclude overlapping writes and replays the actual VM trace,
so proposal uncertainty cannot authorize publication. A compact bounded
four-region zero-prefixed fallback now explores the `3 * N + 2` source
geometry after existing search priorities. The red-first regression proves
recovery, four real relocations, normative guest replay under two inputs,
and forged-output refusal. This is a finite candidate grammar, not general
stream synthesis, runtime guest C state or completion of the P0 Fibonacci
program.

### Nonzero-first effects in the four-region proposal

A separate independently encoded 29-cell guest retains four live `j`
relocations, repeated output effects and read-only data revisits, but moves
its initial zero output into an existing later data stride. Its actual VM
transcript is `42 42 03 03 b7 b7 ff b9 a9`, not a host-produced output
record. The prior four-region fallback rejected the trace before search
because it required the first byte to be zero, although the unchanged
independent verifier admitted its complete source and write footprint.

The four-region proposer now also explores a no-output prefix for nonzero-first
streams. The first byte still requires a genuine relocated arithmetic write;
no source or data changes are inferred from the host output bytes. Recovered
code must pass independent positional decoding, source-disjoint write proof,
and normative VM replay with empty and nonempty input; forged expected bytes
refuse. This removes a gratuitous output-value gate within one bounded
geometry, **not** a complete generalized layout solver or guest-runtime C
state. The original twelve-byte Fibonacci C acceptance remains pending.

### Uneven four-region source with an early data stride

The original twelve-iteration Fibonacci C program was rerun and still
refuses guest publication at layout. A separately encoded 30-cell guest
inserts a no-op immediately after the first `j`, moving subsequent live
relocations to positions 15, 20 and 23. The actual VM emits nine bytes
`00 41 41 8a c4 c4 8a c6 86` and consumes no stdin. The existing
29-cell four-region proposal missed this independently admitted guest.

A bounded `3 * N + 3` proposal now admits the shifted four-region geometry
after the previously established `3 * N + 2` shape. The red-first
regression independently decodes the source, checks genuine four-`j`
recovery, replays the normative VM under two inputs, and rejects a forged
output. Source-disjoint writes and exact effect order remain independent
publisher obligations. This is a new finite geometry, not a general C
runtime or the full Fibonacci P0 acceptance.

### Four-region output in the final source instruction

The original complete twelve-output Fibonacci C program still refuses at
guest layout without publishing a guest. A separately encoded 30-cell guest
with four live `j` operands moves a repeated output into the penultimate
source cell, immediately before halt. This changes the loader expansion seed
and emits the actual nine-byte VM trace `00 41 8a ce ce 0b bb 09 09`.
The independent publisher admitted its positional source and source-disjoint
write footprint, but the four-region proposer searched only a final no-op.

That proposal now tests the existing no-op terminal first and a real terminal
output second for each bounded four-region geometry. The last output must
match the current guest accumulator; source-tail memory changes are not
guessed from the desired bytes. Red-first recovery, four-relocation decoding,
empty and nonempty input VM parity, and forged-output rejection pass.

This widens one bounded candidate grammar, not general synthesis or runtime C
arithmetic. The original Fibonacci P0 acceptance is still pending.

### Four-region arithmetic terminal seeds

The original complete twelve-output Fibonacci C program still refuses at
layout with no published guest. A source-independent 30-cell guest with
four live relocations instead makes its final instruction before halt a
real `p` or `*` data write. The unchanged nine output instructions emit
`00 38 38 8a b5 b5 b1 88 b0` with the terminal `p`, or
`00 41 41 8a b5 b5 8a c6 8a` with the terminal `*`. Those source cells
also select a different loader-expanded data stream for earlier writes.

Both 30-cell programs were independently admitted by the publisher and the
normative VM. Earlier four-region proposals searched only terminal no-ops
and outputs, so neither source could be recovered.

A shorter 29-cell source-independent guest exposes the same gap in the
original compact relocation geometry. Its terminal `*` changes the loader
seed while the VM emits `00 42 42 03 c6 c6 a5 18 ff`. The independent
publisher admitted the source before the expanded search; recovery failed
without arithmetic terminal candidates in this shorter geometry.

The four-region composer now makes a tightly bounded first pass over both
`3 * N + 2` and `3 * N + 3` split geometries with 64 retained search steps
for each arithmetic terminal. The established no-op/output searches retain
their previous geometry order and 32,768-step budget. Red-first tests pin
all three guest oracles, check four live `j` relocations, replay both input
streams and reject forged outputs. Independent positional and source-disjoint
write admission remains decisive.

This adds bounded source-tail choices, not arbitrary byte-stream synthesis or
runtime C arithmetic and loops. The original Fibonacci P0 acceptance
remains open.

### Fifth live data relocation across twelve real output effects

The complete, unchanged twelve-iteration Fibonacci C program was retried
before this change and still refused at its positional guest-layout boundary.
The typed C effects remain admitted; no guest artifact was published. The
four-relocation writer had a separate, concrete ceiling: its proposal guard
rejected a source-independent guest with five actual `j` relocations even
though the independent layout checker could admit that guest.

A 30-cell, positionally encoded source with five relocations, twelve distinct
`p` writes, twelve real `<` instructions and a final halt emits
`41 47 5a 25 25 4d 32 18 5a 25 25 4d` in the normative current-profile VM.
The five relocations read untouched operands, and all twelve write addresses
are disjoint and outside code. The red-first test verified that the source
executed and its layout was independently admissible while the bounded
proposal rejected the same guest. Extending the existing relocation-count
parameter to five recovers its exact source. Empty and nonempty stdin replays,
output order, write footprints and forged-output rejection pass.

The general short-stream bridge now tries this additional paired-write search
for streams of 10 to 12 bytes only, after its established smaller-region
proposals. For this output stream the production bridge can independently
admit a different 30-cell guest, which is equally valid because the compiler
contract is observable byte parity, not exact source-byte identity. This
adds one bounded relocation capability; it does not establish shortest-code
optimality, arbitrary output synthesis, guest-side C state, or a witness for
the original Fibonacci C stream. P0 remains open.

### Source-scratch arithmetic after a forward code jump

The complete twelve-iteration conditional Fibonacci C program was retried
first and still refused guest publication at layout. A two-iteration variant
of the same original source independently requires bytes `02 59`, but the
previous guest grammar could not realize that pair. A forward `i` jump can
leave graphical no-op source cells behind the code pointer; the actual VM
may use those cells for `p` and `*` data writes without changing future code.
The prior layout checker refused every in-source arithmetic write.

The layout checker now permits only writes strictly behind the active code
pointer, updates its shadow memory with exact arithmetic results, and still
rejects current or future code overwrites. A bounded source-scratch proposal
explores these skipped loader bytes without host-produced output. The final
publisher independently decodes the forward jump, proves no pending code
write and distinct data writes, re-admits the full source, and executes two
normative VM replays with different stdin. The real pinned C pipeline now
emits a capsule executing 85 guest steps and returning `02 59` on both inputs.
A source-backed positive regression, red-first layout tests, mutated source
rejection and the independent VM oracle cover this new semantic boundary.

This is **not** runtime C loop or arithmetic lowering: the frontend still
projects closed C state at compile time. The full twelve-byte Fibonacci
stream remains unwitnessed by the bounded layout grammar, and P0 stays open.

### Forward-jump scratch streams beyond two effects

The bounded source-scratch search now tracks the jump-encrypted skipped cell
as an exact prospective operand, rather than assuming its original no-op
byte. The guest may rotate or apply crazy arithmetic to that cell after the
forward jump, since it remains behind the code pointer. A targeted layout
regression checks the post-jump encryption value, actual source mutation and
normative VM byte output on two input streams.

The source-scratch proposal also reaches three guest output effects for
`02 59 1b`. The three-distinct-output bridge can propose this geometry and
the file publisher independently decodes its forward jump, re-admits exact
source-cell writes and replays the normative VM. A complete three-iteration C
recurrence with unsigned locals, branch selection and nested arithmetic emits
the same bytes through the pinned pipeline and guest VM. The C control flow
and arithmetic still project at compile time; no guest C integer runtime or
arbitrary output-stream synthesis is claimed. The original twelve-byte
Fibonacci target remains unsupported at layout.

### Loader-valid variable source scratch for twelve-effect C streams

The unchanged twelve-output Fibonacci target still fails closed at layout:
`02 59 5f 08 57 4f 22 6d 03 90 b3 23` has no admitted guest within
these bounds. Its early `5f` effect is a concrete blocker for the previous
fixed-no-op source-scratch geometry. The compiler now supports a distinct,
source-proven complete twelve-iteration C recurrence whose two conditional
arms mask the selected Fibonacci values to five bits. The independent C
oracle is `02 19 1f 08 17 0f 02 0d 03 10 13 03`.

The first attempt at that complete C program reached typed IR but refused
at the guest layout boundary. The repaired layout admits explicit graphical
`SkippedDataByte` words **only inside a proven forward-jump gap**, and only
when the exact decoder phase yields an instruction the normative loader
accepts. The code pointer never executes those cells; the data pointer
reads them as distinct real operands. A finite source-scratch search tracks
both the exact accumulator and its advancing data phase, allowing up to
five arithmetic/no-op steps between output effects. Each candidate is
re-admitted positionally and rerun under two normative VM input streams.

The independent publisher reconstructs the jump and every skipped source
byte from the staged artifact; it does not trust the search proposal or
interpret skipped data as executed opcodes. It proves all source writes are
strictly behind code and distinct, rejects overwritten pending code, and
checks both exact guest byte order and input independence. The full pinned
C pipeline now emits an actual capsule that terminates after 49 VM steps
with all twelve masked bytes under empty and nonempty stdin. Mutating its
source to introduce undefined division is refused before guest publication;
loader-invalid and reachable-as-data placements are negative regressions.

This is bounded output arithmetic in Malbolge after **compile-time**
source-checked C state/branch/loop projection. It does not implement C
runtime loops, arbitrary guest memory, or the original unmasked twelve-byte
Fibonacci stream. The general P0 output-language goal remains open.

The bounded scratch state search now stores predecessor indices instead of
copying full opcode/operand paths for every alternative. Skipped code cells
may also decode as the profile's input instruction or as a jump: the loader
accepts those graphical bytes, but the actual jump skips them, so the guest
reads them **only as data**. The proposal precomputes all eight
loader-valid source bytes at each decoder phase. An independent layout/VM
regression places the otherwise executable input and jump byte at skipped
address one, proves its arithmetic data write lies strictly behind code,
and confirms it consumes no stdin under two inputs. The exact-address layout
checker and normative VM still own acceptance, not the search.

A second source-derived twelve-iteration conditional Fibonacci program
preserves six bits instead of five in each output arm (`& 63U`), with
independent unsigned-C oracle `02 19 1f 08 17 0f 22 2d 03 10 33 23`.
The pinned C frontend, canonical byte bridge and graphical publisher emit a
real VM guest reproducing those twelve bytes on empty and nonempty stdin;
a source mutation introducing division by zero is rejected without an
artifact. This is a semantic-width matrix case, not proof of arbitrary
six-bit streams or of the unchanged unmasked `02 59 5f ...` program.

### Source-proven compound induction in a full C recurrence

A complete twelve-iteration masked Fibonacci C program with the conventional
`for (...; i < 12U; i += 1U)` induction failed at the normalized JSON-to-typed
boundary. The pinned Clang emitted a typed `compound-assignment-expression`
for the loop's step, whereas the bounded source proof admitted only prefix
and postfix `++`. The original attempt correctly returned `Unsupported`
without publishing a guest artifact.

The bounded loop projector now also proves an unsigned induction variable
advanced by exactly the `+=` operator and a single `u32` literal `1`, with
canonical counter identity, complete right-hand side, source ordering and
checked span coverage. The complete pinned C source now produces a real
guest capsule with twelve verified output bytes
`02 19 1f 08 17 0f 02 0d 03 10 13 03`, matching the independent oracle
under empty and nonempty stdin. Source mutations to a two-step increment,
subtraction, and the wrong induction symbol reject without publication; six
forged operator, literal, symbol and span metadata cases also refuse.

Compound assignments in the loop body, variable-derived steps, other
operators and steps other than one remain unsupported. The compiler still
folds the closed C recurrence at compile time, not in guest-side C control
flow. The unchanged unmasked twelve-byte Fibonacci target remains unsupported
at guest layout; the P0 generalized guest-output language goal stays open.

### Bounded non-unit induction with a source-derived trip count

A complete masked Fibonacci C program was first attempted with
`for (unsigned i = 1U; i < 12U; i += 2U)`. The typed frontend rejected
its nonzero start and two-step induction before guest publication. Its
six-byte output required a distinct, expensive guest layout search, so the
whole-program acceptance was instead retained at twelve iterations by
changing the checked loop bound to `25U`.

The bounded loop projector now proves a source-typed unsigned initial value,
positive literal `+=` stride up to twelve, and the exact counter progression
until the `<` test becomes false. The limit is on actual iterations, rather
than the numeric bound. It retains exact source order, canonical counter
identity, typed operands and checked spans. Zero-trip bodies are still proved
without publishing their speculative effects. A zero step, subtraction,
wrong increment symbol, step beyond twelve and thirteen-trip loop are rejected
without a guest artifact.

The independently calculated twelve-iteration C recurrence with `i = 1U`,
`i < 25U`, `i += 2U` emits
`02 19 1f 08 17 0f 02 0d 03 10 13 03`. The real pinned compiler and
normative Malbolge VM reproduce that entire stream with both empty and
nonempty stdin. This broadens compile-time closed-loop evaluation, not
runtime C arithmetic or guest control flow. The unmasked original Fibonacci
stream still has no admitted guest layout; general P0 completion remains open.

### Inclusive unsigned induction in the complete C recurrence

The twelve-output masked Fibonacci C experiment was first retried with
`for (unsigned i = 0U; i <= 11U; ++i)` and a descending
`for (unsigned i = 12U; i >= 1U; --i)`. Both were accepted by the pinned
Clang frontend but rejected by the normalized JSON-to-typed adapter before
publishing guest code. Strict `<` and `>` were the only proven `for` bounds.

The bounded projector now admits `<=` and `>=` against an unsigned literal
bound, with canonical one-space comparison-token geometry independently
checked against Clang source spans. This rejects shortening an inclusive
operator in forged AST metadata while retaining the existing closed-source
provenance and exact counter identity checks. It supports ascending and
descending unary or bounded compound steps, checks each update against
unsigned underflow or the adapter's byte-range ceiling, and refuses any
thirteenth body iteration. Even zero-trip loops must have an admissible
body, and their speculative effects are discarded.

The complete ascending, descending and two-step inclusive C recurrence
variants have the same independent twelve-byte oracle as the strict source:
`02 19 1f 08 17 0f 02 0d 03 10 13 03`. Tests under
`tests/test_compound_c_pipeline.py` compile each entire variant to guest
Malbolge, compare normative VM stdout with empty and nonempty stdin, and
check source and AST mutation refusals. This is compile-time C state folding,
not runtime guest C induction. The original unmasked Fibonacci output is
still outside the bounded layout publisher, so the P0 remains open.

### Source-proven descending bounded induction

The full masked twelve-iteration Fibonacci C source was retried with
`for (unsigned i = 12U; i > 0U; --i)` after the bounded increasing-loop
projector rejected it at the first declaration. The adapter now checks a
strict typed `>` comparison and permits prefix/postfix `--` or literal `-=`
steps on the same unsigned induction symbol. It replays the actual counter
values with checked subtraction, rejects wraparound, and enforces a maximum
of twelve executed iterations rather than a numeric start limit. A zero-trip
body is still fully source-admitted on shadow state without retaining output.

The entire `--i` C recurrence reaches the normative Malbolge VM and emits
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 guest steps, agreeing with an
independently calculated unsigned-C oracle. `tests/test_compound_c_pipeline.py`
checks prefix/postfix decrement and a 24-to-zero two-step countdown against
both empty and nonempty stdin, plus unsafe step, wraparound, loop-bound,
source-symbol and forged Clang-AST mutations. These are **compile-time**
closed-state loops; guest runtime C induction and the unmodified twelve-byte
Fibonacci output remain unsupported.

### Bounded not-equal induction with exact-endpoint guest parity

The complete twelve-iteration masked Fibonacci C program was retried with
`for (unsigned i = 0U; i != 12U; ++i)` rather than a relational bound.
Pinned Clang accepted the whole C function, but the typed adapter rejected
its declaration before any guest publication. A red-first end-to-end test
confirmed the same refusal for descending `i != 0U; --i` and the positive
stride `i != 25U; i += 2U` from one.

The source-bounded projector now accepts `!=` with checked two-character
comparison-token spacing, source-tied induction symbol, discarded prefix,
postfix or bounded compound step, and an exact reachable endpoint. The step
operator determines direction; crossing the bound, `u8` underflow or overflow,
zero stride, wrong symbol, and more than twelve trips all refuse. Zero-trip
bodies are still proved on shadow state without publishing skipped output.
This is a finite **compile-time** projection of known C state, not a guest
implementation of dynamic comparison or induction.

`tests/test_compound_c_pipeline.py` verifies ascending, descending, and
stride-two whole-program variants against the independent twelve-byte oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` using the actual Malbolge guest VM,
with both empty and nonempty stdin. An ascending witness takes 47 VM steps.
A separate zero-trip `!=` full C program preserves a later three-step
`do-while` recurrence and emits only `0x41` on both guest inputs. Negative
C source and forged AST tests refuse without a guest artifact. The original
unmasked Fibonacci stream still has no admitted general guest layout; P0
remains pending on its generalized byte-stream and runtime-control goals.

### Two-level source-proven bounded induction

The complete twelve-output masked Fibonacci C program was first retried with
three outer `row` iterations and four inner `col` iterations. The pinned Clang
frontend accepted the nested `for` statements, but the JSON-to-typed adapter
refused the first declaration because the previous closed-flow projector
allowed only one active induction counter and no nested `for` body. No guest
artifact was published in that red-first experiment.

The bounded projector now permits exactly two lexical `for` levels, each with
its own source-proven unsigned induction, bound, step and symbol. It protects
**all** active counters from body assignments, preserves outer local state
across the inner loop, drops inner lexical declarations at each iteration,
and rechecks source/AST identity during every replay. Both loops retain the
existing checked 12-iteration ceiling; a third nested `for` refuses.

The complete 3-by-4 C recurrence now produces the independently calculated
`02 19 1f 08 17 0f 02 0d 03 10 13 03` through the actual normative VM on
empty and supplied input. An inner zero-trip variant validates the skipped
body on shadow state, discards its output effects and then emits only `0x41`
from a later C call in the real guest. Mutations that assign either active
counter, corrupt the skipped body, forge a Clang parent/step/symbol or add
a third loop nesting level refuse without publication. These are closed
compile-time C loops; the guest does not implement dynamic C induction,
and the unmodified unmasked Fibonacci stream still lacks a guest layout.
The generalized P0 remains open.

A further whole-C experiment removed the outer braces from the same 3-by-4
recurrence, so the outer `for` directly parents the inner `for`. Clang
accepted that ordinary source but the adapter first refused without a guest.
The bounded replay now accepts this **one** unbraced nested `for` body when
its parent, source span and exact final-child end are proven. It does not
invent a compound scope, admit arbitrary unbraced loop bodies, or relax the
two-level induction limit. The unchanged twelve-byte oracle reaches the real
guest VM in 47 steps under empty and binary stdin. A forbidden write to the
outer counter and three forged AST parent/tail mutations refuse without
publishing a guest. The unmasked Fibonacci layout remains unsupported.

### Direct unbraced conditionals as bounded loop bodies (2026-11-10)

Two full twelve-step masked Fibonacci C programs moved all state transfers,
branch-local `unsigned next` declarations and `putchar` outputs into the
selected arms of an `if/else` directly under a `for` or `while`. Both valid
programs were first rejected at the JSON adapter, before guest publication.
The `while` source increments its loop guard in either arm and rechecks the
predicate against updated state for each of the twelve iterations.

The bounded replay now accepts **one** source-checked direct `if` as the
entire unbraced body of either loop. The pinned Clang parent must be the
actual loop statement, and the conditional's source tail must end exactly
where the loop ends. Both branches are proven against the same incoming
state; only the selected branch's local writes and output are committed.
No brace scope is synthesized and no second direct sibling is admitted.
This extends the existing bounded compile-time state proof, not Malbolge
runtime branches, C storage or dynamic induction.

Both complete programs emit the independently derived masked Fibonacci bytes
`02 19 1f 08 17 0f 02 0d 03 10 13 03` from the normative guest VM in
47 steps under empty and binary input. Five invalid C-source cases (a
condition side effect, a forbidden induction-counter write and unproved
`switch` effects) and nine forged AST ancestry, metadata and tail cases
fail without publishing guest code. The original twelve-output unmasked
Fibonacci C still lacks generalized guest layout; P0 remains pending.

### Unbraced `do/while` with conditional and nested `for` (2026-11-10)

The full twelve-step masked Fibonacci C recurrence was retried with an
ordinary `do` whose sole unbraced body is an `if/else`. Both branches declare
an iteration-local `unsigned next`, emit the selected byte, transfer the
recurrence state and increment the enclosing `i`. The trailing
`while (i < 12U);` is tested after every body execution. Pinned Clang
accepted the complete C program but the JSON adapter originally refused
its first local declaration, publishing no guest artifact.

The bounded replay now checks a single direct `if-statement` child of the
`do-statement`, with no invented compound scope. The next direct Clang
sibling must be its pure condition, after the complete conditional span;
its source tail must leave exactly the final semicolon. Source-parent,
span, metadata, local writes, branch effects and the twelve-trip bound
remain checked. As in braced `do/while`, the predicate is evaluated against
state updated by the selected branch, after the mandatory first body trip.

The real normative guest VM emits the independently derived byte oracle
`02 19 1f 08 17 0f 02 0d 03 10 13 03` in 47 steps under both empty and
binary stdin. Three invalid source variants (nonterminating induction,
side-effecting predicate and an unproved nested loop) and five forged AST
cases refuse without publishing guest artifacts. This remains finite
compile-time C-state replay; the original unmasked Fibonacci stream and
dynamic guest C loop execution still lack proof. P0 remains pending.

The same source proof now admits one direct bounded `for` as the entire
unbraced `do` body. A separate complete C Fibonacci program uses three
outer `do` trips, each executing four inner `for` trips. The inner loop's
source-checked `++outer` advances the trailing pure `outer < 12U` guard,
while each inner trip performs the real conditional output and recurrence
state transfer. Pinned Clang parents the inner `for` directly to `do`;
the parser does not synthesize any missing braces. The complete program
initially refused at the JSON adapter; after the repair, it emits the same
independent twelve-byte masked Fibonacci oracle from the normative guest
VM in 47 steps under empty and binary stdin. Three nonterminating or
impure C-source variants and five forged AST mutations reject before
publication. This proves finite source-C replay, not general nested guest
induction or unmasked byte-stream layout. P0 remains pending.

### Source-proven lexical scopes in loop bodies

A complete twelve-output masked Fibonacci C recurrence was first attempted
with an explicit compound scope inside its `for` body. The scope declares an
iteration-local `transfer` from `next`, then updates the enclosing `a` and
`b`. The pinned Clang frontend admitted the C program, but the typed adapter
refused the compound source node without publishing a guest artifact.

The bounded loop-body projector now walks up to four nested lexical compound
scopes with exact Clang parent and span evidence. It retains writes to
outer locals and selected `putchar` effects, drops each scope-local declaration
upon exit and reapplies that proof on every loop replay. The existing loop
iteration, statement, local-count and source-identity bounds still apply;
a fifth nested compound refuses. Skipped-loop shadow traversal also proves
every nested source expression before discarding speculative state and output.

The complete 12-effect C program has an independently calculated masked
Fibonacci oracle `02 19 1f 08 17 0f 02 0d 03 10 13 03`.
`tests/test_compound_c_pipeline.py` exercises actual guest VM parity,
zero-trip preservation of a following `0x41` output, undefined division
inside skipped scopes, forged Clang parent/metadata and excessive nesting.
The original unmasked Fibonacci trace still lacks a general guest layout.
This is compile-time C state propagation, not runtime guest C block storage.
P0 therefore remains open.

### Selected unbraced `break` and `continue` in complete C recurrences

Two complete masked Fibonacci C programs extend the selected-control probe.
The first has three outer `for` trips and five inner trips per row, using
`if (col == 0U) continue; else { ... }`. The second admits six inner
counter values, but `if (col == 4U) break; else { ... }` stops each row
after four recurrence outputs. Both are ordinary, pinned-Clang C sources
with twelve stateful conditional `putchar` effects and the independent
expected byte sequence `02 19 1f 08 17 0f 02 0d 03 10 13 03`.

The original complete sources refused at the JSON adapter. The repaired
bounded projector allows source-proven unbraced `break`/`continue` as one
conditional arm, using its existing exact keyword/Clang-span proof. An
unselected control arm is replayed only on shadow state; the selected arm
carries the exit to the nearest `for`, which consumes `break` or advances
the induction step for `continue`. Other branch-local variables, state
transfers and effects remain source-checked. Both real guest capsules
emitted the independent twelve-byte oracle in 47 normative VM steps under
empty and binary stdin. Four invalid source variants and ten forged AST
keyword, parent, span and metadata cases refused artifact publication.
This does not add dynamic guest C control flow or the original
unmasked byte-stream witness; P0 remains open.

### Unbraced unsigned while updates before conditional output

A pinned-Clang complete twelve-trip Fibonacci source uses an unbraced
`while (parity < (next & 3U)) ++parity;` to calculate an unsigned
local that selects a following putchar branch. The bounded source
projector now admits a directly parented unary while body and replays
its checked writes and condition before each selected output.

The normalized Clang oracle and adapter regression verify twelve
independently source-proven typed output effects, yielding
`02 19 1f 08 17 0f 02 0d 03 10 13 03`, with malformed
statement ancestry, foreign references and kinds refused. The
complete guest compilation still reaches the unsolved literal-stream
layout synthesis without publishing an artifact in its search budget.
This is source-level static replay, not dynamically lowered guest
loop execution; the original unmasked Fibonacci blocker remains.

### Bounded negative reachability after expanded scratch relocation

The complete unmasked C recurrence still requires `02 59 5f` at its
start. After the previously VM-proven `02 59` source-scratch prefix, a
guest `*` write and two live `j` relocations yield a concrete 15-trit
accumulator and a pointer into loader-expanded memory. The bounded scalar
regression now searches up to twelve no-op/crazy/rotate/relocation steps
for the next byte, allowing zero to two further data relocations. For
each candidate length, four final source opcodes before halt independently
change the loader's two-cell recurrence seed. Exact accumulator words
and data-pointer locations remain distinct search states.

No explored fresh-expanded-word state produces `0x5f`. The graph allows
more paths than the admissible linker, but it assumes each arithmetic
operand retains its original loader word; guest-written operand revisits,
modified graphical scratch, and other source tail geometries are outside
this negative result. The existing `02 59 b9 b6` witness still proves two
real expanded-memory arithmetic effects in the normative VM with empty
and binary input. No source compiler capability is claimed, and the P0
remains unresolved.

### Exhaustive fresh graphical scratch reachability

The original full unmasked Fibonacci C source still needs the byte prefix
`02 59 5f`; the compiler continues to refuse at guest layout. A new finite
state-space experiment removes the twelve-instruction limit for a specific
single-forward-code-jump geometry. It starts with the phase-zero jump, varies
every subsequently read graphical scratch operand over all eight
loader-valid positional bytes, and retains the **full 15-trit accumulator**
and number of correctly emitted output effects at each data-pointer position.

`o`, `p`, `*`, `<`, and **any number** of strictly forward `j` data-pointer
relocations are included. Since D always increases, each operand is fresh and
the graph is acyclic; dynamic programming exhausts all 96,732 reachable
state/phase combinations for `02 59 5f` in this geometry. None emits the
third byte. As a positive control, `02 59 5d` is reachable, and a separately
admitted 109-cell source executes it in eleven normative VM instructions under
two binary-input conditions. The result is **not** an impossibility claim for
Malbolge or the full C program: backward/rewritten operand revisits, other
initial jump phases, additional code jumps and loader-expanded memory are not
part of this graph. General guest arithmetic and runtime C control remain P0
work, not a completed compiler capability.

### Mixed unsigned scalar and Boolean C conditions

A new complete twelve-iteration Fibonacci source combines a pure unsigned
bit expression with a nested `&&`/`||` condition. The normalized pinned
Clang AST previously refused the mixed `u32`/`i32` logical operands. Bounded
source-state replay now proves each operand, retains the original checked
Clang ancestry and C truth semantics, and admits the mixed shape in either
order. Two unsigned logical operands remain intentionally unsupported: an
untrusted normalized AST can otherwise forge a same-width `==` operator into
`&&` without distinguishable operand types.

The complete C compiler emits a real 47-step guest whose twelve binary
outputs are exactly `02 19 1f 08 17 0f 02 0d 03 10 13 03`, matching an
independent unsigned recurrence under both empty and nonempty VM input.
This capability extends compile-time C replay, not dynamic Malbolge guest
state. The original unmasked Fibonacci stream and P0 remain pending.

### Source-proven nested short-circuit subtrees (2026-11-11)

A complete twelve-iteration unsigned Fibonacci C program now nests a
Boolean `||` expression under an outer `&&`. The outer guard is false
on even recurrence terms, so the entire nested expression is skipped
including a division whose divisor would be zero. On odd terms, the
inner `||` selectively evaluates a defined division or skips it. The
pinned Clang frontend accepted the full C source, while bounded
source replay originally rejected it before producing a guest artifact.

The projector now authenticates both pure children of a wholly skipped
logical subtree without evaluating undefined C arithmetic. It retains
complete AST ancestry, checked operator metadata, source-ordered spans
and the existing ban on ambiguous two-unsigned logical children. A
limited expression-depth increase to twelve admits this composition;
unknown effects, selected zero division and malformed Clang trees still
refuse. This is **compile-time source replay**, not dynamic guest
short-circuit execution or arbitrary C expressions.

The independently calculated twelve-byte masked recurrence
`02 19 1f 08 17 0f 02 0d 03 10 13 03` matches the actual normative
Malbolge guest in 47 instructions with EOF and binary stdin. The
original unmasked Fibonacci output still has no generalized layout
witness, and the P0 remains open.

### Evolved source-scratch third byte (2026-11-12)

The original unmasked Fibonacci C source initially refused after three loop
iterations (`02 59 5f`) even though a hand-constructed source-independent
VM witness could produce the prefix. A bounded, byte-parameterized proposal
now reuses the genuine two-output source-scratch guest, rotates an untouched
skipped source word, relocates D back to it with a real `j`, and rotates the
modified word a second time. Fresh graphical operands supply the final
arithmetic and third output; neither byte is host-injected into guest stdout.

The independent publisher admits exactly one relocation after two outputs
and one repeated source write only when the relocated D revisits the earlier
written cell. Positional decode, source shadow, all write addresses and two
normative VM replays remain mandatory. The pinned three-trip complete C
program emits `02 59 5f` with EOF and binary stdin, while selected undefined
C arithmetic rejects and the original twelve-trip program still refuses
without publication. This search costs roughly two minutes through the full
pipeline; dynamic guest C control, longer full-width streams and faster
reusable block synthesis remain open.

### Mixed-byte dense source-revisit search (2026-11-14)

A red-first bounded search regression combined six output-progress counts
with every possible low accumulator byte and 65 distinct high-word
representatives. Prior per-progress quotas retained each class's minimum
and maximum full words but discarded its middle candidate `8195`.
With the same guest operand zero, a real `p` step maps the words
`3`, `8195`, and `16387` to distinct low bytes `50`, `93`,
and `223`. Therefore equality of a pending output byte does not justify
discarding this full-word continuation.

The bounded source-revisit beam now keeps an existing word nearest the
midpoint of each active progress/low-byte range in addition to its
extremes. Even the maximum nine progress counts and 256 byte groups use
at most 6,912 protected representatives, below the existing 16,384
state cap; unused capacity remains shared among progress counts. All
candidate sources still require independent positional/layout admission
and normative VM replay. The red-first regression, twelve-byte real
Fibonacci guest and canonical typed publisher pass; the pinned frontend
was unavailable, so no original full source-C pipeline parity or
generalized P0 acceptance is established.

### Mixed signed input and source-proven unsigned local (2026-11-17)

The frontend now independently admits the complete closed C23 shape
`unsigned checksum = 0U; int current = getchar(); checksum += 11U;`
followed by `putchar((int)checksum);`. It checks every normalized Clang
node against the original source, re-admits a canonical signed `Getchar`
followed by a proven unsigned local byte value, and delegates target
emission to the existing separately verified mixed-effect backend. The
signed input is neither converted to a byte nor discarded in typed IR.
A native Clang -O0/-O2 and source/AST mutation regression confirms its
frontend proof; a failing backend injection verifies that unsupported
layout never publishes an artifact. This is **not** an accepted P2 guest
checksum: the new regression does not claim executable guest parity, and
the full mutable EOF loop still rejects at the first unsupported dynamic
storage/control-flow node (29:5). Its layout synthesis remains a costly,
independently verified downstream operation.

### Executed mixed signed input with mutable constant C local (2026-11-17)

The previously source-authenticated complete C23 function with one signed
`getchar()` initializer, `unsigned checksum = 0U`, `checksum += 11U`,
and final `putchar((int)checksum)` has now reached actual target
publication. The normative 15-trit Malbolge VM runs its 1,087-byte
capsule in five guest steps; the real read is preserved before the
source-proven independent output. Six binary/EOF streams (empty, NUL,
`0x80`, `0xff`, `00 80 ff`, `05 00 81`) all emit `0b`, matching native
Clang C23 UBSan `-O0` and `-O2` for the same function. A new complete
pipeline regression checks capsule publication, exact output and bounded
VM steps; source mutations must still fail before publishing an artifact.
The verified local update is constant-folded on the host, **not**
executed as guest storage/arithmetic. Input-dependent updates, runtime
conditional branches and the frozen mutable EOF checksum still refuse
at their first unsupported dynamic construct. This is not P2 acceptance.
EOF may never be treated as a successful `u8` read.

### Publisher-scope signed C23 byte conversion audit (2026-11-24)

The separately linked **second** signed `getchar()` / `putchar()` path now
checks the full **257-class** scalar domain before target publication: every
successful C byte (`00` through `ff`) and true C23 EOF (`-1`), converted
through an independent 15-trit `crazy` truth table and compared with C23's
unsigned-char output. This is fast scalar evidence, **not** 257 extra VM
runs on each compilation. The existing normative VM replay still checks
representative first/second input combinations and now additionally
requires physical `p` execution at C77/M95 and C78/M96, their exact
pre-write operands (7,138,732 and 121), both input-dependent accumulator
results, and the C79 output. The separate exhaustive 259-vector guest
regression remains authoritative for the actual full byte domain; it is too
expensive for every publish transaction.

The complete source-C double-read pipeline, including automatic `int`
aliases, remains executable and agrees with native C23 on EOF and binary
input. The first C37 read is **still consumed**, so the one-read direct
`putchar(getchar())` program must continue to refuse, and this change
does not link mutable checksum state or runtime branches. The source-C
frontend also conservatively refuses unconverted signed direct or aliased
outputs inside `for`, `while`, and `do` loop ancestry; only independent
EOF-capable lowering may relax those refusals.
