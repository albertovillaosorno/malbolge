# Malbolge layout and encoding

The initial executable target encoder admits only bounded straight-line
machine operations: `NoOperation`, profile `InputWord`/`OutputByte`, and final
`Halt`. It can also emit a single `RelocateDataPointer` (`j`) prologue
followed by real `RotateData` (`*`) and `CrazyData` (`p`) operations. There is
no code-pointer jump or executable external guest helper in this subset.

The encoder assigns code addresses starting at zero and uniquely inverts the
normative profile decoder over all 94 graphical source bytes. Independent
admission checks every emitted code byte, selected profile ID/fingerprint,
exact positions, length, and terminal halt. No translation table is copied.

The data relocation is essential: without it, the VM increments its data
pointer alongside the code pointer and rotate/crazy can overwrite the
currently executing instruction. A single `j` at position zero redirects
`D` through the original graphical code cell. This bounded slice requires
the emitted code length not to exceed that cell's value, so subsequent
rotate/crazy data accesses remain outside the source code region. Missing,
late, or potentially aliasing relocation is explicitly rejected.

The source has two to 4096 cells (with a stricter bound for relocated data),
contains exactly one final halt, and carries the canonical selected profile
identity. Real current and historical profile-VM tests prove byte I/O,
rotate/crazy execution, halting, and invalid placement rejection.

This is **not** a C-to-Malbolge compiler. Arbitrary ternary-IR operations,
control-flow jumps, data/global layout, calls, runtime linkage, source maps,
full mutable code-state planning, and final capsule production remain open.
