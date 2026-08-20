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
//   - Integration evidence for the standard-library timing capability
//     transport.
// - Must-Not:
//   - Assert a wall-clock epoch or require positive blocking sleeps in tests.
// - Allows:
//   - Inputs: canonical timing frames and one system timing transport instance.
//   - Outputs: monotonic/result/status assertions through the public
//     dispatcher.
//   - Side effects: monotonic observation and zero/nonblocking sleep requests.
// - Split-When:
//   - Another production host timing runtime requires separate integration.
// - Merge-When:
//   - Timing transport evidence becomes part of runner-level integration tests.
// - Summary:
//   - Exercises the real synchronous timing adapter through semantic dispatch.
// - Description:
//   - Proves local monotonicity and zero/nonblocking sleep behavior without
//     relying on wall-clock values or flaky elapsed-time thresholds.
// - Usage:
//   - Composed by the Cargo VM integration-test target.
// - Defaults:
//   - Only zero-duration blocking sleep is allowed in this test process.
//

//! Integration tests for the standard-library timing capability transport.

use malbolge::{
    HOST_CALL_FLAG_NONBLOCKING, HOST_CAPABILITY_ABI_VERSION,
    HOST_MONOTONIC_TIME_CAPABILITY_ID, HOST_MONOTONIC_TIME_V1_OPERATION,
    HOST_MONOTONIC_TIME_V1_VERSION, HOST_SLEEP_CAPABILITY_ID,
    HOST_SLEEP_V1_OPERATION, HOST_SLEEP_V1_VERSION,
    HostBuiltinCapabilityAvailability, HostCapabilityAvailability,
    HostCapabilityDescriptor, HostCapabilityFrame, HostCapabilityStatus,
    SystemTimingHostCapabilityTransport, decode_host_monotonic_time_v1_result,
    dispatch_builtin_host_capability, encode_host_sleep_v1_request,
    host_builtin_capability_registry,
};

use super::{TestResult, check_equal};

const MEMORY_SIZE: usize = 64;
const REQUEST_OFFSET: u64 = 8;
const REQUEST_START: usize = 8;
const REQUEST_END: usize = 16;
const RESULT_OFFSET: u64 = 24;
const RESULT_START: usize = 24;
const RESULT_END: usize = 32;

const fn registry() -> [HostCapabilityDescriptor; 4] {
    host_builtin_capability_registry(HostBuiltinCapabilityAvailability {
        monotonic_time: HostCapabilityAvailability::Available,
        relative_mouse: HostCapabilityAvailability::Unavailable,
        sleep: HostCapabilityAvailability::Available,
        telemetry: HostCapabilityAvailability::Unavailable,
    })
}

const fn clock_request(call_id: u64) -> HostCapabilityFrame {
    HostCapabilityFrame {
        abi_version: HOST_CAPABILITY_ABI_VERSION,
        call_id,
        capability_id: HOST_MONOTONIC_TIME_CAPABILITY_ID,
        capability_version: HOST_MONOTONIC_TIME_V1_VERSION,
        flags: 0,
        operation: HOST_MONOTONIC_TIME_V1_OPERATION,
        request_length: 0,
        request_offset: REQUEST_OFFSET,
        result_capacity: 8,
        result_length: 0,
        result_offset: RESULT_OFFSET,
        status: HostCapabilityStatus::Pending,
    }
}

const fn sleep_request(call_id: u64, flags: u32) -> HostCapabilityFrame {
    HostCapabilityFrame {
        abi_version: HOST_CAPABILITY_ABI_VERSION,
        call_id,
        capability_id: HOST_SLEEP_CAPABILITY_ID,
        capability_version: HOST_SLEEP_V1_VERSION,
        flags,
        operation: HOST_SLEEP_V1_OPERATION,
        request_length: 8,
        request_offset: REQUEST_OFFSET,
        result_capacity: 0,
        result_length: 0,
        result_offset: RESULT_OFFSET,
        status: HostCapabilityStatus::Pending,
    }
}

fn write_sleep_duration(memory: &mut [u8], nanoseconds: u64) -> TestResult {
    let destination = memory
        .get_mut(REQUEST_START..REQUEST_END)
        .ok_or_else(|| String::from("sleep request range unavailable"))?;
    destination.copy_from_slice(&encode_host_sleep_v1_request(nanoseconds));
    Ok(())
}

fn read_clock_result(memory: &[u8]) -> TestResult<u64> {
    let bytes = memory
        .get(RESULT_START..RESULT_END)
        .ok_or_else(|| String::from("clock result range unavailable"))?;
    decode_host_monotonic_time_v1_result(bytes)
        .map_err(|error| format!("clock result decode: {error:?}"))
}

#[test]
fn system_monotonic_observations_do_not_decrease() -> TestResult {
    let registry = registry();
    let mut transport = SystemTimingHostCapabilityTransport::new();
    let mut memory = [0u8; MEMORY_SIZE];
    let first = dispatch_builtin_host_capability(
        &registry,
        clock_request(1),
        &mut memory,
        &mut transport,
    )
    .map_err(|error| format!("first clock dispatch: {error:?}"))?;
    check_equal(
        &first.status,
        &HostCapabilityStatus::Complete,
        "first clock status",
    )?;
    let first_value = read_clock_result(&memory)?;

    let second = dispatch_builtin_host_capability(
        &registry,
        clock_request(2),
        &mut memory,
        &mut transport,
    )
    .map_err(|error| format!("second clock dispatch: {error:?}"))?;
    check_equal(
        &second.status,
        &HostCapabilityStatus::Complete,
        "second clock status",
    )?;
    let second_value = read_clock_result(&memory)?;
    if second_value < first_value {
        return Err(format!(
            "monotonic value regressed: {first_value} -> {second_value}"
        ));
    }
    Ok(())
}

#[test]
fn system_nonblocking_positive_sleep_would_block() -> TestResult {
    let registry = registry();
    let mut transport = SystemTimingHostCapabilityTransport::new();
    let mut memory = [0u8; MEMORY_SIZE];
    write_sleep_duration(&mut memory, 1_000_000_000)?;

    let response = dispatch_builtin_host_capability(
        &registry,
        sleep_request(3, HOST_CALL_FLAG_NONBLOCKING),
        &mut memory,
        &mut transport,
    )
    .map_err(|error| format!("nonblocking sleep dispatch: {error:?}"))?;

    check_equal(
        &response.status,
        &HostCapabilityStatus::WouldBlock,
        "nonblocking sleep status",
    )?;
    check_equal(&response.result_length, &0, "nonblocking sleep result")
}

#[test]
fn system_zero_duration_sleep_completes() -> TestResult {
    let registry = registry();
    let mut transport = SystemTimingHostCapabilityTransport::new();
    let mut memory = [0u8; MEMORY_SIZE];
    write_sleep_duration(&mut memory, 0)?;

    let response = dispatch_builtin_host_capability(
        &registry,
        sleep_request(4, 0),
        &mut memory,
        &mut transport,
    )
    .map_err(|error| format!("zero sleep dispatch: {error:?}"))?;

    check_equal(
        &response.status,
        &HostCapabilityStatus::Complete,
        "zero sleep status",
    )?;
    check_equal(&response.result_length, &0, "zero sleep result")
}
