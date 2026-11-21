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

use super::super::typed_cfg_adapter::ternary::TernaryCfgScalarKind;
use super::{
    GuestCodeInputSemantics, GuestPlacedOperand, SourceInputSiteObservation,
    SourceInputTraceError, verify_source_cfg_input_order,
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
    // Control predicates are intentionally not interpreted by this check:
    // an EOF first read cannot justify the second read in source C, even
    // though the unselected CFG contains a path to it. Guest branch parity
    // remains a separate mandatory obligation.
    let first_eof = SourceInputSiteObservation {
        input: TraceInput::EndOfInput,
        raw_accumulator: 14_348_906,
        ..first
    };
    assert_eq!(
        verify_source_cfg_input_order(&wire, &[first_eof, loop_read]),
        Ok(())
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
