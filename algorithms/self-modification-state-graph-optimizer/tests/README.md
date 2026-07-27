# Research Tests

`exact.rs` owns the first correctness baseline: identical execution replays must
deduplicate exact nodes/edges, a forced constant digest must not merge distinct
input states, and the research graph admits specification mode only.

The first reduced-state fixture exhausts all 256 possible consumed first-byte
values for `cbO` (`<`, `<`, `v`) and proves consumed-prefix contents disappear
from the future key only after the common second input overwrites `A`.

Further reduced-state tests belong here only after they state a falsifiable
domain and compare against the exact baseline.
