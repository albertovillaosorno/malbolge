// File:
//   - memory.rs
// Path:
//   - vm/src/memory.rs
//
// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Path-Rule:
//   - All paths in this header are repository-root relative.
//
// Boundary-Contract:
// - Owns:
//   - Fixed-size classic Malbolge memory storage and checked word access.
// - Must-Not:
//   - Expose resizable storage or admit values outside the classic word domain.
// - Allows:
//   - Inputs: exact memory images, classic addresses, and classic words.
//   - Outputs: checked reads, replacements, and deterministic memory snapshots.
//   - Side effects: mutation only of the owned in-memory image.
// - Split-When:
//   - Split when extended memory profiles require independent storage
//   - semantics.
// - Merge-When:
//   - Merge when another module owns the same fixed-memory invariant.
// - Summary:
//   - Encapsulates the exact 59049-word classic memory image.
// - Description:
//   - Keeps memory length invariant private while allowing verifier
//   - construction.
// - Usage:
//   - Used by the loader, machine, tests, and future differential verification.
// - Defaults:
//   - Every constructed memory image contains exactly 59049 validated words.
//
// Related documents:
// - docs/technical/specification/malbolge-1998.md
//
// Large file:
//   - false
//

//! Fixed-size storage for the classic Malbolge memory image.

use std::fmt::{Display, Formatter, Result as FormatResult};

use crate::{MEMORY_WORDS, Word};

/// Failure to preserve or access the fixed classic memory invariant.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum MemoryError {
    /// An exact image had a length other than 59049 words.
    InvalidLength {
        /// Number of words supplied by the caller.
        observed: usize,
    },
    /// A valid classic address could not be resolved in owned storage.
    InvariantViolation {
        /// Address that should have existed in the fixed image.
        address: usize,
    },
}

impl Display for MemoryError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::InvalidLength { observed } => write!(
                f,
                "classic memory requires {MEMORY_WORDS} words, got {observed}"
            ),
            Self::InvariantViolation { address } => {
                write!(f, "classic memory invariant lost address {address}")
            },
        }
    }
}

/// Owned classic memory containing exactly 59049 words.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Memory {
    words: Vec<Word>,
}

impl Memory {
    /// Creates a fixed memory image filled with one classic word.
    #[must_use]
    pub fn filled(fill: Word) -> Self {
        Self {
            words: vec![fill; MEMORY_WORDS],
        }
    }

    /// Creates memory from an exact 59049-word image.
    ///
    /// # Errors
    ///
    /// Returns [`MemoryError`] when the image length is not exactly 59049.
    pub fn from_words(words: Vec<Word>) -> Result<Self, MemoryError> {
        if words.len() == MEMORY_WORDS {
            Ok(Self { words })
        } else {
            Err(MemoryError::InvalidLength { observed: words.len() })
        }
    }

    /// Reads one classic address.
    ///
    /// # Errors
    ///
    /// Returns [`MemoryError`] if the fixed memory invariant is broken.
    pub fn read(&self, address: Word) -> Result<Word, MemoryError> {
        let index = usize::from(address.value());
        self.words
            .get(index)
            .copied()
            .ok_or(MemoryError::InvariantViolation { address: index })
    }

    /// Replaces one classic address with a validated word.
    ///
    /// # Errors
    ///
    /// Returns [`MemoryError`] if the fixed memory invariant is broken.
    pub fn replace(
        &mut self,
        address: Word,
        value: Word,
    ) -> Result<(), MemoryError> {
        let index = usize::from(address.value());
        let target = self
            .words
            .get_mut(index)
            .ok_or(MemoryError::InvariantViolation { address: index })?;
        *target = value;
        Ok(())
    }

    /// Returns all words in deterministic address order.
    #[must_use]
    pub fn words(&self) -> &[Word] {
        &self.words
    }
}
