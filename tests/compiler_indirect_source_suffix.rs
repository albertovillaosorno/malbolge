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
// A terminal indirect transfer revisits actually encrypted previous code
// and returns to an earlier reached v, without faking a new guest output.
const THREE_INPUT_FOLD_RETURN_SUFFIX: &[u8] = b"/<oooojpp<*i";
// This second linear window reads a fourth word after the saved M106 fold,
// then legally rewrites an already executed and encrypted source code cell.
const FOUR_INPUT_CODE_ALIAS_SUFFIX: &[u8] = b"/<oooojpp<*/jojpv";
// A protected C134 i follows a fourth-input-dependent output and returns
// through previously encrypted code to the reached C82 v.
const FOUR_INPUT_COMPUTED_RETURN_SUFFIX: &[u8] = b"/<oooojpp<*/jojp<i";
// An encrypted prior output becomes an indirect D operand, so C132 folds
// the fourth raw word into the same M106 state as the first three reads.
const FOUR_INPUT_CUMULATIVE_SUFFIX: &[u8] = b"/<oooojpp<*/jjopv";
// The terminal i keeps that folded state and enters previously encrypted code.
const FOUR_INPUT_CUMULATIVE_RETURN_SUFFIX: &[u8] = b"/<oooojpp<*/jjopi";

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

#[test]
#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::integer_division_remainder_used,
    reason = "independent 257-class fourth-input source-code write oracle"
)]
fn all_fourth_input_classes_rewrite_only_the_finished_code_alias() {
    let original = saved_fold_source();
    let protected = (0..111).chain([124, 127, 134]).collect::<Vec<_>>();
    let plan = plan_source_loaded_indirect_suffix(
        current_profile(),
        &original,
        111,
        117,
        117,
        FOUR_INPUT_CODE_ALIAS_SUFFIX,
        &protected,
    )
    .expect("protected 17-opcode source continuation");
    assert_eq!(plan.source.len(), original.len());
    assert_eq!((plan.pointer_word, plan.landing_address), (116, 117));
    for position in [40usize, 54, 110, 124, 127, 134] {
        assert_eq!(plan.source[position], original[position]);
    }
    let profile = current_profile();
    let pristine = ProfileMachine::from_source(profile, &plan.source, vec![])
        .expect("strict N15 source loader");
    assert_eq!(pristine.memory_word(40), Ok(122));
    assert_eq!(pristine.memory_word(54), Ok(108));
    assert_eq!(pristine.memory_word(110), Ok(52));
    let twice = scalar_crazy(scalar_crazy(121, 3), 4);
    let thrice = scalar_crazy(twice, scalar_crazy(57, 5));
    for fourth in (0..=255u32).chain(once(profile.eof_word())) {
        let mut input = vec![3, 4, 5];
        if fourth != profile.eof_word() {
            input.push(u8::try_from(fourth).expect("byte input"));
        }
        let mut vm = pristine.fork_with_input(input.clone()).expect("VM fork");
        assert_eq!(
            vm.run(120),
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 112,
            }),
            "fourth={fourth}"
        );
        assert_eq!(vm.input_consumed(), input.len());
        assert_eq!(vm.output(), &[
            3,
            u8::try_from(twice % 256).expect("low fold"),
            5,
            u8::try_from(thrice % 256).expect("low fold"),
        ]);
        assert_eq!(vm.memory_word(105), Ok(scalar_crazy(57, 5)));
        assert_eq!(vm.memory_word(106), Ok(thrice));
        assert_eq!(
            vm.memory_word(40),
            Ok(scalar_crazy(63, fourth)),
            "fourth={fourth}"
        );
    }
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::integer_division_remainder_used,
    reason = "encrypted-code data provenance and negative mutations"
)]
fn fourth_input_code_rewrite_follows_real_encrypted_operands() {
    use malbolge::encrypt_profile_cell;
    let original = saved_fold_source();
    let protected = (0..111).chain([124, 127, 134]).collect::<Vec<_>>();
    let plan = plan_source_loaded_indirect_suffix(
        current_profile(),
        &original,
        111,
        117,
        117,
        FOUR_INPUT_CODE_ALIAS_SUFFIX,
        &protected,
    )
    .expect("source-admitted data alias");
    let mut vm =
        ProfileMachine::from_source(current_profile(), &plan.source, vec![
            3, 4, 5, 6,
        ])
        .expect("normative source loader");
    let mut trace = Vec::new();
    assert_eq!(
        vm.run_traced(120, &mut |step| trace.push(*step)),
        Ok(RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 112,
        })
    );
    assert_eq!(encrypt_profile_cell(122), Some(63));
    assert_eq!(encrypt_profile_cell(108), Some(39));
    for (step, after) in [(40, 63), (54, 39)] {
        assert_eq!(
            trace[usize::try_from(step).expect("step")]
                .before
                .registers
                .code_pointer,
            step
        );
        assert_eq!(
            trace[usize::try_from(step).expect("step")]
                .memory_delta
                .encryption
                .map(|write| write.after),
            Some(after),
        );
    }
    assert_eq!(trace[106].decoded, Some(b'/'));
    assert_eq!(trace[106].input, Some(TraceInput::Byte(6)));
    for (index, code, address, value, new_data_pointer) in
        [(107, 129, 110, 52, 53), (109, 131, 54, 39, 40)]
    {
        assert_eq!(trace[index].before.registers.code_pointer, code);
        assert_eq!(trace[index].decoded, Some(b'j'));
        assert_eq!(
            trace[index]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((address, value))
        );
        assert_eq!(trace[index].after.registers.data_pointer, new_data_pointer);
    }
    assert_eq!(trace[110].decoded, Some(b'p'));
    assert_eq!(
        trace[110]
            .memory_reads
            .data
            .map(|read| (read.address, read.value)),
        Some((40, 63))
    );
    assert_eq!(trace[110].after.registers.accumulator, scalar_crazy(63, 6));
    assert_eq!(vm.memory_word(40), Ok(scalar_crazy(63, 6)));
    assert_eq!(trace[111].decoded, Some(b'v'));
    // The prior M106 fold is not extended to four words; this separate
    // source-code scratch write is intentionally not a C23 checksum.
    assert_eq!(vm.memory_word(106), Ok(58));
    for altered_code in [128usize, 131, 132] {
        let mut changed = plan.source.clone();
        changed[altered_code] =
            graphical(u32::try_from(altered_code).expect("code site"), b'o')
                .expect("source-valid no-op mutation");
        let mut mutant =
            ProfileMachine::from_source(current_profile(), &changed, vec![
                3, 4, 5, 6,
            ])
            .expect("mutation is graphical");
        let outcome = mutant.run(120);
        assert!(
            outcome
                != Ok(RunOutcome::Terminated {
                    reason: Termination::HaltInstruction,
                    steps: 112,
                })
                || mutant.memory_word(40) != Ok(scalar_crazy(63, 6)),
            "mutation at C{altered_code} preserved an unearned fourth store"
        );
    }
}

// The terminal C128 i reads virgin source M109=66, transfers into earlier
// encrypted instructions, and eventually executes a *real* encrypted C82 v.
// This is control composition, not a source-C loop, EOF test or checksum.
#[expect(
    clippy::indexing_slicing,
    reason = "frozen 135-cell source has a valid M109 operand"
)]
fn saved_fold_return_plan() -> IndirectSourceSuffixPlan {
    let mut source = saved_fold_source();
    source[109] = 66;
    assert_eq!(
        decode_profile_instruction(66, 109),
        Some(b'v'),
        "indirect operand must be valid code at source position 109"
    );
    open_suffix(&source, THREE_INPUT_FOLD_RETURN_SUFFIX)
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::cognitive_complexity,
    reason = "real encrypted guest control return with full VM state checks"
)]
fn source_loaded_fold_indirectly_returns_to_earlier_encrypted_halt() {
    let original = saved_fold_source();
    let plan = saved_fold_return_plan();
    assert_eq!((plan.pointer_word, plan.landing_address), (116, 117));
    assert_eq!(plan.source.len(), 135);
    assert_eq!(plan.source[109], 66);
    for protected in [40usize, 54, 109, 110, 124, 127, 134] {
        assert_eq!(
            plan.source[protected],
            if protected == 109 {
                66
            } else {
                original[protected]
            }
        );
    }
    let mut vm =
        ProfileMachine::from_source(current_profile(), &plan.source, vec![
            3, 4, 5,
        ])
        .expect("fully graphical 135-cell N15 source");
    let mut trace = Vec::new();
    assert_eq!(
        vm.run_traced(140, &mut |step| trace.push(*step)),
        Ok(RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 123,
        })
    );
    let twice = scalar_crazy(scalar_crazy(121, 3), 4);
    let thrice = scalar_crazy(twice, scalar_crazy(57, 5));
    assert_eq!(vm.input_consumed(), 3);
    assert_eq!(vm.output(), [3, 49, 5, 58]);
    assert_eq!(vm.memory_word(105), Ok(scalar_crazy(57, 5)));
    assert_eq!(vm.memory_word(106), Ok(thrice));
    assert_eq!(trace[106].before.registers.code_pointer, 128);
    assert_eq!(trace[106].decoded, Some(b'i'));
    assert_eq!(
        trace[106]
            .memory_reads
            .data
            .map(|word| (word.address, word.value)),
        Some((109, 66))
    );
    assert_eq!(trace[106].after.registers.code_pointer, 67);
    assert_eq!(trace[107].before.registers.code_pointer, 67);
    assert_eq!(trace[122].before.registers.code_pointer, 82);
    assert_eq!(trace[122].decoded, Some(b'v'));
    // This terminal v is reached only after C82 was executed, encrypted
    // and used as code again: it is not an extra source-level v fixture.
    let first_c82 = trace
        .iter()
        .position(|step| step.before.registers.code_pointer == 82)
        .expect("first C82 instruction");
    assert!(first_c82 < 106);
    assert_eq!(trace[first_c82].decoded, Some(b'/'));
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::integer_division_remainder_used,
    reason = "257 real third-input classes through indirect guest reentry"
)]
fn terminal_guest_reentry_preserves_all_third_input_classes() {
    let plan = saved_fold_return_plan();
    let profile = current_profile();
    let pristine = ProfileMachine::from_source(profile, &plan.source, vec![])
        .expect("one admitted source, independent stdin forks");
    let twice = scalar_crazy(scalar_crazy(121, 3), 4);
    for third in (0..=255u32).chain(once(profile.eof_word())) {
        let mut input = vec![3, 4];
        if third != profile.eof_word() {
            input.push(u8::try_from(third).expect("byte"));
        }
        let mut vm = pristine.fork_with_input(input.clone()).expect("VM fork");
        assert_eq!(
            vm.run(140),
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 123,
            }),
            "third={third}"
        );
        let expected = scalar_crazy(twice, scalar_crazy(57, third));
        assert_eq!(vm.input_consumed(), input.len());
        assert_eq!(vm.memory_word(106), Ok(expected));
        assert_eq!(
            vm.output(),
            [
                3,
                u8::try_from(twice % 256).expect("low byte"),
                u8::try_from(third % 256).expect("third byte"),
                u8::try_from(expected % 256).expect("fold byte"),
            ],
            "third={third}"
        );
    }
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    reason = "two authentic source-controlled indirect transfer negatives"
)]
fn terminal_indirect_return_requires_its_encrypted_data_operand() {
    let plan = saved_fold_return_plan();
    let mut no_return = plan.source.clone();
    no_return[128] = graphical(128, b'v').expect("source-valid halt");
    let mut direct =
        ProfileMachine::from_source(current_profile(), &no_return, vec![
            3, 4, 5,
        ])
        .expect("changed source is still valid");
    assert_eq!(
        direct.run(140),
        Ok(RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 107,
        })
    );
    let mut old_data = plan.source;
    old_data[109] = saved_fold_source()[109];
    let mut missing =
        ProfileMachine::from_source(current_profile(), &old_data, vec![
            3, 4, 5,
        ])
        .expect("changed source is still valid");
    assert_ne!(
        missing.run(140),
        Ok(RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 123,
        }),
        "terminal i cannot claim a halt from the old pointer"
    );
    assert_eq!(
        plan_source_loaded_indirect_suffix(
            current_profile(),
            &saved_fold_source(),
            111,
            117,
            117,
            b"/<ioojpp<*i",
            &(0..111).collect::<Vec<_>>()
        ),
        Err(IndirectSourceSuffixError::InvalidSuffix),
        "interior i is not a linear suffix"
    );
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::integer_division_remainder_used,
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "two 256-class marginals and truncated EOF reads checked in guest"
)]
fn terminal_return_preserves_live_first_and_second_fold_inputs() {
    let plan = saved_fold_return_plan();
    let profile = current_profile();
    let pristine = ProfileMachine::from_source(profile, &plan.source, vec![])
        .expect("source-valid terminal indirect return");
    for vary_first in [true, false] {
        for byte in 0..=255u8 {
            let first = if vary_first {
                byte
            } else {
                3
            };
            let second = if vary_first {
                4
            } else {
                byte
            };
            let input = vec![first, second, 128];
            let mut vm =
                pristine.fork_with_input(input.clone()).expect("VM fork");
            assert_eq!(
                vm.run(140),
                Ok(RunOutcome::Terminated {
                    reason: Termination::HaltInstruction,
                    steps: 123,
                }),
                "vary_first={vary_first} byte={byte}"
            );
            let twice = scalar_crazy(
                scalar_crazy(121, u32::from(first)),
                u32::from(second),
            );
            let thrice = scalar_crazy(twice, scalar_crazy(57, 128));
            assert_eq!(vm.input_consumed(), input.len());
            assert_eq!(vm.memory_word(106), Ok(thrice));
            assert_eq!(
                vm.output(),
                [
                    first,
                    u8::try_from(twice % 256).expect("low second fold"),
                    128,
                    u8::try_from(thrice % 256).expect("low third fold"),
                ],
                "vary_first={vary_first} byte={byte}"
            );
        }
    }
    // EOF is a *missing read*, not a forged 257th stdin byte. A suffix
    // following true EOF must still reach the same physical encrypted halt.
    for input in [vec![], vec![0], vec![255], vec![0, 255]] {
        let raw = |index| {
            input
                .get(index)
                .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte))
        };
        let twice = scalar_crazy(scalar_crazy(121, raw(0)), raw(1));
        let thrice = scalar_crazy(twice, scalar_crazy(57, raw(2)));
        let mut vm = pristine.fork_with_input(input.clone()).expect("VM fork");
        assert_eq!(
            vm.run(140),
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 123,
            }),
            "input={input:?}"
        );
        assert_eq!(vm.input_consumed(), input.len());
        assert_eq!(vm.memory_word(106), Ok(thrice));
        assert_eq!(vm.output(), [
            u8::try_from(raw(0) % 256).expect("first low"),
            u8::try_from(twice % 256).expect("second low"),
            u8::try_from(raw(2) % 256).expect("third low"),
            u8::try_from(thrice % 256).expect("third fold low"),
        ]);
    }
}

// The complete bounded source-code operand census prevents a fourth raw
// input attempt from being mistaken for a live fourth-input computation.
// Freeze C109=33..126, stdin 03 04 05 06, max 180 real N15 steps.
#[test]
#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    reason = "94 finite source pointers and actual VM I/O classification"
)]
fn terminal_return_pointer_census_identifies_noncomputing_fourth_reads() {
    let baseline =
        open_suffix(&saved_fold_source(), THREE_INPUT_FOLD_RETURN_SUFFIX);
    let mut admissible = 0usize;
    let mut halts = 0usize;
    let mut fourth_read = 0usize;
    for word in 33..=126u8 {
        let mut source = baseline.source.clone();
        source[109] = word;
        if layout::admit_c23_probe_graphical_source(&source).is_err() {
            continue;
        }
        admissible += 1;
        let mut vm =
            ProfileMachine::from_source(current_profile(), &source, vec![
                3, 4, 5, 6,
            ])
            .expect("source-valid candidate");
        let mut trace = Vec::new();
        let outcome = vm.run_traced(180, &mut |step| trace.push(*step));
        assert_eq!(trace[106].before.registers.code_pointer, 128);
        assert_eq!(trace[106].decoded, Some(b'i'));
        let reads = trace.iter().filter(|step| step.input.is_some()).count();
        if reads == 4 {
            fourth_read += 1;
        }
        if matches!(
            outcome,
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                ..
            })
        ) {
            halts += 1;
        }
    }
    assert_eq!((admissible, fourth_read, halts), (8, 3, 6));
    // These two source-valid indirect paths reach another real / and v,
    // but the fourth input is overwritten before any dependent output.
    for (word, steps, expected) in [
        (83u8, 156, vec![3, 49, 5, 58]),
        (118, 161, vec![3, 49, 5, 58, 197]),
    ] {
        let mut source = baseline.source.clone();
        source[109] = word;
        for input in [
            vec![3, 4, 5],
            vec![3, 4, 5, 0],
            vec![3, 4, 5, 6],
            vec![3, 4, 5, 255],
            vec![3, 4, 5, 6, 7],
        ] {
            let mut vm = ProfileMachine::from_source(
                current_profile(),
                &source,
                input.clone(),
            )
            .expect("strict N15 loader");
            let mut trace = Vec::new();
            assert_eq!(
                vm.run_traced(180, &mut |step| trace.push(*step)),
                Ok(RunOutcome::Terminated {
                    reason: Termination::HaltInstruction,
                    steps,
                }),
                "operand={word}, stdin={input:?}"
            );
            let reads = trace
                .iter()
                .filter(|step| step.input.is_some())
                .collect::<Vec<_>>();
            assert_eq!(reads.len(), 4);
            assert_eq!(reads[3].before.registers.code_pointer, 126);
            assert_eq!(vm.input_consumed(), input.len().min(4));
            assert_eq!(vm.output(), expected, "operand={word} stdin={input:?}");
            assert_eq!(vm.memory_word(106), Ok(58));
        }
    }
}

#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    reason = "C134 is a protected graphical source word in the frozen guest"
)]
fn fourth_fold_return_plan() -> IndirectSourceSuffixPlan {
    let original = saved_fold_source();
    assert_eq!(
        decode_profile_instruction(u32::from(original[134]), 134),
        Some(b'i'),
        "protected source M134 must execute as i"
    );
    let protected = (0..111).chain([124, 127, 134]).collect::<Vec<_>>();
    plan_source_loaded_indirect_suffix(
        current_profile(),
        &original,
        111,
        117,
        117,
        FOUR_INPUT_COMPUTED_RETURN_SUFFIX,
        &protected,
    )
    .expect("source-loaded fourth-input computed return")
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::integer_division_remainder_used,
    clippy::cognitive_complexity,
    reason = "all 257 fourth-input classes run the normative physical guest"
)]
fn fourth_input_computation_is_output_and_valid_halt_for_every_byte_and_eof() {
    let original = saved_fold_source();
    let plan = fourth_fold_return_plan();
    assert_eq!((plan.pointer_word, plan.landing_address), (116, 117));
    assert_eq!(plan.source.len(), original.len());
    for at in [40usize, 42, 54, 110, 124, 127, 134] {
        assert_eq!(plan.source[at], original[at]);
    }
    assert_eq!(
        layout::admit_c23_probe_graphical_source(&plan.source),
        Ok(())
    );
    let profile = current_profile();
    let pristine = ProfileMachine::from_source(profile, &plan.source, vec![])
        .expect("strictly admitted original N15 source");
    let twice = scalar_crazy(scalar_crazy(121, 3), 4);
    let thrice = scalar_crazy(twice, scalar_crazy(57, 5));
    for fourth in (0..=255u32).chain(once(profile.eof_word())) {
        let mut input = vec![3, 4, 5];
        if fourth != profile.eof_word() {
            input.push(u8::try_from(fourth).expect("binary byte"));
        }
        let mut vm =
            pristine.fork_with_input(input.clone()).expect("stdin fork");
        assert_eq!(
            vm.run(150),
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 137,
            }),
            "fourth={fourth}"
        );
        let fourth_result = scalar_crazy(63, fourth);
        assert_eq!(vm.input_consumed(), input.len());
        assert_eq!(vm.memory_word(106), Ok(thrice));
        assert_eq!(vm.memory_word(40), Ok(fourth_result));
        assert_eq!(vm.output(), [
            3,
            u8::try_from(twice % 256).expect("second fold byte"),
            5,
            u8::try_from(thrice % 256).expect("third fold byte"),
            u8::try_from(fourth_result % 256).expect("fourth result byte"),
        ]);
    }
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::cognitive_complexity,
    reason = "trace sites are frozen by source and actual VM execution"
)]
fn fourth_computed_output_returns_through_source_protected_indirect_code() {
    use malbolge::encrypt_profile_cell;
    let plan = fourth_fold_return_plan();
    let mut vm =
        ProfileMachine::from_source(current_profile(), &plan.source, vec![
            3, 4, 5, 6,
        ])
        .expect("strict N15 source");
    let mut trace = Vec::new();
    assert_eq!(
        vm.run_traced(150, &mut |step| trace.push(*step)),
        Ok(RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 137,
        })
    );
    assert_eq!(encrypt_profile_cell(u32::from(plan.source[42])), Some(58));
    assert_eq!(
        trace[42].memory_delta.encryption.map(|write| write.after),
        Some(58)
    );
    assert_eq!(trace[106].before.registers.code_pointer, 128);
    assert_eq!(trace[106].decoded, Some(b'/'));
    assert_eq!(trace[106].input, Some(TraceInput::Byte(6)));
    assert_eq!(trace[110].before.registers.code_pointer, 132);
    assert_eq!(trace[110].decoded, Some(b'p'));
    assert_eq!(
        trace[110]
            .memory_reads
            .data
            .map(|read| (read.address, read.value)),
        Some((40, 63))
    );
    assert_eq!(trace[110].after.registers.accumulator, scalar_crazy(63, 6));
    assert_eq!(trace[111].before.registers.code_pointer, 133);
    assert_eq!(trace[111].decoded, Some(b'<'));
    assert_eq!(trace[111].output, Some(77));
    assert_eq!(trace[112].before.registers.code_pointer, 134);
    assert_eq!(trace[112].decoded, Some(b'i'));
    assert_eq!(
        trace[112]
            .memory_reads
            .data
            .map(|read| (read.address, read.value)),
        Some((42, 58))
    );
    assert_eq!(trace[112].after.registers.code_pointer, 59);
    assert_eq!(trace[113].before.registers.code_pointer, 59);
    assert_eq!(trace[136].before.registers.code_pointer, 82);
    assert_eq!(trace[136].decoded, Some(b'v'));
    assert_eq!(trace[82].before.registers.code_pointer, 82);
    assert_eq!(trace[82].decoded, Some(b'/'));
    assert_eq!(vm.output(), [3, 49, 5, 58, 77]);
    assert_eq!(vm.memory_word(40), Ok(scalar_crazy(63, 6)));
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::integer_division_remainder_used,
    clippy::indexing_slicing,
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "finite independently justified prior-input marginals and EOF"
)]
fn fourth_computed_return_keeps_all_previous_input_dependencies() {
    let plan = fourth_fold_return_plan();
    let profile = current_profile();
    let pristine = ProfileMachine::from_source(profile, &plan.source, vec![])
        .expect("source-backed immutable candidate");
    for vary in 0..3usize {
        for byte in 0..=255u8 {
            let mut input = vec![3, 4, 5, 128];
            input[vary] = byte;
            let mut vm =
                pristine.fork_with_input(input.clone()).expect("input fork");
            let first = u32::from(input[0]);
            let second = u32::from(input[1]);
            let third = u32::from(input[2]);
            let twice = scalar_crazy(scalar_crazy(121, first), second);
            let thrice = scalar_crazy(twice, scalar_crazy(57, third));
            let fourth = scalar_crazy(63, 128);
            assert_eq!(
                vm.run(150),
                Ok(RunOutcome::Terminated {
                    reason: Termination::HaltInstruction,
                    steps: 137,
                }),
                "vary={vary} byte={byte}"
            );
            assert_eq!(vm.input_consumed(), 4);
            assert_eq!(vm.memory_word(106), Ok(thrice));
            assert_eq!(vm.memory_word(40), Ok(fourth));
            assert_eq!(vm.output(), [
                u8::try_from(first).expect("first input byte"),
                u8::try_from(twice % 256).expect("two-input fold byte"),
                u8::try_from(third % 256).expect("third byte"),
                u8::try_from(thrice % 256).expect("three-input fold byte"),
                u8::try_from(fourth % 256).expect("fourth byte"),
            ]);
        }
    }
    for input in [vec![], vec![0], vec![255], vec![0, 255], vec![
        3, 4, 5, 6, 7,
    ]] {
        let raw = |index| {
            input
                .get(index)
                .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte))
        };
        let twice = scalar_crazy(scalar_crazy(121, raw(0)), raw(1));
        let thrice = scalar_crazy(twice, scalar_crazy(57, raw(2)));
        let fourth = scalar_crazy(63, raw(3));
        let mut vm =
            pristine.fork_with_input(input.clone()).expect("input fork");
        assert_eq!(
            vm.run(150),
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 137,
            }),
            "stdin={input:?}"
        );
        assert_eq!(vm.input_consumed(), input.len().min(4));
        assert_eq!(vm.memory_word(106), Ok(thrice));
        assert_eq!(vm.memory_word(40), Ok(fourth));
        assert_eq!(vm.output(), [
            u8::try_from(raw(0) % 256).expect("first input low"),
            u8::try_from(twice % 256).expect("second fold low"),
            u8::try_from(raw(2) % 256).expect("third input low"),
            u8::try_from(thrice % 256).expect("third fold low"),
            u8::try_from(fourth % 256).expect("fourth low"),
        ]);
    }
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    reason = "finite source graphical negative opcode controls"
)]
fn fourth_computed_return_requires_reached_input_store_and_output() {
    let plan = fourth_fold_return_plan();
    for changed in [128usize, 132, 133] {
        let mut source = plan.source.clone();
        source[changed] =
            graphical(u32::try_from(changed).expect("source site"), b'o')
                .expect("source no-op");
        let mut vm =
            ProfileMachine::from_source(current_profile(), &source, vec![
                3, 4, 5, 6,
            ])
            .expect("graphical mutation");
        let outcome = vm.run(150);
        assert!(
            outcome
                != Ok(RunOutcome::Terminated {
                    reason: Termination::HaltInstruction,
                    steps: 137,
                })
                || vm.output() != [3, 49, 5, 58, 77]
                || vm.memory_word(40) != Ok(scalar_crazy(63, 6)),
            "altered C{changed} forged real fourth computation"
        );
    }
}

// M110=117 is a source-loadable pointer read by C129 j. C130 j then reads
// the previously encrypted C118 output opcode as 104, restoring D=105;
// C131 o advances to D=106 for a live M106 crazy write at C132.
#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    reason = "fixed 135-cell saved state and protected source operands"
)]
fn fourth_cumulative_plan(suffix: &[u8]) -> IndirectSourceSuffixPlan {
    let original = saved_fold_source();
    let protected = (0..111).chain([124, 127, 134]).collect::<Vec<_>>();
    let mut plan = plan_source_loaded_indirect_suffix(
        current_profile(),
        &original,
        111,
        117,
        117,
        suffix,
        &protected,
    )
    .expect("source-loadable fourth fold continuation");
    plan.source[110] = 117;
    assert_eq!(
        layout::admit_c23_probe_graphical_source(&plan.source),
        Ok(()),
        "entire fourth-fold source must be loader legal"
    );
    assert_eq!(
        plan.source[118],
        graphical(118, b'<').expect("saved output"),
        "C118 must become a real encrypted relocation operand"
    );
    assert_eq!(plan.source[124], 126, "protected M124 pointer");
    assert_eq!(plan.source[127], 100, "protected M127 pointer");
    assert_eq!(plan.source[134], 58, "protected M134 pointer");
    plan
}

#[expect(
    clippy::integer_division_remainder_used,
    clippy::expect_used,
    reason = "finite low-byte projection is independently computed"
)]
fn fourth_fold_expected(
    first: u32,
    second: u32,
    third: u32,
    fourth: u32,
) -> (u32, [u8; 4]) {
    let twice = scalar_crazy(scalar_crazy(121, first), second);
    let thrice = scalar_crazy(twice, scalar_crazy(57, third));
    let fourfold = scalar_crazy(thrice, fourth);
    (fourfold, [
        u8::try_from(first % 256).expect("raw first byte"),
        u8::try_from(twice % 256).expect("folded second byte"),
        u8::try_from(third % 256).expect("raw third byte"),
        u8::try_from(thrice % 256).expect("folded third byte"),
    ])
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    reason = "four full raw input marginals and EOF are bounded N15 guests"
)]
fn fourth_input_updates_the_same_three_input_fold_and_reaches_a_real_halt() {
    let plan = fourth_cumulative_plan(FOUR_INPUT_CUMULATIVE_SUFFIX);
    let profile = current_profile();
    let pristine = ProfileMachine::from_source(profile, &plan.source, vec![])
        .expect("source loader accepts the exact protected route");
    let verify = |input: Vec<u8>| {
        let raw = |at| {
            input
                .get(at)
                .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte))
        };
        let (fourfold, output) =
            fourth_fold_expected(raw(0), raw(1), raw(2), raw(3));
        let mut vm =
            pristine.fork_with_input(input.clone()).expect("stdin fork");
        assert_eq!(
            vm.run(130),
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 112,
            }),
            "stdin={input:?}",
        );
        assert_eq!(vm.input_consumed(), input.len().min(4));
        assert_eq!(vm.memory_word(106), Ok(fourfold), "stdin={input:?}");
        assert_eq!(vm.output(), output, "stdin={input:?}");
    };
    for fourth in 0..=255u8 {
        verify(vec![3, 4, 5, fourth]);
    }
    for vary in 0..3usize {
        for byte in 0..=255u8 {
            let mut input = vec![3, 4, 5, 0x80];
            input[vary] = byte;
            verify(input);
        }
    }
    for input in [vec![], vec![0], vec![255], vec![3, 4], vec![3, 4, 5], vec![
        3, 4, 5, 6, 7,
    ]] {
        verify(input);
    }
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "fixed guest trace asserts ordered physical transitions"
)]
fn fourth_cumulative_store_consumes_an_encrypted_pointer_and_prior_guest_state()
{
    use malbolge::encrypt_profile_cell;
    let plan = fourth_cumulative_plan(FOUR_INPUT_CUMULATIVE_SUFFIX);
    let original = saved_fold_source();
    for at in (0..135).filter(|at| {
        ![
            110, 111, 117, 118, 119, 120, 121, 122, 123, 125, 126, 128, 129,
            130, 131, 132, 133,
        ]
        .contains(at)
    }) {
        assert_eq!(plan.source[at], original[at], "C{at} changed");
    }
    assert_eq!(encrypt_profile_cell(u32::from(plan.source[118])), Some(104));
    let mut vm =
        ProfileMachine::from_source(current_profile(), &plan.source, vec![
            3, 4, 5, 6,
        ])
        .expect("strict source VM");
    let mut trace = Vec::new();
    assert_eq!(
        vm.run_traced(130, &mut |step| trace.push(*step)),
        Ok(RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 112,
        })
    );
    assert_eq!(trace[96].before.registers.code_pointer, 118);
    assert_eq!(trace[96].decoded, Some(b'<'));
    assert_eq!(
        trace[96].memory_delta.encryption.map(|write| write.after),
        Some(104)
    );
    assert_eq!(trace[106].before.registers.code_pointer, 128);
    assert_eq!(trace[106].input, Some(TraceInput::Byte(6)));
    for (index, code, at, value, resulting_pointer) in
        [(107, 129, 110, 117, 118), (108, 130, 118, 104, 105)]
    {
        let step = &trace[index];
        assert_eq!(step.before.registers.code_pointer, code);
        assert_eq!(step.decoded, Some(b'j'));
        assert_eq!(
            step.memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((at, value))
        );
        assert_eq!(step.after.registers.data_pointer, resulting_pointer);
    }
    assert_eq!(trace[109].before.registers.code_pointer, 131);
    assert_eq!(trace[109].decoded, Some(b'o'));
    assert_eq!(trace[110].before.registers.code_pointer, 132);
    assert_eq!(trace[110].decoded, Some(b'p'));
    assert_eq!(
        trace[110]
            .memory_reads
            .data
            .map(|read| (read.address, read.value)),
        Some((106, 58))
    );
    assert_eq!(
        trace[110].memory_delta.data.map(|write| (
            write.address,
            write.before,
            write.after
        )),
        Some((106, 58, scalar_crazy(58, 6)))
    );
    assert_eq!(trace[110].after.registers.accumulator, scalar_crazy(58, 6));
    assert_eq!(trace[111].before.registers.code_pointer, 133);
    assert_eq!(trace[111].decoded, Some(b'v'));
    assert_eq!(vm.output(), [3, 49, 5, 58]);
    assert_eq!(vm.memory_word(106), Ok(scalar_crazy(58, 6)));
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    reason = "source-mutation controls cannot counterfeit physical M106 input"
)]
fn fourth_cumulative_fold_fails_when_guest_input_or_relocation_is_removed() {
    let plan = fourth_cumulative_plan(FOUR_INPUT_CUMULATIVE_SUFFIX);
    let expected = scalar_crazy(58, 6);
    for changed in [110usize, 128, 129, 130, 132] {
        let mut source = plan.source.clone();
        source[changed] = if changed == 110 {
            52
        } else {
            graphical(u32::try_from(changed).expect("code cell"), b'o')
                .expect("source-loadable no-op")
        };
        let mut vm =
            ProfileMachine::from_source(current_profile(), &source, vec![
                3, 4, 5, 6,
            ])
            .expect("mutant is still graphical");
        let outcome = vm.run(130);
        assert!(
            outcome
                != Ok(RunOutcome::Terminated {
                    reason: Termination::HaltInstruction,
                    steps: 112,
                })
                || vm.memory_word(106) != Ok(expected)
                || vm.input_consumed() != 4,
            "C{changed} mutation forged a fourth live M106 fold"
        );
    }
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "fixed guest trace and fourth-input return census"
)]
fn fourth_cumulative_state_survives_a_real_indirect_return_to_encrypted_code() {
    let plan = fourth_cumulative_plan(FOUR_INPUT_CUMULATIVE_RETURN_SUFFIX);
    let profile = current_profile();
    let pristine = ProfileMachine::from_source(profile, &plan.source, vec![])
        .expect("strict graphical source");
    let twice = scalar_crazy(scalar_crazy(121, 3), 4);
    let thrice = scalar_crazy(twice, scalar_crazy(57, 5));
    assert_eq!(thrice, 58);
    for fourth in (0..=255u32).chain(once(profile.eof_word())) {
        let mut input = vec![3, 4, 5];
        if fourth != profile.eof_word() {
            input.push(u8::try_from(fourth).expect("input byte"));
        }
        let mut vm =
            pristine.fork_with_input(input.clone()).expect("stdin fork");
        assert_eq!(
            vm.run(170),
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 139,
            }),
            "fourth={fourth}",
        );
        assert_eq!(vm.input_consumed(), input.len());
        assert_eq!(vm.memory_word(106), Ok(scalar_crazy(thrice, fourth)));
        // The extra output is produced by a later rotation of a fixed word;
        // it must not be mistaken for the new folded checksum byte.
        assert_eq!(vm.output(), [3, 49, 5, 58, 87]);
    }
    let mut vm = pristine
        .fork_with_input(vec![3, 4, 5, 6])
        .expect("tracked fourth input");
    let mut trace = Vec::new();
    assert_eq!(
        vm.run_traced(170, &mut |step| trace.push(*step)),
        Ok(RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 139,
        }),
    );
    assert_eq!(trace[110].before.registers.code_pointer, 132);
    assert_eq!(trace[110].decoded, Some(b'p'));
    assert_eq!(
        trace[110]
            .memory_reads
            .data
            .map(|read| (read.address, read.value)),
        Some((106, 58)),
    );
    assert_eq!(trace[111].before.registers.code_pointer, 133);
    assert_eq!(trace[111].decoded, Some(b'i'));
    assert_eq!(
        trace[111]
            .memory_reads
            .data
            .map(|read| (read.address, read.value)),
        Some((107, 55)),
    );
    assert_eq!(trace[112].before.registers.code_pointer, 56);
    assert_eq!(trace[112].decoded, Some(b'*'));
    assert_eq!(trace[113].before.registers.code_pointer, 57);
    assert_eq!(trace[113].decoded, Some(b'<'));
    assert_eq!(trace[113].output, Some(87));
    assert_eq!(trace[138].before.registers.code_pointer, 82);
    assert_eq!(trace[138].decoded, Some(b'v'));
    assert_eq!(vm.memory_word(106), Ok(scalar_crazy(58, 6)));
}
