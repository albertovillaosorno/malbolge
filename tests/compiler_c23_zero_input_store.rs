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
//   - A source-loaded zero C32 pair and genuinely input-derived low-cell write.
// - Must-Not:
//   - Claim this lossy write is signed C23 getchar or a linked checksum.
// - Allows:
//   - Inputs: the fixed 62-cell N15 loader and finite byte/EOF streams.
//   - Outputs: exact guest writes with an independent 257-class scalar oracle.
//   - Side effects: isolated bounded normative VM runs only.
// - Split-When:
//   - A real C23 typed SSA store replaces this partial physical continuation.
// - Merge-When:
//   - The original checksum runs its first executable signed source store.

//! First source-loaded P2 zero initializer, read, and revisited data store.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use malbolge::{
    ProfileMachine, ProfileRegisters, RunOutcome, Termination, TraceInput,
    current_profile, decode_profile_instruction, historical_profile,
};

// Canonical 62-byte physical zero initializer, not a hand-seeded memory image.
// C14 and C17 make adjacent zero writes before the suffix is patched.
const INITIAL_SOURCE: &str = concat!(
    "44434241403f3e3d3c7d34337a31302f762d3f31302f2e2d2c2b2a292827",
    "2625242322217e7d7c7b7a797877767574737271706f6e6d6c6b6a6968672725",
);
const LOW: u32 = 7_174_417;
const HIGH: u32 = LOW + 1;
const ENCODED: u32 = 7_174_439;
const REENTRY: u32 = ENCODED + 1;
const MODULUS: u32 = 14_348_907;

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "independent finite 15-trit ternary scalar oracle"
)]
fn scalar_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    const TABLE: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut result = 0;
    let mut place = 1;
    for _ in 0..15 {
        result +=
            TABLE[(data % 3) as usize][(accumulator % 3) as usize] * place;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    result
}

fn graphical(position: usize, operation: u8) -> u8 {
    (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), position as u32)
                == Some(operation)
        })
        .expect("every fixed probe operation is graphically representable")
}

fn patched_source() -> Vec<u8> {
    let mut source = INITIAL_SOURCE
        .as_bytes()
        .chunks_exact(2)
        .map(|pair| {
            let hex = std::str::from_utf8(pair).expect("fixed ASCII hex");
            u8::from_str_radix(hex, 16).expect("fixed graphical source")
        })
        .collect::<Vec<_>>();
    assert_eq!(source.len(), 62);
    for (index, operation) in [
        (18usize, b'o'),
        (37, b'/'),
        (38, b'o'),
        (39, b'p'),
        (40, b'j'),
        (41, b'p'),
        (42, b'v'),
    ] {
        source[index] = graphical(index, operation);
    }
    source
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "finite 257-class oracle and real 43-step source-loaded traces"
)]
fn first_real_c37_read_revisits_zero_low_and_writes_guest_data()
-> Result<(), String> {
    let profile = current_profile();
    let source = patched_source();
    assert_eq!(layout::admit_c23_probe_graphical_source(&source), Ok(()));
    let prepared = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    assert_eq!(prepared.memory_word(LOW), Ok(37));
    assert_eq!(prepared.memory_word(HIGH), Ok(7_174_416));
    assert_eq!(prepared.memory_word(ENCODED), Ok(37));
    assert_eq!(prepared.memory_word(REENTRY), Ok(7_174_416));
    let all_results = (0..=255u32)
        .chain([MODULUS - 1])
        .map(|raw| scalar_crazy(0, scalar_crazy(37, raw)))
        .collect::<Vec<_>>();
    assert_eq!(
        all_results.iter().copied().collect::<BTreeSet<_>>().len(),
        40
    );
    assert_eq!(
        (all_results[0], all_results[255], all_results[256]),
        (0, 255, 7_174_416)
    );
    assert!(!all_results[..256].contains(&all_results[256]));
    // The 40 image classes prove this is NOT a C23 signed/unsigned input
    // representation, even though EOF stays distinguishable from every byte.
    for input in [
        vec![],
        vec![0],
        vec![1],
        vec![2],
        vec![127],
        vec![255],
        vec![255, 4],
    ] {
        let raw = input
            .first()
            .map_or(profile.eof_word(), |byte| u32::from(*byte));
        let mut vm = ProfileMachine::from_state(
            profile,
            prepared.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = vm
            .run_traced(43, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 43,
        });
        assert_eq!(trace.len(), 43);
        assert_eq!(trace[14].decoded, Some(b'p'));
        assert_eq!(trace[17].decoded, Some(b'p'));
        assert_eq!(trace[37].decoded, Some(b'/'));
        assert_eq!(
            trace[37].input,
            Some(
                input
                    .first()
                    .map_or(TraceInput::EndOfInput, |b| TraceInput::Byte(*b))
            )
        );
        assert_eq!(trace[38].decoded, Some(b'o'));
        assert_eq!(trace[39].decoded, Some(b'p'));
        assert_eq!(trace[39].before.registers.data_pointer, ENCODED);
        assert_eq!(trace[39].before.registers.accumulator, raw);
        assert_eq!(trace[39].memory_reads.data.map(|r| r.value), Some(37));
        let intermediate = scalar_crazy(37, raw);
        assert_eq!(trace[39].after.registers.accumulator, intermediate);
        assert_eq!(trace[40].decoded, Some(b'j'));
        assert_eq!(
            trace[40].memory_reads.data.map(|r| (r.address, r.value)),
            Some((REENTRY, LOW - 1))
        );
        assert_eq!(trace[40].after.registers.data_pointer, LOW);
        assert_eq!(trace[41].decoded, Some(b'p'));
        assert_eq!(
            trace[41].memory_reads.data.map(|r| (r.address, r.value)),
            Some((LOW, 0))
        );
        let expected_low = scalar_crazy(0, intermediate);
        assert_eq!(trace[41].after.registers.accumulator, expected_low);
        assert_eq!(vm.memory_word(LOW), Ok(expected_low));
        assert_eq!(vm.memory_word(HIGH), Ok(0));
        assert_eq!(vm.memory_word(ENCODED), Ok(intermediate));
        assert_eq!(trace[42].decoded, Some(b'v'));
        assert_eq!(vm.input_consumed(), usize::from(!input.is_empty()));
        assert!(vm.output().is_empty());
    }
    Ok(())
}

#[test]
fn source_loaded_fold_builder_matches_independent_physical_oracle() {
    let plan = layout::build_adjacent_c32_zero_c37_input_low_fold_source(
        current_profile(),
    )
    .expect("bounded N15 loader admits the input low-cell fold");
    assert_eq!(plan.zero_pair.source, patched_source());
    assert_eq!(plan.zero_pair.zero_high_code_address, 14);
    assert_eq!(plan.zero_pair.zero_low_code_address, 17);
    assert_eq!(plan.zero_pair.input_code_address, Some(37));
    assert_eq!(plan.zero_pair.zero_low_address, LOW);
    assert_eq!(plan.zero_pair.zero_high_address, HIGH);
    assert_eq!(plan.encoded_store_code_address, 39);
    assert_eq!(plan.encoded_data_address, ENCODED);
    assert_eq!(plan.reentry_code_address, 40);
    assert_eq!(plan.low_fold_code_address, 41);
    assert_eq!(plan.halt_code_address, 42);
    assert_eq!(
        layout::build_adjacent_c32_zero_c37_input_low_fold_source(
            historical_profile(),
        ),
        Err(layout::ZeroCellSourceError::UnsupportedProfile),
    );
}
