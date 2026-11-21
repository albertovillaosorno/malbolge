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
//   - Actual N15 code-site phase replay for fetched and jump-encrypted cells.
// - Must-Not:
//   - Claim a reusable source-C loop, state restoration or checksum linkage.
// - Allows:
//   - Inputs: one frozen 120-cell graphical source, four live guest reads.
//   - Outputs: checked XLAT2 visit phases, off-site encryption and refusals.
//   - Side effects: bounded normative guest VM execution only.
// - Split-When:
//   - Full physical CFG code/data linking subsumes per-cell phase witnesses.
// - Merge-When:
//   - The compiler backend verifies complete source-linked mutation schedules.
// - Summary:
//   - Repeated i is stable while its jump targets independently self-modify.

//! Source-loaded code-phase checks against the guest VM's real memory effects.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use layout::{
    CodeCellEvent, CodeCellScheduleError, CodeVisitRequirement,
    admit_code_cell_schedule, encode_code_cell_schedule,
};
use malbolge::{
    ProfileMachine, RunOutcome, TraceInput, current_profile,
    decode_profile_instruction, encrypt_profile_cell, historical_profile,
};

const SOURCE: &[u8] =
    include_bytes!("compiler/fixtures/same-site-four-read.malbolge");
const STEP_BUDGET: usize = 83;

fn is_operation(byte: u8) -> bool {
    b"oijp*/<v".contains(&byte)
}

fn site_events(
    site: u32,
    trace: &[malbolge::ProfileStepTrace],
) -> Vec<CodeCellEvent> {
    let mut events = Vec::new();
    for step in trace {
        let fetched_site = step.before.registers.code_pointer == site;
        if fetched_site {
            let requirement = match step.decoded {
                Some(opcode) if is_operation(opcode) => {
                    CodeVisitRequirement::Decoded(opcode)
                },
                _ => CodeVisitRequirement::Inert,
            };
            events.push(CodeCellEvent::Fetch(requirement));
        }
        // `i` encrypts its target, not its fetched instruction. Every other
        // successful non-halt instruction self-encrypts its fetched cell.
        if step
            .memory_delta
            .encryption
            .is_some_and(|word| word.address == site)
            && (!fetched_site || step.decoded == Some(b'i'))
        {
            events.push(CodeCellEvent::JumpTargetEncryption);
        }
    }
    events
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "one physical four-read source with exact ordered XLAT2 effects"
)]
fn real_guest_fetch_and_jump_target_phases_match_source_bytes()
-> Result<(), String> {
    let profile = current_profile();
    assert_eq!(SOURCE.len(), 120);
    for input in [vec![], vec![0], vec![0xff], vec![1, 2, 3, 4, 5], vec![
        0x80, 0, 0, 0xff,
    ]] {
        let mut vm =
            ProfileMachine::from_source(profile, SOURCE, input.clone())
                .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = vm
            .run_traced(STEP_BUDGET, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::BudgetExhausted { steps: STEP_BUDGET });
        assert_eq!(trace.len(), STEP_BUDGET);
        let inputs = trace
            .iter()
            .filter_map(|step| step.input)
            .collect::<Vec<_>>();
        let expected_inputs = (0..4)
            .map(|index| {
                input
                    .get(index)
                    .copied()
                    .map_or(TraceInput::EndOfInput, TraceInput::Byte)
            })
            .collect::<Vec<_>>();
        assert_eq!(inputs, expected_inputs);
        assert_eq!(vm.input_consumed(), input.len().min(4));

        // C47 is physically revisited seven times; only four phases are `/`.
        // C49 executes `i` repeatedly but never self-encrypts its code byte.
        // C43 is fetched before later `i` instructions encrypt it off-site.
        for (site, expected_fetches, min_jumps) in
            [(47u32, 7usize, 0usize), (49, 7, 0), (43, 1, 1), (46, 5, 0)]
        {
            let events = site_events(site, &trace);
            let initial = *SOURCE
                .get(usize::try_from(site).map_err(|error| error.to_string())?)
                .ok_or("missing source code site")?;
            let schedule =
                admit_code_cell_schedule(profile, site, initial, &events)
                    .map_err(|error| format!("C{site}: {error:?}"))?;
            let proposed = encode_code_cell_schedule(profile, site, &events)
                .map_err(|error| format!("C{site} encoding: {error:?}"))?;
            assert_eq!(proposed.initial, initial);
            assert_eq!(schedule, proposed);
            assert_eq!(schedule.fetches, expected_fetches);
            assert!(schedule.target_encryptions >= min_jumps);
            assert_eq!(
                u32::from(schedule.final_cell),
                vm.memory_word(site).map_err(|error| error.to_string())?,
                "wrong final XLAT2 word at M{site}"
            );
        }
        let jump_events = site_events(49, &trace);
        assert_eq!(
            jump_events,
            [CodeCellEvent::Fetch(CodeVisitRequirement::Decoded(b'i'),); 7]
        );
        assert_eq!(
            vm.memory_word(49),
            Ok(u32::from(*SOURCE.get(49).ok_or("missing C49 source byte")?))
        );
        let input_events = site_events(47, &trace);
        assert_eq!(
            input_events
                .iter()
                .filter(|event| matches!(
                    event,
                    CodeCellEvent::Fetch(CodeVisitRequirement::Decoded(b'/'))
                ))
                .count(),
            4
        );
        let target_events = site_events(43, &trace);
        assert!(target_events.iter().any(|event| {
            matches!(event, CodeCellEvent::JumpTargetEncryption)
        }));
        // Omitting an off-site encryption cannot prove the actual live word.
        let mut forged = target_events;
        let missing = forged
            .iter()
            .position(|event| *event == CodeCellEvent::JumpTargetEncryption)
            .ok_or("missing real jump-target encryption")?;
        let _removed = forged.remove(missing);
        let bad_schedule = admit_code_cell_schedule(
            profile,
            43,
            *SOURCE.get(43).ok_or("missing C43 source byte")?,
            &forged,
        )
        .map_err(|error| format!("forged C43 schedule: {error:?}"))?;
        assert_ne!(
            u32::from(bad_schedule.final_cell),
            vm.memory_word(43).map_err(|error| error.to_string())?,
        );
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "exhaustive opcode phase checks"
)]
fn unchanged_i_site_and_aliased_jump_encryption_have_distinct_schedules()
-> Result<(), String> {
    for profile in [current_profile(), historical_profile()] {
        for address in 0..94u32 {
            let repeated_i =
                [CodeCellEvent::Fetch(CodeVisitRequirement::Decoded(b'i')); 3];
            let encoded =
                encode_code_cell_schedule(profile, address, &repeated_i)
                    .map_err(|error| format!("C{address}: {error:?}"))?;
            assert_eq!(encoded.fetches, 3);
            assert_eq!(encoded.target_encryptions, 0);
            assert_eq!(u32::from(encoded.initial), encoded.final_cell);
            assert_eq!(
                decode_profile_instruction(u32::from(encoded.initial), address),
                Some(b'i')
            );
            let target_encrypted = [
                CodeCellEvent::Fetch(CodeVisitRequirement::Decoded(b'i')),
                CodeCellEvent::JumpTargetEncryption,
            ];
            let affected = admit_code_cell_schedule(
                profile,
                address,
                encoded.initial,
                &target_encrypted,
            )
            .map_err(|error| format!("C{address} aliased i: {error:?}"))?;
            assert_eq!(
                Some(u32::from(affected.final_cell)),
                encrypt_profile_cell(u32::from(encoded.initial)),
            );
        }
    }
    Ok(())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::panic_in_result_fn,
    reason = "exhaustive positional decoder and XLAT2 orbit census"
)]
fn same_site_input_revisit_requires_a_non_input_intermediate_phase()
-> Result<(), String> {
    use CodeCellEvent::Fetch;
    use CodeVisitRequirement::{Decoded, Inert};
    let profile = current_profile();
    let mut site_periods = Vec::new();
    for site in 0..94u32 {
        let first =
            encode_code_cell_schedule(profile, site, &[Fetch(Decoded(b'/'))])
                .map_err(|error| format!("C{site}: {error:?}"))?;
        assert_eq!(
            decode_profile_instruction(u32::from(first.initial), site),
            Some(b'/'),
        );
        assert_eq!(
            encode_code_cell_schedule(profile, site, &[
                Fetch(Decoded(b'/')),
                Fetch(Decoded(b'/')),
            ]),
            Err(CodeCellScheduleError::NoEncoding),
            "no direct consecutive / is possible without a code write",
        );
        let mut word = u32::from(first.initial);
        let mut first_return_period = None;
        for turn in 1..=68usize {
            word = encrypt_profile_cell(word).ok_or("missing XLAT2 cycle")?;
            if decode_profile_instruction(word, site) == Some(b'/') {
                first_return_period = Some(turn);
                break;
            }
        }
        let period =
            first_return_period.ok_or("missing input site recurrence")?;
        if period == 2 {
            let alternation = encode_code_cell_schedule(profile, site, &[
                Fetch(Decoded(b'/')),
                Fetch(Inert),
                Fetch(Decoded(b'/')),
            ])
            .map_err(|error| format!("C{site} alternating: {error:?}"))?;
            assert_eq!(alternation.initial, first.initial);
            assert!(matches!((site, first.initial), (43, 74) | (47, 70)));
        }
        site_periods.push((site, period));
    }
    for (period, expected_count) in
        [(2, 2), (4, 4), (5, 5), (6, 6), (9, 9), (68, 68)]
    {
        assert_eq!(
            site_periods
                .iter()
                .filter(|entry| entry.1 == period)
                .count(),
            expected_count,
            "source-loaded input encoding orbit census for length {period}",
        );
    }
    Ok(())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "explicit phase-schedule refusal matrix"
)]
fn malformed_phase_schedules_fail_closed() {
    use CodeCellEvent::{Fetch, JumpTargetEncryption};
    use CodeVisitRequirement::{Decoded, Inert};
    let profile = current_profile();
    let address = 47;
    let source_byte = SOURCE.get(47).copied().unwrap_or_default();
    assert_eq!(
        admit_code_cell_schedule(profile, address, source_byte, &[]),
        Err(CodeCellScheduleError::Empty),
    );
    assert_eq!(
        admit_code_cell_schedule(profile, address, 32, &[Fetch(Decoded(b'/'))]),
        Err(CodeCellScheduleError::InvalidSourceCell),
    );
    assert_eq!(
        admit_code_cell_schedule(
            profile,
            profile.memory_words(),
            source_byte,
            &[Fetch(Decoded(b'/'))]
        ),
        Err(CodeCellScheduleError::AddressOutOfBounds),
    );
    assert_eq!(
        admit_code_cell_schedule(profile, address, source_byte, &[
            JumpTargetEncryption,
            Fetch(Decoded(b'/'))
        ]),
        Err(CodeCellScheduleError::InvalidFirstEvent),
    );
    assert_eq!(
        admit_code_cell_schedule(profile, address, source_byte, &[Fetch(
            Inert
        )]),
        Err(CodeCellScheduleError::InvalidFirstEvent),
    );
    assert_eq!(
        admit_code_cell_schedule(
            profile,
            address,
            source_byte,
            &[Fetch(Decoded(b'/')); 65]
        ),
        Err(CodeCellScheduleError::TooMany),
    );
    assert_eq!(
        admit_code_cell_schedule(profile, address, source_byte, &[
            Fetch(Decoded(b'/')),
            Fetch(Decoded(b'/')),
        ]),
        Err(CodeCellScheduleError::DecodeMismatch { event: 1 }),
    );
    assert_eq!(
        encode_code_cell_schedule(profile, address, &[
            Fetch(Decoded(b'/')),
            Fetch(Decoded(b'/')),
        ]),
        Err(CodeCellScheduleError::NoEncoding),
    );
    let halt = encode_code_cell_schedule(profile, 41, &[Fetch(Decoded(b'v'))]);
    assert!(halt.is_ok());
    assert_eq!(
        encode_code_cell_schedule(profile, 41, &[
            Fetch(Decoded(b'v')),
            JumpTargetEncryption
        ]),
        Err(CodeCellScheduleError::EventsAfterHalt { event: 0 }),
    );
}
