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
//   - Filesystem binding for one preconfigured cached-retry telemetry blob.
// - Must-Not:
//   - Interpret telemetry bytes, choose byte limits, infer policy, or remove a
//     published destination before replacement.
// - Allows:
//   - Inputs: explicit destination path plus admitted bounded blob operations.
//   - Outputs: absent/present bytes or exact filesystem failure evidence.
//   - Side effects: bounded file reads and same-directory staged publication.
// - Split-When:
//   - Crash-durable directory syncing or multi-process locking gains semantics.
// - Merge-When:
//   - One filesystem adapter owns the same single-blob lifecycle everywhere.
// - Summary:
//   - Binds telemetry blob storage to fail-closed standard filesystem I/O.
// - Description:
//   - Staged bytes sync before rename; failed publication preserves
//     destination.
// - Usage:
//   - Construct with one explicit file path and pass through the blob-store
//     port.
// - Defaults:
//   - Missing files load as absent; staging never deletes a published blob.
//

//! Filesystem-backed outbound adapter for one cached-retry telemetry blob.

use std::fs::{self, File, OpenOptions};
use std::io::{ErrorKind, Read as _, Write as _};
use std::num::NonZeroUsize;
use std::path::{Path, PathBuf};
use std::process;
use std::sync::atomic::{AtomicU64, Ordering};

use crate::cached_retry_telemetry_blob_store::{
    NativeContinuationCachedRetryTelemetryBlobLoadResult,
    NativeContinuationCachedRetryTelemetryBlobStore,
};

const MAX_STAGING_ATTEMPTS: usize = 64;
static NEXT_STAGING_ID: AtomicU64 = AtomicU64::new(1);

/// Why filesystem-backed telemetry blob storage failed closed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationTelemetryFileBlobStoreError {
    /// Caller byte limit cannot be represented by the host read API.
    ByteLimitRepresentation {
        /// Exact positive bound that could not be represented.
        maximum_bytes: NonZeroUsize,
    },
    /// Configured destination does not name one file entry.
    InvalidDestination,
    /// A loaded file contained more bytes than the caller admitted.
    LoadByteLimit {
        /// Exact positive bound supplied by application orchestration.
        maximum_bytes: NonZeroUsize,
    },
    /// Opening an existing destination failed for a reason other than absence.
    Open {
        /// Host filesystem error category.
        kind: ErrorKind,
    },
    /// Publishing the fully synced staging file failed.
    Publish {
        /// Best-effort staging cleanup failure after publication rejection.
        cleanup: Option<ErrorKind>,
        /// Host filesystem publication error category.
        kind: ErrorKind,
    },
    /// Reading bounded destination bytes failed.
    Read {
        /// Host filesystem error category.
        kind: ErrorKind,
    },
    /// No collision-free staging filename was available in the retry budget.
    StagingExhausted,
    /// Creating one same-directory staging file failed.
    StagingOpen {
        /// Host filesystem error category.
        kind: ErrorKind,
    },
    /// The staging identifier space was exhausted without wrapping.
    StagingSequenceExhausted,
    /// Syncing complete staging bytes before publication failed.
    Sync {
        /// Best-effort staging cleanup failure after sync rejection.
        cleanup: Option<ErrorKind>,
        /// Host filesystem error category.
        kind: ErrorKind,
    },
    /// Writing complete admitted bytes to staging failed.
    Write {
        /// Best-effort staging cleanup failure after write rejection.
        cleanup: Option<ErrorKind>,
        /// Host filesystem error category.
        kind: ErrorKind,
    },
}

type NativeContinuationTelemetryStagingOpenResult =
    Result<(File, PathBuf), NativeContinuationTelemetryFileBlobStoreError>;

/// Filesystem-backed store for one explicit cached-retry telemetry blob path.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeContinuationTelemetryFileBlobStore {
    destination: PathBuf,
}

impl NativeContinuationTelemetryFileBlobStore {
    /// Returns the exact adapter-owned destination path.
    #[must_use]
    pub fn destination(&self) -> &Path {
        &self.destination
    }

    /// Binds one filesystem adapter to an explicit destination path.
    #[must_use]
    pub const fn new(destination: PathBuf) -> Self {
        Self { destination }
    }

    fn open_staging(&self) -> NativeContinuationTelemetryStagingOpenResult {
        for _attempt in 0..MAX_STAGING_ATTEMPTS {
            let staging_id = next_staging_id()?;
            let staging = self.staging_path(staging_id)?;
            match OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&staging)
            {
                Ok(file) => return Ok((file, staging)),
                Err(error) if error.kind() == ErrorKind::AlreadyExists => {},
                Err(error) => {
                    return Err(
                        NativeContinuationTelemetryFileBlobStoreError::
                            StagingOpen { kind: error.kind() },
                    );
                },
            }
        }
        Err(NativeContinuationTelemetryFileBlobStoreError::StagingExhausted)
    }

    fn staging_path(
        &self,
        staging_id: u64,
    ) -> Result<PathBuf, NativeContinuationTelemetryFileBlobStoreError> {
        let Some(file_name) = self.destination.file_name() else {
            return Err(
                NativeContinuationTelemetryFileBlobStoreError::
                    InvalidDestination,
            );
        };
        let mut staging_name = file_name.to_os_string();
        staging_name.push(format!(".stage.{}.{staging_id}", process::id()));
        Ok(self.destination.with_file_name(staging_name))
    }
}

impl NativeContinuationCachedRetryTelemetryBlobStore
    for NativeContinuationTelemetryFileBlobStore
{
    type Error = NativeContinuationTelemetryFileBlobStoreError;

    fn load(
        &mut self,
        maximum_bytes: NonZeroUsize,
    ) -> NativeContinuationCachedRetryTelemetryBlobLoadResult<Self::Error> {
        let mut file = match File::open(&self.destination) {
            Ok(file) => file,
            Err(error) if error.kind() == ErrorKind::NotFound => {
                return Ok(None);
            },
            Err(error) => {
                return Err(
                    NativeContinuationTelemetryFileBlobStoreError::Open {
                        kind: error.kind(),
                    },
                );
            },
        };
        let read_limit =
            u64::try_from(maximum_bytes.get()).map_err(|_error| {
                NativeContinuationTelemetryFileBlobStoreError::
                ByteLimitRepresentation { maximum_bytes }
            })?;
        let mut bytes = Vec::new();
        {
            let mut bounded = (&mut file).take(read_limit);
            let _read_bytes =
                bounded.read_to_end(&mut bytes).map_err(|error| {
                    NativeContinuationTelemetryFileBlobStoreError::Read {
                        kind: error.kind(),
                    }
                })?;
        }
        let mut extra = [0u8; 1];
        let extra_bytes = file.read(&mut extra).map_err(|error| {
            NativeContinuationTelemetryFileBlobStoreError::Read {
                kind: error.kind(),
            }
        })?;
        if extra_bytes == 0 {
            Ok(Some(bytes))
        } else {
            Err(
                NativeContinuationTelemetryFileBlobStoreError::LoadByteLimit {
                    maximum_bytes,
                },
            )
        }
    }

    fn replace(&mut self, bytes: &[u8]) -> Result<(), Self::Error> {
        let (mut staging_file, staging_path) = self.open_staging()?;
        if let Err(error) = staging_file.write_all(bytes) {
            drop(staging_file);
            return Err(NativeContinuationTelemetryFileBlobStoreError::Write {
                cleanup: cleanup_staging(&staging_path),
                kind: error.kind(),
            });
        }
        if let Err(error) = staging_file.sync_all() {
            drop(staging_file);
            return Err(NativeContinuationTelemetryFileBlobStoreError::Sync {
                cleanup: cleanup_staging(&staging_path),
                kind: error.kind(),
            });
        }
        drop(staging_file);
        if let Err(error) = fs::rename(&staging_path, &self.destination) {
            return Err(
                NativeContinuationTelemetryFileBlobStoreError::Publish {
                    cleanup: cleanup_staging(&staging_path),
                    kind: error.kind(),
                },
            );
        }
        Ok(())
    }
}

fn cleanup_staging(staging_path: &Path) -> Option<ErrorKind> {
    match fs::remove_file(staging_path) {
        Ok(()) => None,
        Err(error) if error.kind() == ErrorKind::NotFound => None,
        Err(error) => Some(error.kind()),
    }
}

fn next_staging_id()
-> Result<u64, NativeContinuationTelemetryFileBlobStoreError> {
    NEXT_STAGING_ID
        .try_update(Ordering::Relaxed, Ordering::Relaxed, |current| {
            current.checked_add(1)
        })
        .map_err(|_current| {
            NativeContinuationTelemetryFileBlobStoreError::
                StagingSequenceExhausted
        })
}
