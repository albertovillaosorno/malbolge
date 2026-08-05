# Historical-Fallback Capsule Fixture

`current-profile-capsule.hex` is the canonical version-one compatibility byte
vector. It is lowercase hexadecimal wrapped for text hygiene; decoding it yields
the exact `.malbolge` bytes emitted by the Rust `build_capsule()` API.

Its historical visible source is exactly:

```text
(C<;_"K
```

Every remaining byte is ASCII space or horizontal tab. Ben Olmstead's immutable
loader discards those bytes through `isspace`, so old tooling receives only the
seven-byte fallback. That fallback decodes to `j o p p < * v`, emits ASCII `!`
under the documented H-001 reversed-I/O behavior, consumes no input, avoids
H-004 invalid self-encryption, and halts.

Modern code instead decodes the space/tab suffix as the `MALBCAP1` frame. The
fixture binds to canonical profile `malbolge-2026`, carries its exact
`malbolge-profile-v1` fingerprint, and contains payload bytes `75 62 4f 0a`
(`ubO` plus LF). The payload decodes to `/`, `<`, and `v` under the current
profile.

The decoded frame checksum is FNV-1a-64 `844425f59cae4308`. This checksum is a
transport-corruption detector only; profile identity is bound separately by the
SHA-256 profile fingerprint.
