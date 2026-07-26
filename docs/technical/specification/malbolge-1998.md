# Historical Malbolge Semantics Specification

- Status: Active normative specification
- Planning identity: `historical-malbolge-semantics-specification`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Specification Authority And Malbolge
  Evolution](../adr/specification-authority-and-malbolge-evolution.md)

## Authority

Ben Olmstead's 1998 prose specification is the normative authority for the
classic machine in this repository. The original C interpreter at
`tools/malbolge/main.c` is immutable historical evidence, not the semantic
arbiter when it contradicts the written specification.

The original interpreter remains valuable for differential testing over the
intersection where its behavior is defined and agrees with this specification.
Known disagreements and C defects are cataloged in
[`historical-undefined-behavior.md`](historical-undefined-behavior.md).

## Machine State

Let

\[ W = 3^{10} = 59049. \]

A classic word is an unsigned ten-trit value in `0..=59048`. Classic memory is
exactly `W` words. The machine state contains accumulator `A`, code pointer `C`,
data pointer `D`, memory `M`, an input byte stream, and an output byte stream.
All three registers begin at zero.

The normative ternary rotate and crazy operation are defined in
[`mathematics/machine.tex`](mathematics/machine.tex).

## Loading

Whitespace is ignored and does not consume memory. Each non-whitespace source
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

Modern tooling defines the source representation deterministically as ASCII
whitespace plus graphical ASCII source bytes `33..126`. Inputs for which the
historical prose lacks enough information to construct the required two-cell
memory recurrence are rejected rather than resolved through host C behavior.

## Decode

Before execution, the current cell must be graphical ASCII `33..126`. Otherwise
the classic machine terminates immediately.

For a graphical current cell:

```text
decoded = xlat1[(M[C] - 33 + C) mod 94]
```

A decoded character not listed below is a no-op.

## Instructions

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

Read one ASCII input value into `A`.

- Line feed is numeric value `10`.
- End of input is represented by `59048`.

This is the normative input instruction even though the original C interpreter
accidentally implements `<` as output.

### `/`

Convert `A` to the corresponding ASCII output value and write it to stdout.
Value `10` is line feed.

This is the normative output instruction even though the original C interpreter
accidentally implements `/` as input.

### `v`

Terminate the machine immediately.

### `o`

Perform no instruction-specific operation.

## Self-Modification

After every non-halting instruction, the instruction at the current code pointer
is encrypted through the 94-character `xlat2` table described by the 1998
specification. The resulting character replaces the current cell.

The exact behavior of pointer-changing instructions and the post-instruction
mutation must be represented by one deterministic VM transition and covered by
state-level tests. Historical C behavior may be used as corroborating evidence
only where it agrees with the normative text and does not invoke C undefined
behavior.

## Pointer Advancement

After a non-halting instruction and its self-modification, both `C` and `D`
advance by one with classic-word wraparound:

```text
C := (C + 1) mod 59049
D := (D + 1) mod 59049
```

## Observation Model

Specification conformance compares:

- input consumption and EOF handling;
- output values and order;
- termination;
- register and memory transitions where traced; and
- loader acceptance or rejection.

Host allocation strategy, C integer types, buffering, locales, text-mode file
translation, and historical implementation accidents are not guest semantics.

## Implementation Freedom

A conforming VM may use Rust, C, SIMD, JIT/AOT compilation, GPU kernels,
clusters, lookup tables, packed ternary forms, or other implementations. Those
choices are correct only when their observable state transitions implement this
normative machine.

This separation is deliberate: the language semantics remain small and stable
while execution and compiler algorithms may be optimized aggressively.

## Historical Interpreter Role

`tools/malbolge/main.c` is retained unchanged for:

- historical provenance;
- discovering implementation/specification discrepancies;
- differential testing of semantics on which it agrees with the specification;
- sanitizer and UB research; and
- optional `legacy-ben` execution-mode tests.

It does not override the specification.

## Sources

- [Original Malbolge bibliography record][malbolge-bib]
- `tools/malbolge/main.c`

[malbolge-bib]: ../../bibliography/malbolge-and-esolangs/malbolge-1998.md
