# Malbolge layout and encoding

The first source-emitting slice is deliberately bounded to straight-line
`NoOperation`, `InputWord`, `OutputByte`, and terminal `Halt` machine
instructions. It assigns consecutive code positions starting at zero, inverts
the normative profile instruction decoder over the 94 graphical source bytes,
and independently checks exact position-sensitive decoding before returning
an admitted graphical `.malbolge` stream.

The emitted stream has no data layout, branches, jumps, allocations, runtime
linkage, or ternary-IR program realization; it must not be marketed as C
compilation. The layout requires two to 4096 code cells, terminates exactly
once at the end, and carries the canonical selected profile identity and
fingerprint. Arbitrary byte strings cannot bypass independent admission.

Real VM integration tests check both accepted historical and current profiles.
Nonlinear control flow, mutable code-state planning, guest runtime binding,
full source maps, and complete semantic target verification remain unfinished.
