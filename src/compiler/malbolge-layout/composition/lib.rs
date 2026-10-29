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
//   - Implement host guest computation, arbitrary jumps or claim C lowering.
// - Allows:
//   - Inputs: canonical profile, bounded opcodes, proven forward jump chain.
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
//   - Rejects early halt, backward/forged jumps and noncanonical code.
//

//! Small address-sensitive, verifier-rechecked Malbolge code layout.
//!
//! This module does **not** lower arbitrary ternary IR or allocate guest data.
//! It proves an executable subset for which the code pointer advances by one
//! position after every ordinary step, and stops inside the emitted source.
//! Crazy/rotate may mutate memory only after a data-pointer relocation to
//! an address beyond all emitted code. Forward code jumps are admitted only
//! when the exact evolving data-pointer cells and skipped padding prove them.

use malbolge::{ProfileDescriptor, decode_profile_instruction};

const GRAPHICAL_START: u8 = 33;
const GRAPHICAL_END: u8 = 126;
const MIN_SOURCE_CELLS: usize = 2;
const MAX_LINEAR_CELLS: usize = 4096;
const HALT_INSTRUCTION: u8 = b'v';
const NO_OP_INSTRUCTION: u8 = b'o';

/// One supported decoded machine operation at an exact source code position.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LinearOpcode {
    /// Execute the canonical ternary crazy operation at the data pointer.
    CrazyData,
    /// Stop execution; this must be the only terminal operation.
    Halt,
    /// Read one raw profile word using the profile's input instruction.
    InputWord,
    /// Jump to a forward address read from the current data-pointer cell.
    JumpForward {
        /// Required code address after the VM's automatic increment.
        target: u32,
    },
    /// The canonical explicit `o` no-operation instruction.
    NoOperation,
    /// Emit one byte using the profile's output instruction.
    OutputByte,
    /// Redirect the data pointer from the original graphical code cell.
    RelocateDataPointer,
    /// Rotate the data-pointer word one trit to the right.
    RotateData,
}

impl LinearOpcode {
    const fn decoded(self, profile: &ProfileDescriptor) -> u8 {
        match self {
            Self::CrazyData => b'p',
            Self::InputWord => profile.input_instruction(),
            Self::JumpForward { .. } => b'i',
            Self::OutputByte => profile.output_instruction(),
            Self::NoOperation => NO_OP_INSTRUCTION,
            Self::Halt => HALT_INSTRUCTION,
            Self::RelocateDataPointer => b'j',
            Self::RotateData => b'*',
        }
    }
}

/// One fully admitted graphical source with exact canonical profile identity.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LinearLayout {
    data_pointer_positions: Vec<u32>,
    data_write_positions: Vec<Option<u32>>,
    encrypted_code_positions: Vec<u32>,
    executed_code_positions: Vec<u32>,
    profile_fingerprint: &'static str,
    profile_id: &'static str,
    source: Vec<u8>,
}

impl LinearLayout {
    /// Returns the data-pointer address read by each statically reachable step.
    /// A jump reads its data-pointer cell even when code and data have diverged.
    #[must_use]
    pub fn data_pointer_positions(&self) -> &[u32] {
        &self.data_pointer_positions
    }

    /// Returns each reached step's planned guest data-write address.
    /// Rotate/crazy write the current D word; all other steps write none.
    /// The final halt has no write, and every admitted address is outside
    /// the graphical source region. This does not predict the written value.
    #[must_use]
    pub fn data_write_positions(&self) -> &[Option<u32>] {
        &self.data_write_positions
    }

    /// Returns the ordered code addresses encrypted after each nonhalt step.
    /// Jumps encrypt the target-minus-one cell rather than the fetched cell.
    /// Data-memory writes by rotate/crazy are not included here.
    #[must_use]
    pub fn encrypted_code_positions(&self) -> &[u32] {
        &self.encrypted_code_positions
    }

    /// Returns the ordered code addresses of every statically reachable step.
    /// Includes the terminal halt address and excludes skipped padding.
    #[must_use]
    pub fn executed_code_positions(&self) -> &[u32] {
        &self.executed_code_positions
    }

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
    /// The jump shape would revisit code or skip non-padding operations.
    JumpPathUnsupported,
    /// The jump's claimed target disagrees with the encoded source cell.
    JumpTargetMismatch {
        /// Address of the incorrectly targeted jump.
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
    /// Data relocation is required before rotate/crazy or is misplaced.
    UnsafeDataPlacement,
}

struct DerivedExecutionPositions {
    data: Vec<u32>,
    encrypted: Vec<u32>,
    executed: Vec<u32>,
    writes: Vec<Option<u32>>,
}

struct JumpSuccessor {
    encryption: usize,
    position: usize,
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
    let relocation = operations
        .iter()
        .position(|op| *op == LinearOpcode::RelocateDataPointer);
    let second_relocation = relocation.is_some_and(|position| {
        operations
            .iter()
            .skip(position.saturating_add(1))
            .any(|op| *op == LinearOpcode::RelocateDataPointer)
    });
    let unplaced_arithmetic = operations.iter().enumerate().any(|(position, op)| {
        matches!(op, LinearOpcode::CrazyData | LinearOpcode::RotateData)
            && relocation.is_none_or(|base| position <= base)
    });
    if second_relocation || unplaced_arithmetic {
        return Err(LinearLayoutError::UnsafeDataPlacement);
    }
    validate_jump_shape(operations)
}

fn validate_jump_shape(operations: &[LinearOpcode]) -> Result<(), LinearLayoutError> {
    let relocation = operations
        .iter()
        .position(|operation| *operation == LinearOpcode::RelocateDataPointer);
    for (position, operation) in operations.iter().enumerate() {
        let LinearOpcode::JumpForward { target } = operation else {
            continue;
        };
        // Once j relocates D beyond graphical source, later i operands are
        // synthesized loader data and not yet covered by this small proof.
        if relocation.is_some_and(|relocate_at| position > relocate_at) {
            return Err(LinearLayoutError::JumpPathUnsupported);
        }
        let target_position =
            usize::try_from(*target).map_err(|_error| LinearLayoutError::JumpPathUnsupported)?;
        if target_position <= position || target_position >= operations.len() {
            return Err(LinearLayoutError::JumpPathUnsupported);
        }
        let skip_begin = position.saturating_add(1);
        if operations
            .iter()
            .skip(skip_begin)
            .take(target_position.saturating_sub(skip_begin))
            .any(|skipped| *skipped != LinearOpcode::NoOperation)
        {
            return Err(LinearLayoutError::JumpPathUnsupported);
        }
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

fn jump_successor(
    code_cells: &[u32],
    data_pointer: usize,
    position: usize,
    target: u32,
) -> Result<JumpSuccessor, LinearLayoutError> {
    let data_cell = code_cells
        .get(data_pointer)
        .ok_or(LinearLayoutError::JumpPathUnsupported)?;
    if data_cell.saturating_add(1) != target {
        return Err(LinearLayoutError::JumpTargetMismatch { position });
    }
    let encryption = usize::try_from(target.saturating_sub(1))
        .map_err(|_error| LinearLayoutError::JumpPathUnsupported)?;
    let successor =
        usize::try_from(target).map_err(|_error| LinearLayoutError::JumpPathUnsupported)?;
    Ok(JumpSuccessor {
        encryption,
        position: successor,
    })
}

fn planned_data_write(
    operation: LinearOpcode,
    data_address: u32,
    source_length: usize,
) -> Result<Option<u32>, LinearLayoutError> {
    if !matches!(
        operation,
        LinearOpcode::CrazyData | LinearOpcode::RotateData
    ) {
        return Ok(None);
    }
    let code_end = u32::try_from(source_length).map_err(|_error| LinearLayoutError::TooLong)?;
    if data_address < code_end {
        return Err(LinearLayoutError::UnsafeDataPlacement);
    }
    Ok(Some(data_address))
}

fn derive_execution_positions(
    operations: &[LinearOpcode],
    source: &[u8],
) -> Result<DerivedExecutionPositions, LinearLayoutError> {
    let mut data = Vec::new();
    let mut executed = Vec::new();
    let mut encrypted = Vec::new();
    let mut writes = Vec::new();
    // Every jump and the sole relocation read a source-addressed data cell.
    // After relocation all further operations are linear and never inspect
    // memory contents for code control flow. Arithmetic cannot alias source.
    let mut code_cells: Vec<u32> = source.iter().copied().map(u32::from).collect();
    let mut data_pointer = 0usize;
    let mut position = 0usize;
    while let Some(operation) = operations.get(position) {
        let code = u32::try_from(position).map_err(|_error| LinearLayoutError::TooLong)?;
        executed.push(code);
        let data_address =
            u32::try_from(data_pointer).map_err(|_error| LinearLayoutError::TooLong)?;
        data.push(data_address);
        writes.push(planned_data_write(*operation, data_address, source.len())?);
        if *operation == LinearOpcode::Halt {
            break;
        }
        let (encryption_address, next_position) = match operation {
            LinearOpcode::JumpForward { target } => {
                let next = jump_successor(&code_cells, data_pointer, position, *target)?;
                (next.encryption, next.position)
            }
            LinearOpcode::CrazyData
            | LinearOpcode::InputWord
            | LinearOpcode::NoOperation
            | LinearOpcode::OutputByte
            | LinearOpcode::RelocateDataPointer
            | LinearOpcode::RotateData => (position, position.saturating_add(1)),
            LinearOpcode::Halt => return Err(LinearLayoutError::EarlyHalt { position }),
        };
        let next_data_pointer = if *operation == LinearOpcode::RelocateDataPointer {
            let data_word = usize::try_from(
                *code_cells
                    .get(data_pointer)
                    .ok_or(LinearLayoutError::UnsafeDataPlacement)?,
            )
            .map_err(|_error| LinearLayoutError::UnsafeDataPlacement)?;
            if data_word < source.len() {
                return Err(LinearLayoutError::UnsafeDataPlacement);
            }
            data_word.saturating_add(1)
        } else {
            data_pointer.saturating_add(1)
        };
        let code_cell = code_cells
            .get_mut(encryption_address)
            .ok_or(LinearLayoutError::JumpPathUnsupported)?;
        *code_cell = malbolge::encrypt_profile_cell(*code_cell)
            .ok_or(LinearLayoutError::JumpPathUnsupported)?;
        encrypted
            .push(u32::try_from(encryption_address).map_err(|_error| LinearLayoutError::TooLong)?);
        position = next_position;
        data_pointer = next_data_pointer;
    }
    Ok(DerivedExecutionPositions {
        data,
        encrypted,
        executed,
        writes,
    })
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
    let path = derive_execution_positions(operations, source)?;
    Ok(LinearLayout {
        data_pointer_positions: path.data,
        data_write_positions: path.writes,
        encrypted_code_positions: path.encrypted,
        executed_code_positions: path.executed,
        profile_fingerprint: profile.fingerprint(),
        profile_id: profile.id(),
        source: source.to_vec(),
    })
}

/// Assigns contiguous addresses from zero, encodes each desired decoded
/// operation, and re-admits the entire graphical stream before publication.
///
/// Forward jumps read their target from the exact dynamically evolving
/// data-pointer cell, not necessarily the jump's code cell. A later `j` may
/// move data beyond source if the proven current D word admits that boundary. Every intervening
/// skipped source position must be inert graphical padding.
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
