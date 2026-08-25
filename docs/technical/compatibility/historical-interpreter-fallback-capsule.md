# Historical-Interpreter Fallback Capsule

## Status

Active implementation

## Purpose

Define a versioned `.malbolge` container that modern runtimes can recognize and
validate while the historical Ben Olmstead loader sees only a small, deliberate
classic fallback program.

The fallback is containment and communication for old tooling. It is not
semantic compatibility evidence for the modern payload.

## Scope

This contract currently governs:

- `src/runtime/virtual-machine/domain/capsule.rs`
- `tests/vm/capsule.rs`
- `tests/compatibility/test_capsule.py`
- `tests/compatibility/capsule/current-profile-capsule.hex`
- `tests/compatibility/capsule/malbolge-2026.3-capsule.hex`
- `tests/compatibility/capsule/README.md`

Raw capsules contain intentional tabs and trailing whitespace, so the annual
and versioned fixtures are stored as text-hygienic hexadecimal byte vectors.
Tests decode both vectors and require `build_capsule()` to reproduce the
selected annual-current vector exactly. This changes fixture storage only, never
the
`.malbolge` wire format.

The canonical profile authority remains repository-root `malbolge.json` and
profile fingerprints remain governed by
`custom-target-profile-identity.md`.

## Current Behavior

### File Shape

Version one has exactly two physical regions:

```text
historical fallback bytes
space/tab sideband suffix
```

The fixed version-one fallback is the seven graphical ASCII bytes:

```text
(C<;_"K
```

No whitespace may occur inside this fallback. Every following byte in a
recognized version-one sideband is either ASCII space (`0x20`) or horizontal tab
(`0x09`). No CR, LF, vertical-tab, or form-feed symbol is used to encode data.
This avoids relying on C text-mode newline translation in the historical
interpreter.

The historical loader calls `isspace(x)` before storing source bytes, so both
space and tab disappear from its memory image. Therefore the checked-in capsule
fixture is seen historically as exactly `(C<;_"K`.

### Historical Sentinel

At loaded positions zero through six, `(C<;_"K` decodes as:

```text
j o p p < * v
```

The initial `j` moves `D` away from the current code pointer before either `p`
instruction mutates data. This keeps every subsequent historical xlat2 target in
graphical ASCII and avoids H-004 out-of-bounds self-encryption.

The fallback intentionally relies on the documented H-001 Ben-interpreter I/O
reversal only inside this isolated historical surface: decoded `<` emits the
accumulator in Ben's implementation. The fixed sequence emits one ASCII `!`,
consumes no input, then halts.

Modern specification execution never uses this fallback as payload semantics.

### Sideband Bit Encoding

Each decoded frame byte expands to eight whitespace symbols, most-significant
bit
first:

- bit `0` -> ASCII space (`0x20`);
- bit `1` -> horizontal tab (`0x09`).

The exact magic `MALBCAP1` must decode immediately after the fallback. A file is
not treated as a capsule merely because it begins with the fallback or ends in
ordinary whitespace. Before the magic is recognized, recognition returns
"ordinary source" rather than an error. After exact magic recognition, malformed
framing fails closed.

### Version-One Frame

The decoded binary frame is:

```text
8 bytes   magic               = "MALBCAP1"
1 byte    version             = 1
1 byte    flags               = 0
2 bytes   profile_id_length   unsigned big-endian
2 bytes   fingerprint_length  unsigned big-endian
4 bytes   payload_length      unsigned big-endian
N bytes   profile_id          UTF-8 canonical profile ID
M bytes   fingerprint         UTF-8 malbolge-profile-v1 fingerprint
P bytes   payload             raw modern payload bytes
8 bytes   checksum            FNV-1a-64, unsigned big-endian
```

The checksum covers every decoded frame byte before the checksum field. FNV-1a
is used only as a deterministic transport-corruption check. It is not a security
boundary and is not a substitute for the SHA-256 canonical profile fingerprint.

Version-one flags are closed at zero. Unknown versions or nonzero flags fail
explicitly.

### Modern Runtime Boundary

`build_capsule()` emits the fixed fallback plus a deterministic sideband for one
canonical `ProfileDescriptor` and arbitrary payload bytes.

`parse_capsule()` returns `Ok(None)` for ordinary source. Recognition inspects
the 64 space/tab symbols that encode the exact magic before classifying the
remaining suffix. Once exact magic is recognized, any non-space/tab symbol in
later framing fails `MALBOLGE-CAPSULE-001`; the parser then validates lengths,
checksum, canonical profile lookup, and exact profile fingerprint before
returning payload bytes and the selected canonical descriptor.

The annual-current fixture selects `malbolge-2026` and carries `ubO` plus LF
as its small payload. The preserved `malbolge-2026.3` fixture carries the same
payload under its immutable published ID and fingerprint. At loaded positions
0, 1, and 2, those bytes decode to
`/`, `<`, and `v`, matching the current profile's interpreter-compatible I/O
assignment. Parsing succeeds. Passing that extracted payload/profile into the
classic `ExecutionMachine::from_source_for_profile()` still fails

`safe-rust-classic` capability preflight before the ten-trit loader. Passing the
same explicit descriptor/payload to `ProfileMachine` succeeds under
`safe-rust-profiled`, consumes one input byte, emits it, and halts normatively.
Capsule recognition therefore never chooses a runtime implicitly: classic and
profile-driven consumers remain distinct and fail/execute according to their
advertised capacities.

### Ordinary Classic Programs

Classic source remains ordinary `.malbolge`. In particular:

- `ctO` or `ubO` with ordinary whitespace is not a capsule;
- the fixed fallback followed by ordinary whitespace is not a capsule unless the
  exact whitespace-encoded magic is present;
- no existing source is reinterpreted merely because whitespace exists.

## Invariants

- The version-one sideband alphabet is exactly space and horizontal tab.
- The historical visible source is exactly `(C<;_"K`.
- The historical fallback emits `!`, consumes no input, halts, and does not rely
  on H-004 or another undefined xlat2 access.
- H-001 reliance is isolated to the fallback and never becomes normative guest
  semantics.
- Modern payload selection uses canonical profile ID plus exact
  `malbolge-profile-v1` fingerprint.
- FNV-1a-64 detects accidental frame corruption only; it makes no
  cryptographic-security claim.
- A runtime that does not support the selected profile still fails capability
  preflight; the historical fallback is never used as semantic recovery.
- The profile-driven safe Rust runtime can execute the current capsule, while
  the
  classic facade continues to reject the same profile explicitly.
- Ordinary classic source remains ordinary source when capsule magic is absent.

## Failure Behavior

After exact magic recognition:

- malformed framing -> `MALBOLGE-CAPSULE-001`;
- unsupported version -> `MALBOLGE-CAPSULE-002`;
- checksum mismatch -> `MALBOLGE-CAPSULE-003`;
- unknown canonical profile -> `MALBOLGE-CAPSULE-004`;
- profile fingerprint mismatch -> shared `MALBOLGE-PROFILE-ID-001`,
  naming the profile plus declared `expected` and canonical `observed`
  fingerprints;
- unsupported flags -> `MALBOLGE-CAPSULE-006`.

Build-time length overflow uses `MALBOLGE-CAPSULE-BUILD-001`.

A failure never executes either the sideband payload or the historical fallback
through the modern capsule path.

## Verification

- `tests/vm/capsule.rs` locks the Rust builder against the annual-current
  fixture, parses and executes the preserved `malbolge-2026.3` vector, validates
  checksum tampering, post-magic non-sideband rejection, exact shared
  fingerprint mismatch, and unknown-profile rejection without fallback; proves
  ordinary-source non-recognition, verifies
  the historical visible bytes, runs the fixed fallback under
  `ExecutionMode::Interpreter`, and proves current-profile execution reaches
  capability preflight before payload loading.
- `tests/compatibility/test_capsule.py` independently decodes both whitespace
  frame, recomputes FNV-1a-64, checks the immutable historical C loader's
  `fopen(..., "r")` plus `isspace` behavior, and reconstructs the seven fixed
  historical transitions including every xlat2 safety boundary.
- The repo-local LLVM 22 bundle is a frontend/tooling bundle and does not ship C
  runtime headers such as `stdio.h`, so direct native execution of the immutable
  historical C interpreter is not a repository validation gate. No such native
  execution claim is made here.
- `jig validate --root .` remains the repository-wide closure gate.

## References

- [Custom target profile identity](custom-target-profile-identity.md)
- [Required-profile diagnostics](required-profile-diagnostics.md)
- [Historical undefined
  behavior](../specification/historical-undefined-behavior.md)
- [Specification Authority And Malbolge
  Evolution](../adr/specification-authority-and-malbolge-evolution.md)

### Governing ADR Paths

- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
