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

use std::fs::{self, File, OpenOptions};
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
    file: File,
    lock_path: PathBuf,
}

/// Non-cloneable shared filesystem coordination guard.
#[derive(Debug)]
pub struct NativeContinuationFileSharedGuard {
    file: File,
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
    ) -> Result<NativeContinuationFileExclusiveGuard, NativeContinuationFileCoordinationError> {
        let file = self.open_lock_file()?;
        file.lock()
            .map_err(|error| NativeContinuationFileCoordinationError::Lock {
                kind: error.kind(),
            })?;
        self.verify_lock_path(&file)?;
        Ok(NativeContinuationFileExclusiveGuard {
            file,
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
    ) -> Result<NativeContinuationFileSharedGuard, NativeContinuationFileCoordinationError> {
        let file = self.open_lock_file()?;
        file.lock_shared()
            .map_err(|error| NativeContinuationFileCoordinationError::Lock {
                kind: error.kind(),
            })?;
        self.verify_lock_path(&file)?;
        Ok(NativeContinuationFileSharedGuard {
            file,
            lock_path: self.lock_path.clone(),
        })
    }

    const fn invalid_lock_source() -> NativeContinuationFileCoordinationError {
        NativeContinuationFileCoordinationError::Open {
            kind: ErrorKind::InvalidData,
        }
    }

    fn lock_path_matches(&self, file: &File) -> bool {
        let Ok(opened) = file.metadata() else {
            return false;
        };
        let Ok(named) = fs::symlink_metadata(&self.lock_path) else {
            return false;
        };
        if !same_lock_file(&opened, &named) {
            return false;
        }
        #[cfg(target_os = "linux")]
        {
            use std::os::fd::AsRawFd as _;

            // A replaced parent or hard-link pathname can still name the
            // original inode. The opened dentry must itself remain at the
            // currently resolved configured path, not merely share its inode.
            let descriptor = format!("/proc/self/fd/{}", file.as_raw_fd());
            let Ok(opened_path) = fs::read_link(descriptor) else {
                return false;
            };
            let Ok(named_path) = fs::canonicalize(&self.lock_path) else {
                return false;
            };
            if opened_path != named_path {
                return false;
            }
        }
        true
    }

    /// Returns whether one exclusive guard belongs to this coordination path.
    #[must_use]
    pub fn matches_exclusive(&self, guard: &NativeContinuationFileExclusiveGuard) -> bool {
        self.lock_path.as_os_str() == guard.lock_path.as_os_str()
            && self.lock_path_matches(&guard.file)
    }

    /// Returns whether one shared guard belongs to this coordination path.
    #[must_use]
    pub fn matches_shared(&self, guard: &NativeContinuationFileSharedGuard) -> bool {
        self.lock_path.as_os_str() == guard.lock_path.as_os_str()
            && self.lock_path_matches(&guard.file)
    }

    /// Binds one coordinator to an explicit persistent lock path.
    #[must_use]
    pub const fn new(lock_path: PathBuf) -> Self {
        Self { lock_path }
    }

    fn open_lock_file(&self) -> Result<File, NativeContinuationFileCoordinationError> {
        // A FIFO, device or symlink must not become the shared advisory-lock
        // authority. In particular, non-regular nodes must be rejected before
        // any potentially blocking open on platforms without O_NONBLOCK.
        match fs::symlink_metadata(&self.lock_path) {
            Ok(metadata) if !metadata.is_file() => {
                return Err(Self::invalid_lock_source());
            }
            Err(error) if error.kind() != ErrorKind::NotFound => {
                return Err(NativeContinuationFileCoordinationError::Open { kind: error.kind() });
            }
            Ok(_) | Err(_) => {}
        }
        let mut options = OpenOptions::new();
        #[cfg(any(target_os = "linux", target_os = "android"))]
        {
            use std::os::unix::fs::OpenOptionsExt as _;

            // Linux asm-generic fcntl.h; regular files ignore O_NONBLOCK.
            const LINUX_O_NONBLOCK: i32 = 1 << 11;
            const LINUX_O_NOFOLLOW: i32 = 1 << 17;
            let _configured_flags = options.custom_flags(LINUX_O_NONBLOCK | LINUX_O_NOFOLLOW);
        };
        let file = options
            .read(true)
            .write(true)
            .create(true)
            .truncate(false)
            .open(&self.lock_path)
            .map_err(|error| NativeContinuationFileCoordinationError::Open {
                kind: error.kind(),
            })?;
        self.verify_lock_path(&file)?;
        Ok(file)
    }

    /// Returns the exact persistent lock path.
    #[must_use]
    pub fn path(&self) -> &Path {
        &self.lock_path
    }

    fn verify_lock_path(&self, file: &File) -> Result<(), NativeContinuationFileCoordinationError> {
        if self.lock_path_matches(file) {
            Ok(())
        } else {
            Err(Self::invalid_lock_source())
        }
    }
}

// Advisory-lock identity belongs to a regular inode, not just a pathname.
// Never follow a substituted final symlink when matching a held guard.
#[cfg(unix)]
fn same_lock_file(opened: &fs::Metadata, named: &fs::Metadata) -> bool {
    use std::os::unix::fs::MetadataExt as _;

    opened.is_file()
        && named.is_file()
        && opened.dev() == named.dev()
        && opened.ino() == named.ino()
}

#[cfg(windows)]
fn same_lock_file(opened: &fs::Metadata, named: &fs::Metadata) -> bool {
    use std::os::windows::fs::MetadataExt as _;

    opened.is_file()
        && named.is_file()
        && opened.volume_serial_number().is_some()
        && opened.volume_serial_number() == named.volume_serial_number()
        && opened.file_index().is_some()
        && opened.file_index() == named.file_index()
}

#[cfg(not(any(unix, windows)))]
const fn same_lock_file(_opened: &fs::Metadata, _named: &fs::Metadata) -> bool {
    // No portable identity API: do not authorize a guard on an unproved inode.
    false
}
