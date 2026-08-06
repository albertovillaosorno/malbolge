# uv 0.11.16

## Status

Verified; evidence verified.

## Subject

- Canonical name: uv 0.11.16
- Subject class: Python package and project manager
- Stable identifier: Astral uv 0.11.16
- Publisher or authority: Astral Software and uv contributors

## Repository Use

uv 0.11.16 is the pinned standalone package manager used to create and
synchronize the repository-local Python validation environment. The bootstrap
creates the virtual environment without pip and invokes `uv pip sync` against
the exact requirements file.

## Provenance

Astral published uv 0.11.16 on 2026-05-21 with signed release metadata,
platform-specific archives, checksums, and attestations. The repository tracks
five supported host artifacts in `uv-toolchain.json` and verifies SHA-256 before
extracting only the expected executable member.

## Identity And Version

- Canonical name: uv 0.11.16
- Subject class: Python package and project manager
- Stable identifier: Astral uv 0.11.16
- Publisher or authority: Astral Software and uv contributors

## License Or Terms

uv is dual-licensed under Apache-2.0 or MIT at the user's option. Downloaded
Python packages retain independent licenses. The standalone archive and its
third-party notices remain external material.

## Evidence

### Verified

- uv 0.11.16 was released on 2026-05-21.
- Official standalone archives exist for the tracked Windows, Linux, and macOS
  host classes.
- uv's pip interface does not rely on or invoke pip.
- The bootstrap explicitly removes legacy pip after synchronizing packages.
- The repository pins version, asset names, members, and SHA-256 values.

### Unresolved

Release attestations are not yet verified automatically. The bootstrap verifies
tracked SHA-256 values but still depends on HTTPS availability for first
install.

## Sources

- <https://github.com/astral-sh/uv/releases/tag/0.11.16> - accessed
  2026-08-05.
- <https://github.com/astral-sh/uv/releases/download/> - accessed
  2026-08-05.
- <https://github.com/astral-sh/uv/releases/download/0.11.16/> - accessed
  2026-08-05.
- <https://docs.astral.sh/uv/getting-started/installation/> - accessed
  2026-08-05.
- <https://docs.astral.sh/uv/pip/> - accessed 2026-08-05.
- <https://docs.astral.sh/uv/reference/cli/#uv-pip-sync> - accessed
  2026-08-05.
- <https://github.com/astral-sh/uv#license> - accessed 2026-08-05.
