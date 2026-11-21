# Physical Reentry State Contract

## Status

Bounded N15 compiler-layout evidence, 2026-11-21. The original mutable C23
EOF checksum remains unlinked. No source-C checksum guest was published.
Executable witness: `tests/compiler_physical_reentry.rs`.

## Why a Return Address Is Not a Loop

Malbolge execution encrypts code after every committed non-halt step.
Returning to the same code address, or matching a positional decoder phase,
does not restore the accumulator, data pointer, mutable memory or I/O state.

`observe_physical_reentries` loads canonical graphical source into the
normative profile VM and observes genuine entries **before** instruction
fetch. The analyzer admits 2-4 visits, a 1-2048-step budget, at most 4,096
source cells and at most 2,048 stdin bytes. It never synthesizes VM output,
overwrites the guest image or restores registers.

Each interval records exact `A/C/D` registers, stdin cursor, stdout length,
all reached reads (including EOF), emitted bytes, reached `p`/`*` writes,
changed XLAT2 writes and a sorted net memory-difference journal. The
chronological data-read and `p`/`*` write-address lists preserve the actual
helper footprint, including idempotent stores and `i`/`j` reads.
Each observed interval also projects its reached VM traces through the
existing portable v6 effect-IR checker. Its sorted `memory_live_ins` and
`register_live_ins` identify values actually read before a first committed
write. This includes code fetch, data and XLAT2 operand reads. A separate
source-loaded VM replay checks that the effect-IR dependencies match its
trace projection; full source-memory snapshots verify their entry values.
The journal tracks the first before-value and last after-value even when a data or
encryption instruction writes the same address multiple times. It need not
copy the entire N15 image at every reentry.

`core_state_restored` requires identical registers and no net changes
anywhere in memory. `exact_closed_cycle` additionally requires unchanged
input consumption and output length. The less restrictive
`live_entry_restored` checks just the v6-proven register and memory
live-ins; `fixed_input_replay_preconditions` also requires the same input
cursor. Those predicates permit output growth or changes to dead cells, but
only describe this *observed fixed-input region*. Neither is a source-C
loop certificate, a translation proof or a promise about different inputs.

Since source, profile and complete input are fixed, and the observed
interval has no termination, the stricter `exact_closed_cycle` equality
suffices for deterministic *fixed-input* repetition.
It does not prove a useful dynamic byte-stream loop or C source translation.
A stream-processing loop needs a separately proved parametric live-state
relation allowing specified data, code and I/O changes.

## Real N15 Negative Witness

A source-loaded 132-cell signed second-input EOF classifier is re-encoded
at C71 (first-pass `<`), C104 (first-pass `o`) and C112 (first-pass `p`).
No host-provided guest state is injected. Three streams `03 04 05`,
`00 ff 80` and `ff 00 01` independently reach C71 a second time
within 190 guest steps.

| Property | First C71 entry | Reentered C71 |
| --- | ---: | ---: |
| Completed steps | 71 | 141 |
| Accumulator A | 134 | 4,783,015 |
| Code pointer C | 71 | 71 |
| Data pointer D | 141 | 7,174,359 |
| Input bytes consumed | 2 | 2 |
| Output bytes committed | 1 | 3 |

The intervening interval changes **78 memory words** in net, with
**8 executed data-writing instructions** and **70 changed XLAT2 writes**.
It emits `86 9a` without another input event. All three streams have
the same measured boundary values. A separate normative execution clones
the complete 14,348,907-word memory at the two actual entries and checks
the journal against the full before/after difference, word by word. A separate
trace replay checks the ordered data-read and data-write address lists and
the count of all eight reached `p`/`*` operations. The portable v6
register-masked effect projector agrees with the source-loaded physical
window's memory live-ins on two independent binary streams. Its observed
entry dependencies are not restored at C71, so the fixed-input replay
preconditions reject this candidate.

This is a physically verified return, but not an exact restored core
state. Empty input and `03` alone do not return to C71; seeking a third
C71 visit on `03 04 05` instead encounters an actual invalid transition,
reported as a guest error, not fabricated as another return. Malformed
source and finite-request bounds also fail closed.

## Reproduction and Next Gate

Run with the pinned compiler and normative VM:

```sh
cargo test --test compiler_physical_reentry
python3.14 -B -m unittest tests.test_eof_checksum_pipeline -v
```

If the machine's `/tmp` quota blocks native Clang, set `TMPDIR` to a
writable ignored directory before launching the Python test. This only
redirects temporary host files; it does not change guest oracles.

The next P2 physical linker must establish a valid *parametric* entry/exit
relation for a stateful source-C operation, including live memory versions,
control, I/O and the real instruction/encryption effects. The unchanged
seven-block C23 mutable checksum still needs physically linked arithmetic,
phi transfer, branching, EOF and byte output. Returning to C71 does not
retire that acceptance gate.
