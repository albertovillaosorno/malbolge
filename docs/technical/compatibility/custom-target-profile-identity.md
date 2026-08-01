# Custom target profile identity

## Status

Active implementation

## Purpose

Give canonical and user-supplied Malbolge target profiles stable content-bound
identity so artifacts and external configuration can detect semantic mismatch
instead of silently interpreting the same bytes under another profile.

The fingerprint is an integrity and identity mechanism. It is not encryption,
obfuscation, copy protection, or evidence that a profile-dependent encoding is
hard to reverse engineer.

## Scope

This document currently governs:

- `malbolge.json`
- `compatibility/profile-fingerprints.json`
- `compatibility/custom-profile.example.json`
- `scripts/validate/target_profile.py`
- `scripts/validate/profile_identity.py`
- `scripts/validate/experiment_manifest.py`
- `vm/src/profile.rs`
- `vm/src/profile_generated.rs`
- `tests/test_target_profile.py`
- `tests/compatibility/test_profile_identity.py`
- `tests/test_experiment_manifest.py`

## Current Behavior

### Canonicalization Identity

Malbolge Profile Canonicalization v1 has the stable label
`malbolge-profile-v1`.

For one profile, canonical identity material is compact JSON containing exactly:

- `canonicalization = "malbolge-profile-v1"`;
- `target_schema_version`;
- `profile_id`; and
- `profile`, containing `version`, `word`, `memory`, and `semantics`.

Objects are serialized with lexicographically sorted keys, no insignificant
whitespace, JSON booleans/integers, and ASCII JSON escaping. The resulting ASCII
bytes are hashed with SHA-256. The self-describing fingerprint is:

`malbolge-profile-v1:sha256:<64 lowercase hexadecimal digits>`.

Repository registry field `kind` is intentionally excluded. `kind` describes a
profile's lifecycle role in the registry, not its immutable language meaning.
For example, `malbolge-2026.1` changed from `current` to `versioned` when
`malbolge-2026.2` became current; artifacts bound to 2026.1 must not acquire a
new fingerprint because of that registry transition.

Profile ID and version remain included. Therefore two profiles with identical
geometry and semantics, such as `malbolge-1998` and the ten-trit transition
profile `malbolge-2026.1`, still have distinct fingerprints.

### Canonical Fingerprint Manifest

`compatibility/profile-fingerprints.json` is a generated review artifact. It
records one fingerprint for every canonical profile in `malbolge.json` together
with the canonicalization and target-schema versions.

`tests/test_target_profile.py` requires this manifest and the checked-in Rust
profile projection to equal their deterministic renderers byte for byte.

The Rust `ProfileDescriptor` exposes the same generated fingerprint through
`fingerprint()`, so future artifact code does not need a handwritten profile
hash table.

### External Custom Profile Format

A user-supplied profile identity document has closed schema version 1:

```json
{
  "schema_version": 1,
  "target_schema_version": 2,
  "profile_id": "custom-14-example",
  "profile": {
    "version": "custom-14.1",
    "word": {},
    "memory": {},
    "semantics": {}
  }
}
```

The nested `word`, `memory`, and `semantics` objects use exactly the same closed
shape and invariants as canonical target profiles. `kind` is absent because an
external identity is not allowed to claim registry lifecycle authority.

A custom profile may choose another ternary word width/capacity while preserving
the defining Malbolge semantic core. It may not switch guest order, remove
self-modification, change byte-I/O meaning, or otherwise use the custom-profile
mechanism to define an unrelated language.

If `profile_id` already exists in canonical `malbolge.json`, the external
profile definition must exactly match that canonical profile after excluding
`kind`. This prevents a supplied file from rebinding `malbolge-2026.2` or any
other published ID to different semantics or geometry.

`compatibility/custom-profile.example.json` is a non-authoritative example of a
new 14-trit custom identity using the current defining semantic core.

### Fingerprint CLI

Run:

```text
.\.dependencies\python\3.14.6\Scripts\python-jig.cmd -m scripts.validate.profile_identity PROFILE.json
```

to validate the external profile and print its canonical fingerprint.

Run:

```text
.\.dependencies\python\3.14.6\Scripts\python-jig.cmd -m scripts.validate.profile_identity PROFILE.json EXPECTED-FINGERPRINT
```

to verify an artifact/profile binding. A mismatch fails with exit status 1 and
stable diagnostic code `MALBOLGE-PROFILE-ID-001`, naming the profile plus the
expected and observed fingerprints.

The example profile currently fingerprints to:

`malbolge-profile-v1:sha256:221015e0ac4cbde88444ad6d55c703a2e2cc96904bd65b81cb44e256aa1f3177`.

### Artifact And Container Binding

Experiment Manifest v1 and the `MALBCAP1` runtime capsule both require this
content-bound identity. Canonical target IDs must include the exact generated
`target_profile_fingerprint`; the validator recomputes it from `malbolge.json`
and emits `MALBOLGE-PROFILE-ID-001` on mismatch. Unknown IDs fail rather than
falling back. Explicit aggregate research scopes remain legal only without a
fingerprint because they do not identify one canonical semantic profile.

Ten checked-in canonical-profile manifests currently carry this binding: five
algorithm plans and five retained current-profile accelerator evidence records.
The `MALBCAP1` capsule carries the same ID/fingerprint pair, recomputes canonical
identity before exposing payload, emits shared `MALBOLGE-PROFILE-ID-001` on
mismatch, and rejects unknown IDs without fallback. Compiler objects and
product-level artifact metadata remain open.

### Security Boundary

SHA-256 gives a compact collision-resistant identity for the exact canonical
profile material. It does not hide the profile. Anyone who possesses the profile
or artifact metadata can inspect or reproduce the fingerprint.

Profile-dependent instruction encoding remains a separate research question. If
pursued, it must be described as encoding/layout variation rather than a claim
that reverse engineering can be made cryptographically impossible.

## Invariants

- Canonical profile fingerprints are derived from `malbolge.json`; they are not
  maintained independently by hand.
- `kind` never participates in immutable profile fingerprints.
- Profile ID, version, target schema, word model, memory model, and semantics do
  participate in the fingerprint.
- JSON source formatting and object key order do not affect identity.
- A canonical profile ID cannot be redefined by an external file.
- Custom profiles preserve the defining Malbolge semantic core.
- A supplied fingerprint mismatch is explicit and deterministic.
- Fingerprints provide identity/integrity, not secrecy.

## Failure Behavior

Malformed external schema, target-schema mismatch, invalid ternary geometry,
semantic-core drift, or canonical-ID redefinition fails before a fingerprint is
accepted.

A structurally valid profile whose computed fingerprint differs from the
artifact expectation fails with `MALBOLGE-PROFILE-ID-001`; the external profile
is never silently substituted for the expected identity.

Experiment manifests and `MALBCAP1` capsules now carry this fingerprint for
canonical research and runtime-container artifacts. Compiler objects and
product-level artifacts do not yet universally carry it, so this contract
remains active.

## Verification

- `tests/test_target_profile.py` locks canonical manifest and Rust projection
  generation byte for byte.
- `tests/compatibility/test_profile_identity.py` covers stable example identity,
  key-order independence, canonical/external equivalence, profile-ID
  participation, semantic drift, canonical-ID collision, and exact mismatch
  diagnostics.
- `tests/test_experiment_manifest.py` covers canonical artifact fingerprints,
  unknown-ID rejection, noncanonical-scope separation, and the shared exact
  mismatch diagnostic.
- `tests/vm/capsule.rs` covers exact capsule fingerprint mismatch fields/text,
  unknown-profile rejection without fallback, checksum-valid tampering, and
  canonical payload exposure only after identity verification.
- `tests/vm/profile_requirements.rs` verifies the current Rust descriptor exposes
  the generated canonical fingerprint.
- The CLI is smoke-tested with matching and mismatching expected fingerprints.
- `jig validate --root .` remains the repository-wide closure gate.

## References

- [Specification Authority And Malbolge
  Evolution](../adr/specification-authority-and-malbolge-evolution.md)
- [Canonical Malbolge target profile](../specification/target-profile.md)
- [Required-profile diagnostics](required-profile-diagnostics.md)

### Governing ADR Paths

- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
