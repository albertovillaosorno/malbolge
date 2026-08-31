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
//   - Canonical COFF byte construction for reviewed templates.
// - Must-Not:
//   - Bypass canonical object identity or semantic admission.
// - Allows:
//   - Inputs: reviewed direct-native planning and artifact values.
//   - Outputs: deterministic values owned by this direct-native slice.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - The slice exceeds one independently reviewable responsibility.
// - Merge-When:
//   - Another module owns the exact same direct-native authority.
// - Summary:
//   - Canonical direct-native COFF construction.
// - Description:
//   - Isolates one direct-native responsibility from the facade.
// - Usage:
//   - Used only through the parent direct-native module.
// - Defaults:
//   - Unsupported values fail closed.
//

//! Canonical COFF construction for direct-native templates.

use super::*;

pub(super) fn canonical_coff(
    key: &NativeArtifactKey,
) -> Result<Vec<u8>, DirectDeoptError> {
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => aarch64::deopt_code(),
        HostIsa::X86_64 => x86_64::deopt_code(),
    };
    build_minimal_coff(key, text).ok_or(DirectDeoptError::ObjectBytes)
}

pub(super) fn build_minimal_coff(
    key: &NativeArtifactKey,
    text: &[u8],
) -> Option<Vec<u8>> {
    let (machine, text_characteristics) = match key.target().host_isa() {
        HostIsa::AArch64 => (IMAGE_FILE_MACHINE_ARM64, IMAGE_SCN_ARM64_TEXT),
        HostIsa::X86_64 => (IMAGE_FILE_MACHINE_AMD64, IMAGE_SCN_X86_TEXT),
    };
    let metadata = canonical_profile_metadata(key)?;
    let section_headers = COFF_SECTION_BYTES.checked_mul(2)?;
    let text_start = COFF_HEADER_BYTES.checked_add(section_headers)?;
    let metadata_start = text_start.checked_add(text.len())?;
    let symbol_start = metadata_start.checked_add(metadata.len())?;
    let symbol_start_u32 = u32::try_from(symbol_start).ok()?;
    let text_start_u32 = u32::try_from(text_start).ok()?;
    let metadata_start_u32 = u32::try_from(metadata_start).ok()?;
    let text_len = u32::try_from(text.len()).ok()?;
    let metadata_len = u32::try_from(metadata.len()).ok()?;
    let string_length =
        4usize.checked_add(REQUIRED_ENTRY.len())?.checked_add(1)?;
    let string_length_u32 = u32::try_from(string_length).ok()?;
    let capacity = symbol_start
        .checked_add(COFF_SYMBOL_BYTES)?
        .checked_add(string_length)?;

    let mut object = Vec::with_capacity(capacity);
    push_coff_header(&mut object, machine, symbol_start_u32);
    push_text_section(
        &mut object,
        text_len,
        text_start_u32,
        text_characteristics,
    );
    push_profile_section(&mut object, metadata_len, metadata_start_u32);
    object.extend_from_slice(text);
    object.extend_from_slice(&metadata);
    push_entry_symbol(&mut object, string_length_u32);
    Some(object)
}

pub(super) fn push_coff_header(
    output: &mut Vec<u8>,
    machine: u16,
    symbol_start: u32,
) {
    push_u16(output, machine);
    push_u16(output, 2);
    push_u32(output, 0);
    push_u32(output, symbol_start);
    push_u32(output, 1);
    push_u16(output, 0);
    push_u16(output, 0);
}

pub(super) fn push_profile_section(
    output: &mut Vec<u8>,
    raw_len: u32,
    raw_start: u32,
) {
    output.extend_from_slice(b".mbprof\0");
    push_u32(output, 0);
    push_u32(output, 0);
    push_u32(output, raw_len);
    push_u32(output, raw_start);
    push_u32(output, 0);
    push_u32(output, 0);
    push_u16(output, 0);
    push_u16(output, 0);
    push_u32(output, IMAGE_SCN_PROFILE_METADATA);
}

pub(super) fn push_text_section(
    output: &mut Vec<u8>,
    raw_len: u32,
    raw_start: u32,
    characteristics: u32,
) {
    output.extend_from_slice(b".text\0\0\0");
    push_u32(output, 0);
    push_u32(output, 0);
    push_u32(output, raw_len);
    push_u32(output, raw_start);
    push_u32(output, 0);
    push_u32(output, 0);
    push_u16(output, 0);
    push_u16(output, 0);
    push_u32(output, characteristics);
}

pub(super) fn push_entry_symbol(output: &mut Vec<u8>, string_length: u32) {
    push_u32(output, 0);
    push_u32(output, 4);
    push_u32(output, 0);
    push_u16(output, 1);
    push_u16(output, IMAGE_SYM_DTYPE_FUNCTION);
    output.push(IMAGE_SYM_CLASS_EXTERNAL);
    output.push(0);
    push_u32(output, string_length);
    output.extend_from_slice(REQUIRED_ENTRY.as_bytes());
    output.push(0);
}

pub(super) fn halt_registers_coff(
    key: &NativeArtifactKey,
    observation: ProfileMachineObservation,
) -> Result<Vec<u8>, DirectHaltRegistersError> {
    let direct = direct_entry_observation(observation)
        .ok_or(DirectHaltRegistersError::ObjectBytes)?;
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => aarch64::halt_observation_code(direct),
        HostIsa::X86_64 => x86_64::halt_observation_code(direct),
    }
    .ok_or(DirectHaltRegistersError::ObjectBytes)?;
    build_minimal_coff(key, &text).ok_or(DirectHaltRegistersError::ObjectBytes)
}

pub(super) fn execution_geometry_initial_halt_coff(
    key: &NativeArtifactKey,
    selected: DirectFetchedTerminalProgram,
) -> Result<Vec<u8>, DirectExecutionGeometryInitialHaltError> {
    let observation = direct_entry_observation(selected.observation)
        .ok_or(DirectExecutionGeometryInitialHaltError::ObjectBytes)?;
    let guard = DirectFetchedCellGuard {
        live_in_value: selected.live_in.value,
        required_memory_words: key.ir().required_memory_words(),
    };
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => aarch64::halt_fetch_code(observation, guard),
        HostIsa::X86_64 => x86_64::halt_fetch_code(observation, guard),
    }
    .ok_or(DirectExecutionGeometryInitialHaltError::ObjectBytes)?;
    build_minimal_coff(key, &text)
        .ok_or(DirectExecutionGeometryInitialHaltError::ObjectBytes)
}

pub(super) fn execution_geometry_initial_jump_data_coff(
    key: &NativeArtifactKey,
    selected: DirectInitialJumpDataProgram,
) -> Result<Vec<u8>, DirectExecutionGeometryInitialJumpDataError> {
    let observation = direct_entry_observation(selected.observation)
        .ok_or(DirectExecutionGeometryInitialJumpDataError::ObjectBytes)?;
    let guard = DirectFetchedCellGuard {
        live_in_value: selected.live_in.value,
        required_memory_words: key.ir().required_memory_words(),
    };
    let commit = DirectCodeWriteCommit {
        encrypted_address: selected.live_in.address,
        encrypted_value: selected.encrypted_value,
        next_code_pointer: selected.next_code_pointer,
        next_data_pointer: selected.next_data_pointer,
    };
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => {
            aarch64::no_operation_code(observation, guard, commit)
        },
        HostIsa::X86_64 => {
            x86_64::no_operation_code(observation, guard, commit)
        },
    }
    .ok_or(DirectExecutionGeometryInitialJumpDataError::ObjectBytes)?;
    build_minimal_coff(key, &text)
        .ok_or(DirectExecutionGeometryInitialJumpDataError::ObjectBytes)
}

pub(super) fn execution_geometry_input_coff(
    key: &NativeArtifactKey,
    selected: DirectInputProgram,
) -> Result<Vec<u8>, DirectExecutionGeometryInputError> {
    let observation = direct_entry_observation(selected.observation)
        .ok_or(DirectExecutionGeometryInputError::ObjectBytes)?;
    let guard = DirectInputGuard {
        code_live_in: selected.live_in.value,
        input: selected.input,
        input_index: observation.input_consumed,
        required_memory_words: key.ir().required_memory_words(),
    };
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => {
            aarch64::input_code(observation, guard, selected.commit)
        },
        HostIsa::X86_64 => {
            x86_64::input_code(observation, guard, selected.commit)
        },
    }
    .ok_or(DirectExecutionGeometryInputError::ObjectBytes)?;
    build_minimal_coff(key, &text)
        .ok_or(DirectExecutionGeometryInputError::ObjectBytes)
}

pub(super) fn execution_geometry_no_operation_coff(
    key: &NativeArtifactKey,
    selected: DirectNoOperationProgram,
) -> Result<Vec<u8>, DirectExecutionGeometryNoOperationError> {
    let observation = direct_entry_observation(selected.observation)
        .ok_or(DirectExecutionGeometryNoOperationError::ObjectBytes)?;
    let guard = DirectFetchedCellGuard {
        live_in_value: selected.live_in.value,
        required_memory_words: key.ir().required_memory_words(),
    };
    let commit = DirectCodeWriteCommit {
        encrypted_address: selected.live_in.address,
        encrypted_value: selected.encrypted_value,
        next_code_pointer: selected.next_code_pointer,
        next_data_pointer: selected.next_data_pointer,
    };
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => {
            aarch64::no_operation_code(observation, guard, commit)
        },
        HostIsa::X86_64 => {
            x86_64::no_operation_code(observation, guard, commit)
        },
    }
    .ok_or(DirectExecutionGeometryNoOperationError::ObjectBytes)?;
    build_minimal_coff(key, &text)
        .ok_or(DirectExecutionGeometryNoOperationError::ObjectBytes)
}

pub(super) fn execution_geometry_output_coff(
    key: &NativeArtifactKey,
    selected: DirectOutputProgram,
) -> Result<Vec<u8>, DirectExecutionGeometryOutputError> {
    let observation = direct_entry_observation(selected.observation)
        .ok_or(DirectExecutionGeometryOutputError::ObjectBytes)?;
    let guard = DirectFetchedCellGuard {
        live_in_value: selected.live_in.value,
        required_memory_words: key.ir().required_memory_words(),
    };
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => {
            aarch64::output_code(observation, guard, selected.commit)
        },
        HostIsa::X86_64 => {
            x86_64::output_code(observation, guard, selected.commit)
        },
    }
    .ok_or(DirectExecutionGeometryOutputError::ObjectBytes)?;
    build_minimal_coff(key, &text)
        .ok_or(DirectExecutionGeometryOutputError::ObjectBytes)
}

pub(super) fn execution_geometry_rotate_coff(
    key: &NativeArtifactKey,
    selected: DirectRotateProgram,
) -> Result<Vec<u8>, DirectExecutionGeometryRotateError> {
    let observation = direct_entry_observation(selected.observation)
        .ok_or(DirectExecutionGeometryRotateError::ObjectBytes)?;
    let guard = DirectRotateGuard {
        code_live_in: selected.code_live_in.value,
        data_live_in: selected.data_live_in.value,
        required_memory_words: key.ir().required_memory_words(),
    };
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => {
            aarch64::rotate_code(observation, guard, selected.commit)
        },
        HostIsa::X86_64 => {
            x86_64::rotate_code(observation, guard, selected.commit)
        },
    }
    .ok_or(DirectExecutionGeometryRotateError::ObjectBytes)?;
    build_minimal_coff(key, &text)
        .ok_or(DirectExecutionGeometryRotateError::ObjectBytes)
}

pub(super) fn halt_fetch_coff(
    key: &NativeArtifactKey,
    selected: DirectFetchedTerminalProgram,
) -> Result<Vec<u8>, DirectHaltFetchError> {
    let observation = direct_entry_observation(selected.observation)
        .ok_or(DirectHaltFetchError::ObjectBytes)?;
    let guard = DirectFetchedCellGuard {
        live_in_value: selected.live_in.value,
        required_memory_words: key.ir().required_memory_words(),
    };
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => aarch64::halt_fetch_code(observation, guard),
        HostIsa::X86_64 => x86_64::halt_fetch_code(observation, guard),
    }
    .ok_or(DirectHaltFetchError::ObjectBytes)?;
    build_minimal_coff(key, &text).ok_or(DirectHaltFetchError::ObjectBytes)
}

pub(super) fn non_graphical_coff(
    key: &NativeArtifactKey,
    selected: DirectFetchedTerminalProgram,
) -> Result<Vec<u8>, DirectNonGraphicalError> {
    let observation = direct_entry_observation(selected.observation)
        .ok_or(DirectNonGraphicalError::ObjectBytes)?;
    let guard = DirectFetchedCellGuard {
        live_in_value: selected.live_in.value,
        required_memory_words: key.ir().required_memory_words(),
    };
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => aarch64::non_graphical_code(observation, guard),
        HostIsa::X86_64 => x86_64::non_graphical_code(observation, guard),
    }
    .ok_or(DirectNonGraphicalError::ObjectBytes)?;
    build_minimal_coff(key, &text).ok_or(DirectNonGraphicalError::ObjectBytes)
}

pub(super) fn jump_code_coff(
    key: &NativeArtifactKey,
    selected: DirectJumpCodeProgram,
) -> Result<Vec<u8>, DirectJumpCodeError> {
    let observation = direct_entry_observation(selected.observation)
        .ok_or(DirectJumpCodeError::ObjectBytes)?;
    let guard = DirectJumpCodeGuard {
        code_live_in: selected.code_live_in.value,
        data_live_in: selected.data_live_in.value,
        encryption_live_in: selected.encryption_live_in.value,
        required_memory_words: key.ir().required_memory_words(),
    };
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => {
            aarch64::jump_code_code(observation, guard, selected.commit)
        },
        HostIsa::X86_64 => {
            x86_64::jump_code_code(observation, guard, selected.commit)
        },
    }
    .ok_or(DirectJumpCodeError::ObjectBytes)?;
    build_minimal_coff(key, &text).ok_or(DirectJumpCodeError::ObjectBytes)
}

pub(super) fn jump_data_coff(
    key: &NativeArtifactKey,
    selected: DirectJumpDataProgram,
) -> Result<Vec<u8>, DirectJumpDataError> {
    let observation = direct_entry_observation(selected.observation)
        .ok_or(DirectJumpDataError::ObjectBytes)?;
    let guard = DirectJumpDataGuard {
        code_live_in: selected.code_live_in.value,
        data_live_in: selected.data_live_in.value,
        required_memory_words: key.ir().required_memory_words(),
    };
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => {
            aarch64::jump_data_code(observation, guard, selected.commit)
        },
        HostIsa::X86_64 => {
            x86_64::jump_data_code(observation, guard, selected.commit)
        },
    }
    .ok_or(DirectJumpDataError::ObjectBytes)?;
    build_minimal_coff(key, &text).ok_or(DirectJumpDataError::ObjectBytes)
}

pub(super) fn crazy_coff(
    key: &NativeArtifactKey,
    selected: DirectCrazyProgram,
) -> Result<Vec<u8>, DirectCrazyError> {
    let observation = direct_entry_observation(selected.observation)
        .ok_or(DirectCrazyError::ObjectBytes)?;
    let guard = DirectCrazyGuard {
        code_live_in: selected.code_live_in.value,
        data_live_in: selected.data_live_in.value,
        required_memory_words: key.ir().required_memory_words(),
    };
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => {
            aarch64::crazy_code(observation, guard, selected.commit)
        },
        HostIsa::X86_64 => {
            x86_64::crazy_code(observation, guard, selected.commit)
        },
    }
    .ok_or(DirectCrazyError::ObjectBytes)?;
    build_minimal_coff(key, &text).ok_or(DirectCrazyError::ObjectBytes)
}

pub(super) fn input_coff(
    key: &NativeArtifactKey,
    selected: DirectInputProgram,
) -> Result<Vec<u8>, DirectInputError> {
    let observation = direct_entry_observation(selected.observation)
        .ok_or(DirectInputError::ObjectBytes)?;
    let guard = DirectInputGuard {
        code_live_in: selected.live_in.value,
        input: selected.input,
        input_index: observation.input_consumed,
        required_memory_words: key.ir().required_memory_words(),
    };
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => {
            aarch64::input_code(observation, guard, selected.commit)
        },
        HostIsa::X86_64 => {
            x86_64::input_code(observation, guard, selected.commit)
        },
    }
    .ok_or(DirectInputError::ObjectBytes)?;
    build_minimal_coff(key, &text).ok_or(DirectInputError::ObjectBytes)
}

pub(super) fn output_coff(
    key: &NativeArtifactKey,
    selected: DirectOutputProgram,
) -> Result<Vec<u8>, DirectOutputError> {
    let observation = direct_entry_observation(selected.observation)
        .ok_or(DirectOutputError::ObjectBytes)?;
    let guard = DirectFetchedCellGuard {
        live_in_value: selected.live_in.value,
        required_memory_words: key.ir().required_memory_words(),
    };
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => {
            aarch64::output_code(observation, guard, selected.commit)
        },
        HostIsa::X86_64 => {
            x86_64::output_code(observation, guard, selected.commit)
        },
    }
    .ok_or(DirectOutputError::ObjectBytes)?;
    build_minimal_coff(key, &text).ok_or(DirectOutputError::ObjectBytes)
}

pub(super) fn rotate_coff(
    key: &NativeArtifactKey,
    selected: DirectRotateProgram,
) -> Result<Vec<u8>, DirectRotateError> {
    let observation = direct_entry_observation(selected.observation)
        .ok_or(DirectRotateError::ObjectBytes)?;
    let guard = DirectRotateGuard {
        code_live_in: selected.code_live_in.value,
        data_live_in: selected.data_live_in.value,
        required_memory_words: key.ir().required_memory_words(),
    };
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => {
            aarch64::rotate_code(observation, guard, selected.commit)
        },
        HostIsa::X86_64 => {
            x86_64::rotate_code(observation, guard, selected.commit)
        },
    }
    .ok_or(DirectRotateError::ObjectBytes)?;
    build_minimal_coff(key, &text).ok_or(DirectRotateError::ObjectBytes)
}

pub(super) fn no_operation_coff(
    key: &NativeArtifactKey,
    selected: DirectNoOperationProgram,
) -> Result<Vec<u8>, DirectNoOperationError> {
    let observation = direct_entry_observation(selected.observation)
        .ok_or(DirectNoOperationError::ObjectBytes)?;
    let guard = DirectFetchedCellGuard {
        live_in_value: selected.live_in.value,
        required_memory_words: key.ir().required_memory_words(),
    };
    let commit = DirectCodeWriteCommit {
        encrypted_address: selected.live_in.address,
        encrypted_value: selected.encrypted_value,
        next_code_pointer: selected.next_code_pointer,
        next_data_pointer: selected.next_data_pointer,
    };
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => {
            aarch64::no_operation_code(observation, guard, commit)
        },
        HostIsa::X86_64 => {
            x86_64::no_operation_code(observation, guard, commit)
        },
    }
    .ok_or(DirectNoOperationError::ObjectBytes)?;
    build_minimal_coff(key, &text).ok_or(DirectNoOperationError::ObjectBytes)
}

pub(super) fn initial_halt_coff(
    key: &NativeArtifactKey,
) -> Result<Vec<u8>, DirectInitialHaltError> {
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => aarch64::initial_halt_code(),
        HostIsa::X86_64 => x86_64::initial_halt_code(),
    };
    build_minimal_coff(key, text).ok_or(DirectInitialHaltError::ObjectBytes)
}

pub(super) fn direct_entry_observation(
    observation: ProfileMachineObservation,
) -> Option<DirectEntryObservation> {
    let registers = observation.registers;
    Some(DirectEntryObservation {
        accumulator: registers.accumulator,
        code_pointer: registers.code_pointer,
        data_pointer: registers.data_pointer,
        input_consumed: u64::try_from(observation.input_consumed).ok()?,
        output_len: u64::try_from(observation.output_len).ok()?,
    })
}

pub(super) fn is_zero_observation(
    observation: ProfileMachineObservation,
) -> bool {
    observation.input_consumed == 0
        && observation.output_len == 0
        && observation.registers == ProfileRegisters::default()
        && observation.termination.is_none()
}

pub(super) fn push_u16(output: &mut Vec<u8>, value: u16) {
    output.extend_from_slice(&value.to_le_bytes());
}

pub(super) fn push_u32(output: &mut Vec<u8>, value: u32) {
    output.extend_from_slice(&value.to_le_bytes());
}
