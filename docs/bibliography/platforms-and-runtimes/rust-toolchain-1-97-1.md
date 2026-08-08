# Rust Toolchain 1.97.1

## Status

Verified; evidence verified.

## Subject

- Canonical name: Rust 1.97.1 toolchain
- Subject class: Rust compiler and build-tool release
- Stable identifier: Rust 1.97.1
- Publisher or authority: Rust Project

## Repository Use

Rust 1.97.1 is the minimum and pinned stable toolchain for Cargo builds, tests,
documentation, and benchmark evidence. The repository also uses a dated nightly
for Clippy and rustfmt, but stable 1.97.1 remains the product compiler baseline.

## Provenance

The Rust Release Team announced Rust 1.97.1 on 2026-07-16 as a point release
fixing an LLVM-optimization miscompilation. `Cargo.toml`, Jig configuration, and
benchmark evidence pin the exact version and Windows GNU host toolchain.

## Identity And Version

- Canonical name: Rust 1.97.1 toolchain
- Subject class: Rust compiler and build-tool release
- Stable identifier: Rust 1.97.1
- Publisher or authority: Rust Project

## License Or Terms

Rust compiler and tool distributions contain multiple components under their
upstream licenses. The Rust Project publishes licensing information separately;
using the toolchain does not relicense repository source or generated artifacts.

## Evidence

### Verified

- The Rust Release Team published Rust 1.97.1 on 2026-07-16.
- The point release fixes a reported LLVM optimization miscompilation.
- `Cargo.toml` requires Rust 1.97.1.
- `.jig/version/rust-toolchain.toml` pins the Windows GNU stable channel.
- Rust 1.97.1 documents `Instant` as an opaque monotonically nondecreasing
  clock suitable for elapsed-time measurement rather than wall-clock identity.
- Rust 1.97.1 documents `thread::sleep` as blocking for at least the requested
  duration, with platform-specific rounding or interrupted-sleep retries.

### Unresolved

The exact archive hashes, bundled LLVM components, standard-library payload, and
dated nightly tools require installation-manifest evidence for each host.

## Sources

- <https://blog.rust-lang.org/2026/07/16/Rust-1.97.1/> - accessed
  2026-08-05.
- <https://doc.rust-lang.org/1.97.1/> - accessed 2026-08-05.
- <https://doc.rust-lang.org/1.97.1/std/time/struct.Instant.html> - accessed
  2026-08-08.
- <https://doc.rust-lang.org/1.97.1/std/thread/fn.sleep.html> - accessed
  2026-08-08.
- <https://www.rust-lang.org/policies/licenses> - accessed 2026-08-05.
