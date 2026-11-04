// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - LicenseRef-Proprietary
// Confidential:
//   - true
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Early structural cursor admission for untrusted MBNPC1 responses.
// - Must-Not:
//   - Replace native semantic verification or allocate executable memory.
// - Allows:
//   - Inputs: exact requests and forged full or truncated response frames.
//   - Outputs: typed cursor rejection before response payload decoding.
//   - Side effects: none.
// - Split-When:
//   - A new response wire version has distinct progress requirements.
// - Merge-When:
//   - Response and request wire tests share one boundary owner.
// - Summary:
//   - Rejects impossible response progress before request-sized allocations.
// - Description:
//   - Tests full frames and fixed headers with over-capacity cursors.
// - Usage:
//   - Included by the MBNPC1 codec test module.
// - Defaults:
//   - Exact-at-capacity progress remains admitted.
//
//! Early MBNPC1 response cursor admission against the original request.

#[test]
fn response_cursors_fail_before_request_sized_payload_reads() -> Result<(), String> {
    use super::super::process_call::{
        NativeProcessCallRequest, NativeProcessCallResponse, NativeProcessCallState,
    };
    use super::{
        NATIVE_PROCESS_CALL_RESPONSE_FIXED_BYTES, NativeExecutableMappingId,
        NativeProcessCallWireError, decode_native_process_call_response,
        encode_native_process_call_response,
    };

    let id = NativeExecutableMappingId::new(13)
        .ok_or_else(|| String::from("expected nonzero mapping id"))?;
    let state = NativeProcessCallState::from_raw([2, 1, 2], [1, 2], [1, 0, 1], 0);
    let memory = [4u32, 5];
    let input = [0x11u8];
    let output = [0x22u8, 0x33];
    let request = NativeProcessCallRequest::new(id, state, 0, (&memory, &input, &output));
    let response =
        NativeProcessCallResponse::new(id, state, (memory.to_vec(), output.to_vec()), (0i32, true));
    let valid = encode_native_process_call_response(&request, &response)
        .map_err(|error| format!("valid response: {error:?}"))?;
    if decode_native_process_call_response(&valid, &request) != Ok(response) {
        return Err(String::from("exact-capacity response progress must decode"));
    }

    // State fields in a response begin immediately after magic and mapping ID.
    for (offset, value, expected) in [
        (40usize, 2u64, NativeProcessCallWireError::InputCursor),
        (48usize, 3u64, NativeProcessCallWireError::OutputCursor),
        (40usize, u64::MAX, NativeProcessCallWireError::InputCursor),
        (48usize, u64::MAX, NativeProcessCallWireError::OutputCursor),
    ] {
        let mut forged = valid.clone();
        let span = forged
            .get_mut(offset..offset + size_of::<u64>())
            .ok_or_else(|| String::from("fixed response state layout drifted"))?;
        span.copy_from_slice(&value.to_le_bytes());
        let header = forged
            .get(..NATIVE_PROCESS_CALL_RESPONSE_FIXED_BYTES)
            .ok_or_else(|| String::from("fixed response header missing"))?;
        if decode_native_process_call_response(&forged, &request) != Err(expected)
            || decode_native_process_call_response(header, &request) != Err(expected)
        {
            return Err(format!("forged response progress decoded: {expected:?}"));
        }
        let forged_state = if offset == 40 {
            state.with_input_consumed(value)
        } else {
            state.with_output_len(value)
        };
        let forged_response = NativeProcessCallResponse::new(
            id,
            forged_state,
            (memory.to_vec(), output.to_vec()),
            (0i32, true),
        );
        if encode_native_process_call_response(&request, &forged_response) != Err(expected) {
            return Err(format!("forged response progress encoded: {expected:?}"));
        }
    }
    Ok(())
}
