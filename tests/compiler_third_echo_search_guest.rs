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
//   - Finite graphical one-cell bound for guarded-third-read continuation.
// - Must-Not:
//   - Treat a halted wrong-output path as a valid third-byte echo or C23.
// - Allows:
//   - Inputs: exact N15 layout, 104 source-valid single-cell candidates.
//   - Outputs: independent real-VM byte/EOF branch counterexamples.
//   - Side effects: isolated in-memory guest executions only.
// - Split-When:
//   - A general encrypted-revisit layout solver replaces this fixed bound.
// - Merge-When:
//   - Verified dynamic source-C guest control subsumes the local rejection.
// - Summary:
//   - Rejects one-cell repairs that fail to emit a guarded third input.

//! The fixed guarded third-input skeleton has no safe one-cell third echo.
//! This is a bound on one *specific* four-patch continuation, not a proof
//! that no larger guest source can emit the conditional third byte.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use malbolge::{
    ProfileMachine, ProfileRegisters, RunOutcome, Termination, TraceInput,
    current_profile, decode_profile_instruction,
};

fn graphical_opcode(position: u32, opcode: u8) -> Option<u8> {
    (33..=126u8).find(|byte| {
        decode_profile_instruction(u32::from(*byte), position) == Some(opcode)
    })
}

struct PathOutcome {
    consumed: usize,
    halted: bool,
    output: Vec<u8>,
    read_sites: Vec<(u32, TraceInput)>,
}

fn actual_path(memory: &[u32], input: Vec<u8>) -> Result<PathOutcome, String> {
    let mut vm = ProfileMachine::from_state(
        current_profile(),
        memory.to_vec(),
        input,
        ProfileRegisters::default(),
    )
    .map_err(|error| error.to_string())?;
    let mut read_sites = Vec::new();
    let result = vm.run_traced(220, &mut |step| {
        if let Some(value) = step.input {
            read_sites.push((step.before.registers.code_pointer, value));
        }
    });
    Ok(PathOutcome {
        consumed: vm.input_consumed(),
        halted: matches!(
            result,
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                ..
            })
        ),
        output: vm.output().to_vec(),
        read_sites,
    })
}

#[test]
#[expect(
    clippy::too_many_lines,
    reason = "enumerated source-encoding and two full guest-path controls"
)]
fn no_single_cell_fix_restores_third_echo_and_second_eof() -> Result<(), String>
{
    let profile = current_profile();
    let mut source =
        layout::build_second_input_guarded_third_read_source(profile)
            .map_err(|error| format!("guarded source: {error:?}"))?;
    // These four published negative-control edits suppress the encrypted
    // C104 halt, avoid C112's unintended indirect jump, then reserve a
    // C115 third-word output and C116 halt. C114 still fails on revisit.
    for (position, opcode) in
        [(104u32, b'o'), (112, b'p'), (115, b'<'), (116, b'v')]
    {
        source
            [usize::try_from(position).map_err(|error| error.to_string())?] =
            graphical_opcode(position, opcode)
                .ok_or("missing graphical continuation encoding")?;
    }
    let loaded = ProfileMachine::from_source(profile, &source, vec![])
        .map_err(|error| error.to_string())?;
    let base = loaded.memory();
    let baseline = actual_path(base, vec![3, 4, 5])?;
    assert_eq!(baseline.read_sites, [
        (53, TraceInput::Byte(3)),
        (63, TraceInput::Byte(4)),
        (101, TraceInput::Byte(5)),
    ]);
    assert!(!baseline.halted);
    assert_eq!(baseline.output, [3, 154]);

    // Exhaust all loader-valid instruction encodings at C102..C114.
    // Only the final two source bytes seed high-memory expansion; these
    // edits leave it fixed. Patching the loaded source word is therefore
    // equivalent to reloading the same candidate, and avoids 104 complete
    // 15-trit memory expansions inside this bounded VM enumeration.
    let mut tried = 0usize;
    let mut halted_three_reads = Vec::new();
    let mut accepted = Vec::new();
    for position in 102..=114u32 {
        for byte in 33..=126u8 {
            let Some(first) =
                decode_profile_instruction(u32::from(byte), position)
            else {
                continue;
            };
            if !b"oijp*/<v".contains(&first) {
                continue;
            }
            let mut memory = base.to_vec();
            memory[usize::try_from(position)
                .map_err(|error| error.to_string())?] = u32::from(byte);
            tried += 1;
            let path = actual_path(&memory, vec![3, 4, 5])?;
            if path.halted && path.consumed == 3 {
                halted_three_reads.push((position, byte, path.output.clone()));
            }
            if !path.halted
                || path.output != [3, 154, 5]
                || path.read_sites
                    != [
                        (53, TraceInput::Byte(3)),
                        (63, TraceInput::Byte(4)),
                        (101, TraceInput::Byte(5)),
                    ]
            {
                continue;
            }
            let eof = actual_path(&memory, vec![3])?;
            if eof.halted
                && eof.output == [3, 30]
                && eof.consumed == 1
                && eof.read_sites
                    == [(53, TraceInput::Byte(3)), (63, TraceInput::EndOfInput)]
            {
                accepted.push((position, byte));
            }
        }
    }
    assert_eq!(tried, 104);
    // These are the two deceptively halted candidates. The first fails
    // to output byte three; the second omits the second-byte marker.
    assert_eq!(halted_three_reads, [
        (104, 123, vec![3, 154]),
        (114, 97, vec![3, 5])
    ]);
    assert!(accepted.is_empty(), "a legitimate echo needs guest proof");
    Ok(())
}
