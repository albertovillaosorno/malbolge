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
//   - Independent replay of the recurrent two-bit checksum state.
// - Must-Not:
//   - Claim complete checksum arithmetic or source-frame admission.
// - Allows:
//   - Inputs: graphical source and independent byte-stream oracle.
//   - Outputs: actual state, table, reset, EOF and output evidence.
//   - Side effects: isolated normative VM execution.
// - Split-When:
//   - General recurrent arithmetic replay owns the same effects.
// - Merge-When:
//   - Full checksum replay subsumes this projection.
// - Summary:
//   - Authenticate state-dependent two-bit transitions across input cycles.

use std::collections::BTreeSet;
use std::iter::repeat_n;

use malbolge::{
    ProfileMachine, StepOutcome, Termination, TraceInput, current_profile,
    decode_profile_instruction, historical_profile,
};

use super::super::super::super::layout::{
    RelocatedRecurrentMod4Source, ZeroCellSourceError,
    build_relocated_recurrent_mod4_source,
};
use super::relocated_recurrent_reload::reset_operand;
use super::{
    BYTE, CONSTANTS, EOF, EOF_EVEN, EOF_ODD, INITIAL, ONES, check_store, cycle,
    effect, enter, fold, independent_crazy, plus, prev, routing, select, word,
};

const BOOT_BUDGET: usize = 4_200_000;
const TABLE_BASE: u32 = 7_179_192;
const SEED_BASE: u32 = 7_189_500;
const STATE_CONSTANTS: [u32; 3] = [7_175_060, 7_175_062, 7_175_064];
const SCRATCH_CONSTANTS: [u32; 3] = [7_175_070, 7_175_072, 7_175_074];

fn source() -> Result<RelocatedRecurrentMod4Source, String> {
    build_relocated_recurrent_mod4_source(current_profile())
        .map_err(|error| format!("mod4 source: {error:?}"))
}

const fn checksum(state: u8, byte: u8) -> u8 {
    if byte & 1 == 0 {
        state.wrapping_add(byte).wrapping_add(3)
    } else {
        (state ^ byte).wrapping_add(3)
    }
}

fn state_row(state: u8) -> Result<u32, String> {
    plus(
        TABLE_BASE,
        u32::from(state).checked_mul(729).ok_or("state row")?,
    )
}

fn mask(state: u8) -> Result<u32, String> {
    plus(independent_crazy(state_row(state)?, EOF), 364)
}

fn lookup(
    vm: &mut ProfileMachine,
    guest: &RelocatedRecurrentMod4Source,
    pointer: u32,
    next: u8,
) -> Result<u32, String> {
    let base = &guest.capture;
    let next_mask = mask(next)?;
    let seed = plus(
        SEED_BASE,
        u32::from(next).checked_mul(8).ok_or("seed stride")?,
    )?;
    let [first, second] = guest.lookup;
    for (site, (address, value)) in [
        (prev(prev(first)?)?, (guest.state, pointer)),
        (prev(first)?, (plus(pointer, 1)?, prev(seed)?)),
    ] {
        let trace = effect(vm, base, site, b'j')?;
        if trace
            .memory_reads
            .data
            .map(|read| (read.address, read.value))
            != Some((address, value))
        {
            return Err(format!("wrong transition selection: {trace:?}"));
        }
        routing(&trace, base.branch)?;
    }
    let dirty = fold(vm, base, (first, seed), (next_mask, EOF))?;
    let rotation = effect(vm, base, guest.seed_rotate, b'*')?;
    check_store(&rotation, plus(seed, 5)?, EOF, EOF)?;
    let restored = fold(vm, base, (second, seed), (dirty, EOF))?;
    if restored != next_mask || word(vm, seed)? != next_mask {
        return Err("transition seed was not restored".to_owned());
    }
    Ok(restored)
}

fn transition(
    vm: &mut ProfileMachine,
    guest: &RelocatedRecurrentMod4Source,
    (byte, encoded): (u8, u32),
    (prior, next): (u8, u8),
) -> Result<(), String> {
    let base = &guest.capture;
    let [first, second] = guest.load;
    select(vm, base, 7_180_670, 7_182_199)?;
    let load_rotation = effect(vm, base, base.rotate, b'*')?;
    check_store(&load_rotation, 7_175_050, EOF, EOF)?;
    let transformed = fold(vm, base, (first, base.capture), (encoded, EOF))?;
    let pointer =
        fold(vm, base, (first, guest.state), (mask(prior)?, transformed))?;
    if pointer
        != plus(state_row(prior)?, 728)?
            .checked_sub(u32::from(byte))
            .ok_or("index")?
    {
        return Err("incorrect joint state/byte index".to_owned());
    }
    let lookup_rotation = effect(vm, base, base.rotate, b'*')?;
    check_store(&lookup_rotation, 7_175_052, EOF, EOF)?;
    let selected = lookup(vm, guest, pointer, next)?;
    let mut inverse =
        fold(vm, base, (base.crazy, guest.scratch), (ONES, selected))?;
    let expected_inverse = inverse;
    reset_operand(vm, base, (guest.state, pointer), STATE_CONSTANTS)?;
    reset_operand(vm, base, (base.capture, transformed), CONSTANTS)?;
    for (address, site) in
        [7_175_054, 7_175_056].into_iter().zip([first, second])
    {
        let rotation = effect(vm, base, base.rotate, b'*')?;
        check_store(&rotation, address, EOF, EOF)?;
        inverse = fold(vm, base, (site, guest.scratch), (inverse, EOF))?;
    }
    if inverse != expected_inverse {
        return Err("saved next-state inverse lost".to_owned());
    }
    let actual = fold(vm, base, (second, guest.state), (ONES, inverse))?;
    if actual != mask(next)? {
        return Err("wrong committed recurrent state".to_owned());
    }
    reset_operand(vm, base, (guest.scratch, inverse), SCRATCH_CONSTANTS)?;
    select(vm, base, 7_175_090, 7_175_199)?;
    Ok(())
}

fn check_terminal(
    vm: &mut ProfileMachine,
    guest: &RelocatedRecurrentMod4Source,
    class: u32,
    expected: u8,
) -> Result<(), String> {
    let base = &guest.capture;
    let load = effect(vm, base, guest.terminal, b'*')?;
    check_store(&load, plus(class, 2)?, EOF, EOF)?;
    let mut state = fold(
        vm,
        base,
        (plus(guest.terminal, 2)?, guest.state),
        (mask(expected)?, EOF),
    )?;
    if state != plus(state_row(expected)?, 728)? {
        return Err("wrong terminal state decode".to_owned());
    }
    for offset in 0..6u32 {
        let site = plus(
            guest.terminal,
            plus(4, offset.checked_mul(2).ok_or("rotation site")?)?,
        )?;
        let new = plus(
            state.checked_div(3).ok_or("rotation quotient")?,
            state
                .checked_rem(3)
                .and_then(|trit| trit.checked_mul(4_782_969))
                .ok_or("rotation")?,
        )?;
        let rotation = effect(vm, base, site, b'*')?;
        check_store(&rotation, guest.state, state, new)?;
        state = new;
    }
    let output = effect(vm, base, base.output, b'<')?;
    if output.output != Some(expected)
        || output.before.registers.accumulator != state
        || output.input.is_some()
        || output.memory_delta.data.is_some()
    {
        return Err(format!("wrong checksum projection output: {output:?}"));
    }
    let mut record = None;
    let outcome = vm
        .step_traced(&mut |entry| record = Some(*entry))
        .map_err(|error| error.to_string())?;
    let trace = record.ok_or("missing terminal trace")?;
    if outcome != StepOutcome::Terminated(Termination::HaltInstruction)
        || trace.before.registers.code_pointer != base.halt
        || trace.decoded != Some(b'v')
        || trace.input.is_some()
        || trace.output.is_some()
        || trace.memory_delta.data.is_some()
        || word(vm, base.capture)? != EOF
    {
        return Err(format!("wrong physical halt: {trace:?}"));
    }
    Ok(())
}

fn run(
    boot: &ProfileMachine,
    guest: &RelocatedRecurrentMod4Source,
    stream: &[u8],
) -> Result<(), String> {
    let mut vm = boot
        .fork_with_input(stream.to_vec())
        .map_err(|error| error.to_string())?;
    let base = &guest.capture;
    let mut classifier = INITIAL;
    let mut full = 0u8;
    for &byte in stream {
        let prior = full & 3;
        if word(&vm, guest.state)? != mask(prior)?
            || word(&vm, guest.scratch)? != ONES
        {
            return Err("incorrect pre-input persistent state".to_owned());
        }
        let encoded = cycle(
            &mut vm,
            base,
            &mut classifier,
            (TraceInput::Byte(byte), BYTE),
        )?;
        full = checksum(full, byte);
        transition(&mut vm, guest, (byte, encoded), (prior, full & 3))?;
    }
    let class = if stream.len() & 1 == 1 {
        EOF_ODD
    } else {
        EOF_EVEN
    };
    let encoded = cycle(
        &mut vm,
        base,
        &mut classifier,
        (TraceInput::EndOfInput, class),
    )?;
    if encoded != EOF
        || word(&vm, guest.state)? != mask(full & 3)?
        || word(&vm, guest.scratch)? != ONES
        || !vm.output().is_empty()
    {
        return Err("EOF changed state or byte path emitted output".to_owned());
    }
    check_terminal(&mut vm, guest, class, full & 3)?;
    if vm.input_consumed() != stream.len() || vm.output() != [full & 3] {
        return Err("wrong final checksum projection".to_owned());
    }
    Ok(())
}

// Route all 1024 state-byte combinations through one actual recurrent stream.
// Zero decrements the projected state, so at most three setup bytes suffice.
fn transition_stream() -> Vec<u8> {
    let mut stream = Vec::new();
    let mut current = 0u8;
    for prior in 0..4u8 {
        for byte in 0..=255u8 {
            let setup = current.wrapping_sub(prior) & 3;
            stream.extend(repeat_n(0, usize::from(setup)));
            for _ in 0..setup {
                current = checksum(current, 0);
            }
            stream.push(byte);
            current = checksum(current, byte);
        }
    }
    stream
}

#[test]
fn relocated_recurrent_mod4_all_transitions_and_eof() -> Result<(), String> {
    let guest = source()?;
    if guest.capture.source.len() != 4_270_106 {
        return Err("incorrect source extent".to_owned());
    }
    let boot = enter(&guest.capture, BOOT_BUDGET)?;
    let census = transition_stream();
    if census.len() != 2_561 {
        return Err("incorrect census length".to_owned());
    }
    let mut visited = BTreeSet::new();
    let mut full = 0u8;
    for &byte in &census {
        let _: bool = visited.insert((full & 3, byte));
        full = checksum(full, byte);
    }
    if visited.len() != 1_024 {
        return Err("incomplete transition census".to_owned());
    }
    let mut eof_classes = BTreeSet::new();
    for stream in [
        vec![],
        vec![1],
        vec![2],
        vec![2, 3],
        vec![3],
        vec![3, 1],
        vec![0],
        vec![0, 3],
        census,
    ] {
        let state = stream.iter().copied().fold(0, checksum) & 3;
        let _: bool = eof_classes.insert((state, stream.len() & 1));
        run(&boot, &guest, &stream)?;
    }
    if eof_classes.len() != 8 {
        return Err("incomplete EOF census".to_owned());
    }
    Ok(())
}

#[test]
fn relocated_recurrent_mod4_is_checksum_projection() {
    for state in 0..=255u8 {
        for byte in 0..=255u8 {
            assert_eq!(
                checksum(state, byte) & 3,
                checksum(state & 3, byte) & 3
            );
        }
    }
}

#[test]
fn relocated_recurrent_mod4_refuses_other_profile() {
    assert_eq!(
        build_relocated_recurrent_mod4_source(historical_profile()),
        Err(ZeroCellSourceError::UnsupportedProfile)
    );
}

#[test]
fn relocated_recurrent_mod4_omitted_effects_refuse() -> Result<(), String> {
    let guest = source()?;
    let [_, restore] = guest.lookup;
    let [_, commit] = guest.load;
    for site in [
        restore,
        commit,
        plus(guest.terminal, 4)?,
        guest.capture.output,
    ] {
        let mut modified = guest.clone();
        let noop = (33..=126u8)
            .find(|byte| {
                decode_profile_instruction(u32::from(*byte), site) == Some(b'o')
            })
            .ok_or("missing noop")?;
        *modified
            .capture
            .source
            .get_mut(usize::try_from(site).map_err(|error| error.to_string())?)
            .ok_or("missing mutation site")? = noop;
        let boot = enter(&modified.capture, BOOT_BUDGET)?;
        if run(&boot, &modified, &[0, 255]).is_ok() {
            return Err(format!("accepted omitted state effect C{site}"));
        }
    }
    Ok(())
}
