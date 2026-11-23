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
//   - One normative VM replay authenticating an entire loaded source image.
// - Must-Not:
//   - Claim source-C checksum compilation or infer unreachable C semantics.
// - Allows:
//   - Inputs: fixed graphical N15 guests, binary input and finite step caps.
//   - Outputs: exact per-code-cell journals, untouched parity and refusals.
//   - Side effects: isolated normative VM execution only.
// - Split-When:
//   - The source-linked physical compiler checks its complete guest image.
// - Merge-When:
//   - Whole-CFG translation verification subsumes physical image checking.
// - Summary:
//   - Every changed code cell must have an observed real guest effect.

//! Whole-image physical source verification, not a C23 checksum witness.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use layout::{
    CodeCellEvent, CodeVisitRequirement, SourceCodeImageTraceError,
    SourcePhysicalCodeFetch, SourcePhysicalDataRead, SourcePhysicalDataWrite,
    SourcePhysicalImageTraceError, SourcePhysicalIoEvent,
    SourcePhysicalWordEffect,
    build_byte_exact_input_store_source, verify_source_code_cell_trace,
    verify_source_code_image_trace, verify_source_expanded_code_cells_trace,
    verify_source_physical_image_trace,
};
use malbolge::{
    ProfileMachine, RunOutcome, TraceInput, current_profile,
    decode_profile_instruction, historical_profile,
};

const FOUR_READS: &[u8] =
    include_bytes!("compiler/fixtures/same-site-four-read.malbolge");
const DYNAMIC_INPUT: &[u8] =
    include_bytes!("compiler/fixtures/code-data-alias-dynamic-input.malbolge");

/// Literal physical oracle from the five-step dependent indirect jump guest.
const INDIRECT_DATA_READS: [SourcePhysicalDataRead; 4] = [
    SourcePhysicalDataRead {
        code_address: 0,
        data_address: 0,
        last_data_write_step: None,
        last_word_effect: None,
        opcode: b'j',
        trace_index: 0,
        value: 40,
    },
    SourcePhysicalDataRead {
        code_address: 1,
        data_address: 41,
        last_data_write_step: None,
        last_word_effect: None,
        opcode: b'p',
        trace_index: 1,
        value: 7_174_467,
    },
    SourcePhysicalDataRead {
        code_address: 2,
        data_address: 42,
        last_data_write_step: None,
        last_word_effect: None,
        opcode: b'j',
        trace_index: 2,
        value: 40,
    },
    SourcePhysicalDataRead {
        code_address: 3,
        data_address: 41,
        last_data_write_step: Some(1),
        last_word_effect: Some(SourcePhysicalWordEffect::DataWrite {
            trace_index: 1,
        }),
        opcode: b'i',
        trace_index: 3,
        value: 7_174_480,
    },
];

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "source-loaded entire-code-image and independent site replay"
)]
fn original_code_mutation_and_all_untouched_sites_have_exact_journals()
-> Result<(), String> {
    let profile = current_profile();
    let input = [0x00, 0xff];
    let image =
        verify_source_code_image_trace(profile, DYNAMIC_INPUT, &input, 81)
            .map_err(|error| format!("physical image: {error:?}"))?;
    assert_eq!(image.source_cells, 81);
    assert_eq!(image.outcome, RunOutcome::Terminated {
        reason: malbolge::Termination::HaltInstruction,
        steps: 81,
    });
    assert!(
        image
            .touched
            .windows(2)
            .all(|pair| pair[0].site < pair[1].site)
    );
    assert_eq!(image.touched.len(), image.source_cells);
    let alias = image
        .touched
        .iter()
        .find(|cell| cell.site == 79)
        .ok_or("missing actual source code/data alias")?;
    assert_eq!(alias.schedule.data_writes, 1);
    assert_eq!(alias.schedule.fetches, 1);
    assert_eq!(alias.events, [
        CodeCellEvent::DataWrite { before: 114, after: 38 },
        CodeCellEvent::Fetch(CodeVisitRequirement::Decoded(b'/')),
    ]);
    let isolated =
        verify_source_code_cell_trace(profile, DYNAMIC_INPUT, &input, 81, 79)
            .map_err(|error| format!("isolated source site: {error:?}"))?;
    assert_eq!(alias.events, isolated.events);
    assert_eq!(alias.schedule, isolated.schedule);
    assert_eq!(alias.final_word, isolated.final_word);
    assert_eq!(image.outcome, isolated.outcome);
    let mut vm =
        ProfileMachine::from_source(profile, DYNAMIC_INPUT, input.to_vec())
            .map_err(|error| error.to_string())?;
    let mut input_events = Vec::new();
    let outcome = vm
        .run_traced(81, &mut |step| {
            if let Some(event) = step.input {
                input_events.push(event);
            }
        })
        .map_err(|error| error.to_string())?;
    assert_eq!(image.outcome, outcome);
    assert_eq!(input_events, [TraceInput::Byte(0)]);
    for site in 0..DYNAMIC_INPUT.len() {
        let site = u32::try_from(site).map_err(|error| error.to_string())?;
        let actual = vm.memory_word(site).map_err(|error| error.to_string())?;
        let journaled = image.touched.iter().find(|cell| cell.site == site);
        assert_eq!(
            actual,
            journaled.map_or(
                u32::from(
                    DYNAMIC_INPUT[usize::try_from(site)
                        .map_err(|error| error.to_string())?]
                ),
                |cell| cell.final_word
            )
        );
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real repeated input and offsite code encryption image parity"
)]
fn full_four_input_code_image_has_repeated_fetches_and_offsite_xlat2()
-> Result<(), String> {
    let profile = current_profile();
    for input in [&b""[..], &b"\x00\xff\x80\x01\x02"[..]] {
        let full =
            verify_source_physical_image_trace(profile, FOUR_READS, input, 83)
                .map_err(|error| format!("four-read image: {error:?}"))?;
        let image = &full.source;
        assert_eq!(image.source_cells, 120);
        assert_eq!(image.outcome, RunOutcome::BudgetExhausted { steps: 83 });
        for (site, fetches, jump_encryption) in
            [(43, 1, true), (47, 7, false), (49, 7, false)]
        {
            let site_state = image
                .touched
                .iter()
                .find(|cell| cell.site == site)
                .ok_or("missing source-image physical site")?;
            assert_eq!(site_state.schedule.fetches, fetches);
            assert_eq!(
                site_state.schedule.target_encryptions > 0,
                jump_encryption
            );
        }
        let actual_input = if input.is_empty() {
            TraceInput::EndOfInput
        } else {
            TraceInput::Byte(input[0])
        };
        let io_reads = &full.io_events;
        assert_eq!(io_reads.len(), 5);
        assert_eq!(
            io_reads.iter().filter(|event| matches!(
                event, SourcePhysicalIoEvent::Input { code_address: 47, .. }
            )).count(),
            4,
        );
        assert!(matches!(io_reads[3], SourcePhysicalIoEvent::Output {
            code_address: 46,
            trace_index: 73,
            ..
        }));
        assert_eq!(io_reads[0], SourcePhysicalIoEvent::Input {
            code_address: 47,
            raw_word: match actual_input {
                TraceInput::Byte(byte) => u32::from(byte),
                TraceInput::EndOfInput => profile.eof_word(),
            },
            read: actual_input,
            trace_index: 47,
        });
        let input_site = image
            .touched
            .iter()
            .find(|cell| cell.site == 47)
            .ok_or("missing repeated input site")?;
        assert_eq!(
            input_site
                .events
                .iter()
                .filter(|event| {
                    **event
                        == CodeCellEvent::Fetch(CodeVisitRequirement::Decoded(
                            b'/',
                        ))
                })
                .count(),
            4
        );
        let jump_site = image
            .touched
            .iter()
            .find(|cell| cell.site == 49)
            .ok_or("missing repeated jump site")?;
        assert_eq!(jump_site.final_word, u32::from(FOUR_READS[49]));
        assert!(jump_site.events.iter().all(|event| {
            *event == CodeCellEvent::Fetch(CodeVisitRequirement::Decoded(b'i'))
        }));
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "raw-source loader fidelity and fail-closed image bounds"
)]
fn image_source_uses_loaded_positions_and_rejects_invalid_bounds()
-> Result<(), String> {
    let profile = current_profile();
    let canonical =
        verify_source_code_image_trace(profile, FOUR_READS, &[], 83)
            .map_err(|error| format!("canonical image: {error:?}"))?;
    let whitespace = [b' ', b'\t', b'\n', 0x0b, 0x0c, b'\r'];
    let mut spaced = Vec::with_capacity(FOUR_READS.len() * 2 + 6);
    spaced.extend_from_slice(&whitespace);
    for (byte, separator) in FOUR_READS
        .iter()
        .copied()
        .zip(whitespace.iter().copied().cycle())
    {
        spaced.push(byte);
        spaced.push(separator);
    }
    let formatted = verify_source_code_image_trace(profile, &spaced, &[], 83)
        .map_err(|error| format!("whitespace image: {error:?}"))?;
    assert_eq!(formatted, canonical);
    assert_eq!(
        verify_source_code_image_trace(profile, FOUR_READS, &[], 0),
        Err(SourceCodeImageTraceError::InvalidBound),
    );
    assert_eq!(
        verify_source_code_image_trace(profile, FOUR_READS, &[], 513),
        Err(SourceCodeImageTraceError::InvalidBound),
    );
    assert_eq!(
        verify_source_code_image_trace(profile, &vec![b' '; 4097], &[], 1),
        Err(SourceCodeImageTraceError::InvalidBound),
    );
    let invalid_byte = (33u8..=126u8)
        .find(|byte| {
            !b"oijp*/<v".contains(
                &decode_profile_instruction(u32::from(*byte), 0)
                    .unwrap_or_default(),
            )
        })
        .ok_or("no loader-invalid graphical byte")?;
    assert_eq!(
        verify_source_code_image_trace(profile, &[invalid_byte], &[], 1),
        Err(SourceCodeImageTraceError::InvalidSource),
    );
    // Historical C0..C1 loader-valid inert code still has a complete image.
    // A subsequent untouched C2/C3 tail must remain byte-identical.
    let source = [
        (33u8..=126u8)
            .find(|byte| {
                decode_profile_instruction(u32::from(*byte), 0) == Some(b'o')
            })
            .ok_or("missing historical inert byte")?,
        (33u8..=126u8)
            .find(|byte| {
                decode_profile_instruction(u32::from(*byte), 1) == Some(b'v')
            })
            .ok_or("missing historical halt byte")?,
        (33u8..=126u8)
            .find(|byte| {
                decode_profile_instruction(u32::from(*byte), 2) == Some(b'o')
            })
            .ok_or("missing historical tail byte")?,
        (33u8..=126u8)
            .find(|byte| {
                decode_profile_instruction(u32::from(*byte), 3) == Some(b'o')
            })
            .ok_or("missing historical tail byte")?,
    ];
    let historical =
        verify_source_code_image_trace(historical_profile(), &source, &[], 2)
            .map_err(|error| format!("historical image: {error:?}"))?;
    assert_eq!(historical.source_cells, 4);
    assert_eq!(historical.touched.len(), 2);
    assert_eq!(historical.touched[0].site, 0);
    assert_eq!(historical.touched[1].site, 1);
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "whole-source terminal alias proof with real normative VM"
)]
fn terminal_non_graphical_code_fetch_is_reconciled_in_whole_image()
-> Result<(), String> {
    let profile = current_profile();
    let mut source = (0..43u32)
        .map(|site| {
            (33..=126u8)
                .find(|byte| {
                    decode_profile_instruction(u32::from(*byte), site)
                        == Some(b'o')
                })
                .ok_or_else(|| format!("missing C{site} inert source byte"))
        })
        .collect::<Result<Vec<_>, _>>()?;
    for (site, opcode) in [(0, b'j'), (1, b'p'), (2, b'i'), (41, b'i')] {
        *source.get_mut(site).ok_or("missing expected code site")? = (33
            ..=126u8)
            .find(|byte| {
                decode_profile_instruction(
                    u32::from(*byte),
                    u32::try_from(site).unwrap_or_default(),
                ) == Some(opcode)
            })
            .ok_or("unencodable source opcode")?;
    }
    *source.get_mut(42).ok_or("missing jump operand")? = 39;
    let image = verify_source_code_image_trace(profile, &source, &[], 8)
        .map_err(|error| format!("non-graphical terminal image: {error:?}"))?;
    assert_eq!(image.outcome, RunOutcome::Terminated {
        reason: malbolge::Termination::NonGraphicalCell,
        steps: 5,
    });
    assert_eq!(image.source_cells, source.len());
    let terminal = image
        .touched
        .iter()
        .find(|cell| cell.site == 41)
        .ok_or("missing source site 41")?;
    assert_eq!(terminal.schedule.fetches, 1);
    assert_eq!(terminal.schedule.data_writes, 1);
    assert!(terminal.final_word > 126);
    assert_eq!(terminal.events.len(), 2);
    assert!(matches!(
        terminal.events.first(),
        Some(CodeCellEvent::DataWrite { .. })
    ));
    assert_eq!(
        terminal.events.get(1),
        Some(&CodeCellEvent::FetchNonGraphicalHalt)
    );
    assert!(image.touched.iter().all(|cell| cell.site <= 42));
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real byte/EOF stores and all expanded memory from one VM replay"
)]
fn complete_physical_footprint_includes_both_input_dependent_expanded_writes()
-> Result<(), String> {
    let profile = current_profile();
    let plan = build_byte_exact_input_store_source(profile)
        .map_err(|error| format!("source builder: {error:?}"))?;
    assert!(
        usize::try_from(plan.exact_data_address)
            .is_ok_and(|site| site >= plan.source.len())
    );
    assert!(
        usize::try_from(plan.first_data_address)
            .is_ok_and(|site| site >= plan.source.len())
    );
    let mut sites = [plan.first_data_address, plan.exact_data_address];
    sites.sort_unstable();
    for input in [&b""[..], &b"\x00"[..], &b"\x02"[..], &b"\xff"[..]] {
        let complete = verify_source_physical_image_trace(
            profile,
            &plan.source,
            input,
            512,
        )
        .map_err(|error| format!("complete physical image: {error:?}"))?;
        let isolated = verify_source_expanded_code_cells_trace(
            profile,
            &plan.source,
            input,
            512,
            &sites,
        )
        .map_err(|error| format!("isolated expanded sites: {error:?}"))?;
        let source_only =
            verify_source_code_image_trace(profile, &plan.source, input, 512)
                .map_err(|error| format!("source image: {error:?}"))?;
        assert_eq!(complete.source, source_only);
        assert_eq!(complete.expanded, isolated);
        assert_eq!(complete.expanded.len(), 2);
        assert!(complete.expanded.iter().all(|cell| {
            cell.schedule.data_writes == 1 && cell.schedule.fetches == 0
        }));
        assert_eq!(
            complete
                .expanded
                .iter()
                .map(|cell| cell.site)
                .collect::<Vec<_>>(),
            sites,
        );
        let expected = input
            .first()
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let stored = complete
            .expanded
            .iter()
            .find(|cell| cell.site == plan.exact_data_address)
            .ok_or("missing exact input store")?;
        assert_eq!(stored.final_word, expected);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "actual data-dependent guest jump and expanded terminal fetch"
)]
fn physical_image_discovers_indirect_jump_and_unexecutable_expanded_cell()
-> Result<(), String> {
    let profile = current_profile();
    let source = b"(=&_@?>=<;:987C";
    let complete = verify_source_physical_image_trace(profile, source, &[], 5)
        .map_err(|error| format!("complete indirect jump: {error:?}"))?;
    assert_eq!(complete.source.source_cells, source.len());
    assert_eq!(complete.source.outcome, RunOutcome::Terminated {
        reason: malbolge::Termination::NonGraphicalCell,
        steps: 5,
    });
    assert_eq!(
        complete
            .expanded
            .iter()
            .map(|cell| cell.site)
            .collect::<Vec<_>>(),
        [41, 7_174_480, 7_174_481]
    );
    assert_eq!(
        complete.expanded.first().map(|cell| cell.events.as_slice()),
        Some(
            [CodeCellEvent::DataWrite {
                before: 7_174_467,
                after: 7_174_480,
            }]
            .as_slice()
        )
    );
    assert_eq!(
        complete.expanded.get(1).map(|cell| cell.events.as_slice()),
        Some([CodeCellEvent::JumpTargetEncryption].as_slice())
    );
    assert_eq!(
        complete.expanded.get(2).map(|cell| cell.events.as_slice()),
        Some([CodeCellEvent::FetchNonGraphicalHalt].as_slice())
    );
    // Prove one actually reached guest p write precedes the later i operand
    // read of the *new* value, without inferring a C source branch.
    assert_eq!(complete.data_reads, INDIRECT_DATA_READS);
    assert_eq!(complete.data_writes, [SourcePhysicalDataWrite {
        code_address: 1,
        data_address: 41,
        before: 7_174_467,
        after: 7_174_480,
        last_word_effect: None,
        opcode: b'p',
        trace_index: 1,
    }]);
    assert_eq!(
        complete.expanded,
        verify_source_expanded_code_cells_trace(profile, source, &[], 5, &[
            41, 7_174_480, 7_174_481
        ],)
        .map_err(|error| format!("selected indirect jump: {error:?}"))?
    );
    assert_eq!(
        complete.source,
        verify_source_code_image_trace(profile, source, &[], 5)
            .map_err(|error| format!("indirect jump source: {error:?}"))?
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real code-data alias and exact fetch-before-encryption ordering"
)]
fn physical_fetches_retain_data_write_and_xlat2_provenance()
-> Result<(), String> {
    let profile = current_profile();
    let alias =
        verify_source_physical_image_trace(profile, DYNAMIC_INPUT, &[], 81)
            .map_err(|error| format!("source-code alias image: {error:?}"))?;
    assert_eq!(alias.code_fetches.len(), 81);
    assert!(alias.data_writes.iter().any(|write| {
        write.code_address == 57
            && write.opcode == b'*'
            && write.data_address == 79
            && write.before == 114
            && write.after == 38
            && write.last_word_effect.is_none()
            && write.trace_index == 57
    }));
    assert_eq!(alias.code_fetches[79], SourcePhysicalCodeFetch {
        code_address: 79,
        last_data_write_step: Some(57),
        last_word_effect: Some(SourcePhysicalWordEffect::DataWrite {
            trace_index: 57,
        }),
        trace_index: 79,
        value: 38,
    });
    assert_eq!(
        decode_profile_instruction(alias.code_fetches[79].value, 79),
        Some(b'/'),
        "later instruction must decode physically changed source word",
    );

    let repeated =
        verify_source_physical_image_trace(profile, FOUR_READS, &[], 83)
            .map_err(|error| format!("repeated code-fetch image: {error:?}"))?;
    assert_eq!(repeated.code_fetches.len(), 83);
    assert!(
        repeated
            .code_fetches
            .iter()
            .enumerate()
            .all(|(step, fetch)| { fetch.trace_index == step })
    );
    let reads = repeated
        .code_fetches
        .iter()
        .filter(|fetch| fetch.code_address == 47)
        .collect::<Vec<_>>();
    assert_eq!(reads.len(), 7);
    assert_eq!(reads[0].last_word_effect, None);
    for pair in reads.windows(2) {
        let before = pair[0];
        let after = pair[1];
        assert_eq!(after.last_data_write_step, None);
        assert_eq!(
            after.last_word_effect,
            Some(SourcePhysicalWordEffect::Encryption {
                trace_index: before.trace_index,
            }),
            "C47 is re-fetched after its own latest XLAT2",
        );
    }
    let jumps = repeated
        .code_fetches
        .iter()
        .filter(|fetch| fetch.code_address == 49)
        .collect::<Vec<_>>();
    assert_eq!(jumps.len(), 7);
    assert!(
        jumps.iter().all(|fetch| {
            fetch.last_word_effect.is_none()
                && fetch.value == u32::from(FOUR_READS[49])
        }),
        "repeated i never encrypts its fetched C49 instruction"
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real source and expanded terminal fetch evidence"
)]
fn physical_fetches_include_terminal_non_graphical_read_after_data_write()
-> Result<(), String> {
    // Keep C56 j/C57 * and all preceding code identical, but rotate an
    // initially loader-valid source word at C79 into a non-graphical value.
    let profile = current_profile();
    let mut non_graphical = DYNAMIC_INPUT.to_vec();
    let original = (33..=126u8)
        .find(|byte| {
            byte % 3 != 0
                && b"oijp*/<v".contains(
                    &decode_profile_instruction(u32::from(*byte), 79)
                        .unwrap_or_default(),
                )
        })
        .ok_or("no source-valid non-graphical rotation at C79")?;
    non_graphical[79] = original;
    let rewritten =
        verify_source_physical_image_trace(profile, &non_graphical, &[], 81)
            .map_err(|error| format!("code/data terminal alias: {error:?}"))?;
    assert_eq!(rewritten.source.outcome, RunOutcome::Terminated {
        reason: malbolge::Termination::NonGraphicalCell,
        steps: 80,
    });
    assert_eq!(rewritten.code_fetches.len(), 80);
    assert!(rewritten.code_fetches.last().is_some_and(|fetch| {
        fetch.code_address == 79
            && fetch.trace_index == 79
            && fetch.value > 126
            && fetch.last_data_write_step == Some(57)
            && fetch.last_word_effect
                == Some(SourcePhysicalWordEffect::DataWrite { trace_index: 57 })
    }));

    let source = b"(=&_@?>=<;:987C";
    let trace =
        verify_source_physical_image_trace(current_profile(), source, &[], 5)
            .map_err(|error| format!("terminal fetch image: {error:?}"))?;
    assert_eq!(trace.code_fetches.len(), 5);
    assert_eq!(
        trace.code_fetches.last().map(|fetch| (
            fetch.code_address,
            fetch.trace_index,
            fetch.last_word_effect,
        )),
        Some((7_174_481, 4, None))
    );
    assert!(
        trace
            .code_fetches
            .last()
            .is_some_and(|fetch| fetch.value > 126)
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real two-indirect-jump physical XLAT2 before target fetch"
)]
fn offsite_xlat2_precedes_first_code_fetch_at_original_target()
-> Result<(), String> {
    let profile = current_profile();
    let encode = |site: u32, opcode: u8| {
        (33..=126u8)
            .find(|byte| {
                decode_profile_instruction(u32::from(*byte), site)
                    == Some(opcode)
            })
            .ok_or_else(|| format!("cannot encode {opcode} at C{site}"))
    };
    // C0 i encrypts C98 and jumps to C99; C99 i reads untouched M1=97,
    // targets C97 and jumps back to C98, *after* its earlier off-site XLAT2.
    let first_jump = encode(0, b'i')?;
    assert_eq!(first_jump, 98);
    let target = u32::from(first_jump);
    let jump_site = target.checked_add(1).ok_or("jump overflow")?;
    let mut source = (0..=jump_site)
        .map(|site| encode(site, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    source[0] = first_jump;
    source[1] = first_jump.checked_sub(1).ok_or("bad jump operand")?;
    assert_eq!(
        decode_profile_instruction(u32::from(source[1]), 1),
        Some(b'i'),
        "the unexecuted second-jump operand must remain loader-admitted",
    );
    source[usize::try_from(jump_site).map_err(|error| error.to_string())?] =
        encode(jump_site, b'i')?;
    let original_target =
        source[usize::try_from(target).map_err(|error| error.to_string())?];
    let encrypted_target =
        malbolge::encrypt_profile_cell(u32::from(original_target))
            .ok_or("source target cannot be encrypted")?;
    assert_ne!(encrypted_target, u32::from(original_target));
    let image = verify_source_physical_image_trace(profile, &source, &[], 3)
        .map_err(|error| format!("XLAT2-before-fetch image: {error:?}"))?;
    assert_eq!(image.source.outcome, RunOutcome::BudgetExhausted {
        steps: 3
    });
    assert_eq!(image.code_fetches.len(), 3);
    assert_eq!(
        image
            .code_fetches
            .iter()
            .map(|read| read.code_address)
            .collect::<Vec<_>>(),
        [0, jump_site, target],
    );
    assert_eq!(image.data_reads.len(), 2);
    assert_eq!(image.data_reads[0].value, target);
    assert_eq!(image.data_reads[1].value, target - 1);
    assert_eq!(image.code_fetches[2], SourcePhysicalCodeFetch {
        code_address: target,
        last_data_write_step: None,
        last_word_effect: Some(SourcePhysicalWordEffect::Encryption {
            trace_index: 0,
        }),
        trace_index: 2,
        value: encrypted_target,
    });
    assert_eq!(
        decode_profile_instruction(image.code_fetches[2].value, target),
        Some(b'J'),
        "post-XLAT2 target is an inert instruction, not its original o",
    );
    // Changing only the second i to a true halt leaves C98 encrypted, but
    // never fetched. An XLAT2 effect is not evidence of target reachability.
    let mut no_fetch = source;
    no_fetch
        [usize::try_from(jump_site).map_err(|error| error.to_string())?] =
        encode(jump_site, b'v')?;
    let halted = verify_source_physical_image_trace(profile, &no_fetch, &[], 3)
        .map_err(|error| format!("unreached XLAT2 target image: {error:?}"))?;
    assert_eq!(halted.source.outcome, RunOutcome::Terminated {
        reason: malbolge::Termination::HaltInstruction,
        steps: 2,
    });
    assert_eq!(halted.code_fetches.len(), 2);
    assert!(
        !halted
            .code_fetches
            .iter()
            .any(|fetch| { fetch.code_address == target })
    );
    let untouched_by_fetch = halted
        .source
        .touched
        .iter()
        .find(|cell| cell.site == target)
        .ok_or("missing real off-site XLAT2")?;
    assert_eq!(untouched_by_fetch.events, [
        CodeCellEvent::JumpTargetEncryption
    ],);
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "complete-prefix bounds and source-only negative controls"
)]
fn physical_image_is_bounded_and_does_not_invent_unreached_expanded_effects()
-> Result<(), String> {
    let profile = current_profile();
    let image =
        verify_source_physical_image_trace(profile, DYNAMIC_INPUT, &[], 81)
            .map_err(|error| format!("source-only image: {error:?}"))?;
    assert!(image.expanded.is_empty());
    assert_eq!(image.source.source_cells, DYNAMIC_INPUT.len());
    for steps in [0, 513] {
        assert_eq!(
            verify_source_physical_image_trace(
                profile,
                DYNAMIC_INPUT,
                &[],
                steps,
            ),
            Err(SourcePhysicalImageTraceError::Source(
                SourceCodeImageTraceError::InvalidBound
            ))
        );
    }
    assert_eq!(
        verify_source_physical_image_trace(profile, &vec![b' '; 4097], &[], 1,),
        Err(SourcePhysicalImageTraceError::Source(
            SourceCodeImageTraceError::InvalidBound
        ))
    );
    Ok(())
}

/// Encode only the three real positional guest instructions used below.
fn three_step_read_source() -> Result<Vec<u8>, String> {
    b"jpv"
        .iter()
        .copied()
        .enumerate()
        .map(|(site, opcode)| {
            (33..=126u8)
                .find(|byte| {
                    decode_profile_instruction(
                        u32::from(*byte),
                        u32::try_from(site).unwrap_or_default(),
                    ) == Some(opcode)
                })
                .ok_or_else(|| format!("cannot encode {opcode} at C{site}"))
        })
        .collect()
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    reason = "two real profile executions with whitespace and prefix parity"
)]
fn physical_operand_reads_preserve_loader_positions_and_prefix_bounds()
-> Result<(), String> {
    for profile in [current_profile(), historical_profile()] {
        let source = three_step_read_source()?;
        assert_eq!(source.first(), Some(&40));
        let complete =
            verify_source_physical_image_trace(profile, &source, &[], 3)
                .map_err(|error| {
                    format!("full three-step read journal: {error:?}")
                })?;
        assert_eq!(complete.source.source_cells, 3);
        assert_eq!(complete.source.outcome, RunOutcome::Terminated {
            reason: malbolge::Termination::HaltInstruction,
            steps: 3,
        });
        assert_eq!(complete.data_reads.len(), 2);
        assert_eq!(complete.data_writes.len(), 1);
        assert_eq!(complete.data_writes[0].trace_index, 1);
        assert_eq!(complete.data_writes[0].code_address, 1);
        assert_eq!(complete.data_writes[0].data_address, 41);
        assert_eq!(
            complete.data_writes[0].before,
            complete.data_reads[1].value
        );
        assert_eq!(complete.data_writes[0].opcode, b'p');
        assert_eq!(
            complete.data_reads.first().map(|read| (
                read.trace_index,
                read.opcode,
                read.data_address,
                read.value,
            )),
            Some((0, b'j', 0, 40)),
        );
        assert_eq!(
            complete.data_reads.get(1).map(|read| (
                read.trace_index,
                read.opcode,
                read.data_address,
                read.last_data_write_step,
            )),
            Some((1, b'p', 41, None)),
        );
        assert_eq!(complete.expanded.len(), 1);
        assert_eq!(
            complete
                .expanded
                .first()
                .map(|cell| (cell.site, cell.schedule.data_writes,)),
            Some((41, 1))
        );
        let padded = source
            .iter()
            .flat_map(|byte| [b'\n', *byte, b'\t'])
            .collect::<Vec<_>>();
        assert_eq!(
            verify_source_physical_image_trace(profile, &padded, &[], 3),
            Ok(complete.clone()),
        );
        let prefix =
            verify_source_physical_image_trace(profile, &source, &[], 1)
                .map_err(|error| {
                    format!("one-step read-only prefix: {error:?}")
                })?;
        assert!(prefix.expanded.is_empty());
        assert!(prefix.data_writes.is_empty());
        assert_eq!(prefix.data_reads.len(), 1);
        assert_eq!(prefix.data_reads.first(), complete.data_reads.first());
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "three real guest I/O instructions and exact EOF effects"
)]
fn physical_input_output_journal_keeps_raw_eof_and_output_order()
-> Result<(), String> {
    // The actual graphical source executes /; <; v. This is a physical
    // I/O witness only: it is not a source-C EOF normalization or checksum.
    let profile = current_profile();
    let source = [b'/', b'<', b'v']
        .into_iter()
        .enumerate()
        .map(|(site, opcode)| {
            (33..=126u8)
                .find(|byte| {
                    decode_profile_instruction(
                        u32::from(*byte),
                        u32::try_from(site).unwrap_or_default(),
                    ) == Some(opcode)
                })
                .ok_or_else(|| format!("cannot encode {opcode} at C{site}"))
        })
        .collect::<Result<Vec<_>, _>>()?;
    for input in [&b""[..], &b"\x00"[..], &b"\xff\x05"[..]] {
        let raw = input.first().map_or_else(
            || profile.eof_word(), |byte| u32::from(*byte),
        );
        let read = input.first().map_or(
            TraceInput::EndOfInput, |byte| TraceInput::Byte(*byte),
        );
        let image = verify_source_physical_image_trace(
            profile, &source, input, 3,
        )
        .map_err(|error| format!("real guest byte I/O: {error:?}"))?;
        assert_eq!(image.source.outcome, RunOutcome::Terminated {
            reason: malbolge::Termination::HaltInstruction,
            steps: 3,
        });
        assert!(image.data_reads.is_empty());
        assert!(image.data_writes.is_empty());
        assert_eq!(image.io_events, [
            SourcePhysicalIoEvent::Input {
                code_address: 0,
                raw_word: raw,
                read,
                trace_index: 0,
            },
            SourcePhysicalIoEvent::Output {
                code_address: 1,
                accumulator: raw,
                byte: *raw.to_le_bytes().first().ok_or("missing low byte")?,
                trace_index: 1,
            },
        ]);
        let prefix = verify_source_physical_image_trace(
            profile, &source, input, 1,
        )
        .map_err(|error| format!("one-input prefix: {error:?}"))?;
        assert_eq!(prefix.source.outcome, RunOutcome::BudgetExhausted {
            steps: 1,
        });
        assert_eq!(prefix.io_events, image.io_events[..1]);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "idempotent physical store is a reached guest effect, not a delta"
)]
fn physical_data_writes_retain_idempotent_store_and_last_writer()
-> Result<(), String> {
    let profile = current_profile();
    let encode = |site: u32, opcode: u8| {
        (33..=126u8)
            .find(|byte| {
                decode_profile_instruction(u32::from(*byte), site)
                    == Some(opcode)
            })
            .ok_or_else(|| format!("cannot encode {opcode} at C{site}"))
    };
    let mut source = (0..59u32)
        .map(|site| encode(site, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    for (site, opcode) in
        [(0, b'j'), (1, b'p'), (2, b'j'), (3, b'p'), (4, b'v')]
    {
        source[site] = encode(
            u32::try_from(site).map_err(|error| error.to_string())?,
            opcode,
        )?;
    }
    for (site, byte) in [(41, 40), (42, 56), (57, 60)] {
        source[site] = byte;
    }
    let image = verify_source_physical_image_trace(profile, &source, &[], 5)
        .map_err(|error| format!("idempotent guest image: {error:?}"))?;
    assert_eq!(image.source.outcome, RunOutcome::Terminated {
        reason: malbolge::Termination::HaltInstruction,
        steps: 5,
    });
    assert_eq!(image.data_writes, [
        SourcePhysicalDataWrite {
            code_address: 1,
            data_address: 41,
            before: 40,
            after: 7_174_453,
            last_word_effect: None,
            opcode: b'p',
            trace_index: 1,
        },
        SourcePhysicalDataWrite {
            code_address: 3,
            data_address: 57,
            before: 60,
            after: 60,
            last_word_effect: None,
            opcode: b'p',
            trace_index: 3,
        },
    ]);
    let observed = image
        .source
        .touched
        .iter()
        .find(|cell| cell.site == 57)
        .ok_or("idempotent source site not journaled")?;
    assert_eq!(observed.events, [CodeCellEvent::DataWrite {
        before: 60,
        after: 60,
    }]);
    assert_eq!(observed.schedule.data_writes, 1);
    assert_eq!(observed.final_word, 60);
    let mut without_store = source;
    without_store[3] = encode(3, b'o')?;
    let missing =
        verify_source_physical_image_trace(profile, &without_store, &[], 5)
            .map_err(|error| format!("disabled idempotent store: {error:?}"))?;
    assert_eq!(missing.data_writes.len(), 1);
    assert!(!missing.source.touched.iter().any(|cell| cell.site == 57));
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "source-loaded p self-alias and post-store XLAT2"
)]
fn physical_data_journal_distinguishes_same_step_alias_from_xlat2()
-> Result<(), String> {
    let profile = current_profile();
    let encode = |site: u32, opcode: u8| {
        (33..=126u8)
            .find(|byte| {
                decode_profile_instruction(u32::from(*byte), site)
                    == Some(opcode)
            })
            .ok_or_else(|| format!("cannot encode {opcode} at C{site}"))
    };
    let mut source = (0..86u32)
        .map(|site| encode(site, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    for (site, opcode) in [
        (0, b'j'), (1, b'p'), (2, b'i'), (83, b'j'),
        (84, b'p'), (85, b'v'),
    ] {
        source[site] = encode(
            u32::try_from(site).map_err(|error| error.to_string())?,
            opcode,
        )?;
    }
    for (site, byte) in [(41, 40), (42, 75), (50, 83)] {
        source[site] = byte;
    }
    assert_eq!(source[84], 72);
    let image = verify_source_physical_image_trace(profile, &source, &[], 13)
        .map_err(|error| format!("self-alias physical image: {error:?}"))?;
    assert_eq!(image.source.outcome, RunOutcome::Terminated {
        reason: malbolge::Termination::HaltInstruction,
        steps: 13,
    });
    assert_eq!(image.data_writes.len(), 2);
    let last = image.data_writes.last().ok_or("missing self-alias p")?;
    assert_eq!(*last, SourcePhysicalDataWrite {
        code_address: 84,
        data_address: 84,
        before: 72,
        after: 72,
        last_word_effect: None,
        opcode: b'p',
        trace_index: 11,
    });
    let code = image.code_fetches.iter()
        .find(|read| read.code_address == 84)
        .ok_or("self-alias fetch not found")?;
    assert_eq!(code.trace_index, last.trace_index);
    assert_eq!(code.value, last.before);
    assert_eq!(code.last_word_effect, None);
    let cell = image.source.touched.iter()
        .find(|cell| cell.site == 84)
        .ok_or("missing self-alias cell")?;
    assert_eq!(cell.events, [CodeCellEvent::FetchSelfWrite {
        opcode: b'p', after: 72,
    }]);
    assert_eq!(cell.schedule.data_writes, 1);
    assert_eq!(cell.final_word, malbolge::encrypt_profile_cell(72)
        .ok_or("self-alias must encrypt")?);
    Ok(())
}
