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
//   - Source-scratch proposal for an actual Fibonacci C output prefix.
// - Must-Not:
//   - Publish a host-computed byte trace without real guest VM output.
// - Allows:
//   - Inputs: independent unsigned recurrence bytes and code phases.
//   - Outputs: a verified forward-jump source and two real guest effects.
//   - Side effects: bounded normative VM replay only.
// - Split-When:
//   - General source-scratch linker work has separate ownership.
// - Merge-When:
//   - A general guest layout synthesizer proves this geometry.
// - Summary:
//   - A forward jump permits scratch writes to past code cells.

use super::super::{ProfileMachine, RunOutcome, pair_source_cells};
use super::*;

#[test]
fn fibonacci_prefix_uses_source_scratch_not_host_output() -> Result<(), String>
{
    let mut previous = 1u32;
    let mut current = 1u32;
    let mut expected = [0u8; 2];
    for byte in &mut expected {
        let next = (previous + current) & 255;
        *byte = u8::try_from(if next & 1 == 0 {
            next
        } else {
            next ^ 0x5a
        })
        .map_err(|error| error.to_string())?;
        previous = current;
        current = next;
    }
    assert_eq!(expected, [0x02, 0x59]);
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile).ok_or("missing decoder phases")?;
    let layout =
        verified_source_scratch_output_layout(profile, expected, &cells)
            .ok_or("source-scratch prefix proposal missed real C effects")?;
    assert!(layout.source().len() > 99);
    assert!(
        layout
            .data_write_positions()
            .iter()
            .flatten()
            .any(|&address| {
                usize::try_from(address)
                    .is_ok_and(|value| value < layout.source().len())
            })
    );
    for input in [Vec::new(), vec![0, 255, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|error| format!("guest load: {error:?}"))?;
        assert!(matches!(
            vm.run(layout.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { .. })
        ));
        assert_eq!(vm.output(), expected);
        assert_eq!(vm.input_consumed(), 0);
    }
    Ok(())
}

#[test]
fn scratch_search_emits_a_third_byte_after_a_forward_jump() -> Result<(), String>
{
    let expected = [0x02, 0x59, 0x1b];
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile).ok_or("missing decoder phases")?;
    let layout =
        verified_source_scratch_output_layout(profile, expected, &cells)
            .ok_or("missing third guest effect")?;
    for input in [Vec::new(), vec![0, 255, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|error| format!("guest load: {error:?}"))?;
        assert!(matches!(
            vm.run(layout.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { .. })
        ));
        assert_eq!(vm.output(), expected);
    }
    Ok(())
}
