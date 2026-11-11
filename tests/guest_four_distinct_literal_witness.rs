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
//   - A source-independent four-distinct-byte guest arithmetic witness.
// - Must-Not:
//   - Synthesize output bytes on the host or claim general C compilation.
// - Allows:
//   - Inputs: canonical current-profile linear guest operations.
//   - Outputs: four distinct VM bytes, exact steps and disjoint write addresses.
//   - Side effects: none.
// - Split-When:
//   - General guest byte-sequence synthesis replaces bounded witnesses.
// - Merge-When:
//   - Four-byte source compilation owns the same physical guest proof.
// - Summary:
//   - Four relocated CrazyData operations emit T=4> under the actual VM.
// - Description:
//   - Retains one observed independently executable output witness.
// - Usage:
//   - cargo test --locked --test guest_four_distinct_literal_witness
// - Defaults:
//   - Does not admit any four-byte source C program to the compiler.

//! A candidate four-distinct-byte target that executes on the normative VM.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use layout::{encode_linear_layout, LinearOpcode};
use malbolge::{current_profile, ProfileMachine, RunOutcome};

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "assertions bind the actual guest arithmetic and VM trace"
)]
fn four_independent_guest_writes_emit_four_printable_bytes() -> Result<(), String> {
    // The eleven inert positions change the loader-expanded source memory.
    let mut operations = vec![LinearOpcode::NoOperation; 11];
    operations.push(LinearOpcode::RelocateDataPointer);
    for _ in 0..4 {
        operations.extend([LinearOpcode::CrazyData, LinearOpcode::OutputByte]);
    }
    operations.push(LinearOpcode::Halt);
    assert_eq!(operations.len(), 21);

    let source = encode_linear_layout(current_profile(), &operations)
        .map_err(|error| format!("encode: {error:?}"))?;
    let writes: Vec<u32> = source
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    assert_eq!(writes.len(), 4, "four independent CrazyData writes");
    assert_eq!(writes.iter().copied().collect::<BTreeSet<_>>().len(), 4);
    assert!(writes.iter().all(|address| {
        usize::try_from(*address).is_ok_and(|value| value >= source.source().len())
    }));

    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm = ProfileMachine::from_source(current_profile(), source.source(), input)
            .map_err(|error| format!("load: {error:?}"))?;
        let outcome = vm
            .run(operations.len())
            .map_err(|error| format!("run: {error:?}"))?;
        assert!(matches!(outcome, RunOutcome::Terminated { steps, .. } if steps == 21));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), b"T=4>");
    }
    Ok(())
}
