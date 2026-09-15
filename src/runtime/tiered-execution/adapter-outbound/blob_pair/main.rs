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
//   - Filesystem binding for one preconfigured atomic opaque blob pair.
// - Must-Not:
//   - Interpret payload bytes, choose byte limits, infer policy, or expose a
//     partially published generation.
// - Allows:
//   - Inputs: explicit manifest path plus admitted bounded pair operations.
//   - Outputs: missing/present pair bytes or exact filesystem failure evidence.
//   - Side effects: immutable generation writes, atomic manifest replacement,
//     and explicit superseded-generation reclamation.
// - Split-When:
//   - Reclamation scheduling or N-object transactions gain semantics.
// - Merge-When:
//   - One filesystem adapter owns this exact generation-pointer lifecycle.
// - Summary:
//   - Binds atomic opaque blob-pair storage to filesystem generation
//     indirection.
// - Description:
//   - One stable lock coordinates reads, publication, and explicit reclamation.
// - Usage:
//   - Construct with one explicit manifest path and pass through pair-store
//     port.
// - Defaults:
//   - Missing manifest means absent pair; unreferenced generations are ignored.
//

//! Filesystem-backed atomic pair store using immutable generations plus
//! manifest.

use std::fs::{self, File, OpenOptions};
use std::io::{ErrorKind, Read as _, Write as _};
use std::num::NonZeroUsize;
use std::path::{Path, PathBuf};
use std::process;
use std::sync::atomic::{AtomicU64, Ordering};

use crate::blob_pair_store::{
    NativeContinuationBlobPair,
    NativeContinuationBlobPairConditionalPublication,
    NativeContinuationBlobPairConditionalRequest,
    NativeContinuationBlobPairLoadResult, NativeContinuationBlobPairStore,
    NativeContinuationConditionalBlobPairStore,
    NativeContinuationDurableBlobPairStore,
    NativeContinuationReclaimableBlobPairStore,
    NativeContinuationVersionedBlobPair,
};

const MANIFEST_BYTES: usize = 24;
const MANIFEST_MAGIC: [u8; 8] = *b"MBPPAIR1";
const MAX_STAGING_ATTEMPTS: usize = 64;
static NEXT_PAIR_ID: AtomicU64 = AtomicU64::new(1);

/// Which immutable pair member one filesystem error concerns.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationFileBlobPairMember {
    /// First opaque pair member.
    First,
    /// Second opaque pair member.
    Second,
}

/// Why post-publication pair durability confirmation failed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationFileBlobPairDurabilityError {
    /// Configured manifest does not expose a parent directory.
    InvalidManifest,
    /// Opening the manifest directory failed after pair publication.
    OpenDirectory {
        /// Host filesystem error category.
        kind: ErrorKind,
    },
    /// Synchronizing the manifest directory failed after pair publication.
    SyncDirectory {
        /// Host filesystem error category.
        kind: ErrorKind,
    },
}

/// Why one filesystem-backed atomic pair operation failed closed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationFileBlobPairStoreError {
    /// Caller byte limit cannot be represented by the host read API.
    ByteLimitRepresentation {
        /// Exact positive bound that could not be represented.
        maximum_bytes: NonZeroUsize,
        /// Pair member whose read required the bound.
        member: NativeContinuationFileBlobPairMember,
    },
    /// No collision-free immutable generation was available in the retry
    /// budget.
    GenerationExhausted,
    /// Opening one immutable generation member failed.
    GenerationOpen {
        /// Host filesystem error category.
        kind: ErrorKind,
        /// Pair member that could not be opened.
        member: NativeContinuationFileBlobPairMember,
    },
    /// Reading one immutable generation member failed.
    GenerationRead {
        /// Host filesystem error category.
        kind: ErrorKind,
        /// Pair member that could not be read.
        member: NativeContinuationFileBlobPairMember,
    },
    /// Synchronizing one complete immutable generation member failed.
    GenerationSync {
        /// Host filesystem error category.
        kind: ErrorKind,
        /// Pair member that could not be synchronized.
        member: NativeContinuationFileBlobPairMember,
    },
    /// Writing one complete immutable generation member failed.
    GenerationWrite {
        /// Host filesystem error category.
        kind: ErrorKind,
        /// Pair member that could not be written.
        member: NativeContinuationFileBlobPairMember,
    },
    /// Configured manifest does not name one file entry.
    InvalidManifest,
    /// One immutable generation member exceeded its admitted byte limit.
    LoadByteLimit {
        /// Positive caller-configured byte limit.
        maximum_bytes: NonZeroUsize,
        /// Pair member that exceeded its bound.
        member: NativeContinuationFileBlobPairMember,
    },
    /// Acquiring the stable sibling pair-operation lock failed.
    Lock {
        /// Host filesystem error category.
        kind: ErrorKind,
    },
    /// Opening the stable sibling pair-operation lock failed.
    LockOpen {
        /// Host filesystem error category.
        kind: ErrorKind,
    },
    /// Manifest generation identifier was noncanonical zero.
    ManifestGenerationZero,
    /// Manifest magic or revision was not canonical.
    ManifestMagic,
    /// Opening an existing manifest failed for a reason other than absence.
    ManifestOpen {
        /// Host filesystem error category.
        kind: ErrorKind,
    },
    /// Publishing the fully synced staging manifest failed.
    ManifestPublish {
        /// Best-effort staging cleanup failure after publication rejection.
        cleanup: Option<ErrorKind>,
        /// Host filesystem publication error category.
        kind: ErrorKind,
    },
    /// Reading the current manifest failed.
    ManifestRead {
        /// Host filesystem error category.
        kind: ErrorKind,
    },
    /// Manifest byte length was not exactly the canonical fixed size.
    ManifestSize {
        /// Exact observed manifest byte count, including an extra-byte probe.
        observed_bytes: usize,
    },
    /// No collision-free staging manifest was available in the retry budget.
    ManifestStagingExhausted,
    /// Creating one staging manifest failed.
    ManifestStagingOpen {
        /// Host filesystem error category.
        kind: ErrorKind,
    },
    /// Synchronizing the complete staging manifest failed.
    ManifestSync {
        /// Best-effort staging cleanup failure after synchronization
        /// rejection.
        cleanup: Option<ErrorKind>,
        /// Host filesystem error category.
        kind: ErrorKind,
    },
    /// Writing the complete staging manifest failed.
    ManifestWrite {
        /// Best-effort staging cleanup failure after write rejection.
        cleanup: Option<ErrorKind>,
        /// Host filesystem error category.
        kind: ErrorKind,
    },
    /// Process/generation identifier space was exhausted without wrapping.
    SequenceExhausted,
}

/// One exact generation-member deletion that failed during reclamation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeContinuationFileBlobPairReclamationFailure {
    kind: ErrorKind,
    path: PathBuf,
}

/// Completed explicit generation-reclamation evidence.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationFileBlobPairReclamation {
    /// Every eligible deletion and directory durability confirmation succeeded.
    Durable {
        /// Exact generation-member paths removed by this pass.
        removed: Vec<PathBuf>,
    },
    /// At least one eligible generation member could not be removed.
    Partial {
        /// Post-removal directory durability failure, when confirmation
        /// failed.
        durability_error: Option<NativeContinuationFileBlobPairDurabilityError>,
        /// Exact generation-member removal failures retained for retry.
        failures: Vec<NativeContinuationFileBlobPairReclamationFailure>,
        /// Exact generation-member paths removed before or beside failures.
        removed: Vec<PathBuf>,
    },
    /// All eligible removals succeeded but directory durability failed.
    Published {
        /// Exact post-removal directory durability failure.
        durability_error: NativeContinuationFileBlobPairDurabilityError,
        /// Exact generation-member paths already removed by this pass.
        removed: Vec<PathBuf>,
    },
}

/// Why explicit generation reclamation failed before deletion could proceed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationFileBlobPairReclamationError {
    /// Reading one directory entry failed before cleanup began.
    DirectoryEntry {
        /// Host filesystem error category.
        kind: ErrorKind,
    },
    /// Opening the manifest directory for enumeration failed.
    DirectoryOpen {
        /// Host filesystem error category.
        kind: ErrorKind,
    },
    /// Manifest filename cannot be matched safely as UTF-8 generation prefix.
    ManifestName,
    /// Locking or reading the current manifest failed before deletion began.
    Store(NativeContinuationFileBlobPairStoreError),
}

/// Result of one explicit generation-reclamation pass.
pub type NativeContinuationFileBlobPairReclamationResult = Result<
    NativeContinuationFileBlobPairReclamation,
    NativeContinuationFileBlobPairReclamationError,
>;

/// Opaque filesystem publication revision for one committed blob pair.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationFileBlobPairRevision {
    generation: u64,
    process: u64,
}

/// Filesystem-backed pair store rooted at one explicit manifest path.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeContinuationFileBlobPairStore {
    manifest: PathBuf,
}

type PairStoreError = NativeContinuationFileBlobPairStoreError;

type NativeContinuationFileBlobPairRevisionOpenResult = Result<
    (
        NativeContinuationFileBlobPairRevision,
        File,
        PathBuf,
        File,
        PathBuf,
    ),
    NativeContinuationFileBlobPairStoreError,
>;

type PairManifestStagingOpenResult =
    Result<(File, PathBuf), NativeContinuationFileBlobPairStoreError>;

impl NativeContinuationFileBlobPairReclamation {
    /// Borrows post-removal durability failure, when confirmation failed.
    #[must_use]
    pub const fn durability_error(
        &self,
    ) -> Option<&NativeContinuationFileBlobPairDurabilityError> {
        match self {
            Self::Durable { .. } => None,
            Self::Partial { durability_error, .. } => durability_error.as_ref(),
            Self::Published { durability_error, .. } => Some(durability_error),
        }
    }

    /// Borrows exact generation-member removal failures retained for retry.
    #[must_use]
    pub fn failures(
        &self,
    ) -> &[NativeContinuationFileBlobPairReclamationFailure] {
        match self {
            Self::Partial { failures, .. } => failures,
            Self::Durable { .. } | Self::Published { .. } => &[],
        }
    }

    /// Borrows exact generation-member paths removed by this pass.
    #[must_use]
    pub fn removed(&self) -> &[PathBuf] {
        match self {
            Self::Durable { removed }
            | Self::Partial { removed, .. }
            | Self::Published { removed, .. } => removed,
        }
    }
}

impl NativeContinuationFileBlobPairReclamationFailure {
    /// Returns the host filesystem error category for this failed removal.
    #[must_use]
    pub const fn kind(&self) -> ErrorKind {
        self.kind
    }

    /// Borrows the exact generation-member path whose removal failed.
    #[must_use]
    pub fn path(&self) -> &Path {
        &self.path
    }
}

impl NativeContinuationFileBlobPairStore {
    fn generation_path(
        &self,
        generation: NativeContinuationFileBlobPairRevision,
        member: NativeContinuationFileBlobPairMember,
    ) -> Result<PathBuf, NativeContinuationFileBlobPairStoreError> {
        let Some(file_name) = self.manifest.file_name() else {
            return Err(
                NativeContinuationFileBlobPairStoreError::InvalidManifest,
            );
        };
        let suffix = match member {
            NativeContinuationFileBlobPairMember::First => "first",
            NativeContinuationFileBlobPairMember::Second => "second",
        };
        let mut generation_name = file_name.to_os_string();
        generation_name.push(format!(
            ".generation.{}.{generation_id}.{suffix}",
            generation.process,
            generation_id = generation.generation,
        ));
        Ok(self.manifest.with_file_name(generation_name))
    }

    fn lock_path(
        &self,
    ) -> Result<PathBuf, NativeContinuationFileBlobPairStoreError> {
        let Some(file_name) = self.manifest.file_name() else {
            return Err(
                NativeContinuationFileBlobPairStoreError::InvalidManifest,
            );
        };
        let mut lock_name = file_name.to_os_string();
        lock_name.push(".lock");
        Ok(self.manifest.with_file_name(lock_name))
    }

    /// Returns the exact adapter-owned manifest path.
    #[must_use]
    pub fn manifest(&self) -> &Path {
        &self.manifest
    }

    fn manifest_directory(
        &self,
    ) -> Result<&Path, NativeContinuationFileBlobPairDurabilityError> {
        let Some(parent) = self.manifest.parent() else {
            return Err(
                NativeContinuationFileBlobPairDurabilityError::InvalidManifest,
            );
        };
        if parent.as_os_str().is_empty() {
            Ok(Path::new("."))
        } else {
            Ok(parent)
        }
    }

    fn manifest_staging_path(
        &self,
        staging_id: u64,
    ) -> Result<PathBuf, NativeContinuationFileBlobPairStoreError> {
        let Some(file_name) = self.manifest.file_name() else {
            return Err(
                NativeContinuationFileBlobPairStoreError::InvalidManifest,
            );
        };
        let mut staging_name = file_name.to_os_string();
        staging_name.push(format!(".stage.{}.{staging_id}", process::id()));
        Ok(self.manifest.with_file_name(staging_name))
    }

    /// Binds one filesystem pair adapter to an explicit manifest path.
    #[must_use]
    pub const fn new(manifest: PathBuf) -> Self {
        Self { manifest }
    }

    fn open_generation(
        &self,
    ) -> NativeContinuationFileBlobPairRevisionOpenResult {
        for _attempt in 0..MAX_STAGING_ATTEMPTS {
            let generation = NativeContinuationFileBlobPairRevision {
                generation: next_pair_id()?,
                process: u64::from(process::id()),
            };
            let first_path = self.generation_path(
                generation,
                NativeContinuationFileBlobPairMember::First,
            )?;
            let first = match OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&first_path)
            {
                Ok(file) => file,
                Err(error) if error.kind() == ErrorKind::AlreadyExists => {
                    continue;
                },
                Err(error) => {
                    return Err(PairStoreError::GenerationOpen {
                        kind: error.kind(),
                        member: NativeContinuationFileBlobPairMember::First,
                    });
                },
            };
            let second_path = self.generation_path(
                generation,
                NativeContinuationFileBlobPairMember::Second,
            )?;
            match OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&second_path)
            {
                Ok(second) => {
                    return Ok((
                        generation,
                        first,
                        first_path,
                        second,
                        second_path,
                    ));
                },
                Err(error) if error.kind() == ErrorKind::AlreadyExists => {
                    drop(first);
                    let _cleanup = fs::remove_file(&first_path);
                },
                Err(error) => {
                    return Err(PairStoreError::GenerationOpen {
                        kind: error.kind(),
                        member: NativeContinuationFileBlobPairMember::Second,
                    });
                },
            }
        }
        Err(NativeContinuationFileBlobPairStoreError::GenerationExhausted)
    }

    fn open_manifest_staging(&self) -> PairManifestStagingOpenResult {
        for _attempt in 0..MAX_STAGING_ATTEMPTS {
            let staging = self.manifest_staging_path(next_pair_id()?)?;
            match OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&staging)
            {
                Ok(file) => return Ok((file, staging)),
                Err(error) if error.kind() == ErrorKind::AlreadyExists => {},
                Err(error) => {
                    return Err(PairStoreError::ManifestStagingOpen {
                        kind: error.kind(),
                    });
                },
            }
        }
        Err(NativeContinuationFileBlobPairStoreError::ManifestStagingExhausted)
    }

    fn open_publication_lock(
        &self,
    ) -> Result<File, NativeContinuationFileBlobPairStoreError> {
        let file = OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .truncate(false)
            .open(self.lock_path()?)
            .map_err(|error| {
                NativeContinuationFileBlobPairStoreError::LockOpen {
                    kind: error.kind(),
                }
            })?;
        file.lock().map_err(|error| {
            NativeContinuationFileBlobPairStoreError::Lock {
                kind: error.kind(),
            }
        })?;
        Ok(file)
    }

    fn open_read_lock(
        &self,
    ) -> Result<File, NativeContinuationFileBlobPairStoreError> {
        let file = OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .truncate(false)
            .open(self.lock_path()?)
            .map_err(|error| {
                NativeContinuationFileBlobPairStoreError::LockOpen {
                    kind: error.kind(),
                }
            })?;
        file.lock_shared().map_err(|error| {
            NativeContinuationFileBlobPairStoreError::Lock {
                kind: error.kind(),
            }
        })?;
        Ok(file)
    }

    #[cfg(test)]
    pub(crate) fn open_read_lock_for_test(
        &self,
    ) -> Result<File, NativeContinuationFileBlobPairStoreError> {
        self.open_read_lock()
    }

    fn publish_manifest(
        &self,
        generation: NativeContinuationFileBlobPairRevision,
    ) -> Result<(), NativeContinuationFileBlobPairStoreError> {
        let bytes = encode_manifest(generation);
        let (mut staging, staging_path) = self.open_manifest_staging()?;
        if let Err(error) = staging.write_all(&bytes) {
            drop(staging);
            return Err(
                NativeContinuationFileBlobPairStoreError::ManifestWrite {
                    cleanup: cleanup_staging(&staging_path),
                    kind: error.kind(),
                },
            );
        }
        if let Err(error) = staging.sync_all() {
            drop(staging);
            return Err(
                NativeContinuationFileBlobPairStoreError::ManifestSync {
                    cleanup: cleanup_staging(&staging_path),
                    kind: error.kind(),
                },
            );
        }
        drop(staging);
        if let Err(error) = fs::rename(&staging_path, &self.manifest) {
            return Err(
                NativeContinuationFileBlobPairStoreError::ManifestPublish {
                    cleanup: cleanup_staging(&staging_path),
                    kind: error.kind(),
                },
            );
        }
        Ok(())
    }

    fn read_generation_member(
        &self,
        generation: NativeContinuationFileBlobPairRevision,
        member: NativeContinuationFileBlobPairMember,
        maximum_bytes: NonZeroUsize,
    ) -> Result<Vec<u8>, NativeContinuationFileBlobPairStoreError> {
        let mut file = File::open(self.generation_path(generation, member)?)
            .map_err(|error| PairStoreError::GenerationOpen {
                kind: error.kind(),
                member,
            })?;
        let read_limit = u64::try_from(maximum_bytes.get()).map_err(|_error| {
            NativeContinuationFileBlobPairStoreError::ByteLimitRepresentation {
                maximum_bytes,
                member,
            }
        })?;
        let mut bytes = Vec::new();
        {
            let mut bounded = (&mut file).take(read_limit);
            let _read = bounded.read_to_end(&mut bytes).map_err(|error| {
                NativeContinuationFileBlobPairStoreError::GenerationRead {
                    kind: error.kind(),
                    member,
                }
            })?;
        }
        let mut extra = [0u8; 1];
        let extra_bytes = file.read(&mut extra).map_err(|error| {
            NativeContinuationFileBlobPairStoreError::GenerationRead {
                kind: error.kind(),
                member,
            }
        })?;
        if extra_bytes == 0 {
            Ok(bytes)
        } else {
            Err(NativeContinuationFileBlobPairStoreError::LoadByteLimit {
                maximum_bytes,
                member,
            })
        }
    }

    fn read_manifest(
        &self,
    ) -> Result<Option<NativeContinuationFileBlobPairRevision>, PairStoreError>
    {
        let mut file = match File::open(&self.manifest) {
            Ok(file) => file,
            Err(error) if error.kind() == ErrorKind::NotFound => {
                return Ok(None);
            },
            Err(error) => {
                return Err(
                    NativeContinuationFileBlobPairStoreError::ManifestOpen {
                        kind: error.kind(),
                    },
                );
            },
        };
        let mut bytes = Vec::with_capacity(MANIFEST_BYTES + 1);
        let mut bounded = (&mut file).take(25);
        let _read = bounded.read_to_end(&mut bytes).map_err(|error| {
            NativeContinuationFileBlobPairStoreError::ManifestRead {
                kind: error.kind(),
            }
        })?;
        decode_manifest(&bytes).map(Some)
    }

    /// Reclaims every superseded generation member owned by this manifest.
    ///
    /// # Errors
    ///
    /// Returns only pre-deletion lock, manifest, directory-open,
    /// directory-entry, or manifest-name failures. Removal and post-removal
    /// durability failures are committed cleanup evidence in the successful
    /// result.
    pub fn reclaim_generations(
        &mut self,
    ) -> NativeContinuationFileBlobPairReclamationResult {
        self.reclaim_generations_preserving(&[])
    }

    /// Reclaims superseded generation members except exact caller-preserved
    /// revisions.
    ///
    /// The current manifest generation is always preserved independently of the
    /// caller-provided revision set. Revision equality is the only retention
    /// relation interpreted by this adapter.
    ///
    /// # Errors
    ///
    /// Returns only pre-deletion lock, manifest, directory-open,
    /// directory-entry, or manifest-name failures. Removal and post-removal
    /// durability failures are committed cleanup evidence in the successful
    /// result.
    pub fn reclaim_generations_preserving(
        &mut self,
        preserved: &[NativeContinuationFileBlobPairRevision],
    ) -> NativeContinuationFileBlobPairReclamationResult {
        let _lock = self
            .open_publication_lock()
            .map_err(NativeContinuationFileBlobPairReclamationError::Store)?;
        let current = self
            .read_manifest()
            .map_err(NativeContinuationFileBlobPairReclamationError::Store)?;
        if let Some(current_revision) = current {
            self.validate_generation_members(current_revision).map_err(
                NativeContinuationFileBlobPairReclamationError::Store,
            )?;
        }
        let candidates = self.reclamation_candidates(current, preserved)?;
        let mut failures = Vec::new();
        let mut removed = Vec::new();
        for path in candidates {
            match fs::remove_file(&path) {
                Ok(()) => removed.push(path),
                Err(error) if error.kind() == ErrorKind::NotFound => {},
                Err(error) => {
                    failures.push(
                        NativeContinuationFileBlobPairReclamationFailure {
                            kind: error.kind(),
                            path,
                        },
                    );
                },
            }
        }
        let durability_error = if removed.is_empty() {
            None
        } else {
            self.confirm_pair_durability().err()
        };
        if failures.is_empty() {
            if let Some(durability_failure) = durability_error {
                Ok(NativeContinuationFileBlobPairReclamation::Published {
                    durability_error: durability_failure,
                    removed,
                })
            } else {
                Ok(NativeContinuationFileBlobPairReclamation::Durable {
                    removed,
                })
            }
        } else {
            Ok(NativeContinuationFileBlobPairReclamation::Partial {
                durability_error,
                failures,
                removed,
            })
        }
    }

    fn reclamation_candidate(
        &self,
        path: &Path,
        manifest_name: &str,
    ) -> Result<
        Option<NativeContinuationFileBlobPairRevision>,
        NativeContinuationFileBlobPairStoreError,
    > {
        let Some(file_name) = path.file_name().and_then(|name| name.to_str())
        else {
            return Ok(None);
        };
        let prefix = format!("{manifest_name}.generation.");
        let Some(remainder) = file_name.strip_prefix(&prefix) else {
            return Ok(None);
        };
        let mut parts = remainder.split('.');
        let (
            Some(process_text),
            Some(generation_text),
            Some(member_text),
            None,
        ) = (parts.next(), parts.next(), parts.next(), parts.next())
        else {
            return Ok(None);
        };
        let Ok(process_id) = process_text.parse::<u64>() else {
            return Ok(None);
        };
        let Ok(generation_id) = generation_text.parse::<u64>() else {
            return Ok(None);
        };
        if generation_id == 0 {
            return Ok(None);
        }
        let member = match member_text {
            "first" => NativeContinuationFileBlobPairMember::First,
            "second" => NativeContinuationFileBlobPairMember::Second,
            _ => return Ok(None),
        };
        let revision = NativeContinuationFileBlobPairRevision {
            generation: generation_id,
            process: process_id,
        };
        if self.generation_path(revision, member)? == path {
            Ok(Some(revision))
        } else {
            Ok(None)
        }
    }

    fn reclamation_candidates(
        &self,
        current: Option<NativeContinuationFileBlobPairRevision>,
        preserved: &[NativeContinuationFileBlobPairRevision],
    ) -> Result<Vec<PathBuf>, NativeContinuationFileBlobPairReclamationError>
    {
        let Some(manifest_name) =
            self.manifest.file_name().and_then(|name| name.to_str())
        else {
            return Err(
                NativeContinuationFileBlobPairReclamationError::ManifestName,
            );
        };
        let directory =
            self.manifest.parent().unwrap_or_else(|| Path::new("."));
        let entries = fs::read_dir(directory).map_err(|error| {
            NativeContinuationFileBlobPairReclamationError::DirectoryOpen {
                kind: error.kind(),
            }
        })?;
        let mut candidates = Vec::new();
        for entry_result in entries {
            let entry = entry_result.map_err(|error| {
                NativeContinuationFileBlobPairReclamationError::DirectoryEntry {
                    kind: error.kind(),
                }
            })?;
            let path = entry.path();
            let candidate_revision =
                self.reclamation_candidate(&path, manifest_name).map_err(
                    NativeContinuationFileBlobPairReclamationError::Store,
                )?;
            if let Some(revision) = candidate_revision
                && Some(revision) != current
                && !preserved.contains(&revision)
            {
                candidates.push(path);
            }
        }
        candidates.sort();
        Ok(candidates)
    }

    fn replace_pair_locked(
        &self,
        first: &[u8],
        second: &[u8],
    ) -> Result<
        NativeContinuationFileBlobPairRevision,
        NativeContinuationFileBlobPairStoreError,
    > {
        let (
            generation,
            mut first_file,
            _first_path,
            mut second_file,
            _second_path,
        ) = self.open_generation()?;
        write_generation_member(
            &mut first_file,
            first,
            NativeContinuationFileBlobPairMember::First,
        )?;
        write_generation_member(
            &mut second_file,
            second,
            NativeContinuationFileBlobPairMember::Second,
        )?;
        drop(first_file);
        drop(second_file);
        self.publish_manifest(generation)?;
        Ok(generation)
    }

    fn validate_generation_members(
        &self,
        revision: NativeContinuationFileBlobPairRevision,
    ) -> Result<(), NativeContinuationFileBlobPairStoreError> {
        for member in [
            NativeContinuationFileBlobPairMember::First,
            NativeContinuationFileBlobPairMember::Second,
        ] {
            let path = self.generation_path(revision, member)?;
            let _file = File::open(path).map_err(|error| {
                NativeContinuationFileBlobPairStoreError::GenerationOpen {
                    kind: error.kind(),
                    member,
                }
            })?;
        }
        Ok(())
    }

    fn versioned_pair(
        &self,
        revision: NativeContinuationFileBlobPairRevision,
        first_maximum_bytes: NonZeroUsize,
        second_maximum_bytes: NonZeroUsize,
    ) -> Result<
        NativeContinuationVersionedBlobPair<
            NativeContinuationFileBlobPairRevision,
        >,
        NativeContinuationFileBlobPairStoreError,
    > {
        let first = self.read_generation_member(
            revision,
            NativeContinuationFileBlobPairMember::First,
            first_maximum_bytes,
        )?;
        let second = self.read_generation_member(
            revision,
            NativeContinuationFileBlobPairMember::Second,
            second_maximum_bytes,
        )?;
        Ok(NativeContinuationVersionedBlobPair {
            pair: NativeContinuationBlobPair { first, second },
            revision,
        })
    }
}

impl NativeContinuationBlobPairStore for NativeContinuationFileBlobPairStore {
    type Error = NativeContinuationFileBlobPairStoreError;

    fn load_pair(
        &mut self,
        first_maximum_bytes: NonZeroUsize,
        second_maximum_bytes: NonZeroUsize,
    ) -> NativeContinuationBlobPairLoadResult<Self::Error> {
        let _lock = self.open_read_lock()?;
        let Some(revision) = self.read_manifest()? else {
            return Ok(None);
        };
        Ok(Some(
            self.versioned_pair(
                revision,
                first_maximum_bytes,
                second_maximum_bytes,
            )?
            .pair,
        ))
    }

    fn replace_pair(
        &mut self,
        first: &[u8],
        second: &[u8],
    ) -> Result<(), Self::Error> {
        let _lock = self.open_publication_lock()?;
        let _revision = self.replace_pair_locked(first, second)?;
        Ok(())
    }
}

impl NativeContinuationConditionalBlobPairStore
    for NativeContinuationFileBlobPairStore
{
    type Revision = NativeContinuationFileBlobPairRevision;

    fn compare_and_swap_pair(
        &mut self,
        request: NativeContinuationBlobPairConditionalRequest<
            '_,
            Self::Revision,
        >,
    ) -> Result<
        NativeContinuationBlobPairConditionalPublication<Self::Revision>,
        Self::Error,
    > {
        let _lock = self.open_publication_lock()?;
        let current_revision = self.read_manifest()?;
        if current_revision.as_ref() != request.expected {
            let current = current_revision
                .map(|revision| {
                    self.versioned_pair(
                        revision,
                        request.first_maximum_bytes,
                        request.second_maximum_bytes,
                    )
                })
                .transpose()?;
            return Ok(
                NativeContinuationBlobPairConditionalPublication::Conflict {
                    current,
                },
            );
        }
        let revision =
            self.replace_pair_locked(request.first, request.second)?;
        Ok(
            NativeContinuationBlobPairConditionalPublication::Published {
                revision,
            },
        )
    }

    fn load_pair_versioned(
        &mut self,
        first_maximum_bytes: NonZeroUsize,
        second_maximum_bytes: NonZeroUsize,
    ) -> Result<
        Option<NativeContinuationVersionedBlobPair<Self::Revision>>,
        Self::Error,
    > {
        let _lock = self.open_read_lock()?;
        let Some(revision) = self.read_manifest()? else {
            return Ok(None);
        };
        self.versioned_pair(revision, first_maximum_bytes, second_maximum_bytes)
            .map(Some)
    }
}

impl NativeContinuationReclaimableBlobPairStore
    for NativeContinuationFileBlobPairStore
{
    type Reclamation = NativeContinuationFileBlobPairReclamation;
    type ReclamationError = NativeContinuationFileBlobPairReclamationError;

    fn reclaim_pair_generations(
        &mut self,
        preserved: &[Self::Revision],
    ) -> Result<Self::Reclamation, Self::ReclamationError> {
        self.reclaim_generations_preserving(preserved)
    }
}

impl NativeContinuationDurableBlobPairStore
    for NativeContinuationFileBlobPairStore
{
    type DurabilityError = NativeContinuationFileBlobPairDurabilityError;

    fn confirm_pair_durability(&mut self) -> Result<(), Self::DurabilityError> {
        let directory =
            File::open(self.manifest_directory()?).map_err(|error| {
                NativeContinuationFileBlobPairDurabilityError::OpenDirectory {
                    kind: error.kind(),
                }
            })?;
        directory.sync_all().map_err(|error| {
            NativeContinuationFileBlobPairDurabilityError::SyncDirectory {
                kind: error.kind(),
            }
        })
    }
}

fn cleanup_staging(path: &Path) -> Option<ErrorKind> {
    match fs::remove_file(path) {
        Ok(()) => None,
        Err(error) if error.kind() == ErrorKind::NotFound => None,
        Err(error) => Some(error.kind()),
    }
}

fn decode_manifest(
    bytes: &[u8],
) -> Result<
    NativeContinuationFileBlobPairRevision,
    NativeContinuationFileBlobPairStoreError,
> {
    if bytes.len() != MANIFEST_BYTES {
        return Err(NativeContinuationFileBlobPairStoreError::ManifestSize {
            observed_bytes: bytes.len(),
        });
    }
    if bytes.get(..8) != Some(MANIFEST_MAGIC.as_slice()) {
        return Err(NativeContinuationFileBlobPairStoreError::ManifestMagic);
    }
    let process_slice = bytes.get(8..16).ok_or(
        NativeContinuationFileBlobPairStoreError::ManifestSize {
            observed_bytes: bytes.len(),
        },
    )?;
    let process_bytes: [u8; 8] =
        process_slice.try_into().map_err(|_error| {
            NativeContinuationFileBlobPairStoreError::ManifestSize {
                observed_bytes: bytes.len(),
            }
        })?;
    let generation_slice = bytes.get(16..24).ok_or(
        NativeContinuationFileBlobPairStoreError::ManifestSize {
            observed_bytes: bytes.len(),
        },
    )?;
    let generation_bytes: [u8; 8] =
        generation_slice.try_into().map_err(|_error| {
            NativeContinuationFileBlobPairStoreError::ManifestSize {
                observed_bytes: bytes.len(),
            }
        })?;
    let process = u64::from_le_bytes(process_bytes);
    let generation = u64::from_le_bytes(generation_bytes);
    if generation == 0 {
        return Err(
            NativeContinuationFileBlobPairStoreError::ManifestGenerationZero,
        );
    }
    Ok(NativeContinuationFileBlobPairRevision { generation, process })
}

fn encode_manifest(
    generation: NativeContinuationFileBlobPairRevision,
) -> [u8; MANIFEST_BYTES] {
    let mut bytes = [0u8; MANIFEST_BYTES];
    bytes[..8].copy_from_slice(&MANIFEST_MAGIC);
    bytes[8..16].copy_from_slice(&generation.process.to_le_bytes());
    bytes[16..24].copy_from_slice(&generation.generation.to_le_bytes());
    bytes
}

fn next_pair_id() -> Result<u64, NativeContinuationFileBlobPairStoreError> {
    NEXT_PAIR_ID
        .try_update(Ordering::Relaxed, Ordering::Relaxed, |current| {
            current.checked_add(1)
        })
        .map_err(|_current| {
            NativeContinuationFileBlobPairStoreError::SequenceExhausted
        })
}

fn write_generation_member(
    file: &mut File,
    bytes: &[u8],
    member: NativeContinuationFileBlobPairMember,
) -> Result<(), NativeContinuationFileBlobPairStoreError> {
    file.write_all(bytes).map_err(|error| {
        NativeContinuationFileBlobPairStoreError::GenerationWrite {
            kind: error.kind(),
            member,
        }
    })?;
    file.sync_all().map_err(|error| {
        NativeContinuationFileBlobPairStoreError::GenerationSync {
            kind: error.kind(),
            member,
        }
    })
}
