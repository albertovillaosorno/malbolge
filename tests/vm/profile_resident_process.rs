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
//   - Process-transport regressions for the resident profile backend adapter.
// - Must-Not:
//   - Require accelerator hardware or weaken safe-Rust fallback semantics.
// - Allows:
//   - Inputs: validated repository Python and derived profile requests.
//   - Outputs: backend/fallback origin and complete profile checkpoint
//     equality.
//   - Side effects: short-lived repository-local synthetic child processes.
// - Split-When:
//   - Concrete accelerator worker lifecycle needs independent evidence.
// - Merge-When:
//   - Process adapter behavior is fully covered by another VM integration
//     suite.
// - Summary:
//   - Proves MBPRN2 child-process transport independently of CUDA availability.
// - Description:
//   - Exercises accepted, unavailable, and oversized child responses.
// - Usage:
//   - Composed by `tests/vm.rs` under the standard VM integration target.
// - Defaults:
//   - Synthetic workers never import accelerator packages or use device APIs.
//

//! Resident profile process transport integration tests.

use std::ffi::OsString;
use std::path::Path;

use malbolge::{
    BatchExecutionOrigin, ProfileBatchRequest, ProfileBatchResult,
    ProfileMachine, ProfileResidentProcessTransport,
    ProfileResidentTransportBackend, current_profile, execute_profile_batch,
    execute_profile_batch_with_backend_report,
    verify_minimum_initial_halt_profile_width,
};

use crate::{TestResult, check_equal, normalize_result, validation_python};

const ECHO_WORKER: &str = r#"
import sys

data = sys.stdin.buffer.read()

def u32(offset):
    return int.from_bytes(data[offset:offset + 4], "little")

def pack(*values):
    return b"".join(value.to_bytes(4, "little") for value in values)

if data[:8] != b"MBPRN2\x00\x00" or u32(32) != 1:
    raise SystemExit(2)
memory_words = u32(16)
request = 36
accumulator = u32(request)
code_pointer = u32(request + 4)
data_pointer = u32(request + 8)
input_len = u32(request + 12)
input_consumed = u32(request + 16)
output_len = u32(request + 20)
step_budget = u32(request + 24)
termination = u32(request + 28)
if input_len != 0 or output_len != 0 or step_budget != 0 or termination != 0:
    raise SystemExit(3)
memory_start = request + 32
memory_end = memory_start + memory_words * 4
memory = data[memory_start:memory_end]
if len(memory) != memory_words * 4 or len(data) != memory_end:
    raise SystemExit(4)
response = b"MBPRN2\x00\x00" + pack(0, 1)
response += pack(
    0, 0, accumulator, code_pointer, data_pointer, input_consumed,
    0, 0, 0, 0, 0,
)
response += memory
sys.stdout.buffer.write(response)
"#;

const OVERSIZED_WORKER: &str = r#"
import sys
sys.stdin.buffer.read()
sys.stdout.buffer.write(b"x" * 300000)
sys.stdout.buffer.flush()
"#;

const UNAVAILABLE_WORKER: &str = r#"
import sys
sys.stdin.buffer.read()
def pack(*values):
    return b"".join(value.to_bytes(4, "little") for value in values)
sys.stdout.buffer.write(b"MBPRN2\x00\x00" + pack(1, 0))
"#;

#[test]
fn process_backend_accepts_bounded_derived_completion() -> TestResult {
    let request = derived_zero_step_request()?;
    let expected = execute_profile_batch(vec![request.clone()]);
    let mut backend = python_backend(ECHO_WORKER);
    let (observed, report) =
        execute_profile_batch_with_backend_report(vec![request], &mut backend);
    check_equal(
        &report.origins(),
        &(&[BatchExecutionOrigin::Backend][..]),
        "resident process accepted origin",
    )?;
    compare_single(&observed, &expected, "resident process accepted state")
}

#[test]
fn process_backend_bounds_child_response_before_decode() -> TestResult {
    let request = derived_zero_step_request()?;
    let expected = execute_profile_batch(vec![request.clone()]);
    let mut backend = python_backend(OVERSIZED_WORKER);
    let (observed, report) =
        execute_profile_batch_with_backend_report(vec![request], &mut backend);
    check_equal(
        &report.origins(),
        &(&[BatchExecutionOrigin::SafeRustFallback][..]),
        "resident process oversized origin",
    )?;
    compare_single(&observed, &expected, "resident process oversized state")
}

#[test]
fn process_backend_treats_explicit_unavailable_as_fallback() -> TestResult {
    let request = derived_zero_step_request()?;
    let expected = execute_profile_batch(vec![request.clone()]);
    let mut backend = python_backend(UNAVAILABLE_WORKER);
    let (observed, report) =
        execute_profile_batch_with_backend_report(vec![request], &mut backend);
    check_equal(
        &report.origins(),
        &(&[BatchExecutionOrigin::SafeRustFallback][..]),
        "resident process unavailable origin",
    )?;
    compare_single(&observed, &expected, "resident process unavailable state")
}

fn compare_single(
    observed: &[ProfileBatchResult],
    expected: &[ProfileBatchResult],
    context: &str,
) -> TestResult {
    let actual = observed
        .first()
        .ok_or_else(|| format!("{context}: observed result missing"))?;
    let oracle = expected
        .first()
        .ok_or_else(|| format!("{context}: expected result missing"))?;
    check_equal(&actual.error(), &oracle.error(), context)?;
    check_equal(&actual.outcome(), &oracle.outcome(), context)?;
    let observed_state =
        actual
            .machine()
            .map(ProfileMachine::snapshot_state)
            .ok_or_else(|| format!("{context}: observed machine missing"))?;
    let expected_state =
        oracle
            .machine()
            .map(ProfileMachine::snapshot_state)
            .ok_or_else(|| format!("{context}: expected machine missing"))?;
    check_equal(&observed_state, &expected_state, context)
}

fn derived_zero_step_request() -> TestResult<ProfileBatchRequest> {
    let verified = normalize_result(
        verify_minimum_initial_halt_profile_width(current_profile(), b"QP"),
    )?;
    let machine = normalize_result(ProfileMachine::from_verified_source(
        &verified,
        Vec::new(),
    ))?;
    Ok(ProfileBatchRequest::from_machine(machine, 0))
}

fn python_backend(
    script: &str,
) -> ProfileResidentTransportBackend<ProfileResidentProcessTransport> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let transport =
        ProfileResidentProcessTransport::new(validation_python(root))
            .argument(OsString::from("-c"))
            .argument(OsString::from(script));
    ProfileResidentTransportBackend::new(transport)
}
