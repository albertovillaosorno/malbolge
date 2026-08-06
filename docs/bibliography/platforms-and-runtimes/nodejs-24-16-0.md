# Node.js 24.16.0 LTS

## Status

Verified; evidence verified.

## Subject

- Canonical name: Node.js 24.16.0 LTS
- Subject class: JavaScript runtime release
- Stable identifier: Node.js v24.16.0 Krypton LTS
- Publisher or authority: OpenJS Foundation and Node.js contributors

## Repository Use

Node.js 24.16.0 is the runtime payload selected by the pinned unofficial Python
wheel used to execute BasedPyright. Node.js is validation infrastructure; it is
not a guest runtime or a required dependency of generated `.malbolge` programs.

## Provenance

The Node.js project published version 24.16.0, codename Krypton, as an LTS
release on 2026-05-21. The official download index publishes platform artifacts
and signed SHA-256 manifests. The repository obtains the runtime through the
separately cataloged `nodejs-wheel-binaries` package.

## Identity And Version

- Canonical name: Node.js 24.16.0 LTS
- Subject class: JavaScript runtime release
- Stable identifier: Node.js v24.16.0 Krypton LTS
- Publisher or authority: OpenJS Foundation and Node.js contributors

## License Or Terms

Node.js is distributed under the MIT License with bundled third-party component
licenses. The unofficial wheel and its exact embedded payload require separate
provenance and notice review.

## Evidence

### Verified

- Node.js 24.16.0 LTS was published on 2026-05-21.
- The release codename is Krypton.
- Official platform downloads and signed SHA-256 manifests are published.
- The validation environment pins a package carrying version 24.16.0.

### Unresolved

The exact Node.js artifact embedded in the selected Python wheel, its byte hash,
and complete bundled-license inventory require installed-wheel evidence.

## Sources

- <https://nodejs.org/en/blog/release/v24.16.0> - accessed 2026-08-05.
- <https://nodejs.org/download/release/v24.16.0/> - accessed 2026-08-05.
- <https://github.com/nodejs/node/blob/v24.16.0/LICENSE> - accessed
  2026-08-05.
