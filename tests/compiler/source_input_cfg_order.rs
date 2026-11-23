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
//   - Source-CFG reachability of authenticated physical input prefixes.
// - Must-Not:
//   - Treat branch reachability as a proof of source branch predicates.
// - Allows:
//   - Inputs: frozen source-C checksum and synthetic source-site orderings.
//   - Outputs: exact admission/refusal for feasible source CFG prefixes.
//   - Side effects: none.
// - Split-When:
//   - Complete guest control-flow translation verification is available.
// - Merge-When:
//   - Input reachability becomes part of full source-linked trace checking.
// - Summary:
//   - Forbids physical inputs in an impossible source CFG order.

//! Source path ordering is a necessary condition, not a guest branch proof.

use std::str;

use malbolge::TraceInput;

use super::super::typed_cfg_adapter::lower_canonical_dynamic_cfg;
use super::super::typed_cfg_adapter::ternary::{
    TernaryCfgBlock, TernaryCfgFunction, TernaryCfgScalarKind,
    TernaryCfgTerminator, TernaryI32Scalar, TernaryOperation,
    TernarySourcePosition, TernarySourceSpan,
};
use super::{
    GuestCodeInputSemantics, GuestPlacedOperand, SourceInputIoEvent,
    SourceInputSiteObservation, SourceInputTraceError,
    source_path_matches_input_observables, source_path_matches_input_prefix,
    source_path_matches_input_trace, source_path_matches_input_walk,
    verify_source_cfg_input_order,
};

const CHECKSUM_TYPED: &str =
    include_str!("typed-ir/golden/mutable-eof-checksum.hex");

fn checksum_wire() -> Result<Vec<u8>, String> {
    let hex = CHECKSUM_TYPED
        .trim_end()
        .strip_prefix("malbolge-typed-ir-v1:")
        .ok_or_else(|| "frozen typed checksum fixture".to_owned())?;
    let (chunks, remainder) = hex.as_bytes().as_chunks::<2>();
    if !remainder.is_empty() {
        return Err("odd-length canonical hex fixture".to_owned());
    }
    chunks
        .iter()
        .map(|chunk| {
            let pair =
                str::from_utf8(chunk).map_err(|error| error.to_string())?;
            u8::from_str_radix(pair, 16).map_err(|error| error.to_string())
        })
        .collect()
}

fn observed(block: u32, ordinal: u32) -> SourceInputSiteObservation {
    SourceInputSiteObservation {
        block,
        code_address: if block == 0 {
            37
        } else {
            66
        },
        destination: GuestPlacedOperand {
            address: 200u32.saturating_add(block),
            type_kind: TernaryCfgScalarKind::I32,
            value: ordinal.saturating_add(1),
            words: 2,
        },
        function: 0,
        input: TraceInput::Byte(3),
        ordinal,
        raw_accumulator: 3,
        semantics: GuestCodeInputSemantics::SignedC23 {
            raw_eof_word: 14_348_906,
            c23_eof_cells: [4_644_102, 299],
        },
        trace_index: usize::try_from(block).unwrap_or_default(),
    }
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "explicit source CFG assertions"
)]
fn actual_checksum_cfg_requires_first_read_before_backedge_read()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let first = observed(0, 1);
    let loop_read = observed(5, 2);
    assert_eq!(
        verify_source_cfg_input_order(&wire, &[first, loop_read]),
        Ok(())
    );
    assert_eq!(verify_source_cfg_input_order(&wire, &[first]), Ok(()));
    // First-read EOF must take the source exit, even though a purely
    // branch-insensitive reachability walk could reach the loop read.
    let first_eof = SourceInputSiteObservation {
        input: TraceInput::EndOfInput,
        raw_accumulator: 14_348_906,
        ..first
    };
    assert_eq!(
        verify_source_cfg_input_order(&wire, &[first_eof, loop_read]),
        Err(SourceInputTraceError::SourceInputUnreachable)
    );
    assert_eq!(
        verify_source_cfg_input_order(&wire, &[loop_read]),
        Err(SourceInputTraceError::SourceInputUnreachable)
    );
    assert_eq!(
        verify_source_cfg_input_order(&wire, &[loop_read, first]),
        Err(SourceInputTraceError::SourceInputUnreachable)
    );
    // A source loop may reach the same read site again. The separate physical
    // prefix verifier refuses repeated code-site execution until a real
    // runtime CFG and guest state linker can prove repeated guest effects.
    assert_eq!(
        verify_source_cfg_input_order(&wire, &[first, loop_read, loop_read]),
        Ok(())
    );
    let second_eof = SourceInputSiteObservation {
        input: TraceInput::EndOfInput,
        raw_accumulator: 14_348_906,
        ..loop_read
    };
    assert_eq!(
        verify_source_cfg_input_order(&wire, &[first, second_eof, loop_read]),
        Err(SourceInputTraceError::SourceInputUnreachable)
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "complete source return and EOF input obligations"
)]
fn checksum_cfg_skipped_loop_input_requires_real_source_return()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let cfg = lower_canonical_dynamic_cfg(&wire)
        .map_err(|error| format!("{error:?}"))?;
    let function = cfg.functions.first().ok_or("missing source function")?;
    let first = observed(0, 1);
    let loop_read = observed(5, 2);
    let first_eof = SourceInputSiteObservation {
        input: TraceInput::EndOfInput,
        raw_accumulator: 14_348_906,
        ..first
    };
    let loop_eof = SourceInputSiteObservation {
        input: TraceInput::EndOfInput,
        raw_accumulator: 14_348_906,
        ..loop_read
    };
    for (sequence, possible) in [
        (vec![&first_eof], true),
        (vec![&first], false),
        (vec![&first, &loop_read], false),
        (vec![&first, &loop_eof], true),
        (vec![&first_eof, &loop_read], false),
        (vec![&loop_eof], false),
    ] {
        assert_eq!(
            source_path_matches_input_trace(function, &sequence, 128, true),
            Ok(possible),
            "source return after input sequence {sequence:?}",
        );
    }
    assert_eq!(
        source_path_matches_input_trace(function, &[&first_eof], 1, true),
        Err(SourceInputTraceError::SourceInputSearchLimit)
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "explicit source CFG refusals"
)]
fn source_cfg_path_cannot_skip_or_invent_source_input_sites()
-> Result<(), String> {
    let wire = checksum_wire()?;
    assert_eq!(
        verify_source_cfg_input_order(&wire, &[observed(6, 0)]),
        Err(SourceInputTraceError::SourceInputUnreachable)
    );
    assert_eq!(
        verify_source_cfg_input_order(&wire, &[observed(0, 2)]),
        Err(SourceInputTraceError::SourceInputUnreachable)
    );
    let mut corrupted = wire;
    corrupted.push(0);
    assert_eq!(
        verify_source_cfg_input_order(&corrupted, &[observed(0, 1)]),
        Err(SourceInputTraceError::InvalidSourcePlacement)
    );
    Ok(())
}

fn dummy_span() -> TernarySourceSpan {
    TernarySourceSpan {
        begin: TernarySourcePosition {
            byte: 0,
            column: 1,
            line: 1,
        },
        end: TernarySourcePosition {
            byte: 1,
            column: 2,
            line: 1,
        },
    }
}

fn guarded_inequality_fixture() -> TernaryCfgFunction {
    let span = dummy_span();
    TernaryCfgFunction {
        blocks: vec![
            TernaryCfgBlock {
                id: 0,
                operations: vec![
                    TernaryOperation::GetcharI32 { result: 0, span },
                    TernaryOperation::MaterializeI32 {
                        result: 1,
                        scalar: TernaryI32Scalar::from_bits(u32::MAX),
                        span,
                    },
                    TernaryOperation::NotEqualI32 {
                        left: 0,
                        result: 2,
                        right: 1,
                        span,
                    },
                ],
                phis: Vec::new(),
                terminator: TernaryCfgTerminator::Branch {
                    condition: 2,
                    false_target: 1,
                    span,
                    true_target: 2,
                },
            },
            TernaryCfgBlock {
                id: 1,
                operations: vec![TernaryOperation::GetcharI32 {
                    result: 3,
                    span,
                }],
                phis: Vec::new(),
                terminator: TernaryCfgTerminator::Return(
                    TernaryOperation::ReturnVoid { span },
                ),
            },
            TernaryCfgBlock {
                id: 2,
                operations: vec![TernaryOperation::GetcharI32 {
                    result: 4,
                    span,
                }],
                phis: Vec::new(),
                terminator: TernaryCfgTerminator::Return(
                    TernaryOperation::ReturnVoid { span },
                ),
            },
        ],
        entry: 0,
        id: 0,
        name: "emit".to_owned(),
        span,
    }
}

// Per-block ordinals reset at legitimate source CFG loop backedges. A
// monotone-ordinal check over the whole trace would incorrectly reject them;
// the authenticated CFG walk must also reject skipped earlier reads.
#[test]
fn source_loop_restarts_same_block_input_ordinals_without_reordering() {
    let span = dummy_span();
    let function = TernaryCfgFunction {
        blocks: vec![TernaryCfgBlock {
            id: 0,
            operations: vec![
                TernaryOperation::GetcharI32 { result: 0, span },
                TernaryOperation::GetcharI32 { result: 1, span },
            ],
            phis: Vec::new(),
            terminator: TernaryCfgTerminator::Jump { target: 0, span },
        }],
        entry: 0,
        id: 0,
        name: "emit".to_owned(),
        span,
    };
    let first = observed(0, 0);
    let second = observed(0, 1);
    for (sequence, valid) in [
        (vec![&first, &second, &first, &second], true),
        (vec![&first, &second, &first], true),
        (vec![&first, &first], false),
        (vec![&second, &first], false),
        (vec![&first, &second, &second], false),
    ] {
        assert_eq!(
            source_path_matches_input_prefix(&function, &sequence, 128),
            Ok(valid),
            "unexpected same-block CFG read order {sequence:?}",
        );
    }
}

#[test]
fn source_known_inequality_discriminates_high_byte_and_true_eof() {
    let function = guarded_inequality_fixture();
    let first_high = SourceInputSiteObservation {
        input: TraceInput::Byte(255),
        raw_accumulator: 255,
        ..observed(0, 0)
    };
    let first_eof = SourceInputSiteObservation {
        input: TraceInput::EndOfInput,
        raw_accumulator: 14_348_906,
        ..observed(0, 0)
    };
    let eof_arm = observed(1, 0);
    let byte_arm = observed(2, 0);
    assert_eq!(
        source_path_matches_input_prefix(
            &function,
            &[&first_high, &byte_arm],
            16_384,
        ),
        Ok(true)
    );
    assert_eq!(
        source_path_matches_input_prefix(
            &function,
            &[&first_high, &eof_arm],
            16_384,
        ),
        Ok(false)
    );
    assert_eq!(
        source_path_matches_input_prefix(
            &function,
            &[&first_eof, &eof_arm],
            16_384,
        ),
        Ok(true)
    );
    assert_eq!(
        source_path_matches_input_prefix(
            &function,
            &[&first_eof, &byte_arm],
            16_384,
        ),
        Ok(false)
    );
}

#[test]
fn exhausted_source_path_search_is_not_an_unreachable_path_proof() {
    let function = guarded_inequality_fixture();
    let first = observed(0, 0);
    let second = observed(2, 0);
    assert_eq!(
        source_path_matches_input_prefix(&function, &[&first, &second], 1),
        Err(SourceInputTraceError::SourceInputSearchLimit)
    );
    assert_eq!(
        source_path_matches_input_prefix(&function, &[&first, &second], 128),
        Ok(true)
    );
}

fn guarded_byte_cast_fixture() -> TernaryCfgFunction {
    let span = dummy_span();
    let mut function = guarded_inequality_fixture();
    let Some(block) = function.blocks.first_mut() else {
        return function;
    };
    block.operations = vec![
        TernaryOperation::GetcharI32 { result: 0, span },
        TernaryOperation::BitcastI32ToU32 {
            result: 1,
            value: 0,
            span,
        },
        TernaryOperation::TruncateU32ToU8 {
            result: 2,
            value: 1,
            span,
        },
        TernaryOperation::U8ToBool {
            result: 3,
            value: 2,
            span,
        },
    ];
    block.terminator = TernaryCfgTerminator::Branch {
        condition: 3,
        false_target: 1,
        true_target: 2,
        span,
    };
    function
}

#[test]
fn source_known_c23_casts_preserve_zero_and_truncate_eof() {
    let function = guarded_byte_cast_fixture();
    let first_zero = SourceInputSiteObservation {
        input: TraceInput::Byte(0),
        raw_accumulator: 0,
        ..observed(0, 0)
    };
    let first_high = SourceInputSiteObservation {
        input: TraceInput::Byte(255),
        raw_accumulator: 255,
        ..observed(0, 0)
    };
    let first_eof = SourceInputSiteObservation {
        input: TraceInput::EndOfInput,
        raw_accumulator: 14_348_906,
        ..observed(0, 0)
    };
    let zero_arm = observed(1, 0);
    let nonzero_arm = observed(2, 0);
    for (first, expected_block) in
        [(first_zero, 1u32), (first_high, 2u32), (first_eof, 2u32)]
    {
        for (arm, block) in [(zero_arm, 1u32), (nonzero_arm, 2u32)] {
            assert_eq!(
                source_path_matches_input_prefix(
                    &function,
                    &[&first, &arm],
                    128,
                ),
                Ok(block == expected_block),
                "source input {first:?}, successor block {block}",
            );
        }
    }
}

#[test]
fn source_known_equality_selects_only_the_matching_input_arm() {
    let mut function = guarded_inequality_fixture();
    let span = dummy_span();
    if let Some(operation) = function
        .blocks
        .first_mut()
        .and_then(|block| block.operations.get_mut(2))
    {
        *operation = TernaryOperation::EqualI32 {
            left: 0,
            result: 2,
            right: 1,
            span,
        };
    }
    let first_byte = observed(0, 0);
    let first_eof = SourceInputSiteObservation {
        input: TraceInput::EndOfInput,
        raw_accumulator: 14_348_906,
        ..first_byte
    };
    let false_arm = observed(1, 0);
    let true_arm = observed(2, 0);
    assert_eq!(
        source_path_matches_input_prefix(
            &function,
            &[&first_byte, &true_arm],
            128
        ),
        Ok(false),
    );
    assert_eq!(
        source_path_matches_input_prefix(
            &function,
            &[&first_eof, &false_arm],
            128
        ),
        Ok(false),
    );
    assert_eq!(
        source_path_matches_input_prefix(
            &function,
            &[&first_eof, &true_arm],
            128
        ),
        Ok(true),
    );
}

fn guarded_threshold_fixture(unsigned: bool) -> TernaryCfgFunction {
    let span = dummy_span();
    let mut function = guarded_inequality_fixture();
    let Some(block) = function.blocks.first_mut() else {
        return function;
    };
    let initial_read = TernaryOperation::GetcharI32 { result: 0, span };
    let threshold = TernaryI32Scalar::from_bits(128);
    if unsigned {
        block.operations = vec![
            initial_read,
            TernaryOperation::BitcastI32ToU32 {
                value: 0,
                result: 5,
                span,
            },
            TernaryOperation::MaterializeU32 {
                result: 1,
                scalar: threshold,
                span,
            },
            TernaryOperation::LessUnsignedU32 {
                left: 5,
                right: 1,
                result: 2,
                span,
            },
        ];
    } else {
        block.operations = vec![
            initial_read,
            TernaryOperation::MaterializeI32 {
                result: 1,
                scalar: threshold,
                span,
            },
            TernaryOperation::LessSignedI32 {
                left: 0,
                right: 1,
                result: 2,
                span,
            },
        ];
    }
    function
}

#[test]
fn source_known_signed_and_unsigned_thresholds_separate_eof_from_bytes() {
    let signed = guarded_threshold_fixture(false);
    let unsigned = guarded_threshold_fixture(true);
    let first = observed(0, 0);
    let false_arm = observed(1, 0);
    let true_arm = observed(2, 0);
    for (input, signed_true, unsigned_true) in [
        (TraceInput::Byte(0), true, true),
        (TraceInput::Byte(127), true, true),
        (TraceInput::Byte(128), false, false),
        (TraceInput::Byte(255), false, false),
        (TraceInput::EndOfInput, true, false),
    ] {
        let current = SourceInputSiteObservation { input, ..first };
        for (function, expected) in
            [(&signed, signed_true), (&unsigned, unsigned_true)]
        {
            assert_eq!(
                source_path_matches_input_prefix(
                    function,
                    &[&current, &true_arm],
                    128,
                ),
                Ok(expected),
            );
            assert_eq!(
                source_path_matches_input_prefix(
                    function,
                    &[&current, &false_arm],
                    128,
                ),
                Ok(!expected),
            );
        }
    }
}

// This oracle walks the original normalized C CFG, not the guest VM. Every
// real source input (including true EOF) must reach exactly the one C output
// byte; arbitrary output guesses must not satisfy the authenticated path.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "independently computed checksum and source CFG output assertions"
)]
fn complete_checksum_source_paths_require_exact_output_bytes()
-> Result<(), String> {
    let cfg = lower_canonical_dynamic_cfg(&checksum_wire()?)
        .map_err(|error| format!("{error:?}"))?;
    let source = cfg.functions.first().ok_or("missing checksum function")?;
    for input in [vec![], vec![0], vec![0xff], vec![1, 0, 0x80, 0xfe], vec![
        5, 0, 0x81,
    ]] {
        let first = observed(0, 1);
        let next = observed(5, 2);
        let mut reads = Vec::new();
        for (index, byte) in input.iter().copied().enumerate() {
            let site = if index == 0 {
                first
            } else {
                next
            };
            reads.push(SourceInputSiteObservation {
                input: TraceInput::Byte(byte),
                raw_accumulator: u32::from(byte),
                ..site
            });
        }
        reads.push(SourceInputSiteObservation {
            input: TraceInput::EndOfInput,
            raw_accumulator: 14_348_906,
            ..if input.is_empty() {
                first
            } else {
                next
            }
        });
        let observations = reads.iter().collect::<Vec<_>>();
        let mut checksum = 0u8;
        for byte in &input {
            checksum = if byte & 1 == 0 {
                checksum.wrapping_add(*byte)
            } else {
                checksum ^ byte
            };
            checksum = checksum.wrapping_add(3);
        }
        assert_eq!(
            source_path_matches_input_observables(
                source,
                &observations,
                &[checksum],
                16_384,
            ),
            Ok(true),
            "source refused correct checksum for {input:?}"
        );
        assert_eq!(
            source_path_matches_input_observables(
                source,
                &observations,
                &[checksum ^ 1],
                16_384,
            ),
            Ok(false),
            "source admitted incorrect checksum for {input:?}"
        );
    }
    Ok(())
}

// Deliberately unknown target arithmetic must not be promoted into a known
// source byte merely because a guest happened to emit that particular byte.
#[test]
fn unknown_source_arithmetic_cannot_certify_guest_output() {
    let span = dummy_span();
    let function = TernaryCfgFunction {
        blocks: vec![TernaryCfgBlock {
            id: 0,
            operations: vec![
                TernaryOperation::GetcharI32 { result: 0, span },
                TernaryOperation::MaterializeU32 {
                    result: 1,
                    scalar: TernaryI32Scalar::from_bits(0),
                    span,
                },
                TernaryOperation::MultiplyU32 {
                    left: 0,
                    result: 2,
                    right: 1,
                    span,
                },
                TernaryOperation::TruncateU32ToU8 {
                    result: 3,
                    value: 2,
                    span,
                },
                TernaryOperation::ByteOutput { value: 3, span },
            ],
            phis: Vec::new(),
            terminator: TernaryCfgTerminator::Return(
                TernaryOperation::ReturnVoid { span },
            ),
        }],
        entry: 0,
        id: 0,
        name: "unknown_output".to_owned(),
        span,
    };
    let first = observed(0, 0);
    assert_eq!(
        source_path_matches_input_observables(&function, &[&first], &[0], 128),
        Ok(false),
    );
    // An input-only path may exist without knowledge of target arithmetic.
    assert_eq!(
        source_path_matches_input_trace(&function, &[&first], 128, true),
        Ok(true),
    );
}

// Unsigned C32 additions wrap even when the guest must preserve two words.
// Reject a forged output and missing/extra outputs after a valid source return.
#[test]
fn known_source_unsigned_addition_preserves_full_width_wraparound() {
    let span = dummy_span();
    let function = TernaryCfgFunction {
        blocks: vec![TernaryCfgBlock {
            id: 0,
            operations: vec![
                TernaryOperation::MaterializeU32 {
                    result: 0,
                    scalar: TernaryI32Scalar::from_bits(u32::MAX),
                    span,
                },
                TernaryOperation::MaterializeU32 {
                    result: 1,
                    scalar: TernaryI32Scalar::from_bits(2),
                    span,
                },
                TernaryOperation::AddU32 {
                    left: 0,
                    result: 2,
                    right: 1,
                    span,
                },
                TernaryOperation::TruncateU32ToU8 {
                    result: 3,
                    value: 2,
                    span,
                },
                TernaryOperation::ByteOutput { value: 3, span },
            ],
            phis: Vec::new(),
            terminator: TernaryCfgTerminator::Return(
                TernaryOperation::ReturnVoid { span },
            ),
        }],
        entry: 0,
        id: 0,
        name: "unsigned_wrap".to_owned(),
        span,
    };
    assert_eq!(
        source_path_matches_input_observables(&function, &[], &[1], 128),
        Ok(true),
    );
    for wrong in [&[][..], &[0][..], &[1, 1][..], &[255][..]] {
        assert_eq!(
            source_path_matches_input_observables(&function, &[], wrong, 128),
            Ok(false),
        );
    }
}

// Matching the final bytes is not enough: the source checksum emits only
// after the exact final EOF input, not before a pending source read.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "original source CFG checks independently ordered physical I/O"
)]
fn checksum_source_io_requires_output_after_final_eof() -> Result<(), String> {
    let cfg = lower_canonical_dynamic_cfg(&checksum_wire()?)
        .map_err(|error| format!("{error:?}"))?;
    let source = cfg.functions.first().ok_or("missing source CFG")?;
    let first = SourceInputSiteObservation {
        input: TraceInput::Byte(1),
        raw_accumulator: 1,
        ..observed(0, 1)
    };
    let end = SourceInputSiteObservation {
        input: TraceInput::EndOfInput,
        raw_accumulator: 14_348_906,
        ..observed(5, 2)
    };
    let input_zero = SourceInputIoEvent::Input { observation_index: 0 };
    let input_one = SourceInputIoEvent::Input { observation_index: 1 };
    let output = SourceInputIoEvent::Output(4);
    let observed = [&first, &end];
    let good = [input_zero, input_one, output];
    let early = [input_zero, output, input_one];
    let reordered = [input_one, input_zero, output];
    for (events, valid) in [
        (&good[..], true),
        (&early[..], false),
        (&reordered[..], false),
    ] {
        assert_eq!(
            source_path_matches_input_walk(
                source,
                &observed,
                16_384,
                true,
                Some(&[4]),
                Some(events),
            ),
            Ok(valid),
            "I/O order {events:?}"
        );
    }
    Ok(())
}

// The same physical 132-cell byte/EOF branch can host two source-identified
// input effect sites even when their proposed code blocks reserve extra room
// for operand setup. This is input-only, not source-C state or CFG linkage.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "bounded source-locked and normative-guest input admission"
)]
fn physically_reached_input_effects_allow_expanded_code_block_anchors()
-> Result<(), String> {
    use malbolge::{RunOutcome, Termination, current_profile};

    use super::super::signed_eof_branch_source as signed_source;
    use super::super::typed_cfg_adapter::state_relocation::{
        GuestCodeBlockPlacement, GuestCodeEdgeKind, GuestCodeEdgePadPlacement,
        GuestCodeInputAnchor, GuestCodeOperationAnchor, GuestCodeProposals,
    };
    use super::SourceInputProbe;

    let wire = checksum_wire()?;
    let physical = signed_source::build_guarded_signed_eof_second_read_source(
        current_profile(),
    )
    .map_err(|error| format!("{error:?}"))?;
    assert_eq!(physical.len(), 132);
    let blocks = [
        (0, 40, 66, 67),
        (1, 0, 1, 2),
        (2, 2, 5, 6),
        (3, 6, 10, 11),
        (4, 11, 15, 16),
        (5, 91, 104, 105),
        (6, 16, 18, 19),
    ]
    .map(|(block, start, control_start, end_exclusive)| {
        GuestCodeBlockPlacement {
            block,
            control_start,
            end_exclusive,
            function: 0,
            start,
        }
    });
    let pads = [
        (0, 1, 19, 28),
        (3, 5, 28, 33),
        (4, 5, 33, 38),
        (5, 1, 105, 114),
    ]
    .map(|(predecessor, successor, start, end_exclusive)| {
        GuestCodeEdgePadPlacement {
            end_exclusive,
            function: 0,
            kind: GuestCodeEdgeKind::Jump,
            predecessor,
            start,
            successor,
        }
    });
    let proposals = GuestCodeProposals {
        code_blocks: &blocks,
        edge_pads: &pads,
    };
    let read_sites = [
        GuestCodeInputAnchor {
            block: 0,
            code_address: 53,
            function: 0,
            ordinal: 1,
        },
        GuestCodeInputAnchor {
            block: 5,
            code_address: 101,
            function: 0,
            ordinal: 2,
        },
    ];
    let operation_anchors = [
        GuestCodeOperationAnchor {
            block: 0,
            code_address: 53,
            function: 0,
            ordinal: 1,
        },
        GuestCodeOperationAnchor {
            block: 5,
            code_address: 101,
            function: 0,
            ordinal: 2,
        },
    ];
    for (input, expected, steps) in [
        (&[][..], vec![(53, TraceInput::EndOfInput)], 119),
        (
            &[0][..],
            vec![(53, TraceInput::Byte(0)), (101, TraceInput::EndOfInput)],
            175,
        ),
        (
            &[255, 0, 44][..],
            vec![(53, TraceInput::Byte(255)), (101, TraceInput::Byte(0))],
            175,
        ),
    ] {
        let proof = SourceInputProbe {
            anchors: &read_sites,
            canonical: &wire,
            frame_base: 256,
            input,
            physical_source: &physical,
            step_budget: 175,
        }
        .verify_with_operation_anchors(proposals, &operation_anchors)
        .map_err(|error| format!("source-bound guest: {error:?}"))?;
        assert_eq!(proof.outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps,
        });
        assert_eq!(
            proof
                .observations
                .iter()
                .map(|event| (event.code_address, event.input))
                .collect::<Vec<_>>(),
            expected
        );
    }
    // Reached signed reads alone do not implement the source checksum.
    // The unchanged physical helper emits a class marker, not the source
    // checksum byte, and one branch outputs before the final EOF read.
    for input in [&[][..], &[0][..], &[255][..]] {
        assert_eq!(
            SourceInputProbe {
                anchors: &read_sites,
                canonical: &wire,
                frame_base: 256,
                input,
                physical_source: &physical,
                step_budget: 175,
            }
            .verify_output_with_operation_anchors(
                proposals,
                &operation_anchors,
            ),
            Err(SourceInputTraceError::SourceOutputNotProven),
        );
    }
    assert_eq!(
        SourceInputProbe {
            anchors: &read_sites,
            canonical: &wire,
            frame_base: 256,
            input: &[255, 0, 44],
            physical_source: &physical,
            step_budget: 175,
        }
        .verify_output_with_operation_anchors(proposals, &operation_anchors),
        Err(SourceInputTraceError::UnreachedSourceInput),
        "source CFG cannot halt before its third loop input",
    );
    // The 132-cell guest reads real bytes, but it does not write the
    // source-C32 signed result into both authenticated SSA frame words.
    // Passing the input-placement and source-return gates is insufficient.
    for input in [&[][..], &[0][..], &[255][..]] {
        assert_eq!(
            SourceInputProbe {
                anchors: &read_sites,
                canonical: &wire,
                frame_base: 256,
                input,
                physical_source: &physical,
                step_budget: 175,
            }
            .verify_stored_with_operation_anchors(
                proposals,
                &operation_anchors,
            ),
            Err(SourceInputTraceError::MissingInputResultStore),
        );
    }
    let changed = [
        GuestCodeInputAnchor {
            code_address: 52,
            ..read_sites[0]
        },
        read_sites[1],
    ];
    assert_eq!(
        SourceInputProbe {
            anchors: &changed,
            canonical: &wire,
            frame_base: 256,
            input: &[0],
            physical_source: &physical,
            step_budget: 175,
        }
        .verify_with_operation_anchors(proposals, &operation_anchors),
        Err(SourceInputTraceError::InvalidSourcePlacement),
    );
    Ok(())
}
