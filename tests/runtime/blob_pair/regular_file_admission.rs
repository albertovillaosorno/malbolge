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
//   - Pair-file manifest and immutable member regular-file admission.
// - Must-Not:
//   - Modify the shared tiered-execution suite or select runtime policy.
// - Allows:
//   - Inputs: isolated manifest and generation member path fixtures.
//   - Outputs: exact typed regular-file rejection evidence.
//   - Side effects: ignored temporary fixture files in the repository.
// - Split-When:
//   - Cross-platform filesystem adversaries need separate host runners.
// - Merge-When:
//   - Pair-store host transport validation owns the same admission boundary.
// - Summary:
//   - Rejects linked and nonregular pair inputs before bounded reading.
// - Description:
//   - Uses exact manifest and member paths without a shared-test edit.
// - Usage:
//   - `cargo test --test tiered_execution file_blob_pair_store::regular_file_admission`.
// - Defaults:
//   - A nonregular or redirected path is never a pair-member byte source.
//
//! Filesystem pair-store regular-file admission regression fixtures.

use super::*;
#[cfg(unix)]
use std::os::unix::fs::symlink;
use std::sync::atomic::AtomicUsize;

static FIXTURE_NUMBER: AtomicUsize = AtomicUsize::new(0);

struct Fixture(PathBuf);

impl Fixture {
    fn manifest(&self) -> PathBuf {
        self.0.join("state.manifest")
    }

    fn new() -> Result<Self, String> {
        let number = FIXTURE_NUMBER.fetch_add(1, Ordering::Relaxed);
        let root = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join(".temp")
            .join(format!("pair-regular-admission-{}-{number}", process::id()));
        #[expect(
            clippy::create_dir,
            reason = "fresh fixture names avoid accidental reuse"
        )]
        fs::create_dir(&root).map_err(|error| error.to_string())?;
        Ok(Self(root))
    }
}

#[expect(clippy::missing_trait_methods, reason = "Fixture owns cleanup")]
impl Drop for Fixture {
    fn drop(&mut self) {
        drop(fs::remove_dir_all(&self.0));
    }
}

#[cfg(unix)]
#[test]
#[expect(clippy::panic_in_result_fn, reason = "assert typed admission error")]
fn manifest_symlink_is_rejected_before_read() -> Result<(), String> {
    let fixture = Fixture::new()?;
    let foreign = fixture.0.join("foreign-manifest");
    let manifest = fixture.manifest();
    fs::write(
        &foreign,
        encode_manifest(NativeContinuationFileBlobPairRevision {
            epoch: 42,
            generation: 1,
        }),
    )
    .map_err(|error| error.to_string())?;
    symlink(&foreign, &manifest).map_err(|error| error.to_string())?;
    let store = NativeContinuationFileBlobPairStore::new(manifest);
    assert_eq!(
        store.read_manifest(),
        Err(PairStoreError::ManifestOpen {
            kind: ErrorKind::InvalidData,
        })
    );
    Ok(())
}

#[cfg(unix)]
#[test]
#[expect(clippy::panic_in_result_fn, reason = "assert typed admission error")]
fn manifest_directory_is_rejected_before_read() -> Result<(), String> {
    let fixture = Fixture::new()?;
    let manifest = fixture.manifest();
    fs::create_dir_all(&manifest).map_err(|error| error.to_string())?;
    let store = NativeContinuationFileBlobPairStore::new(manifest);
    assert_eq!(
        store.read_manifest(),
        Err(PairStoreError::ManifestOpen {
            kind: ErrorKind::InvalidData,
        })
    );
    Ok(())
}

#[cfg(unix)]
#[test]
#[expect(clippy::panic_in_result_fn, reason = "assert typed member error")]
fn member_symlink_is_rejected_before_read() -> Result<(), String> {
    let fixture = Fixture::new()?;
    let store = NativeContinuationFileBlobPairStore::new(fixture.manifest());
    let revision = NativeContinuationFileBlobPairRevision {
        epoch: 42,
        generation: 1,
    };
    let member = NativeContinuationFileBlobPairMember::First;
    let name = store
        .generation_path(revision, member)
        .map_err(|error| format!("{error:?}"))?;
    let foreign = fixture.0.join("foreign-member");
    fs::write(&foreign, b"A").map_err(|error| error.to_string())?;
    symlink(&foreign, &name).map_err(|error| error.to_string())?;
    assert_eq!(
        store.read_generation_member(revision, member, NonZeroUsize::MIN),
        Err(PairStoreError::GenerationOpen {
            kind: ErrorKind::InvalidData,
            member
        })
    );
    Ok(())
}

#[cfg(unix)]
#[test]
#[expect(clippy::panic_in_result_fn, reason = "assert typed member error")]
fn member_directory_is_rejected_before_read() -> Result<(), String> {
    let fixture = Fixture::new()?;
    let store = NativeContinuationFileBlobPairStore::new(fixture.manifest());
    let revision = NativeContinuationFileBlobPairRevision {
        epoch: 42,
        generation: 1,
    };
    let member = NativeContinuationFileBlobPairMember::First;
    let name = store
        .generation_path(revision, member)
        .map_err(|error| format!("{error:?}"))?;
    fs::create_dir_all(&name).map_err(|error| error.to_string())?;
    assert_eq!(
        store.read_generation_member(revision, member, NonZeroUsize::MIN),
        Err(PairStoreError::GenerationOpen {
            kind: ErrorKind::InvalidData,
            member
        })
    );
    Ok(())
}

#[cfg(unix)]
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "reclamation must reject linked member"
)]
fn reclamation_validation_rejects_member_symlink() -> Result<(), String> {
    let fixture = Fixture::new()?;
    let store = NativeContinuationFileBlobPairStore::new(fixture.manifest());
    let revision = NativeContinuationFileBlobPairRevision {
        epoch: 42,
        generation: 1,
    };
    let foreign = fixture.0.join("foreign-member");
    fs::write(&foreign, b"A").map_err(|error| error.to_string())?;
    let first = store
        .generation_path(revision, NativeContinuationFileBlobPairMember::First)
        .map_err(|error| format!("{error:?}"))?;
    let second = store
        .generation_path(revision, NativeContinuationFileBlobPairMember::Second)
        .map_err(|error| format!("{error:?}"))?;
    symlink(&foreign, &first).map_err(|error| error.to_string())?;
    fs::write(&second, b"B").map_err(|error| error.to_string())?;
    assert_eq!(
        store.validate_generation_members(revision),
        Err(PairStoreError::GenerationOpen {
            kind: ErrorKind::InvalidData,
            member: NativeContinuationFileBlobPairMember::First,
        })
    );
    Ok(())
}

#[cfg(target_os = "linux")]
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "FIFO admission must be nonblocking"
)]
fn manifest_fifo_rejects_before_open() -> Result<(), String> {
    let fixture = Fixture::new()?;
    let manifest = fixture.manifest();
    let created = process::Command::new("mkfifo")
        .arg(&manifest)
        .status()
        .map_err(|error| error.to_string())?;
    if !created.success() {
        return Err(String::from("cannot create manifest FIFO fixture"));
    }
    let store = NativeContinuationFileBlobPairStore::new(manifest);
    assert_eq!(
        store.read_manifest(),
        Err(PairStoreError::ManifestOpen {
            kind: ErrorKind::InvalidData,
        })
    );
    Ok(())
}

#[cfg(target_os = "linux")]
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "FIFO admission must be nonblocking"
)]
fn member_fifo_rejects_before_open() -> Result<(), String> {
    let fixture = Fixture::new()?;
    let store = NativeContinuationFileBlobPairStore::new(fixture.manifest());
    let revision = NativeContinuationFileBlobPairRevision {
        epoch: 42,
        generation: 1,
    };
    let member = NativeContinuationFileBlobPairMember::First;
    let path = store
        .generation_path(revision, member)
        .map_err(|error| format!("{error:?}"))?;
    let created = process::Command::new("mkfifo")
        .arg(&path)
        .status()
        .map_err(|error| error.to_string())?;
    if !created.success() {
        return Err(String::from("cannot create member FIFO fixture"));
    }
    assert_eq!(
        store.read_generation_member(revision, member, NonZeroUsize::MIN),
        Err(PairStoreError::GenerationOpen {
            kind: ErrorKind::InvalidData,
            member
        })
    );
    Ok(())
}
