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
//   - Side effects: immutable generation writes and atomic manifest
//     replacement.
// - Split-When:
//   - Pair CAS, generation reclamation, or N-object transactions gain
//     semantics.
// - Merge-When:
//   - One filesystem adapter owns this exact generation-pointer lifecycle.
// - Summary:
//   - Binds atomic opaque blob-pair storage to filesystem generation
//     indirection.
// - Description:
//   - One stable lock serializes generation creation and manifest publication.
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
    NativeContinuationBlobPair, NativeContinuationBlobPairLoadResult,
    NativeContinuationBlobPairStore, NativeContinuationDurableBlobPairStore,
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
    /// Acquiring the stable sibling publication lock failed.
    Lock {
        /// Host filesystem error category.
        kind: ErrorKind,
    },
    /// Opening the stable sibling publication lock failed.
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

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct PairGeneration {
    generation: u64,
    process: u64,
}

/// Filesystem-backed pair store rooted at one explicit manifest path.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeContinuationFileBlobPairStore {
    manifest: PathBuf,
}

type PairStoreError = NativeContinuationFileBlobPairStoreError;

type PairGenerationOpenResult = Result<
    (PairGeneration, File, PathBuf, File, PathBuf),
    NativeContinuationFileBlobPairStoreError,
>;

type PairManifestStagingOpenResult =
    Result<(File, PathBuf), NativeContinuationFileBlobPairStoreError>;

impl NativeContinuationFileBlobPairStore {
    fn generation_path(
        &self,
        generation: PairGeneration,
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

    fn open_generation(&self) -> PairGenerationOpenResult {
        for _attempt in 0..MAX_STAGING_ATTEMPTS {
            let generation = PairGeneration {
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

    fn publish_manifest(
        &self,
        generation: PairGeneration,
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
        generation: PairGeneration,
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

    fn read_manifest(&self) -> Result<Option<PairGeneration>, PairStoreError> {
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

    fn replace_pair_locked(
        &self,
        first: &[u8],
        second: &[u8],
    ) -> Result<(), NativeContinuationFileBlobPairStoreError> {
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
        self.publish_manifest(generation)
    }
}

impl NativeContinuationBlobPairStore for NativeContinuationFileBlobPairStore {
    type Error = NativeContinuationFileBlobPairStoreError;

    fn load_pair(
        &mut self,
        first_maximum_bytes: NonZeroUsize,
        second_maximum_bytes: NonZeroUsize,
    ) -> NativeContinuationBlobPairLoadResult<Self::Error> {
        let Some(generation) = self.read_manifest()? else {
            return Ok(None);
        };
        let first = self.read_generation_member(
            generation,
            NativeContinuationFileBlobPairMember::First,
            first_maximum_bytes,
        )?;
        let second = self.read_generation_member(
            generation,
            NativeContinuationFileBlobPairMember::Second,
            second_maximum_bytes,
        )?;
        Ok(Some(NativeContinuationBlobPair { first, second }))
    }

    fn replace_pair(
        &mut self,
        first: &[u8],
        second: &[u8],
    ) -> Result<(), Self::Error> {
        let _lock = self.open_publication_lock()?;
        self.replace_pair_locked(first, second)
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
) -> Result<PairGeneration, NativeContinuationFileBlobPairStoreError> {
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
    Ok(PairGeneration { generation, process })
}

fn encode_manifest(generation: PairGeneration) -> [u8; MANIFEST_BYTES] {
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
