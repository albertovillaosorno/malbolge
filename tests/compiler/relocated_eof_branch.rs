// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Boundary-Contract:
// - Owns:
//   - Exhaustive physical byte/EOF dispatch and output-store regression.
// - Must-Not:
//   - Certify source-C arithmetic, complete frame ownership, or publication.
// - Allows:
//   - Inputs: the graphical relocated source and all first-input classes.
//   - Outputs: independently reconciled guest effects and exact I/O order.
//   - Side effects: isolated normative VM executions.
// - Split-When:
//   - A genuine loop needs an additional source-bound verifier.
// - Merge-When:
//   - General source-C branch lowering subsumes this bounded physical prefix.
// - Summary:
//   - Exercises both reached code arms, raw stores, and omitted-effect
//     controls.

//! All 257 raw input classes follow one of two genuine guest code arms.

use std::ops::RangeInclusive;

use malbolge::{
    RunOutcome, Termination, TraceInput, current_profile,
    decode_profile_instruction, historical_profile,
};

use super::layout::{
    AddressSelectedIndirectCase, AddressSelectedIndirectError,
    AddressSelectedIndirectProbe, RelocatedEofBranchSource,
    SourcePhysicalImageTrace, SourcePhysicalIoEvent, SourcePhysicalWordEffect,
    SourceWrittenIndirectGuestError, SourceWrittenIndirectGuestProbe,
    build_relocated_eof_branch_source, verify_address_selected_indirect_guest,
    verify_source_physical_image_trace, verify_source_written_indirect_guest,
};

const CHECKSUM_LOW: u32 = 7_174_417;
const CHECKSUM_HIGH: u32 = 7_174_418;
const RAW_LOW: u32 = 7_174_419;
const RAW_HIGH: u32 = 7_174_420;
const ENCODED: u32 = 7_174_421;
const MASK: u32 = 7_174_423;
const OUTPUT: u32 = 7_174_455;
const ONES: u32 = 7_174_453;
const BYTE_CLASS: u32 = 6_554_439;
const EOF_CLASS: u32 = 13_108_878;

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    clippy::indexing_slicing,
    reason = "independent scalar 15-trit truth-table oracle"
)]
fn crazy(mut data: u32, mut accumulator: u32) -> u32 {
    let truth = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut result = 0;
    let mut place = 1;
    for _ in 0usize..15 {
        result += truth[usize::try_from(data % 3).unwrap_or(3)]
            [usize::try_from(accumulator % 3).unwrap_or(3)]
            * place;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    result
}

fn plan() -> Result<RelocatedEofBranchSource, String> {
    build_relocated_eof_branch_source(current_profile())
        .map_err(|error| format!("relocated source: {error:?}"))
}

fn image(
    source: &[u8],
    input: &[u8],
) -> Result<SourcePhysicalImageTrace, String> {
    verify_source_physical_image_trace(current_profile(), source, input, 136)
        .map_err(|error| format!("input {input:?}: {error:?}"))
}

fn final_word(journal: &SourcePhysicalImageTrace, address: u32) -> Option<u32> {
    journal
        .expanded
        .iter()
        .find(|cell| cell.site == address)
        .map(|cell| cell.final_word)
}

fn write(
    journal: &SourcePhysicalImageTrace,
    code: u32,
    address: u32,
    value: u32,
) -> bool {
    journal.data_writes.iter().any(|effect| {
        (effect.code_address, effect.data_address, effect.after)
            == (code, address, value)
    })
}

fn input_event(
    code: u32,
    step: usize,
    byte: Option<u8>,
) -> SourcePhysicalIoEvent {
    SourcePhysicalIoEvent::Input {
        code_address: code,
        raw_word: byte.map_or(current_profile().eof_word(), u32::from),
        read: byte.map_or(TraceInput::EndOfInput, TraceInput::Byte),
        trace_index: step,
    }
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "assert exact static source geometry and canonical profile"
)]
#[test]
fn relocated_source_is_graphical_and_profile_bound() -> Result<(), String> {
    let guest = plan()?;
    assert_eq!(guest.source.len(), 156, "exact loader geometry");
    assert_eq!(
        guest.source.get(154..),
        Some(&[39, 37][..]),
        "exact loader seeds"
    );
    assert_eq!(
        guest.zero_pair,
        [CHECKSUM_LOW, CHECKSUM_HIGH],
        "checksum words"
    );
    assert_eq!(guest.input_pair, [RAW_LOW, RAW_HIGH], "raw input words");
    assert_eq!(
        [guest.class_data_address, guest.output_data_address],
        [MASK, OUTPUT],
        "class and source output data words"
    );
    assert_eq!(
        [
            guest.class_store_code_address,
            guest.first_input_code_address,
            guest.branch_code_address,
            guest.byte_input_code_address,
            guest.byte_halt_code_address,
            guest.eof_arm_code_address,
            guest.eof_output_store_code_address,
            guest.eof_output_code_address,
            guest.eof_halt_code_address
        ],
        [99, 53, 118, 120, 121, 126, 140, 141, 142],
        "exact shared/byte/EOF physical code sites"
    );
    assert!(
        guest.source.iter().enumerate().all(|(position, &cell)| {
            decode_profile_instruction(
                u32::from(cell),
                u32::try_from(position).unwrap_or(u32::MAX),
            )
            .is_some_and(|op| b"ji*p</vo".contains(&op))
        }),
        "all source cells must decode to loader-admitted instructions"
    );
    assert_eq!(
        build_relocated_eof_branch_source(historical_profile()),
        Err(super::layout::ZeroCellSourceError::UnsupportedProfile),
        "do not reuse the N15 layout for N10"
    );
    Ok(())
}

#[test]
fn independent_class_oracle_distinguishes_all_bytes_from_eof() {
    for raw in (0..=255).chain([current_profile().eof_word()]) {
        let encoded = crazy(ONES, raw);
        assert_eq!(crazy(ONES, encoded), raw, "lossless input {raw}");
        let folded = crazy(encoded, BYTE_CLASS);
        let class = if raw == current_profile().eof_word() {
            assert_eq!(folded, raw, "true EOF remains distinct");
            EOF_CLASS
        } else {
            assert!(
                (620_014..=620_135).contains(&folded),
                "intermediate for {raw}"
            );
            BYTE_CLASS
        };
        assert_eq!(
            crazy(BYTE_CLASS, folded),
            class,
            "exact final class for {raw}"
        );
    }
}

fn assert_prefix_writes(
    journal: &SourcePhysicalImageTrace,
    raw: u32,
    class: u32,
) {
    let encoded = crazy(ONES, raw);
    let folded = crazy(encoded, BYTE_CLASS);
    // Includes the physically reached idempotent high-word store.
    for (code, address, value) in [
        (44, CHECKSUM_HIGH, 0),
        (47, CHECKSUM_LOW, 0),
        (59, ENCODED, encoded),
        (63, RAW_LOW, raw),
        (64, RAW_HIGH, 0),
        (67, MASK, 4_782_981),
        (75, MASK, 1_594_327),
        (83, MASK, 5_314_411),
        (91, MASK, BYTE_CLASS),
        (97, ENCODED, folded),
        (99, MASK, class),
    ] {
        assert!(
            write(journal, code, address, value),
            "raw {raw}: physical C{code} must store {value} at M{address}"
        );
    }
    for (address, value) in [
        (CHECKSUM_LOW, 0),
        (CHECKSUM_HIGH, 0),
        (RAW_LOW, raw),
        (RAW_HIGH, 0),
        (MASK, class),
    ] {
        assert_eq!(
            final_word(journal, address),
            Some(value),
            "raw {raw}: final live M{address}"
        );
    }
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "assert exact physical branch operand and last-writer lineage"
)]
fn assert_common_prefix(
    journal: &SourcePhysicalImageTrace,
    first: Option<u8>,
) -> Result<(), String> {
    let raw = first.map_or(current_profile().eof_word(), u32::from);
    let (class, dereference, operand) = if first.is_some() {
        (BYTE_CLASS, 6_554_440, 7_174_416)
    } else {
        (EOF_CLASS, 13_108_879, 37)
    };
    assert_prefix_writes(journal, raw, class);

    let class_read = journal
        .data_reads
        .iter()
        .find(|effect| effect.code_address == 107)
        .ok_or("missing class read")?;
    assert_eq!(
        (class_read.data_address, class_read.value),
        (MASK, class),
        "C107 class word for {raw}"
    );
    assert_eq!(
        class_read.last_word_effect,
        Some(SourcePhysicalWordEffect::DataWrite { trace_index: 99 }),
        "C107 must read the actual C99 store"
    );
    let next_read = journal
        .data_reads
        .iter()
        .find(|effect| effect.code_address == 108)
        .ok_or("missing class-dependent loader read")?;
    assert_eq!(
        (next_read.data_address, next_read.value),
        (dereference, operand),
        "C108 class-selected loader word for {raw}"
    );
    assert_eq!(
        next_read.last_word_effect, None,
        "untouched C108 loader word"
    );

    // Neither branch selection nor reentry can depend on the raw byte cell.
    assert!(
        !journal.data_reads.iter().any(|effect| {
            (100..=118).contains(&effect.code_address)
                && effect.data_address == RAW_LOW
        }),
        "no raw-byte-dependent pointer route after classification"
    );
    assert_selected_branch(journal, first)
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "assert real C118 operand and target-encryption chronology"
)]
fn assert_selected_branch(
    journal: &SourcePhysicalImageTrace,
    first: Option<u8>,
) -> Result<(), String> {
    let raw = first.map_or(current_profile().eof_word(), u32::from);
    let branch = journal
        .data_reads
        .iter()
        .find(|effect| effect.code_address == 118)
        .ok_or("missing real indirect branch")?;
    let (address, target_word, landing) = if first.is_some() {
        (117, 119, 120)
    } else {
        (48, 125, 126)
    };
    assert_eq!(
        (branch.opcode, branch.data_address, branch.value),
        (b'i', address, target_word),
        "actual indirect operand for {raw}"
    );
    assert_eq!(
        branch.last_word_effect,
        Some(SourcePhysicalWordEffect::Encryption {
            trace_index: usize::try_from(address)
                .map_err(|error| error.to_string())?,
        }),
        "target pointer must be the prior encrypted code word"
    );
    assert_eq!(
        journal
            .code_fetches
            .get(119)
            .map(|fetch| fetch.code_address),
        Some(landing),
        "exact reached physical branch arm for {raw}"
    );
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "assert exact bounded byte arm and ordered input effects"
)]
fn assert_byte_arm(
    journal: &SourcePhysicalImageTrace,
    first: u8,
    next: Option<u8>,
) -> Result<(), String> {
    assert_common_prefix(journal, Some(first))?;
    assert_eq!(
        journal.source.outcome,
        RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 121,
        },
        "real byte-arm halt for {first}"
    );
    assert_eq!(
        journal.io_events,
        [
            input_event(53, 53, Some(first)),
            input_event(120, 119, next),
        ],
        "exact first and second input events for {first}"
    );
    assert_eq!(
        journal.code_fetches.last().map(|fetch| fetch.code_address),
        Some(121),
        "actual byte-arm halt address"
    );
    assert_eq!(
        final_word(journal, OUTPUT),
        None,
        "byte arm leaves output cell untouched"
    );
    assert!(
        !journal
            .data_writes
            .iter()
            .any(|effect| effect.data_address == OUTPUT),
        "no byte-arm output store"
    );
    Ok(())
}

// Partition the exhaustive matrix into contiguous ranges so test runners can
// parallelize or isolate one failing first-byte region without changing the
// corpus. Every case uses an independently loaded, reconciled VM image.
fn byte_matrix(range: RangeInclusive<u8>) -> Result<(), String> {
    let guest = plan()?;
    for first in range {
        let input = [first, 0xa5, 0x5a];
        let proof = verify_address_selected_indirect_guest(
            current_profile(),
            address_probe(&guest.source, &input),
        )
        .map_err(|error| {
            format!("byte {first}: paired address proof {error:?}")
        })?;
        let [byte, eof] = proof.cases();
        assert_byte_arm(byte.journal(), first, Some(0xa5))?;
        assert_common_prefix(eof.journal(), None)?;
    }
    Ok(())
}

#[test]
fn relocated_byte_arm_00_1f() -> Result<(), String> {
    byte_matrix(0x00..=0x1f)
}

#[test]
fn relocated_byte_arm_20_3f() -> Result<(), String> {
    byte_matrix(0x20..=0x3f)
}

#[test]
fn relocated_byte_arm_40_5f() -> Result<(), String> {
    byte_matrix(0x40..=0x5f)
}

#[test]
fn relocated_byte_arm_60_7f() -> Result<(), String> {
    byte_matrix(0x60..=0x7f)
}

#[test]
fn relocated_byte_arm_80_9f() -> Result<(), String> {
    byte_matrix(0x80..=0x9f)
}

#[test]
fn relocated_byte_arm_a0_bf() -> Result<(), String> {
    byte_matrix(0xa0..=0xbf)
}

#[test]
fn relocated_byte_arm_c0_df() -> Result<(), String> {
    byte_matrix(0xc0..=0xdf)
}

#[test]
fn relocated_byte_arm_e0_ff() -> Result<(), String> {
    byte_matrix(0xe0..=0xff)
}

#[test]
fn relocated_byte_arm_preserves_real_second_eof() -> Result<(), String> {
    let guest = plan()?;
    // A byte followed by true EOF still enters the byte arm, not the
    // first-EOF output arm. In particular 0xff is not the EOF sentinel.
    for first in [0, 0xff] {
        assert_byte_arm(&image(&guest.source, &[first])?, first, None)?;
    }
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "assert exact reached EOF-only output operand and I/O effects"
)]
#[test]
fn relocated_eof_arm_materializes_and_emits_zero() -> Result<(), String> {
    let guest = plan()?;
    let journal = image(&guest.source, &[])?;
    assert_common_prefix(&journal, None)?;
    assert_eq!(
        journal.source.outcome,
        RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 136,
        },
        "real first-EOF halt"
    );
    assert_eq!(
        journal.io_events,
        [input_event(53, 53, None), SourcePhysicalIoEvent::Output {
            code_address: 141,
            accumulator: 0,
            byte: 0,
            trace_index: 134,
        },],
        "EOF must emit zero only after the first read"
    );
    assert!(write(&journal, 127, 76, 4_782_981), "physical reentry seed");
    assert!(
        write(&journal, 133, CHECKSUM_LOW, 0),
        "read/rotate the zero checksum"
    );
    assert!(write(&journal, 139, 7_174_454, ONES), "prime output word");
    assert!(write(&journal, 140, OUTPUT, 0), "physical output SSA store");
    assert_eq!(
        final_word(&journal, OUTPUT),
        Some(0),
        "live output SSA word"
    );
    assert_eq!(
        journal.code_fetches.last().map(|fetch| fetch.code_address),
        Some(142),
        "actual EOF halt address"
    );
    Ok(())
}

fn omit(source: &[u8], position: usize) -> Result<Vec<u8>, String> {
    replace_opcode(source, position, b'o')
}

fn replace_opcode(
    source: &[u8],
    position: usize,
    opcode: u8,
) -> Result<Vec<u8>, String> {
    let mut mutant = source.to_vec();
    let site = u32::try_from(position).map_err(|error| error.to_string())?;
    *mutant.get_mut(position).ok_or("invalid mutation site")? = (33..=126u8)
        .find(|&cell| {
            decode_profile_instruction(u32::from(cell), site) == Some(opcode)
        })
        .ok_or("missing instruction encoding")?;
    Ok(mutant)
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "assert precise omission effects in actual guest executions"
)]
#[test]
fn omitted_discriminator_branch_read_and_output_store_are_observable()
-> Result<(), String> {
    let guest = plan()?;
    // Removing C97 routes byte zero through the wrong EOF-only output arm.
    let wrong_class = image(&omit(&guest.source, 97)?, &[0, 0xa5])?;
    assert_eq!(
        final_word(&wrong_class, MASK),
        Some(620_014),
        "omitted fold changes the class word"
    );
    assert_eq!(
        wrong_class.io_events,
        [
            input_event(53, 53, Some(0)),
            SourcePhysicalIoEvent::Output {
                code_address: 141,
                accumulator: 0,
                byte: 0,
                trace_index: 134,
            },
        ],
        "byte zero incorrectly enters the EOF output arm"
    );

    // Removing C118 bypasses the actual conditional and causes a second EOF
    // attempt on an empty stream instead of materializing the output operand.
    let wrong_branch = image(&omit(&guest.source, 118)?, &[])?;
    assert_eq!(
        wrong_branch.io_events,
        [input_event(53, 53, None), input_event(120, 120, None),],
        "omitted branch performs a second EOF attempt"
    );
    assert_eq!(
        final_word(&wrong_branch, OUTPUT),
        None,
        "no reached EOF operand store"
    );

    let missing_read = image(&omit(&guest.source, 120)?, &[0xff, 0xa5])?;
    assert_eq!(
        missing_read.io_events,
        [input_event(53, 53, Some(0xff))],
        "second input must really execute"
    );

    let missing_write = image(&omit(&guest.source, 140)?, &[])?;
    assert_eq!(
        missing_write.io_events,
        [input_event(53, 53, None), SourcePhysicalIoEvent::Output {
            code_address: 141,
            accumulator: ONES,
            byte: 53,
            trace_index: 134,
        },],
        "omitted output store leaks the prime accumulator"
    );
    assert_eq!(
        final_word(&missing_write, OUTPUT),
        None,
        "output operand was not written"
    );
    Ok(())
}

const fn address_probe<'source>(
    source: &'source [u8],
    input: &'source [u8],
) -> AddressSelectedIndirectProbe<'source> {
    AddressSelectedIndirectProbe {
        cases: [
            AddressSelectedIndirectCase {
                input,
                landing_address: 120,
                pointer_cell: 117,
            },
            AddressSelectedIndirectCase {
                input: &[],
                landing_address: 126,
                pointer_cell: 48,
            },
        ],
        indirect_code_cell: 118,
        input_code_cell: 53,
        selector_cell: MASK,
        selector_code_cell: 107,
        selector_store_code_cell: 99,
        source,
        step_budget: 136,
    }
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "assert independently reconstructed paired physical evidence"
)]
#[test]
fn paired_address_selection_authenticates_byte_and_eof() -> Result<(), String> {
    let guest = plan()?;
    let input = [0xff, 0xa5];
    let proof = verify_address_selected_indirect_guest(
        current_profile(),
        address_probe(&guest.source, &input),
    )
    .map_err(|error| format!("paired address proof: {error:?}"))?;
    let [byte, eof] = proof.cases();
    assert_eq!(proof.source(), guest.source, "same admitted source");
    assert_eq!(byte.input(), input, "exact byte stream");
    assert!(eof.input().is_empty(), "real EOF stream");
    assert_eq!(
        byte.input_origin(),
        (TraceInput::Byte(0xff), 53),
        "byte input"
    );
    assert_eq!(
        eof.input_origin(),
        (TraceInput::EndOfInput, 53),
        "EOF input"
    );
    assert_route_receipt(byte, BYTE_CLASS, 117, 120);
    assert_route_receipt(eof, EOF_CLASS, 48, 126);
    assert_byte_arm(byte.journal(), 0xff, Some(0xa5))?;
    assert_common_prefix(eof.journal(), None)?;
    Ok(())
}

fn assert_route_receipt(
    case: &super::layout::AddressSelectedIndirectCaseProof,
    class: u32,
    pointer: u32,
    landing: u32,
) {
    assert_eq!(case.selector_write().after, class, "reached class write");
    assert_eq!(case.selector_write().code_address, 99, "actual class store");
    assert_eq!(
        case.route().first().map(|read| read.code_address),
        Some(107),
        "first selector jump"
    );
    assert_eq!(
        case.route().get(1).map(|read| read.data_address),
        class.checked_add(1),
        "first selected route operand"
    );
    assert_eq!(
        case.transfer().data_address,
        pointer,
        "actual selected address"
    );
    assert_eq!(
        case.transfer().value.checked_add(1),
        Some(landing),
        "actual selected pointer word"
    );
    assert_eq!(case.landing_address(), landing, "actual landing");
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "negative controls distinguish proof boundaries"
)]
#[test]
fn address_selection_rejects_false_claims() -> Result<(), String> {
    let guest = plan()?;
    let probe = address_probe(&guest.source, &[0]);
    let mut wrong_pointer = probe;
    let [byte, eof] = &mut wrong_pointer.cases;
    byte.pointer_cell = eof.pointer_cell;
    let mut wrong_landing = probe;
    let [byte_landing, eof_landing] = &mut wrong_landing.cases;
    byte_landing.landing_address = eof_landing.landing_address;
    let [same_byte, _] = probe.cases;
    let controls = [
        (wrong_pointer, AddressSelectedIndirectError::InvalidTransfer),
        (wrong_landing, AddressSelectedIndirectError::InvalidTransfer),
        (
            AddressSelectedIndirectProbe {
                input_code_cell: 54,
                ..probe
            },
            AddressSelectedIndirectError::InvalidInput,
        ),
        (
            AddressSelectedIndirectProbe {
                selector_store_code_cell: 97,
                ..probe
            },
            AddressSelectedIndirectError::InvalidSelector,
        ),
        (
            AddressSelectedIndirectProbe {
                selector_cell: RAW_LOW,
                ..probe
            },
            AddressSelectedIndirectError::InvalidSelector,
        ),
        (
            AddressSelectedIndirectProbe {
                cases: [same_byte, same_byte],
                ..probe
            },
            AddressSelectedIndirectError::NonDistinctCases,
        ),
        (
            AddressSelectedIndirectProbe {
                step_budget: 120,
                ..probe
            },
            AddressSelectedIndirectError::InvalidTermination,
        ),
    ];
    for (bad, expected) in controls {
        assert_eq!(
            verify_address_selected_indirect_guest(current_profile(), bad),
            Err(expected),
            "refuse forged physical witness {bad:?}"
        );
    }
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "actual mutation and independent writer-only gate refusals"
)]
#[test]
fn address_selection_preserves_writer_gate() -> Result<(), String> {
    let guest = plan()?;
    let probe = address_probe(&guest.source, &[0]);
    let mutant = omit(&guest.source, 118)?;
    assert!(
        verify_address_selected_indirect_guest(
            current_profile(),
            address_probe(&mutant, &[0])
        )
        .is_err(),
        "missing transfer cannot supply evidence"
    );
    assert_eq!(
        verify_address_selected_indirect_guest(historical_profile(), probe),
        Err(AddressSelectedIndirectError::InvalidBound),
        "N10 profile must not authenticate N15 source"
    );
    for case in probe.cases {
        assert_eq!(
            verify_source_written_indirect_guest(
                current_profile(),
                SourceWrittenIndirectGuestProbe {
                    allowed_landings: &[120, 126],
                    indirect_code_cell: 118,
                    input: case.input,
                    pointer_cell: case.pointer_cell,
                    source: probe.source,
                    step_budget: probe.step_budget,
                },
            ),
            Err(SourceWrittenIndirectGuestError::MissingGuestPointerWrite),
            "address selection does not constitute a guest pointer-value write"
        );
    }
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "actual route mutation preserves landings but must be refused"
)]
#[test]
fn address_selection_refuses_route_write_despite_matching_arms()
-> Result<(), String> {
    let guest = plan()?;
    let mutant = replace_opcode(&guest.source, 111, b'*')?;
    for (input, landing) in [(&[0u8][..], 120), (&[][..], 126)] {
        let journal = image(&mutant, input)?;
        assert_eq!(
            journal
                .code_fetches
                .get(119)
                .map(|fetch| fetch.code_address),
            Some(landing),
            "mutation still physically reaches the expected arm"
        );
        assert!(
            journal
                .data_writes
                .iter()
                .any(|write| write.code_address == 111),
            "the route really executes a rotate store"
        );
    }
    assert_eq!(
        verify_address_selected_indirect_guest(
            current_profile(),
            address_probe(&mutant, &[0])
        ),
        Err(AddressSelectedIndirectError::InvalidRoute),
        "an intervening data write invalidates a read-only route proof"
    );
    Ok(())
}
