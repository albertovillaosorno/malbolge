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
//   - Normative source-to-loader-expanded memory cell phase verification.
// - Must-Not:
//   - Claim compiler-produced guest C branches or a compiled checksum loop.
// - Allows:
//   - Inputs: one j/(p or *)/v source and exact expanded memory sites.
//   - Outputs: real off-source data writes, phase parity and refusals.
//   - Side effects: isolated, bounded normative VM runs.
// - Split-When:
//   - A complete physical CFG linker verifies all expanded code/data cells.
// - Merge-When:
//   - Source-linked whole-memory translation proof supersedes this boundary.
// - Summary:
//   - Loader-expanded memory needs full-width initial phase identities.

//! Source-loaded guest writes to initially non-graphical expanded memory.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use layout::{
    CodeCellEvent, CodeCellScheduleError, CodeVisitRequirement,
    MAX_EXPANDED_CODE_CELLS, SourceCodeCellTraceError,
    SourceExpandedCodeBatchError, admit_code_cell_schedule,
    admit_loaded_code_cell_schedule, verify_source_expanded_code_cell_trace,
    verify_source_expanded_code_cells_trace,
};
use malbolge::{
    ProfileDescriptor, ProfileMachine, RunOutcome, Termination,
    current_profile, decode_profile_instruction, historical_profile,
};

const EXPANDED_SITE: u32 = 41;
const STEPS: usize = 3;

fn encoded(site: u32, opcode: u8) -> Result<u8, String> {
    (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), site) == Some(opcode)
        })
        .ok_or_else(|| format!("missing opcode {opcode} at C{site}"))
}

fn source(writer: u8) -> Result<Vec<u8>, String> {
    let bytes = vec![encoded(0, b'j')?, encoded(1, writer)?, encoded(2, b'v')?];
    if bytes.first().copied() != Some(40) {
        return Err(String::from("j must select loader-expanded M41"));
    }
    Ok(bytes)
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "finite three-step normative VM and independent phase rejection"
)]
fn expanded_loader_word_receives_real_guest_p_and_rotate_writes()
-> Result<(), String> {
    for profile in [current_profile(), historical_profile()] {
        for writer in *b"p*" {
            let source = source(writer)?;
            let mut machine =
                ProfileMachine::from_source(profile, &source, Vec::new())
                    .map_err(|error| error.to_string())?;
            let before = machine
                .memory_word(EXPANDED_SITE)
                .map_err(|error| error.to_string())?;
            assert!(before > 126, "expanded M41 must not be a source byte");
            let mut trace = Vec::new();
            let outcome = machine
                .run_traced(STEPS, &mut |step| trace.push(*step))
                .map_err(|error| error.to_string())?;
            assert_eq!(outcome, RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: STEPS,
            });
            assert_eq!(trace.len(), STEPS);
            let first = trace.first().ok_or("missing j step")?;
            let write_step = trace.get(1).ok_or("missing writer step")?;
            let halt = trace.get(2).ok_or("missing halt step")?;
            assert_eq!(first.decoded, Some(b'j'));
            assert_eq!(write_step.decoded, Some(writer));
            assert_eq!(halt.decoded, Some(b'v'));
            assert_eq!(write_step.before.registers.data_pointer, EXPANDED_SITE);
            let after = write_step.after.registers.accumulator;
            assert_ne!(after, before);
            assert_eq!(
                write_step.memory_delta.data.map(|delta| {
                    (delta.address, delta.before, delta.after)
                }),
                Some((EXPANDED_SITE, before, after))
            );
            let verified = verify_source_expanded_code_cell_trace(
                profile,
                &source,
                &[],
                STEPS,
                EXPANDED_SITE,
            )
            .map_err(|error| format!("expanded M41: {error:?}"))?;
            assert_eq!(verified.initial_word, before);
            assert_eq!(verified.final_word, after);
            assert_eq!(verified.outcome, outcome);
            assert_eq!(verified.events, [CodeCellEvent::DataWrite {
                before,
                after,
            }]);
            assert_eq!(verified.schedule.initial_word, before);
            assert_eq!(verified.schedule.final_cell, after);
            assert_eq!(verified.schedule.data_writes, 1);
            assert_eq!(verified.schedule.fetches, 0);
            assert_eq!(verified.schedule.target_encryptions, 0);
            assert_eq!(
                admit_code_cell_schedule(
                    profile,
                    EXPANDED_SITE,
                    0,
                    &verified.events
                ),
                Err(CodeCellScheduleError::InvalidSourceCell)
            );
            assert_eq!(
                admit_loaded_code_cell_schedule(
                    profile,
                    EXPANDED_SITE,
                    before,
                    &[CodeCellEvent::DataWrite {
                        before: before.saturating_add(1),
                        after,
                    }],
                ),
                Err(CodeCellScheduleError::DataWriteMismatch { event: 0 })
            );
            assert_eq!(
                admit_loaded_code_cell_schedule(
                    profile,
                    EXPANDED_SITE,
                    profile.memory_words(),
                    &verified.events,
                ),
                Err(CodeCellScheduleError::InvalidLoadedWord)
            );
            assert_eq!(
                admit_loaded_code_cell_schedule(
                    profile,
                    EXPANDED_SITE,
                    before,
                    &[CodeCellEvent::Fetch(CodeVisitRequirement::Decoded(
                        b'/'
                    ))],
                ),
                Err(CodeCellScheduleError::DecodeMismatch { event: 0 })
            );
        }
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "bounded raw-loader site and no-effect rejection"
)]
fn expanded_checker_rejects_original_source_and_unreached_memory()
-> Result<(), String> {
    let profile: &'static ProfileDescriptor = current_profile();
    let source = source(b'p')?;
    for site in 0..u32::try_from(source.len()).unwrap_or_default() {
        assert_eq!(
            verify_source_expanded_code_cell_trace(
                profile,
                &source,
                &[],
                3,
                site
            ),
            Err(SourceCodeCellTraceError::InvalidBound)
        );
    }
    assert_eq!(
        verify_source_expanded_code_cell_trace(profile, &source, &[], 3, 42),
        Err(SourceCodeCellTraceError::MissingEffect)
    );
    for steps in [0, 513] {
        assert_eq!(
            verify_source_expanded_code_cell_trace(
                profile,
                &source,
                &[],
                steps,
                EXPANDED_SITE,
            ),
            Err(SourceCodeCellTraceError::InvalidBound)
        );
    }
    assert_eq!(
        verify_source_expanded_code_cell_trace(
            profile,
            &source,
            &[],
            3,
            profile.memory_words(),
        ),
        Err(SourceCodeCellTraceError::InvalidBound)
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "source-loaded off-site jump and terminal expanded fetch"
)]
fn actual_indirect_jump_encrypts_expanded_word_then_fetches_non_graphical()
-> Result<(), String> {
    let profile = current_profile();
    let source = b"jioooo"
        .iter()
        .copied()
        .enumerate()
        .map(|(position, op)| {
            encoded(u32::try_from(position).unwrap_or_default(), op)
        })
        .collect::<Result<Vec<_>, _>>()?;
    let mut machine = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    // Independent 15-trit recurrence for this source predicts M41=63,
    // M63=36 and non-graphical M64=7,174,471 before the guest runs.
    assert_eq!(machine.memory_word(41), Ok(63));
    assert_eq!(machine.memory_word(63), Ok(36));
    assert_eq!(machine.memory_word(64), Ok(7_174_471));
    let mut trace = Vec::new();
    let outcome = machine
        .run_traced(3, &mut |step| trace.push(*step))
        .map_err(|error| error.to_string())?;
    assert_eq!(outcome, RunOutcome::Terminated {
        reason: Termination::NonGraphicalCell,
        steps: 3,
    });
    let first = trace.first().ok_or("missing j step")?;
    let jump_step = trace.get(1).ok_or("missing i step")?;
    let bad_fetch = trace.get(2).ok_or("missing terminal fetch")?;
    assert_eq!(first.decoded, Some(b'j'));
    assert_eq!(jump_step.decoded, Some(b'i'));
    assert_eq!(jump_step.memory_reads.data.map(|read| read.value), Some(63));
    assert_eq!(
        jump_step.memory_delta.encryption.map(|delta| delta.address),
        Some(63)
    );
    assert_eq!(bad_fetch.before.registers.code_pointer, 64);
    assert_eq!(bad_fetch.fetched_cell, Some(7_174_471));
    assert_eq!(bad_fetch.decoded, None);

    let jump =
        verify_source_expanded_code_cell_trace(profile, &source, &[], 3, 63)
            .map_err(|error| format!("expanded i-target: {error:?}"))?;
    assert_eq!(jump.events, [CodeCellEvent::JumpTargetEncryption]);
    assert_eq!(jump.schedule.target_encryptions, 1);
    assert_eq!(jump.schedule.fetches, 0);
    assert_eq!(jump.initial_word, 36);
    assert_eq!(
        jump.final_word,
        machine.memory_word(63).map_err(|error| error.to_string())?
    );

    let fetch =
        verify_source_expanded_code_cell_trace(profile, &source, &[], 3, 64)
            .map_err(|error| format!("expanded invalid fetch: {error:?}"))?;
    assert_eq!(fetch.events, [CodeCellEvent::FetchNonGraphicalHalt]);
    assert_eq!(fetch.schedule.fetches, 1);
    assert_eq!(fetch.schedule.data_writes, 0);
    assert_eq!(fetch.final_word, 7_174_471);
    assert_eq!(fetch.outcome, outcome);
    assert_eq!(
        admit_loaded_code_cell_schedule(profile, 64, fetch.initial_word, &[
            CodeCellEvent::JumpTargetEncryption
        ],),
        Err(CodeCellScheduleError::InvalidEncryptionTarget { event: 0 })
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "two-site VM parity and exact rejection of adversarial site sets"
)]
fn selected_expanded_sites_share_one_normative_execution() -> Result<(), String>
{
    let profile = current_profile();
    let source = b"jioooo"
        .iter()
        .copied()
        .enumerate()
        .map(|(position, opcode)| {
            encoded(u32::try_from(position).unwrap_or_default(), opcode)
        })
        .collect::<Result<Vec<_>, _>>()?;
    let batch =
        verify_source_expanded_code_cells_trace(profile, &source, &[], 3, &[
            63, 64,
        ])
        .map_err(|error| format!("two-site expanded image: {error:?}"))?;
    assert_eq!(batch.len(), 2);
    for (index, site) in [63, 64].into_iter().enumerate() {
        let separate = verify_source_expanded_code_cell_trace(
            profile,
            &source,
            &[],
            3,
            site,
        )
        .map_err(|error| format!("separate M{site}: {error:?}"))?;
        assert_eq!(batch.get(index), Some(&separate));
        assert_eq!(separate.site, site);
    }
    for bad in [
        vec![],
        vec![64, 63],
        vec![63, 63],
        vec![0, 63],
        vec![63, profile.memory_words()],
        (63..63
            + u32::try_from(MAX_EXPANDED_CODE_CELLS + 1).unwrap_or_default())
            .collect::<Vec<_>>(),
    ] {
        assert_eq!(
            verify_source_expanded_code_cells_trace(
                profile,
                &source,
                &[],
                3,
                &bad,
            ),
            Err(SourceExpandedCodeBatchError::InvalidBound),
            "invalid site set: {bad:?}"
        );
    }
    assert_eq!(
        verify_source_expanded_code_cells_trace(profile, &source, &[], 3, &[
            63, 65
        ],),
        Err(SourceExpandedCodeBatchError::Cell {
            site: 65,
            error: SourceCodeCellTraceError::MissingEffect,
        })
    );
    assert_eq!(
        verify_source_expanded_code_cells_trace(profile, &source, &[], 2, &[
            63, 64
        ],),
        Err(SourceExpandedCodeBatchError::Cell {
            site: 64,
            error: SourceCodeCellTraceError::MissingEffect,
        })
    );
    let padded = source
        .iter()
        .flat_map(|byte| [b'\n', *byte, b'\t'])
        .collect::<Vec<_>>();
    assert_eq!(
        verify_source_expanded_code_cells_trace(profile, &padded, &[], 3, &[
            63, 64
        ]),
        Ok(batch)
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "real p write, j pointer restore, i dependency and guest fetch"
)]
fn actual_guest_write_controls_an_expanded_indirect_jump() -> Result<(), String>
{
    // Loader-encoded positions: C0 j, C1 p, C2 j, C3 i, then inert
    // filler, ending with v. The real loader yields M42=40 so C2 j
    // restores D41 after the p write, and C3 i reads that changed M41.
    let source = b"(=&_@?>=<;:987C";
    let profile = current_profile();
    let site = 41;
    let target = 7_174_480;
    let next = target + 1;
    let mut machine = ProfileMachine::from_source(profile, source, Vec::new())
        .map_err(|error| error.to_string())?;
    assert_eq!(machine.memory_word(site), Ok(7_174_467));
    assert_eq!(machine.memory_word(42), Ok(40));
    assert_eq!(machine.memory_word(target), Ok(67));
    let mut steps = Vec::new();
    let outcome = machine
        .run_traced(5, &mut |step| steps.push(*step))
        .map_err(|error| format!("live write/indirect jump: {error}"))?;
    assert_eq!(outcome, RunOutcome::Terminated {
        reason: Termination::NonGraphicalCell,
        steps: 5,
    });
    assert_eq!(steps.len(), 5);
    let first = steps.first().ok_or("missing initial j")?;
    let write = steps.get(1).ok_or("missing p store")?;
    let restore = steps.get(2).ok_or("missing D-restore j")?;
    let jump = steps.get(3).ok_or("missing indirect i")?;
    let halt = steps.get(4).ok_or("missing non-graphical fetch")?;
    assert_eq!(first.decoded, Some(b'j'));
    assert_eq!(write.decoded, Some(b'p'));
    assert_eq!(
        write
            .memory_delta
            .data
            .map(|delta| { (delta.address, delta.before, delta.after) }),
        Some((site, 7_174_467, target))
    );
    assert_eq!(restore.decoded, Some(b'j'));
    assert_eq!(
        restore
            .memory_reads
            .data
            .map(|read| { (read.address, read.value) }),
        Some((42, 40))
    );
    assert_eq!(jump.decoded, Some(b'i'));
    assert_eq!(
        jump.memory_reads
            .data
            .map(|read| { (read.address, read.value) }),
        Some((site, target))
    );
    assert_eq!(
        jump.memory_delta
            .encryption
            .map(|delta| { (delta.address, delta.before) }),
        Some((target, 67))
    );
    assert_eq!(halt.before.registers.code_pointer, next);
    assert_eq!(halt.decoded, None);

    let cells =
        verify_source_expanded_code_cells_trace(profile, source, &[], 5, &[
            site, target, next,
        ])
        .map_err(|error| format!("data-dependent expanded i: {error:?}"))?;
    assert_eq!(cells.len(), 3);
    let data = cells.first().ok_or("no M41 observation")?;
    let encrypted = cells.get(1).ok_or("no jump-target observation")?;
    let fetched = cells.get(2).ok_or("no fetched-site observation")?;
    assert_eq!(data.site, site);
    assert_eq!(data.initial_word, 7_174_467);
    assert_eq!(data.final_word, target);
    assert_eq!(data.events, [CodeCellEvent::DataWrite {
        before: 7_174_467,
        after: target,
    }]);
    assert_eq!(encrypted.site, target);
    assert_eq!(encrypted.events, [CodeCellEvent::JumpTargetEncryption]);
    assert_eq!(fetched.site, next);
    assert_eq!(fetched.events, [CodeCellEvent::FetchNonGraphicalHalt]);
    assert_eq!(fetched.outcome, outcome);
    assert_eq!(
        verify_source_expanded_code_cells_trace(profile, source, &[], 5, &[
            site, 42, target
        ],),
        Err(SourceExpandedCodeBatchError::Cell {
            site: 42,
            error: SourceCodeCellTraceError::MissingEffect,
        })
    );
    Ok(())
}
