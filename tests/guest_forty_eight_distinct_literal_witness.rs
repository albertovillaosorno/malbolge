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
//   - A source-independent forty-eight-distinct-byte guest arithmetic witness.
// - Must-Not:
//   - Synthesize guest output on the host or claim forty-eight-byte C lowering.
// - Allows:
//   - Inputs: canonical current-profile linear guest operations.
//   - Outputs: forty-eight exact VM bytes and disjoint guest data writes.
//   - Side effects: none.
// - Split-When:
//   - General guest byte sequence synthesis replaces bounded witnesses.
// - Merge-When:
//   - A source-to-guest forty-eight-byte compiler owns this physical proof.
// - Summary:
//   - Forty-eight relocated guest arithmetic instructions emit distinct bytes.
// - Description:
//   - Every byte is computed by the real VM, not host output substitution.
// - Usage:
//   - cargo test --locked --test guest_forty_eight_distinct_literal_witness
// - Defaults:
//   - Does not admit any forty-eight-byte source C program to the compiler.

//! Forty-eight disjoint guest arithmetic writes and distinct bytes in the real
//! VM.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use layout::{LinearOpcode, encode_linear_layout};
use malbolge::{ProfileMachine, RunOutcome, current_profile};

const EXPECTED: [u8; 48] = [
    81, 55, 52, 56, 251, 206, 159, 152, 184, 180, 131, 205, 4, 202, 28, 27, 46,
    79, 139, 207, 167, 162, 149, 214, 150, 161, 175, 197, 186, 224, 157, 225,
    185, 65, 71, 92, 42, 68, 41, 14, 50, 78, 49, 24, 31, 76, 32, 23,
];

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "assertions bind guest arithmetic to the normative real VM"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "one physical witness checks writes, exact steps and binary output"
)]
fn forty_eight_distinct_binary_bytes_are_computed_by_guest_arithmetic()
-> Result<(), String> {
    // Thirteen reached no-ops place relocation at source position 13.
    // Ten interleaved no-ops shift the 48 distinct arithmetic data words.
    // Four rotations break repeated crazy-derived output bytes.
    const PADS: [u32; 10] = [13, 14, 16, 18, 20, 22, 27, 37, 40, 44];
    const ROTATIONS: [u32; 4] = [4, 12, 18, 33];
    let mut operations = vec![LinearOpcode::NoOperation; 13];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0..48u32 {
        if PADS.contains(&index) {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if ROTATIONS.contains(&index) {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    assert_eq!(operations.len(), 121);
    let layout = encode_linear_layout(current_profile(), &operations)
        .map_err(|error| format!("encode: {error:?}"))?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    let expected_writes: Vec<u32> = (0..48u32)
        .map(|i| {
            122 + 2 * i
                + PADS.iter().filter(|&&pad_at| i >= pad_at).count() as u32
        })
        .collect();
    assert_eq!(writes, expected_writes);
    assert_eq!(writes.iter().copied().collect::<BTreeSet<_>>().len(), 48);
    assert!(writes.iter().all(|address| {
        usize::try_from(*address)
            .is_ok_and(|position| position >= layout.source().len())
    }));
    assert_eq!(EXPECTED.iter().copied().collect::<BTreeSet<_>>().len(), 48);
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm = ProfileMachine::from_source(
            current_profile(),
            layout.source(),
            input,
        )
        .map_err(|error| format!("load: {error:?}"))?;
        let outcome = vm.run(121).map_err(|error| format!("run: {error:?}"))?;
        assert!(matches!(outcome, RunOutcome::Terminated { steps: 121, .. }));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), EXPECTED);
    }
    // The encoded j word leaves exactly one word beyond the 121 source cells;
    // extending source by one cell must refuse the code/data alias.
    operations.insert(operations.len() - 1, LinearOpcode::NoOperation);
    assert!(matches!(
        encode_linear_layout(current_profile(), &operations),
        Err(layout::LinearLayoutError::UnsafeDataPlacement)
    ));
    Ok(())
}
