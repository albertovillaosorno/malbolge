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
    GuestCodeCellCopySite, GuestCodeInputSemantics, GuestPlacedOperand,
};
use super::*;

type LinkedPhiState = (GuestCodeControlEdge, [GuestFramePlacement; 1]);
type PhysicalTwoPadLayout =
    ([GuestCodeControlEdge; 2], [GuestCodeBlockPlacement; 3]);

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

// A real six-step current-N15 guest inserts a physical `j` between
// snapshot and commit. It routes D from M102 to the distant M120, rather
// than the adjacent M103. A forged p in the same gap performs an
// unauthorized real frame write regardless of final output.
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "one fixed finite physical guest trace"
)]
fn guest_phi_trace_with_setup(
    gap_opcode: u8,
    gap_word: u32,
) -> Result<Vec<ProfileStepTrace>, String> {
    let mut source = (0..59)
        .map(|site| graphical(site, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    for (site, opcode) in [
        (0, b'p'),
        (1, b'j'),
        (2, b'p'),
        (3, gap_opcode),
        (4, b'p'),
        (5, b'v'),
    ] {
        source[site] = graphical(site, opcode)?;
    }
    let profile = current_profile();
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| format!("loaded guest: {error:?}"))?;
    let mut memory = loaded.memory().to_vec();
    for address in [70usize, 101, 103, 120] {
        *memory.get_mut(address).ok_or("missing frame seed")? = 7_174_453;
    }
    *memory.get_mut(71).ok_or("missing jump seed")? = 100;
    *memory.get_mut(102).ok_or("missing pointer route")? = gap_word;
    let registers = malbolge::ProfileRegisters {
        accumulator: profile.eof_word(),
        code_pointer: 0,
        data_pointer: 70,
    };
    let mut machine =
        ProfileMachine::from_state(profile, memory, Vec::new(), registers)
            .map_err(|error| format!("physical guest state: {error:?}"))?;
    let mut steps = Vec::new();
    let outcome = machine
        .run_traced(6, &mut |step| steps.push(*step))
        .map_err(|error| format!("physical guest execution: {error:?}"))?;
    let escaped = gap_opcode == b'i';
    assert_eq!(outcome, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: if escaped {
            5
        } else {
            6
        },
    });
    let actual = steps.iter().map(|step| step.decoded).collect::<Vec<_>>();
    let mut expected =
        vec![Some(b'p'), Some(b'j'), Some(b'p'), Some(gap_opcode)];
    expected.extend((!escaped).then_some(Some(b'p')));
    expected.push(Some(b'v'));
    assert_eq!(actual, expected);
    assert_eq!(steps[2].before.registers.data_pointer, 101);
    assert_eq!(steps[3].before.registers.data_pointer, 102);
    if gap_opcode == b'j' {
        assert_eq!(steps[4].before.registers.data_pointer, 120);
    }
    Ok(steps)
}

#[test]
fn real_guest_sparse_phi_pad_allows_setup_but_not_foreign_frame_writes()
-> Result<(), String> {
    let good = guest_phi_trace_with_setup(b'j', 119)?;
    let mut edge = placed_edge();
    edge.entry_address = 2;
    let commit = edge.commit_sites.first_mut().ok_or("missing commit")?;
    commit.code_address = 4;
    commit.copy.destination = 120;
    edge.commits.first_mut().ok_or("missing copy")?.destination = 120;
    edge.pad_exit_address = Some(5);
    edge.target_address = 6;
    let [first] = frames();
    let frame = [GuestFramePlacement {
        end_exclusive: 121,
        ..first
    }];
    let proof = verify_traced_phi_copies(
        from_ref(&edge),
        &[initial_store(None)],
        &frame,
        &good,
    )
    .map_err(|error| format!("sparse phi guest: {error:?}"))?;
    if proof.completed_pads != 1
        || !matches!(proof.copies.as_slice(), [snapshot, observed_commit]
            if snapshot.trace_index == 2
                && observed_commit.trace_index == 4
                && observed_commit.destination == 120)
    {
        return Err(format!("incorrect sparse phi proof: {proof:?}"));
    }
    let forged = guest_phi_trace_with_setup(b'p', 119)?;
    if verify_traced_phi_copies(
        from_ref(&edge),
        &[initial_store(None)],
        &frame,
        &forged,
    ) != Err(SourcePhiCopyTraceError::UnexpectedFrameEffect)
    {
        return Err("off-site guest frame write must refuse".into());
    }
    let mut wrong_site = edge;
    wrong_site
        .commit_sites
        .first_mut()
        .ok_or("missing commit")?
        .code_address = 3;
    if verify_traced_phi_copies(
        &[wrong_site],
        &[initial_store(None)],
        &frame,
        &good,
    ) != Err(SourcePhiCopyTraceError::InvalidPhiCopy)
    {
        return Err("wrong-site guest phi copy must refuse".into());
    }
    Ok(())
}

// The first sparse copy at C2 is valid, but the next instruction must not
// write even an unchanged frame word or jump out before the final commit.
#[test]
fn real_guest_sparse_phi_gap_rejects_idempotent_effect_and_escape()
-> Result<(), String> {
    // For the all-two-trit EOF accumulator, crazy(0, EOF) == 0:
    // this is a physical p write which does not produce a changed-cell delta.
    let stable_word = 0u32;
    let idempotent = guest_phi_trace_with_setup(b'p', stable_word)?;
    let step = idempotent.get(3).ok_or("missing real gap instruction")?;
    if step.decoded != Some(b'p')
        || !step.memory_reads.data.is_some_and(|read| {
            (read.address, read.value) == (102, stable_word)
        })
        || step.after.registers.accumulator != stable_word
        || step.memory_delta.data.is_some()
    {
        return Err(format!("expected actual unchanged physical p: {step:?}"));
    }
    let mut edge = placed_edge();
    edge.entry_address = 2;
    let commit = edge.commit_sites.first_mut().ok_or("missing commit")?;
    commit.code_address = 4;
    commit.copy.destination = 120;
    edge.commits.first_mut().ok_or("missing copy")?.destination = 120;
    edge.pad_exit_address = Some(5);
    edge.target_address = 6;
    let [first] = frames();
    let frame = [GuestFramePlacement {
        end_exclusive: 121,
        ..first
    }];
    if verify_traced_phi_copies(
        from_ref(&edge),
        &[initial_store(None)],
        &frame,
        &idempotent,
    ) != Err(SourcePhiCopyTraceError::UnexpectedFrameEffect)
    {
        return Err("idempotent foreign p in phi gap must refuse".into());
    }

    // At C3 a real `i` reads M102=4, jumps directly to the halt at C5
    // and skips the required C4 commit; output and termination alone must
    // not turn a partial phi copy into a complete authenticated pad.
    let escaped = guest_phi_trace_with_setup(b'i', 4)?;
    if !matches!(escaped.last(), Some(halt)
        if halt.before.registers.code_pointer == 5
            && halt.decoded == Some(b'v'))
    {
        return Err("physical jump did not escape the phi pad".into());
    }
    if verify_traced_phi_copies(
        from_ref(&edge),
        &[initial_store(None)],
        &frame,
        &escaped,
    ) != Err(SourcePhiCopyTraceError::InvalidPhiOrder)
    {
        return Err("guest escape before final phi commit must refuse".into());
    }
    Ok(())
}

// A real N15 pad executes p / j / p / j / p / i before landing on the
// successor halt. The indirect successor jump is observable as C5 -> C8;
// copying the correct words without this final transfer is insufficient.
#[expect(
    clippy::indexing_slicing,
    reason = "fixed graphical guest code sites"
)]
fn guest_phi_source_with_successor_at(
    exit_address: u32,
    exit_opcode: u8,
) -> Result<Vec<u8>, String> {
    let mut source = (0..59)
        .map(|position| graphical(position, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    for (site, opcode) in [
        (0, b'p'),
        (1, b'j'),
        (2, b'p'),
        (3, b'j'),
        (4, b'p'),
        (
            5,
            if exit_address == 5 {
                exit_opcode
            } else {
                b'o'
            },
        ),
        (
            6,
            if exit_address == 6 {
                exit_opcode
            } else {
                b'v'
            },
        ),
        (7, b'v'),
        (8, b'v'),
        (9, b'v'),
    ] {
        source[site] = graphical(site, opcode)?;
    }
    Ok(source)
}

#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "fixed seeded real guest trace and normative pointer assertions"
)]
fn guest_phi_trace_with_successor_at(
    exit_address: u32,
    exit_opcode: u8,
    jump_operand: u32,
) -> Result<Vec<ProfileStepTrace>, String> {
    let source = guest_phi_source_with_successor_at(exit_address, exit_opcode)?;
    let profile = current_profile();
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| format!("source-loaded phi guest: {error:?}"))?;
    let mut memory = loaded.memory().to_vec();
    for address in [70usize, 101, 120] {
        *memory.get_mut(address).ok_or("missing copy frame")? = 7_174_453;
    }
    *memory.get_mut(71).ok_or("missing first pointer seed")? = 100;
    *memory.get_mut(102).ok_or("missing second pointer seed")? = 119;
    let pointer_cell = usize::try_from(exit_address)
        .ok()
        .and_then(|offset| offset.checked_add(116))
        .ok_or("invalid successor pointer")?;
    *memory
        .get_mut(pointer_cell)
        .ok_or("missing successor pointer seed")? = jump_operand;
    let mut machine = ProfileMachine::from_state(
        profile,
        memory,
        Vec::new(),
        malbolge::ProfileRegisters {
            accumulator: profile.eof_word(),
            code_pointer: 0,
            data_pointer: 70,
        },
    )
    .map_err(|error| format!("seeded successor guest: {error:?}"))?;
    let mut steps = Vec::new();
    let steps_expected = usize::try_from(exit_address)
        .ok()
        .and_then(|step| step.checked_add(2))
        .ok_or("invalid exit address")?;
    let outcome = machine
        .run_traced(steps_expected, &mut |step| steps.push(*step))
        .map_err(|error| format!("successor guest run: {error:?}"))?;
    assert_eq!(outcome, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: steps_expected,
    });
    assert_eq!(steps[2].before.registers.data_pointer, 101);
    assert_eq!(steps[4].before.registers.data_pointer, 120);
    assert_eq!(steps[5].before.registers.data_pointer, 121);
    Ok(steps)
}

fn guest_phi_trace_with_successor(
    exit_opcode: u8,
    jump_operand: u32,
) -> Result<Vec<ProfileStepTrace>, String> {
    guest_phi_trace_with_successor_at(5, exit_opcode, jump_operand)
}

fn linked_phi_edge() -> Result<LinkedPhiState, String> {
    let mut edge = placed_edge();
    let commit = edge.commit_sites.first_mut().ok_or("missing commit site")?;
    commit.code_address = 4;
    commit.copy.destination = 120;
    edge.commits
        .first_mut()
        .ok_or("missing phi commit")?
        .destination = 120;
    edge.pad_exit_address = Some(5);
    edge.target_address = 8;
    let [first] = frames();
    Ok((edge, [GuestFramePlacement {
        end_exclusive: 121,
        ..first
    }]))
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "fixed normative VM successor instruction assertions"
)]
fn real_guest_phi_exit_reaches_source_successor() -> Result<(), String> {
    let good = guest_phi_trace_with_successor(b'i', 7)?;
    let (edge, frame) = linked_phi_edge()?;
    assert_eq!(good.iter().map(|step| step.decoded).collect::<Vec<_>>(), [
        Some(b'p'),
        Some(b'j'),
        Some(b'p'),
        Some(b'j'),
        Some(b'p'),
        Some(b'i'),
        Some(b'v'),
    ]);
    let jump = good.get(5).ok_or("missing phi successor jump")?;
    let successor = good.get(6).ok_or("missing successor instruction")?;
    assert_eq!(jump.before.registers.code_pointer, 5);
    assert_eq!(jump.after.registers.code_pointer, 8);
    assert_eq!(successor.before.registers.code_pointer, 8);
    let proof = verify_traced_phi_copies_with_transfer_policy(
        PhiTraceContext {
            edges: from_ref(&edge),
            effects: &[initial_store(None)],
            frames: &frame,
        },
        &good,
        true,
    )
    .map_err(|error| format!("physical phi jump: {error:?}"))?;
    assert_eq!(proof.completed_pads, 1);
    assert_eq!(proof.copies.len(), 2);
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "bounded guest negative controls assert exact typed refusals"
)]
fn real_guest_phi_exit_refuses_unlinked_continuations() -> Result<(), String> {
    let good = guest_phi_trace_with_successor(b'i', 7)?;
    let no_jump = guest_phi_trace_with_successor(b'o', 7)?;
    let (edge, frame) = linked_phi_edge()?;
    // Physical copy values remain correct in the no-jump negative control.
    assert!(
        verify_traced_phi_copies(
            from_ref(&edge),
            &[initial_store(None)],
            &frame,
            &no_jump,
        )
        .is_ok(),
        "the unchanged copy-only gate should admit equal writes"
    );
    let incomplete = good.get(..5).ok_or("missing complete copied prefix")?;
    for steps in [no_jump.as_slice(), incomplete] {
        assert_eq!(
            verify_traced_phi_copies_with_transfer_policy(
                PhiTraceContext {
                    edges: from_ref(&edge),
                    effects: &[initial_store(None)],
                    frames: &frame,
                },
                steps,
                true,
            ),
            Err(SourcePhiCopyTraceError::InvalidPhiTransfer),
        );
    }
    let wrong_successor = guest_phi_trace_with_successor(b'i', 8)?;
    let jump = wrong_successor.get(5).ok_or("missing wrong jump")?;
    assert_eq!(jump.after.registers.code_pointer, 9);
    assert_eq!(
        verify_traced_phi_copies_with_transfer_policy(
            PhiTraceContext {
                edges: from_ref(&edge),
                effects: &[initial_store(None)],
                frames: &frame,
            },
            &wrong_successor,
            true,
        ),
        Err(SourcePhiCopyTraceError::InvalidPhiTransfer),
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real bounded successor jump and early-exit negative controls"
)]
fn real_guest_phi_transfer_allows_post_commit_setup() -> Result<(), String> {
    let good = guest_phi_trace_with_successor_at(6, b'i', 7)?;
    let (mut edge, frame) = linked_phi_edge()?;
    edge.pad_exit_address = Some(6);
    let setup = good.get(5).ok_or("missing post-commit setup")?;
    let jump = good.get(6).ok_or("missing reserved successor exit")?;
    assert_eq!(setup.decoded, Some(b'o'));
    assert_eq!(jump.decoded, Some(b'i'));
    assert_eq!(jump.before.registers.code_pointer, 6);
    assert_eq!(jump.after.registers.code_pointer, 8);
    let check = |steps: &[ProfileStepTrace]| {
        verify_traced_phi_copies_with_transfer_policy(
            PhiTraceContext {
                edges: from_ref(&edge),
                effects: &[initial_store(None)],
                frames: &frame,
            },
            steps,
            true,
        )
    };
    let proof = check(&good)
        .map_err(|error| format!("post-commit setup: {error:?}"))?;
    assert_eq!(proof.completed_pads, 1);
    // Exact writes followed by a jump one cell too early do not prove the
    // source-reserved exit, even when the target block is otherwise right.
    let early = guest_phi_trace_with_successor_at(5, b'i', 7)?;
    assert_eq!(
        check(&early),
        Err(SourcePhiCopyTraceError::InvalidPhiTransfer),
    );
    let missing = guest_phi_trace_with_successor_at(6, b'o', 7)?;
    assert_eq!(
        check(&missing),
        Err(SourcePhiCopyTraceError::InvalidPhiTransfer),
    );
    Ok(())
}

// The same real source-loaded N15 guest can complete every phi copy and its
// reserved successor jump without proving where the phi pad was entered.
// Physical ingress must come from the source-identified predecessor's control
// interval, not an arbitrary earlier instruction or a foreign jump.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "source-bound real VM ingress/refusal assertions"
)]
fn real_guest_phi_entry_requires_own_predecessor_control() -> Result<(), String>
{
    let steps = guest_phi_trace_with_successor(b'i', 7)?;
    let (edge, frame) = linked_phi_edge()?;
    let blocks = [GuestCodeBlockPlacement {
        function: 0,
        block: 0,
        start: 0,
        end_exclusive: 2,
        control_start: 1,
    }];
    // All predecessor, copy and exit addresses come from the actual trace.
    let proof = verify_traced_phi_copies_with_transfer_policy(
        PhiTraceContext {
            edges: from_ref(&edge),
            effects: &[initial_store(None)],
            frames: &frame,
        },
        &steps,
        true,
    )
    .map_err(|error| format!("source phi exit: {error:?}"))?;
    assert_eq!(proof.completed_pads, 1);
    assert_eq!(
        verify_predecessor_phi_entries(&blocks, from_ref(&edge), &steps),
        Ok(())
    );

    // Correct physical copies and C5 -> C8 exit cannot make an instruction
    // outside the declared predecessor's control suffix into a CFG transfer.
    let foreign_control = [GuestCodeBlockPlacement {
        end_exclusive: 1,
        control_start: 0,
        ..blocks[0]
    }];
    assert_eq!(
        verify_predecessor_phi_entries(
            &foreign_control,
            from_ref(&edge),
            &steps
        ),
        Err(SourcePhiCopyTraceError::InvalidPhiEntry),
    );
    // An unexpected direct landing in the middle of this pad is never
    // justified by correctly executed writes after the landing.
    let middle = steps.get(3..).ok_or("missing guest suffix")?;
    assert_eq!(
        verify_predecessor_phi_entries(&blocks, from_ref(&edge), middle),
        Err(SourcePhiCopyTraceError::InvalidPhiEntry),
    );
    Ok(())
}

// Two complete, real N15 guest runs perform identical frame stores and phi
// snapshots/commits, but only one reaches the phi pad from its reserved
// predecessor control C2. The other uses an actual C1 `i` to skip C2. The
// two traces retain the same real C3 pointer route and C4/C6 frame effects.
#[expect(
    clippy::indexing_slicing,
    reason = "bounded graphical source sites are checked before indexing"
)]
fn guest_phi_source_with_predecessor_bypass(
    bypass: bool,
) -> Result<Vec<u8>, String> {
    let mut source = (0..59)
        .map(|site| graphical(site, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    for (site, opcode) in [
        (0, graphical(0, b'p')?),
        (
            1,
            graphical(
                1,
                if bypass {
                    b'i'
                } else {
                    b'o'
                },
            )?,
        ),
        (2, graphical(2, b'o')?),
        (3, graphical(3, b'j')?),
        (4, graphical(4, b'p')?),
        (5, graphical(5, b'j')?),
        (6, graphical(6, b'p')?),
        (7, graphical(7, b'i')?),
        (10, graphical(10, b'v')?),
    ] {
        source[site] = opcode;
    }
    Ok(source)
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "bounded actual N15 execution and exact control flow assertions"
)]
fn guest_phi_trace_with_predecessor_bypass(
    bypass: bool,
) -> Result<Vec<ProfileStepTrace>, String> {
    let source = guest_phi_source_with_predecessor_bypass(bypass)?;
    let profile = current_profile();
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| format!("loader: {error:?}"))?;
    let mut memory = loaded.memory().to_vec();
    for address in [70usize, 101, 120] {
        *memory.get_mut(address).ok_or("missing frame seed")? = 7_174_453;
    }
    for (address, value) in
        [(71, 2), (72, 100), (73, 100), (102, 119), (121, 9)]
    {
        *memory.get_mut(address).ok_or("missing control seed")? = value;
    }
    let mut machine = ProfileMachine::from_state(
        profile,
        memory,
        Vec::new(),
        malbolge::ProfileRegisters {
            accumulator: profile.eof_word(),
            code_pointer: 0,
            data_pointer: 70,
        },
    )
    .map_err(|error| format!("guest setup: {error:?}"))?;
    let mut steps = Vec::new();
    let outcome = machine
        .run_traced(12, &mut |step| steps.push(*step))
        .map_err(|error| format!("guest trace: {error:?}"))?;
    assert_eq!(outcome, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: if bypass {
            8
        } else {
            9
        },
    });
    assert_eq!(
        steps
            .iter()
            .map(|step| step.before.registers.code_pointer)
            .collect::<Vec<_>>(),
        if bypass {
            vec![0, 1, 3, 4, 5, 6, 7, 10]
        } else {
            vec![0, 1, 2, 3, 4, 5, 6, 7, 10]
        }
    );
    assert_eq!(
        steps
            .iter()
            .find(|step| step.before.registers.code_pointer == 3)
            .and_then(|step| step.decoded),
        Some(b'j')
    );
    Ok(steps)
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "paired real VM transfer and refusal assertions"
)]
fn real_guest_foreign_predecessor_jump_cannot_authorize_phi_pad()
-> Result<(), String> {
    let good = guest_phi_trace_with_predecessor_bypass(false)?;
    let bypass = guest_phi_trace_with_predecessor_bypass(true)?;
    let (mut edge, frame) = linked_phi_edge()?;
    edge.control_address = 2;
    edge.entry_address = 3;
    edge.snapshot_sites
        .first_mut()
        .ok_or("snapshot")?
        .code_address = 4;
    edge.commit_sites.first_mut().ok_or("commit")?.code_address = 6;
    edge.pad_exit_address = Some(7);
    edge.target_address = 10;
    let blocks = [GuestCodeBlockPlacement {
        function: 0,
        block: 0,
        start: 0,
        end_exclusive: 3,
        control_start: 2,
    }];
    for steps in [&good, &bypass] {
        let proof = verify_traced_phi_copies_with_transfer_policy(
            PhiTraceContext {
                edges: from_ref(&edge),
                effects: &[initial_store(None)],
                frames: &frame,
            },
            steps,
            true,
        )
        .map_err(|error| format!("source copy/successor: {error:?}"))?;
        assert_eq!(proof.completed_pads, 1);
        assert_eq!(proof.copies.len(), 2);
    }
    assert_eq!(
        verify_predecessor_phi_entries(&blocks, from_ref(&edge), &good),
        Ok(())
    );
    assert_eq!(
        verify_predecessor_phi_entries(&blocks, from_ref(&edge), &bypass),
        Err(SourcePhiCopyTraceError::InvalidPhiEntry),
    );
    Ok(())
}

// A source control exit must land at the exact bound successor, whether the
// predecessor targets an edge-local phi pad or a phi-free successor block.
// Source-block exit admission is separate from source branch truth, which
// still requires later guest arithmetic and condition verification.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real guest source edge and negative target assertions"
)]
fn real_guest_source_block_exits_refuse_early_and_wrong_targets()
-> Result<(), String> {
    let good = guest_phi_trace_with_predecessor_bypass(false)?;
    let bypass = guest_phi_trace_with_predecessor_bypass(true)?;
    let mut phi = linked_phi_edge()?.0;
    phi.control_address = 2;
    phi.entry_address = 3;
    let blocks = [GuestCodeBlockPlacement {
        function: 0,
        block: 0,
        start: 0,
        end_exclusive: 3,
        control_start: 2,
    }];
    assert_eq!(
        verify_source_block_exits(&blocks, from_ref(&phi), &good),
        Ok(())
    );
    assert_eq!(
        verify_source_block_exits(&blocks, from_ref(&phi), &bypass),
        Err(SourcePhiCopyTraceError::InvalidControlTransfer),
    );
    phi.entry_address = 4;
    assert_eq!(
        verify_source_block_exits(&blocks, from_ref(&phi), &good),
        Err(SourcePhiCopyTraceError::InvalidControlTransfer),
    );

    // The real five-step guest has an adjacent phi-free C1 -> C2 source
    // edge. A matching output or return would not authenticate C1 -> C3.
    let compact = guest_trace()?;
    let block = [GuestCodeBlockPlacement {
        function: 0,
        block: 0,
        start: 0,
        end_exclusive: 2,
        control_start: 1,
    }];
    let mut direct = placed_edge();
    direct.control_address = 1;
    direct.entry_address = 2;
    direct.pad_exit_address = None;
    assert_eq!(
        verify_source_block_exits(&block, from_ref(&direct), &compact),
        Ok(())
    );
    direct.entry_address = 3;
    assert_eq!(
        verify_source_block_exits(&block, from_ref(&direct), &compact),
        Err(SourcePhiCopyTraceError::InvalidControlTransfer),
    );
    Ok(())
}

// A real current-profile guest writes one Boolean by rotating M70, then an
// actual indirect C1 `i` chooses either the false C2 or true C4 source block.
// The pointer is seeded independently: this witnesses *consistency* of the
// reached edge with a prior guest-written Boolean, not implementation of a
// C expression or dependence of the jump target on that Boolean.
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "fixed real VM branch and physical pointer assertions"
)]
fn physical_source_boolean_branch(
    seed: u32,
    destination: u32,
) -> Result<Vec<ProfileStepTrace>, String> {
    let mut source = (0..59)
        .map(|site| graphical(site, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    for (site, opcode) in [(0, b'*'), (1, b'i'), (2, b'v'), (4, b'v')] {
        source[site] = graphical(site, opcode)?;
    }
    let profile = current_profile();
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| format!("Boolean source load: {error:?}"))?;
    let mut memory = loaded.memory().to_vec();
    *memory.get_mut(70).ok_or("missing Boolean SSA cell")? = seed;
    *memory.get_mut(71).ok_or("missing branch pointer cell")? =
        destination.checked_sub(1).ok_or("invalid branch target")?;
    let mut machine = ProfileMachine::from_state(
        profile,
        memory,
        Vec::new(),
        malbolge::ProfileRegisters {
            accumulator: profile.eof_word(),
            code_pointer: 0,
            data_pointer: 70,
        },
    )
    .map_err(|error| format!("physical Boolean branch: {error:?}"))?;
    let mut steps = Vec::new();
    let outcome = machine
        .run_traced(3, &mut |step| steps.push(*step))
        .map_err(|error| format!("Boolean branch run: {error:?}"))?;
    assert_eq!(outcome, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: 3,
    });
    assert_eq!(steps[0].decoded, Some(b'*'));
    assert_eq!(steps[1].decoded, Some(b'i'));
    assert_eq!(steps[2].decoded, Some(b'v'));
    assert_eq!(steps[1].after.registers.code_pointer, destination);
    Ok(steps)
}

fn physical_boolean_edges() -> [GuestCodeControlEdge; 2] {
    let mut false_edge = placed_edge();
    false_edge.snapshot_sites.clear();
    false_edge.commit_sites.clear();
    false_edge.snapshots.clear();
    false_edge.commits.clear();
    false_edge.control_address = 1;
    false_edge.entry_address = 2;
    false_edge.pad_exit_address = None;
    false_edge.target_address = 2;
    false_edge.kind = GuestCodeEdgeKind::WhenFalse;
    false_edge.condition = Some(GuestPlacedOperand {
        address: 70,
        type_kind: TernaryCfgScalarKind::Bool,
        value: 0,
        words: 1,
    });
    let mut true_edge = false_edge.clone();
    true_edge.kind = GuestCodeEdgeKind::WhenTrue;
    true_edge.entry_address = 4;
    true_edge.target_address = 4;
    true_edge.successor = 2;
    [false_edge, true_edge]
}

fn physical_boolean_blocks() -> [GuestCodeBlockPlacement; 3] {
    [
        GuestCodeBlockPlacement {
            function: 0,
            block: 0,
            start: 0,
            end_exclusive: 2,
            control_start: 1,
        },
        GuestCodeBlockPlacement {
            function: 0,
            block: 1,
            start: 2,
            end_exclusive: 3,
            control_start: 2,
        },
        GuestCodeBlockPlacement {
            function: 0,
            block: 2,
            start: 4,
            end_exclusive: 5,
            control_start: 4,
        },
    ]
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "bounded physical Boolean decisions and negative proofs"
)]
fn real_guest_branch_arm_requires_prior_source_boolean_write()
-> Result<(), String> {
    let false_run = physical_source_boolean_branch(0, 2)?;
    let true_run = physical_source_boolean_branch(3, 4)?;
    let edges = physical_boolean_edges();
    let blocks = physical_boolean_blocks();
    let stores = [initial_store(None)];
    let frames = frames();
    for (steps, expected) in [(&false_run, 0), (&true_run, 1)] {
        assert_eq!(steps[0].after.registers.accumulator, expected);
        assert_eq!(verify_source_block_exits(&blocks, &edges, steps), Ok(()));
        assert_eq!(
            verify_source_branch_choices(
                &blocks, &edges, &stores, &frames, steps
            ),
            Ok(())
        );
    }
    // Both mismatches reach source-placed successor blocks through real i
    // instructions, yet neither follows its materialized Boolean arm.
    let false_to_true = physical_source_boolean_branch(0, 4)?;
    let true_to_false = physical_source_boolean_branch(3, 2)?;
    for steps in [&false_to_true, &true_to_false] {
        assert_eq!(verify_source_block_exits(&blocks, &edges, steps), Ok(()));
        assert_eq!(
            verify_source_branch_choices(
                &blocks, &edges, &stores, &frames, steps
            ),
            Err(SourcePhiCopyTraceError::InvalidBranchSelection)
        );
    }
    // A loader-seeded condition cannot authorize a branch without the
    // actual source-placed write, even when the same physical guest wrote it
    // earlier in a prefix omitted from the alleged control-flow proof.
    assert_eq!(
        verify_source_branch_choices(
            &blocks,
            &edges,
            &stores,
            &frames,
            false_run.get(1..).ok_or("missing branch suffix")?,
        ),
        Err(SourcePhiCopyTraceError::MissingBranchCondition)
    );
    let non_boolean = physical_source_boolean_branch(6, 4)?;
    assert_eq!(non_boolean[0].after.registers.accumulator, 2);
    assert_eq!(
        verify_source_branch_choices(
            &blocks,
            &edges,
            &stores,
            &frames,
            &non_boolean
        ),
        Err(SourcePhiCopyTraceError::InvalidBranchSelection)
    );
    assert_eq!(
        verify_source_branch_choices(&blocks, &edges, &[], &frames, &true_run),
        Err(SourcePhiCopyTraceError::UnexpectedFrameEffect)
    );
    Ok(())
}

// Source-locked block ingress is a separate physical proof obligation from
// source-block exit or Boolean arm consistency: an unexplained arrival at a
// successor is not justified by a valid site anywhere else in the trace.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "actual three-/nine-step N15 branch and phi ingress assertions"
)]
fn real_guest_source_block_entries_require_own_predecessors()
-> Result<(), String> {
    let blocks = physical_boolean_blocks();
    let edges = physical_boolean_edges();
    let entry = [GuestCodeFunctionEntry {
        function: 0,
        block: 0,
        address: 0,
    }];
    let false_run = physical_source_boolean_branch(0, 2)?;
    let true_run = physical_source_boolean_branch(3, 4)?;
    for steps in [&false_run, &true_run] {
        assert_eq!(
            verify_source_block_entries(&blocks, &edges, &entry, steps),
            Ok(())
        );
    }
    // A trace starting from the successor cannot launder an arbitrary
    // source block into the canonical function entry.
    assert_eq!(
        verify_source_block_entries(
            &blocks,
            &edges,
            &entry,
            false_run.get(2..).ok_or("missing successor")?,
        ),
        Err(SourcePhiCopyTraceError::InvalidBlockEntry)
    );
    let mut wrong_predecessor = edges.clone();
    wrong_predecessor[0].predecessor = 2;
    assert_eq!(
        verify_source_block_entries(
            &blocks,
            &wrong_predecessor,
            &entry,
            &false_run
        ),
        Err(SourcePhiCopyTraceError::InvalidBlockEntry)
    );
    // The actual true jump enters C4, not the start of a forged combined
    // C2..C4 successor body, even if the proposed edge claims C4.
    let mut middle = blocks;
    middle[2].start = 2;
    assert_eq!(
        verify_source_block_entries(&middle, &edges, &entry, &true_run),
        Err(SourcePhiCopyTraceError::InvalidBlockEntry)
    );

    let pad_run = guest_phi_trace_with_predecessor_bypass(false)?;
    let mut phi = linked_phi_edge()?.0;
    phi.control_address = 2;
    phi.entry_address = 3;
    phi.pad_exit_address = Some(7);
    phi.target_address = 10;
    let pad_blocks = [
        GuestCodeBlockPlacement {
            function: 0,
            block: 0,
            start: 0,
            end_exclusive: 3,
            control_start: 2,
        },
        GuestCodeBlockPlacement {
            function: 0,
            block: 1,
            start: 10,
            end_exclusive: 11,
            control_start: 10,
        },
    ];
    assert_eq!(
        verify_source_block_entries(
            &pad_blocks,
            from_ref(&phi),
            &entry,
            &pad_run
        ),
        Ok(())
    );
    phi.pad_exit_address = Some(6);
    assert_eq!(
        verify_source_block_entries(
            &pad_blocks,
            from_ref(&phi),
            &entry,
            &pad_run
        ),
        Err(SourcePhiCopyTraceError::InvalidBlockEntry)
    );
    Ok(())
}

// A physically executed control-suffix jump back to the same block start is
// a source CFG backedge, not an invisible ordinary setup loop. The post-jump
// fetch at C0 is a real VM step even though its code was self-encrypted.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::indexing_slicing,
    reason = "fixed three-step N15 control-to-entry backedge"
)]
fn real_guest_self_backedge_requires_source_control_edge() -> Result<(), String>
{
    let mut source = (0..59)
        .map(|site| graphical(site, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    source[0] = graphical(0, b'p')?;
    source[1] = graphical(1, b'i')?;
    let profile = current_profile();
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| format!("self-backedge loader: {error:?}"))?;
    let mut memory = loaded.memory().to_vec();
    memory[70] = 7_174_453;
    memory[71] = u32::try_from(loaded.memory().len())
        .map_err(|error| format!("memory bound: {error:?}"))?
        - 1;
    let mut machine = ProfileMachine::from_state(
        profile,
        memory,
        Vec::new(),
        malbolge::ProfileRegisters {
            accumulator: profile.eof_word(),
            code_pointer: 0,
            data_pointer: 70,
        },
    )
    .map_err(|error| format!("self-backedge machine: {error:?}"))?;
    let mut steps = Vec::new();
    let _ = machine
        .run_traced(3, &mut |step| steps.push(*step))
        .map_err(|error| format!("self-backedge run: {error:?}"))?;
    assert_eq!(
        steps
            .iter()
            .map(|step| step.before.registers.code_pointer)
            .collect::<Vec<_>>(),
        [0, 1, 0]
    );
    assert_eq!(steps[1].decoded, Some(b'i'));
    assert_eq!(steps[1].after.registers.code_pointer, 0);
    let blocks = [GuestCodeBlockPlacement {
        function: 0,
        block: 0,
        start: 0,
        end_exclusive: 2,
        control_start: 1,
    }];
    let entries = [GuestCodeFunctionEntry {
        function: 0,
        block: 0,
        address: 0,
    }];
    let mut backedge = placed_edge();
    backedge.snapshot_sites.clear();
    backedge.commit_sites.clear();
    backedge.snapshots.clear();
    backedge.commits.clear();
    backedge.predecessor = 0;
    backedge.successor = 0;
    backedge.control_address = 1;
    backedge.entry_address = 0;
    backedge.pad_exit_address = None;
    backedge.target_address = 0;
    assert_eq!(
        verify_source_block_exits(&blocks, &[], &steps),
        Err(SourcePhiCopyTraceError::InvalidControlTransfer)
    );
    assert_eq!(
        verify_source_block_entries(&blocks, &[], &entries, &steps),
        Err(SourcePhiCopyTraceError::InvalidBlockEntry)
    );
    assert_eq!(
        verify_source_block_exits(&blocks, from_ref(&backedge), &steps),
        Ok(())
    );
    assert_eq!(
        verify_source_branch_choices(
            &blocks,
            &[],
            from_ref(&initial_store(None)),
            &frames(),
            &steps
        ),
        Err(SourcePhiCopyTraceError::InvalidControlTransfer)
    );
    assert_eq!(
        verify_source_branch_choices(
            &blocks,
            from_ref(&backedge),
            from_ref(&initial_store(None)),
            &frames(),
            &steps
        ),
        Ok(())
    );
    assert_eq!(
        verify_source_block_entries(
            &blocks,
            from_ref(&backedge),
            &entries,
            &steps
        ),
        Ok(())
    );
    Ok(())
}

// The source-block control suffix can be reached by a real intra-block `i`
// that skips a prior mandatory operation site. Source-block exit and entry
// checks alone cannot distinguish that execution from a complete visit.
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "fixed N15 op-site skip and normative step assertions"
)]
fn physical_source_effect_skip(
    skip: bool,
    store_opcode: u8,
    setup_opcode: u8,
    early_halt: bool,
) -> Result<Vec<ProfileStepTrace>, String> {
    let mut source = (0..59)
        .map(|site| graphical(site, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    for (site, opcode) in [
        (0, store_opcode),
        (
            1,
            if skip {
                b'i'
            } else {
                setup_opcode
            },
        ),
        (2, b'o'),
        (
            3,
            if early_halt {
                b'v'
            } else {
                b'o'
            },
        ),
        (4, b'v'),
    ] {
        source[site] = graphical(site, opcode)?;
    }
    let profile = current_profile();
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| format!("effect skip loader: {error:?}"))?;
    let mut memory = loaded.memory().to_vec();
    *memory.get_mut(70).ok_or("missing source data")? = 7_174_453;
    *memory.get_mut(71).ok_or("missing skip pointer")? = 2;
    let mut machine = ProfileMachine::from_state(
        profile,
        memory,
        Vec::new(),
        malbolge::ProfileRegisters {
            accumulator: profile.eof_word(),
            code_pointer: 0,
            data_pointer: 70,
        },
    )
    .map_err(|error| format!("effect skip VM: {error:?}"))?;
    let mut steps = Vec::new();
    let outcome = machine
        .run_traced(6, &mut |step| steps.push(*step))
        .map_err(|error| format!("effect skip run: {error:?}"))?;
    assert_eq!(outcome, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: if skip || early_halt {
            4
        } else {
            5
        },
    });
    assert_eq!(
        steps
            .iter()
            .map(|step| step.before.registers.code_pointer)
            .collect::<Vec<_>>(),
        if skip {
            vec![0, 1, 3, 4]
        } else if early_halt {
            vec![0, 1, 2, 3]
        } else {
            vec![0, 1, 2, 3, 4]
        },
    );
    Ok(steps)
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "physical CFG op skip and source-order refusals"
)]
fn real_guest_cannot_skip_source_operation_inside_same_block()
-> Result<(), String> {
    let complete = physical_source_effect_skip(false, b'p', b'o', false)?;
    let skipped = physical_source_effect_skip(true, b'p', b'o', false)?;
    let wrong_store = physical_source_effect_skip(false, b'o', b'o', false)?;
    let stray_output = physical_source_effect_skip(false, b'p', b'<', false)?;
    let stray_input = physical_source_effect_skip(false, b'p', b'/', false)?;
    let blocks = [
        GuestCodeBlockPlacement {
            function: 0,
            block: 0,
            start: 0,
            end_exclusive: 4,
            control_start: 3,
        },
        GuestCodeBlockPlacement {
            function: 0,
            block: 1,
            start: 4,
            end_exclusive: 5,
            control_start: 4,
        },
    ];
    let mut edge = placed_edge();
    edge.snapshot_sites.clear();
    edge.commit_sites.clear();
    edge.snapshots.clear();
    edge.commits.clear();
    edge.control_address = 3;
    edge.entry_address = 4;
    edge.pad_exit_address = None;
    edge.target_address = 4;
    let entry = [GuestCodeFunctionEntry {
        function: 0,
        block: 0,
        address: 0,
    }];
    let effects = [initial_store(None), GuestCodeOperationEffectSite {
        block: 0,
        code_address: 2,
        effect: GuestCodeOperationEffect::Compute,
        function: 0,
        ordinal: 1,
    }];
    for steps in [&complete, &skipped] {
        assert_eq!(
            verify_source_block_exits(&blocks, from_ref(&edge), steps),
            Ok(())
        );
        assert_eq!(
            verify_source_block_entries(
                &blocks,
                from_ref(&edge),
                &entry,
                steps
            ),
            Ok(())
        );
    }
    assert_eq!(
        verify_source_block_effect_visits(&blocks, &effects, &complete),
        Ok(())
    );
    // An extra real guest read/write in an unanchored setup cell is not
    // source-C I/O, even if all declared operation sites still execute.
    for steps in [&stray_output, &stray_input] {
        assert_eq!(
            verify_source_block_effect_visits(&blocks, &effects, steps),
            Err(SourcePhiCopyTraceError::UnexpectedSourceIo)
        );
    }
    // Conversely, each real I/O opcode is admissible at its exact source
    // effect site; this alone does not prove guest C dataflow or EOF
    // conversion.
    let mut sourced_output = vec![
        effects[0],
        GuestCodeOperationEffectSite {
            block: 0,
            code_address: 1,
            effect: GuestCodeOperationEffect::Output {
                source: GuestPlacedOperand {
                    address: 70,
                    type_kind: TernaryCfgScalarKind::U8,
                    value: 1,
                    words: 1,
                },
            },
            function: 0,
            ordinal: 1,
        },
        effects[1],
    ];
    sourced_output[2].ordinal = 2;
    assert_eq!(
        verify_source_block_effect_visits(
            &blocks,
            &sourced_output,
            &stray_output
        ),
        Ok(())
    );
    sourced_output[1].effect = GuestCodeOperationEffect::Input {
        destination: GuestPlacedOperand {
            address: 71,
            type_kind: TernaryCfgScalarKind::U8,
            value: 2,
            words: 1,
        },
        semantics: GuestCodeInputSemantics::ByteU8,
    };
    assert_eq!(
        verify_source_block_effect_visits(
            &blocks,
            &sourced_output,
            &stray_input
        ),
        Ok(())
    );
    assert_eq!(
        verify_source_block_effect_visits(
            &blocks,
            &sourced_output,
            &stray_output
        ),
        Err(SourcePhiCopyTraceError::UnexpectedSourceIo)
    );
    assert_eq!(
        verify_source_block_effect_visits(&blocks, &effects, &skipped),
        Err(SourcePhiCopyTraceError::MissingBlockEffect)
    );
    // A matching code address alone cannot claim a frame Store when the
    // physical guest executed o there, nor can a p to M70 prove a write to M71.
    assert_eq!(
        verify_source_block_effect_visits(&blocks, &effects, &wrong_store),
        Err(SourcePhiCopyTraceError::InvalidBlockEffect)
    );
    let mut wrong_destination = effects;
    wrong_destination[0] = initial_store(None);
    wrong_destination[0].effect = GuestCodeOperationEffect::Store {
        destination: 71,
        literal: None,
    };
    assert_eq!(
        verify_source_block_effect_visits(
            &blocks,
            &wrong_destination,
            &complete
        ),
        Err(SourcePhiCopyTraceError::InvalidBlockEffect)
    );
    let mut wrong_output = effects;
    wrong_output[1].effect = GuestCodeOperationEffect::Output {
        source: GuestPlacedOperand {
            address: 70,
            type_kind: TernaryCfgScalarKind::U8,
            value: 1,
            words: 1,
        },
    };
    assert_eq!(
        verify_source_block_effect_visits(&blocks, &wrong_output, &complete),
        Err(SourcePhiCopyTraceError::InvalidBlockEffect)
    );
    // Even if every site appears somewhere in the visit, the source order
    // of their first required effects is itself a verifier obligation.
    let reversed = [effects[1], effects[0]];
    assert_eq!(
        verify_source_block_effect_visits(&blocks, &reversed, &complete),
        Err(SourcePhiCopyTraceError::MissingBlockEffect)
    );
    Ok(())
}

// A source-located output still needs the exact live guest-written U8 operand.
// The real VM can emit a plausible byte from A without first materializing
// the named SSA cell, or after a different source store changes A.
#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "one bounded VM positive and three source-output counterexamples"
)]
fn real_guest_source_output_requires_current_frame_operand()
-> Result<(), String> {
    let trace =
        |second_word: Option<u32>| -> Result<Vec<ProfileStepTrace>, String> {
            let mut source = (0..59)
                .map(|site| graphical(site, b'o'))
                .collect::<Result<Vec<_>, _>>()?;
            for (site, opcode) in [
                (0, b'*'),
                (
                    1,
                    if second_word.is_some() {
                        b'*'
                    } else {
                        b'o'
                    },
                ),
                (2, b'<'),
                (3, b'v'),
            ] {
                source[site] = graphical(site, opcode)?;
            }
            let profile = current_profile();
            let loaded =
                ProfileMachine::from_source(profile, &source, Vec::new())
                    .map_err(|error| {
                        format!("output operand loader: {error:?}")
                    })?;
            let mut memory = loaded.memory().to_vec();
            memory[70] = 3;
            memory[71] = second_word.unwrap_or(6);
            let mut machine = ProfileMachine::from_state(
                profile,
                memory,
                Vec::new(),
                malbolge::ProfileRegisters {
                    accumulator: profile.eof_word(),
                    code_pointer: 0,
                    data_pointer: 70,
                },
            )
            .map_err(|error| format!("output operand VM: {error:?}"))?;
            let mut steps = Vec::new();
            let outcome = machine
                .run_traced(4, &mut |step| steps.push(*step))
                .map_err(|error| format!("output operand run: {error:?}"))?;
            assert_eq!(outcome, RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 4,
            });
            assert_eq!(
                steps.iter().map(|step| step.decoded).collect::<Vec<_>>(),
                if second_word.is_some() {
                    vec![Some(b'*'), Some(b'*'), Some(b'<'), Some(b'v')]
                } else {
                    vec![Some(b'*'), Some(b'o'), Some(b'<'), Some(b'v')]
                }
            );
            Ok(steps)
        };
    let complete = trace(None)?;
    let other_accumulator = trace(Some(6))?;
    let same_value_other_source = trace(Some(3))?;
    let matching_byte_wrong_word = trace(Some(771))?;
    let blocks = [GuestCodeBlockPlacement {
        function: 0,
        block: 0,
        start: 0,
        end_exclusive: 4,
        control_start: 3,
    }];
    let stored = GuestCodeOperationEffectSite {
        block: 0,
        code_address: 0,
        effect: GuestCodeOperationEffect::Store {
            destination: 70,
            literal: None,
        },
        function: 0,
        ordinal: 0,
    };
    let output = GuestCodeOperationEffectSite {
        block: 0,
        code_address: 2,
        effect: GuestCodeOperationEffect::Output {
            source: GuestPlacedOperand {
                address: 70,
                type_kind: TernaryCfgScalarKind::U8,
                value: 0,
                words: 1,
            },
        },
        function: 0,
        ordinal: 1,
    };
    let effects = [stored, output];
    let frames = frames();
    assert_eq!(complete[0].after.registers.accumulator, 1);
    assert_eq!(complete[2].output, Some(1));
    assert_eq!(other_accumulator[1].after.registers.accumulator, 2);
    assert_eq!(other_accumulator[2].output, Some(2));
    assert_eq!(same_value_other_source[1].after.registers.accumulator, 1);
    assert_eq!(same_value_other_source[2].output, Some(1));
    assert_eq!(matching_byte_wrong_word[1].after.registers.accumulator, 257);
    assert_eq!(matching_byte_wrong_word[2].output, Some(1));
    assert_eq!(
        verify_source_block_effect_visits(&blocks, &effects, &complete),
        Ok(())
    );
    assert_eq!(
        verify_source_branch_choices(
            &blocks,
            &[],
            &effects,
            &frames,
            &complete
        ),
        Ok(())
    );
    let mut never_stored = effects;
    never_stored[1].effect = GuestCodeOperationEffect::Output {
        source: GuestPlacedOperand {
            address: 71,
            type_kind: TernaryCfgScalarKind::U8,
            value: 1,
            words: 1,
        },
    };
    assert_eq!(
        verify_source_block_effect_visits(&blocks, &never_stored, &complete),
        Ok(())
    );
    assert_eq!(
        verify_source_branch_choices(
            &blocks,
            &[],
            &never_stored,
            &frames,
            &complete
        ),
        Err(SourcePhiCopyTraceError::MissingOutputMaterialization)
    );
    let extra_store = GuestCodeOperationEffectSite {
        block: 0,
        code_address: 1,
        effect: GuestCodeOperationEffect::Store {
            destination: 71,
            literal: None,
        },
        function: 0,
        ordinal: 1,
    };
    let changed = [stored, extra_store, GuestCodeOperationEffectSite {
        ordinal: 2,
        ..output
    }];
    // The second real * writes an unrelated SSA cell, but happens to load
    // exactly the same word. Numeric output equality is not source dataflow.
    assert_eq!(
        verify_source_block_effect_visits(
            &blocks,
            &changed,
            &same_value_other_source
        ),
        Ok(())
    );
    assert_eq!(
        verify_source_branch_choices(
            &blocks,
            &[],
            &changed,
            &frames,
            &same_value_other_source
        ),
        Err(SourcePhiCopyTraceError::MissingOutputProvenance)
    );
    assert_eq!(
        verify_source_block_effect_visits(
            &blocks,
            &changed,
            &other_accumulator
        ),
        Ok(())
    );
    assert_eq!(
        verify_source_branch_choices(
            &blocks,
            &[],
            &changed,
            &frames,
            &other_accumulator
        ),
        Err(SourcePhiCopyTraceError::InvalidOutputValue)
    );
    // The actual byte can agree while the full physical A word is wrong.
    assert_eq!(
        verify_source_block_effect_visits(
            &blocks,
            &changed,
            &matching_byte_wrong_word
        ),
        Ok(())
    );
    assert_eq!(
        verify_source_branch_choices(
            &blocks,
            &[],
            &changed,
            &frames,
            &matching_byte_wrong_word
        ),
        Err(SourcePhiCopyTraceError::InvalidOutputValue)
    );
    Ok(())
}

// An interior setup jump can execute the same canonical operation effect
// twice without crossing a source CFG edge. Source effect sites are not a
// license for repeated I/O or arithmetic inside a single block visit.
#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "frozen real N15 instruction reentry and exact site counts"
)]
fn real_guest_repeated_source_effect_needs_a_new_block_visit()
-> Result<(), String> {
    let trace = |repeat: bool| -> Result<Vec<ProfileStepTrace>, String> {
        let mut source = (0..59)
            .map(|site| graphical(site, b'o'))
            .collect::<Result<Vec<_>, _>>()?;
        for (site, opcode) in [
            (0, b'o'),
            (1, b'o'),
            (
                2,
                if repeat {
                    b'i'
                } else {
                    b'o'
                },
            ),
            (
                3,
                if repeat {
                    b'o'
                } else {
                    b'v'
                },
            ),
            (10, b'v'),
        ] {
            source[site] = graphical(site, opcode)?;
        }
        let profile = current_profile();
        let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
            .map_err(|error| format!("repeated effect loader: {error:?}"))?;
        let mut memory = loaded.memory().to_vec();
        memory[72] = 0; // First C2 i reaches C1 inside the source block.
        memory[74] = 9; // Second C2 i reaches C10, which already contains v.
        let mut machine = ProfileMachine::from_state(
            profile,
            memory,
            Vec::new(),
            malbolge::ProfileRegisters {
                accumulator: profile.eof_word(),
                code_pointer: 0,
                data_pointer: 70,
            },
        )
        .map_err(|error| format!("repeated effect guest: {error:?}"))?;
        let mut steps = Vec::new();
        let outcome = machine
            .run_traced(8, &mut |step| steps.push(*step))
            .map_err(|error| {
                format!(
                    "repeated effect run: {error:?}; steps: {:?}",
                    steps
                        .iter()
                        .map(|s| (
                            s.before.registers.code_pointer,
                            s.decoded,
                            s.before.registers.data_pointer,
                            s.after.registers.code_pointer,
                        ))
                        .collect::<Vec<_>>()
                )
            })?;
        let expected = if repeat {
            vec![0, 1, 2, 1, 2, 10]
        } else {
            vec![0, 1, 2, 3]
        };
        assert_eq!(
            steps
                .iter()
                .map(|step| step.before.registers.code_pointer)
                .collect::<Vec<_>>(),
            expected,
        );
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: if repeat {
                6
            } else {
                4
            },
        });
        Ok(steps)
    };
    let blocks = [
        GuestCodeBlockPlacement {
            function: 0,
            block: 0,
            start: 0,
            end_exclusive: 3,
            control_start: 2,
        },
        GuestCodeBlockPlacement {
            function: 0,
            block: 1,
            start: 3,
            end_exclusive: 4,
            control_start: 3,
        },
    ];
    let effects = [
        GuestCodeOperationEffectSite {
            function: 0,
            block: 0,
            code_address: 0,
            effect: GuestCodeOperationEffect::Compute,
            ordinal: 0,
        },
        GuestCodeOperationEffectSite {
            function: 0,
            block: 0,
            code_address: 1,
            effect: GuestCodeOperationEffect::Compute,
            ordinal: 1,
        },
    ];
    let once = trace(false)?;
    let repeated = trace(true)?;
    assert_eq!(
        verify_source_block_effect_visits(&blocks, &effects, &once),
        Ok(())
    );
    assert_eq!(
        verify_source_block_effect_visits(&blocks, &effects, &repeated),
        Err(SourcePhiCopyTraceError::RepeatedBlockEffect)
    );
    Ok(())
}

// A control-suffix self-backedge starts a fresh source-block iteration even
// though the VM's code pointer never leaves that block's address interval.
// A bounded prefix ends at reentered C0, before C1's required effect.
#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "actual four-step self-modifying N15 guest and fresh-visit check"
)]
fn real_guest_self_backedge_rechecks_all_source_effect_sites()
-> Result<(), String> {
    let mut source = (0..59)
        .map(|site| graphical(site, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    source[0] = graphical(0, b'o')?;
    source[1] = graphical(1, b'o')?;
    source[2] = graphical(2, b'i')?;
    let profile = current_profile();
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| format!("iteration loader: {error:?}"))?;
    let mut memory = loaded.memory().to_vec();
    memory[72] = u32::try_from(memory.len())
        .map_err(|error| format!("guest capacity: {error:?}"))?
        - 1;
    let mut machine = ProfileMachine::from_state(
        profile,
        memory,
        Vec::new(),
        malbolge::ProfileRegisters {
            accumulator: profile.eof_word(),
            code_pointer: 0,
            data_pointer: 70,
        },
    )
    .map_err(|error| format!("iteration guest: {error:?}"))?;
    let mut steps = Vec::new();
    let outcome = machine
        .run_traced(4, &mut |step| steps.push(*step))
        .map_err(|error| format!("iteration run: {error:?}"))?;
    assert_eq!(outcome, RunOutcome::BudgetExhausted { steps: 4 });
    assert_eq!(
        steps
            .iter()
            .map(|step| step.before.registers.code_pointer)
            .collect::<Vec<_>>(),
        [0, 1, 2, 0],
    );
    assert_eq!(steps[3].decoded, Some(b'+'));
    let blocks = [GuestCodeBlockPlacement {
        function: 0,
        block: 0,
        start: 0,
        end_exclusive: 3,
        control_start: 2,
    }];
    let effects = [
        GuestCodeOperationEffectSite {
            function: 0,
            block: 0,
            code_address: 0,
            effect: GuestCodeOperationEffect::Compute,
            ordinal: 0,
        },
        GuestCodeOperationEffectSite {
            function: 0,
            block: 0,
            code_address: 1,
            effect: GuestCodeOperationEffect::Compute,
            ordinal: 1,
        },
    ];
    assert_eq!(
        verify_source_block_effect_visits(&blocks, &effects, &steps),
        Err(SourcePhiCopyTraceError::MissingBlockEffect)
    );
    Ok(())
}

// An actual `v` in an earlier source control suffix can halt without
// traversing the source Return block. All earlier source effects are present,
// so ordinary block visitation and edge checks alone cannot reject it.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "bounded real guest return and early-halt provenance"
)]
fn real_guest_halt_requires_source_return_control() -> Result<(), String> {
    let good = physical_source_effect_skip(false, b'p', b'o', false)?;
    let early = physical_source_effect_skip(false, b'p', b'o', true)?;
    let blocks = [
        GuestCodeBlockPlacement {
            function: 0,
            block: 0,
            start: 0,
            end_exclusive: 4,
            control_start: 3,
        },
        GuestCodeBlockPlacement {
            function: 0,
            block: 1,
            start: 4,
            end_exclusive: 5,
            control_start: 4,
        },
    ];
    let mut edge = placed_edge();
    edge.snapshot_sites.clear();
    edge.commit_sites.clear();
    edge.snapshots.clear();
    edge.commits.clear();
    edge.control_address = 3;
    edge.entry_address = 4;
    edge.pad_exit_address = None;
    edge.target_address = 4;
    let effects = [initial_store(None), GuestCodeOperationEffectSite {
        block: 0,
        code_address: 2,
        effect: GuestCodeOperationEffect::Compute,
        function: 0,
        ordinal: 1,
    }];
    for steps in [&good, &early] {
        assert_eq!(
            verify_source_block_exits(&blocks, from_ref(&edge), steps),
            Ok(())
        );
        assert_eq!(
            verify_source_block_effect_visits(&blocks, &effects, steps),
            Ok(())
        );
    }
    let returns = [GuestCodeReturnSite {
        block: 1,
        address: 4,
        function: 0,
        value: None,
    }];
    assert_eq!(verify_source_return_sites(&blocks, &returns, &good), Ok(()));
    assert_eq!(
        verify_source_return_sites(&blocks, &returns, &early),
        Err(SourcePhiCopyTraceError::InvalidSourceReturn)
    );
    assert_eq!(
        verify_source_return_sites(&blocks, &[], &good),
        Err(SourcePhiCopyTraceError::InvalidSourceReturn)
    );
    // Even a claimed return in the reached block must start at its exact
    // source-reserved control address, not a convenient earlier code cell.
    let misplaced = [GuestCodeReturnSite { address: 3, ..returns[0] }];
    assert_eq!(
        verify_source_return_sites(&blocks, &misplaced, &good),
        Err(SourcePhiCopyTraceError::InvalidSourceReturn)
    );
    Ok(())
}

#[expect(
    clippy::indexing_slicing,
    reason = "fixed physical code sites"
)]
fn physical_two_phi_pad_source(skip: bool) -> Result<Vec<u8>, String> {
    let mut source = (0..59)
        .map(|site| graphical(site, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    for (site, opcode) in [
        (0, b'p'),
        (1, b'j'),
        (2, b'p'),
        (3, b'j'),
        (4, b'p'),
        (5, b'i'),
        (
            11,
            if skip {
                b'i'
            } else {
                b'j'
            },
        ),
        (12, b'p'),
        (13, b'p'),
        (
            14,
            if skip {
                b'j'
            } else {
                b'o'
            },
        ),
        (16, b'i'),
        (19, b'v'),
    ] {
        source[site] = graphical(site, opcode)?;
    }
    Ok(source)
}

fn physical_two_phi_pad_memory(
    skip: bool,
    source: &[u8],
) -> Result<Vec<u32>, String> {
    let loaded =
        ProfileMachine::from_source(current_profile(), source, Vec::new())
            .map_err(|error| format!("two-pad loader: {error:?}"))?;
    let mut memory = loaded.memory().to_vec();
    for address in [70usize, 101, 120, 130, 131] {
        *memory.get_mut(address).ok_or("missing phi frame")? = 7_174_453;
    }
    for (address, value) in [
        (71, 100),
        (102, 119),
        (121, 7),
        (
            125,
            if skip {
                13
            } else {
                129
            },
        ),
        (126, 140),
        (134, 18),
        (142, 18),
    ] {
        *memory.get_mut(address).ok_or("missing pointer seed")? = value;
    }
    Ok(memory)
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "fixed normative guest trace"
)]
fn physical_two_phi_pad_trace(
    skip: bool,
) -> Result<Vec<ProfileStepTrace>, String> {
    let profile = current_profile();
    let source = physical_two_phi_pad_source(skip)?;
    let memory = physical_two_phi_pad_memory(skip, &source)?;
    let mut machine = ProfileMachine::from_state(
        profile,
        memory,
        Vec::new(),
        malbolge::ProfileRegisters {
            accumulator: profile.eof_word(),
            code_pointer: 0,
            data_pointer: 70,
        },
    )
    .map_err(|error| format!("two-pad state: {error:?}"))?;
    let mut steps = Vec::new();
    let outcome = machine
        .run_traced(20, &mut |step| steps.push(*step))
        .map_err(|error| format!("two-pad VM: {error:?}"))?;
    assert_eq!(outcome, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: if skip {
            14
        } else {
            16
        },
    });
    assert_eq!(
        steps
            .iter()
            .map(|step| step.before.registers.code_pointer)
            .collect::<Vec<_>>(),
        if skip {
            vec![0, 1, 2, 3, 4, 5, 8, 9, 10, 11, 14, 15, 16, 19]
        } else {
            vec![0, 1, 2, 3, 4, 5, 8, 9, 10, 11, 12, 13, 14, 15, 16, 19]
        }
    );
    Ok(steps)
}

#[expect(
    clippy::indexing_slicing,
    reason = "fixed phi sites in source plan"
)]
fn physical_two_phi_pad_layout() -> Result<PhysicalTwoPadLayout, String> {
    let (first, _frame) = linked_phi_edge()?;
    let mut second = first.clone();
    second.predecessor = 1;
    second.successor = 2;
    second.control_address = 10;
    second.entry_address = 11;
    second.pad_exit_address = Some(16);
    second.target_address = 19;
    second.snapshot_sites[0] = GuestCodeCellCopySite {
        code_address: 12,
        copy: GuestPlacedCellCopy {
            destination: 130,
            source: 120,
        },
    };
    second.commit_sites[0] = GuestCodeCellCopySite {
        code_address: 13,
        copy: GuestPlacedCellCopy {
            destination: 131,
            source: 130,
        },
    };
    second.snapshots[0] = second.snapshot_sites[0].copy;
    second.commits[0] = second.commit_sites[0].copy;
    Ok(([first, second], [
        GuestCodeBlockPlacement {
            function: 0,
            block: 0,
            start: 0,
            end_exclusive: 2,
            control_start: 1,
        },
        GuestCodeBlockPlacement {
            function: 0,
            block: 1,
            start: 8,
            end_exclusive: 11,
            control_start: 10,
        },
        GuestCodeBlockPlacement {
            function: 0,
            block: 2,
            start: 19,
            end_exclusive: 20,
            control_start: 19,
        },
    ]))
}

// A complete first pad must not authorize a later visited phi pad that jumps
// across every source-required copy but still reaches its correct successor.
// Both paths execute on the normative N15 VM with real pointer routing.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "fixed, real VM two-pad trace with checked code positions"
)]
fn real_guest_second_phi_pad_cannot_skip_all_its_copies() -> Result<(), String>
{
    let skipped = physical_two_phi_pad_trace(true)?;
    let complete = physical_two_phi_pad_trace(false)?;
    let (edges, blocks) = physical_two_phi_pad_layout()?;
    for steps in [&complete, &skipped] {
        assert_eq!(verify_source_block_exits(&blocks, &edges, steps), Ok(()));
        assert_eq!(
            verify_source_block_entries(
                &blocks,
                &edges,
                &[GuestCodeFunctionEntry {
                    block: 0,
                    address: 0,
                    function: 0,
                }],
                steps,
            ),
            Ok(())
        );
        assert_eq!(
            verify_predecessor_phi_entries(&blocks, &edges, steps),
            Ok(())
        );
    }
    let frame = [GuestFramePlacement {
        base: 70,
        end_exclusive: 151,
        source_cells: 59,
    }];
    let effects = [initial_store(None)];
    let context = || PhiTraceContext {
        edges: &edges,
        effects: &effects,
        frames: &frame,
    };
    let proof = verify_traced_phi_copies_with_transfer_policy(
        context(),
        &complete,
        true,
    )
    .map_err(|error| format!("complete two-pad transfer: {error:?}"))?;
    assert_eq!(proof.completed_pads, 2);
    assert_eq!(proof.copies.len(), 4);
    // The deliberately weaker copy-only gate observes one complete pad.
    assert_eq!(
        verify_traced_phi_copies_with_transfer_policy(
            context(),
            &skipped,
            false
        )
        .map(|observed| observed.completed_pads),
        Ok(1)
    );
    // Strong CFG linkage must account for *every* physically entered pad.
    assert_eq!(
        verify_traced_phi_copies_with_transfer_policy(
            context(),
            &skipped,
            true
        ),
        Err(SourcePhiCopyTraceError::InvalidPhiOrder)
    );
    Ok(())
}

// A real terminating source-block path may select no phi-bearing edge. The
// strongest CFG gate must still validate block/control provenance without
// inventing a required phi visit; the copy-only study retains its reached-
// copy requirement. The unreachable pad remains available on another path.
#[test]
fn real_guest_phi_free_return_path_satisfies_cfg_transfer_gate()
-> Result<(), String> {
    let mut source = (0..8)
        .map(|site| graphical(site, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    let halt = source.get_mut(2).ok_or("missing return code cell")?;
    *halt = graphical(2, b'v')?;
    let mut machine =
        ProfileMachine::from_source(current_profile(), &source, Vec::new())
            .map_err(|error| format!("real return guest: {error:?}"))?;
    let mut steps = Vec::new();
    let outcome = machine
        .run_traced(4, &mut |step| steps.push(*step))
        .map_err(|error| format!("real return trace: {error:?}"))?;
    assert_eq!(outcome, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: 3,
    });
    let mut unreachable = placed_edge();
    unreachable.entry_address = 4;
    unreachable.pad_exit_address = Some(6);
    unreachable.snapshot_sites[0].code_address = 4;
    unreachable.commit_sites[0].code_address = 5;
    unreachable.target_address = 7;
    let edges = [unreachable];
    let blocks = [GuestCodeBlockPlacement {
        function: 0,
        block: 0,
        start: 0,
        end_exclusive: 3,
        control_start: 2,
    }];
    assert_eq!(verify_source_block_exits(&blocks, &edges, &steps), Ok(()));
    assert_eq!(
        verify_source_block_entries(
            &blocks,
            &edges,
            &[GuestCodeFunctionEntry {
                function: 0,
                block: 0,
                address: 0,
            }],
            &steps,
        ),
        Ok(())
    );
    assert_eq!(
        verify_source_block_effect_visits(&blocks, &[], &steps),
        Ok(())
    );
    assert_eq!(
        verify_source_return_sites(
            &blocks,
            &[GuestCodeReturnSite {
                function: 0,
                block: 0,
                address: 2,
                value: None,
            }],
            &steps,
        ),
        Ok(())
    );
    assert_eq!(
        verify_predecessor_phi_entries(&blocks, &edges, &steps),
        Ok(())
    );
    assert_eq!(
        verify_source_branch_choices(&blocks, &edges, &[], &frames(), &steps),
        Ok(())
    );
    let frame = frames();
    let context = || PhiTraceContext {
        edges: &edges,
        effects: &[],
        frames: &frame,
    };
    let proof =
        verify_traced_phi_copies_with_transfer_policy(context(), &steps, true)
            .map_err(|error| {
                format!("unreached phi must not fail CFG: {error:?}")
            })?;
    assert_eq!(proof.completed_pads, 0);
    assert!(proof.copies.is_empty());
    assert_eq!(
        verify_traced_phi_copies_with_transfer_policy(context(), &steps, false),
        Err(SourcePhiCopyTraceError::NoReachedPhiCopy),
    );
    Ok(())
}

// Optional *arrival* at a phi pad is not optional *execution*: entering the
// pad and halting before its first snapshot must fail the transfer policy,
// even when the complete trace contains no phi copies at all.
#[test]
fn real_guest_entered_phi_pad_without_copies_refuses_cfg_transfer()
-> Result<(), String> {
    let mut source = (0..10)
        .map(|site| graphical(site, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    *source.get_mut(4).ok_or("missing phi entry")? = graphical(4, b'v')?;
    let mut machine =
        ProfileMachine::from_source(current_profile(), &source, Vec::new())
            .map_err(|error| format!("early phi halt: {error:?}"))?;
    let mut steps = Vec::new();
    let outcome = machine
        .run_traced(6, &mut |step| steps.push(*step))
        .map_err(|error| format!("early phi trace: {error:?}"))?;
    assert_eq!(outcome, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: 5,
    });
    let mut edge = placed_edge();
    edge.control_address = 3;
    edge.entry_address = 4;
    edge.snapshot_sites[0].code_address = 5;
    edge.commit_sites[0].code_address = 6;
    edge.pad_exit_address = Some(7);
    edge.target_address = 8;
    let blocks = [GuestCodeBlockPlacement {
        function: 0,
        block: 0,
        start: 0,
        end_exclusive: 4,
        control_start: 3,
    }];
    assert_eq!(
        verify_predecessor_phi_entries(&blocks, from_ref(&edge), &steps),
        Ok(())
    );
    assert_eq!(
        verify_traced_phi_copies_with_transfer_policy(
            PhiTraceContext {
                edges: from_ref(&edge),
                effects: &[],
                frames: &frames(),
            },
            &steps,
            true,
        ),
        Err(SourcePhiCopyTraceError::InvalidPhiOrder),
    );
    Ok(())
}
