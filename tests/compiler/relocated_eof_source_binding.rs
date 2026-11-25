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
//   - Source-locked reservations for the relocated EOF experiment.
// - Must-Not:
//   - Claim an executable complete source CFG or signed EOF normalization.
// - Allows:
//   - Inputs: canonical original checksum wire and real graphical guest.
//   - Outputs: exact reserved sites and independent source-I/O checks.
//   - Side effects: isolated normative VM replays.
// - Split-When:
//   - Complete source control and storage linking becomes available.
// - Merge-When:
//   - General source-locked physical linker tests subsume this witness.
// - Summary:
//   - Retains source identity while checking relocated guest limitations.

//! Original C23 checksum reservation and physical I/O boundary.

use std::str;

use malbolge::{TraceInput, current_profile};

use super::layout::typed_cfg_adapter::state_relocation::{
    GuestAddressedCfgPlan, GuestCodeBlockPlacement, GuestCodeEdgeKind,
    GuestCodeEdgePadPlacement, GuestCodeEffectAnchor, GuestCodeInputAnchor,
    GuestCodeOperationAnchor, GuestCodeOperationEffect, GuestCodeProposals,
    bind_source_locked_cfg_code_targets_with_effect_anchors,
};
use super::layout::{
    AddressSelectedIndirectCase, AddressSelectedIndirectProbe,
    AddressSelectedIndirectProof, AddressSelectedSourceReturnError,
    AddressSelectedSourceReturnProbe, SourceBranchLanding, SourceInputProbe,
    SourceInputTraceError, build_relocated_eof_branch_source,
    verify_address_selected_indirect_guest,
    verify_address_selected_source_return,
};

const FRAME: u32 = 7_174_417;
const BLOCKS: [GuestCodeBlockPlacement; 7] = [
    block(0, 0, 75, 76),
    block(1, 117, 118, 119),
    block(2, 120, 123, 124),
    block(3, 80, 84, 85),
    block(4, 85, 89, 90),
    block(5, 90, 97, 98),
    block(6, 126, 142, 143),
];
const PADS: [GuestCodeEdgePadPlacement; 4] = [
    pad(0, 1, 98, 107),
    pad(3, 5, 107, 112),
    pad(4, 5, 112, 117),
    pad(5, 1, 143, 152),
];
const PROPOSALS: GuestCodeProposals<'static> = GuestCodeProposals {
    code_blocks: &BLOCKS,
    edge_pads: &PADS,
};

const OPERATIONS: [GuestCodeOperationAnchor; 4] = [
    operation(0, 1, 53),
    operation(5, 2, 94),
    operation(6, 0, 140),
    operation(6, 1, 141),
];
const EFFECTS: [GuestCodeEffectAnchor; 4] = [
    effect(0, 0, 47),
    effect(0, 1, 44),
    effect(1, 1, 63),
    effect(1, 2, 64),
];
const READS: [GuestCodeInputAnchor; 2] = [
    GuestCodeInputAnchor {
        block: 0,
        code_address: 53,
        function: 0,
        ordinal: 1,
    },
    GuestCodeInputAnchor {
        block: 5,
        code_address: 94,
        function: 0,
        ordinal: 2,
    },
];
const BRANCH: SourceBranchLanding = SourceBranchLanding {
    after_inputs: 1,
    block: 1,
    false_landing: 126,
    function: 0,
    true_landing: 120,
};

const fn block(
    id: u32,
    start: u32,
    control: u32,
    end: u32,
) -> GuestCodeBlockPlacement {
    GuestCodeBlockPlacement {
        function: 0,
        block: id,
        start,
        end_exclusive: end,
        control_start: control,
    }
}

const fn pad(
    from: u32,
    to: u32,
    start: u32,
    end: u32,
) -> GuestCodeEdgePadPlacement {
    GuestCodeEdgePadPlacement {
        end_exclusive: end,
        function: 0,
        kind: GuestCodeEdgeKind::Jump,
        predecessor: from,
        start,
        successor: to,
    }
}

const fn operation(
    block: u32,
    ordinal: u32,
    code_address: u32,
) -> GuestCodeOperationAnchor {
    GuestCodeOperationAnchor {
        block,
        code_address,
        function: 0,
        ordinal,
    }
}

const fn effect(
    ordinal: u32,
    effect_index: u32,
    code_address: u32,
) -> GuestCodeEffectAnchor {
    GuestCodeEffectAnchor {
        block: 0,
        code_address,
        effect_index,
        function: 0,
        ordinal,
    }
}

fn checksum_wire() -> Result<Vec<u8>, String> {
    let digits = include_str!("typed-ir/golden/mutable-eof-checksum.hex")
        .trim_end()
        .strip_prefix("malbolge-typed-ir-v1:")
        .ok_or("missing original checksum wire prefix")?;
    let (pairs, remainder) = digits.as_bytes().as_chunks::<2>();
    if !remainder.is_empty() {
        return Err("odd original checksum wire digits".into());
    }
    pairs
        .iter()
        .map(|bytes| {
            let hex =
                str::from_utf8(bytes).map_err(|error| error.to_string())?;
            u8::from_str_radix(hex, 16).map_err(|error| error.to_string())
        })
        .collect()
}

fn physical_proof(
    source: &[u8],
) -> Result<AddressSelectedIndirectProof, String> {
    verify_address_selected_indirect_guest(
        current_profile(),
        AddressSelectedIndirectProbe {
            cases: [
                AddressSelectedIndirectCase {
                    input: &[0],
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
            selector_cell: 7_174_423,
            selector_code_cell: 107,
            selector_store_code_cell: 99,
            source,
            step_budget: 136,
        },
    )
    .map_err(|error| format!("paired route {error:?}"))
}

const fn source_probe<'source>(
    canonical: &'source [u8],
    source: &'source [u8],
    input: &'source [u8],
) -> AddressSelectedSourceReturnProbe<'source> {
    AddressSelectedSourceReturnProbe {
        branch: BRANCH,
        effect_anchors: &EFFECTS,
        operation_anchors: &OPERATIONS,
        proposals: PROPOSALS,
        source_input: SourceInputProbe {
            anchors: &READS,
            canonical,
            frame_base: FRAME,
            input,
            physical_source: source,
            step_budget: 136,
        },
    }
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "exact original typed source reservation"
)]
#[test]
fn relocated_source_reservations_match_branch_and_eof_output()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let plan = bind_source_locked_cfg_code_targets_with_effect_anchors(
        &wire,
        156,
        FRAME,
        PROPOSALS,
        &OPERATIONS,
        &EFFECTS,
    )
    .map_err(|error| format!("original source plan: {error:?}"))?;
    assert_eq!(plan.code_blocks, BLOCKS, "seven original source blocks");
    assert_eq!(plan.edge_pads, PADS, "four original phi pads");
    let effects = plan
        .operation_effect_sites
        .iter()
        .filter_map(|site| match site.effect {
            GuestCodeOperationEffect::Store { destination, .. }
                if [44, 47, 63, 64, 140].contains(&site.code_address) =>
            {
                Some((site.code_address, destination))
            },
            GuestCodeOperationEffect::Input { .. }
            | GuestCodeOperationEffect::Output { .. }
            | GuestCodeOperationEffect::Store { .. }
            | GuestCodeOperationEffect::Compute => None,
        })
        .collect::<Vec<_>>();
    assert_eq!(
        effects,
        [
            (44, 7_174_418),
            (47, 7_174_417),
            (63, 7_174_419),
            (64, 7_174_420),
            (140, 7_174_455)
        ],
        "exact source destination reservations"
    );
    assert_output_and_control_reservations(&plan)
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "exact original output and control sites"
)]
fn assert_output_and_control_reservations(
    plan: &GuestAddressedCfgPlan,
) -> Result<(), String> {
    let output = plan
        .operation_effect_sites
        .iter()
        .find(|site| {
            matches!(site.effect, GuestCodeOperationEffect::Output { .. })
        })
        .ok_or("missing source output")?;
    let GuestCodeOperationEffect::Output { source } = output.effect else {
        return Err("wrong source effect".into());
    };
    assert_eq!(
        (
            output.block,
            output.ordinal,
            output.code_address,
            source.address
        ),
        (6, 1, 141, 7_174_455),
        "original checksum output"
    );
    for (kind, landing) in [
        (GuestCodeEdgeKind::WhenTrue, 120),
        (GuestCodeEdgeKind::WhenFalse, 126),
    ] {
        assert!(
            plan.control_edges.iter().any(|edge| {
                edge.predecessor == 1
                    && edge.kind == kind
                    && edge.control_address == 118
                    && edge.entry_address == landing
            }),
            "actual branch entry reservations"
        );
    }
    assert_eq!(
        plan.return_sites.first().map(|site| site.address),
        Some(142),
        "EOF halt reservation"
    );
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "exact source-bound I/O and omitted byte arm"
)]
#[test]
fn relocated_eof_source_return_io_passes_but_byte_arm_refuses()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let guest = build_relocated_eof_branch_source(current_profile())
        .map_err(|error| format!("{error:?}"))?;
    let physical = physical_proof(&guest.source)?;
    let probe = source_probe(&wire, &guest.source, &[]);
    let receipt = verify_address_selected_source_return(&physical, &probe)
        .map_err(|error| format!("source EOF return: {error:?}"))?;
    assert_eq!(
        receipt.guest_output,
        [0],
        "real original checksum for empty stdin"
    );
    assert_eq!(receipt.bytes_consumed, 0, "true first EOF");
    let [input] = receipt.observations.as_slice() else {
        return Err("missing first source read".into());
    };
    assert_eq!(
        (
            input.block,
            input.ordinal,
            input.code_address,
            input.input,
            input.trace_index
        ),
        (0, 1, 53, TraceInput::EndOfInput, 53),
        "exact first C23 getchar"
    );
    let [output] = receipt.output_sites.as_slice() else {
        return Err("missing source output".into());
    };
    assert_eq!(
        (
            output.block,
            output.ordinal,
            output.code_address,
            output.byte,
            output.trace_index
        ),
        (6, 1, 141, 0, 134),
        "exact source ByteOutput"
    );
    let byte = source_probe(&wire, &guest.source, &[0]);
    assert_eq!(
        verify_address_selected_source_return(&physical, &byte),
        Err(AddressSelectedSourceReturnError::SourceInput(
            SourceInputTraceError::UnexpectedGuestInput
        )),
        "C120 is the loop-body entry, not the later C23 getchar"
    );
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "source/physical join refusal boundaries"
)]
#[test]
fn relocated_source_join_refuses_forged_control_and_replay()
-> Result<(), String> {
    use AddressSelectedSourceReturnError as Error;
    let wire = checksum_wire()?;
    let guest = build_relocated_eof_branch_source(current_profile())
        .map_err(|error| format!("{error:?}"))?;
    let physical = physical_proof(&guest.source)?;
    let probe = source_probe(&wire, &guest.source, &[]);
    let wrong_direction = SourceBranchLanding {
        false_landing: 120,
        true_landing: 126,
        ..BRANCH
    };
    assert_eq!(
        verify_address_selected_source_return(
            &physical,
            &AddressSelectedSourceReturnProbe {
                branch: wrong_direction,
                ..probe
            }
        ),
        Err(Error::InvalidBinding),
        "a swapped source branch is not a matching reservation"
    );
    assert_eq!(
        verify_address_selected_source_return(
            &physical,
            &AddressSelectedSourceReturnProbe {
                branch: SourceBranchLanding {
                    after_inputs: 0,
                    ..BRANCH
                },
                ..probe
            }
        ),
        Err(Error::InvalidBinding),
        "source conditional must follow the real first read"
    );
    assert_eq!(
        verify_address_selected_source_return(
            &physical,
            &source_probe(&wire, &guest.source, &[255])
        ),
        Err(Error::CaseNotProven),
        "physical proof only covers its own inputs"
    );
    assert_eq!(
        verify_address_selected_source_return(
            &physical,
            &source_probe(&wire, b"oo", &[])
        ),
        Err(Error::CaseNotProven),
        "same source cannot be replaced"
    );
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "exact output and halt reservation refusal"
)]
#[test]
fn relocated_source_join_refuses_other_output_and_halt_sites()
-> Result<(), String> {
    use AddressSelectedSourceReturnError as Error;
    let wire = checksum_wire()?;
    let guest = build_relocated_eof_branch_source(current_profile())
        .map_err(|error| format!("{error:?}"))?;
    let physical = physical_proof(&guest.source)?;
    let probe = source_probe(&wire, &guest.source, &[]);
    let wrong_output = [
        operation(0, 1, 53),
        operation(5, 2, 94),
        operation(6, 0, 139),
        operation(6, 1, 140),
    ];
    assert_eq!(
        verify_address_selected_source_return(
            &physical,
            &AddressSelectedSourceReturnProbe {
                operation_anchors: &wrong_output,
                ..probe
            }
        ),
        Err(Error::SourceInput(
            SourceInputTraceError::UnexpectedGuestOutput
        )),
        "a matching output value cannot borrow a different source effect"
    );
    let mut blocks = BLOCKS;
    let last = blocks.last_mut().ok_or("missing return block")?;
    last.control_start = 143;
    last.end_exclusive = 144;
    let mut pads = PADS;
    let backedge = pads.last_mut().ok_or("missing backedge")?;
    backedge.start = 144;
    backedge.end_exclusive = 153;
    assert_eq!(
        verify_address_selected_source_return(
            &physical,
            &AddressSelectedSourceReturnProbe {
                proposals: GuestCodeProposals {
                    code_blocks: &blocks,
                    edge_pads: &pads
                },
                ..probe
            }
        ),
        Err(Error::InvalidBinding),
        "actual halt cannot borrow a different reserved return"
    );
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "unimplemented source second input cannot occupy loop entry"
)]
#[test]
fn second_source_input_cannot_borrow_loop_entry() -> Result<(), String> {
    let wire = checksum_wire()?;
    let misplaced = [
        operation(0, 1, 53),
        operation(5, 2, 120),
        operation(6, 0, 140),
        operation(6, 1, 141),
    ];
    assert!(
        bind_source_locked_cfg_code_targets_with_effect_anchors(
            &wire, 156, FRAME, PROPOSALS, &misplaced, &EFFECTS,
        )
        .is_err(),
        "C120 belongs to block 2, not block 5's second source getchar"
    );
    Ok(())
}
