// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier: Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Source-admitted indirect leaf placement and physical guest continuation.
// - Must-Not:
//   - Claim signed C23 EOF, source-C arithmetic, a loop, or a linked checksum.
// - Allows:
//   - Inputs: a fixed source-backed two-read fold and finite real VM stdin.
//   - Outputs: physical indirect transitions, state, I/O, halt and refusals.
//   - Side effects: isolated current-profile VM runs only.
// - Split-When:
//   - A source-C CFG guest continuation linker proves these same obligations.
// - Merge-When:
//   - Complete guest source construction subsumes bounded pointer-code leaves.
// - Summary:
//   - Guest pointer bytes must load as source code before an indirect suffix.

//! A checked *placement* helper, independently exercised in a physical guest.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::iter::once;

use layout::{
    IndirectSourceSuffixError, IndirectSourceSuffixPlan,
    plan_source_loaded_indirect_suffix,
};
use malbolge::{
    ProfileMachine, RunOutcome, Termination, TraceInput, current_profile,
    decode_profile_instruction, historical_profile,
};

// The suffix is a 12-cell linear source window, but it is not a pure I/O
// leaf: its reached j reads the *encrypted* earlier output instruction, and
// two reached p operations update the earlier guest-computed state.
const THREE_INPUT_FOLD_SUFFIX: &[u8] = b"/<oooojpp<*v";

fn graphical(position: u32, opcode: u8) -> Option<u8> {
    (33..=126u8).find(|byte| {
        decode_profile_instruction(u32::from(*byte), position) == Some(opcode)
    })
}

#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    reason = "fixed 135-cell frozen physical saved-fold experiment"
)]
fn saved_fold_source() -> Vec<u8> {
    let mut source = (0..135u32)
        .map(|at| graphical(at, b'o').expect("graphical no-op"))
        .collect::<Vec<_>>();
    for (at, opcode) in [
        (10u32, b'/'),
        (11, b'<'),
        (29, b'j'),
        (30, b'p'),
        (58, b'j'),
        (59, b'j'),
        (82, b'/'),
        (83, b'j'),
        (84, b'j'),
        (85, b'j'),
        (86, b'j'),
        (87, b'p'),
        (88, b'<'),
        (89, b'j'),
        (90, b'j'),
        (91, b'j'),
        (92, b'j'),
        (93, b'j'),
        (94, b'i'),
    ] {
        source[usize::try_from(at).expect("code position")] =
            graphical(at, opcode).expect("encoded opcode");
    }
    for (at, word) in [
        (95usize, 97u8),
        (98, 36),
        (99, 94),
        (100, 93),
        (101, 110),
        (104, 123),
        (106, 121),
        (108, 103),
        (111, 81),
        (124, 126),
        (127, 100),
        (134, 58),
    ] {
        source[at] = word;
    }
    assert_eq!(layout::admit_c23_probe_graphical_source(&source), Ok(()));
    source
}

// Scalar ternary proof independent of the production guest crazy operation.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    clippy::indexing_slicing,
    clippy::as_conversions,
    reason = "indices and digits bounded below three in the scalar oracle"
)]
fn scalar_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    const DIGITS: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut result = 0u32;
    let mut place = 1u32;
    for _ in 0u8..15 {
        result +=
            DIGITS[(data % 3) as usize][(accumulator % 3) as usize] * place;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    result
}

fn open_suffix(source: &[u8], suffix: &[u8]) -> IndirectSourceSuffixPlan {
    // C0..C111 are already executed or are physically read operands when
    // C94 i is reached. The source value at C111 is the sole changed read;
    // C124/C127/C134 are live route operands and must remain untouched.
    let protected = (0..111).chain([124, 127, 134]).collect::<Vec<usize>>();
    plan_source_loaded_indirect_suffix(
        current_profile(),
        source,
        111,
        112,
        123,
        suffix,
        &protected,
    )
    .unwrap_or_else(|error| panic!("source-valid indirect leaf: {error:?}"))
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::integer_division_remainder_used,
    clippy::too_many_lines,
    clippy::cognitive_complexity,
    reason = "independent executable I/O and self-encrypted control witness"
)]
fn source_loaded_indirect_leaf_follows_guest_fold_and_reads_real_third_word() {
    let source = saved_fold_source();
    let candidate = open_suffix(&source, b"/<v");
    assert_eq!(candidate.pointer_word, 116);
    assert_eq!(candidate.landing_address, 117);
    assert_eq!(candidate.source.len(), 135);
    assert_eq!(candidate.source[111], 116);
    assert_eq!(decode_profile_instruction(116, 111), Some(b'*'));
    for (position, opcode) in [(117, b'/'), (118, b'<'), (119, b'v')] {
        assert_eq!(
            decode_profile_instruction(
                u32::from(candidate.source[position]),
                u32::try_from(position).expect("in-domain source position")
            ),
            Some(opcode)
        );
    }
    assert_eq!(
        layout::admit_c23_probe_graphical_source(&candidate.source),
        Ok(())
    );
    // The plan must not silently disturb the 94-step fold and pointer route.
    for position in (0..135).filter(|at| ![111, 117, 118, 119].contains(at)) {
        assert_eq!(candidate.source[position], source[position]);
    }
    let profile = current_profile();
    let pristine =
        ProfileMachine::from_source(profile, &candidate.source, vec![])
            .expect("strict N15 source loader");
    for input in [
        vec![],
        vec![0],
        vec![255],
        vec![3, 4],
        vec![0, 255, 0],
        vec![3, 4, 5],
        vec![5, 3, 4],
        vec![255, 0, 128, 1],
        vec![0x80, 0x7f, 0xff],
    ] {
        let first = input
            .first()
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let second = input
            .get(1)
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let third = input
            .get(2)
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let saved = scalar_crazy(121, first);
        let folded = scalar_crazy(saved, second);
        let mut vm = pristine
            .fork_with_input(input.clone())
            .expect("fresh stdin");
        let mut steps = Vec::new();
        assert_eq!(
            vm.run_traced(110, &mut |step| steps.push(*step)),
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 98,
            }),
            "stdin={input:?}"
        );
        assert_eq!(vm.input_consumed(), input.len().min(3));
        assert_eq!(vm.output(), [
            u8::try_from(first % 256).expect("low byte"),
            u8::try_from(folded % 256).expect("low fold"),
            u8::try_from(third % 256).expect("third low byte"),
        ]);
        assert_eq!(vm.memory_word(106), Ok(folded));
        for (index, expected) in
            [(10, input.first()), (82, input.get(1)), (95, input.get(2))]
        {
            assert_eq!(
                steps[index].input,
                Some(expected.map_or(TraceInput::EndOfInput, |byte| {
                    TraceInput::Byte(*byte)
                }))
            );
        }
        assert_eq!(steps[30].decoded, Some(b'p'));
        assert_eq!(steps[30].after.registers.accumulator, saved);
        assert_eq!(steps[87].decoded, Some(b'p'));
        assert_eq!(steps[87].after.registers.accumulator, folded);
        assert_eq!(
            steps[87].memory_reads.data.map(|read| read.address),
            Some(106)
        );
        assert_eq!(steps[94].decoded, Some(b'i'));
        assert_eq!(
            steps[94]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((111, 116))
        );
        assert_eq!(steps[94].after.registers.code_pointer, 117);
        assert_eq!(steps[95].before.registers.code_pointer, 117);
        assert_eq!(steps[95].decoded, Some(b'/'));
        assert_eq!(steps[96].decoded, Some(b'<'));
        assert_eq!(
            steps[96].output,
            Some(u8::try_from(third % 256).expect("low byte"))
        );
        assert_eq!(steps[97].decoded, Some(b'v'));
    }
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::integer_division_remainder_used,
    reason = "all 257 independent third-input/EOF classes"
)]
fn all_guest_third_bytes_preserve_the_earlier_two_input_fold() {
    let plan = open_suffix(&saved_fold_source(), b"/<v");
    let profile = current_profile();
    let pristine = ProfileMachine::from_source(profile, &plan.source, vec![])
        .expect("loaded once, cloned with separately owned input");
    let folded = scalar_crazy(scalar_crazy(121, 3), 4);
    for third in (0..=255u32).chain(once(profile.eof_word())) {
        let mut input = vec![3, 4];
        if third != profile.eof_word() {
            input.push(u8::try_from(third).expect("byte"));
        }
        let mut vm =
            pristine.fork_with_input(input).expect("independent input");
        assert_eq!(
            vm.run(110),
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 98,
            }),
            "third={third}"
        );
        assert_eq!(vm.memory_word(106), Ok(folded));
        assert_eq!(vm.output(), &[
            3,
            u8::try_from(folded % 256).expect("low fold"),
            u8::try_from(third % 256).expect("low third")
        ]);
    }
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::integer_division_remainder_used,
    reason = "two independently source-backed leaf shapes"
)]
fn same_planner_places_output_only_leaf_without_an_extra_input() {
    let plan = open_suffix(&saved_fold_source(), b"<v");
    assert_eq!(plan.landing_address, 117);
    let mut vm =
        ProfileMachine::from_source(current_profile(), &plan.source, vec![
            3, 4, 5,
        ])
        .expect("graphical source");
    let folded = scalar_crazy(scalar_crazy(121, 3), 4);
    assert_eq!(
        vm.run(110),
        Ok(RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 97,
        })
    );
    assert_eq!(vm.input_consumed(), 2);
    assert_eq!(vm.output(), &[
        3,
        u8::try_from(folded % 256).expect("low fold"),
        u8::try_from(folded % 256).expect("low fold")
    ]);
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::cognitive_complexity,
    reason = "finite explicit rejected geometry and source mutations"
)]
fn placement_refuses_unsafe_pointer_words_and_overlapping_code() {
    use IndirectSourceSuffixError::{
        InvalidPlacement, InvalidSource, InvalidSuffix,
        NoSourceLoadablePointer, UnsupportedProfile,
    };
    let source = saved_fold_source();
    let call = |input_source: &[u8],
                from,
                through,
                leaf: &[u8],
                protected: &[usize]| {
        plan_source_loaded_indirect_suffix(
            current_profile(),
            input_source,
            111,
            from,
            through,
            leaf,
            protected,
        )
    };
    assert_eq!(
        call(&source, 112, 112, b"/<v", &[]),
        Err(NoSourceLoadablePointer),
        "M111=111 would jump to C112 but is invalid source at C111"
    );
    assert_eq!(call(&source, 112, 123, b"", &[]), Err(InvalidSuffix));
    assert_eq!(call(&source, 112, 123, b"/<", &[]), Err(InvalidSuffix));
    assert_eq!(call(&source, 112, 123, b"v<", &[]), Err(InvalidSuffix));
    assert_eq!(call(&source, 111, 123, b"v", &[]), Err(InvalidPlacement));
    assert_eq!(call(&source, 133, 134, b"/<v", &[]), Err(InvalidPlacement));
    assert_eq!(
        call(&source, 117, 118, b"/<v", &[117, 118]),
        Err(NoSourceLoadablePointer)
    );
    assert_eq!(
        call(&source, 117, 118, b"/<v", &[111]),
        Err(InvalidPlacement)
    );
    let mut corrupted = source.clone();
    corrupted[5] = b' ';
    assert_eq!(call(&corrupted, 112, 123, b"/<v", &[]), Err(InvalidSource));
    assert_eq!(
        plan_source_loaded_indirect_suffix(
            historical_profile(),
            &source,
            111,
            112,
            123,
            b"/<v",
            &[]
        ),
        Err(UnsupportedProfile)
    );
    let alternate = call(&source, 117, 118, b"/<v", &[117])
        .expect("next source-valid pointer word");
    assert_eq!(
        (alternate.pointer_word, alternate.landing_address),
        (117, 118)
    );
    assert_eq!(
        layout::admit_c23_probe_graphical_source(&alternate.source),
        Ok(())
    );
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    reason = "a changed guest operand or opcode must lose the physical witness"
)]
fn saved_fold_continuation_depends_on_the_source_pointer_and_input_opcode() {
    let source = saved_fold_source();
    let plan = open_suffix(&source, b"/<v");
    // A different *admissible* pointer sends C94 back to the previously
    // encrypted C82 halt. The extra input/output cannot be fabricated.
    let mut redirected = plan.source.clone();
    redirected[111] = source[111];
    let mut vm =
        ProfileMachine::from_source(current_profile(), &redirected, vec![
            3, 4, 5,
        ])
        .expect("old source-valid pointer");
    assert_eq!(
        vm.run(110),
        Ok(RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 96,
        })
    );
    assert_eq!(vm.input_consumed(), 2);
    assert_eq!(vm.output().len(), 2);
    // Changing only the landing input opcode retains the source-valid
    // jump but no longer consumes a third word.
    let mut no_read = plan.source;
    no_read[117] = graphical(117, b'o').expect("valid positional no-op");
    let mut no_read_vm =
        ProfileMachine::from_source(current_profile(), &no_read, vec![3, 4, 5])
            .expect("valid mutated code");
    assert_eq!(
        no_read_vm.run(110),
        Ok(RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 98,
        })
    );
    assert_eq!(no_read_vm.input_consumed(), 2);
    assert_ne!(no_read_vm.output().last(), Some(&5));
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::integer_division_remainder_used,
    clippy::too_many_lines,
    clippy::cognitive_complexity,
    reason = "physical three-input state fold and encryption witness"
)]
fn source_loaded_indirect_suffix_updates_saved_state_from_real_third_input() {
    use malbolge::encrypt_profile_cell;
    let original = saved_fold_source();
    let plan = open_suffix(&original, THREE_INPUT_FOLD_SUFFIX);
    assert_eq!((plan.pointer_word, plan.landing_address), (116, 117));
    assert_eq!(plan.source.len(), original.len());
    // C124 and C127 are essential first/two-input pointer words. The
    // suffix executes their pre-existing p/* code without rewriting them.
    for protected in [124usize, 127, 134] {
        assert_eq!(plan.source[protected], original[protected]);
    }
    for at in
        (0..135).filter(|at| ![111, 117, 118, 123, 125, 126, 128].contains(at))
    {
        assert_eq!(plan.source[at], original[at]);
    }
    assert_eq!(plan.source[118], 75);
    assert_eq!(encrypt_profile_cell(75), Some(104));
    assert_eq!(plan.source[124], 126);
    assert_eq!(plan.source[127], 100);
    assert_eq!(
        layout::admit_c23_probe_graphical_source(&plan.source),
        Ok(())
    );
    let profile = current_profile();
    let pristine = ProfileMachine::from_source(profile, &plan.source, vec![])
        .expect("fully source-admitted 135-cell guest");
    assert_eq!(pristine.memory_word(105), Ok(57));
    assert_eq!(pristine.memory_word(106), Ok(121));
    for input in [
        vec![],
        vec![0],
        vec![0, 0],
        vec![3, 4, 5],
        vec![255, 0, 128, 1],
        vec![3, 4, 5, 6],
        vec![0, 255, 0],
        vec![128, 127, 255],
        vec![255, 255, 255],
    ] {
        let raw = |index| {
            input
                .get(index)
                .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte))
        };
        let first = raw(0);
        let second = raw(1);
        let third = raw(2);
        let folded_twice = scalar_crazy(scalar_crazy(121, first), second);
        let seeded_third = scalar_crazy(57, third);
        let folded_thrice = scalar_crazy(folded_twice, seeded_third);
        let low = |value: u32| u8::try_from(value % 256).expect("low byte");
        let mut vm = pristine
            .fork_with_input(input.clone())
            .expect("isolated VM state");
        let mut trace = Vec::new();
        assert_eq!(
            vm.run_traced(110, &mut |step| trace.push(*step)),
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 107,
            }),
            "stdin={input:?}"
        );
        assert_eq!(vm.input_consumed(), input.len().min(3));
        assert_eq!(vm.output(), &[
            low(first),
            low(folded_twice),
            low(third),
            low(folded_thrice)
        ]);
        assert_eq!(vm.memory_word(105), Ok(seeded_third));
        assert_eq!(vm.memory_word(106), Ok(folded_thrice));
        assert_eq!(trace[94].decoded, Some(b'i'));
        assert_eq!(trace[94].after.registers.code_pointer, 117);
        assert_eq!(
            trace[95].input,
            Some(input.get(2).map_or(TraceInput::EndOfInput, |byte| {
                TraceInput::Byte(*byte)
            }))
        );
        assert_eq!(trace[96].before.registers.code_pointer, 118);
        assert_eq!(trace[96].output, Some(low(third)));
        assert_eq!(
            trace[96].memory_delta.encryption.map(|change| change.after),
            Some(104)
        );
        assert_eq!(trace[101].decoded, Some(b'j'));
        assert_eq!(
            trace[101]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((118, 104))
        );
        assert_eq!(trace[101].after.registers.data_pointer, 105);
        for (step, at, read, result) in [
            (102, 124, (105, 57), seeded_third),
            (103, 125, (106, folded_twice), folded_thrice),
        ] {
            assert_eq!(trace[step].before.registers.code_pointer, at);
            assert_eq!(trace[step].decoded, Some(b'p'));
            assert_eq!(
                trace[step]
                    .memory_reads
                    .data
                    .map(|word| (word.address, word.value)),
                Some(read)
            );
            assert_eq!(trace[step].after.registers.accumulator, result);
        }
        assert_eq!(trace[104].output, Some(low(folded_thrice)));
        assert_eq!(trace[105].decoded, Some(b'*'));
        assert_eq!(trace[106].decoded, Some(b'v'));
    }
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::integer_division_remainder_used,
    reason = "257 third-input/EOF classes and independent fold oracle"
)]
fn all_third_input_classes_reach_the_earlier_guest_fold_again() {
    let plan = open_suffix(&saved_fold_source(), THREE_INPUT_FOLD_SUFFIX);
    let profile = current_profile();
    let pristine = ProfileMachine::from_source(profile, &plan.source, vec![])
        .expect("source-loaded fold");
    let folded_twice = scalar_crazy(scalar_crazy(121, 3), 4);
    for third in (0..=255u32).chain(once(profile.eof_word())) {
        let mut input = vec![3, 4];
        if third != profile.eof_word() {
            input.push(u8::try_from(third).expect("byte"));
        }
        let mut vm = pristine.fork_with_input(input).expect("VM fork");
        assert_eq!(
            vm.run(110),
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 107,
            }),
            "third={third}"
        );
        let expected = scalar_crazy(folded_twice, scalar_crazy(57, third));
        assert_eq!(vm.memory_word(106), Ok(expected));
        assert_eq!(vm.output(), &[
            3,
            u8::try_from(folded_twice % 256).expect("fold low"),
            u8::try_from(third % 256).expect("third low"),
            u8::try_from(expected % 256).expect("three-input low"),
        ]);
    }
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::integer_division_remainder_used,
    reason = "all first and second byte/EOF marginals with a third-input fold"
)]
fn all_prior_input_classes_contribute_to_the_third_guest_fold() {
    let plan = open_suffix(&saved_fold_source(), THREE_INPUT_FOLD_SUFFIX);
    let profile = current_profile();
    let pristine = ProfileMachine::from_source(profile, &plan.source, vec![])
        .expect("source-admitted stateful fold");
    // The first two successful-byte marginals each vary independently,
    // holding a nontrivial third byte fixed. Real EOF cases are truncated
    // streams: input cannot resume after EOF has already been observed.
    let streams = (0..=255u8)
        .map(|first| vec![first, 4, 0x80])
        .chain((0..=255u8).map(|second| vec![3, second, 0x80]))
        .chain([vec![], vec![3]]);
    for input in streams {
        let raw = |index| {
            input
                .get(index)
                .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte))
        };
        let first = raw(0);
        let second = raw(1);
        let third = raw(2);
        let twice = scalar_crazy(scalar_crazy(121, first), second);
        let seeded = scalar_crazy(57, third);
        let thrice = scalar_crazy(twice, seeded);
        let low = |word| u8::try_from(word % 256).expect("low byte");
        let mut vm = pristine
            .fork_with_input(input.clone())
            .expect("independent VM memory");
        assert_eq!(
            vm.run(110),
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 107,
            }),
            "stdin={input:?}"
        );
        assert_eq!(vm.input_consumed(), input.len().min(3));
        assert_eq!(vm.memory_word(105), Ok(seeded));
        assert_eq!(vm.memory_word(106), Ok(thrice));
        assert_eq!(
            vm.output(),
            &[low(first), low(twice), low(third), low(thrice)],
            "stdin={input:?}"
        );
    }
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    reason = "pinned data-alias and code/data dependency negative controls"
)]
fn three_input_fold_requires_encrypted_pointer_and_two_real_data_writes() {
    use IndirectSourceSuffixError::{InvalidSuffix, NoSourceLoadablePointer};
    let original = saved_fold_source();
    let protected = (0..111).chain([124, 127, 134]).collect::<Vec<_>>();
    let plan = open_suffix(&original, THREE_INPUT_FOLD_SUFFIX);
    let invalid_suffix = plan_source_loaded_indirect_suffix(
        current_profile(),
        &original,
        111,
        117,
        117,
        b"/<oooojip<*v",
        &protected,
    );
    assert_eq!(invalid_suffix, Err(InvalidSuffix));
    // Executing protected M124 as anything other than its original p is
    // impossible without overwriting a live original pointer operand.
    let protected_conflict = plan_source_loaded_indirect_suffix(
        current_profile(),
        &original,
        111,
        117,
        117,
        b"/<oooojop<*v",
        &protected,
    );
    assert_eq!(protected_conflict, Err(NoSourceLoadablePointer));
    for altered_site in [118usize, 123, 125] {
        let mut mutated = plan.source.clone();
        mutated[altered_site] =
            graphical(u32::try_from(altered_site).expect("code index"), b'o')
                .expect("no-op source encoding");
        let mut vm =
            ProfileMachine::from_source(current_profile(), &mutated, vec![
                3, 4, 5,
            ])
            .expect("changed source remains graphical");
        let result = vm.run(110);
        assert!(
            result
                != Ok(RunOutcome::Terminated {
                    reason: Termination::HaltInstruction,
                    steps: 107,
                })
                || vm.output() != [3, 49, 5, 58],
            "site C{altered_site} mutation forged the guest-dependent fold"
        );
    }
}
