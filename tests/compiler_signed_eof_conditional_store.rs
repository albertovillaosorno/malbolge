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

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    reason = "independent three-input conditional store and guard trace"
)]
fn second_read_eof_stores_or_reads_third_word_on_real_guest()
-> Result<(), String> {
    let profile = current_profile();
    let source =
        layout::build_second_input_eof_store_or_third_read_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    let baseline =
        layout::build_second_input_guarded_third_read_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    assert_eq!(source.len(), 132);
    assert_eq!(source.get(130..), Some(b"-}".as_slice()));
    let differences = source
        .iter()
        .zip(baseline)
        .enumerate()
        .filter_map(|(index, (changed, previous))| {
            (changed != &previous).then_some(index)
        })
        .collect::<Vec<_>>();
    assert_eq!(differences, [127]);
    assert_eq!(
        decode_profile_instruction(
            u32::from(*source.get(127).ok_or("missing C127")?),
            127,
        ),
        Some(b'p')
    );

    let original =
        layout::build_second_input_eof_classified_first_echo_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    assert_ne!(original.get(101), source.get(101));
    let loaded = ProfileMachine::from_source(profile, &source, vec![])
        .map_err(|error| error.to_string())?;
    assert_eq!(
        loaded.memory_word(EOF_SCRATCH_ADDRESS),
        Ok(EOF_SCRATCH_BEFORE)
    );

    let cases = [
        vec![],
        vec![0],
        vec![255],
        vec![0, 0, 17],
        vec![255, 255, 0, 254],
        vec![128, 127, 255, 44],
    ];
    for input in cases
        .into_iter()
        .chain((u8::MIN..=u8::MAX).map(|second| vec![0xa7, second, 0, 255]))
    {
        // This expectation is defined from the *second* supplied input,
        // independently of any generated source or guest-state calculation.
        let eof = input.len() < 2;
        let expected_first = input.first().copied().unwrap_or(106);
        let expected_read_sites = if eof {
            [53, 63].as_slice()
        } else {
            [53, 63, 101].as_slice()
        };
        let mut vm = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = vec![];
        let outcome = vm
            .run_traced(177, &mut |step| trace.push(*step))
            .map_err(|error| format!("input {input:?}: {error}"))?;
        let reads = trace
            .iter()
            .filter(|step| step.decoded == Some(b'/'))
            .map(|step| step.before.registers.code_pointer)
            .collect::<Vec<_>>();
        assert_eq!(reads.as_slice(), expected_read_sites, "input {input:?}");
        assert_eq!(
            vm.input_consumed(),
            input.len().min(expected_read_sites.len()),
            "input {input:?}"
        );
        assert_eq!(
            vm.output(),
            &[
                expected_first,
                if eof {
                    171
                } else {
                    154
                }
            ],
            "input {input:?}"
        );
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
        let branch = trace
            .iter()
            .find(|step| step.before.registers.code_pointer == 114)
            .ok_or("missing physical branch at C114")?;
        assert_eq!(branch.decoded, Some(b'i'));
        assert_eq!(
            branch.after.registers.code_pointer,
            if eof {
                126
            } else {
                45
            },
            "input {input:?}"
        );
        let stores = trace
            .iter()
            .filter(|step| step.before.registers.code_pointer == 127)
            .collect::<Vec<_>>();
        if eof {
            let [store] = stores.as_slice() else {
                return Err(format!("input {input:?}: expected one EOF store"));
            };
            assert_eq!(store.decoded, Some(b'p'));
            assert_eq!(store.before.registers.accumulator, EOF_CLASS_WORD);
            assert_eq!(
                store
                    .memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((EOF_SCRATCH_ADDRESS, EOF_SCRATCH_BEFORE))
            );
            assert_eq!(
                store
                    .memory_delta
                    .data
                    .map(|write| (write.address, write.after)),
                Some((EOF_SCRATCH_ADDRESS, EOF_SCRATCH_AFTER))
            );
        } else {
            assert!(stores.is_empty(), "input {input:?}");
        }
        assert_eq!(
            vm.memory_word(EOF_SCRATCH_ADDRESS),
            Ok(if eof {
                EOF_SCRATCH_AFTER
            } else {
                EOF_SCRATCH_BEFORE
            }),
            "input {input:?}"
        );
    }
    Ok(())
}

#[test]
fn composed_guard_and_store_refuses_noncanonical_profile() {
    assert_eq!(
        layout::build_second_input_eof_store_or_third_read_source(
            malbolge::historical_profile()
        ),
        Err(layout::SignedEofBranchSourceError::UnsupportedProfile)
    );
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::panic_in_result_fn,
    reason = "independent guest replay for two destructive source mutations"
)]
fn composing_guard_and_store_has_independent_negative_controls()
-> Result<(), String> {
    let profile = current_profile();
    let source =
        layout::build_second_input_eof_store_or_third_read_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    let no_guard = {
        let mut changed = source.clone();
        let no_read =
            layout::build_second_input_eof_classified_first_echo_source(
                profile,
            )
            .map_err(|error| format!("{error:?}"))?;
        *changed.get_mut(101).ok_or("missing C101")? =
            *no_read.get(101).ok_or("missing original C101")?;
        changed
    };
    let no_store = {
        let mut changed = source.clone();
        *changed.get_mut(127).ok_or("missing C127")? = (33..=126u8)
            .find(|byte| {
                decode_profile_instruction(u32::from(*byte), 127) == Some(b'o')
            })
            .ok_or("missing C127 no-op encoding")?;
        changed
    };
    for (guest, expected_consumed, expected_output, expected_scratch) in [
        (source.as_slice(), 3, vec![0x12, 154], EOF_SCRATCH_BEFORE),
        (no_guard.as_slice(), 2, vec![0x12, 154], EOF_SCRATCH_BEFORE),
    ] {
        let mut vm =
            ProfileMachine::from_source(profile, guest, vec![0x12, 0x34, 0xff])
                .map_err(|error| error.to_string())?;
        assert_eq!(
            vm.run(176).map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 175,
            }
        );
        assert_eq!(vm.input_consumed(), expected_consumed);
        assert_eq!(vm.output(), expected_output);
        assert_eq!(vm.memory_word(EOF_SCRATCH_ADDRESS), Ok(expected_scratch));
    }
    for (guest, expected_output, expected_scratch) in [
        (source.as_slice(), vec![0x12, 171], EOF_SCRATCH_AFTER),
        (no_store.as_slice(), vec![0x12, 154], EOF_SCRATCH_BEFORE),
    ] {
        let mut vm = ProfileMachine::from_source(profile, guest, vec![0x12])
            .map_err(|error| error.to_string())?;
        assert_eq!(
            vm.run(120).map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 119,
            }
        );
        assert_eq!(vm.input_consumed(), 1);
        assert_eq!(vm.output(), expected_output);
        assert_eq!(vm.memory_word(EOF_SCRATCH_ADDRESS), Ok(expected_scratch));
    }
    Ok(())
}

const FIRST_FOLD_ADDRESS: u32 = 132;
const FIRST_FOLD_BEFORE: u32 = 7_174_350;
const SECOND_CLASS_ADDRESS: u32 = 7_174_355;
const SECOND_CLASS_BEFORE: u32 = 125;

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    reason = "source-independent two-input state, branch and guard VM admission"
)]
fn two_input_class_writes_survive_the_guarded_third_read() -> Result<(), String>
{
    let profile = current_profile();
    let source =
        layout::build_two_input_class_state_with_guarded_third_read_source(
            profile,
        )
        .map_err(|error| format!("{error:?}"))?;
    let baseline =
        layout::build_second_input_eof_store_or_third_read_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    assert_eq!(source.len(), 132);
    assert_eq!(source.get(130..), Some(b"-}".as_slice()));
    let changed = source
        .iter()
        .zip(&baseline)
        .enumerate()
        .filter_map(|(position, (new, old))| (new != old).then_some(position))
        .collect::<Vec<_>>();
    assert_eq!(changed, [62, 103]);

    // Decode each added physical instruction independently. The encrypted
    // C103 revisit must not overwrite the newly stored second-input class.
    for position in [62usize, 103] {
        assert_eq!(
            decode_profile_instruction(
                u32::from(source[position]),
                position as u32
            ),
            Some(b'p'),
        );
    }
    let second_pass = malbolge::encrypt_profile_cell(u32::from(source[103]))
        .and_then(|word| decode_profile_instruction(word, 103));
    assert_eq!(second_pass, Some(b'#'));

    let loaded = ProfileMachine::from_source(profile, &source, vec![])
        .map_err(|error| error.to_string())?;
    for (address, original) in [
        (FIRST_FOLD_ADDRESS, FIRST_FOLD_BEFORE),
        (SECOND_CLASS_ADDRESS, SECOND_CLASS_BEFORE),
        (EOF_SCRATCH_ADDRESS, EOF_SCRATCH_BEFORE),
    ] {
        assert_eq!(loaded.memory_word(address), Ok(original));
    }

    // Exercise all 256 byte values in both input positions in one diagonal
    // matrix, plus distinct mixed and truncated streams at all EOF sites.
    let cases = [
        vec![],
        vec![0],
        vec![255],
        vec![0xa7],
        vec![128, 127],
        vec![0, 0, 255],
        vec![255, 255, 0, 253],
        vec![0xa7, 0, 255],
    ];
    for input in cases
        .into_iter()
        .chain((0..=255u8).map(|byte| vec![byte, byte, 255, 0]))
    {
        let second_eof = input.len() < 2;
        let first_raw = input
            .first()
            .map_or(profile.eof_word(), |byte| u32::from(*byte));
        let expected_first = input.first().copied().unwrap_or(106);
        let class_accumulator = if second_eof {
            7_174_354
        } else {
            7_174_435
        };
        let expected_class =
            independent_crazy(SECOND_CLASS_BEFORE, class_accumulator);
        assert_eq!(
            expected_class,
            if second_eof {
                134
            } else {
                53
            }
        );
        let expected_first_fold =
            independent_crazy(FIRST_FOLD_BEFORE, first_raw);

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
                steps: if second_eof {
                    119
                } else {
                    175
                },
            },
            "input {input:?}",
        );
        assert_eq!(
            vm.output(),
            &[
                expected_first,
                if second_eof {
                    171
                } else {
                    154
                }
            ],
            "input {input:?}",
        );
        assert_eq!(
            vm.input_consumed(),
            input.len().min(if second_eof {
                2
            } else {
                3
            })
        );
        let read_sites = trace
            .iter()
            .filter(|step| step.decoded == Some(b'/'))
            .map(|step| step.before.registers.code_pointer)
            .collect::<Vec<_>>();
        assert_eq!(
            read_sites,
            if second_eof {
                vec![53, 63]
            } else {
                vec![53, 63, 101]
            },
            "input {input:?}",
        );

        for (address, previous, expected, code, accumulator) in [
            (
                FIRST_FOLD_ADDRESS,
                FIRST_FOLD_BEFORE,
                expected_first_fold,
                62,
                first_raw,
            ),
            (
                SECOND_CLASS_ADDRESS,
                SECOND_CLASS_BEFORE,
                expected_class,
                103,
                class_accumulator,
            ),
        ] {
            let reached = trace
                .iter()
                .filter(|step| step.before.registers.code_pointer == code)
                .collect::<Vec<_>>();
            assert_eq!(
                reached.len(),
                if second_eof {
                    1
                } else {
                    2
                },
                "input {input:?}"
            );
            let store = reached[0];
            assert_eq!(store.decoded, Some(b'p'));
            assert_eq!(store.before.registers.accumulator, accumulator);
            assert_eq!(
                store
                    .memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((address, previous)),
                "input {input:?}",
            );
            assert_eq!(
                store.memory_delta.data.map(|write| (
                    write.address,
                    write.before,
                    write.after
                )),
                (previous != expected).then_some((address, previous, expected)),
                "input {input:?}",
            );
            assert_eq!(vm.memory_word(address), Ok(expected));
            if !second_eof {
                assert_ne!(reached[1].decoded, Some(b'p'));
            }
        }
        let branch = trace
            .iter()
            .find(|step| step.before.registers.code_pointer == 114)
            .ok_or("missing physical EOF branch")?;
        assert_eq!(branch.decoded, Some(b'i'));
        assert_eq!(
            branch.after.registers.code_pointer,
            if second_eof {
                126
            } else {
                45
            },
        );
        let eof_writes = trace
            .iter()
            .filter(|step| step.before.registers.code_pointer == 127)
            .collect::<Vec<_>>();
        assert_eq!(eof_writes.len(), usize::from(second_eof));
        if second_eof {
            let store = eof_writes[0];
            assert_eq!(store.decoded, Some(b'p'));
            assert_eq!(store.before.registers.accumulator, EOF_CLASS_WORD);
            assert_eq!(
                store.memory_delta.data.map(|write| (
                    write.address,
                    write.before,
                    write.after
                )),
                Some((
                    EOF_SCRATCH_ADDRESS,
                    EOF_SCRATCH_BEFORE,
                    EOF_SCRATCH_AFTER
                )),
            );
        }
        assert_eq!(
            vm.memory_word(EOF_SCRATCH_ADDRESS),
            Ok(if second_eof {
                EOF_SCRATCH_AFTER
            } else {
                EOF_SCRATCH_BEFORE
            }),
        );
    }
    Ok(())
}

#[test]
fn independent_mutations_detect_each_new_guest_state_write()
-> Result<(), String> {
    let profile = current_profile();
    let source =
        layout::build_two_input_class_state_with_guarded_third_read_source(
            profile,
        )
        .map_err(|error| format!("{error:?}"))?;
    let baseline =
        layout::build_second_input_eof_store_or_third_read_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    for (position, input, changed_address) in [
        (62usize, vec![7, 8, 9], FIRST_FOLD_ADDRESS),
        (103, vec![7, 8, 9], SECOND_CLASS_ADDRESS),
        (103, vec![7], SECOND_CLASS_ADDRESS),
    ] {
        let mut altered = source.clone();
        altered[position] = baseline[position];
        let mut vm = ProfileMachine::from_source(profile, &altered, input)
            .map_err(|error| error.to_string())?;
        let result = vm.run(176).map_err(|error| error.to_string())?;
        assert!(matches!(result, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            ..
        }));
        let expected = if changed_address == FIRST_FOLD_ADDRESS {
            FIRST_FOLD_BEFORE
        } else {
            SECOND_CLASS_BEFORE
        };
        assert_eq!(vm.memory_word(changed_address), Ok(expected));
    }
    assert_eq!(
        layout::build_two_input_class_state_with_guarded_third_read_source(
            malbolge::historical_profile(),
        ),
        Err(layout::SignedEofBranchSourceError::UnsupportedProfile),
    );
    Ok(())
}
