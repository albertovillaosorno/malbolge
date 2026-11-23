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
    SourcePhysicalImageTraceError, build_byte_exact_input_store_source,
    verify_source_code_cell_trace, verify_source_code_image_trace,
    verify_source_expanded_code_cells_trace,
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
        let image =
            verify_source_code_image_trace(profile, FOUR_READS, input, 83)
                .map_err(|error| format!("four-read image: {error:?}"))?;
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
