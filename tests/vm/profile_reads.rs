// File:
//   - profile_reads.rs
// Path:
//   - tests/vm/profile_reads.rs
//
// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Path-Rule:
//   - All paths in this header are repository-root relative.
//
// Boundary-Contract:
// - Owns:
//   - Semantic profile-memory read-role conformance for every instruction
//   - family.
// - Must-Not:
//   - Infer private transition plans or count diagnostic/instrumentation reads.
// - Allows:
//   - Inputs: public profile state construction and traced single-step
//   - execution.
//   - Outputs: exact fetch/data/encryption read records, including rejection.
//   - Side effects: test-process allocation only.
// - Split-When:
//   - Split when a future profile schema adds another semantic memory-read
//   - role.
// - Merge-When:
//   - Merge when read roles become ordinary profile-tracing conformance
//   - fixtures.
// - Summary:
//   - Proves trace read roles come from the normative profile transition
//   - engine.
// - Description:
//   - Covers all instruction families plus rejected jump encryption atomically.
// - Usage:
//   - Composed by `tests/vm.rs` under the ordinary VM integration-test target.
// - Defaults:
//   - Fetch always occurs for live state; data/encryption exist only when read.
//
// Related documents:
// - docs/technical/runtime/vm/safe-rust-malbolge-vm.md
// - vm/src/profile_trace.rs
//
// Large file:
//   - false
//

//! Exact semantic memory-read role fixtures for current-profile execution.

use malbolge::{
    ProfileMachine, ProfileMachineError, ProfileMachineIoState,
    ProfileMachineState, ProfileMemoryRead, ProfileMemoryReads,
    ProfileRegisters, ProfileStepTrace, current_profile,
};

use super::{TestResult, check_equal, normalize_result};

const ACCUMULATOR: u32 = 7;
const BASE_SOURCE: &[u8] = b"QP";
const CODE_ADDRESS: u32 = 0;
const DATA_ADDRESS: u32 = 1;
const DATA_VALUE: u32 = 2;
const ENCRYPTION_TARGET: u32 = 2;
const GRAPHICAL_TARGET: u32 = 68;
const INPUT: u8 = 0x41;

const CASES: &[ReadCase] = &[
    ReadCase {
        cell: b'>',
        data_read: true,
        encryption_address: Some(CODE_ADDRESS),
        rejection: false,
    },
    ReadCase {
        cell: b'Q',
        data_read: false,
        encryption_address: None,
        rejection: false,
    },
    ReadCase {
        cell: b'c',
        data_read: false,
        encryption_address: Some(CODE_ADDRESS),
        rejection: false,
    },
    ReadCase {
        cell: b'b',
        data_read: true,
        encryption_address: Some(ENCRYPTION_TARGET),
        rejection: false,
    },
    ReadCase {
        cell: b'(',
        data_read: true,
        encryption_address: Some(CODE_ADDRESS),
        rejection: false,
    },
    ReadCase {
        cell: b'D',
        data_read: false,
        encryption_address: Some(CODE_ADDRESS),
        rejection: false,
    },
    ReadCase {
        cell: b'u',
        data_read: false,
        encryption_address: Some(CODE_ADDRESS),
        rejection: false,
    },
    ReadCase {
        cell: b'\'',
        data_read: true,
        encryption_address: Some(CODE_ADDRESS),
        rejection: false,
    },
    ReadCase {
        cell: b'b',
        data_read: true,
        encryption_address: Some(ENCRYPTION_TARGET),
        rejection: true,
    },
];

#[derive(Clone, Copy, Debug)]
struct ReadCase {
    cell: u8,
    data_read: bool,
    encryption_address: Option<u32>,
    rejection: bool,
}

fn case_machine(case: ReadCase) -> TestResult<ProfileMachine> {
    let base = normalize_result(ProfileMachine::from_source(
        current_profile(),
        BASE_SOURCE,
        Vec::new(),
    ))?;
    let mut memory = base.snapshot_state().memory().to_vec();
    let instruction = memory
        .get_mut(
            usize::try_from(CODE_ADDRESS).map_err(|error| error.to_string())?,
        )
        .ok_or_else(|| String::from("missing read-role instruction cell"))?;
    *instruction = u32::from(case.cell);
    let data = memory
        .get_mut(
            usize::try_from(DATA_ADDRESS).map_err(|error| error.to_string())?,
        )
        .ok_or_else(|| String::from("missing read-role data cell"))?;
    *data = DATA_VALUE;
    let target = memory
        .get_mut(
            usize::try_from(ENCRYPTION_TARGET)
                .map_err(|error| error.to_string())?,
        )
        .ok_or_else(|| String::from("missing read-role encryption cell"))?;
    *target = if case.rejection {
        0
    } else {
        GRAPHICAL_TARGET
    };
    let io = normalize_result(ProfileMachineIoState::new(
        vec![INPUT],
        0,
        Vec::new(),
        None,
    ))?;
    let state = normalize_result(ProfileMachineState::new(
        current_profile(),
        memory,
        ProfileRegisters {
            accumulator: ACCUMULATOR,
            code_pointer: CODE_ADDRESS,
            data_pointer: DATA_ADDRESS,
        },
        io,
    ))?;
    Ok(ProfileMachine::from_snapshot(state))
}

fn expected_reads(case: ReadCase) -> ProfileMemoryReads {
    let data = case.data_read.then_some(ProfileMemoryRead {
        address: DATA_ADDRESS,
        value: DATA_VALUE,
    });
    let encryption = case.encryption_address.map(|address| ProfileMemoryRead {
        address,
        value: if address == CODE_ADDRESS {
            u32::from(case.cell)
        } else if case.rejection {
            0
        } else {
            GRAPHICAL_TARGET
        },
    });
    ProfileMemoryReads {
        data,
        encryption,
        fetch: Some(ProfileMemoryRead {
            address: CODE_ADDRESS,
            value: u32::from(case.cell),
        }),
    }
}

#[test]
fn current_instruction_families_report_exact_semantic_memory_reads()
-> TestResult {
    for case in CASES {
        let mut machine = case_machine(*case)?;
        let mut observed = None;
        let result = machine.step_traced(&mut |trace: &ProfileStepTrace| {
            observed = Some(trace.memory_reads);
        });
        if case.rejection {
            check_equal(
                &result,
                &Err(ProfileMachineError::InvalidEncryptionTarget {
                    pointer: ENCRYPTION_TARGET,
                    value: 0,
                }),
                "read-role rejected jump result",
            )?;
        } else {
            let _outcome = normalize_result(result)?;
        }
        let reads = observed.ok_or_else(|| {
            String::from("missing semantic memory-read trace")
        })?;
        let expected = expected_reads(*case);
        check_equal(&reads, &expected, "semantic memory-read roles")?;
        check_equal(
            &reads.read_count(),
            &expected.read_count(),
            "semantic memory-read count",
        )?;
    }
    Ok(())
}
