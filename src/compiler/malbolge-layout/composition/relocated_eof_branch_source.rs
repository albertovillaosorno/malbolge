// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Boundary-Contract:
// - Owns:
//   - One relocated N15 byte/EOF dispatch with a genuine EOF output store.
// - Must-Not:
//   - Treat raw EOF as signed C23 or claim a linked source checksum loop.
// - Allows:
//   - Inputs: the exact modern profile and bounded graphical source geometry.
//   - Outputs: a source image and the physical addresses of reached effects.
//   - Side effects: none; the normative VM independently checks execution.
// - Split-When:
//   - The two arms require separate relocatable code-layout machinery.
// - Merge-When:
//   - The source-C linker owns general conditional dispatch and state storage.
// - Summary:
//   - Collapses every successful first byte into one physical branch class.

//! A relocated two-arm physical prefix for the original C23 EOF checksum.
//!
//! The byte arm performs one more genuine input and stops, without computing
//! an iteration. Only EOF writes the empty-stream output word and emits zero.
//! The source's signed EOF representation and loop remain unimplemented.

use malbolge::{ProfileDescriptor, current_profile};

use super::{
    CodeVisitRequirement, LinearOpcode, ZeroCellSourceError,
    encode_code_visits, unique_graphical_cell, unwritten_loader_word,
};

const SOURCE_CELLS: usize = 156;

/// One finite source-loaded byte/EOF branch with adjacent raw input storage.
///
/// Physical effects and their addresses are candidates for independent VM
/// verification, not a source-frame certificate. Some scratch writes borrow
/// the source frame's reserved words. The raw EOF pair is not C23 signed -1.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RelocatedEofBranchSource {
    /// Shared C118 indirect code transfer.
    pub branch_code_address: u32,
    /// C121 halt of the byte arm, without an implemented checksum iteration.
    pub byte_halt_code_address: u32,
    /// C120 byte landing and second actual input instruction.
    pub byte_input_code_address: u32,
    /// M7,174,423 holds one of two class words after the C99 crazy operation.
    pub class_data_address: u32,
    /// C99 writes the final byte/EOF class word.
    pub class_store_code_address: u32,
    /// C126 EOF-only landing.
    pub eof_arm_code_address: u32,
    /// C142 EOF-only halt after zero output.
    pub eof_halt_code_address: u32,
    /// C141 EOF-only output instruction.
    pub eof_output_code_address: u32,
    /// C140 actual zero store into the original source output operand.
    pub eof_output_store_code_address: u32,
    /// C53 first actual input instruction.
    pub first_input_code_address: u32,
    /// The physically stored raw first-input pair, low then high.
    pub input_pair: [u32; 2],
    /// The original source output SSA operand's physical address.
    pub output_data_address: u32,
    /// Graphical source including its two distinct loader seed bytes.
    pub source: Vec<u8>,
    /// The physically initialized checksum pair, low then high.
    pub zero_pair: [u32; 2],
}

const fn relocated_opcode(position: usize) -> LinearOpcode {
    use LinearOpcode::{
        CrazyData, Halt, InputWord, NoOperation, OutputByte,
        RelocateDataPointer, RotateData, SkippedDataByte,
    };
    match position {
        9
        | 42
        | 46
        | 54
        | 60
        | 68
        | 76
        | 84
        | 92
        | 100
        | 107
        | 108
        | 110
        | 112..=115
        | 126
        | 128
        | 131
        | 132
        | 138 => RelocateDataPointer,
        40
        | 41
        | 43..=45
        | 47
        | 49..=51
        | 59
        | 63
        | 66
        | 97
        | 99
        | 139
        | 140 => CrazyData,
        64 | 67 | 75 | 83 | 91 | 127 | 133 => RotateData,
        53 | 120 => InputWord,
        121 | 142 => Halt,
        141 => OutputByte,
        154 => SkippedDataByte { byte: 39 },
        155 => SkippedDataByte { byte: 37 },
        _ => NoOperation,
    }
}

/// Build the relocated source with a stable byte arm and true EOF arm.
///
/// The 156-cell image leaves the first C9 relocation pointing to source
/// C126, then advances D to expanded memory M156 before the initial writes.
/// Four rotations of loader word 37 construct mask 6,554,439. With the
/// input encoded by all-ones crazy, C97 and C99 fold it into exactly
/// 6,554,439 for a byte and 13,108,878 for EOF. C107 and C108 then read
/// distinct virgin loader cells and the C118 transfer selects C120 or C126.
/// No branch route dereferences the saved raw first-input word. On EOF
/// only, an actual reentry and two crazy stores produce the output operand.
///
/// # Errors
/// Refuses noncurrent profiles or changed graphical/loader geometry.
pub fn build_relocated_eof_branch_source(
    profile: &ProfileDescriptor,
) -> Result<RelocatedEofBranchSource, ZeroCellSourceError> {
    use ZeroCellSourceError::{NoLoadableZero, UnsupportedProfile};
    if profile != current_profile() {
        return Err(UnsupportedProfile);
    }

    let mut source = Vec::with_capacity(SOURCE_CELLS);
    for position in 0..SOURCE_CELLS {
        let cell = if position == 118 {
            // The real target depends on D, unlike linear JumpForward.
            encode_code_visits(profile, 118, &[CodeVisitRequirement::Decoded(
                b'i',
            )])
            .map_err(|_error| NoLoadableZero)?
        } else {
            unique_graphical_cell(profile, relocated_opcode(position), position)
                .map_err(|_error| NoLoadableZero)?
        };
        source.push(cell);
    }

    if source.get(9) != Some(&125) {
        return Err(NoLoadableZero);
    }
    for (address, expected) in [
        (156, 7_174_416),
        (157, 37),
        (158, 7_174_416),
        (6_554_440, 7_174_416),
        (13_108_879, 37),
        (7_174_417, 37),
        (7_174_418, 7_174_416),
        (7_174_423, 37),
        (7_174_424, 7_174_416),
        (7_174_454, 7_174_416),
        (7_174_455, 37),
        (4_782_982, 7_174_416),
    ] {
        if unwritten_loader_word(&source, address, profile)
            .map_err(|_error| NoLoadableZero)?
            != expected
        {
            return Err(NoLoadableZero);
        }
    }

    Ok(RelocatedEofBranchSource {
        branch_code_address: 118,
        byte_halt_code_address: 121,
        byte_input_code_address: 120,
        class_data_address: 7_174_423,
        class_store_code_address: 99,
        eof_arm_code_address: 126,
        eof_halt_code_address: 142,
        eof_output_code_address: 141,
        eof_output_store_code_address: 140,
        first_input_code_address: 53,
        input_pair: [7_174_419, 7_174_420],
        output_data_address: 7_174_455,
        source,
        zero_pair: [7_174_417, 7_174_418],
    })
}
