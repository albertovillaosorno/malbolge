# Historical Interpreter Behavior And Undefined C Boundaries

## Status

Active historical catalogue

## Purpose

This catalogue separates authoritative original-interpreter behavior from
host-dependent or undefined behavior in Ben Olmstead's C implementation.

The resolution rule is:

1. defined, reproducible interpreter behavior is authoritative for
   `malbolge-1998`;
2. contradictory prose remains explicit specification-comparison evidence;
3. undefined, locale-dependent, or host-dependent C behavior is rejected safely
   or governed by an explicit versioned profile.

## Scope

- `src/interoperability/historical-malbolge/`
- `docs/technical/specification/`
- `tests/compatibility/`

## Current Behavior

### Compatibility Policy

Modern Rust, independent C, native, and accelerator implementations reproduce
the portable state transitions of the original interpreter. They do not invoke
historical undefined behavior merely to imitate the C program.

### H-001 - Interpreter I/O Assignment

Classification: **intended interpreter semantics / prose discrepancy**.

The prose assigns `<` to input and `/` to output. The original interpreter
implements:

```c
case '<': putc(a, stdout); break;
case '/': x = getc(stdin); /* ... */ break;
```

Authoritative rule: `<` writes the low byte of `A`; `/` reads a byte into
`A`, or the classic EOF word when input is exhausted.
`ExecutionMode::Specification`
retains the prose assignment only for explicit comparison.

### H-002 - Non-Graphical Current Cell Does Not Progress

Classification: **intended interpreter semantics / prose discrepancy**.

The interpreter executes:

```c
if (mem[c] < 33 || mem[c] > 126) continue;
```

Neither pointer advances. Modern bounded APIs model one request as `Continued`
with no state, I/O, memory, or termination change. A bounded run exhausts its
budget rather than hanging the host. Olmstead's 2014 interview identifies this
behavior as intended and the contradictory prose as the defect.

### H-003 - Fewer Than Two Loaded Words

Classification: **C undefined behavior / underspecified loader edge**.

Memory completion reads `mem[i - 1]` and `mem[i - 2]`. With fewer than two
loaded words, the original program reads before the allocation.

Project rule: source admission rejects a recurrence without two predecessor
words. No arbitrary bytes are invented.

### H-004 - Invalid Self-Encryption Index After Pointer Change

Classification: **C undefined behavior risk**.

The `i` instruction may change `C` before post-instruction encryption. If the
resulting cell is non-graphical, the historical C program can index outside the
94-character encryption table.

Project rule: modern VMs return
`UnsupportedInterpreterBehavior::InvalidSelfEncryptionTarget` atomically before
any table access or state publication.

### H-005 - Exotic Newline Branch Reads An Uninitialized Local

Classification: **C undefined behavior / portability defect**.

On an execution character set where newline is not numeric `10`, one historical
branch can inspect a local before initialization.

Project rule: byte input and output use explicit numeric values. Line feed is
`10`; no host character-set branch alters guest semantics.

### H-006 - Loader Validation Uses Host `isspace`

Classification: **portability boundary**.

The original loader delegates whitespace classification to the host C library.
Modern source admission uses explicit ASCII whitespace and graphical-byte rules,
independent of locale.

### H-007 - Historical Text-Mode I/O

Classification: **portability boundary**.

The interpreter uses C text streams, so newline and EOF translation may vary by
platform. Modern execution uses explicit byte streams.

### H-008 - Historical Integer And Memory-Model Assumptions

Classification: **portability boundary**.

Comments and allocation choices reflect historical compiler integer widths and
large-array models. Classic words and addresses are fixed by the target profile,
not by host C types.

### H-009 - Output Conversion Is Host-C Shaped

Classification: **portable projection required**.

The historical program passes `A` to `putc`. The portable interpreter contract
writes `A mod 256`, preserving the defined low-byte result across Rust, C,
native, and accelerator paths.

### H-010 - Halt Control Flow Is Easy To Mis-Factor

Classification: **conformance trap**.

Halt terminates immediately. Implementations must not apply post-halt encryption
or pointer advancement through shared non-halting code.

## Invariants

- Every discrepancy is classified as authoritative interpreter behavior,
  specification-comparison behavior, undefined C behavior, or portability
  boundary.
- No modern path invokes C undefined behavior to claim compatibility.
- Interpreter-authority results are deterministic and versionable.
- Versioned current profiles retain independent semantic identities.

## Failure Behavior

Unsupported or undefined historical behavior returns a typed deterministic
failure. No silent fallback to specification semantics and no partial state
publication are accepted.

## Verification

- `tests/vm/modes.rs` covers H-001 through H-004.
- `tests/vm/conformance.rs` covers portable classic transitions.
- `tests/vm/differential.rs` binds Rust to the independent C oracle.
- CUDA classic tests compare device results with the interpreter-authority VM.
- The original source remains unchanged for sanitizer and provenance work.

## References

- [Interpreter Authority And Malbolge
  Evolution](../adr/specification-authority-and-malbolge-evolution.md)
- [Historical Malbolge semantics](malbolge-1998.md)
- `docs/bibliography/specifications-and-standards/malbolge/malbolge-1998.md`
- `docs/bibliography/specifications-and-standards/malbolge/`
  `ben-olmstead-2014-interview.md`
- `src/interoperability/historical-malbolge/adapter-outbound/main.c`

### Governing ADR Paths

- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
