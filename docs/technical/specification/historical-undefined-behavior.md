# Historical Interpreter Defects And Specification Discrepancies

## Status

Active historical catalogue

## Purpose

This catalogue records places where Ben Olmstead's original C interpreter is
incorrect, host-dependent, undefined, pathological, or otherwise unsuitable as
the normative language definition.

The resolution rule is simple: the written 1998 specification defines classic
Malbolge. Interpreter disagreements are implementation defects unless a later
accepted language profile explicitly changes the specification.

## Scope

This document governs the following declared TODO scope:

- `tools/malbolge/`
- `docs/technical/specification/`
- `tests/compatibility/`

## Current Behavior

### Compatibility Policy

Historical compatibility is evidence, not semantic authority.

1. Where the C interpreter is defined and agrees with the specification, it is a
   useful differential oracle. 2. Where it disagrees with the specification, the
   modern VM follows the specification. 3. Where it invokes or risks C undefined
   behavior, modern code uses deterministic specification-derived behavior or
   rejects an underspecified source boundary. 4. `legacy-ben` may emulate
   selected defects only through explicit, safe modern logic and only for
   historical study.

This policy intentionally permits old bug-dependent examples to stop working.
The compiler and execution platform optimize a clean machine definition rather
than preserving accidental nostalgia.

### H-001 - Input And Output Reversed

Classification: **historical interpreter defect**.

The specification defines `<` as input and `/` as output. The original C
interpreter implements the opposite:

```c
case '<': putc(a, stdout); break;
case '/': x = getc(stdin); /* ... */ break;
```

Normative rule: `<` reads and `/` writes.

Compatibility consequence: programs written around the interpreter bug may not
behave the same on the modern specification-conformant VM. That incompatibility
is accepted. An optional `legacy-ben` mode may model the historical behavior for
archaeology but cannot redefine the language or satisfy compiler verification.

Required fixture: `spec-io-roundtrip.malbolge` must distinguish the normative
read-then-write behavior from the historical interpreter's write-then-read bug.

### H-002 - Non-Graphical Current Cell Does Not Terminate

Classification: **historical interpreter defect**.

The specification says a current cell outside graphical ASCII `33..126`
immediately ends the program. The C interpreter instead executes:

```c
if (mem[c] < 33 || mem[c] > 126) continue;
```

Because neither pointer advances, the interpreter can remain in a tight
non-progressing loop.

Normative rule: the machine terminates immediately.

A legacy diagnostic harness may demonstrate the historical non-progressing state
using bounded stepping or a separately controlled process.

### H-003 - Fewer Than Two Loaded Words

Classification: **C undefined behavior / underspecified loader edge**.

The interpreter completes memory with:

```c
mem[i] = op(mem[i - 1], mem[i - 2]);
```

With fewer than two loaded words, this reads before the allocation. The prose
specification describes completion from the previous two cells but does not give
a meaningful recurrence base for zero- or one-word programs.

Project rule: normative tooling rejects source that cannot provide the two
predecessor cells required by the specified recurrence.

### H-004 - Pointer Change Can Expose Invalid Self-Encryption Index

Classification: **C undefined behavior risk**.

The C interpreter can change `C` during `i` and later index `xlat2` from the
cell at that resulting address. A state that places a non-graphical value there
can index outside the 94-character table.

Project rule: the normative transition is defined from the specification and
validated before any optimized implementation performs a table access. No modern
VM may reproduce an out-of-bounds C lookup.

### H-005 - Exotic Newline Branch Reads An Uninitialized Local

Classification: **C undefined behavior / portability defect**.

On hosts where the C execution character set does not encode `'\n'` as numeric
`10`, the interpreter's output branch can inspect local variable `x` before it
has been initialized by an input instruction.

Project rule: line feed is explicit numeric value `10`. Host character-set
peculiarities do not alter guest semantics.

### H-006 - Loader Validation Depends On Host `isspace`

Classification: **portability defect**.

The original loader delegates whitespace classification to the host C library
and validates the instruction mapping only for bytes strictly inside graphical
ASCII. This can admit host-dependent or non-graphical inputs.

Project rule: source encoding and whitespace are explicit and
locale-independent.

### H-007 - Historical Text-Mode I/O

Classification: **portability defect**.

The interpreter opens source using C text mode and uses standard text-oriented
streams. Platform newline/EOF translations are therefore host behavior, not
Malbolge behavior.

Project rule: compiler, VM, tests, and self-hosting runtime define byte-stream
semantics explicitly.

### H-008 - Historical Host Integer And Memory-Model Assumptions

Classification: **portability defect**.

The source discusses 16-bit `short` assumptions and special large-array memory
models for old compilers. These are properties of the 1998 implementation, not
of the ten-trit abstract machine.

Project rule: guest word width and address-space semantics are independent of
host integer types and host allocation models.

### H-009 - Output Conversion Is Host-C Shaped

Classification: **implementation boundary**.

The C interpreter passes ten-trit `A` directly to `putc`, whose host-language
conversion rules are not a satisfactory normative byte-stream definition for a
modern multi-backend VM.

Project rule: the normative output mapping is specified explicitly by the
language/runtime profile and implemented identically by Rust, C, native, and
accelerator backends.

### H-010 - Halt Control Flow Is Easy To Mis-Factor

Classification: **conformance trap, not a specification defect**.

The halt instruction terminates immediately; an implementation must not execute
post-halt self-modification or pointer advancement merely because those actions
are factored into shared code for other instructions.

## Invariants

- Every known implementation defect or undefined/pathological behavior is
  classified as intended semantics, compatibility quirk, implementation defect,
  or unspecified historical behavior with a regression fixture where
  reproducible.
- The authoritative rule/specification is deterministic, versionable, and does
  not depend on undocumented host behavior.
- The declared scope contains no unresolved placeholder implementation or
  undocumented workaround required for this objective to function.
- Evidence is durable enough to move this TODO to `docs/todo/completed/` and
  remove the exact TODO heading without losing unfinished intent.

## Failure Behavior

- Unsupported, unverified, or contradictory behavior remains explicit; silent
  semantic fallback is not accepted.

## Verification

- Expected durable artifact surface: `tools/malbolge/`,
  `docs/technical/specification/`, `tests/compatibility/`.
- Required evidence: reviewed authority text plus deterministic
  parser/schema/governance tests for the declared boundary.
- Prerequisite completion evidence:
  `historical-malbolge-semantics-specification`.
## References

- [Specification Authority And Malbolge
  Evolution](../adr/specification-authority-and-malbolge-evolution.md)

- [Historical Malbolge semantics](malbolge-1998.md)
- `docs/bibliography/specifications-and-standards/malbolge/malbolge-1998.md`
- `tools/malbolge/main.c`

### Governing ADR Paths

- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
