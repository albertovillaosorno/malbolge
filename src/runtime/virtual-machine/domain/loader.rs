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
//   - Deterministic classic source validation, loading, and memory recurrence.
// - Must-Not:
//   - Depend on locale whitespace, host text encoding, or historical C
//   - overread.
// - Allows:
//   - Inputs: raw source bytes containing ASCII whitespace and graphical bytes.
//   - Outputs: one exact initialized classic memory image or a typed
//   - diagnostic.
//   - Side effects: none.
// - Split-When:
//   - Split when extended image formats gain a separate loading contract.
// - Merge-When:
//   - Merge when another module owns the same classic source admission rules.
// - Summary:
//   - Loads validated classic source into the normative 59049-word image.
// - Description:
//   - Applies decode admission before deterministic crazy-operation fill.
// - Usage:
//   - Used before constructing the default classic VM execution state.
// - Defaults:
//   - Rejects fewer than two loaded words instead of reproducing C
//   - undefinedness.
//

//! Deterministic loader for normative classic Malbolge source bytes.

use std::fmt::{Display, Formatter, Result as FormatResult};

use crate::{MEMORY_WORDS, Memory, MemoryError, Word, decode_instruction};

/// Deterministic failure while admitting classic Malbolge source.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LoadError {
    /// The source lacks the two words required by the fill recurrence.
    InsufficientRecurrenceBase,
    /// An internal exact-domain conversion or table invariant failed.
    InternalInvariant,
    /// A graphical byte decodes to an instruction forbidden at load time.
    InvalidInstruction {
        /// Loaded word position after whitespace removal.
        position: usize,
        /// Original graphical source byte.
        byte: u8,
    },
    /// A non-whitespace source byte is outside graphical ASCII.
    InvalidSourceByte {
        /// Byte offset in the original source stream.
        offset: usize,
        /// Rejected raw byte value.
        byte: u8,
    },
    /// More non-whitespace words were supplied than classic memory can hold.
    SourceTooLong,
}

impl Display for LoadError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::InsufficientRecurrenceBase => f.write_str(
                "classic source requires at least two non-whitespace words",
            ),
            Self::InvalidInstruction { position, byte } => write!(
                f,
                "source byte {byte} at loaded position {position} is invalid"
            ),
            Self::InvalidSourceByte { offset, byte } => write!(
                f,
                "source byte {byte} at offset {offset} is not graphical ASCII"
            ),
            Self::SourceTooLong => f.write_str(
                "classic source exceeds the 59049-word memory image",
            ),
            Self::InternalInvariant => {
                f.write_str("classic loader internal invariant failed")
            },
        }
    }
}

impl From<MemoryError> for LoadError {
    fn from(_error: MemoryError) -> Self {
        Self::InternalInvariant
    }
}

/// Loads validated classic source and fills the complete memory recurrence.
///
/// # Errors
///
/// Returns [`LoadError`] when source admission or memory initialization fails.
pub fn load(source: &[u8]) -> Result<Memory, LoadError> {
    let admitted = collect_source(source)?;
    validate_source(&admitted)?;
    fill_memory(admitted)
}

fn collect_source(source: &[u8]) -> Result<Vec<u8>, LoadError> {
    let mut admitted = Vec::new();
    for (offset, byte) in source.iter().copied().enumerate() {
        if byte.is_ascii_whitespace() {
            continue;
        }
        if !(33..=126).contains(&byte) {
            return Err(LoadError::InvalidSourceByte { offset, byte });
        }
        admitted.push(byte);
    }
    if admitted.len() < 2 {
        return Err(LoadError::InsufficientRecurrenceBase);
    }
    if admitted.len() > MEMORY_WORDS {
        return Err(LoadError::SourceTooLong);
    }
    Ok(admitted)
}

fn fill_memory(admitted: Vec<u8>) -> Result<Memory, LoadError> {
    let mut words: Vec<Word> =
        admitted.into_iter().map(Word::from_byte).collect();
    let mut reverse = words.iter().rev().copied();
    let mut previous = reverse.next().ok_or(LoadError::InternalInvariant)?;
    let mut older = reverse.next().ok_or(LoadError::InternalInvariant)?;
    while words.len() < MEMORY_WORDS {
        let next = older.crazy(previous);
        words.push(next);
        older = previous;
        previous = next;
    }
    Memory::from_words(words).map_err(LoadError::from)
}

fn validate_source(admitted: &[u8]) -> Result<(), LoadError> {
    for (position, byte) in admitted.iter().copied().enumerate() {
        let pointer_value = u16::try_from(position)
            .map_err(|_error| LoadError::InternalInvariant)?;
        let pointer = Word::new(pointer_value)
            .map_err(|_error| LoadError::InternalInvariant)?;
        let decoded = decode_instruction(Word::from_byte(byte), pointer)
            .ok_or(LoadError::InternalInvariant)?;
        if !matches!(
            decoded,
            b'j' | b'i' | b'*' | b'p' | b'<' | b'/' | b'v' | b'o'
        ) {
            return Err(LoadError::InvalidInstruction { position, byte });
        }
    }
    Ok(())
}
