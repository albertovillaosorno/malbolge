// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - One explicit filesystem advisory-lock path shared by cooperating runtime
//     adapters.
// - Must-Not:
//   - Interpret protected state, choose transaction policy, or expose an
//     unlocked mutation capability.
// - Allows:
//   - Inputs: explicit lock path and shared/exclusive acquisition requests.
//   - Outputs: non-cloneable lock guards or exact host lock failure evidence.
//   - Side effects: creates/opens the persistent lock file and acquires one
//     operating-system advisory lock.
// - Split-When:
//   - Distributed coordination or non-filesystem lock backends gain semantics.
// - Merge-When:
//   - Another filesystem component owns the exact same lock lifecycle.
// - Summary:
//   - Coordinates multiple filesystem adapters through one explicit lock path.
// - Description:
//   - Guard identity is the exact configured lock path; dropping a guard
//     releases its operating-system lock.
// - Usage:
//   - Clone one coordinator into every adapter participating in one local
//     transaction domain.
// - Defaults:
//   - No path inference or transaction semantics exist in this module.
//

//! Shared filesystem coordination for cooperating tiered-execution adapters.

use std::fs::{File, OpenOptions};
use std::io::ErrorKind;
use std::path::{Path, PathBuf};

/// Why one filesystem coordination lock could not be acquired.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationFileCoordinationError {
    /// Acquiring the requested advisory lock failed.
    Lock {
        /// Host filesystem error category.
        kind: ErrorKind,
    },
    /// Opening or creating the configured lock file failed.
    Open {
        /// Host filesystem error category.
        kind: ErrorKind,
    },
}

/// Filesystem coordination identity shared by cooperating adapters.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeContinuationFileCoordination {
    lock_path: PathBuf,
}

/// Non-cloneable exclusive filesystem coordination guard.
#[derive(Debug)]
pub struct NativeContinuationFileExclusiveGuard {
    _file: File,
    lock_path: PathBuf,
}

/// Non-cloneable shared filesystem coordination guard.
#[derive(Debug)]
pub struct NativeContinuationFileSharedGuard {
    _file: File,
    lock_path: PathBuf,
}

impl NativeContinuationFileCoordination {
    /// Acquires one exclusive advisory lock for the configured path.
    ///
    /// # Errors
    ///
    /// Returns exact lock-file open or lock acquisition evidence.
    pub fn acquire_exclusive(
        &self,
    ) -> Result<
        NativeContinuationFileExclusiveGuard,
        NativeContinuationFileCoordinationError,
    > {
        let file = self.open_lock_file()?;
        file.lock().map_err(|error| {
            NativeContinuationFileCoordinationError::Lock { kind: error.kind() }
        })?;
        Ok(NativeContinuationFileExclusiveGuard {
            _file: file,
            lock_path: self.lock_path.clone(),
        })
    }

    /// Acquires one shared advisory lock for the configured path.
    ///
    /// # Errors
    ///
    /// Returns exact lock-file open or lock acquisition evidence.
    pub fn acquire_shared(
        &self,
    ) -> Result<
        NativeContinuationFileSharedGuard,
        NativeContinuationFileCoordinationError,
    > {
        let file = self.open_lock_file()?;
        file.lock_shared().map_err(|error| {
            NativeContinuationFileCoordinationError::Lock { kind: error.kind() }
        })?;
        Ok(NativeContinuationFileSharedGuard {
            _file: file,
            lock_path: self.lock_path.clone(),
        })
    }

    /// Returns whether one exclusive guard belongs to this coordination path.
    #[must_use]
    pub fn matches_exclusive(
        &self,
        guard: &NativeContinuationFileExclusiveGuard,
    ) -> bool {
        self.lock_path.as_os_str() == guard.lock_path.as_os_str()
    }

    /// Returns whether one shared guard belongs to this coordination path.
    #[must_use]
    pub fn matches_shared(
        &self,
        guard: &NativeContinuationFileSharedGuard,
    ) -> bool {
        self.lock_path.as_os_str() == guard.lock_path.as_os_str()
    }

    /// Binds one coordinator to an explicit persistent lock path.
    #[must_use]
    pub const fn new(lock_path: PathBuf) -> Self {
        Self { lock_path }
    }

    fn open_lock_file(
        &self,
    ) -> Result<File, NativeContinuationFileCoordinationError> {
        OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .truncate(false)
            .open(&self.lock_path)
            .map_err(|error| NativeContinuationFileCoordinationError::Open {
                kind: error.kind(),
            })
    }

    /// Returns the exact persistent lock path.
    #[must_use]
    pub fn path(&self) -> &Path {
        &self.lock_path
    }
}
