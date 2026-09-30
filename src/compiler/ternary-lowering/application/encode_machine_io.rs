// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE-APACHE-2.0
//
// Boundary-Contract:
// - Owns:
//   - Deterministic graphical source-cell encoding for realized machine I/O.
// - Must-Not:
//   - Copy XLAT1, guess missing encodings, assign layout positions, or execute
//     VM state.
// - Allows:
//   - Inputs: realized machine I/O, exact code position, canonical decoder
//     port.
//   - Outputs: one unique graphical source cell preserving operation semantics.
//   - Side effects: none.
// - Split-When:
//   - Multi-cell or control-flow encoding requires independent layout policy.
// - Merge-When:
//   - Another application module owns this exact single-cell inverse decode.
// - Summary:
//   - Inverts canonical profile decoding for one already-placed I/O operation.
// - Description:
//   - Exhausts the finite graphical alphabet and rejects zero or multiple
//     matches.
// - Usage:
//   - Called after profile realization and after a code position is chosen.
// - Defaults:
//   - Graphical source alphabet is exactly ASCII 33 through 126 inclusive.
//

//! Deterministic single-cell encoder for realized machine I/O operations.

use super::instruction_decoder_input::ProfileInstructionDecoder;
use super::model::{EncodedMachineIo, MachineIoOperation};

const GRAPHICAL_END: u8 = 126;
const GRAPHICAL_START: u8 = 33;

/// Stable failures for profile instruction-cell encoding.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum MachineIoEncodingError {
    /// More than one graphical source cell decoded to the requested operation.
    AmbiguousEncoding,
    /// No graphical source cell decoded to the requested operation.
    MissingEncoding,
}

/// Encodes one realized machine I/O operation at an exact code position.
///
/// # Errors
///
/// Returns [`MachineIoEncodingError`] unless canonical decoding produces
/// exactly one graphical source cell for the requested decoded instruction.
pub fn encode_machine_io(
    operation: MachineIoOperation,
    code_pointer: u32,
    decoder: &dyn ProfileInstructionDecoder,
) -> Result<EncodedMachineIo, MachineIoEncodingError> {
    let mut selected = None;
    for cell in GRAPHICAL_START..=GRAPHICAL_END {
        if decoder.decode(u32::from(cell), code_pointer)
            == Some(operation.instruction)
        {
            if selected.is_some() {
                return Err(MachineIoEncodingError::AmbiguousEncoding);
            }
            selected = Some(cell);
        }
    }
    let source_cell =
        selected.ok_or(MachineIoEncodingError::MissingEncoding)?;
    Ok(EncodedMachineIo {
        code_pointer,
        operation,
        source_cell,
    })
}
