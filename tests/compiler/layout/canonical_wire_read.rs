// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Adversarial canonical compiler-wire file admission regressions.
// - Must-Not:
//   - Accept a drifted input snapshot or publish target artifacts.
// - Allows:
//   - Inputs: owned regular files and deterministic read-time mutations.
//   - Outputs: exact admission or typed rejection assertions.
//   - Side effects: owned ignored temporary fixture files only.
// - Split-When:
//   - A platform-specific input reader needs separate coverage.
// - Merge-When:
//   - The layout CLI's canonical reader boundary moves elsewhere.
// - Summary:
//   - Proves descriptor and pathname stability across bounded wire reads.
// - Description:
//   - Injects same-size in-place and inode replacement after reading.
// - Usage:
//   - `cargo test --bin malbolge_layout canonical_wire_read_tests`.
// - Defaults:
//   - No unverified bytes cross the canonical wire admission boundary.
//

//! Deterministic read-time mutation regressions for canonical compiler input.
use super::{MAX_CANONICAL_WIRE_BYTES, read_canonical_wire_with_reader};
use std::fs::{self, File};
use std::io::{self, Read as _};
use std::path::{Path, PathBuf};
use std::process::id;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::SystemTime;

static SEQUENCE: AtomicUsize = AtomicUsize::new(0);

struct Fixture(PathBuf);

impl Fixture {
    fn new() -> io::Result<Self> {
        let index = SEQUENCE.fetch_add(1, Ordering::Relaxed);
        let root = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join(".temp")
            .join(format!("layout-wire-admission-{}-{index}", id()));
        #[expect(
            clippy::create_dir,
            reason = "test fixtures must never reuse an old path"
        )]
        fs::create_dir(&root)?;
        Ok(Self(root))
    }

    fn path(&self, file: &str) -> PathBuf {
        self.0.join(file)
    }
}

#[expect(
    clippy::missing_trait_methods,
    reason = "fixture cleanup uses normal Drop"
)]
impl Drop for Fixture {
    fn drop(&mut self) {
        drop(fs::remove_dir_all(&self.0));
    }
}

fn read_and_then(
    file: &mut File,
    bytes: &mut Vec<u8>,
    change: impl FnOnce() -> io::Result<()>,
) -> io::Result<usize> {
    let count = file
        .take(MAX_CANONICAL_WIRE_BYTES.saturating_add(1))
        .read_to_end(bytes)?;
    change()?;
    Ok(count)
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "test asserts admission behavior")]
fn admitted_file_must_not_change_in_place_after_read() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let wire = fixture.path("wire.mctr");
    fs::write(&wire, b"abcdefgh").map_err(|error| error.to_string())?;
    let result = read_canonical_wire_with_reader(&wire, "ternary", |file, bytes| {
        read_and_then(file, bytes, || {
            fs::write(&wire, b"12345678")?;
            File::options()
                .write(true)
                .open(&wire)?
                .set_modified(SystemTime::UNIX_EPOCH)
        })
    });
    assert!(
        result
            .as_ref()
            .is_err_and(|error| error.contains("changed during read")),
        "changed same-length source was admitted: {result:?}"
    );
    Ok(())
}

#[cfg(unix)]
#[test]
#[expect(clippy::panic_in_result_fn, reason = "test asserts admission behavior")]
fn admitted_file_must_not_change_path_inode_after_read() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let wire = fixture.path("wire.mctr");
    let replacement = fixture.path("replacement.mctr");
    fs::write(&wire, b"abcdefgh").map_err(|error| error.to_string())?;
    fs::write(&replacement, b"12345678").map_err(|error| error.to_string())?;
    let result = read_canonical_wire_with_reader(&wire, "ternary", |file, bytes| {
        read_and_then(file, bytes, || fs::rename(&replacement, &wire))
    });
    assert!(
        result
            .as_ref()
            .is_err_and(|error| error.contains("changed during read")),
        "replaced same-length source was admitted: {result:?}"
    );
    Ok(())
}

#[cfg(unix)]
#[test]
#[expect(clippy::panic_in_result_fn, reason = "test asserts admission behavior")]
fn stable_regular_file_symlink_remains_admitted() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let target = fixture.path("target.mctr");
    let wire = fixture.path("linked.mctr");
    fs::write(&target, b"abcdefgh").map_err(|error| error.to_string())?;
    std::os::unix::fs::symlink(&target, &wire).map_err(|error| error.to_string())?;
    let bytes = read_canonical_wire_with_reader(&wire, "ternary", |file, bytes| {
        read_and_then(file, bytes, || Ok(()))
    })?;
    assert_eq!(bytes, b"abcdefgh");
    Ok(())
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "test asserts admission behavior")]
fn unchanged_file_remains_admitted() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let wire = fixture.path("wire.mctr");
    fs::write(&wire, b"abcdefgh").map_err(|error| error.to_string())?;
    let bytes = read_canonical_wire_with_reader(&wire, "ternary", |file, bytes| {
        read_and_then(file, bytes, || Ok(()))
    })?;
    assert_eq!(bytes, b"abcdefgh");
    Ok(())
}
