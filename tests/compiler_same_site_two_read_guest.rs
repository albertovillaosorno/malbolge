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
//   - Two physical N15 byte reads at the same encrypted guest code site.
// - Must-Not:
//   - Claim a C23 EOF loop, conditional stop, mutable checksum or compiler.
// - Allows:
//   - Inputs: fixed 117-cell graphical source and five byte/EOF streams.
//   - Outputs: complete real C/D/code-encryption and two-input guest traces.
//   - Side effects: bounded in-memory normative N15 execution only.
// - Split-When:
//   - A general guest loop linker derives the real per-visit code lifecycle.
// - Merge-When:
//   - Source-linked C23 EOF iteration proves bounded and unbounded streams.
// - Summary:
//   - Re-enters one input code cell after two XLAT2 encryptions.

//! Physical fixed two-read example, not an EOF-terminated source-C loop.
//! C47 executes `/`, inert `P`, then `/` again. Two distinct data-driven
//! guest `i` backedges revisit C47, without host-directed control flow.

use malbolge::{
    ProfileMachine, ProfileStepTrace, RunOutcome, Termination, TraceInput,
    current_profile, decode_profile_instruction, encrypt_profile_cell,
    historical_profile,
};

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use layout::{
    CodeVisitEncodingError, CodeVisitRequirement, encode_code_visits,
};

const SOURCE_LENGTH: usize = 117;
const MAX_STEPS: usize = 128;
const INPUT_SITE: u32 = 47;

fn source() -> Result<Vec<u8>, String> {
    let mut source = (0..SOURCE_LENGTH)
        .map(|position| {
            let code =
                u32::try_from(position).map_err(|error| error.to_string())?;
            (33u8..=126)
                .find(|byte| {
                    decode_profile_instruction(u32::from(*byte), code)
                        == Some(b'o')
                })
                .ok_or_else(|| format!("no filler at C{position}"))
        })
        .collect::<Result<Vec<_>, _>>()?;
    for (position, decoded) in [
        (47usize, b'/'),
        (48, b'j'),
        (49, b'i'),
        (73, b'j'),
        (74, b'j'),
        (75, b'i'),
        (116, b'v'),
    ] {
        let code =
            u32::try_from(position).map_err(|error| error.to_string())?;
        let encoded = (33u8..=126)
            .find(|byte| {
                decode_profile_instruction(u32::from(*byte), code)
                    == Some(decoded)
            })
            .ok_or_else(|| format!("no {decoded} encoding at C{position}"))?;
        let cell = source
            .get_mut(position)
            .ok_or_else(|| format!("missing C{position}"))?;
        *cell = encoded;
    }
    // Derive the third-visit input phase from the same physical XLAT2 rule
    // used by the bounded EOF source builder; this does not select a path.
    let input_cell = source
        .get_mut(
            usize::try_from(INPUT_SITE).map_err(|error| error.to_string())?,
        )
        .ok_or("input code cell outside source")?;
    *input_cell = encode_code_visits(current_profile(), INPUT_SITE, &[
        CodeVisitRequirement::Decoded(b'/'),
        CodeVisitRequirement::Inert,
        CodeVisitRequirement::Decoded(b'/'),
    ])
    .map_err(|error| format!("input revisit encoding: {error:?}"))?;
    // All five cells are loader-valid *skipped* source bytes; the second
    // return target is reached through two genuine data pointer resets.
    for (position, value) in
        [(66usize, 109u8), (87, 46), (91, 65), (110, 46), (113, 115)]
    {
        let cell = source
            .get_mut(position)
            .ok_or_else(|| format!("missing M{position}"))?;
        *cell = value;
    }
    Ok(source)
}

fn expected_code_path() -> Vec<u32> {
    let mut positions = (0..=49).collect::<Vec<u32>>();
    positions.extend(47..=49);
    positions.extend(73..=75);
    positions.extend(47..=49);
    positions.push(116);
    positions
}

fn expected_data_path() -> Vec<u32> {
    let mut positions = (0..=48).collect::<Vec<u32>>();
    positions.extend([87, 88, 89, 90, 91, 66, 110, 111, 112, 113, 114]);
    positions
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "two complete real machine traces on five frozen input streams"
)]
fn two_real_reads_revisit_one_graphical_input_site_after_two_encryptions()
-> Result<(), String> {
    let code = source()?;
    let path = expected_code_path();
    let first_code = u32::from(*code.get(47).ok_or("missing input code")?);
    let once = encrypt_profile_cell(first_code)
        .ok_or("first input source encryption invalid")?;
    let twice = encrypt_profile_cell(once)
        .ok_or("second input source encryption invalid")?;
    assert_eq!([first_code, once, twice], [70, 74, 70]);
    assert_eq!(path.len(), 60);
    for profile in [current_profile(), historical_profile()] {
        for bytes in [vec![], vec![0], vec![0x80], vec![0xff], vec![
            0x01, 0x02, 0x03,
        ]] {
            let mut vm =
                ProfileMachine::from_source(profile, &code, bytes.clone())
                    .map_err(|error| error.to_string())?;
            let mut traces = Vec::<ProfileStepTrace>::new();
            let outcome = vm
                .run_traced(MAX_STEPS, &mut |step| traces.push(*step))
                .map_err(|error| error.to_string())?;
            assert_eq!(outcome, RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: path.len(),
            });
            let actual_path = traces
                .iter()
                .map(|step| step.before.registers.code_pointer)
                .collect::<Vec<_>>();
            assert_eq!(actual_path, path);
            assert_eq!(
                traces
                    .iter()
                    .map(|step| step.before.registers.data_pointer)
                    .collect::<Vec<_>>(),
                expected_data_path(),
            );
            let expected_inputs =
                [bytes.first().copied(), bytes.get(1).copied()].map(|byte| {
                    byte.map_or(TraceInput::EndOfInput, TraceInput::Byte)
                });
            let actual_inputs = traces
                .iter()
                .filter_map(|step| step.input)
                .collect::<Vec<_>>();
            assert_eq!(actual_inputs, expected_inputs);
            assert_eq!(vm.input_consumed(), bytes.len().min(2));
            assert_eq!(vm.output(), []);
            let first = traces.get(47).ok_or("no first physical input")?;
            let intermediate = traces.get(50).ok_or("no inert second visit")?;
            let last = traces.get(56).ok_or("no second physical input")?;
            assert_eq!(
                [first, intermediate, last]
                    .map(|step| step.before.registers.code_pointer),
                [INPUT_SITE; 3],
            );
            assert_eq!([first.decoded, intermediate.decoded, last.decoded], [
                Some(b'/'),
                Some(b'P'),
                Some(b'/'),
            ]);
            assert_eq!(
                [
                    first.fetched_cell,
                    intermediate.fetched_cell,
                    last.fetched_cell
                ],
                [Some(first_code), Some(once), Some(twice),]
            );
            for (index, value) in [(47usize, once), (50, twice), (56, once)] {
                let step = traces.get(index).ok_or("missing XLAT2 pass")?;
                let encrypted = step
                    .memory_delta
                    .encryption
                    .ok_or("input code must be XLAT2 encrypted")?;
                assert_eq!(encrypted.address, INPUT_SITE);
                assert_eq!(encrypted.after, value);
            }
            for (index, target, source_word) in
                [(49usize, INPUT_SITE, 46u32), (55usize, INPUT_SITE, 46)]
            {
                let jump = traces.get(index).ok_or("missing guest jump")?;
                assert_eq!(jump.decoded, Some(b'i'));
                assert_eq!(
                    jump.memory_reads.data.map(|read| read.value),
                    Some(source_word),
                );
                assert_eq!(jump.after.registers.code_pointer, target);
            }
            for (position, value) in
                [(66u32, 109u32), (87, 46), (91, 65), (110, 46), (113, 115)]
            {
                assert_eq!(vm.memory_word(position), Ok(value));
            }
            assert_eq!(vm.memory_word(INPUT_SITE), Ok(once));
        }
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "independent XLAT2 phase assertions"
)]
fn checked_code_visit_encoder_covers_all_input_revisit_phases()
-> Result<(), String> {
    let profile = current_profile();
    let triple = [
        CodeVisitRequirement::Decoded(b'/'),
        CodeVisitRequirement::Inert,
        CodeVisitRequirement::Decoded(b'/'),
    ];
    let mut supported = Vec::new();
    for position in 0..94u32 {
        let encoded = encode_code_visits(profile, position, &triple);
        // Independent reverse lookup of the initial code byte; do not
        // trust the new encoder for the following two decoder observations.
        let input_cell = (33u8..=126)
            .find(|byte| {
                decode_profile_instruction(u32::from(*byte), position)
                    == Some(b'/')
            })
            .ok_or_else(|| format!("missing input at phase {position}"))?;
        let first = encrypt_profile_cell(u32::from(input_cell))
            .ok_or("missing first self-encryption")?;
        let second = encrypt_profile_cell(first)
            .ok_or("missing second self-encryption")?;
        let actual = (
            decode_profile_instruction(first, position),
            decode_profile_instruction(second, position),
        );
        if !matches!(
            actual.0,
            Some(b'o' | b'i' | b'j' | b'p' | b'*' | b'/' | b'<' | b'v')
        ) && actual.1 == Some(b'/')
        {
            supported.push(position);
            assert_eq!(encoded, Ok(input_cell));
        } else {
            assert_eq!(
                encoded,
                Err(CodeVisitEncodingError::NoEncoding { position })
            );
        }
        assert_eq!(
            encode_code_visits(profile, position, &[
                CodeVisitRequirement::Decoded(b'/'),
                CodeVisitRequirement::Decoded(b'/'),
            ]),
            Err(CodeVisitEncodingError::NoEncoding { position })
        );
    }
    assert_eq!(supported, [43, 47]);
    Ok(())
}

#[test]
fn checked_code_visit_encoder_rejects_invalid_sequences() {
    let profile = current_profile();
    let triple = [
        CodeVisitRequirement::Decoded(b'/'),
        CodeVisitRequirement::Inert,
        CodeVisitRequirement::Decoded(b'/'),
    ];
    assert_eq!(
        encode_code_visits(profile, 47, &[]),
        Err(CodeVisitEncodingError::Empty)
    );
    assert_eq!(
        encode_code_visits(profile, 47, &triple.repeat(6)),
        Err(CodeVisitEncodingError::TooMany)
    );
    assert_eq!(
        encode_code_visits(profile, profile.memory_words(), &triple),
        Err(CodeVisitEncodingError::AddressOutOfBounds)
    );
    assert_eq!(
        encode_code_visits(profile, 47, &[CodeVisitRequirement::Inert]),
        Err(CodeVisitEncodingError::InvalidInitialOpcode)
    );
    assert_eq!(
        encode_code_visits(profile, 47, &[
            CodeVisitRequirement::Decoded(b'i'),
            CodeVisitRequirement::Inert,
        ]),
        Err(CodeVisitEncodingError::NoSelfEncryption { visit: 0 })
    );
}
