# Historical Malbolge Semantics Specification

## Status

Active interpreter-authority contract

## Purpose

- Status: Active interpreter-authority contract
- Planning identity: `historical-malbolge-semantics-specification`
- Last reviewed: 2026-08-05

## Scope

This document governs the following declared TODO scope:

- `src/interoperability/historical-malbolge/`
- `docs/technical/specification/`
- `src/specification/formal-model/math/specification/`

## Current Behavior

### Authority

Defined and reproducible behavior of Ben Olmstead's original C interpreter is
the semantic authority for `malbolge-1998`. The preserved source at
`src/interoperability/historical-malbolge/adapter-outbound/main.c` is immutable
primary executable evidence.

The 1998 prose remains a primary historical source and an explicit comparison
model. Where it contradicts defined interpreter behavior, the interpreter wins.
Ben Olmstead's 2014 interview supports treating behavior outside graphical
ASCII as intentional and identifies the corresponding prose as erroneous. The
interview's colloquial phrase “stopping execution” does not replace the exact
control flow in the preserved source: the original loop executes `continue`
before decode, encryption, or pointer advancement. Portable bounded APIs model
that exact defined behavior as one non-progress step rather than guest

termination.

Historical host-C undefined behavior is not authoritative. The safe contract
below rejects or explicitly defines loader underflow, invalid encryption-table
indices, locale classification, text-mode translation, integer-width, and memory
model boundaries.

### Machine State

Let

\[ W = 3^{10} = 59049. \]

A classic word is an unsigned ten-trit value in `0..=59048`. Classic memory is
exactly `W` words. The machine state contains accumulator `A`, code pointer `C`,
data pointer `D`, memory `M`, an input byte stream, and an output byte stream.
All three registers begin at zero.

The normative ternary rotate and crazy operation are defined by the equation
source
`src/specification/formal-model/math/specification/malbolge-1998.tex`.

### Loading

The six C-locale whitespace bytes `09`, `0A`, `0B`, `0C`, `0D`, and `20`
(hexadecimal) are ignored and do not consume memory. Each remaining source
character is checked using its loaded position `i`:

```text
xlat1[(source_byte - 33 + i) mod 94]
```

The decoded result must be one of:

```text
j i * p < / v o
```

Source bytes are loaded sequentially. Remaining memory is filled by repeatedly
applying the crazy operation to the previous two cells.

Modern tooling defines the source representation deterministically as those six
whitespace bytes plus graphical ASCII source bytes `33..126`. Inputs for which
the historical prose lacks enough information to construct the required
two-cell memory recurrence are rejected rather than resolved through host C
behavior.

### Decode

If the current cell is outside graphical ASCII `33..126`, one requested
classic step returns `Continued` without changing registers, memory, I/O, or
termination.
A bounded run therefore exhausts its budget rather than hanging the host.

For a graphical current cell:

```text
decoded = xlat1[(M[C] - 33 + C) mod 94]
```

A decoded character not listed below is a no-op.

### Instructions

### `j`

```text
D := M[D]
```

### `i`

```text
C := M[D]
```

### `*`

Rotate the ten-trit value at `M[D]` one place to the right and store the result
in both `M[D]` and `A`.

### `p`

Apply the normative tritwise crazy operation to the word at `M[D]` and `A`, then
store the result in both `M[D]` and `A`.

### `<`

Write the low byte of `A`, defined as `A mod 256`, to the output stream. This is
the original interpreter operation associated with the decoded `<` byte.

### `/`

Read one input byte into `A` as an unsigned value in `0..=255`. End of input
uses the classic maximum word `59048`. This is the original interpreter
operation
associated with the decoded `/` byte.

### `v`

Terminate the machine immediately.

### `o`

Perform no instruction-specific operation.

### Self-Modification

After every non-halting instruction, the instruction at the current code pointer
is encrypted through the 94-character `xlat2` table described by the 1998
specification. The resulting character replaces the current cell.

The `i` instruction changes `C` before this encryption step. Therefore the
encryption target is the resulting code pointer, not necessarily the cell that
contained the decoded `i` instruction.

The encryption table is defined only for graphical ASCII values `33..=126`. If
a pointer-changing instruction exposes a non-graphical encryption target, modern
VMs report `UnsupportedInterpreterBehavior` before table access and do not
partially commit the transition. Historical out-of-bounds C behavior is not
portable semantics.

### Pointer Advancement

After a non-halting instruction and its self-modification, both `C` and `D`
advance by one with classic-word wraparound:

```text
C := (C + 1) mod 59049
D := (D + 1) mod 59049
```

### Observation Model

Interpreter conformance compares:

- input consumption and EOF handling;
- output values and order;
- termination;
- register and memory transitions where traced; and
- loader acceptance or rejection.

Host allocation strategy, C integer types, buffering, locales, text-mode file
translation, and historical implementation accidents are not guest semantics.

### Implementation Freedom

A conforming VM may use Rust, C, SIMD, JIT/AOT compilation, GPU kernels,
clusters, lookup tables, packed ternary forms, or other implementations. Those
choices are correct only when their observable state transitions implement this
interpreter-authority contract.

This separation is deliberate: the language semantics remain small and stable
while execution and compiler algorithms may be optimized aggressively.

### Historical Interpreter Role

The preserved interpreter is the primary semantic source for portable,
reproducible classic behavior. It is also retained for provenance, sanitizer
research, and discovery of host-C boundaries. The modern implementation does not
edit it or invoke its undefined behavior.

The prose specification remains available through
`ExecutionMode::Specification` for comparison, research, and migration analysis.
It does not override interpreter authority for `malbolge-1998`.

## Invariants

- The interpreter-authority contract defines loader behavior, registers,
  memory, instruction decode, crazy operation, rotate, I/O, self-encryption,
  increments/wrap, and halt/error behavior as explicit state transitions.
- The authoritative rule is deterministic, versionable, and excludes
  undocumented host behavior.
- The declared scope contains no unresolved placeholder implementation or
  undocumented workaround required for this objective to function.

## Failure Behavior

- Unsupported, unverified, or contradictory behavior remains explicit; silent
  semantic fallback is not accepted.

## Verification

- Expected durable artifact surface:
  `src/interoperability/historical-malbolge/`,
  `docs/technical/specification/`, and `math/`.
- Required evidence: reviewed authority text plus deterministic
  parser/schema/governance tests for the declared boundary.
- Executable evidence includes exhaustive word, rotate, crazy, encryption,
  loader, and successor domains plus classic/profiled differential execution.

## References

- [Specification Authority And Malbolge
  Evolution](../adr/specification-authority-and-malbolge-evolution.md)

- `docs/bibliography/specifications-and-standards/malbolge/malbolge-1998.md`
- `docs/bibliography/specifications-and-standards/malbolge/`
  `ben-olmstead-2014-interview.md`
- `src/interoperability/historical-malbolge/adapter-outbound/main.c`

### Governing ADR Paths

- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
