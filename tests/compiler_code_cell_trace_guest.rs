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
    CodeCellEvent, SourceCodeCellTraceError, verify_source_code_cell_trace,
};
use malbolge::{
    ProfileMachine, ProfileMemoryRead, RunOutcome, current_profile,
    decode_profile_instruction,
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
