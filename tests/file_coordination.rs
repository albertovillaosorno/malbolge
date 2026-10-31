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
//   - Host-real persistent lock-file source admission and guard identity tests.
// - Must-Not:
//   - Grant transaction authority to a path that names a different lock inode.
// - Allows:
//   - Inputs: isolated lock paths, substituted regular and special nodes.
//   - Outputs: fail-closed acquisition and guard matching assertions.
//   - Side effects: isolated ignored test fixtures and OS advisory locks.
// - Split-When:
//   - Other filesystem coordination adapters require separate evidence.
// - Merge-When:
//   - A generic filesystem lock test harness subsumes this adapter.
// - Summary:
//   - Proves exact path and open-file identity for shared persistence locks.
// - Description:
//   - Checks fresh and replaced lock nodes, aliases, and prelocked guards.
// - Usage:
//   - `cargo test --test file_coordination`.
// - Defaults:
//   - Unexpected special or replaced lock paths cannot authorize transactions.
//
//! Host filesystem coordination admission and stale-guard regressions.

#[path = "../src/runtime/tiered-execution/adapter-outbound/fs_coord/main.rs"]
pub mod file_coordination;

// This standalone source-path test intentionally compiles without the library API.
use malbolge as _;

use file_coordination::{
    NativeContinuationFileCoordination as Coordination,
    NativeContinuationFileCoordinationError as CoordinationError,
};
use std::fs;
use std::io;
#[cfg(unix)]
use std::os::unix::fs::symlink;
use std::path::{Path, PathBuf};
#[cfg(target_os = "linux")]
use std::process::Command;
use std::process::id;
use std::sync::atomic::{AtomicUsize, Ordering};

static SEQUENCE: AtomicUsize = AtomicUsize::new(0);

struct Fixture(PathBuf);

impl Fixture {
    fn new() -> io::Result<Self> {
        let index = SEQUENCE.fetch_add(1, Ordering::Relaxed);
        let root = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join(".temp")
            .join(format!("file-coordination-{}-{index}", id()));
        #[expect(clippy::create_dir, reason = "test requires a fresh fixture")]
        fs::create_dir(&root)?;
        Ok(Self(root))
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
#[expect(clippy::panic_in_result_fn, reason = "assert guard authority")]
fn new_regular_lock_file_allows_both_guard_kinds() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let path = fixture.path("coordinator.lock");
    let coordinator = Coordination::new(path.clone());
    assert_eq!(coordinator.path(), path);
    let exclusive = coordinator
        .acquire_exclusive()
        .map_err(|error| format!("exclusive lock: {error:?}"))?;
    assert!(coordinator.matches_exclusive(&exclusive));
    assert!(
        fs::metadata(&path)
            .map_err(|error| error.to_string())?
            .is_file()
    );
    drop(exclusive);
    let shared = coordinator
        .acquire_shared()
        .map_err(|error| format!("shared lock: {error:?}"))?;
    assert!(coordinator.matches_shared(&shared));
    Ok(())
}

#[cfg(unix)]
#[test]
#[expect(clippy::panic_in_result_fn, reason = "reject symlink lock aliases")]
fn symlink_lock_file_is_rejected_without_following_target() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let target = fixture.path("sensitive");
    let alias = fixture.path("coordinator.lock");
    fs::write(&target, b"unchanged").map_err(|error| error.to_string())?;
    symlink(&target, &alias).map_err(|error| error.to_string())?;
    let coordinator = Coordination::new(alias);
    assert!(matches!(
        coordinator.acquire_exclusive(),
        Err(CoordinationError::Open { .. })
    ));
    assert!(matches!(
        coordinator.acquire_shared(),
        Err(CoordinationError::Open { .. })
    ));
    assert_eq!(
        fs::read(target).map_err(|error| error.to_string())?,
        b"unchanged"
    );
    Ok(())
}

#[cfg(target_os = "linux")]
#[test]
#[expect(clippy::panic_in_result_fn, reason = "reject FIFO lock sources")]
fn fifo_lock_file_is_rejected_before_acquiring_a_guard() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let fifo = fixture.path("coordinator.lock");
    let status = Command::new("mkfifo")
        .arg(&fifo)
        .status()
        .map_err(|error| error.to_string())?;
    assert!(status.success());
    let coordinator = Coordination::new(fifo);
    assert!(matches!(
        coordinator.acquire_exclusive(),
        Err(CoordinationError::Open { .. })
    ));
    assert!(matches!(
        coordinator.acquire_shared(),
        Err(CoordinationError::Open { .. })
    ));
    Ok(())
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "reject directory lock sources")]
fn directory_cannot_serve_as_persistent_lock_file() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let directory = fixture.path("coordinator.lock");
    #[expect(clippy::create_dir, reason = "fresh isolated test directory")]
    fs::create_dir(&directory).map_err(|error| error.to_string())?;
    let coordinator = Coordination::new(directory);
    assert!(matches!(
        coordinator.acquire_exclusive(),
        Err(CoordinationError::Open { .. })
    ));
    assert!(matches!(
        coordinator.acquire_shared(),
        Err(CoordinationError::Open { .. })
    ));
    Ok(())
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "stale lock cannot authorize")]
fn replaced_lock_inode_invalidates_previously_acquired_guard() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let path = fixture.path("coordinator.lock");
    let coordinator = Coordination::new(path.clone());
    let previous = coordinator
        .acquire_exclusive()
        .map_err(|error| format!("previous guard: {error:?}"))?;
    assert!(coordinator.matches_exclusive(&previous));
    fs::rename(&path, fixture.path("parked.lock")).map_err(|error| error.to_string())?;
    fs::write(&path, b"new inode").map_err(|error| error.to_string())?;
    assert!(!coordinator.matches_exclusive(&previous));
    let current = coordinator
        .acquire_exclusive()
        .map_err(|error| format!("new guard: {error:?}"))?;
    assert!(coordinator.matches_exclusive(&current));
    assert!(!coordinator.matches_exclusive(&previous));
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "stale shared guard cannot authorize"
)]
fn replaced_lock_inode_invalidates_shared_guard() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let path = fixture.path("coordinator.lock");
    let coordinator = Coordination::new(path.clone());
    let previous = coordinator
        .acquire_shared()
        .map_err(|error| format!("shared guard: {error:?}"))?;
    fs::rename(&path, fixture.path("parked.lock")).map_err(|error| error.to_string())?;
    fs::write(&path, b"new inode").map_err(|error| error.to_string())?;
    assert!(!coordinator.matches_shared(&previous));
    Ok(())
}

#[cfg(target_os = "linux")]
#[test]
#[expect(clippy::panic_in_result_fn, reason = "assert opened dentry identity")]
fn same_inode_hardlink_replacement_invalidates_exclusive_guard() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let path = fixture.path("coordinator.lock");
    let coordinator = Coordination::new(path.clone());
    let held = coordinator
        .acquire_exclusive()
        .map_err(|error| format!("exclusive guard: {error:?}"))?;
    let alternate = fixture.path("alternate.lock");
    fs::hard_link(&path, &alternate).map_err(|error| error.to_string())?;
    fs::rename(&path, fixture.path("parked.lock")).map_err(|error| error.to_string())?;
    fs::rename(&alternate, &path).map_err(|error| error.to_string())?;
    assert!(
        fs::metadata(&path)
            .map_err(|error| error.to_string())?
            .is_file()
    );
    assert!(
        !coordinator.matches_exclusive(&held),
        "a new pathname of the same inode was authorized by the old guard"
    );
    Ok(())
}

#[cfg(target_os = "linux")]
#[test]
#[expect(clippy::panic_in_result_fn, reason = "assert opened dentry identity")]
fn same_inode_hardlink_replacement_invalidates_shared_guard() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let path = fixture.path("coordinator.lock");
    let coordinator = Coordination::new(path.clone());
    let held = coordinator
        .acquire_shared()
        .map_err(|error| format!("shared guard: {error:?}"))?;
    let alternate = fixture.path("alternate.lock");
    fs::hard_link(&path, &alternate).map_err(|error| error.to_string())?;
    fs::rename(&path, fixture.path("parked.lock")).map_err(|error| error.to_string())?;
    fs::rename(&alternate, &path).map_err(|error| error.to_string())?;
    assert!(
        !coordinator.matches_shared(&held),
        "a new pathname of the same inode was authorized by the old guard"
    );
    Ok(())
}

#[cfg(unix)]
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "stable parent aliases stay usable"
)]
fn stable_symlink_parent_allows_new_regular_lock_file() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let directory = fixture.path("actual");
    #[expect(clippy::create_dir, reason = "fresh isolated directory")]
    fs::create_dir(&directory).map_err(|error| error.to_string())?;
    let alias = fixture.path("alias");
    symlink(&directory, &alias).map_err(|error| error.to_string())?;
    let coordinator = Coordination::new(alias.join("coordinator.lock"));
    let guard = coordinator
        .acquire_exclusive()
        .map_err(|error| format!("alias guard: {error:?}"))?;
    assert!(coordinator.matches_exclusive(&guard));
    assert!(directory.join("coordinator.lock").is_file());
    Ok(())
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "removed lock has no authority")]
fn unlinked_path_invalidates_a_live_shared_guard() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let path = fixture.path("coordinator.lock");
    let coordinator = Coordination::new(path.clone());
    let guard = coordinator
        .acquire_shared()
        .map_err(|error| format!("shared guard: {error:?}"))?;
    fs::remove_file(&path).map_err(|error| error.to_string())?;
    assert!(!coordinator.matches_shared(&guard));
    Ok(())
}

#[cfg(unix)]
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "symlink cannot borrow a lock guard"
)]
fn same_inode_symlink_substitution_invalidates_exclusive_guard() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let path = fixture.path("coordinator.lock");
    let parked = fixture.path("parked.lock");
    let coordinator = Coordination::new(path.clone());
    let guard = coordinator
        .acquire_exclusive()
        .map_err(|error| format!("exclusive guard: {error:?}"))?;
    fs::rename(&path, &parked).map_err(|error| error.to_string())?;
    symlink(&parked, &path).map_err(|error| error.to_string())?;
    assert!(!coordinator.matches_exclusive(&guard));
    assert!(matches!(
        coordinator.acquire_shared(),
        Err(CoordinationError::Open { .. })
    ));
    Ok(())
}

#[cfg(target_os = "linux")]
#[test]
#[expect(clippy::panic_in_result_fn, reason = "parent redirect loses authority")]
fn equal_inode_parent_symlink_replacement_invalidates_shared_guard() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let original = fixture.path("original");
    let foreign = fixture.path("foreign");
    let parked = fixture.path("parked");
    #[expect(clippy::create_dir, reason = "fresh isolated fixture directories")]
    fs::create_dir(&original).map_err(|error| error.to_string())?;
    #[expect(clippy::create_dir, reason = "fresh isolated fixture directories")]
    fs::create_dir(&foreign).map_err(|error| error.to_string())?;
    let path = original.join("coordinator.lock");
    let coordinator = Coordination::new(path.clone());
    let guard = coordinator
        .acquire_shared()
        .map_err(|error| format!("shared guard: {error:?}"))?;
    fs::hard_link(&path, foreign.join("coordinator.lock")).map_err(|error| error.to_string())?;
    fs::rename(&original, &parked).map_err(|error| error.to_string())?;
    symlink(&foreign, &original).map_err(|error| error.to_string())?;
    assert!(path.is_file());
    assert!(
        !coordinator.matches_shared(&guard),
        "parent redirect to same-inode hard link retained authority"
    );
    fs::remove_file(&original).map_err(|error| error.to_string())?;
    fs::rename(&parked, &original).map_err(|error| error.to_string())?;
    assert!(coordinator.matches_shared(&guard));
    Ok(())
}

#[cfg(target_os = "linux")]
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "assert OS advisory lock behavior"
)]
fn separate_descriptor_cannot_bypass_live_exclusive_guard() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let path = fixture.path("coordinator.lock");
    let coordinator = Coordination::new(path.clone());
    let held = coordinator
        .acquire_exclusive()
        .map_err(|error| format!("exclusive guard: {error:?}"))?;
    let challenger = fs::OpenOptions::new()
        .read(true)
        .write(true)
        .open(&path)
        .map_err(|error| error.to_string())?;
    assert!(matches!(
        challenger.try_lock(),
        Err(fs::TryLockError::WouldBlock)
    ));
    assert!(matches!(
        challenger.try_lock_shared(),
        Err(fs::TryLockError::WouldBlock)
    ));
    drop(held);
    challenger.try_lock().map_err(|error| error.to_string())?;
    Ok(())
}

#[cfg(target_os = "linux")]
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "assert shared OS advisory lock behavior"
)]
fn shared_guards_coexist_and_block_other_exclusive_descriptors() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let path = fixture.path("coordinator.lock");
    let original = Coordination::new(path.clone());
    let copy = Coordination::new(path.clone());
    let first = original
        .acquire_shared()
        .map_err(|error| format!("first shared guard: {error:?}"))?;
    let second = copy
        .acquire_shared()
        .map_err(|error| format!("second shared guard: {error:?}"))?;
    assert!(original.matches_shared(&first));
    assert!(copy.matches_shared(&second));
    let challenger = fs::OpenOptions::new()
        .read(true)
        .write(true)
        .open(&path)
        .map_err(|error| error.to_string())?;
    assert!(matches!(
        challenger.try_lock(),
        Err(fs::TryLockError::WouldBlock)
    ));
    drop(first);
    assert!(matches!(
        challenger.try_lock(),
        Err(fs::TryLockError::WouldBlock)
    ));
    drop(second);
    challenger.try_lock().map_err(|error| error.to_string())?;
    Ok(())
}
