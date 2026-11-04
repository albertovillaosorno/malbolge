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
//   - A source-independent seven-distinct-byte guest arithmetic witness.
// - Must-Not:
//   - Synthesize guest output on the host or claim seven-byte C lowering.
// - Allows:
//   - Inputs: canonical current-profile linear guest operations.
//   - Outputs: seven exact VM bytes, 21 steps and disjoint guest data writes.
//   - Side effects: none.
// - Split-When:
//   - General guest byte sequence synthesis replaces bounded witnesses.
// - Merge-When:
//   - A source-to-guest seven-byte compiler owns this physical proof.
// - Summary:
//   - Seven relocated CrazyData operations emit seven distinct binary bytes.
// - Description:
//   - Each byte is produced by a real VM arithmetic instruction.
// - Usage:
//   - cargo test --locked --test guest_seven_distinct_literal_witness
// - Defaults:
//   - Does not admit any seven-byte source C program to the compiler.

//! Seven independent data writes and seven distinct output bytes in the real VM.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use layout::{LinearOpcode, encode_linear_layout};
use malbolge::{ProfileMachine, RunOutcome, current_profile};

const EXPECTED: [u8; 7] = [0x36, 0x3e, 0x35, 0x02, 0x54, 0x1f, 0x18];

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "assertions independently bind guest arithmetic to the actual VM"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "one physical witness checks writes, exact steps and binary VM output"
)]
fn seven_distinct_binary_bytes_are_computed_by_guest_arithmetic() -> Result<(), String> {
    // Prefix and overall source length both affect loader-expanded data words.
    let mut operations = vec![LinearOpcode::NoOperation; 5];
    operations.push(LinearOpcode::RelocateDataPointer);
    for _ in 0usize..7 {
        operations.extend([LinearOpcode::CrazyData, LinearOpcode::OutputByte]);
    }
    operations.push(LinearOpcode::Halt);
    assert_eq!(operations.len(), 21);

    let layout = encode_linear_layout(current_profile(), &operations)
        .map_err(|error| format!("encode: {error:?}"))?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    assert_eq!(writes.len(), 7);
    assert_eq!(writes.iter().copied().collect::<BTreeSet<_>>().len(), 7);
    assert!(writes.iter().all(|address| {
        usize::try_from(*address).is_ok_and(|position| position >= layout.source().len())
    }));

    assert_eq!(EXPECTED.iter().copied().collect::<BTreeSet<_>>().len(), 7);
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm = ProfileMachine::from_source(current_profile(), layout.source(), input)
            .map_err(|error| format!("load: {error:?}"))?;
        let outcome = vm.run(21).map_err(|error| format!("run: {error:?}"))?;
        assert!(matches!(outcome, RunOutcome::Terminated { steps, .. } if steps == 21));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), EXPECTED);
    }
    Ok(())
}
