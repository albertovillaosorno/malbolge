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
//   - Actual N15 EOF-flag to code-jump counterexamples.
// - Must-Not:
//   - Claim a failed physical jump is C23 branch compilation.
// - Allows:
//   - Inputs: the pinned 33-cell EOF-flag guest and a bounded source extension.
//   - Outputs: real VM trace, target refusal and state-invariance evidence.
//   - Side effects: isolated normative VM execution only.
// - Split-When:
//   - An actual EOF-dependent source-linked code branch replaces these probes.
// - Merge-When:
//   - Verified layout control transfer owns phase and mutation obligations.
// - Summary:
//   - Checks that an EOF flag does not license a guessed physical `i` branch.

//! Bounded negative evidence for direct control transfer after the real EOF
//! flag.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use malbolge::{
    ProfileMachine, ProfileMachineError, ProfileRegisters, RunOutcome,
    Termination, current_profile, decode_profile_instruction,
};

fn graphical_opcode(position: usize, opcode: u8) -> Result<u8, String> {
    let code_address =
        u32::try_from(position).map_err(|error| error.to_string())?;
    (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), code_address)
                == Some(opcode)
        })
        .ok_or_else(|| format!("no graphical {opcode} at {position}"))
}

fn direct_jump_probe() -> Result<Vec<u8>, String> {
    let plan =
        layout::build_guest_byte_c32_pair_eof_flag_source(current_profile())
            .map_err(|error| format!("{error:?}"))?;
    let mut source = plan.pair.source;
    for (position, opcode) in [(27, b'j'), (28, b'i'), (29, b'v')] {
        let Some(cell) = source.get_mut(position) else {
            return Err(String::from("missing continuation source cell"));
        };
        *cell = graphical_opcode(position, opcode)?;
    }
    Ok(source)
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "independent two-stream physical control refusal witness"
)]
fn direct_jump_after_real_eof_flag_fails_both_control_arms()
-> Result<(), String> {
    let profile = current_profile();
    let source = direct_jump_probe()?;
    for (input, flag) in [(vec![], 15), (vec![0], 0), (vec![0xff], 0)] {
        let mut machine =
            ProfileMachine::from_source(profile, &source, input.clone())
                .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = machine.run_traced(31, &mut |step| trace.push(*step));
        assert_eq!(trace[26].decoded, Some(b'p'));
        assert_eq!(trace[26].after.registers.accumulator, flag);
        assert_eq!(trace[27].decoded, Some(b'j'));
        assert_eq!(trace[28].decoded, Some(b'i'));
        assert_eq!(machine.input_consumed(), input.len());
        assert!(machine.output().is_empty());
        if input.is_empty() {
            assert_eq!(
                outcome.map_err(|error| error.to_string())?,
                RunOutcome::Terminated {
                    reason: Termination::NonGraphicalCell,
                    steps: 30,
                },
            );
            assert_eq!(
                trace[27].memory_reads.data.map(|read| read.value),
                Some(103)
            );
            assert_eq!(
                trace[28].memory_reads.data.map(|read| read.value),
                Some(36)
            );
            assert_eq!(trace[29].before.registers.code_pointer, 37);
            assert_eq!(trace[29].decoded, None);
        } else if input == [0xff] {
            assert_eq!(
                outcome.map_err(|error| error.to_string())?,
                RunOutcome::Terminated {
                    reason: Termination::NonGraphicalCell,
                    steps: 30,
                },
            );
            assert_eq!(trace[29].before.registers.code_pointer, 7_174_369);
            assert_eq!(trace[29].decoded, None);
            assert_eq!(
                trace[27].memory_reads.data.map(|read| read.value),
                Some(7_174_417),
            );
            assert_eq!(
                trace[28].memory_reads.data.map(|read| read.value),
                Some(7_174_368),
            );
        } else {
            assert_eq!(
                outcome,
                Err(ProfileMachineError::InvalidEncryptionTarget {
                    pointer: 7_174_417,
                    value: 7_174_417,
                }),
            );
            assert_eq!(
                trace[27].memory_reads.data.map(|read| read.value),
                Some(36)
            );
            assert_eq!(
                trace[28].memory_reads.data.map(|read| read.value),
                Some(7_174_417)
            );
        }
    }
    Ok(())
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "bounded physical loader-extension state alias counterexample"
)]
fn six_phase_tail_relocation_does_not_preserve_early_flag_state()
-> Result<(), String> {
    let profile = current_profile();
    let original = direct_jump_probe()?;
    // +30 source cells preserves the modulo-six *post-source* loader phase.
    // It does not preserve memory at 33..62: those cells become code rather
    // than the original expanded words, and the live flag path reads them.
    let mut extended = original[..31].to_vec();
    for position in 31..61 {
        extended.push(graphical_opcode(position, b'o')?);
    }
    extended.extend_from_slice(&original[31..]);
    assert_eq!(extended.len(), 63);
    assert_eq!(&extended[61..], &original[31..]);
    for (position, opcode) in
        [(27, b'j'), (28, b'i'), (37, b'v'), (45, b'<'), (46, b'v')]
    {
        extended[position] = graphical_opcode(position, opcode)?;
    }
    let original_loaded =
        ProfileMachine::from_source(profile, &original, vec![])
            .map_err(|error| error.to_string())?;
    let extended_loaded =
        ProfileMachine::from_source(profile, &extended, vec![])
            .map_err(|error| error.to_string())?;
    // The 6-cycle phase really is unchanged at untouched loader locations.
    assert_eq!(
        original_loaded.memory_word(126),
        extended_loaded.memory_word(126)
    );
    for input in [vec![], vec![0], vec![0xff]] {
        let mut original_machine = ProfileMachine::from_state(
            profile,
            original_loaded.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut extended_machine = ProfileMachine::from_state(
            profile,
            extended_loaded.memory().to_vec(),
            input,
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut original_trace = Vec::new();
        let mut extended_trace = Vec::new();
        assert_eq!(
            original_machine
                .run_traced(27, &mut |step| original_trace.push(*step))
                .map_err(|error| error.to_string())?,
            RunOutcome::BudgetExhausted { steps: 27 },
        );
        assert_eq!(
            extended_machine
                .run_traced(27, &mut |step| extended_trace.push(*step))
                .map_err(|error| error.to_string())?,
            RunOutcome::BudgetExhausted { steps: 27 },
        );
        assert_eq!(original_trace[26].decoded, Some(b'p'));
        assert_eq!(extended_trace[26].decoded, Some(b'p'));
        assert_ne!(
            original_trace[26].after.registers,
            extended_trace[26].after.registers
        );
    }
    Ok(())
}
