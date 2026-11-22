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
    ProfileMachine, RunOutcome, Termination, TraceInput, current_profile,
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
    let unadmitted = (33u8..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), address)
                .is_some_and(|op| !b"oijp*/<v".contains(&op))
        })
        .unwrap_or_default();
    assert!((33..=126).contains(&unadmitted));
    assert_eq!(
        admit_code_cell_schedule(profile, address, unadmitted, &[
            JumpTargetEncryption,
        ]),
        Err(CodeCellScheduleError::InvalidFirstEvent),
    );
    assert_eq!(
        admit_code_cell_schedule(profile, address, source_byte, &[
            JumpTargetEncryption,
            Fetch(Decoded(b'/'))
        ]),
        Err(CodeCellScheduleError::DecodeMismatch { event: 1 }),
    );
    assert_eq!(
        admit_code_cell_schedule(profile, address, source_byte, &[Fetch(
            Inert
        )]),
        Err(CodeCellScheduleError::DecodeMismatch { event: 0 }),
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

// A real reached i can encrypt a *future* graphical cell without fetching it:
// the target is XLAT2-mutated before its first prospective code execution.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "physical N15 jump-target encryption and forged effect chronology"
)]
fn first_event_jump_target_encryption_matches_source_loaded_guest()
-> Result<(), String> {
    use CodeCellEvent::JumpTargetEncryption;
    let profile = current_profile();
    let encoded = |position: usize, opcode: u8| -> Result<u8, String> {
        let address =
            u32::try_from(position).map_err(|error| error.to_string())?;
        (33u8..=126u8)
            .find(|byte| {
                decode_profile_instruction(u32::from(*byte), address)
                    == Some(opcode)
            })
            .ok_or_else(|| format!("no {opcode} at C{position}"))
    };
    let first_jump = encoded(0, b'i')?;
    let target = usize::from(first_jump);
    let mut source = (0..=target + 1)
        .map(|site| encoded(site, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    *source.get_mut(0).ok_or("missing first i")? = first_jump;
    *source.get_mut(target + 1).ok_or("missing halt")? =
        encoded(target + 1, b'v')?;
    let mut guest = ProfileMachine::from_source(profile, &source, vec![])
        .map_err(|error| error.to_string())?;
    let mut trace = Vec::new();
    let outcome = guest
        .run_traced(2, &mut |step| trace.push(*step))
        .map_err(|error| error.to_string())?;
    assert_eq!(outcome, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: 2,
    });
    let jump = trace.first().ok_or("missing physical jump")?;
    let halt = trace.get(1).ok_or("missing physical halt")?;
    assert_eq!(jump.decoded, Some(b'i'));
    assert_eq!(halt.decoded, Some(b'v'));
    let effect = jump.memory_delta.encryption.ok_or("missing XLAT2")?;
    assert_eq!(effect.address, u32::from(first_jump));
    let target_source_byte = *source.get(target).ok_or("missing target")?;
    assert_eq!(effect.before, u32::from(target_source_byte));
    assert_eq!(
        effect.after,
        guest
            .memory_word(effect.address)
            .map_err(|error| error.to_string())?
    );
    let schedule = admit_code_cell_schedule(
        profile,
        effect.address,
        target_source_byte,
        &[JumpTargetEncryption],
    )
    .map_err(|error| format!("off-site first XLAT2 refused: {error:?}"))?;
    assert_eq!(schedule.final_cell, effect.after);
    assert_eq!(schedule.target_encryptions, 1);
    assert_eq!(schedule.fetches, 0);
    let proposed = encode_code_cell_schedule(profile, effect.address, &[
        JumpTargetEncryption,
    ])
    .map_err(|error| format!("XLAT2 phase encoding refused: {error:?}"))?;
    assert_eq!(proposed.target_encryptions, 1);
    assert_eq!(
        proposed.final_cell,
        encrypt_profile_cell(u32::from(proposed.initial)).ok_or("XLAT2")?,
    );
    assert_eq!(
        admit_code_cell_schedule(
            profile,
            effect.address,
            target_source_byte,
            &[JumpTargetEncryption, CodeCellEvent::DataWrite {
                before: effect.before,
                after: effect.before,
            },]
        ),
        Err(CodeCellScheduleError::DataWriteMismatch { event: 1 }),
    );
    Ok(())
}

// A source-valid o is inert from the first fetch. The source loader admits
// this nop, and the VM executes it before the following halt.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "normative N15 first-fetch no-op and exact XLAT2 trace"
)]
fn first_event_inert_fetch_matches_real_guest_noop() -> Result<(), String> {
    let profile = current_profile();
    let encoded = |site: u32, opcode: u8| {
        (33u8..=126u8)
            .find(|candidate| {
                decode_profile_instruction(u32::from(*candidate), site)
                    == Some(opcode)
            })
            .ok_or("no valid graphical source instruction")
    };
    let source = [encoded(0, b'o')?, encoded(1, b'v')?];
    let mut guest = ProfileMachine::from_source(profile, &source, vec![])
        .map_err(|error| error.to_string())?;
    let mut trace = Vec::new();
    let outcome = guest
        .run_traced(2, &mut |step| trace.push(*step))
        .map_err(|error| error.to_string())?;
    assert_eq!(outcome, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: 2,
    });
    assert_eq!(trace.first().ok_or("missing nop")?.decoded, Some(b'o'));
    assert_eq!(trace.get(1).ok_or("missing halt")?.decoded, Some(b'v'));
    let inert = [CodeCellEvent::Fetch(CodeVisitRequirement::Inert)];
    let checked = admit_code_cell_schedule(profile, 0, source[0], &inert)
        .map_err(|error| format!("first nop refused: {error:?}"))?;
    assert_eq!(checked.fetches, 1);
    assert_eq!(
        checked.final_cell,
        guest.memory_word(0).map_err(|error| error.to_string())?
    );
    assert_eq!(encode_code_cell_schedule(profile, 0, &inert), Ok(checked),);
    assert_eq!(
        admit_code_cell_schedule(profile, 0, source[0], &[
            CodeCellEvent::Fetch(CodeVisitRequirement::Decoded(b'/')),
        ]),
        Err(CodeCellScheduleError::DecodeMismatch { event: 0 }),
    );
    Ok(())
}

// The off-site-first source rule is positional and applies to both ten- and
// fifteen-trit profile loaders, not only the physical C0 jump witness.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "94 positional source admission phases in two profile loaders"
)]
fn first_effect_admission_matches_both_profile_loaders_at_all_phases()
-> Result<(), String> {
    use CodeCellEvent::{Fetch, JumpTargetEncryption};
    let mut checked = 0usize;
    for profile in [current_profile(), historical_profile()] {
        for site in 0..94u32 {
            let original = (33u8..=126u8)
                .find(|byte| {
                    decode_profile_instruction(u32::from(*byte), site)
                        == Some(b'o')
                })
                .ok_or("missing source-valid nop")?;
            let xlat2 = admit_code_cell_schedule(profile, site, original, &[
                JumpTargetEncryption,
            ])
            .map_err(|error| format!("C{site} off-site first: {error:?}"))?;
            assert_eq!(
                Some(xlat2.final_cell),
                encrypt_profile_cell(u32::from(original)),
            );
            assert_eq!((xlat2.fetches, xlat2.target_encryptions), (0, 1));
            let inert =
                admit_code_cell_schedule(profile, site, original, &[Fetch(
                    CodeVisitRequirement::Inert,
                )])
                .map_err(|error| format!("C{site} inert first: {error:?}"))?;
            assert_eq!((inert.fetches, inert.target_encryptions), (1, 0));
            assert_eq!(inert.final_cell, xlat2.final_cell);
            let forbidden = (33u8..=126u8)
                .find(|byte| {
                    decode_profile_instruction(u32::from(*byte), site)
                        .is_some_and(|op| !b"oijp*/<v".contains(&op))
                })
                .ok_or("missing forbidden graphical source")?;
            assert_eq!(
                admit_code_cell_schedule(profile, site, forbidden, &[
                    JumpTargetEncryption
                ],),
                Err(CodeCellScheduleError::InvalidFirstEvent),
            );
            checked = checked.saturating_add(1);
        }
    }
    assert_eq!(checked, 188);
    Ok(())
}
