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
//   - A distinct N15 physical EOF-pointer indirect revisit candidate.
// - Must-Not:
//   - Claim an all-byte EOF branch, C23 signed conversion or source checksum.
// - Allows:
//   - Inputs: fixed 62-cell source and true EOF / one successful-byte trace.
//   - Outputs: normative post-jump code encryption, reached p, and byte
//     refusal.
//   - Side effects: isolated bounded N15 VM execution only.
// - Split-When:
//   - A redesigned data/control layout validates the complete 257-class path.
// - Merge-When:
//   - The source-C CFG linker emits a verified branch for every guest input.
// - Summary:
//   - A two-jump EOF route reaches a real encrypted code revisit, not C23.

//! One physical EOF-controlled code revisit that survives target encryption.
//!
//! The naive C55 j / C56 i continuation fails because raw EOF targets a
//! non-graphical encryption word. An additional C56 j instead reaches D=0
//! on true EOF; a real C57 i then reads M0=33, encrypts graphical M33 and
//! transfers to encrypted C34. On the next step C34 executes a new p write.
//! A successful NUL reads M1=85 at C57 and falls into non-graphical C86.
//! Thus this is a bounded physical *EOF path*, not an all-input control edge.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use malbolge::{
    ProfileMachine, RunOutcome, Termination, TraceInput, current_profile,
    decode_profile_instruction,
};

fn graphical(position: u32, opcode: u8) -> Result<u8, String> {
    (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), position)
                == Some(opcode)
        })
        .ok_or_else(|| format!("missing graphical {opcode} at {position}"))
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "one bounded physical EOF/byte N15 dual-path proof"
)]
fn eof_two_pointer_hops_reach_an_encrypted_guest_store_not_a_c23_branch()
-> Result<(), String> {
    let profile = current_profile();
    let mut source =
        layout::build_adjacent_c32_zero_c37_raw_eof_zero_source(profile)
            .map_err(|error| format!("source: {error:?}"))?
            .raw_pointer
            .raw_pair
            .zero_pair
            .source;
    assert_eq!(source.len(), 62);
    for (address, opcode) in [(55u32, b'j'), (56, b'j'), (57, b'i')] {
        source
            [usize::try_from(address).map_err(|error| error.to_string())?] =
            graphical(address, opcode)?;
    }
    assert_eq!(layout::admit_c23_probe_graphical_source(&source), Ok(()));

    let mut eof = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| format!("EOF load: {error:?}"))?;
    let mut trace = Vec::new();
    assert_eq!(
        eof.run_traced(59, &mut |step| trace.push(*step))
            .map_err(|error| format!("EOF run: {error:?}"))?,
        RunOutcome::BudgetExhausted { steps: 59 },
    );
    assert_eq!(trace.len(), 59);
    assert_eq!(trace[37].input, Some(TraceInput::EndOfInput));
    assert_eq!(trace[54].decoded, Some(b'p'));
    assert_eq!(trace[54].after.registers.accumulator, 0);
    assert_eq!(eof.memory_word(127), Ok(0));
    for (site, destination, operand) in [
        (55, 7_174_417, 7_174_416),
        (56, 0, profile.eof_word()),
        (57, 34, 33),
    ] {
        assert_eq!(
            trace[site].before.registers.code_pointer,
            u32::try_from(site).map_err(|error| error.to_string())?,
        );
        assert_eq!(
            trace[site].decoded,
            Some(if site == 57 {
                b'i'
            } else {
                b'j'
            })
        );
        assert_eq!(
            trace[site].memory_reads.data.map(|read| read.value),
            Some(operand),
        );
        if site == 57 {
            assert_eq!(trace[site].after.registers.code_pointer, destination);
        } else {
            assert_eq!(trace[site].after.registers.data_pointer, destination);
        }
    }
    // Actual N15 `i` encrypts M33 after moving C to M0+1 = C34.
    assert_eq!(
        trace[57]
            .memory_reads
            .encryption
            .map(|read| (read.address, read.value)),
        Some((33, 93)),
    );
    assert_eq!(trace[58].before.registers.code_pointer, 34);
    assert_eq!(trace[58].decoded, Some(b'p'));
    assert_eq!(trace[58].before.registers.data_pointer, 1);
    assert_eq!(trace[58].after.registers.accumulator, 7_174_453);
    assert_eq!(eof.memory_word(1), Ok(7_174_453));
    assert_eq!(eof.output(), b"");

    // A successful byte is not a valid alternate C arm: the same genuine
    // C57 i jumps to C86 and then immediately encounters non-graphical code.
    let mut nul = ProfileMachine::from_source(profile, &source, vec![0])
        .map_err(|error| format!("NUL load: {error:?}"))?;
    let mut byte_trace = Vec::new();
    assert_eq!(
        nul.run_traced(59, &mut |step| byte_trace.push(*step))
            .map_err(|error| format!("NUL run: {error:?}"))?,
        RunOutcome::Terminated {
            reason: Termination::NonGraphicalCell,
            steps: 59,
        },
    );
    assert_eq!(byte_trace[37].input, Some(TraceInput::Byte(0)));
    assert_eq!(byte_trace[57].decoded, Some(b'i'));
    assert_eq!(byte_trace[57].after.registers.code_pointer, 86);
    assert_eq!(byte_trace[58].before.registers.code_pointer, 86);
    assert_eq!(nul.memory_word(7_174_417), Ok(0));
    assert_eq!(nul.output(), b"");
    Ok(())
}

// An extra j after C57 makes *both* EOF and NUL reach a valid first
// post-jump encryption target. This is more progress than the shorter jji
// candidate, but the full trace still fails: a later encrypted i reenters
// loader noncode M[7_174_416] for both input classes. The source-controlled
// checksum loop remains unlinked, and the other 255 byte values are unproven.
#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "bounded 119-step VM proof of two physical paths"
)]
fn eof_and_nul_pointer_chain_transfers_but_later_encryption_blocks_loop()
-> Result<(), String> {
    const RAW_LOW: u32 = 7_174_417;
    let profile = current_profile();
    let mut source =
        layout::build_adjacent_c32_zero_c37_raw_eof_zero_source(profile)
            .map_err(|error| format!("source: {error:?}"))?
            .raw_pointer
            .raw_pair
            .zero_pair
            .source;
    for (position, operation) in [
        (55u32, b'j'),
        (56, b'j'),
        (57, b'j'),
        (58, b'j'),
        (59, b'i'),
    ] {
        source
            [usize::try_from(position).map_err(|error| error.to_string())?] =
            graphical(position, operation)?;
    }
    assert_eq!(layout::admit_c23_probe_graphical_source(&source), Ok(()));
    for (input, event, raw, jump, encrypted, failure_at) in [
        (
            Vec::new(),
            TraceInput::EndOfInput,
            profile.eof_word(),
            38,
            (37, 66),
            90,
        ),
        (vec![0], TraceInput::Byte(0), 0, 1, (0, 33), 118),
    ] {
        let mut vm = ProfileMachine::from_source(profile, &source, input)
            .map_err(|error| format!("source load: {error:?}"))?;
        let mut trace = Vec::new();
        assert_eq!(
            vm.run_traced(150, &mut |step| trace.push(*step)),
            Err(malbolge::ProfileMachineError::InvalidEncryptionTarget {
                pointer: RAW_LOW - 1,
                value: RAW_LOW - 1,
            }),
        );
        assert_eq!(trace.len(), failure_at + 1);
        assert_eq!(trace[37].input, Some(event));
        assert_eq!(trace[54].decoded, Some(b'p'));
        assert_eq!(
            trace[54].after.registers.accumulator == 0,
            raw == profile.eof_word()
        );
        assert_eq!(vm.memory_word(RAW_LOW), Ok(raw));
        assert_eq!(vm.memory_word(RAW_LOW + 1), Ok(0));
        for index in 55..=58 {
            assert_eq!(trace[index].decoded, Some(b'j'));
        }
        assert_eq!(trace[59].decoded, Some(b'i'));
        assert_eq!(trace[59].after.registers.code_pointer, jump);
        assert_eq!(
            trace[59]
                .memory_reads
                .encryption
                .map(|read| (read.address, read.value)),
            Some(encrypted),
        );
        assert_eq!(trace[60].before.registers.code_pointer, jump);
        assert!(trace[60].result.is_ok());
        assert_eq!(trace[failure_at].decoded, Some(b'i'));
        assert_eq!(
            trace[failure_at].result,
            Err(malbolge::ProfileMachineError::InvalidEncryptionTarget {
                pointer: RAW_LOW - 1,
                value: RAW_LOW - 1,
            }),
        );
        assert_eq!(vm.output(), b"");
    }
    Ok(())
}
