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
//   - A physically executed EOF-arm-only p store after a genuine i branch.
// - Must-Not:
//   - Treat the loader scratch write as signed C23 frame normalization.
// - Allows:
//   - Inputs: the exact N15 guest branch and bounded byte/EOF stdin.
//   - Outputs: independent crazy arithmetic, two guest paths and data writes.
//   - Side effects: isolated normative VM execution only.
// - Split-When:
//   - The compiler emits source-C condition-dependent destination stores.
// - Merge-When:
//   - Physical branch and state mutations share a general layout verifier.
// - Summary:
//   - An executable EOF branch can conditionally mutate guest memory.

//! Source-loaded branch-dependent data writes without invented source-C state.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::iter::once;

use malbolge::{
    ProfileMachine, ProfileRegisters, RunOutcome, Termination, current_profile,
    decode_profile_instruction,
};

const EOF_SCRATCH_ADDRESS: u32 = 145;
const EOF_SCRATCH_BEFORE: u32 = 134;
const EOF_CLASS_WORD: u32 = 2_391_450;
const EOF_SCRATCH_AFTER: u32 = 4_783_019;

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "independent fixed-width ternary table"
)]
fn independent_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    const TABLE: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut result = 0;
    let mut place = 1;
    for _ in 0usize..15 {
        let row = usize::try_from(data % 3).unwrap_or_default();
        let column = usize::try_from(accumulator % 3).unwrap_or_default();
        let digit = TABLE
            .get(row)
            .and_then(|values| values.get(column))
            .copied()
            .unwrap_or_default();
        result += digit * place;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    result
}

#[test]
fn eof_scratch_result_is_independently_derived() {
    assert_eq!(
        independent_crazy(EOF_SCRATCH_BEFORE, EOF_CLASS_WORD),
        EOF_SCRATCH_AFTER
    );
    assert_eq!(EOF_SCRATCH_AFTER & 255, 171);
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    reason = "all-input physical code branch and per-arm state checks"
)]
fn real_signed_eof_branch_writes_scratch_only_on_eof() -> Result<(), String> {
    let profile = current_profile();
    let source = layout::build_signed_eof_branch_with_eof_store_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    let original = layout::build_signed_eof_branch_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(source.len(), 132);
    assert_eq!(source.get(130..), Some(b"-}".as_slice()));
    let differences = source
        .iter()
        .zip(&original)
        .enumerate()
        .filter_map(|(index, (changed, prior))| {
            (changed != prior).then_some(index)
        })
        .collect::<Vec<_>>();
    assert_eq!(differences, [127]);
    assert_eq!(
        decode_profile_instruction(
            u32::from(*source.get(127).ok_or("missing C127")?),
            127
        ),
        Some(b'p')
    );
    assert_eq!(
        decode_profile_instruction(
            u32::from(*original.get(127).ok_or("missing original C127")?),
            127
        ),
        Some(b'*')
    );
    let loaded = ProfileMachine::from_source(profile, &source, vec![])
        .map_err(|error| error.to_string())?;
    assert_eq!(
        loaded.memory_word(EOF_SCRATCH_ADDRESS),
        Ok(EOF_SCRATCH_BEFORE)
    );
    // Every successful byte must take the already verified success arm;
    // genuine EOF alone can reach the new physical data write.
    for input in once(Vec::new())
        .chain((u8::MIN..=u8::MAX).map(|byte| vec![byte]))
        .chain([vec![0, 1, 2], vec![0xff, 3]])
    {
        let eof = input.is_empty();
        let mut vm = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = vec![];
        let outcome = vm
            .run_traced(176, &mut |step| trace.push(*step))
            .map_err(|error| format!("input {input:?}: {error}"))?;
        assert_eq!(
            outcome,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: if eof {
                    119
                } else {
                    175
                },
            },
            "input {input:?}"
        );
        assert_eq!(
            vm.output(),
            if eof {
                &[171][..]
            } else {
                &[154][..]
            },
            "input {input:?}"
        );
        assert_eq!(vm.input_consumed(), input.len().min(1));
        let branch = trace
            .iter()
            .find(|step| step.before.registers.code_pointer == 114)
            .ok_or("missing actual conditional i")?;
        assert_eq!(branch.decoded, Some(b'i'));
        assert_eq!(
            branch.after.registers.code_pointer,
            if eof {
                126
            } else {
                45
            }
        );
        let writes = trace
            .iter()
            .filter(|step| {
                step.decoded == Some(b'p')
                    && step.before.registers.code_pointer == 127
            })
            .collect::<Vec<_>>();
        if eof {
            assert_eq!(writes.len(), 1);
            let store = writes.first().ok_or("missing EOF store")?;
            assert_eq!(
                store
                    .memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((EOF_SCRATCH_ADDRESS, EOF_SCRATCH_BEFORE))
            );
            assert_eq!(store.before.registers.accumulator, EOF_CLASS_WORD);
            assert_eq!(store.after.registers.accumulator, EOF_SCRATCH_AFTER);
            assert_eq!(
                store.memory_delta.data.map(|write| (
                    write.address,
                    write.before,
                    write.after
                )),
                Some((
                    EOF_SCRATCH_ADDRESS,
                    EOF_SCRATCH_BEFORE,
                    EOF_SCRATCH_AFTER,
                ))
            );
        } else {
            assert_eq!(writes.len(), 0);
            assert!(
                !trace
                    .iter()
                    .any(|step| step.before.registers.code_pointer == 127)
            );
        }
        assert_eq!(
            vm.memory_word(EOF_SCRATCH_ADDRESS),
            Ok(if eof {
                EOF_SCRATCH_AFTER
            } else {
                EOF_SCRATCH_BEFORE
            })
        );
    }
    Ok(())
}

#[test]
fn unsupported_profile_refuses_before_guest_publication() {
    assert_eq!(
        layout::build_signed_eof_branch_with_eof_store_source(
            malbolge::historical_profile()
        ),
        Err(layout::SignedEofBranchSourceError::UnsupportedProfile)
    );
}
