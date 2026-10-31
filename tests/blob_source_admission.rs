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
//   - Deterministic pre-open and post-read blob-source identity regressions.
// - Must-Not:
//   - Treat a symlink, FIFO, or changed pathname as a verified regular source.
// - Allows:
//   - Inputs: isolated regular files and substituted filesystem entries.
//   - Outputs: exact fail-closed descriptor and pathname assertions.
//   - Side effects: ignored local filesystem test fixtures.
// - Split-When:
//   - The blob adapter gains an independent platform-specific read backend.
// - Merge-When:
//   - Equivalent admission evidence is part of a shared filesystem harness.
// - Summary:
//   - Prevents regular-to-special-node races and stale opened-source reuse.
// - Description:
//   - Injects path replacement at metadata and descriptor boundaries.
// - Usage:
//   - `cargo test --test blob_source_admission`.
// - Defaults:
//   - Replaced or modified sources cannot authorize a bounded blob load.
//
//! Isolated single-blob source admission and descriptor-identity regressions.

#[path = "../src/runtime/tiered-execution/port-outbound/blob_store.rs"]
pub mod blob_store;
#[path = "../src/runtime/tiered-execution/adapter-outbound/blob/main.rs"]
pub mod file_blob_store;
#[path = "../src/runtime/tiered-execution/adapter-outbound/fs_coord/main.rs"]
pub mod file_coordination;

use std::fs;
use std::io;
use std::num::NonZeroUsize;
#[cfg(unix)]
use std::os::unix::fs::symlink;
use std::path::{Path, PathBuf};
#[cfg(target_os = "linux")]
use std::process::Command;
use std::process::id;
use std::sync::atomic::{AtomicUsize, Ordering};

use blob_store::NativeContinuationBlobStore as _;
use file_blob_store::NativeContinuationFileBlobStore;
use malbolge as _;

static NEXT_FIXTURE: AtomicUsize = AtomicUsize::new(0);

struct Fixture(PathBuf);

impl Fixture {
    fn new() -> io::Result<Self> {
        let sequence = NEXT_FIXTURE.fetch_add(1, Ordering::Relaxed);
        let directory = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join(".temp")
            .join(format!("blob-source-{}-{sequence}", id()));
        #[expect(clippy::create_dir, reason = "isolated fixture directory")]
        fs::create_dir(&directory)?;
        Ok(Self(directory))
    }

    fn path(&self, name: &str) -> PathBuf {
        self.0.join(name)
    }
}

impl Drop for Fixture {
    fn drop(&mut self) {
        drop(fs::remove_dir_all(&self.0));
    }
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "test asserts source admission")]
fn stable_regular_source_loads_bounded_bytes() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let path = fixture.path("blob.bin");
    fs::write(&path, b"state").map_err(|error| error.to_string())?;
    let mut store = NativeContinuationFileBlobStore::new(path);
    let bound = NonZeroUsize::new(5).ok_or("missing bound")?;
    assert_eq!(store.load(bound), Ok(Some(b"state".to_vec())));
    Ok(())
}

#[cfg(target_os = "linux")]
#[test]
#[expect(clippy::panic_in_result_fn, reason = "test asserts source admission")]
fn swapped_fifo_cannot_block_after_regular_preflight() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let path = fixture.path("blob.bin");
    fs::write(&path, b"initial").map_err(|error| error.to_string())?;
    let before = fs::symlink_metadata(&path).map_err(|error| error.to_string())?;
    fs::remove_file(&path).map_err(|error| error.to_string())?;
    let status = Command::new("mkfifo")
        .arg(&path)
        .status()
        .map_err(|error| error.to_string())?;
    assert!(status.success());
    assert!(file_blob_store::open_bounded_blob_source(&path, &before).is_err());
    Ok(())
}

#[cfg(unix)]
#[test]
#[expect(clippy::panic_in_result_fn, reason = "test asserts source admission")]
fn swapped_symlink_cannot_redirect_after_regular_preflight() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let path = fixture.path("blob.bin");
    fs::write(&path, b"initial").map_err(|error| error.to_string())?;
    let before = fs::symlink_metadata(&path).map_err(|error| error.to_string())?;
    let foreign = fixture.path("foreign.bin");
    fs::rename(&path, &foreign).map_err(|error| error.to_string())?;
    symlink(&foreign, &path).map_err(|error| error.to_string())?;
    assert!(file_blob_store::open_bounded_blob_source(&path, &before).is_err());
    Ok(())
}

#[cfg(target_os = "linux")]
#[test]
#[expect(clippy::panic_in_result_fn, reason = "test asserts source admission")]
fn same_inode_relinked_path_is_not_the_opened_dentry() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let path = fixture.path("blob.bin");
    fs::write(&path, b"state").map_err(|error| error.to_string())?;
    let before = fs::symlink_metadata(&path).map_err(|error| error.to_string())?;
    let file = file_blob_store::open_bounded_blob_source(&path, &before)
        .map_err(|error| error.to_string())?;
    let alternate = fixture.path("alias.bin");
    fs::hard_link(&path, &alternate).map_err(|error| error.to_string())?;
    fs::rename(&path, fixture.path("parked.bin")).map_err(|error| error.to_string())?;
    fs::rename(&alternate, &path).map_err(|error| error.to_string())?;
    assert!(file_blob_store::verify_blob_source(&path, &file, &before).is_err());
    Ok(())
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "test asserts source admission")]
fn changed_source_metadata_invalidates_opened_file() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let path = fixture.path("blob.bin");
    fs::write(&path, b"state").map_err(|error| error.to_string())?;
    let before = fs::symlink_metadata(&path).map_err(|error| error.to_string())?;
    let file = file_blob_store::open_bounded_blob_source(&path, &before)
        .map_err(|error| error.to_string())?;
    fs::write(&path, b"modified longer source").map_err(|error| error.to_string())?;
    assert!(file_blob_store::verify_blob_source(&path, &file, &before).is_err());
    Ok(())
}

#[cfg(unix)]
#[test]
fn stable_symlink_parent_remains_valid() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let target_dir = fixture.path("real");
    #[expect(clippy::create_dir, reason = "isolated real parent")]
    fs::create_dir(&target_dir).map_err(|error| error.to_string())?;
    let parent_alias = fixture.path("alias");
    symlink(&target_dir, &parent_alias).map_err(|error| error.to_string())?;
    let path = parent_alias.join("blob.bin");
    fs::write(&path, b"allowed").map_err(|error| error.to_string())?;
    let before = fs::symlink_metadata(&path).map_err(|error| error.to_string())?;
    let file = file_blob_store::open_bounded_blob_source(&path, &before)
        .map_err(|error| error.to_string())?;
    file_blob_store::verify_blob_source(&path, &file, &before)
        .map_err(|error| error.to_string())?;
    Ok(())
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "test asserts source admission")]
fn missing_destination_remains_an_empty_load() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let mut store = NativeContinuationFileBlobStore::new(fixture.path("missing.bin"));
    let bound = NonZeroUsize::new(3).ok_or("missing bound")?;
    assert_eq!(store.load(bound), Ok(None));
    Ok(())
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "test asserts source admission")]
fn replaced_inode_cannot_pass_preopen_metadata() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let path = fixture.path("blob.bin");
    fs::write(&path, b"original").map_err(|error| error.to_string())?;
    let before = fs::symlink_metadata(&path).map_err(|error| error.to_string())?;
    let replacement = fixture.path("replacement.bin");
    fs::write(&replacement, b"original").map_err(|error| error.to_string())?;
    fs::rename(&replacement, &path).map_err(|error| error.to_string())?;
    assert!(file_blob_store::open_bounded_blob_source(&path, &before).is_err());
    Ok(())
}
