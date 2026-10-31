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
//   - Unix linked-inode lock admission and post-acquisition guard regressions.
// - Must-Not:
//   - Invent distributed lock semantics or modify protected package state.
// - Allows:
//   - Inputs: temporary local regular files and native hard-link aliases.
//   - Outputs: exact guard admission and identity rejection evidence.
//   - Side effects: test-local link creation and removal.
// - Split-When:
//   - Other operating systems require separate hard-link identity evidence.
// - Merge-When:
//   - One filesystem coordination regression suite owns all lock aliases.
// - Summary:
//   - A linked foreign inode must not become coordination lock authority.
// - Description:
//   - Rejects initial and late hard-link aliases for both guard modes.
// - Usage:
//   - Included by fs_coord/main.rs in Unix tiered-execution integration tests.
// - Defaults:
//   - Unique regular-file lock inodes remain admitted.
//

//! Hard-link refusal for shared and exclusive filesystem coordination locks.

use std::fs;
use std::io::ErrorKind;

use super::{NativeContinuationFileCoordination, NativeContinuationFileCoordinationError};
use crate::{file_blob_store_fixture, remove_file_blob_store_fixture};

#[test]
fn linked_foreign_lock_inode_is_rejected_before_acquisition() -> Result<(), String> {
    let fixture = file_blob_store_fixture("coordination-external-hard-link")?;
    let foreign = fixture.directory.join("foreign.lock");
    let link = fixture.directory.join("coordination.lock");
    fs::write(&foreign, b"foreign lock")
        .map_err(|error| format!("cannot create foreign lock: {error}"))?;
    fs::hard_link(&foreign, &link)
        .map_err(|error| format!("cannot create lock hard link: {error}"))?;
    let coordination = NativeContinuationFileCoordination::new(link);
    let expected = NativeContinuationFileCoordinationError::Open {
        kind: ErrorKind::InvalidData,
    };
    let exclusive = coordination.acquire_exclusive();
    let exclusive_rejected = matches!(exclusive, Err(error) if error == expected);
    drop(exclusive);
    let shared = coordination.acquire_shared();
    let accepted = exclusive_rejected && matches!(shared, Err(error) if error == expected);
    drop(shared);
    remove_file_blob_store_fixture(&fixture.directory)?;
    if accepted {
        Ok(())
    } else {
        Err(String::from("foreign linked lock was admitted"))
    }
}

#[test]
fn live_guards_reject_late_hard_link_alias() -> Result<(), String> {
    let fixture = file_blob_store_fixture("coordination-late-hard-link")?;
    let link = fixture.directory.join("coordination.lock");
    let alias = fixture.directory.join("new-alias.lock");
    let coordination = NativeContinuationFileCoordination::new(link.clone());
    let exclusive = coordination
        .acquire_exclusive()
        .map_err(|error| format!("exclusive lock failed: {error:?}"))?;
    let initially_exclusive = coordination.matches_exclusive(&exclusive);
    fs::hard_link(&link, &alias).map_err(|error| format!("cannot link held lock: {error}"))?;
    let rejected_exclusive = !coordination.matches_exclusive(&exclusive);
    drop(exclusive);
    fs::remove_file(&alias).map_err(|error| format!("cannot unlink lock alias: {error}"))?;
    let shared = coordination
        .acquire_shared()
        .map_err(|error| format!("shared lock failed: {error:?}"))?;
    let initially_shared = coordination.matches_shared(&shared);
    fs::hard_link(&link, &alias).map_err(|error| format!("cannot link shared lock: {error}"))?;
    let rejected_shared = !coordination.matches_shared(&shared);
    drop(shared);
    remove_file_blob_store_fixture(&fixture.directory)?;
    if initially_exclusive && initially_shared && rejected_exclusive && rejected_shared {
        Ok(())
    } else {
        Err(String::from("late hard-link guard alias was admitted"))
    }
}
