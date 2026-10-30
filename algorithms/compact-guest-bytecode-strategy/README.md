# Compact guest bytecode strategy: echo macro pilot

## Boundary

This is a research-only structural-compression candidate, **not** a guest
bytecode interpreter and not a compiler backend. The `CEB1` descriptor is six
bytes: four literal magic/version bytes and a little-endian `u16` repetition
count. It describes exactly `n` consecutive successful `ByteInput`/`ByteOutput`
SSA-identical pairs followed by `ReturnVoid`, with `1 <= n <= 2047`.

Both encoding and independent admission require the original already-validated
canonical `malbolge-ternary-ir-v1` program and selected `malbolge-2026` profile.
The descriptor does **not** contain the original source identity, source digest,
ABI, profile fingerprint, function metadata, or guest data placement. Another
valid equal-length source can reuse the same candidate. It cannot be published
or executed as a stand-alone trusted artifact.

## Verification

The candidate generator checks the canonical ternary program and exact effect
shape. The independent decoder checks the full count and every source pair,
reconstructs a **direct** layout on the host, and asks the existing trusted
position-sensitive encoder to verify the final graphical source.

```sh
cargo test --locked --test compact_guest_bytecode_strategy --quiet
cargo clippy --locked --test compact_guest_bytecode_strategy -- -D warnings
```

The test runs all 256 successful `u8` input values through the normative VM
using **expanded direct source**, not guest-interpreted bytecode. Other cases
check 1, 2, 3, 7, 20, 64, 256, and 2047 echo pairs, including the 4095-cell
upper direct bound. The complete 4095-cell source also runs on the normative
VM with all 2047 effects observed in order. All single-byte substitutions,
truncations, trailing bytes, profile drift, wrong SSA uses, empty and overlarge
traces reject. A separate test demonstrates the intentionally missing
source binding.

A separate external-process baseline publishes real `.malbolge` from canonical
MCTR checkpoints for 1, 7, 64, and 256 pairs using `malbolge_layout
--ternary-file`; every published byte equals the independently reconstructed
direct source. These are real **direct** programs, not guest bytecode artifacts.

## Reproducible pilot

`pilot-v0.toml` records the fixed case family and cost assumptions. No seed is
needed because the bounded generation is deterministic. The size comparison is
only **optimistic**: one byte of candidate data is presumed to require exactly
one Malbolge memory cell, while the actual decoder, loader, envelope, dispatch,
relocation, runtime verification, and error semantics are entirely absent.

The estimated runtime-plus-packaging allowance for a *strictly shorter*
artifact is `direct_code_cells - 7`, if nonnegative. A second sensitivity
scenario reserves 32 **hypothetical** memory cells for source/profile binding,
giving the stricter ceiling `direct_code_cells - 39`. Neither figure includes
an executable interpreter or proves authentic provenance. These are upper
bounds, not observed headroom. See the owning research record for the
complete table, failed small cases, and unresolved acceptance criteria.

## Bound follow-up: CEB2 v1 (2026-10-29)

`pilot-v1.toml` and `echo_binding.rs` add a separate, 38-byte research
candidate: four literal `CEB2` bytes, the same little-endian `u16` pair count,
and exactly 32 SHA-256 digest bytes. The digest binds the fixed domain
`CEB2-ternary-profile-v1\0`, the selected *profile fingerprint*, a separator
byte, and the fully validated canonical `malbolge-ternary-ir-v1` wire bytes.
The canonical bytes contain source identifier/hash, guest ABI, profile ID,
function names and every operation/source span. The immutable v0 CEB1 pilot
and its exact six-byte interface remain unchanged.

Both v1 encoding and v1 admission independently revalidate the original
ternary program. Admission rejects an altered digest, unsupported source,
changed count, downgrade to CEB1, truncation or extra bytes. The tests compare
all eight sizes with independently admitted direct layouts, reject every
single-byte mutation of a 38-byte candidate, and reject otherwise-valid
same-count changes to source ID/hash and function name. SHA-256 also passes
published empty, short and multiblock known-answer vectors. This is
**byte equality binding**, not source authentication: a malicious publisher
could still supply matching forged source and candidate, and the caller must
trust the original canonical ternary program and profile.

At the same intentionally optimistic one-byte-per-memory-cell assumption, v1
requires `R + 38 < 2n + 1` for a strict code-size win. The maximum allowable
missing guest-runtime cells at `n=1,7,20,256,2047` are respectively
`None, None, 2, 474, 4056`. The v0 hypothetical +32-cell column shares those
numerical thresholds, but v1 actually carries 32 digest *bytes* in its
research descriptor; it still does **not** prove 32 Malbolge data cells can
hold those bytes or account for a guest digest/decoder, loader, provenance
anchor, source availability, or any real interpreter. It also does not reduce
execution time. The CEB2 envelope is expanded **on the host** to the exact
same executable **direct** source, never interpreted by a guest bytecode VM.

The exact v1 digest framing also has a cross-language golden vector: Python
`hashlib.sha256` independently hashes the profile fingerprint and the 587-byte
canonical MCTR for seven pairs. The regression pins the 32-byte result and
profile identity, preventing Rust encoder/checker co-drift. For 1, 7, 64 and
256 pairs, the real external `malbolge_layout --ternary-file` publisher now
also yields bytes identical to *both* CEB1 and CEB2 host expansions. This
still publishes only direct programs, not resident guest bytecode.

## Literal graphical residency v2 (2026-10-29)

`pilot-v2.toml` and `graphical_residency.rs` now encode the **actual** 38-byte
CEB2 descriptor into Malbolge graphical source bytes. The normative loader
admits only eight decoded instructions (`j i * p < / v o`) at each of its
94 position phases. The pilot sorts the eight admissible graphical characters
at each position, packs three descriptor bits per source cell, and checks the
last two zero pad bits.

A 38-byte CEB2 candidate consequently occupies
**102 graphical cells**, not the previously idealized 38. The fixed
three-cell direct `input/output/halt` witness brings the emitted image to
105 cells, and an independent host reader reconstructs and re-admits the exact
bound candidate. This is an explicit literal packing strategy, **not** a
universal bound on all compressed guest representations.

The resident image is a valid position-sensitive `.malbolge` source: the
profiled VM loads every graphical tail cell, executes one successful byte
input/output, halts, and leaves the 102 tail cells untouched. The guest never
reads or decodes the proposal. The one-byte prefix does **not** reproduce a
7-, 256-, or 2047-pair CEB2 workload. Valid-looking alternative glyphs,
noncanonical pad bits, altered source identity, truncated source, and extra
cells reject under independent host admission. No new code is published
through the product source emitter; this remains a research-only image.

For an eventual *complete and semantically equivalent* n-pair guest runtime,
this particular literal placement requires the stricter necessary inequality
`R + 102 < 2n + 1`, where `R` includes all guest runtime code, dispatch,
source/profile authentication, and other placement costs. The best-case
allowance for missing runtime cells is now `None` at 20 echo pairs, **26** at
64, **410** at 256, and **3992** at 2047. Those are *not* observed interpreter
sizes, proven semantic equivalents, or speedups. A real guest interpreter may
require significantly more cells and independent verification.

## Real guest payload-read probe v3 (2026-10-29)

`pilot-v3.toml` and `guest_payload_probe.rs` add a **genuine guest-side
memory read** on top of the v2 graphical representation. A unique loader-valid
`j` at code address 0 is source glyph `40`. Its Malbolge-defined effect sets
`D` to `M[0] + 1 = 41`, the beginning of the CEB2 data region. Twelve
reached `o` instructions advance `D` to address 53: packed CEB2 ordinal 12
(three bits of its low repeat count). At code address 13, actual guest `*`
rotates and writes that resident data word into guest memory and `A`. Guest
`<` at 14 outputs `A mod 256`; `v` at 15 halts. Positions 16–40 are valid
unexecuted no-op padding; positions 41–142 hold 102 graphical CEB2 glyphs.
The resulting source uses **143 loaded cells** and **16 reached guest steps**.

Unlike v2, the VM **reads and mutates one CEB2 source-memory cell** and its
output depends on that cell. Normative profile executions for 1, 7, 20, 64,
and 256 echo counts check output and memory against an independent scalar
ternary oracle. A separate 16-step trace proves actual `D=53` semantic read,
write, code fetches, encryption, output and halt. Altering the observed count
glyph to another loader-valid glyph changes actual guest output but fails
independent host CEB2 admission. Host reconstruction still rejects malformed,
shifted, truncated and foreign-source payloads; there is no host runtime
callback supplying the guest output.

**This is not a bytecode interpreter.** The guest does not decode a glyph
ordinal, recover the complete count, check the source digest, dispatch a loop,
consume input or execute the original echo instructions. Its single output
byte diagnoses rotated CEB2 data, **not** a byte-echo result. There is no
semantic equivalence or speedup claim. The 143-cell diagnostic is even larger
than the 129-cell direct baseline at 64 pairs; those programs do different
work, so this is only a structural observation, not a performance comparison.

An additional end-to-end executable-artifact regression wraps the **same**
validated research source in a public version-one `.malbolge` capsule and runs
it through the actual general `malbolge` CLI. Distinct seven- and 64-pair
bound descriptors produce distinct exact diagnostic bytes, both independently
predicted from each literal count glyph; `--report-steps` confirms exactly
16 committed guest steps in both external processes. The source is built by
the experiment and framed with the existing capsule API, **not** emitted by
a production bytecode compiler or decoded by a bytecode interpreter.

## Guest-controlled indirect dispatch v4 (2026-10-29)

`pilot-v4.toml` and the v4 helpers in `guest_payload_probe.rs` go beyond the
v3 data-to-accumulator read. The same 143-cell, loader-valid CEB2 resident
image now executes a genuine `i` at code position 13. The initial `j` and
twelve `o` steps position guest D at 53, and `i` reads that *source-backed*
count glyph, sets C to its numeric word, encrypts the newly targeted code
cell, and advances C to `M[53] + 1`. The 15th guest step therefore fetches
and executes a target **inside the original descriptor source region**.
There is no external callback or staged host-controlled machine register.

The experiment spans all eight encodable three-bit count ranks using source
repeat counts 32/2/4/6/8/10/12/14. The independent ordinal oracle predicts
next executed code addresses 46/47/65/81/82/104/110/123. The normative VM
step trace checks the physical data read at 53, pointer relocation, target
XLAT2 encryption, actual post-jump C, fetched source glyph, and decoded
instruction at each address. An alternative loader-admissible count glyph
changes the actual jump target but independently fails the host-side CEB2
source-binding check. Every target remains within the 102-cell descriptor.

**This is a data-driven indirect Malbolge jump, not a bytecode interpreter.**
The guest executes the selected descriptor *glyph as a native Malbolge
instruction*: it never decodes the three-bit ordinal into a bytecode opcode,
interprets a complete CEB2 macro, validates SHA-256, implements an echo
loop, or provides semantic equivalence. Reached-step counts are bounded
witnesses, not a complete workload cost. The 143-cell source is not a
measured size or throughput advantage over the direct echo baseline.

The indirect jump also exposes a **code/data collision**: `i` immediately
XLAT2-encrypts the cell at `C = M[53]`, which is itself inside the bound
CEB2 graphical payload. An explicit negative VM witness checks the changed
physical memory word and shows that the post-jump source no longer passes
original host CEB2 admission. A reusable guest runtime would need a design
that avoids destructive code/data overlap or otherwise preserves a verified
unmodified bytecode representation before indirect dispatch.

## Protected-residency indirect dispatch v5 (2026-10-29)

`isolated_dispatch.rs` and `pilot-v5.toml` implement a bounded negative-case
repair for v4's confirmed XLAT2 destruction of resident CEB2 data. The new
loader-accepted 211-cell source consists of `j@0`, eighty reached no-ops,
`i@81`, 27 **unreached** code-padding no-ops, and a 102-cell CEB2 payload at
positions 109–210. The initial `j` sets D=41; eighty reached no-ops bring D
to the CEB2 count-bearing glyph at 121 (data ordinal 12). The genuine
`i@81` reads `M[121]`, encrypts the count-selected source-code cell
`M[M[121]]`, and advances C to `M[121]+1` after **82 actual VM steps**.

The eight position-valid graphical values of `M[121]` are exactly
35/41/54/71/72/90/106/107. All are strictly below the protected CEB2
start at address 109, so every possible count-derived post-jump XLAT2
write is confined to code. Source-position packing must be redone: literal
original v4 tail glyphs cannot simply be copied to source position 109.
The v5 host proposal preserves the 102 independent glyph ordinals and the
independent admission reconstructs the original 38-byte CEB2 descriptor,
checks canonical padding and revalidates its source/profile SHA-256 binding.

Eight real profiled VM runs cover all count-glyph ranks and check exact guest
reads, code-cell encryption targets, C/D register state, lack of output, and
every unchanged one of the 102 resident data cells. The host independently
re-admits the complete original payload reconstructed from actual guest
memory. A separate exhaustive source-phase oracle checks no-op counts
0 through 80; **80 is the first safe count** in this fixed `j` / repeated
`o` / `i` / 27-pad positional template for *all eight* loader glyphs.
This is not a general lower bound on Malbolge guest encodings.

The separation costs **68 more source cells** (211 vs v4's 143) and
**68 more reached guest steps** (82 vs v4's 14) before any useful bytecode
work. It removes the *first-jump payload mutation* from v4; it does not
prevent unrelated later code changes, interpret an opcode, authenticate
anything inside the guest, loop or execute an echo trace. The v5 and direct
lowering programs still have different semantics and are not a valid
size/speedup comparison.

## Count-selected real guest I/O handlers v5b (2026-10-29)

The optional `pilot-v5-handlers.toml` experiment adds actual distinct guest
work at three of the eight data-derived branch targets, without changing
the 211-cell source size or 102-cell protected payload. Its fixed source
code locations are `/` at 91 (input), `<` at 92 (output), `v` at 93,
and `v` at 107/108. For source-bound pair counts whose CEB2 graphical
count rank is 5, the guest indirect `i` selects 91 and genuinely reads,
echoes, then halts after **85 steps**. For ranks 6 and 7, it selects
107 or 108 and halts after **83 steps** with no input/output. The candidate
is rejected at the host boundary for unsupported ranks 0–4; there is no
implicit fallback to unverified code. Source/profile SHA-256 and all exact
handler glyphs are re-admitted independently before publication.

Normative VM tests cover bounded counts 10, 12 and 14 and input bytes
0, 128 and 255. They check exact output, input consumption, termination,
step counts and all 102 unchanged CEB2 memory words. Source count bits
influence actual reached I/O, not merely a diagnostic register value.

An end-to-end regression additionally frames both rank-five and rank-six
sources in canonical `.malbolge` capsules and executes the **real** general
Malbolge CLI with explicit binary stdin and `--report-steps`. The rank-five
capsule emits exactly `0xff` and reports 85 steps; rank six emits no bytes
and reports 83 steps. The host constructs the source and the guest performs
the reached native instructions; the CLI does not emulate the handler.

**This is not a bytecode interpreter.** The guest branches directly on
loaded ASCII count glyphs to hand-written Malbolge instructions. It never
computes the ordinal itself, decodes a bytecode opcode, counts iterations,
authenticates source identity, or executes all 10/12/14 echo pairs. Only the
selected rank-five route happens to echo **one** byte; the original direct
10-pair program requires ten. The rank-six/seven routes deliberately halt
without output. Neither output behavior nor size/runtime is semantically
equivalent to the direct baseline.

## Single-operation source-bound guest bytecode v6 (2026-10-29)

`single_opcode.rs` and `pilot-v6.toml` introduce a **separate graphical
operation** instead of deriving a branch from one of the CEB2 count bits.
The host admits only an independently canonical, source/profile-bound
**one-pair** echo program, encoded as the complete 38-byte CEB2 descriptor.
The 224-cell Malbolge source contains `j@0`, 80 reached no-ops, `i@81`,
an explicit loader-valid **`ECHO_ONE` opcode** at data position 121
(ordinal 5, actual graphical word 90), and fixed native `/@91`, `<@92`,
`v@93` handlers. Every original CEB2 payload glyph is re-ranked for its
new loader position in an untouched 102-cell data region at 122–223.

In the real guest, the `i@81` instruction reads the encoded opcode from
`M[121]` and transfers C to the graphical value plus one, **91**; `/`,
`<`, `v` then consume exactly one byte, emit the same byte, and halt after
**85 VM steps**. The 3-cell direct one-pair compiler baseline performs the
same successful one-byte trace in **3 steps**. Tests compare independently
emitted sources under the normative VM for bytes 0, 1, 127, 128, 255,
including input consumption and physical preservation of all 102 CEB2
memory cells. The separate general Malbolge CLI runs actual canonical
capsules for both guest and direct code on 0, 128, 255, matching stdout
and independently checked step receipts. No host callback implements I/O.

A separate regression resets validated initial VM memory for **21 selected
byte-boundary values**, exercising independent direct/guest state admission
on each execution instead of reusing self-encrypted code. Further checks
compare genuine EOF behavior and excess trailing input: both programs
agree in stdout, termination and consumed-input count. This is a bounded
matrix, not a claim that 256 VM input values were exhaustively replayed.

An independent source verifier checks the exact opcode/code layout,
reconstructs all 102 graphical CEB2 ranks from the **supplied** guest
image, and re-admits the complete source/profile SHA-256 descriptor against
the separately trusted original one-pair source. Unsupported pair counts,
foreign identities, invalid lengths, changed code or opcode cells, and
loader-valid descriptor-glyph mutations are rejected. This verifier runs
on the host; guest code does not compute SHA-256 or authenticate itself.

**Limited positive result:** One explicitly encoded operation has the same
successful one-byte stdout/input-consumption semantics as direct one-pair
echo. This is the first comparable guest workload here, but costs **221
more loaded source cells** (224 vs 3) and **82 more guest steps** (85 vs 3).
It falsifies any size/step advantage for this small workload. The opcode
is dispatched through the graphical glyph's numeric value, not decoded via
runtime arithmetic. It has no bytecode loop, repeated instructions, second
opcode, unbounded program coverage or compilation advantage. General
interpreter feasibility and the P2 TODO remain open.

## Two sequential source-bound guest opcodes v7 (2026-10-29)

`two_opcode.rs` and `pilot-v7.toml` extend the actual v6 guest I/O
experiment to **two independently fetched graphical operations**. The
227-cell loader-admissible source contains initial `j@0`, 80 no-ops,
`i@81` reading opcode **`M[121]=90`**, then native `/@91`, `<@92`,
`i@93`. The first input/output pair advances guest D to address 124,
so `i@93` reads a **different** graphical opcode `M[124]=104` and
branches to `/@105`, `<@106`, `v@107`. The normative VM fetches and
executes both indirect instructions, consumes exactly two inputs, echoes
both bytes in order and halts after **88 actual guest steps**. Each
indirect jump's mandatory XLAT2 targets code, never bytecode.

A separate 102-cell, 38-byte SHA-256-bound CEB2 graphical descriptor
occupies positions 125–226; all 102 original three-bit ordinals are
re-encoded for their new loader addresses. Every word of the descriptor
remains unchanged after actual two-operation guest execution. Independent
host admission reconstructs exact descriptor bytes from the *supplied*
source and rejects unsupported pair counts, changes to code or either
opcode, all loader-valid alternate opcode glyphs, mutations of data and
foreign canonical source identity.
A separate adversarial VM run changes *only* the second opcode glyph from
104 to another loader-admissible byte, 87, at position 124. The first
real guest read/output remains unchanged, but `i@93` now relocates C to
88 rather than 105 and encrypts a different physical code cell. The
independent source verifier rejects the mutated image before publication.
This proves the second branch depends on actual resident opcode data, not
a staged host decision or an emulated dispatcher. Host admission, not the guest,
authenticates the original two-pair program and selected profile.

Compared with an independently emitted **two-pair** direct baseline, real
VM traces for `[0,255]`, `[255,0]`, `[128,129]` agree in exact stdout,
input consumption and termination. Separate canonical capsules executed
by the *general* Malbolge CLI likewise agree on `[0,255]` and `[255,0]`
with exact **88 vs 5 step** receipts. The guest code is **227 cells**
versus direct **5 cells**: +222 source cells and +83 executed steps for
an equivalent successful two-byte workload. This is another **negative
small-program cost result**, not a demonstrated compression speedup.

Additional full-state replay cases use six input streams: empty, one byte
(0 or 255), exactly two bytes, and three or four supplied bytes. Each
comparison starts from a fresh validated source-memory checkpoint rather
than from self-encrypted guest state. Normative VM output and consumed
input counts agree for EOF, short input and trailing bytes; neither guest
consumes more than two bytes. The tests also sample protected CEB2 memory
after each execution. This confirms a wider bounded I/O contract without
claiming an exhaustive input-stream or general-C semantics proof.

Importantly, the two literal graphical opcode encodings are hand placed
at different phases; this is an **unrolled two-operation guest program**.
It has no count-driven repeat loop, generic opcode decoder, on-guest
CEB2 verification, bounded-loop termination, or independently established
performance benefit for larger programs. The compiler P2 TODO remains
open pending a reusable interpreter and equivalent multi-operation study.

## Status

No **reusable** VM-resident bytecode interpreter has been implemented.
The executable v6/v7 research probes prove one and two hand-placed guest
opcode dispatches, but no generic decoding, count-driven loop, in-guest
source verification or compiler integration. The small equivalent input
workloads have strictly worse source-cell and guest-step counts than direct
lowering; no compilation-time, memory or verification-cost advantage has
been demonstrated. The P2 adoption criterion is not satisfied.
