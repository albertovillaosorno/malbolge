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
//   - The frozen 91-cell C23 decoder's first-read storage geometry.
// - Must-Not:
//   - Claim generic linker impossibility or completed source-C lowering.
// - Allows:
//   - Inputs: all graphical 91-cell loader tails and physical input paths.
//   - Outputs: exact finite obstruction and normative VM rejection evidence.
//   - Side effects: isolated guest VM execution only.
// - Split-When:
//   - Generic code relocation replaces the frozen pointer-chain boundary.
// - Merge-When:
//   - A source-C first-input decoder subsumes this physical experiment.
// - Summary:
//   - Rules out a lossless fixed-layout C38 save without host shortcuts.

//! Exact obstruction to a lossless early save in the frozen C23 converter.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::{BTreeMap, BTreeSet};
use std::iter::once;

use malbolge::{
    ProfileMachine, RunOutcome, Termination, TraceInput, current_profile,
    decode_profile_instruction, encrypt_profile_cell,
};

const WORDS: u32 = 14_348_907;
const EOF: u32 = WORDS - 1;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct EarlyPointerState {
    accumulator: u32,
    data_pointer: u32,
}

// Independent scalar trit arithmetic; no production crazy/rotate helper is
// consulted while classifying the exact graphical loader-tail candidate set.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "finite independent 15-trit guest arithmetic oracle"
)]
fn crazy(mut data: u32, mut accumulator: u32) -> u32 {
    let mut result = 0;
    let mut place = 1;
    for _ in 0..15u8 {
        let value = match (data % 3, accumulator % 3) {
            (0 | 1, 0) | (2, 2) => 1,
            (1, 2) | (2, 0 | 1) => 2,
            _ => 0,
        };
        result += value * place;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    result
}

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    clippy::integer_division,
    reason = "independent trit rotation arithmetic"
)]
const fn rotate(word: u32) -> u32 {
    (word / 3) + (word % 3) * (WORDS / 3)
}

fn signed_classes() -> impl Iterator<Item = u32> {
    (0..=255).chain(once(EOF))
}

#[expect(
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects,
    reason = "fixed 34-word loader oracle with loop bounds inside the array"
)]
fn loader_words(tail: [u8; 2]) -> [u32; 34] {
    let mut words = [0u32; 34];
    words[0] = u32::from(tail[0]);
    words[1] = u32::from(tail[1]);
    for i in 2..words.len() {
        words[i] = crazy(words[i - 2], words[i - 1]);
    }
    words
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::panic_in_result_fn,
    reason = "bounded exhaustive oracle assertions and allocation errors"
)]
fn fixed_converter_has_no_lossless_m97_tail() -> Result<(), String> {
    let profile = current_profile();
    assert_eq!(profile.word_modulus(), WORDS);
    // Indices are loader offsets from M89, so 6=M95, 7=M96,
    // 8=M97, 9=M98, 13=M102, and 33=M122.
    let mut candidate_count = 0usize;
    let mut pointer_compatible = 0usize;
    let mut c23_compatible = Vec::new();
    for first in 33..=126u8 {
        for last in 33..=126u8 {
            candidate_count += 1;
            let tail = [first, last];
            let words = loader_words(tail);
            if words[7] != 121 || words[9] != 157 || words[33] != 157 {
                continue;
            }
            pointer_compatible += 1;
            let rotated = (0u8..9).fold(words[6], |word, _| rotate(word));
            let correct_c23 = signed_classes().all(|raw| {
                let actual = crazy(words[7], crazy(rotated, raw)) & 255;
                let expected = raw.min(255);
                actual == expected
            });
            if !correct_c23 {
                continue;
            }
            c23_compatible.push(tail);
            let first_store = signed_classes()
                .map(|raw| crazy(words[8], raw))
                .collect::<BTreeSet<_>>();
            let alternate_store = signed_classes()
                .map(|raw| crazy(words[13], raw))
                .collect::<BTreeSet<_>>();
            assert_eq!(first_store.len(), 37, "tail {tail:?}");
            assert_eq!(alternate_store.len(), 257, "tail {tail:?}");
            assert_eq!(words[8], 7_174_404, "tail {tail:?}");
            assert_eq!(words[13], 121, "tail {tail:?}");
        }
    }
    assert_eq!(candidate_count, 94 * 94);
    assert_eq!(pointer_compatible, 4);
    assert_eq!(c23_compatible, vec![*b"Hy", *b"Iy", *b"Ky", *b"Ly"]);
    // The actual original `Iy` source is graphically loadable. This finite
    // arithmetic classification is only a necessary tail/pointer bound;
    // it does not turn the other tail pairs into accepted guest programs.
    let source = layout::build_c23_nine_rotated_signed_output_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(source.get(89..91), Some(b"Iy".as_slice()));
    assert_eq!(layout::admit_c23_probe_graphical_source(&source), Ok(()));
    Ok(())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "normative step-indexed VM trace checks for fixed 91-cell layout"
)]
fn moving_c38_save_to_lossless_m102_breaks_executed_bootstrap()
-> Result<(), String> {
    let profile = current_profile();
    let source = layout::build_c23_nine_rotated_signed_output_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(source.get(41), Some(&93));
    assert_eq!(decode_profile_instruction(93, 41), Some(b'j'));
    let mut changed = source.clone();
    for (pos, cell) in changed.iter_mut().enumerate().take(43).skip(38) {
        *cell = (33..=126u8)
            .find(|byte| {
                decode_profile_instruction(
                    u32::from(*byte),
                    u32::try_from(pos).unwrap_or(u32::MAX),
                ) == Some(b'o')
            })
            .ok_or_else(|| format!("missing graphical no-op at C{pos}"))?;
    }
    changed[43] = (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), 43) == Some(b'p')
        })
        .ok_or("missing graphical p at C43")?;
    layout::admit_c23_probe_graphical_source(&changed)
        .map_err(|error| format!("{error:?}"))?;
    // C0 j enters M41 before the source's C37 input. C1 j must read
    // M41=93 and enter M94; patching C41 to an inert no-op also changes
    // that *data* word to 121, redirecting bootstrap to M122 instead.
    let mut original =
        ProfileMachine::from_source(profile, &source, vec![1, 2])
            .map_err(|error| error.to_string())?;
    let mut candidate =
        ProfileMachine::from_source(profile, &changed, vec![1, 2])
            .map_err(|error| error.to_string())?;
    assert_eq!(original.memory_word(41), Ok(93));
    assert_eq!(candidate.memory_word(41), Ok(121));
    let mut original_trace = Vec::new();
    let mut candidate_trace = Vec::new();
    _ = original
        .run_traced(2, &mut |step| original_trace.push(*step))
        .map_err(|error| error.to_string())?;
    let outcome = candidate
        .run_traced(100, &mut |step| candidate_trace.push(*step))
        .map_err(|error| error.to_string())?;
    assert_eq!(
        original_trace[1].memory_reads.data.map(|read| read.value),
        Some(93)
    );
    assert_eq!(
        candidate_trace[1].memory_reads.data.map(|read| read.value),
        Some(121)
    );
    assert_eq!(original_trace[1].after.registers.data_pointer, 94);
    assert_eq!(candidate_trace[1].after.registers.data_pointer, 122);
    assert_eq!(outcome, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: 81,
    });
    assert_eq!(candidate_trace[37].input, Some(TraceInput::Byte(1)));
    assert_eq!(candidate_trace[43].before.registers.data_pointer, 7_174_412);
    assert_ne!(candidate_trace[43].before.registers.data_pointer, 102);
    assert_eq!(candidate.input_consumed(), 2);
    assert_eq!(candidate.output(), &[73]);
    assert_ne!(candidate.output(), &[2]);
    // This rejects the naive C38-C43 relocation only. A different complete
    // bootstrap and source-C CFG linker remain unresolved research work.
    Ok(())
}

// A fixed C41=93 pointer is necessary for bootstrap. All four other
// C38..C42 code sites can encode one of two no-writing operations, o/j.
// Replay those five instructions, including their code encryption, from
// one verified physical post-C37 memory state rather than rebuilding 16 VMs.
fn early_pointer_from_vm(memory: &[u32], mask: u8) -> Result<u32, String> {
    const SITES: [u32; 4] = [38, 39, 40, 42];
    let mut overlay = BTreeMap::new();
    for (bit, site) in SITES.into_iter().enumerate() {
        let opcode = if mask & (1 << bit) == 0 {
            b'o'
        } else {
            b'j'
        };
        let raw = (33..=126u8)
            .find(|byte| {
                decode_profile_instruction(u32::from(*byte), site)
                    == Some(opcode)
            })
            .ok_or_else(|| format!("no source opcode at C{site}"))?;
        _ = overlay.insert(site, u32::from(raw));
    }
    let mut pointer = 97u32;
    for code in 38u32..=42 {
        let read_word = |address: u32| -> Option<u32> {
            overlay.get(&address).copied().or_else(|| {
                usize::try_from(address)
                    .ok()
                    .and_then(|index| memory.get(index).copied())
            })
        };
        let opcode = if code == 41 {
            b'j'
        } else {
            let bit = SITES
                .iter()
                .position(|site| *site == code)
                .ok_or("missing site")?;
            if mask & (1 << bit) == 0 {
                b'o'
            } else {
                b'j'
            }
        };
        pointer = if opcode == b'j' {
            read_word(pointer)
                .and_then(|value| value.checked_add(1))
                .ok_or("invalid pointer read")?
        } else {
            pointer.checked_add(1).ok_or("invalid pointer advance")?
        };
        let old_code = read_word(code).ok_or("missing source cell")?;
        let encrypted =
            encrypt_profile_cell(old_code).ok_or("invalid encryption")?;
        _ = overlay.insert(code, encrypted);
    }
    Ok(pointer)
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "finite physical-state oracle asserts the exact reachable set"
)]
fn early_o_j_routes_cannot_reach_m102_with_c41_fixed() -> Result<(), String> {
    let profile = current_profile();
    let source = layout::build_c23_nine_rotated_signed_output_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    let mut vm = ProfileMachine::from_source(profile, &source, vec![1, 2])
        .map_err(|error| error.to_string())?;
    let mut trace = Vec::new();
    assert_eq!(
        vm.run_traced(38, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?,
        RunOutcome::BudgetExhausted { steps: 38 },
    );
    let post_read = trace.get(37).ok_or("missing first read")?;
    assert_eq!(post_read.after.registers.data_pointer, 97);
    assert_eq!(post_read.input, Some(TraceInput::Byte(1)));
    for step in &trace {
        assert!(
            step.memory_reads.data.is_none_or(|read| {
                ![38, 39, 40, 42].contains(&read.address)
            })
        );
    }
    let mut reachable = BTreeSet::new();
    for mask in 0u8..16 {
        _ = reachable.insert(early_pointer_from_vm(vm.memory(), mask)?);
    }
    assert_eq!(
        reachable,
        BTreeSet::from([37, 38, 67, 68, 159, 7_174_370, 7_174_405, 7_174_406]),
    );
    assert!(!reachable.contains(&102));
    Ok(())
}

// A fixed 4^4 grammar expands the prior o/j-only relocation experiment:
// C38,39,40,42 may decode as o, j, *, or p while bootstrap-critical C41
// remains untouched. The five-step independent interpreter preserves actual
// code encryption, ternary writes and data-dependent pointer jumps. This
// asks only whether a C43 p could save the first input at lossless M102.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "small fixed N15 interpreter with checked bounded source sites"
)]
fn early_arithmetic_pointer(
    memory: &[u32],
    choices: [u8; 4],
    raw: u32,
) -> Result<EarlyPointerState, String> {
    let mut overlay = BTreeMap::new();
    for (site, opcode) in [38u32, 39, 40, 42].into_iter().zip(choices) {
        let encoded = (33..=126u8)
            .find(|byte| {
                decode_profile_instruction(u32::from(*byte), site)
                    == Some(opcode)
            })
            .ok_or("no graphical opcode")?;
        _ = overlay.insert(site, u32::from(encoded));
    }
    let mut pointer = 97u32;
    let mut accumulator = raw;
    for site in 38u32..=42 {
        let read = |address: u32, writes: &BTreeMap<u32, u32>| {
            writes.get(&address).copied().or_else(|| {
                usize::try_from(address)
                    .ok()
                    .and_then(|index| memory.get(index).copied())
            })
        };
        let code = read(site, &overlay).ok_or("missing code")?;
        let opcode = decode_profile_instruction(code, site)
            .ok_or("non-graphical instruction")?;
        let data = read(pointer, &overlay).ok_or("missing data")?;
        match opcode {
            b'o' => pointer = (pointer + 1) % WORDS,
            b'j' => pointer = (data + 1) % WORDS,
            b'*' => {
                accumulator = rotate(data);
                _ = overlay.insert(pointer, accumulator);
                pointer = (pointer + 1) % WORDS;
            },
            b'p' => {
                accumulator = crazy(data, accumulator);
                _ = overlay.insert(pointer, accumulator);
                pointer = (pointer + 1) % WORDS;
            },
            _ => return Err("unexpected mutated code opcode".into()),
        }
        let prior = read(site, &overlay).ok_or("missing executed code")?;
        let encrypted = encrypt_profile_cell(prior)
            .ok_or("non-graphical code encryption")?;
        _ = overlay.insert(site, encrypted);
    }
    Ok(EarlyPointerState {
        accumulator,
        data_pointer: pointer,
    })
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "all 256 frozen pointer instructions check the first C23 NUL"
)]
fn early_arithmetic_routes_cannot_reach_m102_on_nul() -> Result<(), String> {
    let profile = current_profile();
    let source = layout::build_c23_nine_rotated_signed_output_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    let mut vm = ProfileMachine::from_source(profile, &source, vec![0])
        .map_err(|error| error.to_string())?;
    let mut trace = Vec::new();
    assert_eq!(
        vm.run_traced(38, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?,
        RunOutcome::BudgetExhausted { steps: 38 }
    );
    assert_eq!(
        trace.get(37).ok_or("missing C37 read")?.input,
        Some(TraceInput::Byte(0))
    );
    assert_eq!(
        trace
            .get(37)
            .ok_or("missing C37 state")?
            .after
            .registers
            .data_pointer,
        97
    );
    // The bootstrap has no earlier data dependency on edited source cells.
    // In particular the C41=M41 pointer seed remains exactly unchanged.
    for step in &trace {
        assert!(
            step.memory_reads.data.is_none_or(|read| {
                ![38, 39, 40, 42].contains(&read.address)
            })
        );
    }
    let mut targets = BTreeSet::new();
    let mut examined = 0usize;
    for mask in 0..=255u8 {
        let choices = [0u32, 2, 4, 6].map(|shift| match (mask >> shift) & 3 {
            0 => b'o',
            1 => b'j',
            2 => b'*',
            _ => b'p',
        });
        examined += 1;
        let result = early_arithmetic_pointer(vm.memory(), choices, 0)?;
        _ = targets.insert(result.data_pointer);
    }
    assert_eq!(examined, 256);
    assert_eq!(
        targets,
        BTreeSet::from([37, 38, 67, 68, 159, 7_174_370, 7_174_405, 7_174_406,])
    );
    assert!(!targets.contains(&102));
    Ok(())
}

// Recheck the independent five-step interpreter against actual source-loaded
// guest transitions, including opcodes that modify guest memory and A.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "representative executed mixed rotation/crazy pointer controls"
)]
fn early_arithmetic_pointer_matches_real_guest_control() -> Result<(), String> {
    let profile = current_profile();
    let original = layout::build_c23_nine_rotated_signed_output_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    let mut baseline = ProfileMachine::from_source(profile, &original, vec![0])
        .map_err(|error| error.to_string())?;
    assert_eq!(
        baseline.run(38).map_err(|error| error.to_string())?,
        RunOutcome::BudgetExhausted { steps: 38 }
    );
    for choices in [*b"oj*p", *b"p*jo", *b"jpo*", *b"*p*p"] {
        let mut candidate = original.clone();
        for (site, opcode) in [38u32, 39, 40, 42].into_iter().zip(choices) {
            let encoded = (33..=126u8)
                .find(|byte| {
                    decode_profile_instruction(u32::from(*byte), site)
                        == Some(opcode)
                })
                .ok_or("no graphical candidate")?;
            *candidate
                .get_mut(usize::try_from(site).unwrap_or(usize::MAX))
                .ok_or("missing code byte")? = encoded;
        }
        assert_eq!(candidate.get(41), original.get(41));
        layout::admit_c23_probe_graphical_source(&candidate)
            .map_err(|error| format!("{error:?}"))?;
        let mut vm = ProfileMachine::from_source(profile, &candidate, vec![0])
            .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        assert_eq!(
            vm.run_traced(43, &mut |step| trace.push(*step))
                .map_err(|error| error.to_string())?,
            RunOutcome::BudgetExhausted { steps: 43 }
        );
        assert_eq!(
            trace.get(37).ok_or("missing C37")?.input,
            Some(TraceInput::Byte(0))
        );
        let actual = trace
            .get(42)
            .ok_or("missing C42 transition")?
            .after
            .registers;
        let expected = early_arithmetic_pointer(baseline.memory(), choices, 0)?;
        assert_eq!(
            actual.data_pointer, expected.data_pointer,
            "choices {choices:?}"
        );
        assert_eq!(
            actual.accumulator, expected.accumulator,
            "choices {choices:?}"
        );
    }
    Ok(())
}
