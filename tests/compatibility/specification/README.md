# Classic Specification Conformance Fixtures

These fixtures distinguish normative 1998 Malbolge semantics from defects in
Ben Olmstead's historical C interpreter.

`spec-io-roundtrip.malbolge` is deliberately small. At loaded positions 0, 1,
and 2, the source bytes `c`, `t`, and `O` decode respectively to `<`, `/`, and
`v` through the original `xlat1` table.

Under the normative specification, input byte `0x41` therefore produces output
byte `0x41` and halts. The historical C interpreter instead treats `<` as output
and `/` as input, so it emits the initial accumulator byte `0x00`, then consumes
`0x41`, then halts. That disagreement is intentional evidence for H-001 in the
historical defect catalogue.

State-only cases in `cases.toml` describe discrepancies that should not be
forced through an ordinary source file merely to reach an artificial VM state.
In particular, a non-graphical current cell terminates under the specification
while the historical C interpreter loops without pointer progress.

The historical interpreter must never be modified to make these fixtures pass.
It is evidence of the defect; modern VMs implement the specification.

The `output-low-byte` state fixture fixes the byte-stream interpretation of `/`:
output is `A mod 256`, so accumulator `59048` emits byte `0xA8`.

The `invalid-self-encryption-target` fixture fixes the H-004 modern failure
boundary. `i` changes `C` before self-encryption; if the resulting cell is not
graphical ASCII, a conforming modern VM reports an explicit invalid transition
without reproducing or partially committing the historical out-of-bounds lookup.
