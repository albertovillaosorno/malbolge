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
//   - One physical image composing signed EOF and guarded byte parity.
// - Must-Not:
//   - Claim checksum arithmetic, source-frame admission or a loop.
// - Allows:
//   - Inputs: exact current N15 profile.
//   - Outputs: graphical source and proposed physical effect sites.
//   - Side effects: none; normative replay owns acceptance.
// - Split-When:
//   - General physical continuation allocation replaces fixed addresses.
// - Merge-When:
//   - Complete checksum lowering owns both continuations.
// - Summary:
//   - Prepare shared tapes and branch on live input classification.

use malbolge::ProfileDescriptor;

use super::super::{
    LinearOpcode, RelocatedEofBranchSource, unique_graphical_cell,
};
use super::relocated_live_parity_source::{
    NORMALIZER, ONES, PARITY, POINTER, ParityTapes, emit_parity_lookup,
    emit_parity_result,
};
use super::{
    BuildError, Emitter, FRAME, LAYOUT, TapeBounds, TapePlan, encode_i32_cells,
    extended_prefix,
};

const SOURCE_CELLS: usize = 47_814;
const TAPE_BOUNDS: TapeBounds = TapeBounds {
    limit: 7_175_801,
    start: 7_174_601,
};
const ZERO: u32 = 7_174_603;
const BYTE_ENTRY: usize = 30_000;
const EOF_ENTRY: usize = 45_000;
const BYTE_POINTER: u32 = 7_174_485;
const EOF_POINTER: u32 = 7_174_535;
const CLASS: u32 = 7_174_423;

/// A single image with mutually exclusive EOF and successful-byte arms.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RelocatedEofParitySource {
    /// Byte continuation entry.
    pub byte_entry: u32,
    /// Physical class selector word.
    pub class_address: u32,
    /// Initial class write.
    pub class_store_code_address: u32,
    /// Byte and EOF continuation pointer cells, respectively.
    pub continuation_addresses: [u32; 2],
    /// Writes of the two continuation pointer values, respectively.
    pub continuation_store_code_addresses: [u32; 2],
    /// EOF continuation entry.
    pub eof_entry: u32,
    /// EOF halt.
    pub eof_halt_code_address: u32,
    /// EOF output.
    pub eof_output_code_address: u32,
    /// EOF output operand write.
    pub eof_output_store_code_address: u32,
    /// Final normalized low/high writes.
    pub eof_store_code_addresses: [u32; 2],
    /// Even-byte halt.
    pub even_halt_code_address: u32,
    /// Actual first input.
    pub first_input_code_address: u32,
    /// Indirect byte/EOF transfer.
    pub guard_code_address: u32,
    /// Class-selected data transfer.
    pub guard_selector_code_address: u32,
    /// Adjacent input words.
    pub input_pair: [u32; 2],
    /// Actual virgin loader-word rotate.
    pub lookup_code_address: u32,
    /// Odd-byte halt.
    pub odd_halt_code_address: u32,
    /// Output operand address.
    pub output_data_address: u32,
    /// Physical parity scratch word.
    pub parity_address: u32,
    /// Indirect parity transfer.
    pub parity_branch_code_address: u32,
    /// Boolean-selected data transfer.
    pub parity_selector_code_address: u32,
    /// Final Boolean write.
    pub parity_store_code_address: u32,
    /// Complete graphical source.
    pub source: Vec<u8>,
    /// Physical checksum initializer.
    pub zero_pair: [u32; 2],
}

pub(super) fn composed_prefix(
    profile: &ProfileDescriptor,
) -> Result<RelocatedEofBranchSource, BuildError> {
    use LinearOpcode::{Halt, NoOperation, RelocateDataPointer};
    let mut prefix = extended_prefix(profile)?;
    for (position, opcode) in [
        (108, NoOperation),
        (109, RelocateDataPointer),
        (110, NoOperation),
        (111, RelocateDataPointer),
        (112, NoOperation),
        (113, RelocateDataPointer),
        (114, NoOperation),
        (115, NoOperation),
        (116, RelocateDataPointer),
        (117, NoOperation),
        (119, Halt),
        (120, Halt),
        (124, Halt),
    ] {
        let cell = unique_graphical_cell(profile, opcode, position)
            .map_err(|_error| LAYOUT)?;
        *prefix.source.get_mut(position).ok_or(LAYOUT)? = cell;
    }
    Ok(prefix)
}

/// Build both physical continuations in one image.
///
/// The initial dispatch converges at C126 and preserves the input class.
/// Shared marker tapes construct two forward code pointers. The actual
/// class selects one pointer through a read-only route. EOF normalizes
/// the pair and returns zero; bytes retain their raw pair and halt in
/// a parity-selected arm without implementing checksum arithmetic.
///
/// # Errors
/// Refuses unsupported profiles or exhausted bounded layout geometry.
#[expect(
    clippy::too_many_lines,
    reason = "keep the physical sequence auditable"
)]
pub fn build_relocated_eof_parity_source(
    profile: &ProfileDescriptor,
) -> Result<RelocatedEofParitySource, BuildError> {
    use LinearOpcode::{
        CrazyData, Halt, NoOperation, OutputByte, RelocateDataPointer,
        RotateData,
    };
    let prefix = composed_prefix(profile)?;
    let mut emitter = Emitter {
        data: 7_174_418,
        profile,
        source: prefix.source,
        source_cells: SOURCE_CELLS,
        tape_bounds: TAPE_BOUNDS,
    };
    let mut plan = TapePlan::with_bounds(TAPE_BOUNDS);
    let byte_pointer = plan.tape(29_999, false)?;
    let eof_pointer = plan.tape(44_999, false)?;
    let parity = ParityTapes::allocate(&mut plan)?;
    let [low, high] = encode_i32_cells(u32::MAX);
    let eof_low = plan.tape(low, false)?;
    let eof_high = plan.tape(high, false)?;
    emitter.prepare_odd_pairs(&[
        POINTER,
        NORMALIZER,
        PARITY,
        ONES,
        BYTE_POINTER,
        EOF_POINTER,
    ])?;
    emitter.prepare_tape(&plan)?;
    let byte_store = emitter.store_tape(&byte_pointer, BYTE_POINTER, ZERO)?;
    let eof_store = emitter.store_tape(&eof_pointer, EOF_POINTER, ZERO)?;
    emitter.go(CLASS)?;
    let guard_selector_code_address = emitter.append(RelocateDataPointer)?;
    let _: u32 = emitter.append(RelocateDataPointer)?;
    emitter.append_route(b"ooooojoojooooojooj")?;
    for _ in 0u32..68 {
        let _: u32 = emitter.append(NoOperation)?;
    }
    let guard_code_address = emitter.append_indirect()?;

    emitter.pad_to_entry(BYTE_ENTRY, 7_174_486)?;
    parity.store(&mut emitter, ZERO)?;
    let [raw, high_address] = prefix.input_pair;
    let lookup = emit_parity_lookup(&mut emitter, raw)?;
    emitter.append_route(b"ojojoojjjjoojoj")?;
    let parity_store_code_address = emit_parity_result(&mut emitter)?;
    emitter.jump(FRAME)?;
    emitter.walk(PARITY)?;
    let parity_selector_code_address = emitter.append(RelocateDataPointer)?;
    emitter.append_route(b"ojjjjjojjjjojo")?;
    let parity_branch_code_address = emitter.append_indirect()?;

    emitter.pad_to_entry(EOF_ENTRY, 7_174_536)?;
    emitter.prepare_pair()?;
    let low_store = emitter.store_tape(&eof_low, raw, ZERO)?;
    let high_store = emitter.store_tape(&eof_high, high_address, ZERO)?;
    emitter.go(ZERO)?;
    let _: u32 = emitter.linear(RotateData)?;
    emitter.reset()?;
    emitter.walk(7_174_454)?;
    let _: u32 = emitter.linear(CrazyData)?;
    let eof_output_store_code_address = emitter.linear(CrazyData)?;
    let eof_output_code_address = emitter.linear(OutputByte)?;
    let eof_halt_code_address = emitter.append(Halt)?;

    Ok(RelocatedEofParitySource {
        byte_entry: 30_000,
        class_address: CLASS,
        class_store_code_address: prefix.class_store_code_address,
        continuation_addresses: [BYTE_POINTER, EOF_POINTER],
        continuation_store_code_addresses: [byte_store, eof_store],
        eof_entry: 45_000,
        eof_halt_code_address,
        eof_output_code_address,
        eof_output_store_code_address,
        eof_store_code_addresses: [low_store, high_store],
        even_halt_code_address: 124,
        first_input_code_address: prefix.first_input_code_address,
        guard_code_address,
        guard_selector_code_address,
        input_pair: prefix.input_pair,
        lookup_code_address: lookup.lookup,
        odd_halt_code_address: 119,
        output_data_address: prefix.output_data_address,
        parity_address: PARITY,
        parity_branch_code_address,
        parity_selector_code_address,
        parity_store_code_address,
        source: emitter.finish()?,
        zero_pair: prefix.zero_pair,
    })
}
