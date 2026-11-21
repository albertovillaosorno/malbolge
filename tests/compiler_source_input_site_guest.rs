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
//   - Real guest input-site trace matching for the unchanged C23 checksum.
// - Must-Not:
//   - Treat matching / input sites as compiled C arithmetic or EOF control.
// - Allows:
//   - Inputs: frozen typed checksum, physical signed converter, finite streams.
//   - Outputs: raw input site evidence and precise mismatch refusal.
//   - Side effects: bounded isolated normative N15 VM runs.
// - Split-When:
//   - Whole-source C translation validation checks every guest instruction.
// - Merge-When:
//   - The full checksum guest linker emits verified executable control.
// - Summary:
//   - Distinguishes real source-bound input events from proposed code sites.

//! Normative source-typed *input-only* prefix evidence, never C checksum
//! parity.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;
use std::str;

use layout::typed_cfg_adapter::state_relocation::{
    GuestCodeInputAnchor, GuestCodeInputSemantics,
};
use layout::{
    SourceInputIoEvent, SourceInputPrefixProof, SourceInputProbe,
    SourceInputTraceError,
    build_c23_signed_output_with_post_conversion_fold_source,
    build_guarded_signed_eof_second_read_source,
    build_second_input_eof_classified_first_echo_source,
    verify_source_input_site_output_compatible,
    verify_source_input_site_prefix,
    verify_source_input_site_return_compatible,
    verify_source_input_site_stored_results,
};
use malbolge::{
    ProfileMachine, RunOutcome, Termination, TraceInput, current_profile,
    decode_profile_instruction,
};

const CHECKSUM_TYPED: &str =
    include_str!("compiler/typed-ir/golden/mutable-eof-checksum.hex");

// Frozen guest read vector pairs for source prefix matching.
type RevisitedInputVector = (&'static [u8], [TraceInput; 3]);

fn checksum_wire() -> Result<Vec<u8>, String> {
    let digits = CHECKSUM_TYPED
        .trim_end()
        .strip_prefix("malbolge-typed-ir-v1:")
        .ok_or("frozen source-locked C23 checksum IR is missing")?;
    let (chunks, remainder) = digits.as_bytes().as_chunks::<2>();
    if !remainder.is_empty() {
        return Err("odd-length canonical hex fixture".to_owned());
    }
    chunks
        .iter()
        .map(|hex| {
            let text =
                str::from_utf8(hex).map_err(|error| error.to_string())?;
            u8::from_str_radix(text, 16).map_err(|error| error.to_string())
        })
        .collect()
}

const fn input_anchors() -> [GuestCodeInputAnchor; 2] {
    [
        GuestCodeInputAnchor {
            block: 0,
            code_address: 37,
            function: 0,
            ordinal: 1,
        },
        GuestCodeInputAnchor {
            block: 5,
            code_address: 66,
            function: 0,
            ordinal: 2,
        },
    ]
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "exact guest input observations are test assertions"
)]
fn assert_source_input(
    proof: &SourceInputPrefixProof,
    address: u32,
    expected: (u32, u32, Option<u8>),
) -> Result<(), String> {
    let (block, ordinal, byte) = expected;
    let observation = proof
        .observations
        .iter()
        .find(|item| item.code_address == address)
        .ok_or_else(|| format!("missing guest read at {address}"))?;
    assert_eq!((observation.block, observation.ordinal), (block, ordinal));
    assert_eq!(observation.function, 0);
    assert_eq!(
        observation.trace_index,
        usize::try_from(address).map_err(|error| error.to_string())?
    );
    assert_eq!(observation.destination.words, 2);
    assert_eq!(
        observation.input,
        byte.map_or(TraceInput::EndOfInput, TraceInput::Byte)
    );
    assert_eq!(
        observation.raw_accumulator,
        byte.map_or(current_profile().eof_word(), u32::from)
    );
    assert!(matches!(
        observation.semantics,
        GuestCodeInputSemantics::SignedC23 {
            raw_eof_word: 14_348_906,
            c23_eof_cells: [4_644_102, 299],
        }
    ));
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "exact normative guest input and EOF witness"
)]
fn physical_two_read_prefix_matches_both_authenticated_source_input_sites()
-> Result<(), String> {
    let source = build_c23_signed_output_with_post_conversion_fold_source(
        current_profile(),
    )
    .map_err(|error| format!("{error:?}"))?;
    let wire = checksum_wire()?;
    for stream in [
        vec![0x5a],
        vec![0x5a, 0],
        vec![0x5a, 1, 0x77],
        vec![0x5a, 0x80],
        vec![0x5a, 0xff],
        vec![0xff],
        vec![0xff, 0],
    ] {
        let first = stream.first().copied();
        let second = stream.get(1).copied();
        let proof = verify_source_input_site_prefix(SourceInputProbe {
            anchors: &input_anchors(),
            canonical: &wire,
            frame_base: 128,
            input: &stream,
            physical_source: &source,
            step_budget: 82,
        })
        .map_err(|error| format!("{error:?}"))?;
        assert_eq!(proof.outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 82,
        });
        assert_eq!(proof.bytes_consumed, stream.len().min(2));
        assert_eq!(proof.guest_output, [second.unwrap_or(255)]);
        assert_eq!(proof.observations.len(), 2);
        assert_source_input(&proof, 37, (0, 1, first))?;
        assert_source_input(&proof, 66, (5, 2, second))?;
        let unique_destinations = proof
            .observations
            .iter()
            .map(|item| item.destination.address)
            .collect::<BTreeSet<_>>();
        assert_eq!(unique_destinations.len(), 2);
    }
    assert_ne!(current_profile().eof_word(), 255);
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "explicit bounded negative trace checks"
)]
fn physical_input_witness_rejects_unbound_extra_or_missing_guest_reads()
-> Result<(), String> {
    let profile = current_profile();
    let source =
        build_c23_signed_output_with_post_conversion_fold_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    let wire = checksum_wire()?;
    let anchors = input_anchors();
    let probe = SourceInputProbe {
        anchors: &anchors,
        canonical: &wire,
        frame_base: 128,
        input: &[3, 4],
        physical_source: &source,
        step_budget: 82,
    };
    assert_eq!(
        verify_source_input_site_prefix(SourceInputProbe {
            anchors: &anchors[..1],
            ..probe
        }),
        Err(SourceInputTraceError::MissingSourceAnchor),
    );
    assert_eq!(
        verify_source_input_site_prefix(SourceInputProbe {
            step_budget: 0,
            ..probe
        }),
        Err(SourceInputTraceError::InvalidProbeBound),
    );
    assert_eq!(
        verify_source_input_site_prefix(SourceInputProbe {
            step_budget: 81,
            ..probe
        }),
        Err(SourceInputTraceError::StepBudgetExhausted),
    );
    let mut corrupted_wire = wire.clone();
    corrupted_wire.push(0);
    assert_eq!(
        verify_source_input_site_prefix(SourceInputProbe {
            canonical: &corrupted_wire,
            ..probe
        }),
        Err(SourceInputTraceError::InvalidSourcePlacement),
    );
    // C80 normally folds converted data. An extra decoded / at C80 is an
    // actual third read, not an authenticated C23 source-input site.
    let third_read = (33u8..=126)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), 80) == Some(b'/')
        })
        .ok_or("no graphical third read at C80")?;
    let mut extra_source = source.clone();
    *extra_source.get_mut(80).ok_or("short physical guest")? = third_read;
    assert_eq!(
        verify_source_input_site_prefix(SourceInputProbe {
            input: &[3, 4, 5],
            physical_source: &extra_source,
            ..probe
        }),
        Err(SourceInputTraceError::UnexpectedGuestInput),
    );
    Ok(())
}

// Reaching a physical halt is not enough if a required source input was
// replaced by an unrelated legal guest instruction at its code address.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "deliberately substituted physical opcode must fail closed"
)]
fn physically_unreached_c23_input_site_is_rejected() -> Result<(), String> {
    let source = build_c23_signed_output_with_post_conversion_fold_source(
        current_profile(),
    )
    .map_err(|error| format!("{error:?}"))?;
    let replacement_noop = (33u8..=126)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), 66) == Some(b'o')
        })
        .ok_or("no graphical no-op at C66")?;
    let mut missing_read_source = source;
    *missing_read_source
        .get_mut(66)
        .ok_or("short guest source")? = replacement_noop;
    let wire = checksum_wire()?;
    assert_eq!(
        verify_source_input_site_prefix(SourceInputProbe {
            anchors: &input_anchors(),
            canonical: &wire,
            frame_base: 128,
            input: &[3, 4],
            physical_source: &missing_read_source,
            step_budget: 82,
        }),
        Err(SourceInputTraceError::UnreachedSourceInput),
    );
    // True first-read EOF takes the original checksum's source exit; it
    // does not owe the loop's second getchar. This guest is still not a C
    // implementation because its output/state are unlinked.
    let early_exit = verify_source_input_site_prefix(SourceInputProbe {
        anchors: &input_anchors(),
        canonical: &wire,
        frame_base: 128,
        input: &[],
        physical_source: &missing_read_source,
        step_budget: 82,
    })
    .map_err(|error| {
        format!("valid EOF source-input prefix refused: {error:?}")
    })?;
    assert_eq!(early_exit.observations.len(), 1);
    assert_eq!(
        early_exit
            .observations
            .first()
            .ok_or("missing first EOF observation")?
            .input,
        TraceInput::EndOfInput,
    );
    assert_eq!(early_exit.bytes_consumed, 0);
    Ok(())
}

// Input-only opcode parity must not certify an impossible source path: on
// true first-read EOF the original C loop exits without a second getchar.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "source EOF exit is an essential negative guest prefix witness"
)]
fn physical_first_eof_cannot_reach_checksum_loop_read() -> Result<(), String> {
    let source = build_c23_signed_output_with_post_conversion_fold_source(
        current_profile(),
    )
    .map_err(|error| format!("{error:?}"))?;
    let wire = checksum_wire()?;
    assert_eq!(
        verify_source_input_site_prefix(SourceInputProbe {
            anchors: &input_anchors(),
            canonical: &wire,
            frame_base: 128,
            input: &[],
            physical_source: &source,
            step_budget: 82,
        }),
        Err(SourceInputTraceError::SourceInputUnreachable)
    );
    Ok(())
}

// One fresh input at C3 followed by two input events at the *same* C47
// instruction proves a source-loop read can revisit one physical guest cell.
// The guest remains an unconditional finite three-read probe, not a compiled
// C23 EOF branch, mutable checksum or source-verified output.
fn physical_repeated_loop_input_source() -> Result<Vec<u8>, String> {
    let mut source = (0..117u32)
        .map(|position| {
            (33u8..=126)
                .find(|byte| {
                    decode_profile_instruction(u32::from(*byte), position)
                        == Some(b'o')
                })
                .ok_or_else(|| format!("missing no-op at C{position}"))
        })
        .collect::<Result<Vec<_>, _>>()?;
    for (position, opcode) in [
        (3usize, b'/'),
        (47, b'/'),
        (48, b'j'),
        (49, b'i'),
        (73, b'j'),
        (74, b'j'),
        (75, b'i'),
        (116, b'v'),
    ] {
        let code_address =
            u32::try_from(position).map_err(|error| error.to_string())?;
        let encoded = (33u8..=126)
            .find(|byte| {
                decode_profile_instruction(u32::from(*byte), code_address)
                    == Some(opcode)
            })
            .ok_or_else(|| format!("no {opcode} encoding at C{position}"))?;
        *source.get_mut(position).ok_or("short physical source")? = encoded;
    }
    for (position, value) in
        [(66usize, 109u8), (87, 46), (91, 65), (110, 46), (113, 115)]
    {
        *source.get_mut(position).ok_or("short data source")? = value;
    }
    Ok(source)
}

fn repeated_input_vectors() -> [RevisitedInputVector; 4] {
    [
        (&[1, 2][..], [
            TraceInput::Byte(1),
            TraceInput::Byte(2),
            TraceInput::EndOfInput,
        ]),
        (&[1, 2, 3, 4][..], [
            TraceInput::Byte(1),
            TraceInput::Byte(2),
            TraceInput::Byte(3),
        ]),
        (&[0xff, 0x80][..], [
            TraceInput::Byte(0xff),
            TraceInput::Byte(0x80),
            TraceInput::EndOfInput,
        ]),
        (&[1, 0xff, 0][..], [
            TraceInput::Byte(1),
            TraceInput::Byte(0xff),
            TraceInput::Byte(0),
        ]),
    ]
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "finite physical guest read trace assertions"
)]
fn assert_revisited_input_path(
    probe: SourceInputProbe<'_>,
    input: &[u8],
    expected: [TraceInput; 3],
) -> Result<(), String> {
    let result =
        verify_source_input_site_prefix(SourceInputProbe { input, ..probe })
            .map_err(|error| {
                format!("repeated physical source input: {error:?}")
            })?;
    assert_eq!(result.outcome, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: 60,
    });
    assert_eq!(result.bytes_consumed, input.len().min(3));
    assert_eq!(result.guest_output, []);
    assert_eq!(
        result
            .observations
            .iter()
            .map(|item| (item.code_address, item.trace_index, item.input))
            .collect::<Vec<_>>(),
        vec![
            (3, 3, expected[0]),
            (47, 47, expected[1]),
            (47, 56, expected[2]),
        ],
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "actual three-event N15 input execution and source path assertions"
)]
fn physical_loop_read_site_can_repeat_after_source_cfg_backedge()
-> Result<(), String> {
    let physical = physical_repeated_loop_input_source()?;
    let canonical = checksum_wire()?;
    let anchors = [
        GuestCodeInputAnchor {
            block: 0,
            code_address: 3,
            function: 0,
            ordinal: 1,
        },
        GuestCodeInputAnchor {
            block: 5,
            code_address: 47,
            function: 0,
            ordinal: 2,
        },
    ];
    let probe = SourceInputProbe {
        anchors: &anchors,
        canonical: &canonical,
        frame_base: 128,
        input: &[1, 2],
        physical_source: &physical,
        step_budget: 60,
    };
    for (input, expected) in repeated_input_vectors() {
        assert_revisited_input_path(probe, input, expected)?;
    }
    // The source must refuse a third read after either EOF guard. A raw
    // N15 EOF is different from a successful source-C getchar byte 0xff.
    for bytes in [&[][..], &[1][..]] {
        assert_eq!(
            verify_source_input_site_prefix(SourceInputProbe {
                input: bytes,
                ..probe
            }),
            Err(SourceInputTraceError::SourceInputUnreachable),
        );
    }
    assert_eq!(
        verify_source_input_site_prefix(SourceInputProbe {
            step_budget: 59,
            ..probe
        }),
        Err(SourceInputTraceError::StepBudgetExhausted),
    );
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    clippy::too_many_arguments,
    reason = "frozen physical source, two source anchors and one bounded stream"
)]
fn assert_two_read_branch_overlap(
    physical: &[u8],
    wire: &[u8],
    anchors: &[GuestCodeInputAnchor],
    input: &[u8],
    second: TraceInput,
    steps: usize,
) -> Result<(), String> {
    let profile = current_profile();
    let mut machine =
        ProfileMachine::from_source(profile, physical, input.to_vec())
            .map_err(|error| error.to_string())?;
    let mut inputs = Vec::new();
    let outcome = machine
        .run_traced(175, &mut |step| {
            if let Some(byte) = step.input {
                inputs.push((step.before.registers.code_pointer, byte));
            }
        })
        .map_err(|error| error.to_string())?;
    assert_eq!(outcome, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps,
    });
    assert_eq!(inputs, vec![
        (
            53,
            input
                .first()
                .copied()
                .map_or(TraceInput::EndOfInput, TraceInput::Byte,)
        ),
        (63, second),
    ]);
    assert_eq!(
        verify_source_input_site_prefix(SourceInputProbe {
            anchors,
            canonical: wire,
            frame_base: 256,
            input,
            physical_source: physical,
            step_budget: 175,
        }),
        Err(SourceInputTraceError::InvalidSourcePlacement),
    );
    Ok(())
}

// This real physical guest branches after two independent input opcodes,
// but the checksum's C23 block-0 minimum 16-word interval cannot fit beside
// the block-5 input anchor only ten positions later. Reject this exact
// source-site linkage rather than weakening disjoint code-region admission.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "bounded physical EOF-branch witness and exact layout refusal"
)]
fn physical_second_eof_branch_refuses_overlapping_checksum_blocks()
-> Result<(), String> {
    let profile = current_profile();
    let physical = build_second_input_eof_classified_first_echo_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    let wire = checksum_wire()?;
    let anchors = [
        GuestCodeInputAnchor {
            block: 0,
            code_address: 53,
            function: 0,
            ordinal: 1,
        },
        GuestCodeInputAnchor {
            block: 5,
            code_address: 63,
            function: 0,
            ordinal: 2,
        },
    ];
    let minimum = layout::typed_cfg_adapter::state_relocation::
        plan_source_locked_cfg_minimum_code_targets(
            &wire,
            u32::try_from(physical.len()).map_err(|error| error.to_string())?,
            256,
            0,
        )
        .map_err(|error| format!("minimum plan: {error:?}"))?;
    let block0 = minimum.code_blocks.first().ok_or("missing block 0")?;
    assert_eq!(block0.end_exclusive - block0.start, 16);
    let first = anchors.first().ok_or("missing first anchor")?;
    let loop_anchor = anchors.get(1).ok_or("missing loop anchor")?;
    let first_end =
        first.code_address + block0.end_exclusive - block0.start - 1;
    assert!(first_end > loop_anchor.code_address);
    assert_eq!(
        layout::typed_cfg_adapter::state_relocation::
            plan_source_locked_cfg_with_input_anchors(
                &wire,
                u32::try_from(physical.len())
                    .map_err(|error| error.to_string())?,
                256,
                &anchors,
            ),
        Err(layout::typed_cfg_adapter::state_relocation::
            GuestCodePlacementError::InvalidCodePlacement),
    );
    for (input, second, steps) in [
        (&[][..], TraceInput::EndOfInput, 119usize),
        (&[1][..], TraceInput::EndOfInput, 119),
        (&[1, 0][..], TraceInput::Byte(0), 175),
        (&[0xff, 0xff][..], TraceInput::Byte(0xff), 175),
    ] {
        assert_two_read_branch_overlap(
            &physical, &wire, &anchors, input, second, steps,
        )?;
    }
    Ok(())
}

// The first-read EOF branch is a stronger physical candidate than the
// second-read EOF classifier: its two sites are 48 cells apart, so the
// checksum's full-width block-0 reservations need not overlap block 5.
// This remains input-only source/guest linkage, not an emitted C checksum.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "bounded physical conditional input and canonical C23 CFG witness"
)]
fn guarded_first_eof_branch_admits_disjoint_checksum_input_anchors()
-> Result<(), String> {
    let physical =
        build_guarded_signed_eof_second_read_source(current_profile())
            .map_err(|error| format!("{error:?}"))?;
    let wire = checksum_wire()?;
    let anchors = [
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
    let plan = layout::typed_cfg_adapter::state_relocation::
        plan_source_locked_cfg_with_input_anchors(
            &wire,
            u32::try_from(physical.len()).map_err(|error| error.to_string())?,
            256,
            &anchors,
        )
        .map_err(|error| format!("disjoint source plan: {error:?}"))?;
    let first = plan
        .code_blocks
        .iter()
        .find(|block| block.block == 0)
        .ok_or("missing source entry block")?;
    let loop_read = plan
        .code_blocks
        .iter()
        .find(|block| block.block == 5)
        .ok_or("missing source loop-read block")?;
    assert!(first.end_exclusive <= loop_read.start);
    for (input, expected, steps) in [
        (&[][..], vec![(53, TraceInput::EndOfInput)], 119),
        (
            &[0][..],
            vec![(53, TraceInput::Byte(0)), (101, TraceInput::EndOfInput)],
            175,
        ),
        (
            &[0xff][..],
            vec![(53, TraceInput::Byte(0xff)), (101, TraceInput::EndOfInput)],
            175,
        ),
        (
            &[1, 2][..],
            vec![(53, TraceInput::Byte(1)), (101, TraceInput::Byte(2))],
            175,
        ),
    ] {
        let proof = verify_source_input_site_prefix(SourceInputProbe {
            anchors: &anchors,
            canonical: &wire,
            frame_base: 256,
            input,
            physical_source: &physical,
            step_budget: 175,
        })
        .map_err(|error| format!("source-guarded guest: {error:?}"))?;
        assert_eq!(proof.outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps,
        });
        assert_eq!(
            proof
                .observations
                .iter()
                .map(|item| (item.code_address, item.input))
                .collect::<Vec<_>>(),
            expected,
        );
        assert_eq!(proof.bytes_consumed, input.len().min(2));
        let input_zero = SourceInputIoEvent::Input { observation_index: 0 };
        let input_one = SourceInputIoEvent::Input { observation_index: 1 };
        let expected_io = if input.is_empty() {
            vec![input_zero, SourceInputIoEvent::Output(30)]
        } else {
            vec![input_zero, SourceInputIoEvent::Output(154), input_one]
        };
        assert_eq!(proof.io_events, expected_io);
    }
    Ok(())
}

// Physical halt following both anchored reads does not prove a completed
// source input path: a successful second byte makes the C23 checksum loop
// require another read, whereas true second EOF permits a source return.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "physical EOF-aware return-path evidence and necessary refusal"
)]
fn guarded_guest_halt_requires_source_eof_compatible_return_path()
-> Result<(), String> {
    let physical =
        build_guarded_signed_eof_second_read_source(current_profile())
            .map_err(|error| format!("{error:?}"))?;
    let wire = checksum_wire()?;
    let anchors = [
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
    let probe = SourceInputProbe {
        anchors: &anchors,
        canonical: &wire,
        frame_base: 256,
        input: &[],
        physical_source: &physical,
        step_budget: 175,
    };
    for (input, steps, consumed) in
        [(&[][..], 119, 0), (&[1][..], 175, 1), (&[0xff][..], 175, 1)]
    {
        let proof =
            verify_source_input_site_return_compatible(SourceInputProbe {
                input,
                ..probe
            })
            .map_err(|error| {
                format!("valid source-return prefix: {error:?}")
            })?;
        assert_eq!(proof.outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps,
        });
        assert_eq!(proof.bytes_consumed, consumed);
    }
    assert_eq!(
        verify_source_input_site_return_compatible(SourceInputProbe {
            input: &[1, 2],
            ..probe
        }),
        Err(SourceInputTraceError::UnreachedSourceInput),
    );
    assert_eq!(
        verify_source_input_site_return_compatible(SourceInputProbe {
            input: &[1, 0xff],
            ..probe
        }),
        Err(SourceInputTraceError::UnreachedSourceInput),
    );
    assert_eq!(
        verify_source_input_site_return_compatible(SourceInputProbe {
            input: &[1],
            step_budget: 174,
            ..probe
        }),
        Err(SourceInputTraceError::StepBudgetExhausted),
    );
    Ok(())
}

// Source input/return viability is not output parity: this real guest emits
// EOF/byte classifier markers rather than the mutable C checksum result.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "exact real-N15 output refusal for source-locked C checksum"
)]
fn guarded_guest_refuses_checksum_output_parity() -> Result<(), String> {
    let physical =
        build_guarded_signed_eof_second_read_source(current_profile())
            .map_err(|error| format!("{error:?}"))?;
    let canonical = checksum_wire()?;
    let anchors = [
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
    for input in [&[][..], &[0][..], &[1][..], &[0xff][..]] {
        assert_eq!(
            verify_source_input_site_output_compatible(SourceInputProbe {
                anchors: &anchors,
                canonical: &canonical,
                frame_base: 256,
                input,
                physical_source: &physical,
                step_budget: 175,
            }),
            Err(SourceInputTraceError::SourceOutputNotProven),
        );
    }
    assert_eq!(
        verify_source_input_site_output_compatible(SourceInputProbe {
            anchors: &anchors,
            canonical: &canonical,
            frame_base: 256,
            input: &[1, 2],
            physical_source: &physical,
            step_budget: 175,
        }),
        Err(SourceInputTraceError::UnreachedSourceInput),
    );
    Ok(())
}

// The full source C23 input result is two reserved frame words. Real guest
// input opcodes update A but never populate that frame in this classifier;
// input-order, return and even ordered I/O checks cannot substitute stores.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real N15 input transition, missing guest C32 writes"
)]
fn unwritten_c23_input_result_refused() -> Result<(), String> {
    let physical =
        build_guarded_signed_eof_second_read_source(current_profile())
            .map_err(|error| format!("{error:?}"))?;
    let canonical = checksum_wire()?;
    let anchors = [
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
    for input in [&[][..], &[0][..], &[0xff][..]] {
        let probe = SourceInputProbe {
            anchors: &anchors,
            canonical: &canonical,
            frame_base: 256,
            input,
            physical_source: &physical,
            step_budget: 175,
        };
        let returned = verify_source_input_site_return_compatible(probe)
            .map_err(|error| format!("source return: {error:?}"))?;
        assert_eq!(
            returned.observations.len(),
            if input.is_empty() {
                1
            } else {
                2
            }
        );
        assert_eq!(
            verify_source_input_site_stored_results(probe),
            Err(SourceInputTraceError::MissingInputResultStore),
        );
    }
    assert_eq!(
        verify_source_input_site_stored_results(SourceInputProbe {
            anchors: &anchors,
            canonical: &canonical,
            frame_base: 256,
            input: &[1, 2],
            physical_source: &physical,
            step_budget: 175,
        }),
        Err(SourceInputTraceError::UnreachedSourceInput),
    );
    Ok(())
}
