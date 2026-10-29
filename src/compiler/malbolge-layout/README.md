# Malbolge layout and encoding

The initial executable target encoder admits only bounded straight-line
machine operations: `NoOperation`, profile `InputWord`/`OutputByte`, and final
`Halt`. It can also emit either a single `RelocateDataPointer` (`j`) prologue
followed by real `RotateData` (`*`) and `CrazyData` (`p`) operations, **or**
one forward `JumpForward` (`i`). There is no conditional branch, backward
jump, or executable external guest helper in this subset.

The encoder assigns code addresses starting at zero and uniquely inverts the
normative profile decoder over all 94 graphical source bytes. Independent
admission checks every emitted code byte, selected profile ID/fingerprint,
exact positions, length, and terminal halt. No translation table is copied.

Data relocation is necessary before rotate/crazy: without it, code and
data pointers advance together and mutate the currently executing cell.
A single `j` may occur at any code position after no-op/raw byte I/O, but
before all rotate/crazy steps and without a code-pointer jump. The VM still
has `D == C` at that point, so the original graphical source byte at the
chosen phase becomes the new data address. Requiring the complete emitted
source length to be at most that exact byte ensures subsequent data writes
stay outside the code region. Later phases can encode a much larger data
base than the first source cell, admitting longer safe executable layouts.
Missing, duplicate, or potentially aliasing relocation is rejected.
A separate exhaustive decoder-phase test enumerates all safely addressable
rotate/crazy placements at positions 1 through 93, under both declared
profiles, and independently checks the encoded instruction and execution
witness lengths. It complements the longer real-VM boundary regression.

The forward jump can occur after nonmutating operations while the original
code and data pointers still agree. The VM reads the graphical jump cell
through `D`; its encoded byte plus one must equal the claimed forward target.
Every skipped position must be graphical no-operation padding, and the target
must remain inside the emitted source. The VM also encrypts the skipped
`target - 1` cell on the jump step; no such cell may be reached later. To
avoid unjustified data-pointer assumptions, jumps cannot mix with the
relocation/arithmetic subset. Invalid jump targets, backward motion, a
second jump, or effectful skipped code are rejected before publication.

Every admitted layout now also exposes an ordered, deterministic control-flow
witness: the exact reachable source-code positions (including the final halt)
and the exact code cells encrypted after each nonhalt VM step. A jump's
post-step encryption target is `target - 1`, not the jumped-from address;
real VM tests compare the witness against stepwise code-pointer and XLAT2
memory observations on both profiles. The record deliberately excludes
rotate/crazy *data* writes, input-dependent accumulator values, and any claim
of program-wide semantic verification.

The source has two to 4096 cells (with a stricter bound for relocated data),
contains exactly one final halt, and carries the canonical selected profile
identity. Real current and historical profile-VM tests prove byte I/O,
rotate/crazy execution, forward skip-to-target semantics, halting, and
invalid placement rejection.

This is **not** a C-to-Malbolge compiler. Arbitrary ternary-IR operations,
general control-flow jumps, data/global layout, calls, runtime linkage,
source maps, full mutable code-state planning, and final capsule production
remain open.
