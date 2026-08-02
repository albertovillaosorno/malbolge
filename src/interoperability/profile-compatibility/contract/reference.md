# Compatibility Profiles

This directory owns compatibility evidence and profile-boundary artifacts. The
canonical executable profile declaration is the repository-root
`malbolge.json`; this directory does not define a second profile authority.

## Current identities

- `malbolge-1998` freezes the written 1998 ten-trit, 59,049-word machine for
  conformance and archaeology.
- `malbolge-2026.1` is the immutable ten-trit transition identity that first
  separated current-language artifacts from historical conformance.
- `malbolge-2026.2` is the current schema-v2 scalable profile: 14 trits and
  4,782,969 directly addressed words under the same ternary semantic core.

`src/interoperability/profile-compatibility/contract/scalable-memory-evidence.json` records why 14 trits were selected
for the first scalable profile. Future capacity changes create another immutable
profile and advance `current_profile`; they never mutate an existing identity.
Historical interpreter quirks remain outside language profiles and require
explicit `legacy-ben` execution.

Profile identity uses `malbolge-profile-v1` canonicalization and self-describing
SHA-256 fingerprints. `profile-fingerprints.json` is the generated canonical
manifest; `custom-profile.example.json` demonstrates the closed external format.
Use `.\.dependencies\python\3.14.6\Scripts\python-jig.cmd -m scripts.validate.profile_identity` to fingerprint or verify an external profile. Fingerprints bind identity/integrity and do not provide secrecy.

Version-one extended `.malbolge` capsules use the fixed historical fallback
`(C<;_"K` plus a space/tab-only `MALBCAP1` sideband. The sideband binds canonical
profile ID/fingerprint and payload without changing what the historical loader
stores. See the technical capsule contract for exact framing and failure codes.
