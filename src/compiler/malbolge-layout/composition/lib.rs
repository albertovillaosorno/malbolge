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
//   - The first addressed, position-sensitive linear Malbolge code layout.
// - Must-Not:
//   - Implement host computation, choose jumps/data, or claim C lowering.
// - Allows:
//   - Inputs: canonical target profile and a bounded closed linear opcode list.
//   - Outputs: graphical target bytes with exact decode/profile admission.
//   - Side effects: none.
// - Split-When:
//   - Nonlinear layout, self-modifying paths, or runtime linkage are admitted.
// - Merge-When:
//   - The complete target encoder subsumes this strictly linear sublanguage.
// - Summary:
//   - Resolves instruction-cell encoding at every assigned code position.
// - Description:
//   - Purely translates no-op, byte I/O and halt from canonical profile data.
// - Usage:
//   - Feed the closed instruction list to `encode_linear_layout`.
// - Defaults:
//   - Rejects empty, early-halt, jump and noncanonical code before publication.
//

//! Small address-sensitive, verifier-rechecked Malbolge linear code layout.
//!
//! This module does **not** lower arbitrary ternary IR or allocate guest data.
//! It proves an executable subset for which the code pointer advances by one
//! position after every step, and stops before leaving the emitted source.

use malbolge::{ProfileDescriptor, decode_profile_instruction};

const GRAPHICAL_START: u8 = 33;
const GRAPHICAL_END: u8 = 126;
const MIN_SOURCE_CELLS: usize = 2;
const MAX_LINEAR_CELLS: usize = 4096;
const HALT_INSTRUCTION: u8 = b'v';
const NO_OP_INSTRUCTION: u8 = b'o';

/// One supported decoded machine operation at the next linear code position.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LinearOpcode {
    /// Stop execution; this must be the only terminal operation.
    Halt,
    /// Read one raw profile word using the profile's input instruction.
    InputWord,
    /// The canonical explicit `o` no-operation instruction.
    NoOperation,
    /// Emit one byte using the profile's output instruction.
    OutputByte,
}

impl LinearOpcode {
    const fn decoded(self, profile: &ProfileDescriptor) -> u8 {
        match self {
            Self::InputWord => profile.input_instruction(),
            Self::OutputByte => profile.output_instruction(),
            Self::NoOperation => NO_OP_INSTRUCTION,
            Self::Halt => HALT_INSTRUCTION,
        }
    }
}

/// One fully admitted graphical source with exact canonical profile identity.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LinearLayout {
    profile_fingerprint: &'static str,
    profile_id: &'static str,
    source: Vec<u8>,
}

impl LinearLayout {
    /// Returns the canonical profile fingerprint used for emission.
    #[must_use]
    pub const fn profile_fingerprint(&self) -> &'static str {
        self.profile_fingerprint
    }

    /// Returns the canonical profile ID used for emission.
    #[must_use]
    pub const fn profile_id(&self) -> &'static str {
        self.profile_id
    }

    /// Returns the exact position-sensitive graphical `.malbolge` bytes.
    #[must_use]
    pub fn source(&self) -> &[u8] {
        &self.source
    }
}

/// Profile identity claimed by an independently supplied target byte stream.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct LinearProfileIdentity<'identity> {
    /// Immutable target-profile fingerprint of the alleged emitter.
    pub fingerprint: &'identity str,
    /// Immutable target-profile ID of the alleged emitter.
    pub id: &'identity str,
}

/// Rejection at the first reproducible linear encoding/admission boundary.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LinearLayoutError {
    /// More than one graphical cell claims this opcode at the same address.
    AmbiguousEncoding {
        /// Zero-based position admitting multiple encodings.
        position: usize,
    },
    /// The independently admitted source does not match the instructions.
    DecodeMismatch {
        /// Zero-based position of the first altered source cell.
        position: usize,
    },
    /// A halt before the final code position would leave dead instructions.
    EarlyHalt {
        /// Zero-based position of the first premature halt.
        position: usize,
    },
    /// The final operation must halt before the code pointer reaches padding.
    MissingHalt,
    /// An instruction has no inverse graphical code cell at its address.
    NoEncoding {
        /// Zero-based position with no valid source cell.
        position: usize,
    },
    /// The canonical selected profile identity changed.
    ProfileMismatch,
    /// An independently submitted byte stream is not the required length.
    SourceLengthMismatch,
    /// The code exceeds the bounded implementation or profile memory.
    TooLong,
    /// Fewer than two cells cannot initialize the canonical profile loader.
    TooShort,
}

fn validate_shape(
    profile: &ProfileDescriptor,
    operations: &[LinearOpcode],
) -> Result<(), LinearLayoutError> {
    if operations.len() < MIN_SOURCE_CELLS {
        return Err(LinearLayoutError::TooShort);
    }
    if operations.len() > MAX_LINEAR_CELLS
        || operations.len() > usize::try_from(profile.memory_words()).unwrap_or(0)
    {
        return Err(LinearLayoutError::TooLong);
    }
    if operations.last() != Some(&LinearOpcode::Halt) {
        return Err(LinearLayoutError::MissingHalt);
    }
    let before_last = operations.len().saturating_sub(1);
    if let Some(position) = operations
        .iter()
        .take(before_last)
        .position(|op| *op == LinearOpcode::Halt)
    {
        return Err(LinearLayoutError::EarlyHalt { position });
    }
    Ok(())
}

fn unique_graphical_cell(
    profile: &ProfileDescriptor,
    operation: LinearOpcode,
    position: usize,
) -> Result<u8, LinearLayoutError> {
    let address = u32::try_from(position).map_err(|_error| LinearLayoutError::TooLong)?;
    let decoded = operation.decoded(profile);
    let mut candidate = None;
    for byte in GRAPHICAL_START..=GRAPHICAL_END {
        if decode_profile_instruction(u32::from(byte), address) == Some(decoded) {
            if candidate.is_some() {
                return Err(LinearLayoutError::AmbiguousEncoding { position });
            }
            candidate = Some(byte);
        }
    }
    candidate.ok_or(LinearLayoutError::NoEncoding { position })
}

/// Re-admits independently supplied code against an exact linear instruction
/// sequence and the selected canonical target-profile descriptor.
///
/// # Errors
///
/// Returns [`LinearLayoutError`] for unsupported shape, profile drift,
/// changed position-sensitive decoding, or noncanonical source cells.
pub fn admit_linear_layout(
    profile: &'static ProfileDescriptor,
    operations: &[LinearOpcode],
    source: &[u8],
    identity: LinearProfileIdentity<'_>,
) -> Result<LinearLayout, LinearLayoutError> {
    validate_shape(profile, operations)?;
    if identity.id != profile.id() || identity.fingerprint != profile.fingerprint() {
        return Err(LinearLayoutError::ProfileMismatch);
    }
    if source.len() != operations.len() {
        return Err(LinearLayoutError::SourceLengthMismatch);
    }
    for (position, (operation, byte)) in operations.iter().zip(source.iter()).enumerate() {
        if *byte != unique_graphical_cell(profile, *operation, position)? {
            return Err(LinearLayoutError::DecodeMismatch { position });
        }
    }
    Ok(LinearLayout {
        profile_fingerprint: profile.fingerprint(),
        profile_id: profile.id(),
        source: source.to_vec(),
    })
}

/// Assigns contiguous addresses from zero, encodes each desired decoded
/// operation, and re-admits the entire graphical stream before publication.
///
/// # Errors
///
/// Returns [`LinearLayoutError`] for any unsupported, impossible, ambiguous,
/// malformed, or independently rejected layout.
pub fn encode_linear_layout(
    profile: &'static ProfileDescriptor,
    operations: &[LinearOpcode],
) -> Result<LinearLayout, LinearLayoutError> {
    validate_shape(profile, operations)?;
    let source = operations
        .iter()
        .enumerate()
        .map(|(position, operation)| unique_graphical_cell(profile, *operation, position))
        .collect::<Result<Vec<_>, _>>()?;
    admit_linear_layout(
        profile,
        operations,
        &source,
        LinearProfileIdentity {
            fingerprint: profile.fingerprint(),
            id: profile.id(),
        },
    )
}
