# Compatibility Profiles

This directory owns compatibility evidence and profile-boundary artifacts. The
canonical executable profile declaration is the repository-root
`malbolge.json`; this directory does not define a second profile authority.

## Current identities

- `malbolge-1998` freezes defined original-interpreter behavior in the
  ten-trit, 59,049-word machine for conformance and archaeology.
- `malbolge-2026.1` is the immutable ten-trit transition identity that first
  separated current-language artifacts from historical conformance.
- `malbolge-2026.2` is the immutable first 14-trit scalable identity. It retains
  its published specification-first `<` input and `/` output assignment.
- `malbolge-2026.3` is the immutable interpreter-compatible transition
  identity used by byte-exact compatibility fixtures.
- `malbolge-2026` is the official year-only current schema-v2 scalable profile:
  14 trits,
  4,782,969 directly addressed words, `/` input, and `<` output. It keeps modern
  safe failure rules and does not reproduce historical C undefined behavior.

`src/interoperability/profile-compatibility/contract/scalable-memory-evidence.json` records why 14 trits were selected
for the first scalable profile. Future capacity changes create another immutable
profile and advance `current_profile`; they never mutate an existing identity.
Defined original-interpreter behavior belongs to `malbolge-1998`.
Contradictory prose is explicit specification comparison, while undefined C
behavior remains outside every portable profile.

Profile identity uses `malbolge-profile-v1` canonicalization and self-describing
SHA-256 fingerprints. `profile-fingerprints.json` is the generated canonical
manifest; `custom-profile.example.json` demonstrates the closed external format.
Use `.\.dependencies\python\3.14.6\Scripts\python-jig.cmd -m scripts.validate.profile_identity` to fingerprint or verify an external profile. Fingerprints bind identity/integrity and do not provide secrecy.

Version-one extended `.malbolge` capsules use the fixed historical fallback
`(C<;_"K` plus a space/tab-only `MALBCAP1` sideband. The sideband binds canonical
profile ID/fingerprint and payload without changing what the historical loader
stores. See the technical capsule contract for exact framing and failure codes.
