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
    SourceInputPrefixProof, SourceInputProbe, SourceInputTraceError,
    build_c23_signed_output_with_post_conversion_fold_source,
    verify_source_input_site_prefix,
};
use malbolge::{
    RunOutcome, Termination, TraceInput, current_profile,
    decode_profile_instruction,
};

const CHECKSUM_TYPED: &str =
    include_str!("compiler/typed-ir/golden/mutable-eof-checksum.hex");

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
