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
//   - Real N15 phi-copy value, site, temporal and order regressions.
// - Must-Not:
//   - Treat a seeded low-level guest as a complete source-C CFG compiler.
// - Allows:
//   - Inputs: a bounded, real VM p/j/p/p/halt trace and source-site models.
//   - Outputs: authentic guest observations and explicit forged-plan refusals.
//   - Side effects: local VM execution only.
// - Split-When:
//   - A complete source-locked C phi pad executes on the real VM.
// - Merge-When:
//   - Full source CFG guest checking can reuse the same copy chronology.
// - Summary:
//   - Even equal guest output cannot authenticate a forged phi transfer.

//! A physical guest proves data-copy prerequisites, not source CFG linkage.

use std::slice::from_ref;

use super::super::typed_cfg_adapter::state_relocation::{
    GuestCodeCellCopySite, GuestCodeEdgeKind,
};
use super::*;

fn graphical(site: usize, opcode: u8) -> Result<u8, String> {
    (33..=126u8)
        .find(|byte| {
            malbolge::decode_profile_instruction(
                u32::from(*byte),
                u32::try_from(site).unwrap_or(u32::MAX),
            ) == Some(opcode)
        })
        .ok_or_else(|| format!("missing graphical opcode at {site}"))
}

// An actual 5-step N15 guest: source p at C0 writes M70, j at C1
// switches D to M101, and p at C2/C3 writes identical M101/M102 words.
// The all-2-trit A word and all-1-trit data are a crazy fixed point. A
// forged source phi claim must still fail despite identical real words.
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "five checked, fixed-position real VM steps"
)]
fn guest_trace_with_snapshot_seed(
    snapshot_seed: u32,
) -> Result<Vec<ProfileStepTrace>, String> {
    let mut source = (0..59)
        .map(|position| graphical(position, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    for (site, opcode) in
        [(0, b'p'), (1, b'j'), (2, b'p'), (3, b'p'), (4, b'v')]
    {
        source[site] = graphical(site, opcode)?;
    }
    let profile = current_profile();
    let initial = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| format!("initial guest: {error:?}"))?;
    let mut memory = initial.memory().to_vec();
    let eof = profile.eof_word();
    let all_ones = 7_174_453u32; // Exact N15 all-one-trit word.
    for address in [70usize, 101, 102] {
        *memory.get_mut(address).ok_or("seed absent")? = all_ones;
    }
    *memory.get_mut(71).ok_or("indirect seed absent")? = 100;
    *memory.get_mut(101).ok_or("snapshot seed absent")? = snapshot_seed;
    let registers = malbolge::ProfileRegisters {
        accumulator: eof,
        code_pointer: 0,
        data_pointer: 70,
    };
    let mut machine =
        ProfileMachine::from_state(profile, memory, Vec::new(), registers)
            .map_err(|error| format!("seeded guest: {error:?}"))?;
    let mut steps = Vec::new();
    let outcome = machine
        .run_traced(5, &mut |step| steps.push(*step))
        .map_err(|error| format!("guest execution: {error:?}"))?;
    assert_eq!(outcome, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: 5,
    });
    assert_eq!(steps.iter().map(|step| step.decoded).collect::<Vec<_>>(), [
        Some(b'p'),
        Some(b'j'),
        Some(b'p'),
        Some(b'p'),
        Some(b'v'),
    ]);
    assert_eq!(steps[0].before.registers.data_pointer, 70);
    assert_eq!(steps[2].before.registers.data_pointer, 101);
    assert_eq!(steps[3].before.registers.data_pointer, 102);
    assert_eq!(steps[0].after.registers.accumulator, eof);
    Ok(steps)
}

#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "bounded fixed N15 physical guest witness"
)]
fn guest_trace() -> Result<Vec<ProfileStepTrace>, String> {
    let steps = guest_trace_with_snapshot_seed(7_174_453)?;
    for step in [&steps[2], &steps[3]] {
        assert_eq!(
            step.after.registers.accumulator,
            current_profile().eof_word()
        );
    }
    Ok(steps)
}

fn placed_edge() -> GuestCodeControlEdge {
    let snapshot = GuestPlacedCellCopy {
        destination: 101,
        source: 70,
    };
    let commit = GuestPlacedCellCopy {
        destination: 102,
        source: 101,
    };
    GuestCodeControlEdge {
        commit_sites: vec![GuestCodeCellCopySite {
            code_address: 3,
            copy: commit,
        }],
        commits: vec![commit],
        condition: None,
        control_address: 1,
        entry_address: 2,
        function: 0,
        kind: GuestCodeEdgeKind::Jump,
        pad_exit_address: Some(4),
        predecessor: 0,
        snapshot_sites: vec![GuestCodeCellCopySite {
            code_address: 2,
            copy: snapshot,
        }],
        snapshots: vec![snapshot],
        successor: 1,
        target_address: 5,
    }
}

fn initial_store(literal: Option<u32>) -> GuestCodeOperationEffectSite {
    GuestCodeOperationEffectSite {
        block: 0,
        code_address: 0,
        effect: GuestCodeOperationEffect::Store { destination: 70, literal },
        function: 0,
        ordinal: 0,
    }
}

fn frames() -> [GuestFramePlacement; 1] {
    [GuestFramePlacement {
        base: 70,
        end_exclusive: 103,
        source_cells: 59,
    }]
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "one exhaustive real VM proof and negative-control matrix"
)]
fn real_guest_phi_copies_require_exact_source_words() -> Result<(), String> {
    let steps = guest_trace()?;
    let edge = placed_edge();
    let expected = current_profile().eof_word();
    let proof = verify_traced_phi_copies(
        from_ref(&edge),
        &[initial_store(None)],
        &frames(),
        &steps,
    )
    .map_err(|error| format!("physical source copying: {error:?}"))?;
    assert_eq!(proof.completed_pads, 1);
    assert_eq!(proof.copies, vec![
        SourcePhiCopyObservation {
            code_address: 2,
            destination: 101,
            source: 70,
            trace_index: 2,
            word: expected,
        },
        SourcePhiCopyObservation {
            code_address: 3,
            destination: 102,
            source: 101,
            trace_index: 3,
            word: expected,
        },
    ]);
    // The word happened to match the loader value, but no earlier source
    // write to M71 occurred: physical coincidence cannot source a phi copy.
    let mut wrong_source = edge.clone();
    wrong_source.snapshot_sites[0].copy.source = 71;
    assert_eq!(
        verify_traced_phi_copies(
            &[wrong_source],
            &[initial_store(None)],
            &frames(),
            &steps,
        ),
        Err(SourcePhiCopyTraceError::MissingSourceMaterialization),
    );
    // A forged output-equivalent source claims M101 copied a different word.
    let mut wrong_value = edge.clone();
    wrong_value.snapshot_sites[0].copy.source = 102;
    assert_eq!(
        verify_traced_phi_copies(
            &[wrong_value],
            &[initial_store(None)],
            &frames(),
            &steps,
        ),
        Err(SourcePhiCopyTraceError::MissingSourceMaterialization),
    );
    // A different *actual guest memory seed* still follows the same 5
    // instructions, but its snapshot p result differs from the prior
    // materialized M70 word. Equal source site and correct order are not
    // sufficient to authenticate a real phi value transfer.
    let changed_steps = guest_trace_with_snapshot_seed(0)?;
    assert_ne!(changed_steps[2].after.registers.accumulator, expected,);
    assert_eq!(
        verify_traced_phi_copies(
            from_ref(&edge),
            &[initial_store(None)],
            &frames(),
            &changed_steps,
        ),
        Err(SourcePhiCopyTraceError::InvalidPhiCopy),
    );
    // Replacing the true write with a source-invalid constant is not valid.
    assert_eq!(
        verify_traced_phi_copies(
            from_ref(&edge),
            &[initial_store(Some(expected - 1))],
            &frames(),
            &steps,
        ),
        Err(SourcePhiCopyTraceError::UnexpectedFrameEffect),
    );
    assert_eq!(
        verify_traced_phi_copies(&[edge], &[], &frames(), &steps),
        Err(SourcePhiCopyTraceError::UnexpectedFrameEffect),
    );
    Ok(())
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "physical phi source and step-order negatives"
)]
fn physical_phi_copy_rejects_reordered_missing_and_foreign_sites()
-> Result<(), String> {
    let steps = guest_trace()?;
    let edge = placed_edge();
    let mut wrong_site = edge.clone();
    wrong_site.snapshot_sites[0].code_address = 1;
    assert_eq!(
        verify_traced_phi_copies(
            &[wrong_site],
            &[initial_store(None)],
            &frames(),
            &steps,
        ),
        Err(SourcePhiCopyTraceError::InvalidPhiCopy),
    );
    let mut wrong_destination = edge.clone();
    wrong_destination.commit_sites[0].copy.destination = 103;
    assert_eq!(
        verify_traced_phi_copies(
            &[wrong_destination],
            &[initial_store(None)],
            &frames(),
            &steps,
        ),
        Err(SourcePhiCopyTraceError::InvalidPhiCopy),
    );
    let mut reverse = edge.clone();
    reverse.snapshot_sites[0].code_address = 3;
    reverse.commit_sites[0].code_address = 2;
    assert_eq!(
        verify_traced_phi_copies(
            &[reverse],
            &[initial_store(None)],
            &frames(),
            &steps,
        ),
        Err(SourcePhiCopyTraceError::InvalidPhiOrder),
    );
    assert_eq!(
        verify_traced_phi_copies(
            from_ref(&edge),
            &[initial_store(None)],
            &frames(),
            &steps[..3],
        ),
        Err(SourcePhiCopyTraceError::InvalidPhiOrder),
    );
    assert_eq!(
        verify_traced_phi_copies(
            &[],
            &[initial_store(None)],
            &frames(),
            &steps,
        ),
        Err(SourcePhiCopyTraceError::UnexpectedFrameEffect),
    );
    let no_frame: [GuestFramePlacement; 0] = [];
    assert_eq!(
        verify_traced_phi_copies(&[], &[], &no_frame, &steps),
        Err(SourcePhiCopyTraceError::NoReachedPhiCopy),
    );
    Ok(())
}

#[test]
fn phi_guest_public_gate_refuses_unlinked_or_unbounded_source() {
    let physical =
        b"DCBA@?>=<;:98hx/v-210/p-K+*)ji&%$#\"!~}|{zyxwvutsrqponmlkjihgs%H";
    let proposals = GuestCodeProposals {
        code_blocks: &[],
        edge_pads: &[],
    };
    let probe = SourcePhiCopyProbe {
        canonical: &[],
        effect_anchors: &[],
        frame_base: 73,
        input: &[],
        operation_anchors: &[],
        physical_source: physical,
        proposals,
        step_budget: 0,
    };
    assert_eq!(probe.verify(), Err(SourcePhiCopyTraceError::InvalidBound));
    assert_eq!(
        SourcePhiCopyProbe { step_budget: 60, ..probe }.verify(),
        Err(SourcePhiCopyTraceError::InvalidSourcePlacement),
    );
    assert_eq!(
        SourcePhiCopyProbe {
            physical_source: b"n\n\n",
            step_budget: 60,
            ..probe
        }
        .verify(),
        Err(SourcePhiCopyTraceError::InvalidBound),
    );
}

// Two source-placed p writes materialize both guest words required
// by a signed C23 scalar. A real j follows, then two snapshot p writes and two
// commit p writes. This forces the phi implementation to preserve both
// independent source words before either destination is committed.
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "exact bounded eight-step VM trace and N15 frame offsets"
)]
fn two_word_guest_trace(
    high_snapshot_seed: u32,
) -> Result<Vec<ProfileStepTrace>, String> {
    let mut source = (0..59)
        .map(|site| graphical(site, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    for (site, opcode) in [
        (0, b'p'),
        (1, b'p'),
        (2, b'j'),
        (3, b'p'),
        (4, b'p'),
        (5, b'p'),
        (6, b'p'),
        (7, b'v'),
    ] {
        source[site] = graphical(site, opcode)?;
    }
    let profile = current_profile();
    let loader = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| format!("source loader: {error:?}"))?;
    let mut memory = loader.memory().to_vec();
    for address in [70usize, 71, 101, 102, 103, 104] {
        *memory.get_mut(address).ok_or("seed cell absent")? = 7_174_453;
    }
    *memory.get_mut(72).ok_or("jump cell absent")? = 100;
    *memory.get_mut(102).ok_or("high snapshot absent")? = high_snapshot_seed;
    let registers = malbolge::ProfileRegisters {
        accumulator: profile.eof_word(),
        code_pointer: 0,
        data_pointer: 70,
    };
    let mut machine =
        ProfileMachine::from_state(profile, memory, Vec::new(), registers)
            .map_err(|error| format!("seeded VM: {error:?}"))?;
    let mut steps = Vec::new();
    let outcome = machine
        .run_traced(8, &mut |step| steps.push(*step))
        .map_err(|error| format!("guest replay: {error:?}"))?;
    assert_eq!(outcome, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: 8,
    });
    assert_eq!(steps.iter().map(|step| step.decoded).collect::<Vec<_>>(), [
        Some(b'p'),
        Some(b'p'),
        Some(b'j'),
        Some(b'p'),
        Some(b'p'),
        Some(b'p'),
        Some(b'p'),
        Some(b'v'),
    ]);
    for (index, address) in
        [(0, 70), (1, 71), (3, 101), (4, 102), (5, 103), (6, 104)]
    {
        assert_eq!(steps[index].before.registers.data_pointer, address);
    }
    Ok(steps)
}

fn two_word_phi_edge() -> GuestCodeControlEdge {
    let mut edge = placed_edge();
    let snapshots = [
        GuestPlacedCellCopy {
            destination: 101,
            source: 70,
        },
        GuestPlacedCellCopy {
            destination: 102,
            source: 71,
        },
    ];
    let commits = [
        GuestPlacedCellCopy {
            destination: 103,
            source: 101,
        },
        GuestPlacedCellCopy {
            destination: 104,
            source: 102,
        },
    ];
    edge.snapshot_sites = snapshots
        .iter()
        .enumerate()
        .map(|(index, copy)| GuestCodeCellCopySite {
            code_address: u32::try_from(index)
                .unwrap_or(u32::MAX)
                .saturating_add(3),
            copy: *copy,
        })
        .collect();
    edge.commit_sites = commits
        .iter()
        .enumerate()
        .map(|(index, copy)| GuestCodeCellCopySite {
            code_address: u32::try_from(index)
                .unwrap_or(u32::MAX)
                .saturating_add(5),
            copy: *copy,
        })
        .collect();
    edge.snapshots = snapshots.to_vec();
    edge.commits = commits.to_vec();
    edge.control_address = 2;
    edge.entry_address = 3;
    edge.pad_exit_address = Some(7);
    edge.target_address = 8;
    edge
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "two-word physical guest transfer and high-word forgery checks"
)]
fn real_guest_two_word_phi_snapshot_and_commit() -> Result<(), String> {
    let expected = current_profile().eof_word();
    let good = two_word_guest_trace(7_174_453)?;
    let edge = two_word_phi_edge();
    let stores = [initial_store(None), GuestCodeOperationEffectSite {
        code_address: 1,
        effect: GuestCodeOperationEffect::Store {
            destination: 71,
            literal: None,
        },
        ..initial_store(None)
    }];
    let proof =
        verify_traced_phi_copies(from_ref(&edge), &stores, &frames(), &good)
            .map_err(|error| format!("physical two-word copy: {error:?}"))?;
    assert_eq!(proof.completed_pads, 1);
    assert_eq!(proof.copies.len(), 4);
    assert_eq!(
        proof
            .copies
            .iter()
            .map(|copy| copy.code_address)
            .collect::<Vec<_>>(),
        [3, 4, 5, 6]
    );
    assert_eq!(
        proof
            .copies
            .iter()
            .map(|copy| copy.word)
            .collect::<Vec<_>>(),
        [expected; 4]
    );
    // Real incorrect high snapshot retains a valid low word, source order
    // and identical source CFG but must not authenticate the high-word phi.
    let wrong_high = two_word_guest_trace(0)?;
    assert_eq!(wrong_high[3].after.registers.accumulator, expected);
    assert_ne!(wrong_high[4].after.registers.accumulator, expected);
    assert_eq!(
        verify_traced_phi_copies(
            from_ref(&edge),
            &stores,
            &frames(),
            &wrong_high
        ),
        Err(SourcePhiCopyTraceError::InvalidPhiCopy),
    );
    let mut swapped = edge.clone();
    swapped.snapshot_sites.swap(0, 1);
    assert_eq!(
        verify_traced_phi_copies(from_ref(&swapped), &stores, &frames(), &good),
        Err(SourcePhiCopyTraceError::InvalidPhiOrder),
    );
    assert_eq!(
        verify_traced_phi_copies(
            from_ref(&edge),
            &stores,
            &frames(),
            &good[..6]
        ),
        Err(SourcePhiCopyTraceError::InvalidPhiOrder),
    );
    Ok(())
}
