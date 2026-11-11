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
//   - Structural admission of original request capacities and progress.
// - Must-Not:
//   - Replace process-call semantic verification or child-host integration.
// - Allows:
//   - Inputs: inconsistent capacities/cursors or malformed wire requests.
//   - Outputs: typed shape rejection before response encoding or decoding.
//   - Side effects: none.
// - Split-When:
//   - A new response protocol has distinct request-shape assumptions.
// - Merge-When:
//   - Request-shape admission is moved to one common response codec.
// - Summary:
//   - Rejects forged original capacities and cursors at every wire seam.
// - Description:
//   - Uses exact valid frames to isolate original request corruption.
// - Usage:
//   - Included by the native process-call wire module during unit tests.
// - Defaults:
//   - Capacities must agree with buffers and progress must be in bounds.
//

//! Regression cases for response operations over unadmitted original requests.

#[test]
fn response_boundaries_reject_mismatched_original_request_capacities() -> Result<(), String> {
    use super::super::process_call::{
        NativeProcessCallRequest, NativeProcessCallResponse, NativeProcessCallState,
    };
    use super::{
        NativeExecutableMappingId, NativeProcessCallWireError, decode_native_process_call_response,
        encode_native_process_call_response, native_process_call_response_byte_limit,
    };

    let id = NativeExecutableMappingId::new(7)
        .ok_or_else(|| String::from("expected nonzero mapping id"))?;
    let state = NativeProcessCallState::from_raw([2, 1, 2], [0, 0], [0, 0, 0], 0);
    let memory = [4u32, 5];
    let input = [0x11u8];
    let output = [0x22u8, 0x33];
    let valid = NativeProcessCallRequest::new(id, state, 0, (&memory, &input, &output));
    let response =
        NativeProcessCallResponse::new(id, state, (memory.to_vec(), output.to_vec()), (0i32, true));
    let valid_bytes = encode_native_process_call_response(&valid, &response)
        .map_err(|error| format!("valid response: {error:?}"))?;

    for (corrupt, expected) in [
        (
            state.with_memory_words(3),
            NativeProcessCallWireError::MemoryLength,
        ),
        (
            state.with_input_len(2),
            NativeProcessCallWireError::InputLength,
        ),
        (
            state.with_output_capacity(3),
            NativeProcessCallWireError::OutputLength,
        ),
    ] {
        let request = NativeProcessCallRequest::new(id, corrupt, 0, (&memory, &input, &output));
        if native_process_call_response_byte_limit(&request) != Err(expected)
            || encode_native_process_call_response(&request, &response) != Err(expected)
            || decode_native_process_call_response(&valid_bytes, &request) != Err(expected)
        {
            return Err(format!(
                "response codec admitted forged original capacity: {expected:?}"
            ));
        }
    }
    Ok(())
}

#[test]
fn request_cursors_fail_closed_at_wire_admission() -> Result<(), String> {
    use super::super::process_call::{
        NativeProcessCallRequest, NativeProcessCallResponse, NativeProcessCallState,
    };
    use super::{
        NativeExecutableMappingId, NativeProcessCallWireError,
        decode_native_process_call_response, encode_native_process_call_request,
        encode_native_process_call_response, native_process_call_request_byte_len,
        native_process_call_response_byte_limit,
    };

    let id = NativeExecutableMappingId::new(11)
        .ok_or_else(|| String::from("expected nonzero mapping id"))?;
    let state = NativeProcessCallState::from_raw([2, 1, 2], [1, 2], [0, 0, 0], 0);
    let memory = [4u32, 5];
    let input = [0x11u8];
    let output = [0x22u8, 0x33];
    let valid = NativeProcessCallRequest::new(id, state, 0, (&memory, &input, &output));
    let response = NativeProcessCallResponse::new(
        id, state, (memory.to_vec(), output.to_vec()), (0i32, true),
    );
    let valid_response = encode_native_process_call_response(&valid, &response)
        .map_err(|error| format!("valid response: {error:?}"))?;

    for (corrupt, expected) in [
        (state.with_input_consumed(2), NativeProcessCallWireError::InputCursor),
        (state.with_output_len(3), NativeProcessCallWireError::OutputCursor),
        (state.with_input_consumed(u64::MAX), NativeProcessCallWireError::InputCursor),
        (state.with_output_len(u64::MAX), NativeProcessCallWireError::OutputCursor),
    ] {
        let request = NativeProcessCallRequest::new(id, corrupt, 0, (&memory, &input, &output));
        if native_process_call_request_byte_len(&request) != Err(expected)
            || encode_native_process_call_request(&request) != Err(expected)
            || native_process_call_response_byte_limit(&request) != Err(expected)
            || encode_native_process_call_response(&request, &response) != Err(expected)
            || decode_native_process_call_response(&valid_response, &request) != Err(expected)
        {
            return Err(format!("forged request cursor passed a wire seam: {expected:?}"));
        }
    }
    Ok(())
}

#[test]
fn raw_request_decoder_rejects_overrun_cursors() -> Result<(), String> {
    use super::super::process_call::{NativeProcessCallRequest, NativeProcessCallState};
    use super::{
        NativeExecutableMappingId, NativeProcessCallWireError,
        decode_native_process_call_request, encode_native_process_call_request,
    };

    let id = NativeExecutableMappingId::new(11)
        .ok_or_else(|| String::from("expected nonzero mapping id"))?;
    let state = NativeProcessCallState::from_raw([2, 1, 2], [1, 2], [0, 0, 0], 0);
    let memory = [4u32, 5];
    let input = [0x11u8];
    let output = [0x22u8, 0x33];
    let valid = NativeProcessCallRequest::new(id, state, 0, (&memory, &input, &output));
    let valid_frame = encode_native_process_call_request(&valid)
        .map_err(|error| format!("valid request: {error:?}"))?;
    if decode_native_process_call_request(&valid_frame) != Ok(valid) {
        return Err(String::from("exact-capacity progress must decode"));
    }
    for (offset, value, expected) in [
        (48usize, 2u64, NativeProcessCallWireError::InputCursor),
        (56usize, 3u64, NativeProcessCallWireError::OutputCursor),
        (48usize, u64::MAX, NativeProcessCallWireError::InputCursor),
        (56usize, u64::MAX, NativeProcessCallWireError::OutputCursor),
    ] {
        let mut forged = valid_frame.clone();
        let span = forged.get_mut(offset..offset + size_of::<u64>())
            .ok_or_else(|| String::from("fixed request layout drifted"))?;
        span.copy_from_slice(&value.to_le_bytes());
        let header = forged.get(..77)
            .ok_or_else(|| String::from("fixed request header missing"))?;
        if decode_native_process_call_request(&forged) != Err(expected)
            || decode_native_process_call_request(header) != Err(expected)
        {
            return Err(format!("forged request cursor decoded: {expected:?}"));
        }
    }
    Ok(())
}
