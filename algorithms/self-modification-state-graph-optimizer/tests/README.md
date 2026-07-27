# Research Tests

`exact.rs` owns the first correctness baseline: identical execution replays must
deduplicate exact nodes/edges, a forced constant digest must not merge distinct
input states, and the research graph admits specification mode only.

The first reduced-state fixture exhausts all 256 possible consumed first-byte
values for `cbO` (`<`, `<`, `v`) and proves consumed-prefix contents disappear
from the future key only after the common second input overwrites `A`.

Further reduced-state tests belong here only after they state a falsifiable
domain and compare against the exact baseline.

Terminal-state fixtures vary halt-source memory, registers, and input while
requiring one terminal future key; a separate fixture proves live machines are
not admitted to that reduction.

`c.rs` owns current-profile exact-checkpoint evidence: one full current checkpoint
replay must deduplicate, while two unequal current checkpoints remain distinct
under a forced constant digest.

`d.rs` compares complete before/after memory for all eight instruction families
in classic and current profiles. It proves the per-step memory delta never
exceeds two cells and demonstrates both the two-cell and zero-cell boundaries.

`p.rs` proves persistent current memory reconstruction from one complete root and
trace deltas, verifies empty deltas do not add patch depth, and rejects a forged
`before` value before it can enter the persistent chain.

`i.rs` verifies the four-level radix overlay against complete current-profile
checkpoints, inserts 4096 distinct overrides while preserving root fallthrough,
and rejects a forged `before` value before any indexed update commits.

`s.rs` proves incremental full-state reconstruction and exact replay
deduplication, forces all states into one digest bucket without false merge, and
rejects independently allocated roots as foreign lineage instead of performing a
full-root comparison.

`o.rs` proves persistent output materialization, equality of independently built
identical branches, inequality of different branches, and safe 65,536-byte
history destruction/materialization without recursive stack growth.
