// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - LicenseRef-Proprietary
// Confidential:
//   - true
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - A source-independent six-distinct-byte guest arithmetic witness.
// - Must-Not:
//   - Synthesize guest output on the host or claim six-byte C lowering.
// - Allows:
//   - Inputs: canonical current-profile linear guest operations.
//   - Outputs: six exact VM bytes, 15 steps and disjoint guest data writes.
//   - Side effects: none.
// - Split-When:
//   - General guest byte sequence synthesis replaces bounded witnesses.
// - Merge-When:
//   - A source-to-guest six-byte compiler owns this physical proof.
// - Summary:
//   - Six relocated CrazyData operations emit six distinct binary bytes.
// - Description:
//   - Each byte is produced by a real VM arithmetic instruction.
// - Usage:
//   - cargo test --locked --test guest_six_distinct_literal_witness
// - Defaults:
//   - Does not admit any six-byte source C program to the compiler.

//! Six independent data writes and six distinct output bytes in the real VM.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use layout::{encode_linear_layout, LinearOpcode};
use malbolge::{current_profile, ProfileMachine, RunOutcome};

const EXPECTED: [u8; 6] = [0x51, 0x1c, 0x4f, 0x1d, 0x50, 0x1b];

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "assertions independently bind guest arithmetic to the actual VM"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "one physical witness checks writes, exact steps and binary VM output"
)]
fn six_distinct_binary_bytes_are_computed_by_guest_arithmetic() -> Result<(), String> {
    // Prefix and overall source length both affect loader-expanded data words.
    let mut operations = vec![LinearOpcode::NoOperation, LinearOpcode::RelocateDataPointer];
    for _ in 0usize..6 {
        operations.extend([LinearOpcode::CrazyData, LinearOpcode::OutputByte]);
    }
    operations.push(LinearOpcode::Halt);
    assert_eq!(operations.len(), 15);

    let layout = encode_linear_layout(current_profile(), &operations)
        .map_err(|error| format!("encode: {error:?}"))?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    assert_eq!(writes.len(), 6);
    assert_eq!(writes.iter().copied().collect::<BTreeSet<_>>().len(), 6);
    assert!(writes.iter().all(|address| {
        usize::try_from(*address).is_ok_and(|position| position >= layout.source().len())
    }));

    assert_eq!(EXPECTED.iter().copied().collect::<BTreeSet<_>>().len(), 6);
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm = ProfileMachine::from_source(current_profile(), layout.source(), input)
            .map_err(|error| format!("load: {error:?}"))?;
        let outcome = vm.run(15).map_err(|error| format!("run: {error:?}"))?;
        assert!(matches!(outcome, RunOutcome::Terminated { steps, .. } if steps == 15));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), EXPECTED);
    }
    Ok(())
}
