# Self-Restoring Malbolge Runtime: Architecture Exploration Ledger

## Status and Scope

**Research plan, not a completed result.** Initial review: 2026-11-21.
Stable task: `self-restoring-runtime-architecture-exploration`.
Owning TODO: `docs/todo/open/research/self-restoring-runtime-architecture-exploration.mdc`.

Owner-directed goal: allow *wide* exploration of architectures for a
hand-written, reusable Malbolge execution base (dispatcher/kernel-like
entry), verified operation library and a way to prepare a compatible
return state. Prioritize direct physical experiments, including brute-force
search; theoretical elegance is optional, normative guest validity is not.
This study is a **non-blocking parallel investigation**, not a replacement
for the existing mutable-C/EOF P2 compiler route. It must not claim an
infinite loop or universal runtime from finite evidence.

## Central Problem, Without a Preferred Answer

Malbolge code changes when executed, and a jump can also encrypt its
*destination*. Restarting a code pointer alone does not restore the
data pointer, accumulator, live memory, input cursor, output state or
previously encrypted instructions. Repeated control flow is therefore
possible but does not by itself establish a reusable operation.

Can we construct a small **base state/entry contract** that operations can
return to indefinitely *in principle*, or repeatedly for a verified finite
range, without demanding that the entire physical memory image revert to its
original value? The base may be one physical site, an A/B alternation,
a longer orbit, a reconstructed region or a succession of equivalent copies.
An application returning from a game to a menu is the conceptual analogy:
its *interface contract* must recover, not necessarily every historical
byte. This analogy does not establish practical DOOM execution in Malbolge.

## Full Hypothesis Ledger

Each entry is explicitly labeled. Preserve rejection receipts instead of
silently replacing them with a favored theory. New hypotheses may be added
without changing the frozen acceptance of an existing experiment.

<!-- markdownlint-disable MD013 -->
| ID | Hypothesis / question | Evidence classification | Discriminating test |
| --- | --- | --- | --- |
| H01 | Author a small guest base by hand, freeze it and reuse its verified micro-operations | **Proposed**, not validated as a reusable base | Physical source-loaded byte-I/O baseline; mutate one code operand |
| H02 | Decoder phase repeats every 94 positions; initial recurrence phase divides six; combined initial structural period is 282 | **Established structural property**, not guest-state periodicity | Enumerate the 94 phases and recurrence classes independently |
| H03 | Two complementary 141-cell halves can preserve initial decoded operations with opposite graphical-byte recoding | **Verified phase identity**; physical 141-byte copies alone do not preserve full state | Check all 94 phase offsets/eight admitted opcodes |
| H04 | Seed future return operands backward rather than ask executed instructions to magically restore a prior target | **Finite positive execution**: three `i` backedges | Source/loader-derived targets with altered-operand negative |
| H05 | A physical return to a previously executed cell implies a reusable cycle | **Rejected for the existing 564-cell fixture**; live D, code version and I/O differ | Compare full boundary register, code/data and I/O state |
| H06 | A central dispatcher repairs its own required state after each operation | **Open hypothesis** | Return two distinct operations to a base with compatible entry contracts |
| H07 | Each operation prepares/repairs the base before returning | **Open hypothesis** | Compare cleanup cost and state invariants to H06 |
| H08 | A and B deliberately rebuild each other's next executable version | **Open hypothesis** | Two-phase alternating trace with a third *compatible* full entry state |
| H09 | XLAT2 finite mutation orbits can provide an instruction-recovery schedule | **Open architectural hypothesis**; per-byte periods require explicit target-VM verification for candidate sites | Enumerate actual decoded operations at each visit; verify useful rather than merely repeated bytes |
| H10 | Fresh forward-only copies are simpler than repairing old instruction cells | **Open hypothesis** | Equal-budget clone-chain vs restored-block search with source-size accounting |
| H11 | A branch should select among independently validated executable landing sites instead of using raw EOF-derived words as code addresses | **Open hypothesis** motivated by negative direct EOF jump | Real guest EOF-vs-byte dispatch with legal encryption targets |
| H12 | There is a natural recurrence near 1,000 steps/positions, indicated by observed return increases +6, +14 | **Speculative, unsupported**: those targets were hand-seeded | Frozen source/state replay through a predeclared horizon; do not extrapolate increments |
| H13 | Numbers 14, 141, 282 or five-trit representations reveal a useful shorter state basis | **Open numerical heuristic**: five trits encode 243 values; 141 is not a proven minimum | Exhaustive phase/representation comparison with explicit correctness oracle |
| H14 | Explore the semantics of every one of ~14.35 million N15 cells once, then reuse profiles | **Conditionally useful** for initial position classes; **not** complete-state enumeration | Compare phase-indexed initialization with mutated-state traces and revisit invalidations |
| H15 | Brute-force search over a tiny honest candidate grammar can outperform hand reasoning for a usable base or repair stub | **Open empirical comparison** | Same grammar, fixed nodes/time, raw exhaustive vs seeded/inverse/heuristic schedule |
| H16 | A semantic live-in/live-out contract may be repeatable even if the physical memory image is not identical | **Open strongest systems hypothesis** | Two different traversals with exact required-state equivalence and varied I/O |
<!-- markdownlint-enable MD013 -->

## Already Executed: Positive and Negative Evidence

The following are **pre-existing** experiments, not new results from this
research plan. Their referenced source and tests remain the authorities.

<!-- markdownlint-disable MD013 -->
| Evidence ID | Verified observation | Boundary and caution |
| --- | --- | --- |
| E01 | A source-loaded N15 experiment executes two physical 282-cell input/fold/output envelopes for five EOF/binary streams | `tests/compiler_282_phase_blocks.rs`; same phase does not preserve mutable state |
| E02 | A one-cell C281 `i` substitution lands at C46 rather than C0 or C282 | Only that physical grammar fails; no universal impossibility |
| E03 | An exact 141-position graphical-byte half-turn preserves each initial admitted decoded opcode | Decoder identity, not general code relocation after self-encryption |
| E04 | A 564-cell guest achieves C281 to C100 and C281 to C106 on successive passes | Two physically verified returns, not a reset |
| E05 | A modified loader-backed source achieves a third C281 return to C120 by deriving M639=119 | Five-input 640-step finite trace; later returns unproven |
| E06 | Return boundary states have C/D pairs (100,282), (106,464), (120,640); live code and I/O differ | Specifically refutes treating this candidate's returns as identical state |
| E07 | A real 104-cell program revisits source cells and reads/outputs input under bounded execution | `tests/bounded_revisit_layout.rs`; revisited input/output cells mutate and do not imply a reusable service |
| E08 | A physical EOF-zero predicate and byte-vs-EOF data selection have been exercised | `docs/technical/compiler/malbolge-layout-and-encoding-backend.md`; not yet a general code branch |
| E09 | Replacing C25 `*` with `i` after EOF classification produces invalid/non-graphical targets | Rejects this specific direct jump, not a table dispatch or different program |
| E10 | The complete stateful C23 EOF checksum has not passed source-to-guest publication | P2 remains open; no research result here changes that acceptance |
<!-- markdownlint-enable MD013 -->

### Core historical evidence paths

- `docs/technical/compiler/141-half-phase-return-evidence.md`
- `tests/compiler_141_half_phase_returns.rs`
- `tests/compiler_282_phase_blocks.rs`
- `tests/bounded_revisit_layout.rs`
- `docs/technical/compiler/malbolge-layout-and-encoding-backend.md`
- `docs/technical/compiler/parametric-guest-byte-stream-emission.md`
- `docs/todo/open/compiler/parametric-guest-byte-stream-emission.mdc`
- `src/runtime/virtual-machine/domain/instruction.rs`
- `src/runtime/virtual-machine/domain/profile_machine.rs`

## Architectural Candidates to Attempt Without Prior Preference

**A. Minimal fixed base:** preserve a tiny hand-assembled dispatcher and
return to a verified live-in contract after each command. Investigate
operand-selected legal branches, scratch-data separation and compact
recovery code.

**B. Base repaired by operations:** each operation ends with a correction
stub. Explore whether stubs can reconstruct required code bytes and data
pointers before returning without destroying their own next execution.

**C. Base repairs itself:** operations return under a modest contract and
a shared dispatcher normalizes the rest. Compare local per-operation repair
against amortized centralized repair.

**D. Alternating or many-phase code:** two A/B halves, mutation orbits,
141/282 position classes or a longer state cycle. Verify *actual* instruction
versions at visits, not only a nominal position or a byte-period claim.

**E. Unrolled or regenerated continuation:** advance through fresh code
copies or prepare a new copy from old state. Measure memory consumed per
operation and prove when the finite address space would become limiting.

**F. Table-guided input dispatch:** derive an EOF/byte predicate in guest
data, then select among prevalidated executable return targets. Reject raw
input/EOF-derived addresses that are not legal encrypted code positions.

**G. Search rather than intuition:** enumerate loader-valid source words,
short instructions and bounded register/memory contracts. Compare raw
exhaustive search, seeded pseudorandom order, inverse/forward meet-in-the-
middle, canonical-state pruning and optional learned proposals on an
*identical frozen candidate language*. The raw brute-force baseline is
mandatory for comparison; nothing requires the clever strategy to win.

A manually assembled source can be the **immutable reference example** for
all seven investigations. Discovering an unusual mechanism is welcome even
if it does not resemble the existing compiler pipeline.

## How Each Experiment Must Be Logged

Each experiment record includes: stable `EXP-...` ID, date, author/process,
statement of a falsifiable hypothesis, exact N15 or historical profile,
source bytes/hash, loader configuration, state signature (including C/D/A,
selected live code/data and input/output position), instruction budget,
source length, candidates tested, CPU wall-time and memory ceiling, search
ordering and random seeds, verifier build/identity, raw trace paths,
positive/negative expectations, outcome and a narrow generalization claim.

Use four clearly different verdicts: **verified finite success**,
**bounded rejection**, **inconclusive or unavailable**, and **unexecuted
hypothesis**. No proxy host calculation or fabricated guest state is a
verified guest result. Predeclare the budget of each run; do not silently
increase it after observing a near miss. Publish new, independently scoped
runs if expansion is scientifically useful.

## First Frozen Comparison to Complete This Research TODO

1. Freeze a tiny source-loaded, manually authored guest with byte I/O and
   at least one altered-code negative replay. Record source and VM receipts.
2. Freeze **three distinct** base/return architectures and attempt one
   bounded trial per family, accepting correct negative search receipts.
3. Compare literal exhaustive enumeration against at least one alternate
   search ordering on a *shared* candidate grammar. Record all candidates,
   verifier rejects, memory/time caps, seeds and first verified hit, if any.
4. Replay the five pre-existing binary/EOF input streams for any claimed
   input-dependent operation. Inspect exact return entry-state contracts at
   three attempted traversals and one corrupted-operand negative.
5. Produce a compact decision matrix: viable, rejected within declared
   bounds, or unresolved, plus an evidence-specific recommendation.

The research can **finish without a functioning infinite loop**. A negative
or inconclusive outcome is valid if those experiments were honestly
completed and preserved. Future more ambitious experiments are separate
follow-on tasks, not unbounded hidden acceptance criteria for this one.

## Research Independence and Promotion Rules

This study does not touch the normative VM semantics or loosen independent
compiler/translation verification. Research results may inform P2 layout,
P4 state-aware linking and P6 reusable block search **only after** their
actual assumptions are carried through explicit product contracts. This
is not a P2/P5 release gate and cannot replace the full C checksum.

Any substantial executable **algorithm research** derived from this plan
will receive a separately mirrored stable ID under
`docs/research/algorithms/` and `algorithms/`, as required by
`docs/research/adr/research-evidence-and-algorithm-mirror.md`.

## Initial Decision

**Undetermined.** The position-phase identity and finite return machinery
are experimentally useful, but no existing evidence establishes a
repeatable base-state contract or an optimal runtime architecture. The
next discriminating evidence must compare actual live-state recovery,
not simply a larger count of backward jumps.
