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
//   - Source-loaded EOF-zero predicate's finite physical reentry obstruction.
// - Must-Not:
//   - Claim a general branch impossibility, signed C23 conversion or checksum.
// - Allows:
//   - Inputs: fixed N15 source and six {j,o,*,p} continuation cells.
//   - Outputs: real VM entry state and exhaustive independent scalar search.
//   - Side effects: isolated normative guest run only.
// - Split-When:
//   - A general guest CFG linker supersedes this bounded negative route.
// - Merge-When:
//   - A verified physical predicate-to-i transfer replaces this search.

//! Why the exact C54 EOF-zero word cannot yet drive a short guest code jump.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeMap;

use malbolge::{ProfileMachine, RunOutcome, TraceInput, current_profile};

const MODULUS: u32 = 14_348_907;
const EOF_PREDICATE_CELL: u32 = 127;
const RAW_LOW: u32 = 7_174_417;
const RAW_HIGH: u32 = RAW_LOW + 1;

#[derive(Clone)]
struct CandidateState {
    data: u32,
    accumulator: u32,
    writes: BTreeMap<u32, u32>,
}

impl CandidateState {
    fn operand(&self, memory: &[u32]) -> Result<u32, String> {
        if let Some(value) = self.writes.get(&self.data) {
            return Ok(*value);
        }
        memory
            .get(
                usize::try_from(self.data)
                    .map_err(|error| error.to_string())?,
            )
            .copied()
            .ok_or_else(|| "pointer escaped the N15 guest memory".to_owned())
    }

    #[expect(
        clippy::arithmetic_side_effects,
        clippy::integer_division_remainder_used,
        reason = "independent over-approximating finite pointer semantics"
    )]
    fn step(&self, memory: &[u32], instruction: u8) -> Result<Self, String> {
        let operand = self.operand(memory)?;
        let mut next = self.clone();
        match instruction {
            b'j' => next.data = (operand + 1) % MODULUS,
            b'o' => next.data = (next.data + 1) % MODULUS,
            b'*' => {
                let value = operand / 3 + (operand % 3) * (MODULUS / 3);
                _ = next.writes.insert(next.data, value);
                next.accumulator = value;
                next.data = (next.data + 1) % MODULUS;
            },
            b'p' => {
                let value = independent_crazy(operand, next.accumulator);
                _ = next.writes.insert(next.data, value);
                next.accumulator = value;
                next.data = (next.data + 1) % MODULUS;
            },
            _ => {
                return Err(
                    "outside the frozen continuation grammar".to_owned()
                );
            },
        }
        Ok(next)
    }
}

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "independent finite ternary arithmetic, not the VM implementation"
)]
fn independent_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    const TABLE: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut result = 0;
    let mut place = 1;
    for _ in 0..15 {
        result +=
            TABLE[(data % 3) as usize][(accumulator % 3) as usize] * place;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    result
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "bounded genuine guest entry trace with exhaustive six-cell search"
)]
fn source_loaded_eof_zero_has_no_six_cell_data_pointer_reentry()
-> Result<(), String> {
    let profile = current_profile();
    let plan = layout::build_adjacent_c32_zero_c37_raw_eof_zero_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    let source = plan.raw_pointer.raw_pair.zero_pair.source;
    assert_eq!(source.len(), 62);
    assert_eq!(layout::admit_c23_probe_graphical_source(&source), Ok(()));
    let mut vm = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    let mut trace = Vec::new();
    assert_eq!(
        vm.run_traced(55, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?,
        RunOutcome::BudgetExhausted { steps: 55 },
    );
    assert_eq!(trace.len(), 55);
    assert_eq!(trace[37].input, Some(TraceInput::EndOfInput));
    assert_eq!(trace[54].decoded, Some(b'p'));
    assert_eq!(
        trace[54]
            .memory_reads
            .data
            .map(|read| (read.address, read.value)),
        Some((EOF_PREDICATE_CELL, 0)),
    );
    assert_eq!(
        trace[54]
            .memory_delta
            .data
            .map(|write| (write.address, write.after)),
        None, // M127 was already zero; p is a reached idempotent write.
    );
    assert_eq!(trace[54].after.registers.accumulator, 0);
    assert_eq!(trace[54].after.registers.data_pointer, 128);
    assert_eq!(vm.memory_word(RAW_LOW), Ok(profile.eof_word()));
    assert_eq!(vm.memory_word(RAW_HIGH), Ok(0));
    assert_eq!(vm.memory_word(EOF_PREDICATE_CELL), Ok(0));

    // The source has only C55..C61 available. To use the actual C54 store
    // as an i operand at C61, up to six preceding cells must bring D back
    // to M127. Explore all 4^1 + ... + 4^6 = 5,460 sequences, including
    // *unrestricted* p/* data rewrites. This deliberately over-approximates
    // source encoding and code-cell encryption; even the relaxed search has
    // no return to D127. Other layouts and longer paths remain untested.
    let mut frontier = vec![CandidateState {
        data: 128,
        accumulator: 0,
        writes: BTreeMap::new(),
    }];
    for depth in 1u32..=6 {
        let mut next = Vec::new();
        for state in &frontier {
            for instruction in [b'j', b'o', b'*', b'p'] {
                let reached = state.step(vm.memory(), instruction)?;
                assert_ne!(
                    reached.data, EOF_PREDICATE_CELL,
                    "a candidate reached C54's authentic EOF predicate cell",
                );
                next.push(reached);
            }
        }
        assert_eq!(next.len(), 4usize.pow(depth));
        frontier = next;
    }
    Ok(())
}
