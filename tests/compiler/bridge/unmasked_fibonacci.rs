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
//   - Independent original-C Fibonacci prefix and guest loopback evidence.
// - Must-Not:
//   - Substitute host output for guest computation or weaken layout admission.
// - Allows:
//   - Inputs: source-proven unsigned C recurrence and graphical source cells.
//   - Outputs: independently admitted and VM-checked real guest output bytes.
//   - Side effects: bounded normative VM execution only.
// - Split-When:
//   - General source-scratch synthesis subsumes data-write/relocation search.
// - Merge-When:
//   - Complete unmasked C Fibonacci reaches the production guest compiler.
// - Summary:
//   - A real write and live j escape the pristine graphical byte restriction.

use super::super::{ProfileMachine, RunOutcome, encode_linear_layout};
use super::*;

/// Independently evaluate the complete C recurrence, without host output.
fn original_fibonacci_bytes() -> [u8; 12] {
    let (mut a, mut b) = (1u32, 1u32);
    let mut expected = [0u8; 12];
    for output in &mut expected {
        let next = (a + b) & 255;
        *output = (if next & 1 == 0 {
            next
        } else {
            next ^ 0x5a
        }) as u8;
        a = b;
        b = next;
    }
    expected
}

/// Reconstruct reached operations from the independent positional decoder;
/// the original two-byte source is only a search seed, never a guest oracle.
fn decode_prefix_operations(
    source: &[u8],
    jump_target: usize,
) -> Result<Vec<LinearOpcode>, String> {
    let mut operations = Vec::with_capacity(source.len());
    for (address, &byte) in source.iter().enumerate() {
        let operation = if address == 0 {
            LinearOpcode::JumpForward {
                target: u32::try_from(jump_target)
                    .map_err(|error| error.to_string())?,
            }
        } else if address < jump_target {
            LinearOpcode::SkippedDataByte { byte: u32::from(byte) }
        } else {
            match malbolge::decode_profile_instruction(
                u32::from(byte),
                address as u32,
            ) {
                Some(b'o') => LinearOpcode::NoOperation,
                Some(b'p') => LinearOpcode::CrazyData,
                Some(b'*') => LinearOpcode::RotateData,
                Some(b'<') => LinearOpcode::OutputByte,
                Some(b'v') => LinearOpcode::Halt,
                other => {
                    return Err(format!(
                        "unproved reached opcode {other:?} at {address}"
                    ));
                },
            }
        };
        operations.push(operation);
    }
    if operations.pop() != Some(LinearOpcode::Halt) {
        return Err(String::from("two-byte source is not terminated"));
    }
    Ok(operations)
}

#[test]
fn original_fibonacci_third_byte_reaches_real_guest_through_written_source()
-> Result<(), String> {
    let expected = original_fibonacci_bytes();
    assert_eq!(expected, [2, 89, 95, 8, 87, 79, 34, 109, 3, 144, 179, 35]);
    let profile = malbolge::current_profile();
    let prefix = verified_variable_source_scratch_at_jump(
        profile,
        [expected[0], expected[1]],
        0,
        0,
    )
    .ok_or("no original C two-byte guest prefix")?;
    let mut machine =
        ProfileMachine::from_source(profile, prefix.source(), Vec::new())
            .map_err(|error| format!("prefix load: {error:?}"))?;
    let _prefix_run = machine
        .run(prefix.executed_code_positions().len() - 1)
        .map_err(|error| format!("prefix execute: {error:?}"))?;
    if machine.output() != &expected[..2] {
        return Err(String::from("C prefix did not execute on actual VM"));
    }
    // D is 6 before the seed's final halt. A no-op advances D one cell;
    // this intentionally moves it to the previously skipped source at 67.
    let initial_data_pointer =
        usize::try_from(machine.registers().data_pointer)
            .map_err(|error| error.to_string())?;
    let scratch = 67usize;
    if initial_data_pointer != 6 || prefix.source().len() != 105 {
        return Err(String::from("source-scratch prefix geometry drifted"));
    }
    let mut operations = decode_prefix_operations(prefix.source(), 99)?;
    // The first guest * replaces a graphical word with a full rotated word.
    // The following j reads source[68] == 66 and returns D to source[67].
    // The second * and real p operations now consume guest-evolved data.
    for (address, byte) in
        [(67usize, 95u32), (68, 66), (69, 93), (70, 92), (71, 104)]
    {
        operations[address] = LinearOpcode::SkippedDataByte { byte };
    }
    operations.extend(repeat_n(
        LinearOpcode::NoOperation,
        scratch - initial_data_pointer,
    ));
    operations.extend([
        LinearOpcode::RotateData,
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::RotateData,
        LinearOpcode::CrazyData,
        LinearOpcode::CrazyData,
        LinearOpcode::CrazyData,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::Halt,
    ]);
    let guest =
        encode_linear_layout(profile, &operations).map_err(|error| {
            format!("independent source/relocation admission: {error:?}")
        })?;
    assert_eq!(guest.source().len(), operations.len());
    assert_eq!(guest.data_write_positions().iter().flatten().count(), 9);
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, guest.source(), input)
                .map_err(|error| format!("normative VM load: {error:?}"))?;
        let outcome = vm
            .run(guest.executed_code_positions().len())
            .map_err(|error| format!("normative VM replay: {error:?}"))?;
        if !matches!(outcome, RunOutcome::Terminated { steps, .. }
            if steps == guest.executed_code_positions().len())
            || vm.output() != &expected[..3]
            || vm.input_consumed() != 0
        {
            return Err(format!("real C prefix guest diverged: {outcome:?}"));
        }
    }
    Ok(())
}
