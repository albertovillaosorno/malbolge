// File:
//   - profile_state.rs
// Path:
//   - tests/vm/profile_state.rs
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
//   - Validated profiled-state reconstruction and current pointer-wrap
//     evidence.
// - Must-Not:
//   - Depend on private VM decode/encryption helpers or admit unchecked state.
// - Allows:
//   - Inputs: public profile/state APIs and independent translation constants.
//   - Outputs: exact construction errors and one current max-address
//     transition.
//   - Side effects: test-process allocation of canonical profile memory images.
// - Split-When:
//   - Split when native deoptimization state requires a serialized wire format.
// - Merge-When:
//   - Merge when profile construction/state validation shares one test surface.
// - Summary:
//   - Proves fail-closed state reconstruction and current max-address wrap.
// - Description:
//   - Builds current state directly without bypassing profile-domain
//     validation.
// - Usage:
//   - Composed by `tests/vm.rs` under the normal VM integration target.
// - Defaults:
//   - State construction never truncates memory words or register values.
//
// Related documents:
// - docs/technical/runtime/vm/safe-rust-malbolge-vm.md
// - docs/technical/compatibility/scalable-malbolge-memory-model.md
//
// Large file:
//   - false

//! Validated state reconstruction and scalable pointer-wrap conformance.

use malbolge::{
    ProfileMachine, ProfileMachineError, ProfileRegisterName, ProfileRegisters,
    StepOutcome, current_profile, historical_profile,
};

use super::{TestResult, check_equal, normalize_result};

const GRAPHICAL_END: u8 = 126;
const GRAPHICAL_START: u8 = 33;
const TABLE_LEN: usize = 94;
const TEST_XLAT1: &[u8; TABLE_LEN] =
    b"+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA\"lI\
.v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha";
const TEST_XLAT2: &[u8; TABLE_LEN] =
    b"5z]&gqtyfr$(we4{WP)H-Zn,[%\\3dL+Q;>U!pJS72FhOA1C\
B6v^=I_0/8|jsb9m<.TVac`uY*MK'X~xDl}REokN:#?G\"i@";

fn exact_memory_words() -> TestResult<usize> {
    usize::try_from(historical_profile().memory_words()).map_err(|error| {
        format!("historical memory length conversion: {error}")
    })
}

fn noop_cell(pointer: u32) -> TestResult<u8> {
    let table_len = u32::try_from(TABLE_LEN)
        .map_err(|error| format!("decode table length conversion: {error}"))?;
    let phase = usize::try_from(pointer.rem_euclid(table_len))
        .map_err(|error| format!("decode phase conversion: {error}"))?;
    for byte in GRAPHICAL_START..=GRAPHICAL_END {
        let cell_offset = usize::from(byte.saturating_sub(GRAPHICAL_START));
        let index = cell_offset.saturating_add(phase).rem_euclid(TABLE_LEN);
        if TEST_XLAT1.get(index).copied() == Some(b'o') {
            return Ok(byte);
        }
    }
    Err(format!("no independent no-op byte at pointer {pointer}"))
}

#[test]
fn current_state_wraps_max_pointers_after_committed_encryption() -> TestResult {
    let profile = current_profile();
    let maximum = profile.memory_words().saturating_sub(1);
    let memory_len =
        usize::try_from(profile.memory_words()).map_err(|error| {
            format!("current memory length conversion: {error}")
        })?;
    let mut memory = vec![0u32; memory_len];
    let cell = noop_cell(maximum)?;
    let max_index = usize::try_from(maximum).map_err(|error| {
        format!("current maximum index conversion: {error}")
    })?;
    let slot = memory.get_mut(max_index).ok_or_else(|| {
        String::from("current maximum escaped allocated memory")
    })?;
    *slot = u32::from(cell);
    let registers = ProfileRegisters {
        accumulator: 7,
        code_pointer: maximum,
        data_pointer: maximum,
    };
    let mut machine = normalize_result(ProfileMachine::from_state(
        profile,
        memory,
        vec![0x44],
        registers,
    ))?;
    check_equal(
        &normalize_result(machine.step())?,
        &StepOutcome::Continued,
        "current maximum no-op continues",
    )?;
    check_equal(
        &machine.registers(),
        &ProfileRegisters {
            accumulator: 7,
            code_pointer: 0,
            data_pointer: 0,
        },
        "current maximum pointers wrap",
    )?;
    let encryption_index = usize::from(cell.saturating_sub(GRAPHICAL_START));
    let expected = TEST_XLAT2
        .get(encryption_index)
        .copied()
        .map(u32::from)
        .ok_or_else(|| String::from("independent encryption index escaped"))?;
    check_equal(
        &normalize_result(machine.memory_word(maximum))?,
        &expected,
        "current maximum cell encrypts before wrap",
    )?;
    check_equal(&machine.input_consumed(), &0usize, "current wrap input")?;
    check_equal(machine.output(), b"".as_slice(), "current wrap output")
}

#[test]
fn state_constructor_accepts_exact_historical_image() -> TestResult {
    let memory = vec![0u32; exact_memory_words()?];
    let registers = ProfileRegisters {
        accumulator: 17,
        code_pointer: 23,
        data_pointer: 42,
    };
    let machine = normalize_result(ProfileMachine::from_state(
        historical_profile(),
        memory,
        vec![0xaa],
        registers,
    ))?;
    check_equal(
        &machine.registers(),
        &registers,
        "historical state registers",
    )?;
    check_equal(
        &machine.profile().id(),
        &historical_profile().id(),
        "historical state profile",
    )?;
    check_equal(&machine.input_consumed(), &0usize, "historical state input")?;
    check_equal(machine.output(), b"".as_slice(), "historical state output")
}

#[test]
fn state_constructor_rejects_wrong_memory_length() -> TestResult {
    let observed = ProfileMachine::from_state(
        historical_profile(),
        Vec::new(),
        Vec::new(),
        ProfileRegisters::default(),
    );
    check_equal(
        &observed.map(|_machine| ()),
        &Err(ProfileMachineError::MemoryImageLength {
            expected: historical_profile().memory_words(),
            observed: 0,
        }),
        "state memory length rejection",
    )
}

#[test]
fn state_constructor_rejects_out_of_domain_memory_word() -> TestResult {
    let mut memory = vec![0u32; exact_memory_words()?];
    let rejected_address = 17usize;
    let slot = memory
        .get_mut(rejected_address)
        .ok_or_else(|| String::from("historical rejection address escaped"))?;
    *slot = historical_profile().word_modulus();
    let observed = ProfileMachine::from_state(
        historical_profile(),
        memory,
        Vec::new(),
        ProfileRegisters::default(),
    );
    check_equal(
        &observed.map(|_machine| ()),
        &Err(ProfileMachineError::MemoryWordOutOfRange {
            address: 17,
            value: historical_profile().word_modulus(),
        }),
        "state memory word rejection",
    )
}

#[test]
fn state_constructor_rejects_each_out_of_domain_register() -> TestResult {
    let maximum = historical_profile().word_modulus();
    let cases = [
        (ProfileRegisterName::Accumulator, ProfileRegisters {
            accumulator: maximum,
            code_pointer: 0,
            data_pointer: 0,
        }),
        (ProfileRegisterName::CodePointer, ProfileRegisters {
            accumulator: 0,
            code_pointer: maximum,
            data_pointer: 0,
        }),
        (ProfileRegisterName::DataPointer, ProfileRegisters {
            accumulator: 0,
            code_pointer: 0,
            data_pointer: maximum,
        }),
    ];
    for (register, registers) in cases {
        let memory = vec![0u32; exact_memory_words()?];
        let observed = ProfileMachine::from_state(
            historical_profile(),
            memory,
            Vec::new(),
            registers,
        );
        check_equal(
            &observed.map(|_machine| ()),
            &Err(ProfileMachineError::RegisterOutOfRange {
                register,
                value: maximum,
            }),
            "state register rejection",
        )?;
    }
    Ok(())
}
