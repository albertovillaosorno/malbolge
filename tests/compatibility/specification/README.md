# Classic Authority-Discrepancy Fixtures

These fixtures distinguish authoritative `malbolge-1998` interpreter behavior
from the contradictory written specification and from historical C undefined
behavior.

`spec-io-roundtrip.malbolge` is deliberately small. At loaded positions 0, 1,
and 2, source bytes `c`, `t`, and `O` decode to `<`, `/`, and `v` through the
original `xlat1` table.

Under authoritative interpreter semantics, `<` emits the initial accumulator
byte `0x00`, `/` consumes input byte `0x41`, and the program halts. Under
explicit `ExecutionMode::Specification`, the same program reads `0x41`, writes
`0x41`, and halts. The disagreement is intentional evidence for H-001.


`interpreter-io-roundtrip.malbolge` is the current-profile counterpart. At
loaded positions 0, 1, and 2, `u`, `b`, and `O` decode to `/`, `<`, and `v`.
`malbolge-2026.3` therefore consumes one byte, emits the same byte, and halts
while retaining 14-trit geometry and modern safe failure behavior. The fixture
does not replace `spec-io-roundtrip.malbolge`; `malbolge-2026.1` and
`malbolge-2026.2` retain that published specification-first assignment.

State-only cases in `cases.toml` describe boundaries that should not be forced
through an ordinary source. A non-graphical current cell is bounded non-progress
under interpreter authority and immediate termination under specification
comparison.

The historical interpreter must never be modified to make fixtures pass. Modern
VMs reproduce its defined portable behavior and reject its undefined C behavior.

The `output-low-byte` fixture fixes portable output as `A mod 256`; accumulator
`59048` therefore emits byte `0xA8` through interpreter `<`.

The `invalid-self-encryption-target` fixture fixes the H-004 safe boundary. If
`i` exposes a non-graphical encryption target, a modern VM reports a typed
atomic failure instead of reproducing the historical out-of-bounds lookup.
