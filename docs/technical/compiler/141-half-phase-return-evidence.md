# Complementary 141-Position Source Phases and Finite Code Returns

## Status

Bounded, positive **N15 machine-execution research** on 2026-11-21. This is
not an infinite loop, source-C lowering, state-independent relocation,
P2 milestone completion, a P4 linker, or a reusable P6 catalogue entry.
The exact executable witness is
`tests/compiler_141_half_phase_returns.rs`.

## Hypothesis and Exact Structural Finding

The canonical N15 instruction decoder depends on the graphical code byte and
the code address modulo 94. The automatically filled *unexecuted* memory
has a separate, at-most-six-step ternary recurrence phase. Their least common
period is 282. Half of that period, 141, shifts the decoder by 47 phases and
the generated-memory recurrence by three phases. It does **not** preserve an
unmodified graphical instruction byte's opcode.

For a graphical byte in 33 through 126, recoding by adding 47 modulo the
94-character graphical domain before placing it 141 positions later preserves
the decoded opcode. Recoding twice recovers the original graphical byte.
`all_opcode_half_turn_phases_are_exact_but_not_identical_source_bytes`
checks each of the 94 positions and all eight loader-admitted operations,
as well as the involution for all 94 graphical bytes. This is a fact about
**initial code decoding**, not a mapping between complete, evolved VM states.
Neither 141 nor 282 is a universal semantic-cycle length; a five-trit word
has 243 values, not 141. The 14,348,907-word N15 memory does not have a
282-aligned wraparound.

## Frozen Guest Experiment

- Target: current canonical N15 profile, real normative `ProfileMachine`.
- Source: **564 loader-valid graphical cells**, of which C0..C280 and C281
  form two 141-cell active envelopes; the later source is a nonexecuted data
  table for the finite path, not an unbounded self-replicating code region.
- First 140 relative instruction sites: **139 exact half-turn-reencoded
  opcode pairs**. One incompatible double-visit position deliberately uses
  different operations. B's last code cell C281 is the explicit `i` return
  rather than a copy of A's final no-op.
- Bounded executable path: C0..C281, then C100..C281, then C106. Exactly
  **465 VM steps** per complete positive case, with a budget-exhausted
  result by design. The case does not assert termination or stability after
  that frozen prefix.
- Exact first backedge: C281 executes real `i`, with D281 reading its own
  graphical source value M281=99; the VM encrypts its target code cell C99
  and resumes at C100 after automatic increment.
- Exact second backedge: the previous input/output, code encryption and
  unused tail preserve source M463=105; when C281 is revisited, D463 reads
  that value. The VM encrypts target C105 and resumes at C106. This is
  **backward-designed operand placement**, not a host callback or an assumed
  pointer reset. The first return has D281; the second has D463.
- The only physical I/O code effects originate in the guest. The fixture's
  expected operation sequence comes from the frozen source, phase/XLAT2
  transformations and planned code path, not from the VM's emitted bytes.
  It independently checks the raw bytes, EOF, consumed input, output,
  registers and the two jump operand/encryption addresses.
- Exactly five fixed input streams are replayed: empty, `00`, `80`, `ff`
  and `01 02`; each requires the same two physical code-pointer returns.
- Negative control: replace graphical M463=105 with another loader-valid
  value, 106. The VM then returns to C107 rather than C106. A matching
  first return alone cannot certify the planned second return.

## Executed Validation

The repository's pinned Cargo command
`cargo test --test compiler_141_half_phase_returns -- --test-threads=1`
passed **3 tests** (phase identity, positive five-stream N15 paths, negative
changed-operand refusal). This is a reproducible local execution receipt;
the full Jig gate and the unrelated complete C23 mutable EOF checksum are
separate acceptance obligations.

A separate initial off-repository N15 prototype also demonstrated the first
C281-to-C100 reentry in 283 real guest steps. The later two-return test is
the durable authority; the `/tmp` prototype is not needed for reproduction.

## What the Result Does Not Establish

No unbounded loop was synthesized. The two returns lead to **different**
physical A entry addresses and different evolved code/memory conditions.
The third and later returns have not been verified. An identical decoded
instruction at two address phases is not an interchangeable code fragment
once encryption, data-pointer changes, source input and memory writes are
included. This experiment performs guest byte I/O and control, not the
original seven-block C23 checksum's mutable arithmetic/phi/EOF loop.

## Next Bounded Synthesis Hypothesis

Use an exact **forward/backward state-contract search** instead of treating
141 as a magic cycle size. Select one source operation and a finite input
class. For each desired return entry, work backward to valid graphical
loader bytes and memory words that make `i` land at that physical address.
Then explore forward through the normative VM and reject any predecessor
that alters a required live code/data cell or diverges on its finite input
matrix. Freeze search nodes, candidate count, profile, full source/loader
identity, guest-step ceiling, sample count and positive predicate before
searching.

Require at least two distinct *complete* block traversals followed by a
**third** compatible entry, preserving the declared live-in state rather
than only code position. A true reusable cycle must separately establish a
repeatable state relation (including source-sensitive outputs and EOF),
not infer infinity from a finite repetition. Reject an unusable layout
within the declared bound; do not keep enlarging the search forever.

This follow-on belongs to P2 layout while leaving the complete source-C
checksum acceptance unchanged. Only after positive guest state contracts
exist should P4 link the blocks and P6 cache them under full state keys.
