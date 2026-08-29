// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Pure Rust regressions for resident profile backend wire framing.
// - Must-Not:
//   - Spawn accelerator processes or treat wire geometry as semantic authority.
// - Allows:
//   - Inputs: small synthetic resident requests and response byte strings.
//   - Outputs: exact encoding and fail-closed decoding assertions.
//   - Side effects: none.
// - Split-When:
//   - Split when a new wire version gains an independent schema lifecycle.
// - Merge-When:
//   - Merge when another suite owns the exact MBPRN2 Rust contract boundary.
// - Summary:
//   - Proves resident profile wire framing independently of accelerator
//     hardware.
// - Description:
//   - Exercises homogeneous encoding and strict response framing.
// - Usage:
//   - Composed by `tests/vm.rs` on every Rust validation host.
// - Defaults:
//   - Five-trit synthetic geometry keeps byte fixtures deliberately small.
//

//! Transport-neutral resident profile wire contract regressions.

use malbolge::{
    PROFILE_RESIDENT_WIRE_MAGIC, ProfileResidentWireError,
    ProfileResidentWireGeometry, ProfileResidentWireRequest,
    ProfileResidentWireResponse, ProfileResidentWireTermination,
    decode_profile_resident_response, encode_profile_resident_batch,
    profile_resident_response_byte_limit,
};

use crate::{TestResult, check_equal, normalize_result};

const GEOMETRY: ProfileResidentWireGeometry = ProfileResidentWireGeometry {
    eof_word: 242,
    input_instruction: b'<',
    memory_words: 243,
    output_instruction: b'/',
    word_modulus: 243,
    word_trits: 5,
};
const RESPONSE_RESULTS: u32 = 0;

#[test]
fn resident_wire_decodes_complete_result_and_rejects_framing_drift()
-> TestResult {
    let mut response = Vec::new();
    response.extend_from_slice(&PROFILE_RESIDENT_WIRE_MAGIC);
    push_u32(&mut response, RESPONSE_RESULTS);
    push_u32(&mut response, 1);
    for value in [0, 0, 7, 2, 3, 1, 1, 0, 0, 0, 9] {
        push_u32(&mut response, value);
    }
    for value in 0u32..GEOMETRY.memory_words {
        push_u32(&mut response, value);
    }
    response.push(0x42);

    let decoded = normalize_result(decode_profile_resident_response(
        &response,
        GEOMETRY.memory_words,
    ))?;
    let ProfileResidentWireResponse::Results(results) = decoded else {
        return Err(String::from("resident wire result response missing"));
    };
    let result = results
        .first()
        .ok_or_else(|| String::from("resident wire result missing"))?;
    check_equal(&result.accumulator, &7u32, "resident wire accumulator")?;
    check_equal(&result.input_consumed, &1u32, "resident wire input cursor")?;
    check_equal(&result.output, &vec![0x42], "resident wire output")?;
    check_equal(
        &result.memory.len(),
        &243usize,
        "resident wire memory length",
    )?;

    let truncated = decode_profile_resident_response(
        response
            .get(..response.len().saturating_sub(1))
            .unwrap_or(&[]),
        GEOMETRY.memory_words,
    );
    check_equal(
        &truncated,
        &Err(ProfileResidentWireError::ReadFailure),
        "resident wire truncation",
    )?;
    response.push(0xff);
    check_equal(
        &decode_profile_resident_response(&response, GEOMETRY.memory_words),
        &Err(ProfileResidentWireError::TrailingResponse),
        "resident wire trailing byte",
    )
}

#[test]
fn resident_wire_response_limit_tracks_possible_output() -> TestResult {
    let memory = vec![0u32; 243];
    let admitted = request(&memory, GEOMETRY);
    check_equal(
        &normalize_result(profile_resident_response_byte_limit(&[admitted]))?,
        &1_042usize,
        "resident wire response byte limit",
    )?;
    let overflowing = ProfileResidentWireRequest {
        step_budget: usize::MAX,
        ..admitted
    };
    check_equal(
        &profile_resident_response_byte_limit(&[overflowing]),
        &Err(ProfileResidentWireError::CounterOverflow),
        "resident wire response capacity overflow",
    )
}

#[test]
fn resident_wire_encoder_rejects_mixed_geometry() -> TestResult {
    let memory = vec![0u32; 243];
    let first = request(&memory, GEOMETRY);
    let second_geometry = ProfileResidentWireGeometry {
        eof_word: 728,
        input_instruction: b'<',
        memory_words: 729,
        output_instruction: b'/',
        word_modulus: 729,
        word_trits: 6,
    };
    let second = ProfileResidentWireRequest {
        geometry: second_geometry,
        ..first
    };
    check_equal(
        &encode_profile_resident_batch(&[first, second]),
        &Err(ProfileResidentWireError::MixedGeometry),
        "resident wire mixed geometry",
    )
}

#[test]
fn resident_wire_encoder_uses_exact_geometry_and_request_fields() -> TestResult
{
    let memory = vec![0u32; 243];
    let encoded = normalize_result(encode_profile_resident_batch(&[request(
        &memory, GEOMETRY,
    )]))?;
    if !encoded.starts_with(&PROFILE_RESIDENT_WIRE_MAGIC) {
        return Err(String::from("resident wire request magic mismatch"));
    }
    let header = encoded
        .get(PROFILE_RESIDENT_WIRE_MAGIC.len()..)
        .ok_or_else(|| String::from("resident wire request header missing"))?;
    check_equal(
        &read_u32(header, 0)?,
        &GEOMETRY.eof_word,
        "resident wire EOF",
    )?;
    check_equal(
        &read_u32(header, 2)?,
        &GEOMETRY.memory_words,
        "resident wire memory words",
    )?;
    check_equal(&read_u32(header, 5)?, &5u32, "resident wire trits")?;
    check_equal(&read_u32(header, 6)?, &1u32, "resident wire count")
}

fn push_u32(bytes: &mut Vec<u8>, value: u32) {
    bytes.extend_from_slice(&value.to_le_bytes());
}

fn read_u32(bytes: &[u8], index: usize) -> TestResult<u32> {
    let start = index.saturating_mul(size_of::<u32>());
    let end = start.saturating_add(size_of::<u32>());
    let chunk = bytes
        .get(start..end)
        .ok_or_else(|| String::from("resident wire u32 missing"))?;
    let array = <[u8; size_of::<u32>()]>::try_from(chunk)
        .map_err(|error| format!("resident wire u32 shape: {error}"))?;
    Ok(u32::from_le_bytes(array))
}

const fn request(
    memory: &[u32],
    geometry: ProfileResidentWireGeometry,
) -> ProfileResidentWireRequest<'_> {
    ProfileResidentWireRequest {
        accumulator: 7,
        code_pointer: 2,
        data_pointer: 3,
        geometry,
        input: &[0xa5, 0x5a],
        input_consumed: 1,
        memory,
        output: &[0x42],
        step_budget: 9,
        termination: ProfileResidentWireTermination::None,
    }
}
