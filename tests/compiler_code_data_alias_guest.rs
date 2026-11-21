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
//   - Source-loaded physical alias of a data-write target with a code cell.
// - Must-Not:
//   - Claim a source-C loop, arithmetic translator or executable checksum.
// - Allows:
//   - Inputs: one bounded current-N15 graphical program and real data writes.
//   - Outputs: exact VM-backed pre-fetch code mutation and refusal evidence.
//   - Side effects: isolated normative guest execution only.
// - Split-When:
//   - Source-locked physical CFG verification subsumes code/data alias checks.
// - Merge-When:
//   - The full physical compiler linker verifies code-cell data-write epochs.
// - Summary:
//   - A reached guest data operation can mutate source code before any fetch.

//! A real source-loaded code/data alias missing from fetch-only phase planners.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use malbolge::{
    ProfileMachine, RunOutcome, Termination, current_profile,
    decode_profile_instruction,
};

const ALIAS_ADDRESS: u32 = 41;
const DYNAMIC_INPUT_ADDRESS: u32 = 79;
const DYNAMIC_INPUT_LENGTH: usize = 81;
const DYNAMIC_INPUT_SOURCE: &[u8] =
    include_bytes!("compiler/fixtures/code-data-alias-dynamic-input.malbolge");

const SOURCE_LENGTH: usize = 43;

fn encoded(site: usize, opcode: u8) -> Result<u8, String> {
    let position = u32::try_from(site).map_err(|error| error.to_string())?;
    (33..=126u8)
        .find(|candidate| {
            decode_profile_instruction(u32::from(*candidate), position)
                == Some(opcode)
        })
        .ok_or_else(|| format!("unencodable operation {opcode} at C{site}"))
}

#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "exact 43-cell source with fixed in-bounds mutation sites"
)]
fn aliased_code_source(opcode: u8) -> Result<Vec<u8>, String> {
    let mut source = (0..SOURCE_LENGTH)
        .map(|site| encoded(site, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    source[0] = encoded(0, b'j')?;
    source[1] = encoded(1, opcode)?;
    source[2] = encoded(2, b'v')?;
    source[41] = encoded(41, b'i')?;
    // A reached j at C0 sets D to M0+1, which is 41 for its C0 source byte.
    assert_eq!(u32::from(source[0]) + 1, ALIAS_ADDRESS);
    Ok(source)
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::indexing_slicing,
    clippy::cognitive_complexity,
    reason = "bounded normative guest trace assertions"
)]
fn physical_data_write_changes_unfetched_graphical_code_cell()
-> Result<(), String> {
    for opcode in *b"*p" {
        let source = aliased_code_source(opcode)?;
        let mut vm =
            ProfileMachine::from_source(current_profile(), &source, Vec::new())
                .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let result = vm
            .run_traced(3, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(result, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 3,
        });
        assert_eq!(trace.len(), 3);
        assert_eq!(trace[0].decoded, Some(b'j'));
        assert_eq!(trace[1].decoded, Some(opcode));
        assert_eq!(trace[2].decoded, Some(b'v'));
        assert_eq!(trace[1].before.registers.data_pointer, ALIAS_ADDRESS);
        let data = trace[1].memory_delta.data.ok_or("missing data write")?;
        assert_eq!(data.address, ALIAS_ADDRESS);
        assert_eq!(data.before, u32::from(source[41]));
        assert_ne!(data.after, data.before);
        assert_eq!(vm.memory_word(ALIAS_ADDRESS), Ok(data.after));
        assert_eq!(
            trace[1].memory_delta.encryption.map(|write| write.address),
            Some(1),
            "a data write and fetched-cell XLAT2 must be distinct effects",
        );
        assert!(trace.iter().all(|step| {
            step.before.registers.code_pointer != ALIAS_ADDRESS
        }));
        assert!(
            !(33..=126).contains(&data.after),
            "this alias leaves non-graphical code",
        );
    }
    Ok(())
}

#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::integer_division,
    clippy::integer_division_remainder_used,
    reason = "checked source fixture and independent exact rotate arithmetic"
)]
fn source_with_data_written_input_opcode() -> Result<Vec<u8>, String> {
    let source = DYNAMIC_INPUT_SOURCE.to_vec();
    assert_eq!(source.len(), DYNAMIC_INPUT_LENGTH);
    for (site, instruction) in [(56, b'j'), (57, b'*'), (79, b'<'), (80, b'v')]
    {
        assert_eq!(
            decode_profile_instruction(
                u32::from(source[site]),
                u32::try_from(site).map_err(|error| error.to_string())?,
            ),
            Some(instruction),
        );
    }
    // C56's j reads its own original 78 and moves D to M56+1=79.
    assert_eq!(source[56], 78);
    assert_eq!(source[79], 114);
    // A real C57 rotate changes 114 to 38, decoding as '/' at C79.
    assert_eq!(u32::from(source[79]) / 3, 38);
    assert_eq!(
        decode_profile_instruction(38, DYNAMIC_INPUT_ADDRESS),
        Some(b'/')
    );
    Ok(source)
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    clippy::indexing_slicing,
    reason = "four real guest streams and exact dynamic opcode writes"
)]
fn physical_data_write_creates_a_reached_input_opcode_before_first_fetch()
-> Result<(), String> {
    let source = source_with_data_written_input_opcode()?;
    assert_eq!(
        decode_profile_instruction(u32::from(source[79]), 79),
        Some(b'<')
    );
    for input in [vec![], vec![0], vec![0xff], vec![0, 0xff]] {
        let mut vm = ProfileMachine::from_source(
            current_profile(),
            &source,
            input.clone(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let result = vm
            .run_traced(DYNAMIC_INPUT_LENGTH, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(result, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: DYNAMIC_INPUT_LENGTH,
        });
        assert_eq!(trace.len(), DYNAMIC_INPUT_LENGTH);
        assert_eq!(trace[56].decoded, Some(b'j'));
        assert_eq!(trace[57].decoded, Some(b'*'));
        assert_eq!(
            trace[57].before.registers.data_pointer,
            DYNAMIC_INPUT_ADDRESS
        );
        let write = trace[57]
            .memory_delta
            .data
            .ok_or("missing source code write")?;
        assert_eq!((write.address, write.before, write.after), (79, 114, 38));
        assert!(trace.iter().take(79).all(|step| {
            step.before.registers.code_pointer != DYNAMIC_INPUT_ADDRESS
        }));
        let expected_input = input.first().copied().map_or(
            malbolge::TraceInput::EndOfInput,
            malbolge::TraceInput::Byte,
        );
        assert_eq!(
            trace[79].before.registers.code_pointer,
            DYNAMIC_INPUT_ADDRESS
        );
        assert_eq!(trace[79].fetched_cell, Some(38));
        assert_eq!(trace[79].decoded, Some(b'/'));
        assert_eq!(trace[79].input, Some(expected_input));
        assert_eq!(vm.input_consumed(), input.len().min(1));
        assert_eq!(trace[80].decoded, Some(b'v'));
        assert_eq!(vm.output(), &[]);
        assert_eq!(
            vm.memory_word(DYNAMIC_INPUT_ADDRESS),
            Ok(malbolge::encrypt_profile_cell(38).ok_or("invalid XLAT2")?),
        );
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::indexing_slicing,
    reason = "one exact altered-source causal guest control"
)]
fn removing_the_guest_data_write_executes_original_output_instead_of_input()
-> Result<(), String> {
    let mut source = source_with_data_written_input_opcode()?;
    source[57] = encoded(57, b'o')?;
    let mut vm =
        ProfileMachine::from_source(current_profile(), &source, vec![0x5a])
            .map_err(|error| error.to_string())?;
    let mut trace = Vec::new();
    let result = vm
        .run_traced(DYNAMIC_INPUT_LENGTH, &mut |step| trace.push(*step))
        .map_err(|error| error.to_string())?;
    assert_eq!(result, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: DYNAMIC_INPUT_LENGTH,
    });
    assert_eq!(trace[57].decoded, Some(b'o'));
    assert!(trace[57].memory_delta.data.is_none());
    assert_eq!(trace[79].fetched_cell, Some(114));
    assert_eq!(trace[79].decoded, Some(b'<'));
    assert_eq!(trace[79].input, None);
    assert_eq!(trace[79].output, Some(0));
    assert_eq!(vm.output(), &[0]);
    assert_eq!(vm.input_consumed(), 0);
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    reason = "physical alias phase checks and explicit forged-effect refusals"
)]
fn code_cell_planner_admits_real_prefetch_data_write_and_refuses_forgery()
-> Result<(), String> {
    use layout::{
        CodeCellEvent, CodeCellScheduleError, CodeVisitRequirement,
        admit_code_cell_schedule, encode_code_cell_schedule,
    };
    let profile = current_profile();
    let events = [
        CodeCellEvent::DataWrite { before: 114, after: 38 },
        CodeCellEvent::Fetch(CodeVisitRequirement::Decoded(b'/')),
    ];
    let checked = admit_code_cell_schedule(profile, 79, 114, &events)
        .map_err(|error| format!("real guest alias refused: {error:?}"))?;
    assert_eq!(checked.initial, 114);
    assert_eq!(checked.fetches, 1);
    assert_eq!(checked.data_writes, 1);
    assert_eq!(checked.target_encryptions, 0);
    assert_eq!(
        checked.final_cell,
        malbolge::encrypt_profile_cell(38).ok_or("XLAT2")?
    );
    assert_eq!(encode_code_cell_schedule(profile, 79, &events), Ok(checked),);

    let invalid_before = [
        CodeCellEvent::DataWrite { before: 113, after: 38 },
        events[1],
    ];
    assert_eq!(
        admit_code_cell_schedule(profile, 79, 114, &invalid_before),
        Err(CodeCellScheduleError::DataWriteMismatch { event: 0 }),
    );
    let invalid_word = [CodeCellEvent::DataWrite {
        before: 114,
        after: profile.memory_words(),
    }];
    assert_eq!(
        admit_code_cell_schedule(profile, 79, 114, &invalid_word),
        Err(CodeCellScheduleError::InvalidDataWord { event: 0 }),
    );
    let ungraphical = CodeCellEvent::DataWrite { before: 114, after: 19 };
    assert_eq!(
        admit_code_cell_schedule(profile, 79, 114, &[
            ungraphical,
            CodeCellEvent::Fetch(CodeVisitRequirement::Decoded(b'/')),
        ]),
        Err(CodeCellScheduleError::DecodeMismatch { event: 1 }),
    );
    assert_eq!(
        admit_code_cell_schedule(profile, 79, 114, &[
            ungraphical,
            CodeCellEvent::JumpTargetEncryption,
        ]),
        Err(CodeCellScheduleError::InvalidEncryptionTarget { event: 1 }),
    );
    let non_graphical_final =
        admit_code_cell_schedule(profile, 79, 114, &[ungraphical]).map_err(
            |error| format!("valid terminal data-write refused: {error:?}"),
        )?;
    assert_eq!(non_graphical_final.final_cell, 19);
    assert_eq!(non_graphical_final.fetches, 0);
    assert_eq!(non_graphical_final.data_writes, 1);
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::excessive_nesting,
    reason = "all 81 source cells and their real chronological guest effects"
)]
fn physical_code_site_journals_match_every_source_byte_and_final_word()
-> Result<(), String> {
    use layout::{
        CodeCellEvent, CodeVisitRequirement, admit_code_cell_schedule,
        encode_code_cell_schedule,
    };
    let source = source_with_data_written_input_opcode()?;
    for input in [Vec::new(), vec![0x80, 0xff]] {
        let mut vm =
            ProfileMachine::from_source(current_profile(), &source, input)
                .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = vm
            .run_traced(DYNAMIC_INPUT_LENGTH, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: DYNAMIC_INPUT_LENGTH,
        });
        let mut changed_code_sites = 0usize;
        for (index, initial) in source.iter().copied().enumerate() {
            let site =
                u32::try_from(index).map_err(|error| error.to_string())?;
            let mut events = Vec::new();
            for step in &trace {
                if let Some(write) = step.memory_delta.data
                    && write.address == site
                {
                    events.push(CodeCellEvent::DataWrite {
                        before: write.before,
                        after: write.after,
                    });
                }
                if step.before.registers.code_pointer == site {
                    let decoded =
                        step.decoded.ok_or("missing fetched opcode")?;
                    let required = match decoded {
                        b'o' | b'i' | b'j' | b'p' | b'*' | b'v' | b'/'
                        | b'<' => CodeVisitRequirement::Decoded(decoded),
                        _ => CodeVisitRequirement::Inert,
                    };
                    events.push(CodeCellEvent::Fetch(required));
                }
                if step
                    .memory_delta
                    .encryption
                    .is_some_and(|word| word.address == site)
                    && (step.before.registers.code_pointer != site
                        || step.decoded == Some(b'i'))
                {
                    events.push(CodeCellEvent::JumpTargetEncryption);
                }
            }
            assert!(!events.is_empty(), "unreached code cell M{site}");
            let admitted = admit_code_cell_schedule(
                current_profile(),
                site,
                initial,
                &events,
            )
            .map_err(|error| format!("M{site} alias refused: {error:?}"))?;
            let proposed =
                encode_code_cell_schedule(current_profile(), site, &events)
                    .map_err(|error| {
                        format!("M{site} candidate refused: {error:?}")
                    })?;
            assert_eq!(admitted, proposed, "source encoding M{site}");
            assert_eq!(admitted.initial, initial);
            assert_eq!(
                vm.memory_word(site).map_err(|error| error.to_string())?,
                admitted.final_cell,
                "final physical word M{site}",
            );
            if admitted.data_writes != 0 {
                changed_code_sites += 1;
                assert_eq!(site, DYNAMIC_INPUT_ADDRESS);
                assert_eq!(admitted.data_writes, 1);
            }
        }
        assert_eq!(changed_code_sites, 1);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    clippy::excessive_nesting,
    reason = "finite two-profile 94-phase full-width data-write admission"
)]
fn prefetch_full_width_data_writes_admit_all_decoder_phases()
-> Result<(), String> {
    use layout::{
        CodeCellEvent, CodeCellScheduleError, CodeVisitRequirement,
        admit_code_cell_schedule, encode_code_cell_schedule,
    };
    for profile in [current_profile(), malbolge::historical_profile()] {
        for site in 0..94u32 {
            let initial = encoded(
                usize::try_from(site).map_err(|error| error.to_string())?,
                b'o',
            )?;
            for after in [0, 32, 127, profile.memory_words() - 1] {
                let event = CodeCellEvent::DataWrite {
                    before: u32::from(initial),
                    after,
                };
                let schedule =
                    admit_code_cell_schedule(profile, site, initial, &[event])
                        .map_err(|error| format!("C{site}: {error:?}"))?;
                assert_eq!(schedule.initial, initial);
                assert_eq!(schedule.final_cell, after);
                assert_eq!(schedule.data_writes, 1);
                assert_eq!(schedule.fetches, 0);
                assert_eq!(
                    encode_code_cell_schedule(profile, site, &[event]),
                    Ok(schedule),
                );
                if !(33..=126).contains(&after) {
                    let refuse =
                        admit_code_cell_schedule(profile, site, initial, &[
                            event,
                            CodeCellEvent::Fetch(
                                CodeVisitRequirement::Decoded(b'o'),
                            ),
                        ]);
                    assert_eq!(
                        refuse,
                        Err(CodeCellScheduleError::DecodeMismatch { event: 1 }),
                    );
                }
            }
        }
    }
    Ok(())
}
