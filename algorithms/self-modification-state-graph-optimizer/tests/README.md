# Research Tests

`exact.rs` owns the first correctness baseline: identical execution replays must
deduplicate exact nodes/edges, a forced constant digest must not merge distinct
input states, and the research graph admits specification mode only.

Future reduced-state tests belong here only after they state a falsifiable domain
and compare against the exact baseline.
