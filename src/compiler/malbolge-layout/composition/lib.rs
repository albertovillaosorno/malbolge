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
//! Crazy/rotate may also write source cells strictly behind the forward-only
//! code pointer, after a jump separates code and data. Such writes cannot
//! modify instructions that will execute later; full guest semantics still
//! require normative VM validation. Forward code jumps are admitted only
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
    /// A graphical data byte in an unreachable forward-jump gap.
    ///
    /// It is never executed; its byte becomes a real guest memory operand.
    SkippedDataByte {
        /// Exact printable source word, independently checked for reachability.
        byte: u32,
    },
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
            Self::NoOperation | Self::SkippedDataByte { .. } => NO_OP_INSTRUCTION,
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
    /// The final halt has no write; addresses either lie beyond source or
    /// strictly behind the executed code pointer after a forward jump.
    /// This does not predict the written value.
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
    /// The jump revisits code, skips effects or reads an unproven data word.
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
    /// Arithmetic may write only disjoint data or already-passed code cells.
    UnsafeDataPlacement,
}

/// One *reachable* logical operation before address-sensitive gap insertion.
///
/// Unlike `LinearOpcode::JumpForward`, `Jump` intentionally has no numeric
/// target: the instruction's real current D word determines its successor.
/// Unreachable graphical no-op source cells are inserted by the planner.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PaddedForwardStep {
    /// Emit reached no-op phases until a `j` safely relocates future data.
    AutoRelocate,
    /// A reached machine instruction other than explicit `JumpForward`.
    Instruction(LinearOpcode),
    /// Emit a strictly forward code jump and pad its skipped source cells.
    Jump,
}

/// Proven origin of one emitted position-sensitive source code cell.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PaddedCellOrigin {
    /// An inserted no-op that is actually executed on the admitted VM path.
    ExecutedPadding,
    /// One requested logical instruction, identified by its zero-based index.
    Logical(u32),
    /// An inserted no-op skipped by an unconditional forward code jump.
    SkippedPadding,
}

/// Executable automatically padded source, plus bidirectional source maps.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PaddedForwardLayout {
    layout: LinearLayout,
    logical_code_positions: Vec<u32>,
    operations: Vec<LinearOpcode>,
    source_cell_origins: Vec<PaddedCellOrigin>,
}

impl PaddedForwardLayout {
    /// Returns independently re-admitted executable source and VM witnesses.
    #[must_use]
    pub const fn layout(&self) -> &LinearLayout {
        &self.layout
    }

    /// Returns each requested logical step's exact reached code address.
    /// Automatically inserted, skipped graphical padding has no entry.
    #[must_use]
    pub fn logical_code_positions(&self) -> &[u32] {
        &self.logical_code_positions
    }

    /// Returns the complete addressed instruction plan, including padding.
    #[must_use]
    pub fn operations(&self) -> &[LinearOpcode] {
        &self.operations
    }

    /// Maps every emitted code address to its logical or synthetic origin.
    /// Unlike the forward map, this distinguishes executed `AutoRelocate`
    /// fillers from unreachable `Jump` padding, so diagnostics cannot treat
    /// all inserted no-ops as semantically invisible.
    #[must_use]
    pub fn source_cell_origins(&self) -> &[PaddedCellOrigin] {
        &self.source_cell_origins
    }
}

type FixedGraphicalTail = [u8; 2];

struct ForwardPaddingBuilder<'profile> {
    accumulator: Option<u32>,
    data_pointer: usize,
    operations: Vec<LinearOpcode>,
    positions: Vec<u32>,
    profile: &'profile ProfileDescriptor,
    relocated: bool,
    shadow: Vec<u32>,
    expanded_writes: Vec<ExpandedWordWrite>,
    unproven_source_writes: Vec<usize>,
}

impl ForwardPaddingBuilder<'_> {
    fn auto_relocate(
        &mut self,
        remaining: &[PaddedForwardStep],
    ) -> Result<usize, LinearLayoutError> {
        // The address-sensitive decoder cycles over 94 graphical phases.
        // Search only this bounded first cycle. After a forward jump, a
        // known past source operand may select either past scratch or an
        // expanded address beyond the minimum remaining source length.
        // Final independent admission checks the complete source length.
        for _phase in 0..94usize {
            let position = self.operations.len();
            let planned_length = position
                .checked_add(1)
                .and_then(|size| size.checked_add(remaining.len()))
                .ok_or(LinearLayoutError::TooLong)?;
            if planned_length > MAX_LINEAR_CELLS {
                return Err(LinearLayoutError::TooLong);
            }
            let expanded_operand =
                self.proven_expanded_relocation_operand(position, remaining)?;
            if expanded_operand.is_some()
                || self.proven_relocation_operand(position, planned_length)?
            {
                return self.instruction_with_expanded_operand(
                    LinearOpcode::RelocateDataPointer,
                    expanded_operand,
                    remaining,
                );
            }
            // Without an exact fixed suffix, no reached no-op can prove an
            // operand ahead of C: both code and D advance by one.
            if self.relocated && self.data_pointer >= position {
                return Err(LinearLayoutError::UnsafeDataPlacement);
            }
            let _filler = self.instruction(LinearOpcode::NoOperation)?;
            self.advance_data_pointer()?;
        }
        Err(LinearLayoutError::UnsafeDataPlacement)
    }

    fn advance_data_pointer(&mut self) -> Result<(), LinearLayoutError> {
        let memory_words = usize::try_from(self.profile.memory_words())
            .map_err(|_error| LinearLayoutError::TooLong)?;
        self.data_pointer =
            self.data_pointer.saturating_add(1).rem_euclid(memory_words);
        Ok(())
    }

    fn fixed_source_tail(
        &self,
        length: usize,
        remaining: &[PaddedForwardStep],
    ) -> Result<Option<FixedGraphicalTail>, LinearLayoutError> {
        if remaining.len() < 2
            || !remaining
                .iter()
                .all(|step| matches!(step, PaddedForwardStep::Instruction(_)))
        {
            return Ok(None);
        }
        let mut tail = [0u8; 2];
        for (index, cell) in tail.iter_mut().enumerate() {
            let suffix_index =
                remaining.len().saturating_sub(2).saturating_add(index);
            let Some(PaddedForwardStep::Instruction(operation)) =
                remaining.get(suffix_index)
            else {
                return Ok(None);
            };
            *cell = unique_graphical_cell(
                self.profile,
                *operation,
                length.saturating_sub(2).saturating_add(index),
            )?;
        }
        Ok(Some(tail))
    }

    fn instruction(
        &mut self,
        operation: LinearOpcode,
    ) -> Result<usize, LinearLayoutError> {
        self.instruction_with_expanded_operand(operation, None, &[])
    }

    fn instruction_with_expanded_operand(
        &mut self,
        operation: LinearOpcode,
        preset_expanded_operand: Option<u32>,
        remaining: &[PaddedForwardStep],
    ) -> Result<usize, LinearLayoutError> {
        if matches!(operation, LinearOpcode::JumpForward { .. }) {
            return Err(LinearLayoutError::JumpPathUnsupported);
        }
        let expanded_operand = if operation == LinearOpcode::RelocateDataPointer
            && self.relocated
            && self.data_pointer >= self.operations.len()
        {
            preset_expanded_operand.or(self.proven_expanded_relocation_operand(
                self.operations.len(),
                remaining,
            )?)
        } else {
            preset_expanded_operand
        };
        if operation == LinearOpcode::RelocateDataPointer
            && self.relocated
            && expanded_operand.is_none()
        {
            // A known past source operand is the only other safe candidate.
            self.prove_past_source_operand()?;
        }
        // Keep the operand shadow before appending and encrypting this cell.
        if matches!(
            operation,
            LinearOpcode::CrazyData | LinearOpcode::RotateData
        ) {
            self.record_arithmetic_result(operation, remaining)?;
        } else if operation == LinearOpcode::InputWord {
            self.accumulator = None;
        }
        let position = push_padded_cell(
            self.profile,
            &mut self.operations,
            &mut self.shadow,
            operation,
        )?;
        if operation == LinearOpcode::RelocateDataPointer {
            let operand = expanded_operand
                .or_else(|| self.shadow.get(self.data_pointer).copied())
                .ok_or(LinearLayoutError::UnsafeDataPlacement)?;
            self.data_pointer = usize::try_from(operand)
                .map_err(|_error| LinearLayoutError::UnsafeDataPlacement)?;
            self.relocated = true;
        }
        if operation != LinearOpcode::Halt {
            encrypt_padded_cell(&mut self.shadow, position)?;
        }
        Ok(position)
    }

    fn jump(
        &mut self,
        remaining: &[PaddedForwardStep],
    ) -> Result<usize, LinearLayoutError> {
        // A source operand is known from the current shadow. An untouched
        // expanded operand can also be proved by solving the unknown jump
        // gap against its final, fixed graphical suffix.
        let expanded_target =
            if self.relocated && self.data_pointer >= self.operations.len() {
                self.proven_expanded_loader_jump_target(remaining)?
            } else {
                None
            };
        if self.relocated
            && (self.unproven_source_writes.contains(&self.data_pointer)
                || (self.data_pointer >= self.operations.len()
                    && expanded_target.is_none()))
        {
            return Err(LinearLayoutError::JumpPathUnsupported);
        }
        let code_position = push_padded_cell(
            self.profile,
            &mut self.operations,
            &mut self.shadow,
            LinearOpcode::JumpForward { target: 0 },
        )?;
        let target = if let Some(target) = expanded_target {
            target
        } else {
            let operand = self
                .shadow
                .get(self.data_pointer)
                .ok_or(LinearLayoutError::JumpPathUnsupported)?;
            usize::try_from(operand.saturating_add(1))
                .map_err(|_error| LinearLayoutError::JumpPathUnsupported)?
        };
        if target <= code_position.saturating_add(1)
            || target >= MAX_LINEAR_CELLS
        {
            return Err(LinearLayoutError::JumpPathUnsupported);
        }
        *self
            .operations
            .get_mut(code_position)
            .ok_or(LinearLayoutError::JumpPathUnsupported)? =
            LinearOpcode::JumpForward {
                target: u32::try_from(target)
                    .map_err(|_error| LinearLayoutError::TooLong)?,
            };
        while self.operations.len() < target {
            let _padding = push_padded_cell(
                self.profile,
                &mut self.operations,
                &mut self.shadow,
                LinearOpcode::NoOperation,
            )?;
        }
        encrypt_padded_cell(&mut self.shadow, target.saturating_sub(1))?;
        Ok(code_position)
    }

    fn proven_expanded_loader_jump_target(
        &self,
        remaining: &[PaddedForwardStep],
    ) -> Result<Option<usize>, LinearLayoutError> {
        if remaining.len() < 2
            || self.expanded_write_at_data_pointer().is_some()
            || !remaining
                .iter()
                .all(|step| matches!(step, PaddedForwardStep::Instruction(_)))
        {
            return Ok(None);
        }
        let position = self.operations.len();
        let min_target = position.saturating_add(2);
        let max_target = MAX_LINEAR_CELLS
            .min(self.data_pointer)
            .saturating_sub(remaining.len());
        for target in min_target..=max_target {
            let length = target.saturating_add(remaining.len());
            let Some(tail) = self.fixed_source_tail(length, remaining)? else {
                return Ok(None);
            };
            let offset = self.data_pointer.saturating_sub(length).rem_euclid(6);
            let operand = unwritten_loader_word(
                &tail,
                2usize.saturating_add(offset),
                self.profile,
            )?;
            if usize::try_from(operand)
                .ok()
                .and_then(|word| word.checked_add(1))
                == Some(target)
            {
                return Ok(Some(target));
            }
        }
        Ok(None)
    }

    fn proven_relocation_operand(
        &self,
        position: usize,
        planned_length: usize,
    ) -> Result<bool, LinearLayoutError> {
        if self.unproven_source_writes.contains(&self.data_pointer) {
            return Ok(false);
        }
        let data_word = if self.data_pointer == position && !self.relocated {
            Some(u32::from(unique_graphical_cell(
                self.profile,
                LinearOpcode::RelocateDataPointer,
                position,
            )?))
        } else {
            self.shadow.get(self.data_pointer).copied()
        };
        let Some(word) = data_word else {
            return Ok(false);
        };
        let operand_address = usize::try_from(word)
            .map_err(|_error| LinearLayoutError::UnsafeDataPlacement)?;
        let expanded_data = operand_address >= planned_length;
        let past_source_scratch = self.data_pointer < position
            && operand_address.saturating_add(1) < position;
        Ok(expanded_data || past_source_scratch)
    }

    fn prove_past_source_operand(&self) -> Result<(), LinearLayoutError> {
        if self.data_pointer >= self.operations.len()
            || self.unproven_source_writes.contains(&self.data_pointer)
            || self.shadow.get(self.data_pointer).is_none()
        {
            return Err(LinearLayoutError::UnsafeDataPlacement);
        }
        Ok(())
    }

    fn expanded_write_at_data_pointer(&self) -> Option<&ExpandedWordWrite> {
        self.expanded_writes
            .iter()
            .rev()
            .find(|(address, _)| *address == self.data_pointer)
    }

    fn proven_expanded_relocation_operand(
        &self,
        position: usize,
        remaining: &[PaddedForwardStep],
    ) -> Result<Option<u32>, LinearLayoutError> {
        // An untouched expanded word depends on the *final* two graphical
        // source cells. Derive them only when all remaining logical steps
        // are fixed instructions requiring no future jump or padding.
        let Some(length) = position
            .checked_add(remaining.len())
            .and_then(|size| size.checked_add(1))
        else {
            return Err(LinearLayoutError::TooLong);
        };
        if !self.relocated
            || self.data_pointer < length
            || self.data_pointer
                >= usize::try_from(self.profile.memory_words())
                    .map_err(|_error| LinearLayoutError::TooLong)?
        {
            return Ok(None);
        }
        let maybe_operand = if let Some((_, value)) =
            self.expanded_write_at_data_pointer()
        {
            *value
        } else {
            self.unwritten_expanded_operand(length, remaining)?
        };
        let Some(word) = maybe_operand else {
            return Ok(None);
        };
        let destination = usize::try_from(word)
            .map_err(|_error| LinearLayoutError::UnsafeDataPlacement)?;
        // An expanded operand may also select already-passed graphical
        // source scratch. Its provenance is loader memory, but only its
        // destination must be strictly behind the reached code pointer.
        if destination < length && destination.saturating_add(1) >= position {
            return Ok(None);
        }
        Ok(Some(word))
    }

    fn unwritten_expanded_operand(
        &self,
        length: usize,
        remaining: &[PaddedForwardStep],
    ) -> Result<Option<u32>, LinearLayoutError> {
        if self.data_pointer < length || remaining.len() < 2 {
            return Ok(None);
        }
        let Some(tail) = self.fixed_source_tail(length, remaining)? else {
            return Ok(None);
        };
        // The two-cell virtual tail shares the exact six-phase recurrence.
        let offset = self.data_pointer.saturating_sub(length).rem_euclid(6);
        unwritten_loader_word(
            &tail,
            2usize.saturating_add(offset),
            self.profile,
        )
        .map(Some)
    }

    fn record_arithmetic_result(
        &mut self,
        operation: LinearOpcode,
        remaining: &[PaddedForwardStep],
    ) -> Result<(), LinearLayoutError> {
        // Only a known input to p/* can become a future control operand.
        // Expanded initial words require a final fixed two-cell suffix;
        // a prior write takes precedence, including an unknown write.
        let operand = if self.data_pointer < self.shadow.len() {
            self.shadow.get(self.data_pointer).copied().filter(|_| {
                !self.unproven_source_writes.contains(&self.data_pointer)
            })
        } else if let Some((_, value)) = self.expanded_write_at_data_pointer() {
            *value
        } else {
            let length = self
                .operations
                .len()
                .checked_add(1)
                .and_then(|size| size.checked_add(remaining.len()))
                .ok_or(LinearLayoutError::TooLong)?;
            self.unwritten_expanded_operand(length, remaining)?
        };
        let result = proven_arithmetic_result(
            operation,
            operand,
            self.accumulator,
            self.profile,
        );
        if self.data_pointer >= self.shadow.len() {
            self.expanded_writes.push((self.data_pointer, result));
        } else if let Some(cell) = self.shadow.get_mut(self.data_pointer) {
            if let Some(word) = result {
                *cell = word;
            } else if !self.unproven_source_writes.contains(&self.data_pointer)
            {
                self.unproven_source_writes.push(self.data_pointer);
            }
        }
        self.accumulator = result;
        Ok(())
    }
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
        || operations.len()
            > usize::try_from(profile.memory_words()).unwrap_or(0)
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
    // Geometry alone cannot decide arithmetic safety. After a forward jump,
    // D may trail C and an arithmetic write can target a past source cell.
    // The exact execution path below proves D < C for each such write.
    validate_jump_shape(operations)
}

fn validate_jump_shape(
    operations: &[LinearOpcode],
) -> Result<(), LinearLayoutError> {
    let mut skipped_data = vec![false; operations.len()];
    for (position, operation) in operations.iter().enumerate() {
        let LinearOpcode::JumpForward { target } = operation else {
            continue;
        };
        // Independently prove each reached jump from the current D word.
        // After a j, that operand can still be a known past source cell;
        // expanded operands must be loader-proven, and input-tainted operands
        // still fail closed in the checked execution path.
        let target_position = usize::try_from(*target)
            .map_err(|_error| LinearLayoutError::JumpPathUnsupported)?;
        if target_position <= position || target_position >= operations.len() {
            return Err(LinearLayoutError::JumpPathUnsupported);
        }
        let skip_begin = position.saturating_add(1);
        for address in skip_begin..target_position {
            match operations[address] {
                LinearOpcode::NoOperation => {},
                LinearOpcode::SkippedDataByte { .. } => {
                    skipped_data[address] = true
                },
                _ => return Err(LinearLayoutError::JumpPathUnsupported),
            }
        }
    }
    if operations.iter().enumerate().any(|(position, operation)| {
        matches!(operation, LinearOpcode::SkippedDataByte { .. })
            && !skipped_data[position]
    }) {
        return Err(LinearLayoutError::JumpPathUnsupported);
    }
    Ok(())
}

fn unique_graphical_cell(
    profile: &ProfileDescriptor,
    operation: LinearOpcode,
    position: usize,
) -> Result<u8, LinearLayoutError> {
    if let LinearOpcode::SkippedDataByte { byte } = operation {
        if !(u32::from(GRAPHICAL_START)..=u32::from(GRAPHICAL_END))
            .contains(&byte)
        {
            return Err(LinearLayoutError::NoEncoding { position });
        }
        let address = u32::try_from(position)
            .map_err(|_error| LinearLayoutError::TooLong)?;
        let decoded = decode_profile_instruction(byte, address);
        if !decoded.is_some_and(|opcode| {
            matches!(opcode, b'j' | b'i' | b'*' | b'p' | b'v' | b'o')
                || opcode == profile.input_instruction()
                || opcode == profile.output_instruction()
        }) {
            return Err(LinearLayoutError::NoEncoding { position });
        }
        return u8::try_from(byte)
            .map_err(|_error| LinearLayoutError::NoEncoding { position });
    }
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
    data_cell: u32,
    position: usize,
    target: u32,
) -> Result<JumpSuccessor, LinearLayoutError> {
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
    code_address: u32,
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
    if data_address < code_end && data_address >= code_address {
        // Never overwrite the executing instruction or future source code.
        // Forward-only control flow guarantees no return to a past cell.
        return Err(LinearLayoutError::UnsafeDataPlacement);
    }
    Ok(Some(data_address))
}

type ExpandedWordWrite = (usize, Option<u32>);

#[derive(Clone, Copy)]
struct ControlOperandMemory<'memory> {
    profile: &'memory ProfileDescriptor,
    source: &'memory [u8],
    source_shadow: &'memory [Option<u32>],
    expanded_shadow: &'memory [ExpandedWordWrite],
}

/// A later i or j reads an as-yet-unwritten loader-expanded word. The loader
/// expands the original graphical source before any guest mutation; only its
/// final two cells determine an untouched data word beyond the source.
///
/// Every ternary crazy recurrence enters a period dividing six at the *first*
/// expanded word: each of the nine possible adjacent trit pairs has period
/// two or three (possibly after one initial pair). The 10-/15-trit words are
/// componentwise independent, so six steps suffice even for a far relocation.
/// This shortcut is invalid for any data address previously written by a
/// guest instruction; the calling checker rejects those addresses separately.
pub(crate) fn unwritten_loader_word(
    source: &[u8],
    address: usize,
    profile: &ProfileDescriptor,
) -> Result<u32, LinearLayoutError> {
    if address < source.len()
        || address >= usize::try_from(profile.memory_words()).unwrap_or(0)
    {
        return Err(LinearLayoutError::UnsafeDataPlacement);
    }
    let [.., previous_cell, latest_cell] = source else {
        return Err(LinearLayoutError::TooShort);
    };
    let mut previous = u32::from(*previous_cell);
    let mut latest = u32::from(*latest_cell);
    for _ in 0..=((address - source.len()) % 6) {
        let next =
            malbolge::profile_crazy(previous, latest, profile.word_trits());
        previous = latest;
        latest = next;
    }
    Ok(latest)
}

// Both i and j read the *current* D word. Source memory tracks XLAT2 and
// scratch writes; expanded memory tracks known and unknown guest writes.
// Only untouched expanded cells use their original loader-derived value.
fn known_control_operand(
    memory: ControlOperandMemory<'_>,
    data_pointer: usize,
    unproven: LinearLayoutError,
) -> Result<u32, LinearLayoutError> {
    if data_pointer < memory.source.len() {
        return memory
            .source_shadow
            .get(data_pointer)
            .copied()
            .flatten()
            .ok_or(unproven);
    }
    if let Some((_, value)) = memory
        .expanded_shadow
        .iter()
        .rev()
        .find(|(address, _)| *address == data_pointer)
    {
        return value.ok_or(unproven);
    }
    unwritten_loader_word(memory.source, data_pointer, memory.profile)
        .map_err(|_error| unproven)
}

// Only p and * call this helper. Unknown data and input-derived A values
// remain unresolved rather than being copied into the control-flow shadow.
fn proven_arithmetic_result(
    operation: LinearOpcode,
    word: Option<u32>,
    accumulator: Option<u32>,
    profile: &ProfileDescriptor,
) -> Option<u32> {
    if operation == LinearOpcode::CrazyData {
        word.zip(accumulator).map(|(operand, prior)| {
            malbolge::profile_crazy(operand, prior, profile.word_trits())
        })
    } else {
        word.map(|operand| {
            malbolge::profile_rotate(operand, profile.memory_words())
        })
    }
}

fn derive_execution_positions(
    operations: &[LinearOpcode],
    source: &[u8],
    profile: &ProfileDescriptor,
) -> Result<DerivedExecutionPositions, LinearLayoutError> {
    let mut data = Vec::new();
    let mut executed = Vec::new();
    let mut encrypted = Vec::new();
    let mut writes = Vec::new();
    // Control reads use exact source/expanded memory shadows. Arithmetic
    // writes may depend on input, so unresolved values remain unknown and
    // cannot later supply a guessed jump or relocation operand.
    let mut code_cells: Vec<Option<u32>> = source
        .iter()
        .copied()
        .map(|byte| Some(u32::from(byte)))
        .collect();
    // The full source tail determines untouched loader cells; retain every
    // expanded write separately so proven arithmetic can later drive i/j.
    // Unknown input-dependent writes never fall back to the loader value.
    let mut expanded_shadow: Vec<ExpandedWordWrite> = Vec::new();
    let mut data_pointer = 0usize;
    let mut position = 0usize;
    let mut accumulator = Some(0u32);
    while let Some(operation) = operations.get(position) {
        let code = u32::try_from(position)
            .map_err(|_error| LinearLayoutError::TooLong)?;
        executed.push(code);
        let data_address = u32::try_from(data_pointer)
            .map_err(|_error| LinearLayoutError::TooLong)?;
        data.push(data_address);
        writes.push(planned_data_write(
            *operation,
            code,
            data_address,
            source.len(),
        )?);
        if *operation == LinearOpcode::Halt {
            break;
        }
        // Every source/expanded write preserves exact values when proven;
        // input-derived values remain unresolved for later control reads.
        match operation {
            LinearOpcode::CrazyData | LinearOpcode::RotateData
                if data_pointer < source.len() =>
            {
                let data_word = *code_cells
                    .get(data_pointer)
                    .ok_or(LinearLayoutError::UnsafeDataPlacement)?;
                let new_accumulator = proven_arithmetic_result(
                    *operation,
                    data_word,
                    accumulator,
                    profile,
                );
                *code_cells
                    .get_mut(data_pointer)
                    .ok_or(LinearLayoutError::UnsafeDataPlacement)? =
                    new_accumulator;
                accumulator = new_accumulator;
            },
            LinearOpcode::CrazyData | LinearOpcode::RotateData => {
                let operand = known_control_operand(
                    ControlOperandMemory {
                        profile,
                        source,
                        source_shadow: &code_cells,
                        expanded_shadow: &expanded_shadow,
                    },
                    data_pointer,
                    LinearLayoutError::UnsafeDataPlacement,
                )
                .ok();
                let result = proven_arithmetic_result(
                    *operation,
                    operand,
                    accumulator,
                    profile,
                );
                expanded_shadow.push((data_pointer, result));
                accumulator = result;
            },
            LinearOpcode::InputWord => accumulator = None,
            LinearOpcode::Halt
            | LinearOpcode::JumpForward { .. }
            | LinearOpcode::NoOperation
            | LinearOpcode::SkippedDataByte { .. }
            | LinearOpcode::OutputByte
            | LinearOpcode::RelocateDataPointer => {},
        }
        let (encryption_address, next_position) = match operation {
            LinearOpcode::JumpForward { target } => {
                let operand = known_control_operand(
                    ControlOperandMemory {
                        profile,
                        source,
                        source_shadow: &code_cells,
                        expanded_shadow: &expanded_shadow,
                    },
                    data_pointer,
                    LinearLayoutError::JumpPathUnsupported,
                )?;
                let next = jump_successor(operand, position, *target)?;
                (next.encryption, next.position)
            },
            LinearOpcode::CrazyData
            | LinearOpcode::InputWord
            | LinearOpcode::NoOperation
            | LinearOpcode::OutputByte
            | LinearOpcode::RelocateDataPointer
            | LinearOpcode::RotateData => {
                (position, position.saturating_add(1))
            },
            LinearOpcode::SkippedDataByte { .. } => {
                return Err(LinearLayoutError::JumpPathUnsupported);
            },
            LinearOpcode::Halt => {
                return Err(LinearLayoutError::EarlyHalt { position });
            },
        };
        let memory_words = usize::try_from(profile.memory_words())
            .map_err(|_error| LinearLayoutError::UnsafeDataPlacement)?;
        let next_data_pointer = if *operation
            == LinearOpcode::RelocateDataPointer
        {
            let expanded_operand = data_pointer >= source.len();
            let data_word = usize::try_from(known_control_operand(
                ControlOperandMemory {
                    profile,
                    source,
                    source_shadow: &code_cells,
                    expanded_shadow: &expanded_shadow,
                },
                data_pointer,
                LinearLayoutError::UnsafeDataPlacement,
            )?)
            .map_err(|_error| LinearLayoutError::UnsafeDataPlacement)?;
            let next = data_word.saturating_add(1) % memory_words;
            // A proven expanded control operand can also select graphical
            // scratch behind C: only a source-backed operand must itself
            // lie behind C. Later arithmetic is checked against pending
            // source code separately, regardless of the operand's origin.
            let past_source_scratch = next < position
                && (expanded_operand || data_pointer < position);
            if !expanded_operand
                && data_word < source.len()
                && !past_source_scratch
            {
                return Err(LinearLayoutError::UnsafeDataPlacement);
            }
            // A final j cannot affect output. Otherwise a relocation
            // within source is safe only behind the already executed C.
            if position != operations.len().saturating_sub(2)
                && next < source.len()
                && !past_source_scratch
            {
                return Err(LinearLayoutError::UnsafeDataPlacement);
            }
            next
        } else {
            data_pointer.saturating_add(1) % memory_words
        };
        let code_cell = code_cells
            .get_mut(encryption_address)
            .ok_or(LinearLayoutError::JumpPathUnsupported)?;
        *code_cell = Some(
            malbolge::encrypt_profile_cell(
                code_cell.ok_or(LinearLayoutError::JumpPathUnsupported)?,
            )
            .ok_or(LinearLayoutError::JumpPathUnsupported)?,
        );
        encrypted.push(
            u32::try_from(encryption_address)
                .map_err(|_error| LinearLayoutError::TooLong)?,
        );
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
    let path = derive_execution_positions(operations, source, profile)?;
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
/// data-pointer cell, including proven untouched expanded loader words, not
/// necessarily the jump's code cell. A later `j` may
/// move D into expanded memory or to past graphical source scratch strictly
/// behind reached C after a forward jump. Every intervening skipped source
/// position must be inert graphical padding.
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

fn push_padded_cell(
    profile: &ProfileDescriptor,
    operations: &mut Vec<LinearOpcode>,
    shadow: &mut Vec<u32>,
    operation: LinearOpcode,
) -> Result<usize, LinearLayoutError> {
    if operations.len() >= MAX_LINEAR_CELLS {
        return Err(LinearLayoutError::TooLong);
    }
    let position = operations.len();
    let byte = unique_graphical_cell(profile, operation, position)?;
    operations.push(operation);
    shadow.push(u32::from(byte));
    Ok(position)
}

fn encrypt_padded_cell(shadow: &mut [u32], address: usize) -> Result<(), LinearLayoutError> {
    let cell = shadow
        .get_mut(address)
        .ok_or(LinearLayoutError::JumpPathUnsupported)?;
    *cell = malbolge::encrypt_profile_cell(*cell).ok_or(LinearLayoutError::JumpPathUnsupported)?;
    Ok(())
}

fn proven_source_origins(
    layout: &LinearLayout,
    positions: &[u32],
    operations: &[LinearOpcode],
) -> Result<Vec<PaddedCellOrigin>, LinearLayoutError> {
    let mut origins = vec![PaddedCellOrigin::SkippedPadding; operations.len()];
    for (logical_index, &code) in positions.iter().enumerate() {
        let address = usize::try_from(code).map_err(|_error| LinearLayoutError::TooLong)?;
        let slot = origins
            .get_mut(address)
            .ok_or(LinearLayoutError::JumpPathUnsupported)?;
        if *slot != PaddedCellOrigin::SkippedPadding
            || layout
                .executed_code_positions()
                .binary_search(&code)
                .is_err()
        {
            return Err(LinearLayoutError::JumpPathUnsupported);
        }
        *slot = PaddedCellOrigin::Logical(
            u32::try_from(logical_index).map_err(|_error| LinearLayoutError::TooLong)?,
        );
    }
    for &code in layout.executed_code_positions() {
        let address = usize::try_from(code).map_err(|_error| LinearLayoutError::TooLong)?;
        let slot = origins
            .get_mut(address)
            .ok_or(LinearLayoutError::JumpPathUnsupported)?;
        if *slot == PaddedCellOrigin::SkippedPadding {
            if operations.get(address) != Some(&LinearOpcode::NoOperation) {
                return Err(LinearLayoutError::JumpPathUnsupported);
            }
            *slot = PaddedCellOrigin::ExecutedPadding;
        }
    }
    Ok(origins)
}

// This optional finite search handles a single future `Jump` when earlier
// expanded-memory arithmetic cannot be proven until its final source length
// is known. Every tentative gap is separately encoded and independently
// admitted with the *complete* final loader image. Unknown input effects,
// pending-code aliases and mismatched control words still fail closed.
// Keep this expensive fallback bounded; the ordinary online planner handles
// larger plans and multiple jumps without speculative whole-source checks.
const MAX_FIXED_TAIL_SEARCH_CELLS: usize = 256;

fn prove_single_fixed_tail_jump(
    profile: &'static ProfileDescriptor,
    logical: &[PaddedForwardStep],
) -> Result<Option<PaddedForwardLayout>, LinearLayoutError> {
    let mut jump_at = None;
    let mut fixed = Vec::with_capacity(logical.len());
    for (index, step) in logical.iter().enumerate() {
        match step {
            PaddedForwardStep::Instruction(operation)
                if !matches!(operation, LinearOpcode::JumpForward { .. }) =>
            {
                fixed.push(*operation);
            },
            PaddedForwardStep::Jump if jump_at.is_none() => {
                jump_at = Some(index);
            },
            _ => return Ok(None),
        }
    }
    let Some(jump_at) = jump_at else {
        return Ok(None);
    };
    // Input may precede the jump: a later rotate can reset the accumulator
    // to a proven value. The independent full-source checker tracks tainted
    // accumulator/memory and must reject input-dependent control operands.
    let prefix = &fixed[..jump_at];
    if logical.len() > MAX_FIXED_TAIL_SEARCH_CELLS
        || !prefix.iter().any(|operation| {
            matches!(
                operation,
                LinearOpcode::CrazyData | LinearOpcode::RotateData
            )
        })
        || !prefix.contains(&LinearOpcode::RelocateDataPointer)
    {
        return Ok(None);
    }
    let suffix = &fixed[jump_at..];
    let first_target = jump_at.saturating_add(2);
    let final_target = MAX_FIXED_TAIL_SEARCH_CELLS
        .min(MAX_LINEAR_CELLS)
        .saturating_sub(suffix.len());
    for target in first_target..=final_target {
        let mut operations = fixed[..jump_at].to_vec();
        operations.push(LinearOpcode::JumpForward {
            target: u32::try_from(target)
                .map_err(|_error| LinearLayoutError::TooLong)?,
        });
        operations.resize(target, LinearOpcode::NoOperation);
        operations.extend_from_slice(suffix);
        let Ok(layout) = encode_linear_layout(profile, &operations) else {
            continue;
        };
        let mut positions: Vec<u32> = (0..=jump_at)
            .map(|index| {
                u32::try_from(index)
                    .map_err(|_error| LinearLayoutError::TooLong)
            })
            .collect::<Result<_, _>>()?;
        positions.extend(
            (target..target.saturating_add(suffix.len()))
                .map(|index| {
                    u32::try_from(index)
                        .map_err(|_error| LinearLayoutError::TooLong)
                })
                .collect::<Result<Vec<_>, _>>()?,
        );
        let origins = proven_source_origins(&layout, &positions, &operations)?;
        return Ok(Some(PaddedForwardLayout {
            layout,
            logical_code_positions: positions,
            operations,
            source_cell_origins: origins,
        }));
    }
    Ok(None)
}

/// Expands reachable instructions into a bounded graphical source by solving
/// each *unconditional forward* `i` jump's real memory-derived destination.
///
/// Before relocation `D <= C`. When a jump is encountered its operand
/// is either the newly encoded `i` cell (`D == C`) or an already encoded
/// source cell (`D < C`) whose prior XLAT2 mutations are modeled by `shadow`.
/// After relocation, symbolic jumps require proven control words. A single
/// jump with a fully fixed suffix also permits a bounded independently
/// verified whole-source search when earlier expanded arithmetic depends on
/// the final source length.
/// Input-derived operands and unknown future padding remain unsupported.
/// The planner inserts only graphical no-ops to fill unreachable source
/// addresses and encrypts `target - 1` exactly as the VM
/// does. A subsequent `j` may also point to already-passed source scratch
/// when both its operand and destination are behind C; the final independent
/// checker still proves every write is safe. The planner does not search for
/// alternative byte encodings, invent backward edges, or execute guest work.
///
/// # Errors
///
/// Rejects a jump with no skipped forward cell, malformed/oversized plans,
/// unplaceable safe relocation, unproven post-relocation jump operands,
/// explicit targets, or any expanded source refused by independent admission.
pub fn encode_auto_padded_forward_layout(
    profile: &'static ProfileDescriptor,
    logical: &[PaddedForwardStep],
) -> Result<PaddedForwardLayout, LinearLayoutError> {
    if logical.len() < MIN_SOURCE_CELLS {
        return Err(LinearLayoutError::TooShort);
    }
    if logical.len() > MAX_LINEAR_CELLS {
        return Err(LinearLayoutError::TooLong);
    }
    let mut builder = ForwardPaddingBuilder {
        accumulator: Some(0),
        data_pointer: 0,
        operations: Vec::with_capacity(logical.len()),
        positions: Vec::with_capacity(logical.len()),
        profile,
        relocated: false,
        shadow: Vec::with_capacity(logical.len()),
        expanded_writes: Vec::new(),
        unproven_source_writes: Vec::new(),
    };
    for (logical_index, step) in logical.iter().enumerate() {
        let position = match step {
            PaddedForwardStep::AutoRelocate => {
                let remaining = &logical[logical_index + 1..];
                builder.auto_relocate(remaining)
            },
            PaddedForwardStep::Jump => {
                builder.jump(&logical[logical_index + 1..])
            },
            PaddedForwardStep::Instruction(operation) => builder
                .instruction_with_expanded_operand(
                    *operation,
                    None,
                    &logical[logical_index + 1..],
                ),
        };
        let position = match position {
            Ok(position) => position,
            Err(
                error @ (LinearLayoutError::UnsafeDataPlacement
                | LinearLayoutError::JumpPathUnsupported),
            ) => {
                return prove_single_fixed_tail_jump(profile, logical)?
                    .ok_or(error);
            },
            Err(error) => return Err(error),
        };
        builder.positions.push(
            u32::try_from(position)
                .map_err(|_error| LinearLayoutError::TooLong)?,
        );
        builder.advance_data_pointer()?;
    }
    // The existing independent admission controls final source length,
    // dynamic D placement, exact decode identity, skipped gaps and halt.
    let layout = encode_linear_layout(profile, &builder.operations)?;
    let source_cell_origins =
        proven_source_origins(&layout, &builder.positions, &builder.operations)?;
    Ok(PaddedForwardLayout {
        layout,
        logical_code_positions: builder.positions,
        operations: builder.operations,
        source_cell_origins,
    })
}
