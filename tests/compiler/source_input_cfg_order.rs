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
            Err(SourceInputTraceError::UnexpectedGuestOutput),
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
        Err(SourceInputTraceError::UnexpectedGuestOutput),
        "unsourced guest output refuses before checking the missing loop input",
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

// One source-typed byte trace has two real inputs and one source-located
// output. This checks physical effect-site provenance, *not* the missing
// source SSA stores or a compiled C function.
fn two_input_byte_output_wire() -> Result<Vec<u8>, String> {
    use super::super::typed_cfg_adapter::typed::{
        BasicBlock, BasicBlockSpec, BlockId, Function, FunctionId,
        FunctionSpec, Instruction, LocatedInstruction, Module, ModuleSpec,
        SourcePosition, SourceSpan, Terminator, TypeDef, TypeEntry, TypeId,
        ValueId, canonical_bytes, validate_module,
    };
    let span = |start: u32, end: u32| {
        SourceSpan::new(
            SourcePosition::new(start, 1, start + 1),
            SourcePosition::new(end, 1, end + 1),
        )
    };
    let byte_type = TypeId::new(0);
    let module = Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version:
            super::super::typed_cfg_adapter::typed::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions: vec![
                    LocatedInstruction::new(
                        Instruction::ByteInput {
                            result: ValueId::new(0),
                            type_id: byte_type,
                        },
                        span(0, 1),
                    ),
                    LocatedInstruction::new(
                        Instruction::ByteInput {
                            result: ValueId::new(1),
                            type_id: byte_type,
                        },
                        span(1, 2),
                    ),
                    LocatedInstruction::new(
                        Instruction::ByteOutput { value: ValueId::new(1) },
                        span(2, 3),
                    ),
                ],
                phis: Vec::new(),
                span: span(0, 4),
                terminator: Terminator::Return { value: None },
                terminator_span: span(3, 4),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("two_input_byte_output"),
            parameters: Vec::new(),
            signature: TypeId::new(1),
            span: span(0, 4),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/two-input-byte-output.c"),
        source_sha256: [0x45; 32],
        target_profile: String::from("malbolge-2026"),
        types: vec![
            TypeEntry::new(byte_type, TypeDef::U8),
            TypeEntry::new(
                TypeId::new(1),
                TypeDef::function(Vec::new(), None, false),
            ),
        ],
    });
    validate_module(&module).map_err(|error| format!("typed: {error:?}"))?;
    canonical_bytes(&module).map_err(|error| format!("canonical: {error:?}"))
}

// One canonical typed U8 input optionally followed by its byte output.
// Its source-placed effects can be verified against genuine N15 operations
// rather than only necessary minimum code reservations.
fn single_byte_input_wire() -> Result<Vec<u8>, String> {
    single_byte_program_wire(false)
}

fn single_byte_input_output_wire() -> Result<Vec<u8>, String> {
    single_byte_program_wire(true)
}

fn single_byte_program_wire(with_output: bool) -> Result<Vec<u8>, String> {
    use super::super::typed_cfg_adapter::typed::{
        BasicBlock, BasicBlockSpec, BlockId, Function, FunctionId,
        FunctionSpec, Instruction, LocatedInstruction, Module, ModuleSpec,
        SourcePosition, SourceSpan, Terminator, TypeDef, TypeEntry, TypeId,
        ValueId, canonical_bytes, validate_module,
    };
    let span = SourceSpan::new(
        SourcePosition::new(0, 1, 1),
        SourcePosition::new(1, 1, 2),
    );
    let byte_type = TypeId::new(0);
    let mut instructions = vec![LocatedInstruction::new(
        Instruction::ByteInput {
            result: ValueId::new(0),
            type_id: byte_type,
        },
        span,
    )];
    if with_output {
        instructions.push(LocatedInstruction::new(
            Instruction::ByteOutput { value: ValueId::new(0) },
            span,
        ));
    }
    let module = Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version:
            super::super::typed_cfg_adapter::typed::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions,
                phis: Vec::new(),
                span,
                terminator: Terminator::Return { value: None },
                terminator_span: span,
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from(if with_output {
                "single_byte_input_output"
            } else {
                "single_byte_input"
            }),
            parameters: Vec::new(),
            signature: TypeId::new(1),
            span,
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from(if with_output {
            "fixtures/single-byte-input-output.c"
        } else {
            "fixtures/single-byte-input.c"
        }),
        source_sha256: if with_output {
            [0x54; 32]
        } else {
            [0x53; 32]
        },
        target_profile: String::from("malbolge-2026"),
        types: vec![
            TypeEntry::new(byte_type, TypeDef::U8),
            TypeEntry::new(
                TypeId::new(1),
                TypeDef::function(Vec::new(), None, false),
            ),
        ],
    });
    validate_module(&module).map_err(|error| format!("typed: {error:?}"))?;
    canonical_bytes(&module).map_err(|error| format!("canonical: {error:?}"))
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real byte-exact N15 guest and source-locked store-site refusals"
)]
fn actual_guest_byte_store_requires_its_source_effect_address()
-> Result<(), String> {
    use super::super::typed_cfg_adapter::state_relocation::{
        GuestCodeBlockPlacement, GuestCodeEffectAnchor, GuestCodeInputAnchor,
        GuestCodeOperationAnchor, GuestCodeProposals,
    };
    use super::{SourceInputProbe, SourceInputTraceError};

    // Pinned source bytes are independently decoded and proven in the
    // byte-exact guest test; avoid regenerating the bounded search here.
    let physical = b"DCBA@?>n~5|3Ex6";
    assert_eq!(
        malbolge::decode_profile_instruction(u32::from(physical[7]), 7),
        Some(b'/'),
    );
    assert_eq!(
        malbolge::decode_profile_instruction(u32::from(physical[11]), 11),
        Some(b'p'),
    );
    let wire = single_byte_input_wire()?;
    let blocks = [GuestCodeBlockPlacement {
        block: 0,
        control_start: 12,
        end_exclusive: 13,
        function: 0,
        start: 0,
    }];
    let proposals = GuestCodeProposals {
        code_blocks: &blocks,
        edge_pads: &[],
    };
    let operations = [GuestCodeOperationAnchor {
        block: 0,
        code_address: 7,
        function: 0,
        ordinal: 0,
    }];
    let effects = [GuestCodeEffectAnchor {
        block: 0,
        code_address: 11,
        effect_index: 1,
        function: 0,
        ordinal: 0,
    }];
    let inputs = [GuestCodeInputAnchor {
        block: 0,
        code_address: 7,
        function: 0,
        ordinal: 0,
    }];
    for stream in [&[0][..], &[255, 99][..]] {
        let probe = SourceInputProbe {
            anchors: &inputs,
            canonical: &wire,
            frame_base: 55,
            input: stream,
            physical_source: physical,
            step_budget: 13,
        };
        let proof = probe
            .verify_stored_with_effect_anchors(proposals, &operations, &effects)
            .map_err(|error| format!("source store {stream:?}: {error:?}"))?;
        assert_eq!(proof.prefix.bytes_consumed, 1);
        assert!(proof.prefix.guest_output.is_empty());
        assert_eq!(proof.stores.len(), 1);
        assert_eq!(proof.stores[0].cells.len(), 1);
        assert_eq!(
            (
                proof.stores[0].cells[0].code_address,
                proof.stores[0].cells[0].address,
                proof.stores[0].cells[0].trace_index,
                proof.stores[0].cells[0].value,
            ),
            (11, 55, 11, u32::from(stream[0])),
        );
    }
    let probe = SourceInputProbe {
        anchors: &inputs,
        canonical: &wire,
        frame_base: 55,
        input: &[42, 99],
        physical_source: physical,
        step_budget: 13,
    };
    // Matching stored bytes, dependencies and return are insufficient
    // if the only source-identified store code site is C10, not C11.
    let wrong_site = [GuestCodeEffectAnchor {
        code_address: 10,
        ..effects[0]
    }];
    assert!(
        probe
            .verify_return_with_effect_anchors(
                proposals,
                &operations,
                &wrong_site,
            )
            .is_ok()
    );
    assert_eq!(
        probe.verify_stored_with_effect_anchors(
            proposals,
            &operations,
            &wrong_site,
        ),
        Err(SourceInputTraceError::UnexpectedGuestStoreSite),
    );
    // Without a sparse store anchor, an adjacent C8 proposal also
    // cannot authenticate the genuine C11 word write.
    assert_eq!(
        probe.verify_stored_with_effect_anchors(proposals, &operations, &[],),
        Err(SourceInputTraceError::UnexpectedGuestStoreSite),
    );
    let probe = SourceInputProbe {
        anchors: &inputs,
        canonical: &wire,
        frame_base: 55,
        input: &[],
        physical_source: physical,
        step_budget: 13,
    };
    assert_eq!(
        probe.verify_stored_with_effect_anchors(
            proposals,
            &operations,
            &effects,
        ),
        Err(SourceInputTraceError::SourceInputUnreachable),
        "unsigned-byte source paths cannot read true EOF",
    );
    Ok(())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "one physical guest and two negative placement cases"
)]
fn real_guest_byte_store_and_source_output_require_both_effect_sites()
-> Result<(), String> {
    use super::super::typed_cfg_adapter::state_relocation::{
        GuestCodeBlockPlacement, GuestCodeEffectAnchor, GuestCodeInputAnchor,
        GuestCodeOperationAnchor, GuestCodeProposals,
    };
    use super::{SourceInputProbe, SourceInputTraceError};

    // Frozen source-loaded N15 guest derived from the independent
    // byte-exact two-read/reentry generator, with C25/C26 replaced by
    // graphical no-ops. These suppress the helper's extra read/output.
    // The original C13 input, C17 exact p store at M73 and C24 echo remain.
    let physical =
        b"DCBA@?>=<;:98hx/v-210/p-K+*)ji&%$#\"!~}|{zyxwvutsrqponmlkjihgs%H";
    let wire = single_byte_input_output_wire()?;
    let blocks = [GuestCodeBlockPlacement {
        function: 0,
        block: 0,
        start: 0,
        end_exclusive: 61,
        control_start: 60,
    }];
    let proposals = GuestCodeProposals {
        code_blocks: &blocks,
        edge_pads: &[],
    };
    let operations = [
        GuestCodeOperationAnchor {
            block: 0,
            code_address: 13,
            function: 0,
            ordinal: 0,
        },
        GuestCodeOperationAnchor {
            block: 0,
            code_address: 24,
            function: 0,
            ordinal: 1,
        },
    ];
    let effects = [GuestCodeEffectAnchor {
        block: 0,
        code_address: 17,
        effect_index: 1,
        function: 0,
        ordinal: 0,
    }];
    let inputs = [GuestCodeInputAnchor {
        block: 0,
        code_address: 13,
        function: 0,
        ordinal: 0,
    }];
    for stream in [&[0u8][..], &[255, 19][..], &[73, 255][..]] {
        let probe = SourceInputProbe {
            anchors: &inputs,
            canonical: &wire,
            frame_base: 73,
            input: stream,
            physical_source: physical,
            step_budget: 61,
        };
        let proof = probe
            .verify_output_and_stored_with_effect_anchors(
                proposals,
                &operations,
                &effects,
            )
            .map_err(|error| format!("physical byte {stream:?}: {error:?}"))?;
        let first_byte = *stream.first().ok_or("missing first input byte")?;
        let cell = proof
            .stores
            .first()
            .and_then(|store| store.cells.first())
            .ok_or("missing verified guest result word")?;
        assert_eq!(proof.prefix.bytes_consumed, 1, "one physical read");
        assert_eq!(proof.prefix.guest_output, [first_byte], "guest echo");
        assert_eq!(cell.code_address, 17, "reached source store opcode");
        assert_eq!(cell.address, 73, "source result word");
        assert_eq!(cell.value, u32::from(first_byte), "guest input word");
        assert_eq!(proof.frame_writes, [*cell], "no extra frame writes");
    }
    let probe = SourceInputProbe {
        anchors: &inputs,
        canonical: &wire,
        frame_base: 73,
        input: &[37],
        physical_source: physical,
        step_budget: 61,
    };
    assert_eq!(
        probe.verify_output_and_stored_with_effect_anchors(
            proposals,
            &operations,
            &[GuestCodeEffectAnchor {
                code_address: 16,
                ..effects[0]
            }],
        ),
        Err(SourceInputTraceError::UnexpectedGuestStoreSite),
    );
    // Source-compatible byte output and even genuine input-dependent
    // frame storage are insufficient if the reached < instruction has
    // moved away from the authenticated ByteOutput operation at C24.
    let mut shifted = physical.to_vec();
    for (address, opcode) in [(23usize, b'<'), (24, b'o')] {
        let encoded = (33..=126u8)
            .find(|byte| {
                malbolge::decode_profile_instruction(
                    u32::from(*byte),
                    u32::try_from(address).unwrap_or(u32::MAX),
                ) == Some(opcode)
            })
            .ok_or("graphical output shift missing")?;
        *shifted.get_mut(address).ok_or("output address absent")? = encoded;
    }
    let shifted_probe = SourceInputProbe {
        physical_source: &shifted,
        ..probe
    };
    let shifted_store = shifted_probe
        .verify_stored_with_effect_anchors(proposals, &operations, &effects)
        .map_err(|error| format!("shifted output kept store: {error:?}"))?;
    assert_eq!(
        shifted_store
            .stores
            .first()
            .and_then(|store| store.cells.first())
            .map(|cell| cell.value),
        Some(37),
        "wrong output site must not invalidate real input storage",
    );
    assert_eq!(
        shifted_probe.verify_output_and_stored_with_effect_anchors(
            proposals,
            &operations,
            &effects,
        ),
        Err(SourceInputTraceError::UnexpectedGuestOutput),
    );
    // A physically stored result cannot excuse an omitted source output.
    // C24 becomes an inert no-op; nothing else about the input or store
    // provenance changes.
    let mut silent = physical.to_vec();
    let no_output = (33..=126u8)
        .find(|byte| {
            malbolge::decode_profile_instruction(u32::from(*byte), 24)
                == Some(b'o')
        })
        .ok_or("graphical silent instruction missing")?;
    *silent.get_mut(24).ok_or("source output cell absent")? = no_output;
    let silent_probe = SourceInputProbe {
        physical_source: &silent,
        ..probe
    };
    assert_eq!(
        silent_probe.verify_output_and_stored_with_effect_anchors(
            proposals,
            &operations,
            &effects,
        ),
        Err(SourceInputTraceError::SourceOutputNotProven),
    );
    // An unsigned source input does not reinterpret a real guest EOF
    // sentinel as a successful byte even when the physical p path halts.
    let eof_probe = SourceInputProbe { input: &[], ..probe };
    assert_eq!(
        eof_probe.verify_output_and_stored_with_effect_anchors(
            proposals,
            &operations,
            &effects,
        ),
        Err(SourceInputTraceError::SourceInputUnreachable),
    );

    // After the authentic C17 store and C24 output, C29 has D=M73
    // again. Replacing its j with * performs a second *real* store
    // of zero to M73 on NUL. This idempotent mutation leaves the
    // source-compatible input, output, final memory and halt intact,
    // but it is not the source-anchored C17 store.
    let mut rogue = physical.to_vec();
    let extra_rotate = (33..=126u8)
        .find(|byte| {
            malbolge::decode_profile_instruction(u32::from(*byte), 29)
                == Some(b'*')
        })
        .ok_or("graphical rogue rotation missing")?;
    *rogue.get_mut(29).ok_or("rogue code cell absent")? = extra_rotate;
    let rogue_probe = SourceInputProbe {
        input: &[0],
        physical_source: &rogue,
        ..probe
    };
    assert!(
        rogue_probe
            .verify_output_with_operation_anchors(proposals, &operations)
            .is_ok(),
        "raw NUL output and source return still agree",
    );
    assert_eq!(
        rogue_probe.verify_output_and_stored_with_effect_anchors(
            proposals,
            &operations,
            &effects,
        ),
        Err(SourceInputTraceError::UnexpectedGuestStoreSite),
        "all frame mutations, not just the correct C17 store, need anchors",
    );
    let changed_probe = SourceInputProbe {
        input: &[37],
        ..rogue_probe
    };
    assert_eq!(
        changed_probe.verify_output_and_stored_with_effect_anchors(
            proposals,
            &operations,
            &effects,
        ),
        Err(SourceInputTraceError::InputResultMismatch),
        "non-idempotent late mutation also corrupts the live source result",
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "source-locked sparse guest effect placement refusals"
)]
fn sparse_input_effect_anchors_allow_real_setup_gaps_but_not_reordering()
-> Result<(), String> {
    use super::super::typed_cfg_adapter::state_relocation::{
        GuestCodeBlockPlacement, GuestCodeEffectAnchor,
        GuestCodeOperationAnchor, GuestCodeOperationEffect,
        GuestCodePlacementError, GuestCodeProposals,
        bind_source_locked_cfg_code_targets_with_effect_anchors,
    };

    let wire = two_input_byte_output_wire()?;
    let blocks = [GuestCodeBlockPlacement {
        block: 0,
        control_start: 15,
        end_exclusive: 16,
        function: 0,
        start: 0,
    }];
    let proposals = GuestCodeProposals {
        code_blocks: &blocks,
        edge_pads: &[],
    };
    let operations = [
        GuestCodeOperationAnchor {
            block: 0,
            code_address: 0,
            function: 0,
            ordinal: 0,
        },
        GuestCodeOperationAnchor {
            block: 0,
            code_address: 7,
            function: 0,
            ordinal: 1,
        },
        GuestCodeOperationAnchor {
            block: 0,
            code_address: 14,
            function: 0,
            ordinal: 2,
        },
    ];
    let stores = [
        GuestCodeEffectAnchor {
            block: 0,
            code_address: 5,
            effect_index: 1,
            function: 0,
            ordinal: 0,
        },
        GuestCodeEffectAnchor {
            block: 0,
            code_address: 12,
            effect_index: 1,
            function: 0,
            ordinal: 1,
        },
    ];
    let bind = |effects: &[GuestCodeEffectAnchor]| {
        bind_source_locked_cfg_code_targets_with_effect_anchors(
            &wire,
            16,
            256,
            proposals,
            &operations,
            effects,
        )
    };
    let plan = bind(&stores).map_err(|error| format!("layout: {error:?}"))?;
    assert_eq!(
        plan.operation_effect_sites
            .iter()
            .map(|site| (site.code_address, site.ordinal, site.effect))
            .collect::<Vec<_>>(),
        vec![
            (0, 0, plan.operation_effect_sites[0].effect),
            (5, 0, plan.operation_effect_sites[1].effect),
            (7, 1, plan.operation_effect_sites[2].effect),
            (12, 1, plan.operation_effect_sites[3].effect),
            (14, 2, plan.operation_effect_sites[4].effect),
        ],
    );
    assert!(matches!(
        plan.operation_effect_sites[1].effect,
        GuestCodeOperationEffect::Store { .. }
    ));
    assert!(matches!(
        plan.operation_effect_sites[3].effect,
        GuestCodeOperationEffect::Store { .. }
    ));
    assert_eq!(
        plan.operation_sites
            .iter()
            .map(|site| (site.start, site.end_exclusive))
            .collect::<Vec<_>>(),
        [(0, 6), (7, 13), (14, 15)],
    );
    let refusal = Err(GuestCodePlacementError::InvalidCodePlacement);
    for invalid in [
        vec![stores[0], stores[0]],
        vec![GuestCodeEffectAnchor {
            code_address: 0,
            ..stores[0]
        }],
        vec![GuestCodeEffectAnchor {
            code_address: 7,
            ..stores[0]
        }],
        vec![GuestCodeEffectAnchor {
            code_address: 15,
            ..stores[1]
        }],
        vec![GuestCodeEffectAnchor {
            effect_index: 2,
            ..stores[0]
        }],
        vec![GuestCodeEffectAnchor { ordinal: 99, ..stores[0] }],
        vec![GuestCodeEffectAnchor { block: 99, ..stores[0] }],
        vec![GuestCodeEffectAnchor {
            function: 99,
            ..stores[0]
        }],
    ] {
        assert_eq!(bind(&invalid), refusal);
    }
    // The old operation-only entrypoint keeps its adjacent effect layout.
    let ordinary = super::super::typed_cfg_adapter::state_relocation::
        bind_source_locked_cfg_code_targets_with_operation_anchors(
            &wire, 16, 256, proposals, &operations,
        ).map_err(|error| format!("adjacent layout: {error:?}"))?;
    assert_eq!(
        ordinary
            .operation_effect_sites
            .iter()
            .map(|site| site.code_address)
            .collect::<Vec<_>>(),
        [0, 1, 7, 8, 14],
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real guest input and output provenance at exact typed addresses"
)]
fn explicit_output_anchors_require_reached_guest_output_site()
-> Result<(), String> {
    use malbolge::{current_profile, decode_profile_instruction};

    use super::super::typed_cfg_adapter::state_relocation::{
        GuestCodeBlockPlacement, GuestCodeInputAnchor,
        GuestCodeOperationAnchor, GuestCodeProposals,
    };
    use super::SourceInputProbe;

    let wire = two_input_byte_output_wire()?;
    let encoded = |operations: &[u8]| -> Result<Vec<u8>, String> {
        operations
            .iter()
            .enumerate()
            .map(|(address, &opcode)| {
                (33u8..=126)
                    .find(|&byte| {
                        decode_profile_instruction(
                            u32::from(byte),
                            address as u32,
                        ) == Some(opcode)
                    })
                    .ok_or_else(|| {
                        format!("no graphical opcode {opcode} at {address}")
                    })
            })
            .collect()
    };
    let correct = encoded(b"/o/o<v")?;
    let mislocated = encoded(b"/o/<ov")?;
    let blocks = [GuestCodeBlockPlacement {
        block: 0,
        control_start: 5,
        end_exclusive: 6,
        function: 0,
        start: 0,
    }];
    let proposals = GuestCodeProposals {
        code_blocks: &blocks,
        edge_pads: &[],
    };
    let operation_anchors = [
        GuestCodeOperationAnchor {
            block: 0,
            code_address: 0,
            function: 0,
            ordinal: 0,
        },
        GuestCodeOperationAnchor {
            block: 0,
            code_address: 2,
            function: 0,
            ordinal: 1,
        },
        GuestCodeOperationAnchor {
            block: 0,
            code_address: 4,
            function: 0,
            ordinal: 2,
        },
    ];
    let inputs = [
        GuestCodeInputAnchor {
            block: 0,
            code_address: 0,
            function: 0,
            ordinal: 0,
        },
        GuestCodeInputAnchor {
            block: 0,
            code_address: 2,
            function: 0,
            ordinal: 1,
        },
    ];
    for stream in [&[0, 0xff][..], &[0xff, 0][..], &[23, 42, 99][..]] {
        let expected = stream[1];
        let probe = SourceInputProbe {
            anchors: &inputs,
            canonical: &wire,
            frame_base: 256,
            input: stream,
            physical_source: &correct,
            step_budget: 6,
        };
        let proof = probe
            .verify_output_with_operation_anchors(proposals, &operation_anchors)
            .map_err(|error| {
                format!("source-placed guest output: {error:?}")
            })?;
        assert_eq!(proof.guest_output, [expected]);
        assert_eq!(proof.bytes_consumed, 2);
        assert_eq!(proof.io_events, [
            SourceInputIoEvent::Input { observation_index: 0 },
            SourceInputIoEvent::Input { observation_index: 1 },
            SourceInputIoEvent::Output(expected),
        ]);
        let shifted = SourceInputProbe {
            physical_source: &mislocated,
            ..probe
        };
        assert_eq!(
            shifted
                .verify_with_operation_anchors(proposals, &operation_anchors)
                .map_err(|error| format!("raw I/O compatibility: {error:?}"))?
                .guest_output,
            [expected],
            "raw byte parity does not authenticate output sites",
        );
        assert_eq!(
            shifted.verify_output_with_operation_anchors(
                proposals,
                &operation_anchors
            ),
            Err(SourceInputTraceError::UnexpectedGuestOutput),
        );
    }
    // An EOF cannot masquerade as a successful byte-typed source input.
    assert_eq!(
        SourceInputProbe {
            anchors: &inputs,
            canonical: &wire,
            frame_base: 256,
            input: &[23],
            physical_source: &correct,
            step_budget: 6,
        }
        .verify_output_with_operation_anchors(proposals, &operation_anchors),
        Err(SourceInputTraceError::SourceInputUnreachable),
    );
    assert_eq!(current_profile().input_instruction(), b'/');
    Ok(())
}
