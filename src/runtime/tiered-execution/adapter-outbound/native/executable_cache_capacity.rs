// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Exact entry, mapping, and mapped-byte accounting for executable caches.
// - Must-Not:
//   - Load, release, invoke, or retain executable mapping ownership.
// - Allows:
//   - Inputs: ready executable sequences and caller-selected positive limits.
//   - Outputs: exact weights, usage snapshots, and capacity rejection evidence.
//   - Side effects: none.
// - Split-When:
//   - Platform-specific resident-set accounting replaces admitted mapping
//     bytes.
// - Merge-When:
//   - One executable-cache owner subsumes all capacity policy.
// - Summary:
//   - Provides overflow-safe weighted capacity evidence for loaded sequences.
// - Description:
//   - Counts complete entries, live mappings, and admitted mapped byte lengths.
// - Usage:
//   - Derive candidate weight, evict until projected usage fits, then publish.
// - Defaults:
//   - Entry count is bounded; mapping and byte limits are optional.
//

//! Weighted capacity values for loaded executable sequence caches.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::num::NonZeroUsize;

use super::executable_sequence::ReadyNativeExecutableSequence;

/// Positive caller-selected limits for one loaded executable sequence cache.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableSequenceCacheLimits {
    entries: NonZeroUsize,
    mapped_bytes: Option<NonZeroUsize>,
    mappings: Option<NonZeroUsize>,
}

/// Exact resources retained by one loaded executable sequence.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableSequenceWeight {
    mapped_bytes: usize,
    mappings: usize,
}

/// Exact current resource usage retained under cache authority.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct NativeExecutableSequenceCacheUsage {
    entries: usize,
    mapped_bytes: usize,
    mappings: usize,
}

/// Candidate or accounting failure against weighted executable-cache limits.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableSequenceCacheCapacityError {
    /// Candidate mapped bytes exceed the complete cache byte limit.
    MappedBytes {
        /// Exact bytes required by the candidate sequence.
        required: usize,
        /// Maximum admitted mapped bytes.
        limit: NonZeroUsize,
    },
    /// Candidate mapping count exceeds the complete cache mapping limit.
    Mappings {
        /// Exact mappings required by the candidate sequence.
        required: usize,
        /// Maximum admitted live mappings.
        limit: NonZeroUsize,
    },
    /// Summing admitted mapping bytes cannot be represented by `usize`.
    WeightOverflow,
}

impl NativeExecutableSequenceCacheLimits {
    pub(super) const fn candidate_error(
        self,
        weight: NativeExecutableSequenceWeight,
    ) -> Option<NativeExecutableSequenceCacheCapacityError> {
        if let Some(limit) = self.mappings
            && weight.mappings > limit.get()
        {
            return Some(
                NativeExecutableSequenceCacheCapacityError::Mappings {
                    limit,
                    required: weight.mappings,
                },
            );
        }
        if let Some(limit) = self.mapped_bytes
            && weight.mapped_bytes > limit.get()
        {
            return Some(
                NativeExecutableSequenceCacheCapacityError::MappedBytes {
                    limit,
                    required: weight.mapped_bytes,
                },
            );
        }
        None
    }

    /// Returns the positive whole-entry capacity.
    #[must_use]
    pub const fn entry_limit(self) -> NonZeroUsize {
        self.entries
    }

    /// Returns the optional positive mapped-byte capacity.
    #[must_use]
    pub const fn mapped_byte_limit(self) -> Option<NonZeroUsize> {
        self.mapped_bytes
    }

    /// Returns the optional positive live-mapping capacity.
    #[must_use]
    pub const fn mapping_limit(self) -> Option<NonZeroUsize> {
        self.mappings
    }

    /// Constructs limits with only a positive whole-entry bound.
    #[must_use]
    pub const fn new(entry_limit: NonZeroUsize) -> Self {
        Self {
            entries: entry_limit,
            mapped_bytes: None,
            mappings: None,
        }
    }

    pub(super) fn projected_exceeds(
        self,
        usage: NativeExecutableSequenceCacheUsage,
        weight: NativeExecutableSequenceWeight,
    ) -> bool {
        projected_exceeds_limit(usage.entries, 1, self.entries)
            || self.mappings.is_some_and(|limit| {
                projected_exceeds_limit(usage.mappings, weight.mappings, limit)
            })
            || self.mapped_bytes.is_some_and(|limit| {
                projected_exceeds_limit(
                    usage.mapped_bytes,
                    weight.mapped_bytes,
                    limit,
                )
            })
    }

    pub(super) fn usage_exceeds(
        self,
        usage: NativeExecutableSequenceCacheUsage,
    ) -> bool {
        usage.entries > self.entries.get()
            || self
                .mappings
                .is_some_and(|limit| usage.mappings > limit.get())
            || self
                .mapped_bytes
                .is_some_and(|limit| usage.mapped_bytes > limit.get())
    }

    /// Adds a positive mapped-byte limit.
    #[must_use]
    pub const fn with_mapped_byte_limit(
        mut self,
        mapped_byte_limit: NonZeroUsize,
    ) -> Self {
        self.mapped_bytes = Some(mapped_byte_limit);
        self
    }

    /// Adds a positive live-mapping limit.
    #[must_use]
    pub const fn with_mapping_limit(
        mut self,
        mapping_limit: NonZeroUsize,
    ) -> Self {
        self.mappings = Some(mapping_limit);
        self
    }
}

impl NativeExecutableSequenceWeight {
    pub(super) fn from_sequence(
        sequence: &ReadyNativeExecutableSequence,
    ) -> Result<Self, NativeExecutableSequenceCacheCapacityError> {
        let mapped_bytes = sequence.executables().iter().try_fold(
            0usize,
            |total, executable| {
                total.checked_add(executable.mapping().mapped_len())
            },
        );
        Ok(Self {
            mapped_bytes: mapped_bytes.ok_or(
                NativeExecutableSequenceCacheCapacityError::WeightOverflow,
            )?,
            mappings: sequence.len(),
        })
    }

    /// Returns exact admitted mapped bytes retained by the sequence.
    #[must_use]
    pub const fn mapped_bytes(self) -> usize {
        self.mapped_bytes
    }

    /// Returns exact live mapping count retained by the sequence.
    #[must_use]
    pub const fn mappings(self) -> usize {
        self.mappings
    }
}

impl NativeExecutableSequenceCacheUsage {
    pub(super) fn add(
        &mut self,
        weight: NativeExecutableSequenceWeight,
    ) -> Result<(), NativeExecutableSequenceCacheCapacityError> {
        self.entries = self.entries.checked_add(1).ok_or(
            NativeExecutableSequenceCacheCapacityError::WeightOverflow,
        )?;
        self.mappings = self.mappings.checked_add(weight.mappings).ok_or(
            NativeExecutableSequenceCacheCapacityError::WeightOverflow,
        )?;
        self.mapped_bytes =
            self.mapped_bytes.checked_add(weight.mapped_bytes).ok_or(
                NativeExecutableSequenceCacheCapacityError::WeightOverflow,
            )?;
        Ok(())
    }

    pub(super) const fn empty() -> Self {
        Self {
            entries: 0,
            mapped_bytes: 0,
            mappings: 0,
        }
    }

    /// Returns the number of complete sequence entries retained.
    #[must_use]
    pub const fn entries(self) -> usize {
        self.entries
    }

    /// Returns exact admitted mapped bytes retained by all entries.
    #[must_use]
    pub const fn mapped_bytes(self) -> usize {
        self.mapped_bytes
    }

    /// Returns exact live mappings retained by all entries.
    #[must_use]
    pub const fn mappings(self) -> usize {
        self.mappings
    }

    pub(super) const fn remove(
        &mut self,
        weight: NativeExecutableSequenceWeight,
    ) {
        self.entries = self.entries.saturating_sub(1);
        self.mappings = self.mappings.saturating_sub(weight.mappings);
        self.mapped_bytes =
            self.mapped_bytes.saturating_sub(weight.mapped_bytes);
    }

    pub(super) const fn reset(&mut self) {
        *self = Self::empty();
    }
}

impl Display for NativeExecutableSequenceCacheCapacityError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::MappedBytes { limit, required } => write!(
                f,
                "candidate requires {required} mapped bytes, limit is {limit}",
            ),
            Self::Mappings { limit, required } => write!(
                f,
                "candidate requires {required} mappings, limit is {limit}",
            ),
            Self::WeightOverflow => {
                f.write_str("executable sequence cache weight overflow")
            },
        }
    }
}

fn projected_exceeds_limit(
    current: usize,
    added: usize,
    limit: NonZeroUsize,
) -> bool {
    current
        .checked_add(added)
        .is_none_or(|projected| projected > limit.get())
}
