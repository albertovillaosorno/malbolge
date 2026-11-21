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
//   - Source-loaded parametric C32 adjacent literal materialization.
// - Must-Not:
//   - Treat a constant source as signed input normalization or an EOF loop.
// - Allows:
//   - Inputs: canonical N15, 94 no-op prefixes by 94 graphical tail bytes.
//   - Outputs: adjacent exact C32 words from bounded normative guest runs.
//   - Side effects: isolated VM execution without staged artifact publication.
// - Split-When:
//   - A general source-linked guest C32 constant allocator replaces this plan.
// - Merge-When:
//   - Complete mutable checksum compilation subsumes physical C32 writes.
// - Summary:
//   - Proves a finite multiple-literal source emitter without memory seeding.

//! Source-loaded C32 constants require real executable operations and loaders.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::{BTreeMap, BTreeSet};

use malbolge::{
    ProfileMachine, RunOutcome, Termination, current_profile,
    decode_profile_instruction, historical_profile,
};

const MODULUS: u32 = 14_348_907;
const PREFIX_BOUND: usize = 94;

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    clippy::as_conversions,
    clippy::indexing_slicing,
    reason = "independent 15-trit arithmetic loader and rotate oracles"
)]
fn scalar_crazy(mut left: u32, mut right: u32) -> u32 {
    const TABLE: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut result = 0;
    let mut place = 1;
    for _ in 0usize..15usize {
        result += TABLE[(left % 3) as usize][(right % 3) as usize] * place;
        left /= 3;
        right /= 3;
        place *= 3;
    }
    result
}

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division,
    clippy::integer_division_remainder_used,
    reason = "independent fifteen-trit right rotation"
)]
const fn scalar_rotate(seed: u32) -> u32 {
    seed / 3 + seed % 3 * 4_782_969
}

fn encoded(position: usize, opcode: u8) -> Result<u8, String> {
    (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(
                u32::from(*byte),
                u32::try_from(position).unwrap_or(u32::MAX),
            ) == Some(opcode)
        })
        .ok_or_else(|| format!("no graphical {opcode} at {position}"))
}

// Independently derive expanded words without asking production layout for
// loader memory. The recurrence after two source-tail words has period six.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::indexing_slicing,
    clippy::integer_division_remainder_used,
    reason = "finite six-phase independent source-tail memory oracle"
)]
fn original_seed_pair(source: &[u8], data_base: usize) -> [u32; 2] {
    let mut older = u32::from(source[source.len() - 2]);
    let mut newer = u32::from(source[source.len() - 1]);
    for _ in 0..=(data_base - source.len()) % 6 {
        let next = scalar_crazy(older, newer);
        older = newer;
        newer = next;
    }
    [newer, scalar_crazy(older, newer)]
}

fn graphical_tail(last: u8, position: usize) -> bool {
    decode_profile_instruction(
        u32::from(last),
        u32::try_from(position).unwrap_or(u32::MAX),
    )
    .is_some_and(|opcode| {
        matches!(
            opcode,
            b'j' | b'i' | b'*' | b'p' | b'v' | b'o' | b'/' | b'<'
        )
    })
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    reason = "frozen exhaustive 94-by-94 graphical source-seed oracle"
)]
fn source_loaded_c32_emitter_matches_all_bounded_loader_candidates()
-> Result<(), String> {
    let profile = current_profile();
    let mut supported = BTreeMap::<u32, Vec<u8>>::new();
    let mut viable_prefixes = 0usize;
    let mut allowed_suffixes = 0usize;
    let mut source_valid_literals = 0usize;
    for noops in 0..PREFIX_BOUND {
        let mut source = (0..noops)
            .map(|position| encoded(position, b'o'))
            .collect::<Result<Vec<_>, _>>()?;
        for opcode in b"j**v" {
            source.push(encoded(source.len(), *opcode)?);
        }
        let data_base = usize::from(source[noops]) + 1;
        if data_base <= source.len()
            || data_base
                >= usize::try_from(profile.memory_words())
                    .map_err(|error| error.to_string())?
                    - 1
        {
            continue;
        }
        viable_prefixes += 1;
        for last in 33..=126u8 {
            if !graphical_tail(last, source.len()) {
                continue;
            }
            allowed_suffixes += 1;
            source.push(last);
            let seeds = original_seed_pair(&source, data_base);
            let target = seeds.map(scalar_rotate);
            let value = u64::from(target[0])
                + u64::from(target[1]) * u64::from(MODULUS);
            if let Ok(bits) = u32::try_from(value) {
                source_valid_literals += 1;
                _ = supported.entry(bits).or_insert_with(|| source.clone());
            }
            _ = source.pop();
        }
    }
    assert_eq!(viable_prefixes, 66);
    assert_eq!(allowed_suffixes, 528);
    assert_eq!(source_valid_literals, 180);
    assert_eq!(supported.len(), 164);
    assert_eq!(supported.get(&351_548_234), Some(&b"(&%N$".to_vec()));
    for (bits, expected_source) in &supported {
        let candidate =
            layout::build_c32_literal_loader_rotate_source(profile, *bits)
                .map_err(|error| format!("{bits}: {error:?}"))?;
        assert_eq!(&candidate, expected_source, "literal {bits:#x}");
    }
    Ok(())
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "five real source-loaded guest traces and physical write checks"
)]
fn real_vm_stores_selected_c32_constants_after_variable_noop_prefixes()
-> Result<(), String> {
    let profile = current_profile();
    let cases = [
        (351_548_234u32, 0usize),
        (284_586_666, 1),
        (667_224_150, 2),
        (255_888_851, 7),
        (337_199_311, 8),
    ];
    for (bits, expected_noops) in cases {
        let source =
            layout::build_c32_literal_loader_rotate_source(profile, bits)
                .map_err(|error| format!("{bits}: {error:?}"))?;
        let noops = source.len() - 5;
        assert_eq!(noops, expected_noops);
        assert!(noops < PREFIX_BOUND);
        assert_eq!(source.len(), noops + 5);
        let data_base = u32::from(source[noops]) + 1;
        assert!(
            data_base
                >= u32::try_from(source.len())
                    .map_err(|error| error.to_string())?
        );
        let seeded = original_seed_pair(
            &source,
            usize::try_from(data_base).map_err(|error| error.to_string())?,
        );
        let targets = seeded.map(scalar_rotate);
        let plan = layout::plan_c32_literal_rotate_writes(profile, bits)
            .map_err(|error| format!("{error:?}"))?;
        assert_eq!(plan.initial_data_words, seeded);
        assert_eq!(plan.target_cells, targets);
        for (step, opcode) in b"j**v".iter().enumerate() {
            assert_eq!(
                decode_profile_instruction(
                    u32::from(source[noops + step]),
                    u32::try_from(noops + step)
                        .map_err(|error| error.to_string())?,
                ),
                Some(*opcode)
            );
        }
        for input in [vec![], vec![0, 255, 128]] {
            let mut vm = ProfileMachine::from_source(profile, &source, input)
                .map_err(|error| error.to_string())?;
            assert_eq!(vm.memory_word(data_base), Ok(seeded[0]));
            assert_eq!(vm.memory_word(data_base + 1), Ok(seeded[1]));
            let mut trace = Vec::new();
            let outcome = vm
                .run_traced(noops + 4, &mut |step| trace.push(*step))
                .map_err(|error| error.to_string())?;
            assert_eq!(outcome, RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: noops + 4,
            });
            assert_eq!(trace.len(), noops + 4);
            for step in trace.iter().take(noops) {
                assert_eq!(step.decoded, Some(b'o'));
                assert!(step.memory_delta.encryption.is_some());
            }
            assert_eq!(trace[noops].decoded, Some(b'j'));
            assert_eq!(trace[noops].after.registers.data_pointer, data_base);
            for (index, word) in seeded.iter().enumerate() {
                let step = &trace[noops + index + 1];
                let data = data_base
                    + u32::try_from(index)
                        .map_err(|error| error.to_string())?;
                assert_eq!(step.decoded, Some(b'*'));
                assert_eq!(step.before.registers.data_pointer, data);
                assert_eq!(
                    step.memory_reads
                        .data
                        .map(|read| (read.address, read.value)),
                    Some((data, *word))
                );
                assert_eq!(step.after.registers.accumulator, targets[index]);
                assert_eq!(vm.memory_word(data), Ok(targets[index]));
                assert!(step.memory_delta.encryption.is_some());
            }
            assert_eq!(trace[noops + 3].decoded, Some(b'v'));
            assert_eq!(vm.input_consumed(), 0);
            assert_eq!(vm.output(), &[]);
        }
    }
    Ok(())
}

#[test]
fn unsupported_c32_literals_and_profiles_fail_before_source_emission() {
    use layout::C32LiteralLoadedSourceError as Error;
    assert_eq!(
        layout::build_c32_literal_loader_rotate_source(
            historical_profile(),
            351_548_234
        ),
        Err(Error::UnsupportedProfile)
    );
    assert_eq!(
        layout::build_c32_literal_loader_arithmetic_source(
            historical_profile(),
            351_548_234
        ),
        Err(Error::UnsupportedProfile)
    );
    assert_eq!(
        layout::build_c32_literal_after_input_source(
            historical_profile(),
            351_548_234
        ),
        Err(Error::UnsupportedProfile)
    );
    for bits in [0, 255, u32::MAX] {
        assert_eq!(
            layout::build_c32_literal_after_input_source(
                current_profile(),
                bits
            ),
            Err(Error::NoLoadableSeed),
            "input-then-constant cannot forge a missing source seed"
        );
        assert_eq!(
            layout::build_c32_literal_loader_rotate_source(
                current_profile(),
                bits
            ),
            Err(Error::NoLoadableSeed),
            "literal {bits:#x} must not be forged from untouched loader"
        );
        assert_eq!(
            layout::build_c32_literal_loader_arithmetic_source(
                current_profile(),
                bits
            ),
            Err(Error::NoLoadableSeed),
            "mixed guest writes must refuse signed EOF and narrow literals"
        );
    }
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    clippy::excessive_nesting,
    reason = "finite independent mixed-op position/loader arithmetic census"
)]
fn mixed_source_loaded_c32_emitter_matches_independent_four_template_oracle()
-> Result<(), String> {
    let profile = current_profile();
    let mut expected = BTreeMap::<u32, Vec<u8>>::new();
    let mut distinct_per_template = Vec::new();
    for operations in [b"**", b"p*", b"*p", b"pp"] {
        let mut local = BTreeSet::new();
        for noops in 0..PREFIX_BOUND {
            let mut source = (0..noops)
                .map(|position| encoded(position, b'o'))
                .collect::<Result<Vec<_>, _>>()?;
            for opcode in [b'j', operations[0], operations[1], b'v'] {
                source.push(encoded(source.len(), opcode)?);
            }
            let data_base = usize::from(source[noops]) + 1;
            if data_base <= source.len()
                || data_base.saturating_add(1)
                    >= usize::try_from(profile.memory_words())
                        .map_err(|error| error.to_string())?
            {
                continue;
            }
            for tail in 33..=126u8 {
                if !graphical_tail(tail, source.len()) {
                    continue;
                }
                source.push(tail);
                let seeds = original_seed_pair(&source, data_base);
                let low = if operations[0] == b'*' {
                    scalar_rotate(seeds[0])
                } else {
                    scalar_crazy(seeds[0], 0)
                };
                let high = if operations[1] == b'*' {
                    scalar_rotate(seeds[1])
                } else {
                    scalar_crazy(seeds[1], low)
                };
                let combined =
                    u64::from(low) + u64::from(high) * u64::from(MODULUS);
                if let Ok(bits) = u32::try_from(combined) {
                    _ = local.insert(bits);
                    _ = expected.entry(bits).or_insert_with(|| source.clone());
                }
                _ = source.pop();
            }
        }
        distinct_per_template.push(local.len());
    }
    assert_eq!(distinct_per_template, [164, 156, 298, 222]);
    assert_eq!(expected.len(), 750);
    for (bits, expected_source) in expected {
        let actual =
            layout::build_c32_literal_loader_arithmetic_source(profile, bits)
                .map_err(|error| format!("{bits:#x}: {error:?}"))?;
        assert_eq!(actual, expected_source, "canonical literal {bits:#x}");
    }
    Ok(())
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "three physical arithmetic paths with source-loaded data writes"
)]
fn vm_stores_three_mixed_c32_literals() -> Result<(), String> {
    let profile = current_profile();
    for (bits, operations) in [
        (351_548_260u32, b"p*"),
        (911_155_607u32, b"*p"),
        (509_386_234u32, b"pp"),
    ] {
        let source =
            layout::build_c32_literal_loader_arithmetic_source(profile, bits)
                .map_err(|error| format!("{bits:#x}: {error:?}"))?;
        let noops = source.len() - 5;
        assert_eq!(
            decode_profile_instruction(
                u32::from(source[noops + 1]),
                u32::try_from(noops + 1).map_err(|error| error.to_string())?
            ),
            Some(operations[0])
        );
        assert_eq!(
            decode_profile_instruction(
                u32::from(source[noops + 2]),
                u32::try_from(noops + 2).map_err(|error| error.to_string())?
            ),
            Some(operations[1])
        );
        let data_base = u32::from(source[noops]) + 1;
        let seeds = original_seed_pair(
            &source,
            usize::try_from(data_base).map_err(|error| error.to_string())?,
        );
        let low = if operations[0] == b'*' {
            scalar_rotate(seeds[0])
        } else {
            scalar_crazy(seeds[0], 0)
        };
        let high = if operations[1] == b'*' {
            scalar_rotate(seeds[1])
        } else {
            scalar_crazy(seeds[1], low)
        };
        assert_eq!(
            [low, high],
            layout::typed_cfg_adapter::state_storage::encode_i32_cells(bits)
        );
        let mut vm =
            ProfileMachine::from_source(profile, &source, vec![0, 255, 128])
                .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let result = vm
            .run_traced(noops + 4, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(result, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: noops + 4,
        });
        assert_eq!(trace[noops].decoded, Some(b'j'));
        for (index, value) in [low, high].into_iter().enumerate() {
            let step = &trace[noops + 1 + index];
            let destination = data_base
                + u32::try_from(index).map_err(|error| error.to_string())?;
            assert_eq!(step.decoded, Some(operations[index]));
            assert_eq!(step.before.registers.data_pointer, destination);
            assert_eq!(
                step.memory_reads.data.map(|read| read.value),
                Some(seeds[index])
            );
            assert_eq!(step.after.registers.accumulator, value);
            assert_eq!(vm.memory_word(destination), Ok(value));
            assert!(step.memory_delta.encryption.is_some());
        }
        assert_eq!(trace[noops + 3].decoded, Some(b'v'));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), &[]);
    }
    Ok(())
}

// A real `/` makes A unknown, so only a first `*` may erase it before
// source-loaded adjacent C32 writes. This oracle is independent of the
// production graphical encoder, recurrence and ternary arithmetic.
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    clippy::excessive_nesting,
    reason = "bounded independent N15 decoder/loader/trit oracle"
)]
fn input_then_c32_oracle() -> Result<BTreeMap<u32, Vec<u8>>, String> {
    let profile = current_profile();
    let mut expected = BTreeMap::<u32, Vec<u8>>::new();
    let mut per_template = Vec::new();
    for operations in [b"**", b"*p"] {
        let mut distinct = BTreeSet::new();
        for noops in 0..PREFIX_BOUND {
            let mut source = (0..noops)
                .map(|position| encoded(position, b'o'))
                .collect::<Result<Vec<_>, _>>()?;
            for opcode in [b'/', b'j', operations[0], operations[1], b'v'] {
                source.push(encoded(source.len(), opcode)?);
            }
            let data_base = usize::from(source[noops + 1]) + 1;
            if data_base <= source.len()
                || data_base.saturating_add(1)
                    >= usize::try_from(profile.memory_words())
                        .map_err(|error| error.to_string())?
            {
                continue;
            }
            for tail in 33..=126u8 {
                if !graphical_tail(tail, source.len()) {
                    continue;
                }
                source.push(tail);
                let seeds = original_seed_pair(&source, data_base);
                let low = scalar_rotate(seeds[0]);
                let high = if operations[1] == b'*' {
                    scalar_rotate(seeds[1])
                } else {
                    scalar_crazy(seeds[1], low)
                };
                let combined =
                    u64::from(low) + u64::from(high) * u64::from(MODULUS);
                if let Ok(bits) = u32::try_from(combined) {
                    _ = distinct.insert(bits);
                    _ = expected.entry(bits).or_insert_with(|| source.clone());
                }
                _ = source.pop();
            }
        }
        per_template.push(distinct.len());
    }
    assert_eq!(per_template, [163, 297]);
    assert_eq!(expected.len(), 409);
    for unsupported in [0, 255, u32::MAX] {
        assert!(!expected.contains_key(&unsupported));
    }
    Ok(expected)
}

#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    reason = "physical VM input, code and adjacent data write effects"
)]
fn verify_live_input_c32_source(
    bits: u32,
    source: &[u8],
) -> Result<(), String> {
    let profile = current_profile();
    let noops = source.len() - 6;
    let data_base = u32::from(source[noops + 1]) + 1;
    let seeds = original_seed_pair(
        source,
        usize::try_from(data_base).map_err(|error| error.to_string())?,
    );
    let target =
        layout::typed_cfg_adapter::state_storage::encode_i32_cells(bits);
    // Load authentic graphical memory once; each case receives its own
    // independent validated copy rather than retaining guest mutations.
    let prepared = ProfileMachine::from_source(profile, source, vec![])
        .map_err(|error| error.to_string())?;
    for input in [vec![], vec![0], vec![128], vec![255], vec![1, 2]] {
        let mut vm = ProfileMachine::from_state(
            profile,
            prepared.memory().to_vec(),
            input.clone(),
            malbolge::ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = vm
            .run_traced(noops + 5, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: noops + 5,
        });
        assert_eq!(trace[noops].decoded, Some(b'/'));
        assert_eq!(
            trace[noops].input,
            Some(
                input
                    .first()
                    .map_or(malbolge::TraceInput::EndOfInput, |&byte| {
                        malbolge::TraceInput::Byte(byte)
                    })
            )
        );
        assert_eq!(trace[noops + 1].decoded, Some(b'j'));
        assert_eq!(trace[noops + 1].after.registers.data_pointer, data_base);
        for index in 0..2 {
            let step = &trace[noops + 2 + index];
            let address = data_base
                + u32::try_from(index).map_err(|error| error.to_string())?;
            assert_eq!(step.before.registers.data_pointer, address);
            assert_eq!(
                step.memory_reads.data.map(|read| read.value),
                Some(seeds[index])
            );
            assert_eq!(step.after.registers.accumulator, target[index]);
            assert_eq!(vm.memory_word(address), Ok(target[index]));
            assert!(step.memory_delta.encryption.is_some());
        }
        assert_eq!(trace[noops + 4].decoded, Some(b'v'));
        assert_eq!(vm.input_consumed(), usize::from(!input.is_empty()));
        assert_eq!(vm.output(), &[]);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "source matching and real guest path verification"
)]
fn source_loaded_c32_writes_after_real_input_match_bounded_oracle()
-> Result<(), String> {
    let profile = current_profile();
    let expected = input_then_c32_oracle()?;
    // Exhaust the grammar independently, then check the emitter's search
    // against a deterministic spread (every seventeenth, including last).
    for (bits, original) in expected.iter().step_by(17) {
        let source =
            layout::build_c32_literal_after_input_source(profile, *bits)
                .map_err(|error| format!("{bits:#x}: {error:?}"))?;
        assert_eq!(&source, original, "canonical source for {bits:#x}");
    }
    // Both instruction templates must execute real `/` for binary and EOF.
    for operation in *b"*p" {
        let (&bits, source) = expected
            .iter()
            .find(|(_, source)| {
                let noops = source.len() - 6;
                decode_profile_instruction(
                    u32::from(source[noops + 3]),
                    u32::try_from(noops + 3).unwrap_or(u32::MAX),
                ) == Some(operation)
            })
            .ok_or_else(|| format!("missing second operation {operation}"))?;
        verify_live_input_c32_source(bits, source)?;
    }
    Ok(())
}

#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    reason = "independent scalar result and every reached N15 guest effect"
)]
fn verify_raw_first_write(
    source: &[u8],
    loaded: &ProfileMachine,
    first: u8,
    input: &[u8],
) -> Result<u32, String> {
    let profile = current_profile();
    let data_base = u32::from(source[1]) + 1;
    let seeds = original_seed_pair(
        source,
        usize::try_from(data_base).map_err(|error| error.to_string())?,
    );
    let raw = input
        .first()
        .map_or_else(|| profile.eof_word(), |&byte| u32::from(byte));
    let expected_low = if first == b'p' {
        scalar_crazy(seeds[0], raw)
    } else {
        scalar_rotate(seeds[0])
    };
    let expected_high = scalar_crazy(seeds[1], expected_low);
    let mut vm = ProfileMachine::from_state(
        profile,
        loaded.memory().to_vec(),
        input.to_vec(),
        malbolge::ProfileRegisters::default(),
    )
    .map_err(|error| error.to_string())?;
    let mut trace = Vec::new();
    let outcome = vm
        .run_traced(5, &mut |step| trace.push(*step))
        .map_err(|error| error.to_string())?;
    assert_eq!(outcome, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: 5,
    });
    assert_eq!(trace[0].decoded, Some(b'/'));
    assert_eq!(trace[0].after.registers.accumulator, raw);
    assert_eq!(trace[1].decoded, Some(b'j'));
    assert_eq!(trace[1].after.registers.data_pointer, data_base);
    for (index, (&opcode, &word)) in [first, b'p']
        .iter()
        .zip([expected_low, expected_high].iter())
        .enumerate()
    {
        let step = &trace[2 + index];
        let address = data_base
            + u32::try_from(index).map_err(|error| error.to_string())?;
        assert_eq!(step.decoded, Some(opcode));
        assert_eq!(step.before.registers.data_pointer, address);
        assert_eq!(
            step.memory_reads.data.map(|read| read.value),
            Some(seeds[index])
        );
        assert_eq!(step.after.registers.accumulator, word);
        assert_eq!(vm.memory_word(address), Ok(word));
        assert!(step.memory_delta.encryption.is_some());
    }
    assert_eq!(trace[4].decoded, Some(b'v'));
    assert_eq!(vm.output(), &[]);
    Ok(expected_low)
}

// This is an obstruction to a *specific* physical layout, not to C23 input
// conversion generally: a first adjacent low-word write from raw guest `/`
// cannot distinguish byte 2 from EOF at the units trit using fixed `p` or `*`.
#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "two physical input cases and independent one-trit obstruction"
)]
fn raw_input_first_c32_word_needs_nonlocal_trit_routing() -> Result<(), String>
{
    let profile = current_profile();
    let c32_byte =
        layout::typed_cfg_adapter::state_storage::encode_i32_cells(2);
    let c32_eof =
        layout::typed_cfg_adapter::state_storage::encode_i32_cells(u32::MAX);
    assert_eq!(c32_byte, [2, 0]);
    assert_eq!(c32_eof, [4_644_102, 299]);
    assert_eq!(2 % 3, profile.eof_word() % 3);
    assert_ne!(c32_byte[0] % 3, c32_eof[0] % 3);

    // Both zero-prefix sources physically reach `/; j; first; p; v`.
    // The fixed source tail supplies both data cells and is never executed.
    for first in *b"p*" {
        let mut source = Vec::new();
        for opcode in [b'/', b'j', first, b'p', b'v'] {
            source.push(encoded(source.len(), opcode)?);
        }
        let tail = (33..=126u8)
            .find(|&byte| graphical_tail(byte, source.len()))
            .ok_or("missing graphical loader tail")?;
        source.push(tail);
        let data_base = u32::from(source[1]) + 1;
        assert!(
            usize::try_from(data_base).map_err(|error| error.to_string())?
                > source.len()
        );
        let loaded = ProfileMachine::from_source(profile, &source, vec![])
            .map_err(|error| error.to_string())?;
        let first_words = [
            verify_raw_first_write(&source, &loaded, first, &[2])?,
            verify_raw_first_write(&source, &loaded, first, &[])?,
        ];
        // With fixed operand trits, the first `p` preserves equality of
        // the two raw input units trits; `*` cannot depend on input at all.
        // Neither first adjacent store can encode both distinct C32 lows.
        assert_eq!(first_words[0] % 3, first_words[1] % 3);
        assert!(
            first_words[0] != c32_byte[0] || first_words[1] != c32_eof[0],
            "fixed loader source cannot normalize byte 2 and signed EOF"
        );
    }
    Ok(())
}
