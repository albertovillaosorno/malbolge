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
//   - Structural admission of original request capacities at response framing.
// - Must-Not:
//   - Replace process-call semantic verification or child-host integration.
// - Allows:
//   - Inputs: in-process requests with contradictory capacity declarations.
//   - Outputs: typed shape rejection before response encoding or decoding.
//   - Side effects: none.
// - Split-When:
//   - A new response protocol has distinct request-shape assumptions.
// - Merge-When:
//   - Request-shape admission is moved to one common response codec.
// - Summary:
//   - Rejects forged original request capacities at every response boundary.
// - Description:
//   - Uses exact valid response bytes to isolate original request corruption.
// - Usage:
//   - Included by the native process-call wire module during unit tests.
// - Defaults:
//   - All capacity dimensions must agree with the original owned buffers.
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
