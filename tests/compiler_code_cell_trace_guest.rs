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
//   - Real idempotent code-cell store and prefetch XLAT2 journal evidence.
// - Must-Not:
//   - Substitute changed-cell deltas for physical instructions or C linkage.
// - Allows:
//   - Inputs: two source-loaded N15 guests, byte/EOF streams and VM traces.
//   - Outputs: exact live-cell journals and bounded negative outcomes.
//   - Side effects: bounded, isolated normative VM execution only.
// - Split-When:
//   - Complete physical target linker emits authentic chronological journals.
// - Merge-When:
//   - General source-locked verifier proves all C23 code/data effects.
// - Summary:
//   - Unchanged p/* writes still count as physical data operations.

//! Source-loaded trace proof of real code-cell effects without memory deltas.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use layout::{
    CodeCellEvent, CodeCellScheduleError, SourceCodeCellTraceError,
    admit_code_cell_schedule, encode_code_cell_schedule,
    verify_source_code_cell_trace,
};
use malbolge::{
    ProfileMachine, ProfileMemoryRead, RunOutcome, current_profile,
    decode_profile_instruction, historical_profile,
};

const FIRST_DATA_SITE: u32 = 41;
const IDEMPOTENT_SITE: u32 = 57;
const IDEMPOTENT_WORD: u32 = 60;
const FIRST_ACCUMULATOR: u32 = 7_174_453;

fn encoded(site: u32, opcode: u8) -> Result<u8, String> {
    (33u8..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), site) == Some(opcode)
        })
        .ok_or_else(|| format!("unencodable C{site} opcode {opcode}"))
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "independent five-step idempotent p source and VM read evidence"
)]
fn idempotent_code_cell_crazy_is_a_real_write_without_changed_delta()
-> Result<(), String> {
    let profile = current_profile();
    let mut source = (0..59u32)
        .map(|site| encoded(site, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    for (site, opcode) in
        [(0, b'j'), (1, b'p'), (2, b'j'), (3, b'p'), (4, b'v')]
    {
        *source.get_mut(site).ok_or("missing source instruction")? = encoded(
            u32::try_from(site).map_err(|error| error.to_string())?,
            opcode,
        )?;
    }
    // The first j reads its own C0 byte 40 and relocates D to M41.
    // The first p reads M41=40, producing A=all-one trits and D=M42.
    // The second j reads M42=56 and relocates D to M57.
    // The second p then writes crazy(M57=60, A=all-one trits) = 60.
    for (site, value) in [(41, 40), (42, 56), (57, 60)] {
        *source.get_mut(site).ok_or("missing source data cell")? = value;
    }
    let mut vm = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    let mut trace = Vec::new();
    let outcome = vm
        .run_traced(5, &mut |step| trace.push(*step))
        .map_err(|error| error.to_string())?;
    assert_eq!(outcome, RunOutcome::Terminated {
        reason: malbolge::Termination::HaltInstruction,
        steps: 5,
    });
    let first = trace.get(1).ok_or("missing first crazy write")?;
    assert_eq!(first.decoded, Some(b'p'));
    assert_eq!(first.before.registers.data_pointer, FIRST_DATA_SITE);
    assert_eq!(first.after.registers.accumulator, FIRST_ACCUMULATOR);
    let idempotent = trace.get(3).ok_or("missing second crazy write")?;
    assert_eq!(idempotent.decoded, Some(b'p'));
    assert_eq!(idempotent.before.registers.data_pointer, IDEMPOTENT_SITE);
    assert_eq!(
        idempotent.memory_reads.data,
        Some(ProfileMemoryRead {
            address: IDEMPOTENT_SITE,
            value: IDEMPOTENT_WORD,
        })
    );
    assert_eq!(idempotent.after.registers.accumulator, IDEMPOTENT_WORD);
    assert!(idempotent.memory_delta.data.is_none());
    assert_eq!(vm.memory_word(IDEMPOTENT_SITE), Ok(IDEMPOTENT_WORD));
    let admitted = verify_source_code_cell_trace(
        profile,
        &source,
        &[],
        5,
        IDEMPOTENT_SITE,
    )
    .map_err(|error| format!("idempotent code write: {error:?}"))?;
    assert_eq!(admitted.events, [CodeCellEvent::DataWrite {
        before: IDEMPOTENT_WORD,
        after: IDEMPOTENT_WORD,
    }]);
    assert_eq!(admitted.schedule.data_writes, 1);
    assert_eq!(admitted.schedule.fetches, 0);
    assert_eq!(admitted.final_word, IDEMPOTENT_WORD);
    assert_eq!(admitted.outcome, outcome);
    let mut disabled_store = source.clone();
    *disabled_store.get_mut(3).ok_or("missing writer")? = encoded(3, b'o')?;
    assert_eq!(
        verify_source_code_cell_trace(
            profile,
            &disabled_store,
            &[],
            5,
            IDEMPOTENT_SITE,
        ),
        Err(SourceCodeCellTraceError::MissingEffect),
        "no changed-value delta cannot substitute for a reached p",
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "source-loaded first-effect XLAT2 and bounded refusal checks"
)]
fn first_xlat2_and_missing_effect_are_distinct() -> Result<(), String> {
    let profile = current_profile();
    let first = encoded(0, b'i')?;
    let target = usize::from(first);
    let mut source = (0..=target + 1)
        .map(|site| {
            encoded(
                u32::try_from(site).map_err(|error| error.to_string())?,
                b'o',
            )
        })
        .collect::<Result<Vec<_>, _>>()?;
    *source.get_mut(0).ok_or("missing C0")? = first;
    *source.get_mut(target + 1).ok_or("missing halt")? = encoded(
        u32::try_from(target + 1).map_err(|error| error.to_string())?,
        b'v',
    )?;
    let site = u32::from(first);
    let admitted =
        verify_source_code_cell_trace(profile, &source, &[], 2, site)
            .map_err(|error| format!("first-effect XLAT2: {error:?}"))?;
    assert_eq!(admitted.events, [CodeCellEvent::JumpTargetEncryption]);
    assert_eq!(admitted.schedule.target_encryptions, 1);
    assert_eq!(admitted.schedule.fetches, 0);
    assert_eq!(
        verify_source_code_cell_trace(profile, &source, &[], 1, site),
        Ok(layout::SourceCodeCellTrace {
            outcome: RunOutcome::BudgetExhausted { steps: 1 },
            ..admitted
        }),
    );
    // C1 is neither fetched nor overwritten in the two-step guest.
    let untouched = 1u32;
    assert_eq!(
        verify_source_code_cell_trace(profile, &source, &[], 1, untouched),
        Err(SourceCodeCellTraceError::MissingEffect),
    );
    assert_eq!(
        verify_source_code_cell_trace(profile, &source, &[], 0, site),
        Err(SourceCodeCellTraceError::InvalidBound),
    );
    assert_eq!(
        verify_source_code_cell_trace(profile, &source, &[], 513, site),
        Err(SourceCodeCellTraceError::InvalidBound),
    );
    Ok(())
}

/// A real source-loaded `i` skips the intentionally corrupted C41, then a
/// later `j` aligns C and D so p or * writes its *own* fetched instruction.
/// The VM must encrypt the resulting data word, not the original source byte.
fn source_with_self_alias(
    opcode: u8,
    entry: u32,
    self_site: u32,
    operand_site: u32,
) -> Result<Vec<u8>, String> {
    let len =
        usize::try_from(self_site + 2).map_err(|error| error.to_string())?;
    let mut source = (0..u32::try_from(len)
        .map_err(|error| error.to_string())?)
        .map(|site| encoded(site, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    for (site, operation) in [
        (0, b'j'),
        (1, b'p'),
        (2, b'i'),
        (self_site - 1, b'j'),
        (self_site, opcode),
        (self_site + 1, b'v'),
    ] {
        *source
            .get_mut(usize::try_from(site).map_err(|error| error.to_string())?)
            .ok_or("missing code site")? = encoded(site, operation)?;
    }
    for (site, value) in
        [(41, 40), (42, entry - 1), (operand_site, self_site - 1)]
    {
        *source
            .get_mut(usize::try_from(site).map_err(|error| error.to_string())?)
            .ok_or("missing source operand")? =
            u8::try_from(value).map_err(|error| error.to_string())?;
    }
    Ok(source)
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real same-step guest self-alias and exact journal evidence"
)]
fn source_loaded_fetch_and_self_write_preserves_real_event_order()
-> Result<(), String> {
    // Both paths avoid fetching overwritten M41, then align D with C.
    // p uses the previous p's all-one-trit accumulator to write unchanged
    // M84=72; * rotates M122=105 into the graphical word 35.
    for profile in [current_profile(), historical_profile()] {
        for (opcode, entry, site, data_site, expected_written) in
            [(b'p', 76, 84, 50, 72), (b'*', 92, 122, 72, 35)]
        {
            let source =
                source_with_self_alias(opcode, entry, site, data_site)?;
            let initial_byte = *source
                .get(usize::try_from(site).map_err(|error| error.to_string())?)
                .ok_or("missing self-alias byte")?;
            let initial = u32::from(initial_byte);
            let mut vm =
                ProfileMachine::from_source(profile, &source, Vec::new())
                    .map_err(|error| {
                        format!("source opcode {opcode}: {error:?}")
                    })?;
            let mut steps = Vec::new();
            let count = usize::try_from(site - entry + 5)
                .map_err(|error| error.to_string())?;
            let outcome = vm
                .run_traced(count, &mut |step| steps.push(*step))
                .map_err(|error| {
                format!("step opcode {opcode}: {error:?}")
            })?;
            assert_eq!(outcome, RunOutcome::Terminated {
                reason: malbolge::Termination::HaltInstruction,
                steps: count,
            });
            let step = steps.get(count - 2).ok_or("missing alias step")?;
            assert_eq!(step.before.registers.code_pointer, site);
            assert_eq!(step.before.registers.data_pointer, site);
            assert_eq!(step.decoded, Some(opcode));
            assert_eq!(step.fetched_cell, Some(initial));
            assert_eq!(
                step.memory_reads.data,
                Some(ProfileMemoryRead {
                    address: site,
                    value: initial,
                })
            );
            assert_eq!(step.after.registers.accumulator, expected_written);
            assert_eq!(
                step.memory_delta.data, None,
                "self-alias data writes are folded into the net XLAT2 delta",
            );
            let encrypted = malbolge::encrypt_profile_cell(expected_written)
                .ok_or("expected graphical data-write result")?;
            assert_eq!(
                step.memory_delta.encryption,
                Some(malbolge::ProfileMemoryWrite {
                    address: site,
                    before: initial,
                    after: encrypted,
                }),
            );
            assert_eq!(vm.memory_word(site), Ok(encrypted));
            let admitted = verify_source_code_cell_trace(
                profile,
                &source,
                &[],
                count,
                site,
            )
            .map_err(|error| format!("same-step alias: {error:?}"))?;
            assert_eq!(admitted.events, [CodeCellEvent::FetchSelfWrite {
                opcode,
                after: expected_written,
            }]);
            assert_eq!(admitted.schedule.fetches, 1);
            assert_eq!(admitted.schedule.data_writes, 1);
            assert_eq!(admitted.schedule.target_encryptions, 0);
            assert_eq!(
                admitted.final_word,
                vm.memory_word(site).map_err(|error| error.to_string())?
            );
            assert_eq!(admitted.outcome, outcome);
            assert_eq!(
                admit_code_cell_schedule(
                    profile,
                    site,
                    initial_byte,
                    &admitted.events
                ),
                Ok(admitted.schedule),
            );
            assert_eq!(
                encode_code_cell_schedule(profile, site, &admitted.events),
                Ok(admitted.schedule),
            );
            assert_eq!(
                admit_code_cell_schedule(profile, site, initial_byte, &[
                    CodeCellEvent::FetchSelfWrite {
                        opcode: b'j',
                        after: expected_written
                    }
                ],),
                Err(CodeCellScheduleError::DecodeMismatch { event: 0 }),
            );
            for (after, expected) in [
                (8, CodeCellScheduleError::InvalidEncryptionTarget {
                    event: 0,
                }),
                (
                    profile.memory_words(),
                    CodeCellScheduleError::InvalidDataWord { event: 0 },
                ),
            ] {
                assert_eq!(
                    admit_code_cell_schedule(profile, site, initial_byte, &[
                        CodeCellEvent::FetchSelfWrite { opcode, after }
                    ],),
                    Err(expected),
                );
            }
            // A plain fetch loses the * data write, so it cannot reproduce
            // the real encrypted code word even though its opcode is correct.
            let false_fetch =
                admit_code_cell_schedule(profile, site, initial_byte, &[
                    CodeCellEvent::Fetch(
                        layout::CodeVisitRequirement::Decoded(opcode),
                    ),
                ])
                .map_err(|error| format!("unlinked fetch: {error:?}"))?;
            assert_eq!(false_fetch.data_writes, 0);
            if opcode == b'*' {
                assert_ne!(false_fetch.final_cell, admitted.final_word);
            }
        }
    }
    Ok(())
}
