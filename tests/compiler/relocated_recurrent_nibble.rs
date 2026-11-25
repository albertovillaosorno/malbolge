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
//   - Independent replay of the recurrent four-bit checksum state.
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
//   - Authenticate factorized four-bit transitions across input cycles.

use std::collections::BTreeSet;

use malbolge::{
    ProfileMachine, StepOutcome, Termination, TraceInput, current_profile,
    decode_profile_instruction, historical_profile,
};

use super::super::super::super::layout::{
    RelocatedRecurrentProjectionSource, ZeroCellSourceError,
    build_relocated_recurrent_mod32_source,
    build_relocated_recurrent_nibble_source,
};
use super::{
    BYTE, CONSTANTS, EOF, EOF_EVEN, EOF_ODD, INITIAL, ONES, check_store, cycle,
    effect, enter, fold, independent_crazy, plus, prev, routing, select, word,
};

const BOOT_BUDGET: usize = 3_950_000;
const MOD32_BOOT_BUDGET: usize = 5_500_000;
const RAW_TABLE: u32 = 7_195_959;
const RAW_SEEDS: u32 = 7_197_000;
#[derive(Clone, Copy)]
struct Projection {
    mask: u8,
    row: u32,
    state_table: u32,
    state_seeds: u32,
    rotations: u32,
}
const NIBBLE: Projection = Projection {
    mask: 15,
    row: 27,
    state_table: 7_199_010,
    state_seeds: 7_200_000,
    rotations: 3,
};
const MOD32: Projection = Projection {
    mask: 31,
    row: 81,
    state_table: 7_207_056,
    state_seeds: 7_209_700,
    rotations: 4,
};
const STATE_CONSTANTS: [u32; 3] = [7_175_060, 7_175_062, 7_175_064];
const SCRATCH_CONSTANTS: [u32; 3] = [7_175_070, 7_175_072, 7_175_074];
const POINTER_CONSTANTS: [u32; 3] = [7_175_150, 7_175_152, 7_175_154];

type RawProjection = (u32, u32, u32);
type StackEntry = (u8, Option<u8>);

fn source() -> Result<RelocatedRecurrentProjectionSource, String> {
    build_relocated_recurrent_nibble_source(current_profile())
        .map_err(|error| format!("nibble source: {error:?}"))
}

const fn checksum(state: u8, byte: u8) -> u8 {
    if byte & 1 == 0 {
        state.wrapping_add(byte).wrapping_add(3)
    } else {
        (state ^ byte).wrapping_add(3)
    }
}

fn state_row(state: u8, projection: Projection) -> Result<u32, String> {
    plus(
        projection.state_table,
        u32::from(state)
            .checked_mul(projection.row)
            .ok_or("state row")?,
    )
}

fn mask(state: u8, projection: Projection) -> Result<u32, String> {
    plus(
        independent_crazy(state_row(state, projection)?, EOF),
        projection
            .row
            .checked_sub(1)
            .ok_or("row")?
            .checked_div(2)
            .ok_or("half row")?,
    )
}

fn raw_mask() -> Result<u32, String> {
    plus(independent_crazy(RAW_TABLE, EOF), 364)
}

fn seed_address(base: u32, state: u8) -> Result<u32, String> {
    plus(base, u32::from(state).checked_mul(8).ok_or("seed stride")?)
}

fn immutable_prefix(mut value: u32) -> Result<u32, String> {
    let mut prefix = 0u32;
    for place in 0..15 {
        if value.rem_euclid(3) == 0 {
            prefix = plus(
                prefix,
                3u32.pow(place).checked_mul(2).ok_or("prefix trit")?,
            )?;
        }
        value = value.div_euclid(3);
    }
    Ok(prefix)
}

fn lookup(
    vm: &mut ProfileMachine,
    guest: &RelocatedRecurrentProjectionSource,
    (sites, operand): ([u32; 2], u32),
    (pointer, seed, expected): (u32, u32, u32),
) -> Result<u32, String> {
    let base = &guest.capture;
    let [first, second] = sites;
    for (site, (address, value)) in [
        (prev(prev(first)?)?, (operand, pointer)),
        (prev(first)?, (plus(pointer, 1)?, prev(seed)?)),
    ] {
        let trace = effect(vm, base, site, b'j')?;
        if trace
            .memory_reads
            .data
            .map(|read| (read.address, read.value))
            != Some((address, value))
        {
            return Err(format!("wrong factorized selection: {trace:?}"));
        }
        routing(&trace, base.branch)?;
    }
    let prefix = immutable_prefix(expected)?;
    let first_value = fold(vm, base, (first, seed), (prefix, ONES))?;
    let value = fold(vm, base, (second, plus(seed, 1)?), (expected, prefix))?;
    if first_value != prefix
        || value != expected
        || word(vm, seed)? != prefix
        || word(vm, plus(seed, 1)?)? != expected
    {
        return Err("factorized seed was mutated".to_owned());
    }
    Ok(value)
}

fn rotate_constant(
    vm: &mut ProfileMachine,
    guest: &RelocatedRecurrentProjectionSource,
    address: u32,
    value: u32,
) -> Result<(), String> {
    let rotation = effect(vm, &guest.capture, guest.capture.rotate, b'*')?;
    check_store(&rotation, address, value, value)
}

fn raw_projection(
    vm: &mut ProfileMachine,
    guest: &RelocatedRecurrentProjectionSource,
    (byte, encoded): (u8, u32),
    projection: Projection,
) -> Result<RawProjection, String> {
    let base = &guest.capture;
    let [first, _] = guest.load;
    select(vm, base, 7_180_670, 7_182_199)?;
    rotate_constant(vm, guest, 7_175_050, EOF)?;
    let transformed = fold(vm, base, (first, base.capture), (encoded, EOF))?;
    let pointer =
        fold(vm, base, (first, guest.pointer), (raw_mask()?, transformed))?;
    let expected_pointer = plus(RAW_TABLE, 728)?
        .checked_sub(u32::from(byte))
        .ok_or("raw index")?;
    if pointer != expected_pointer {
        return Err("wrong raw-byte index".to_owned());
    }
    rotate_constant(vm, guest, 7_175_058, ONES)?;
    let nibble = byte & projection.mask;
    let projected =
        independent_crazy(independent_crazy(ONES, u32::from(nibble)), EOF);
    let actual = lookup(
        vm,
        guest,
        (guest.raw_lookup, guest.pointer),
        (pointer, seed_address(RAW_SEEDS, nibble)?, projected),
    )?;
    Ok((transformed, pointer, actual))
}

fn reset_operand(
    vm: &mut ProfileMachine,
    base: &super::RelocatedRecurrentCaptureSource,
    (address, dirty): (u32, u32),
    [ones, _, _]: [u32; 3],
) -> Result<(), String> {
    let rotation = effect(vm, base, base.rotate, b'*')?;
    check_store(&rotation, ones, ONES, ONES)?;
    let [first, second, _] = base.reset;
    let middle = fold(vm, base, (first, address), (dirty, ONES))?;
    let restored = fold(vm, base, (second, address), (middle, middle))?;
    if restored != ONES || word(vm, address)? != ONES {
        return Err("two-fold dirty reset failed".to_owned());
    }
    Ok(())
}

fn restore(
    vm: &mut ProfileMachine,
    guest: &RelocatedRecurrentProjectionSource,
    (seed, destination, inverse): (u32, u32, u32),
    constants: [u32; 2],
) -> Result<u32, String> {
    let base = &guest.capture;
    let mut value = inverse;
    for (address, site) in constants.into_iter().zip(guest.load) {
        rotate_constant(vm, guest, address, EOF)?;
        value = fold(vm, base, (site, seed), (value, EOF))?;
    }
    if value != inverse {
        return Err("saved inverse lost".to_owned());
    }
    let [_, second] = guest.load;
    fold(vm, base, (second, destination), (ONES, value))
}

fn transition(
    vm: &mut ProfileMachine,
    guest: &RelocatedRecurrentProjectionSource,
    (byte, encoded): (u8, u32),
    (prior, next): (u8, u8),
    projection: Projection,
) -> Result<(), String> {
    let base = &guest.capture;
    let [first, _] = guest.load;
    let (transformed, raw_pointer, projected) =
        raw_projection(vm, guest, (byte, encoded), projection)?;
    let pointer = fold(
        vm,
        base,
        (first, guest.state),
        (mask(prior, projection)?, projected),
    )?;
    if pointer
        != plus(
            state_row(prior, projection)?,
            projection.row.checked_sub(1).ok_or("row")?,
        )?
        .checked_sub(u32::from(byte & projection.mask))
        .ok_or("state index")?
    {
        return Err("wrong nibble transition index".to_owned());
    }
    rotate_constant(vm, guest, 7_175_176, ONES)?;
    let selected = lookup(
        vm,
        guest,
        (guest.lookup, guest.state),
        (
            pointer,
            seed_address(projection.state_seeds, next)?,
            mask(next, projection)?,
        ),
    )?;
    let inverse =
        fold(vm, base, (base.crazy, guest.scratch), (ONES, selected))?;
    reset_operand(vm, base, (guest.state, pointer), STATE_CONSTANTS)?;
    reset_operand(vm, base, (base.capture, transformed), CONSTANTS)?;
    let actual = restore(vm, guest, (guest.scratch, guest.state, inverse), [
        7_175_054, 7_175_056,
    ])?;
    if actual != mask(next, projection)? {
        return Err("wrong committed nibble".to_owned());
    }
    reset_operand(vm, base, (guest.scratch, inverse), SCRATCH_CONSTANTS)?;
    reset_operand(vm, base, (guest.pointer, raw_pointer), POINTER_CONSTANTS)?;
    let inverse = independent_crazy(ONES, raw_mask()?);
    let prefix = immutable_prefix(inverse)?;
    let loaded_prefix =
        fold(vm, base, (base.crazy, 7_175_164), (prefix, ONES))?;
    let loaded = fold(vm, base, (base.crazy, 7_175_160), (inverse, prefix))?;
    if loaded_prefix != prefix || loaded != inverse {
        return Err("immutable raw mask read failed".to_owned());
    }
    let restored = fold(vm, base, (base.crazy, guest.pointer), (ONES, loaded))?;
    if restored != raw_mask()? {
        return Err("wrong restored raw mask".to_owned());
    }
    select(vm, base, 7_175_090, 7_175_199)?;
    Ok(())
}

fn check_terminal(
    vm: &mut ProfileMachine,
    guest: &RelocatedRecurrentProjectionSource,
    class: u32,
    expected: u8,
    projection: Projection,
) -> Result<(), String> {
    let base = &guest.capture;
    let load = effect(vm, base, guest.terminal, b'*')?;
    check_store(&load, plus(class, 2)?, EOF, EOF)?;
    let mut state = fold(
        vm,
        base,
        (plus(guest.terminal, 2)?, guest.state),
        (mask(expected, projection)?, EOF),
    )?;
    if state
        != plus(
            state_row(expected, projection)?,
            projection.row.checked_sub(1).ok_or("row")?,
        )?
    {
        return Err("wrong terminal state decode".to_owned());
    }
    for offset in 0..projection.rotations {
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
    guest: &RelocatedRecurrentProjectionSource,
    stream: &[u8],
    projection: Projection,
) -> Result<(), String> {
    let mut vm = boot
        .fork_with_input(stream.to_vec())
        .map_err(|error| error.to_string())?;
    let base = &guest.capture;
    let mut classifier = INITIAL;
    let mut full = 0u8;
    for &byte in stream {
        let prior = full & projection.mask;
        if word(&vm, guest.state)? != mask(prior, projection)?
            || word(&vm, guest.scratch)? != ONES
            || word(&vm, guest.pointer)? != raw_mask()?
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
        transition(
            &mut vm,
            guest,
            (byte, encoded),
            (prior, full & projection.mask),
            projection,
        )?;
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
        || word(&vm, guest.state)? != mask(full & projection.mask, projection)?
        || word(&vm, guest.scratch)? != ONES
        || word(&vm, guest.pointer)? != raw_mask()?
        || !vm.output().is_empty()
    {
        return Err("EOF changed state or byte path emitted output".to_owned());
    }
    check_terminal(&mut vm, guest, class, full & projection.mask, projection)?;
    if vm.input_consumed() != stream.len()
        || vm.output() != [full & projection.mask]
    {
        return Err("wrong final checksum projection".to_owned());
    }
    Ok(())
}

// All projected-state/raw-byte edges are balanced: each byte acts as a
// permutation on the states. Build an Euler circuit and check its census.
fn transition_stream(projection: Projection) -> Result<Vec<u8>, String> {
    let count = usize::from(projection.mask)
        .checked_add(1)
        .ok_or("state count")?;
    let mut next_byte = vec![0u16; count];
    let mut stack = vec![(0u8, None)];
    let mut stream = Vec::new();
    while let Some((state, incoming)) = stack.last().copied() {
        let counter = next_byte
            .get_mut(usize::from(state))
            .ok_or("state counter")?;
        if *counter <= 255 {
            let byte =
                u8::try_from(*counter).map_err(|error| error.to_string())?;
            *counter = counter.checked_add(1).ok_or("counter overflow")?;
            stack.push((checksum(state, byte) & projection.mask, Some(byte)));
        } else {
            let _: Option<StackEntry> = stack.pop();
            if let Some(byte) = incoming {
                stream.push(byte);
            }
        }
    }
    stream.reverse();
    Ok(stream)
}

#[test]
fn relocated_recurrent_nibble_all_transitions_and_eof() -> Result<(), String> {
    let guest = source()?;
    if guest.capture.source.len() != 4_012_170 {
        return Err("incorrect source extent".to_owned());
    }
    let boot = enter(&guest.capture, BOOT_BUDGET)?;
    if word(&boot, 7_174_485)? != 7_175_600 {
        return Err("incorrect extra seed anchor".to_owned());
    }
    if word(&boot, 7_174_469)? != ONES {
        return Err("incorrect immutable-seed initial accumulator".to_owned());
    }
    for index in 0..10 {
        let address =
            plus(7_174_611, 4u32.checked_mul(index).ok_or("pair stride")?)?;
        let prefix = word(&boot, address)?;
        let inverse = word(&boot, plus(address, 2)?)?;
        if independent_crazy(prefix, ONES) != prefix
            || independent_crazy(inverse, prefix) != inverse
        {
            return Err("unstable immutable seed pair".to_owned());
        }
    }
    let census = transition_stream(NIBBLE)?;
    let mut visited = BTreeSet::new();
    let mut state = 0u8;
    for &byte in &census {
        let _: bool = visited.insert((state & 15, byte));
        state = checksum(state, byte);
    }
    if census.len() != 4_096 || visited.len() != 4_096 {
        return Err("incomplete raw/state transition census".to_owned());
    }
    run(&boot, &guest, &census, NIBBLE)?;
    run(&boot, &guest, &[], NIBBLE)?;
    for expected in 0..16u8 {
        let odd = [expected.wrapping_sub(3) & 15];
        let second = (0..16u8)
            .find(|byte| checksum(3, *byte) & 15 == expected)
            .ok_or("no even EOF witness")?;
        let even = [0, second];
        run(&boot, &guest, &odd, NIBBLE)?;
        run(&boot, &guest, &even, NIBBLE)?;
    }
    Ok(())
}

#[test]
fn relocated_recurrent_nibble_immutable_read_and_reset_algebra()
-> Result<(), String> {
    // All possible single trits, repeated across a complete N15 word.
    // The crazy operation acts independently at every trit position.
    for value in [0, ONES, EOF] {
        let prefix = immutable_prefix(value)?;
        assert_eq!(independent_crazy(prefix, ONES), prefix);
        assert_eq!(independent_crazy(value, prefix), value);
        let middle = independent_crazy(value, ONES);
        assert_eq!(independent_crazy(middle, middle), ONES);
    }
    Ok(())
}

#[test]
fn relocated_recurrent_nibble_is_checksum_projection() {
    for state in 0..=255u8 {
        for byte in 0..=255u8 {
            for projection in [NIBBLE, MOD32] {
                assert_eq!(
                    checksum(state, byte) & projection.mask,
                    checksum(state & projection.mask, byte) & projection.mask
                );
            }
        }
    }
}

#[test]
fn relocated_recurrent_nibble_refuses_other_profile() {
    assert_eq!(
        build_relocated_recurrent_nibble_source(historical_profile()),
        Err(ZeroCellSourceError::UnsupportedProfile)
    );
    assert_eq!(
        build_relocated_recurrent_mod32_source(historical_profile()),
        Err(ZeroCellSourceError::UnsupportedProfile)
    );
}

#[test]
fn relocated_recurrent_nibble_omitted_effects_refuse() -> Result<(), String> {
    omitted_effects(&source()?, NIBBLE, BOOT_BUDGET)
}

#[test]
fn relocated_recurrent_mod32_omitted_effects_refuse() -> Result<(), String> {
    let guest = build_relocated_recurrent_mod32_source(current_profile())
        .map_err(|error| format!("mod32 source: {error:?}"))?;
    omitted_effects(&guest, MOD32, MOD32_BOOT_BUDGET)
}

fn omitted_effects(
    guest: &RelocatedRecurrentProjectionSource,
    projection: Projection,
    budget: usize,
) -> Result<(), String> {
    let [prefix, value] = guest.lookup;
    let [raw_prefix, raw_value] = guest.raw_lookup;
    let [_, reset, _] = guest.capture.reset;
    let [_, commit] = guest.load;
    for site in [
        raw_prefix,
        raw_value,
        prefix,
        value,
        reset,
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
        let boot = enter(&modified.capture, budget)?;
        if run(&boot, &modified, &[0, 255], projection).is_ok() {
            return Err(format!("accepted omitted state effect C{site}"));
        }
    }
    Ok(())
}

#[test]
fn relocated_recurrent_mod32_all_transitions_and_eof() -> Result<(), String> {
    let guest = build_relocated_recurrent_mod32_source(current_profile())
        .map_err(|error| format!("mod32 source: {error:?}"))?;
    let boot = enter(&guest.capture, MOD32_BOOT_BUDGET)?;
    if word(&boot, 7_174_475)? != 7_211_000
        || guest.capture.source.len() != 5_610_170
    {
        return Err("incorrect five-bit geometry".to_owned());
    }
    let census = transition_stream(MOD32)?;
    let mut visited = BTreeSet::new();
    let mut state = 0u8;
    for &byte in &census {
        let _: bool = visited.insert((state & 31, byte));
        state = checksum(state, byte);
    }
    if census.len() != 8_192 || visited.len() != 8_192 {
        return Err("incomplete five-bit transition census".to_owned());
    }
    run(&boot, &guest, &census, MOD32)?;
    run(&boot, &guest, &[], MOD32)?;
    for expected in 0..32u8 {
        let odd = [expected.wrapping_sub(3) & 31];
        let second = (0..32u8)
            .find(|byte| checksum(3, *byte) & 31 == expected)
            .ok_or("no five-bit even EOF witness")?;
        run(&boot, &guest, &odd, MOD32)?;
        run(&boot, &guest, &[0, second], MOD32)?;
    }
    Ok(())
}
