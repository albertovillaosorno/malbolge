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
//   - The stable Rust representation of native region ABI revision 1.
// - Must-Not:
//   - Invoke machine code, allocate executable memory, or define VM semantics.
// - Allows:
//   - Inputs: borrowed guest buffers and exact normative observations.
//   - Outputs: layout-stable call frames, status values, and observations.
//   - Side effects: borrowed buffer mutation only by a future native invoker.
// - Split-When:
//   - Executable-memory ownership or foreign-call execution gains policy.
// - Merge-When:
//   - One native runner owns both the call frame and invocation lifecycle.
// - Summary:
//   - Defines and validates the native region call-frame ABI.
// - Description:
//   - Mirrors the freestanding C ABI while keeping buffer lifetimes scoped.
// - Usage:
//   - Prepared before future verified native object linking and invocation.
// - Defaults:
//   - Invalid counters or foreign enum values fail closed.
//

//! Stable Rust representation of native region ABI revision 1.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::mem::offset_of;

use malbolge::{ProfileMachineObservation, ProfileRegisters, Termination};

/// Freestanding C declarations shared by bootstrap native candidates.
pub(super) const C_ABI_PREFIX: &str = r#"
typedef unsigned char mb_u8;
typedef unsigned int mb_u32;
typedef unsigned long long mb_u64;

#define MB_U8(value) ((mb_u8)(value))
#define MB_U32(value) ((mb_u32)(value##U))
#define MB_U64(value) ((mb_u64)(value##ULL))

static_assert(sizeof(mb_u8) == 1, "8-bit byte required");
static_assert(sizeof(mb_u32) == 4, "32-bit word required");
static_assert(sizeof(mb_u64) == 8, "64-bit ABI integer required");

enum mb_native_status {
    MB_NATIVE_APPLIED = 0,
    MB_NATIVE_GUARD_MISS = 1,
    MB_NATIVE_INVALID_ARGUMENT = 2
};

struct mb_native_region_state {
    mb_u32 *memory;
    mb_u64 memory_words;
    const mb_u8 *input;
    mb_u64 input_len;
    mb_u64 input_consumed;
    mb_u8 *output;
    mb_u64 output_capacity;
    mb_u64 output_len;
    mb_u32 accumulator;
    mb_u32 code_pointer;
    mb_u32 data_pointer;
    mb_u8 termination;
};

int malbolge_native_region_apply(struct mb_native_region_state *state)
{
"#;

/// Complete byte size of [`NativeRegionState`] on the supported 64-bit hosts.
pub const NATIVE_REGION_STATE_SIZE: usize = size_of::<NativeRegionState>();
/// Byte offset of the guest-memory pointer.
pub const NATIVE_REGION_MEMORY_OFFSET: usize =
    offset_of!(NativeRegionState, memory);
/// Byte offset of the guest-memory capacity.
pub const NATIVE_REGION_MEMORY_WORDS_OFFSET: usize =
    offset_of!(NativeRegionState, memory_words);
/// Byte offset of the input pointer.
pub const NATIVE_REGION_INPUT_OFFSET: usize =
    offset_of!(NativeRegionState, input);
/// Byte offset of the input length.
pub const NATIVE_REGION_INPUT_LEN_OFFSET: usize =
    offset_of!(NativeRegionState, input_len);
/// Byte offset of the committed input cursor.
pub const NATIVE_REGION_INPUT_CONSUMED_OFFSET: usize =
    offset_of!(NativeRegionState, input_consumed);
/// Byte offset of the output pointer.
pub const NATIVE_REGION_OUTPUT_OFFSET: usize =
    offset_of!(NativeRegionState, output);
/// Byte offset of the output capacity.
pub const NATIVE_REGION_OUTPUT_CAPACITY_OFFSET: usize =
    offset_of!(NativeRegionState, output_capacity);
/// Byte offset of the committed output length.
pub const NATIVE_REGION_OUTPUT_LEN_OFFSET: usize =
    offset_of!(NativeRegionState, output_len);
/// Byte offset of the accumulator.
pub const NATIVE_REGION_ACCUMULATOR_OFFSET: usize =
    offset_of!(NativeRegionState, accumulator);
/// Byte offset of the code pointer.
pub const NATIVE_REGION_CODE_POINTER_OFFSET: usize =
    offset_of!(NativeRegionState, code_pointer);
/// Byte offset of the data pointer.
pub const NATIVE_REGION_DATA_POINTER_OFFSET: usize =
    offset_of!(NativeRegionState, data_pointer);
/// Byte offset of the termination byte.
pub const NATIVE_REGION_TERMINATION_OFFSET: usize =
    offset_of!(NativeRegionState, termination);

/// Stable status returned by `malbolge_native_region_apply`.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(i32)]
pub enum NativeRegionStatus {
    /// All guards matched and the exact transition committed.
    Applied = 0,
    /// One semantic guard missed and no state may have changed.
    GuardMiss = 1,
    /// The call frame or one required buffer was invalid.
    InvalidArgument = 2,
}

impl NativeRegionStatus {
    /// Returns the exact integer used by native ABI revision 1.
    #[must_use]
    pub const fn code(self) -> i32 {
        match self {
            Self::Applied => 0,
            Self::GuardMiss => 1,
            Self::InvalidArgument => 2,
        }
    }
}

impl TryFrom<i32> for NativeRegionStatus {
    type Error = NativeRegionStatusError;

    fn try_from(code: i32) -> Result<Self, Self::Error> {
        match code {
            0 => Ok(Self::Applied),
            1 => Ok(Self::GuardMiss),
            2 => Ok(Self::InvalidArgument),
            _ => Err(NativeRegionStatusError { code }),
        }
    }
}

/// Unknown integer returned through the native region status ABI.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeRegionStatusError {
    code: i32,
}

impl NativeRegionStatusError {
    /// Returns the unrecognized foreign status integer.
    #[must_use]
    pub const fn code(self) -> i32 {
        self.code
    }
}

impl Display for NativeRegionStatusError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "unknown native region status {}", self.code)
    }
}

/// Stable byte stored in the native termination field.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum NativeTerminationTag {
    /// Guest execution remains live.
    Running = 0,
    /// Guest execution halted through the graphical halt instruction.
    HaltInstruction = 1,
    /// Guest execution stopped on a non-graphical fetched cell.
    NonGraphicalCell = 2,
}

impl NativeTerminationTag {
    /// Returns the exact byte used by native ABI revision 1.
    #[must_use]
    pub const fn code(self) -> u8 {
        match self {
            Self::Running => 0,
            Self::HaltInstruction => 1,
            Self::NonGraphicalCell => 2,
        }
    }

    /// Converts one normative termination observation to its ABI tag.
    #[must_use]
    pub const fn from_termination(termination: Option<Termination>) -> Self {
        match termination {
            None => Self::Running,
            Some(Termination::HaltInstruction) => Self::HaltInstruction,
            Some(Termination::NonGraphicalCell) => Self::NonGraphicalCell,
        }
    }

    /// Converts this ABI tag back to the normative termination observation.
    #[must_use]
    pub const fn termination(self) -> Option<Termination> {
        match self {
            Self::Running => None,
            Self::HaltInstruction => Some(Termination::HaltInstruction),
            Self::NonGraphicalCell => Some(Termination::NonGraphicalCell),
        }
    }
}

impl TryFrom<u8> for NativeTerminationTag {
    type Error = NativeTerminationTagError;

    fn try_from(value: u8) -> Result<Self, Self::Error> {
        match value {
            0 => Ok(Self::Running),
            1 => Ok(Self::HaltInstruction),
            2 => Ok(Self::NonGraphicalCell),
            _ => Err(NativeTerminationTagError { value }),
        }
    }
}

/// Unknown byte observed in the native termination field.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeTerminationTagError {
    value: u8,
}

impl NativeTerminationTagError {
    /// Returns the unrecognized foreign termination byte.
    #[must_use]
    pub const fn value(self) -> u8 {
        self.value
    }
}

impl Display for NativeTerminationTagError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "unknown native termination tag {}", self.value)
    }
}

/// Exact native region call frame consumed by reviewed machine-code templates.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(C)]
pub struct NativeRegionState {
    memory: *mut u32,
    memory_words: u64,
    input: *const u8,
    input_len: u64,
    input_consumed: u64,
    output: *mut u8,
    output_capacity: u64,
    output_len: u64,
    accumulator: u32,
    code_pointer: u32,
    data_pointer: u32,
    termination: u8,
}

impl NativeRegionState {
    /// Returns the accumulator stored in the call frame.
    #[must_use]
    pub const fn accumulator(&self) -> u32 {
        self.accumulator
    }

    /// Returns the code pointer stored in the call frame.
    #[must_use]
    pub const fn code_pointer(&self) -> u32 {
        self.code_pointer
    }

    /// Returns the data pointer stored in the call frame.
    #[must_use]
    pub const fn data_pointer(&self) -> u32 {
        self.data_pointer
    }

    /// Returns the committed input cursor stored in the call frame.
    #[must_use]
    pub const fn input_consumed(&self) -> u64 {
        self.input_consumed
    }

    /// Returns the immutable input capacity visible to native code.
    #[must_use]
    pub const fn input_len(&self) -> u64 {
        self.input_len
    }

    /// Returns the guest-memory capacity visible to native code.
    #[must_use]
    pub const fn memory_words(&self) -> u64 {
        self.memory_words
    }

    /// Reconstructs one normative observation from this call frame.
    ///
    /// # Errors
    ///
    /// Returns [`NativeRegionObservationError`] for counters that do not fit
    /// the host observation type or for an unknown termination byte.
    pub fn observation(
        &self,
    ) -> Result<ProfileMachineObservation, NativeRegionObservationError> {
        if self.input_consumed > self.input_len {
            return Err(NativeRegionObservationError::InputConsumed);
        }
        if self.output_len > self.output_capacity {
            return Err(NativeRegionObservationError::OutputLength);
        }
        let input_consumed = usize::try_from(self.input_consumed)
            .map_err(|_error| NativeRegionObservationError::CounterOverflow)?;
        let output_len = usize::try_from(self.output_len)
            .map_err(|_error| NativeRegionObservationError::CounterOverflow)?;
        let termination = NativeTerminationTag::try_from(self.termination)
            .map_err(NativeRegionObservationError::Termination)?
            .termination();
        Ok(ProfileMachineObservation {
            input_consumed,
            output_len,
            registers: ProfileRegisters {
                accumulator: self.accumulator,
                code_pointer: self.code_pointer,
                data_pointer: self.data_pointer,
            },
            termination,
        })
    }

    /// Returns the mutable output capacity visible to native code.
    #[must_use]
    pub const fn output_capacity(&self) -> u64 {
        self.output_capacity
    }

    /// Returns the committed output length stored in the call frame.
    #[must_use]
    pub const fn output_len(&self) -> u64 {
        self.output_len
    }

    /// Returns the raw termination byte stored in the call frame.
    #[must_use]
    pub const fn termination_tag(&self) -> u8 {
        self.termination
    }
}

/// Failure while constructing a safe borrowed native call frame.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeRegionCallFrameError {
    /// The requested input cursor exceeds the borrowed input slice.
    InputConsumed,
    /// A borrowed slice length could not be represented by the native ABI.
    LengthOverflow,
    /// The requested output length exceeds the borrowed output slice.
    OutputLength,
}

impl Display for NativeRegionCallFrameError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::LengthOverflow => "native region buffer length exceeds u64",
            Self::InputConsumed => "native region input cursor exceeds input",
            Self::OutputLength => {
                "native region output length exceeds capacity"
            },
        })
    }
}

/// Failure while decoding a possibly foreign-mutated native call frame.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeRegionObservationError {
    /// A native counter cannot be represented by the host observation type.
    CounterOverflow,
    /// The native input cursor exceeds its declared input capacity.
    InputConsumed,
    /// The native output length exceeds its declared output capacity.
    OutputLength,
    /// The native termination field contains an unknown byte.
    Termination(NativeTerminationTagError),
}

impl Display for NativeRegionObservationError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::CounterOverflow => {
                f.write_str("native region counter exceeds host usize")
            },
            Self::InputConsumed => {
                f.write_str("native region input cursor exceeds capacity")
            },
            Self::OutputLength => {
                f.write_str("native region output length exceeds capacity")
            },
            Self::Termination(error) => Display::fmt(error, f),
        }
    }
}

/// Borrow-scoped owner of buffers referenced by one native ABI call frame.
#[derive(Debug)]
pub struct NativeRegionCallFrame<'buffers> {
    input: &'buffers [u8],
    memory: &'buffers mut [u32],
    output: &'buffers mut [u8],
    state: NativeRegionState,
}

impl<'buffers> NativeRegionCallFrame<'buffers> {
    /// Returns the immutable input bytes retained for the frame lifetime.
    #[must_use]
    pub const fn input(&self) -> &[u8] {
        self.input
    }

    /// Returns the borrowed guest memory after any future native call.
    #[must_use]
    pub const fn memory(&self) -> &[u32] {
        self.memory
    }

    /// Creates one native call frame over caller-owned guest buffers.
    ///
    /// # Errors
    ///
    /// Returns [`NativeRegionCallFrameError`] when a capacity cannot be encoded
    /// or the observation counters exceed their corresponding borrowed slices.
    pub fn new(
        memory: &'buffers mut [u32],
        input: &'buffers [u8],
        output: &'buffers mut [u8],
        observation: ProfileMachineObservation,
    ) -> Result<Self, NativeRegionCallFrameError> {
        if observation.input_consumed > input.len() {
            return Err(NativeRegionCallFrameError::InputConsumed);
        }
        if observation.output_len > output.len() {
            return Err(NativeRegionCallFrameError::OutputLength);
        }
        let memory_words = u64::try_from(memory.len())
            .map_err(|_error| NativeRegionCallFrameError::LengthOverflow)?;
        let input_len = u64::try_from(input.len())
            .map_err(|_error| NativeRegionCallFrameError::LengthOverflow)?;
        let input_consumed = u64::try_from(observation.input_consumed)
            .map_err(|_error| NativeRegionCallFrameError::LengthOverflow)?;
        let output_capacity = u64::try_from(output.len())
            .map_err(|_error| NativeRegionCallFrameError::LengthOverflow)?;
        let output_len = u64::try_from(observation.output_len)
            .map_err(|_error| NativeRegionCallFrameError::LengthOverflow)?;
        let state = NativeRegionState {
            memory: memory.as_mut_ptr(),
            memory_words,
            input: input.as_ptr(),
            input_len,
            input_consumed,
            output: output.as_mut_ptr(),
            output_capacity,
            output_len,
            accumulator: observation.registers.accumulator,
            code_pointer: observation.registers.code_pointer,
            data_pointer: observation.registers.data_pointer,
            termination: NativeTerminationTag::from_termination(
                observation.termination,
            )
            .code(),
        };
        Ok(Self {
            input,
            memory,
            output,
            state,
        })
    }

    /// Returns the complete borrowed output capacity.
    #[must_use]
    pub const fn output(&self) -> &[u8] {
        self.output
    }

    /// Returns the committed output prefix described by the current ABI state.
    ///
    /// # Errors
    ///
    /// Returns [`NativeRegionObservationError`] when the foreign output
    /// counter cannot be represented or exceeds the borrowed buffer.
    pub fn output_prefix(&self) -> Result<&[u8], NativeRegionObservationError> {
        let output_len = usize::try_from(self.state.output_len)
            .map_err(|_error| NativeRegionObservationError::CounterOverflow)?;
        self.output
            .get(..output_len)
            .ok_or(NativeRegionObservationError::OutputLength)
    }

    /// Returns the exact ABI state value owned by this frame.
    #[must_use]
    pub const fn state(&self) -> &NativeRegionState {
        &self.state
    }

    /// Returns a mutable raw pointer suitable for a future foreign invoker.
    ///
    /// The frame must remain alive and exclusively borrowed for the complete
    /// foreign call. This method does not invoke or dereference the pointer.
    #[must_use]
    pub const fn state_mut_ptr(&mut self) -> *mut NativeRegionState {
        &raw mut self.state
    }
}
