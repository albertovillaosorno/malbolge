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
//   - Independent auxiliary operand plan for the recurrent bootstrap.
// - Must-Not:
//   - Import emitter word values or authorize source publication.
// - Allows:
//   - Inputs: admitted recurrent arithmetic and control geometry.
//   - Outputs: required uniform constants, restore seeds and EOF links.
//   - Side effects: none.
// - Split-When:
//   - Additional recurrent terminal representations are supported.
// - Merge-When:
//   - General source-frame verification owns bootstrap data admission.

use core::iter::once;

use malbolge::current_profile;

use super::{
    Error, Expected, SourceRecurrentTransitionProbe, TablePlan, crazy,
    high_selector, insert, inverse_rotation,
};

fn exact(plan: &mut TablePlan, address: u32, value: u32) -> Result<(), Error> {
    insert(plan, address, Expected::Auxiliary(value))
}

fn pointer(
    plan: &mut TablePlan,
    address: u32,
    target: u32,
) -> Result<(), Error> {
    exact(
        plan,
        address,
        target
            .checked_sub(1)
            .ok_or(Error::InvalidTransitionBinding)?,
    )
}

fn rotation(
    plan: &mut TablePlan,
    address: u32,
    site: u32,
    value: u32,
) -> Result<(), Error> {
    insert(plan, address, Expected::TerminalRotation {
        site,
        value: inverse_rotation(value),
    })
}

fn raw_operands(
    probe: &SourceRecurrentTransitionProbe<'_>,
    plan: &mut TablePlan,
) -> Result<(), Error> {
    let route = probe.route;
    let twos = current_profile().eof_word();
    let ones = twos.div_euclid(2);
    for address in
        once(route.load_raw_constant).chain(route.recover_raw_constants)
    {
        exact(plan, address, twos)?;
    }
    for address in once(route.capture_reset_constant)
        .chain(route.lookup_constants)
        .chain(probe.reset_constants.into_iter().flatten())
        .chain(route.raw_reset_constants)
    {
        exact(plan, address, ones)?;
    }
    let [raw_low, _, raw_high, _] = probe.tables;
    for (table, [prefix, seed]) in
        [raw_low, raw_high].into_iter().zip(route.raw_restore_words)
    {
        let mask = crazy(table, twos).saturating_add(364);
        let inverse = crazy(ones, mask);
        exact(plan, prefix, crazy(0, inverse).saturating_mul(2))?;
        exact(plan, seed, inverse)?;
    }
    Ok(())
}

fn terminal_operands(
    probe: &SourceRecurrentTransitionProbe<'_>,
    plan: &mut TablePlan,
) -> Result<(), Error> {
    let [low, high] = probe.loop_probe.state.words;
    let [[low_select, low_twos], [high_select, high_twos]] =
        probe.output_constants;
    let [_, _, _, high_table] = probe.tables;
    let terminal = probe.terminal_address;
    let twos = current_profile().eof_word();
    for landing in probe.loop_probe.guard.eof_landings {
        pointer(plan, landing, terminal)?;
        rotation(
            plan,
            landing.saturating_add(1),
            terminal,
            twos.saturating_sub(81),
        )?;
        pointer(plan, landing.saturating_add(2), high)?;
    }
    rotation(
        plan,
        high_select,
        terminal.saturating_add(4),
        high_selector(17, 0, high_table),
    )?;
    rotation(
        plan,
        low_select,
        terminal.saturating_add(21),
        twos.saturating_sub(17),
    )?;
    for address in [high_twos, low_twos] {
        exact(plan, address, twos)?;
    }
    for (address, target) in [
        (high.saturating_add(1), high_select),
        (high_select.saturating_add(1), high),
        (high_twos.saturating_add(1), high),
        (high.saturating_add(7), high_twos),
        (probe.output_scratch.saturating_add(1), low_select),
        (low_select.saturating_add(1), low),
        (low.saturating_add(1), low_twos),
        (low_twos.saturating_add(1), low),
    ] {
        pointer(plan, address, target)?;
    }
    Ok(())
}

pub(super) fn auxiliary_words(
    probe: &SourceRecurrentTransitionProbe<'_>,
    plan: &mut TablePlan,
) -> Result<(), Error> {
    raw_operands(probe, plan)?;
    terminal_operands(probe, plan)
}
