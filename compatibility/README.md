# Compatibility Profiles

This directory owns compatibility evidence and profile-boundary artifacts. The
canonical executable profile declaration is the repository-root
`malbolge.json`; this directory does not define a second profile authority.

## Current identities

- `malbolge-1998` freezes the written 1998 ten-trit, 59,049-word machine for
  conformance and archaeology.
- `malbolge-2026.1` is the first versioned current-language identity. Its current
  executable resource envelope is intentionally identical to `malbolge-1998`
  because the scalable-memory design is not yet settled, but its identity is
  distinct so future evolution cannot silently reinterpret old artifacts.

When the scalable memory model is accepted, it creates a new versioned profile
and advances `current_profile`; it does not mutate either identity above.
Historical interpreter quirks remain outside these language profiles and require
explicit `legacy-ben` execution.

Profile fingerprints and user-supplied custom-profile identity are owned by the
separate custom-target-profile TODO and are not invented here.
