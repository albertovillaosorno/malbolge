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
//   - Bounded recurrent physical access blocks and encryption preparation.
// - Must-Not:
//   - Admit source-C effects or claim arbitrary guest arithmetic.
// - Allows:
//   - Inputs: exact profile and bounded operation envelopes.
//   - Outputs: graphical code and proposed indirect preparation routes.
//   - Side effects: none; independent VM replay owns acceptance.
// - Split-When:
//   - General recurrent instruction allocation replaces fixed envelopes.
// - Merge-When:
//   - Recurrent source lowering owns physical access scheduling.
// - Summary:
//   - Restore multiple code cells by indirect jumps over inert suffixes.

use malbolge::{
    ProfileDescriptor, decode_profile_instruction, encrypt_profile_cell,
};

use super::super::super::LinearOpcode;
use super::super::{BuildError, Emitter, LAYOUT, canonical_noop_cell};

const MAX_CELLS: usize = 8;
const MAX_JUMPS: usize = 2_048;

#[derive(Debug)]
pub(super) struct AccessBlock {
    pub(super) after: u32,
    pub(super) before: u32,
    cells: Vec<u8>,
    pub(super) start: u32,
}

impl AccessBlock {
    fn active_suffix(
        &self,
        state: &[u8],
        index: usize,
    ) -> Result<Option<usize>, BuildError> {
        for (offset, cell) in state.iter().copied().enumerate().rev() {
            if offset <= index {
                break;
            }
            let opcode = decode_profile_instruction(
                u32::from(cell),
                self.address(offset)?,
            )
            .ok_or(LAYOUT)?;
            if b"ji*p/<v".contains(&opcode) {
                return Ok(Some(offset));
            }
        }
        Ok(None)
    }

    fn address(&self, index: usize) -> Result<u32, BuildError> {
        self.start
            .checked_add(u32::try_from(index).map_err(|_error| LAYOUT)?)
            .ok_or(LAYOUT)
    }

    fn advance_suffix(
        &self,
        state: &mut [u8],
        index: usize,
        jumps: &mut Vec<PreparationJump>,
    ) -> Result<(), BuildError> {
        if jumps.len() >= MAX_JUMPS {
            return Err(LAYOUT);
        }
        let suffix = state.get_mut(index..).ok_or(LAYOUT)?;
        jumps.push(PreparationJump {
            target: self.address(index)?,
            words: u32::try_from(suffix.len()).map_err(|_error| LAYOUT)?,
        });
        for cell in suffix {
            *cell = encrypt(*cell)?;
        }
        Ok(())
    }

    pub(super) fn emit(
        &self,
        emitter: &mut Emitter<'_>,
    ) -> Result<(), BuildError> {
        emitter.pad_to_entry(
            usize::try_from(self.start).map_err(|_error| LAYOUT)?,
            0,
        )?;
        emitter.source.extend_from_slice(&self.cells);
        let _: u32 = emitter.append_indirect()?;
        Ok(())
    }

    pub(super) fn new(
        profile: &ProfileDescriptor,
        start: u32,
        op: LinearOpcode,
        shape: AccessShape,
    ) -> Result<Self, BuildError> {
        use super::super::super::unique_graphical_cell;

        let AccessShape {
            after,
            before,
            return_to_route,
        } = shape;
        let size = before
            .checked_add(after)
            .and_then(|sum| sum.checked_add(2))
            .and_then(|sum| sum.checked_add(u32::from(return_to_route)))
            .ok_or(LAYOUT)?;
        if usize::try_from(size).map_err(|_error| LAYOUT)? > MAX_CELLS {
            return Err(LAYOUT);
        }
        let mut operations = vec![LinearOpcode::RelocateDataPointer];
        for _ in 0..before {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.push(op);
        for _ in 0..after {
            operations.push(LinearOpcode::NoOperation);
        }
        if return_to_route {
            operations.push(LinearOpcode::RelocateDataPointer);
        }
        let mut cells = Vec::new();
        for (offset, operation) in operations.into_iter().enumerate() {
            let position = usize::try_from(start)
                .ok()
                .and_then(|value| value.checked_add(offset))
                .ok_or(LAYOUT)?;
            let cell = if operation == LinearOpcode::NoOperation {
                canonical_noop_cell(profile, position)?
            } else {
                unique_graphical_cell(profile, operation, position)
                    .map_err(|_error| LAYOUT)?
            };
            cells.push(cell);
        }
        Ok(Self {
            after,
            before,
            cells,
            start,
        })
    }

    pub(super) fn operation_site(&self) -> Result<u32, BuildError> {
        self.start
            .checked_add(self.before)
            .and_then(|value| value.checked_add(1))
            .ok_or(LAYOUT)
    }

    // Start with the state after exactly one execution of every active
    // and inert cell. Restore the entire envelope, not merely its p.
    pub(super) fn preparation(
        &self,
        bootstrap: bool,
    ) -> Result<Vec<PreparationJump>, BuildError> {
        let dirty = self
            .cells
            .iter()
            .copied()
            .map(encrypt)
            .collect::<Result<Vec<_>, _>>()?;
        let (mut state, goal) = if bootstrap {
            (self.cells.clone(), dirty)
        } else {
            (dirty, self.cells.clone())
        };
        let mut jumps = Vec::new();
        for (index, desired) in goal.into_iter().enumerate() {
            self.restore_cell(&mut state, (index, desired), &mut jumps)?;
        }
        Ok(jumps)
    }

    fn prepare_jump(
        &self,
        state: &mut [u8],
        index: usize,
        jumps: &mut Vec<PreparationJump>,
    ) -> Result<(), BuildError> {
        // Jumping to k encrypts k but starts fetching at k+1. Ensure
        // every fetched suffix instruction is inert before that jump.
        for _ in 0..MAX_JUMPS {
            let Some(offset) = self.active_suffix(state, index)? else {
                return self.advance_suffix(state, index, jumps);
            };
            self.prepare_jump(state, offset, jumps)?;
        }
        Err(LAYOUT)
    }

    fn restore_cell(
        &self,
        state: &mut [u8],
        goal: (usize, u8),
        jumps: &mut Vec<PreparationJump>,
    ) -> Result<(), BuildError> {
        let (index, desired) = goal;
        // A graphical character has an orbit of at most 94 phases.
        for _ in 0..94u8 {
            if state.get(index) == Some(&desired) {
                return Ok(());
            }
            self.prepare_jump(state, index, jumps)?;
        }
        Err(LAYOUT)
    }
}

#[derive(Clone, Copy, Debug)]
pub(super) struct AccessShape {
    pub(super) after: u32,
    pub(super) before: u32,
    pub(super) return_to_route: bool,
}

#[derive(Clone, Copy, Debug)]
pub(super) struct PreparationJump {
    pub(super) target: u32,
    pub(super) words: u32,
}

fn encrypt(cell: u8) -> Result<u8, BuildError> {
    encrypt_profile_cell(u32::from(cell))
        .and_then(|value| u8::try_from(value).ok())
        .ok_or(LAYOUT)
}
