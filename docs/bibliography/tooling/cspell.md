# CSpell Configuration Schema

## Status

Verified; evidence verified.

## Subject

- Canonical name: CSpell configuration schema
- Subject class: Code-spell-checking configuration and schema
- Stable identifier: streetsidesoftware/cspell main schema
- Publisher or authority: Street Side Software and CSpell contributors

## Repository Use

The repository uses CSpell configuration and its published JSON schema to
validate spelling policy under `.jig/cspell/`.

## Provenance

The checked-in configuration references the schema from the upstream CSpell
repository. The repository validates its own policy while treating the schema
and default dictionaries as external tooling.

## Identity And Version

- Canonical name: CSpell configuration schema
- Subject class: Code-spell-checking configuration and schema
- Stable identifier: streetsidesoftware/cspell main schema
- Publisher or authority: Street Side Software and CSpell contributors

## License Or Terms

CSpell is MIT-licensed. Dictionary packages and copied word lists may carry
independent provenance or license terms and are not relicensed by this record.

## Evidence

### Verified

- The repository config references the upstream CSpell schema exactly.
- CSpell supports repository dictionaries and source-aware spelling checks.

### Unresolved

The mutable `main` schema URL is not content-addressed. A future toolchain
manifest should pin the exact CSpell release and schema digest.

## Sources

<!-- jig-ignore-next-line: canonical source URL is indivisible -->
- <https://raw.githubusercontent.com/streetsidesoftware/cspell/main/cspell.schema.json> - accessed 2026-08-05.
- <https://github.com/streetsidesoftware/cspell> - accessed 2026-08-05.
<!-- jig-ignore-next-line: canonical source URL is indivisible -->
- <https://github.com/streetsidesoftware/cspell/blob/main/LICENSE> - accessed 2026-08-05.
