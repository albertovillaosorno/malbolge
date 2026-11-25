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
//   - Independent physical replay of recurrent indexed word access.
// - Must-Not:
//   - Claim source-frame admission or complete checksum execution.
// - Allows:
//   - Inputs: graphical source and an independent nibble oracle.
//   - Outputs: actual data selection, seed restoration and guest output.
//   - Side effects: isolated normative VM execution.
// - Split-When:
//   - General indexed word replay owns the same effects.
// - Merge-When:
//   - Complete recurrent arithmetic supersedes this witness.
// - Summary:
//   - Authenticate an input-dependent immutable table lookup across cycles.

use malbolge::{
    ProfileMachine, TraceInput, current_profile, decode_profile_instruction,
    historical_profile,
};

use super::super::super::super::layout::{
    RelocatedRecurrentIndexedSource, ZeroCellSourceError,
    build_relocated_recurrent_indexed_source,
};
use super::relocated_recurrent_reload::reset_operand;
use super::{
    BYTE, CONSTANTS, EOF, EOF_EVEN, EOF_ODD, INITIAL, ONES, check_store, cycle,
    effect, enter, fold, plus, prev, routing, select, stop, word,
};

const BOOT_BUDGET: usize = 3_600_000;
const TABLE_END: u32 = 7_185_024;
const SEED_BASE: u32 = 7_185_500;
const SEED_STRIDE: u32 = 8;
const MASK_SEED: u32 = 7_175_120;
const POINTER_CONSTANTS: [u32; 3] = [7_175_060, 7_175_062, 7_175_064];

fn source() -> Result<RelocatedRecurrentIndexedSource, String> {
    build_relocated_recurrent_indexed_source(current_profile())
        .map_err(|error| format!("indexed source: {error:?}"))
}

fn lookup(
    vm: &mut ProfileMachine,
    guest: &RelocatedRecurrentIndexedSource,
    byte: u8,
    pointer: u32,
) -> Result<(), String> {
    let base = &guest.capture;
    let nibble = u32::from(byte >> 4);
    let seed = plus(
        SEED_BASE,
        nibble.checked_mul(SEED_STRIDE).ok_or("seed stride")?,
    )?;
    let table = TABLE_END.checked_sub(u32::from(byte)).ok_or("index")?;
    let [first, second] = guest.lookup;
    for (site, (address, value)) in [
        (prev(prev(first)?)?, (guest.pointer, pointer)),
        (prev(first)?, (table, prev(seed)?)),
    ] {
        let trace = effect(vm, base, site, b'j')?;
        if trace
            .memory_reads
            .data
            .map(|read| (read.address, read.value))
            != Some((address, value))
        {
            return Err(format!("incorrect indexed selection: {trace:?}"));
        }
        routing(&trace, base.branch)?;
    }
    let dirty = fold(vm, base, (first, seed), (nibble, EOF))?;
    let rotation = effect(vm, base, guest.seed_rotate, b'*')?;
    check_store(&rotation, plus(seed, 5)?, EOF, EOF)?;
    let restored = fold(vm, base, (second, seed), (dirty, EOF))?;
    if restored != nibble || word(vm, seed)? != nibble {
        return Err("indexed seed not restored".to_owned());
    }
    let output = effect(vm, base, guest.echo, b'<')?;
    if output.output != Some(byte >> 4)
        || output.before.registers.accumulator != nibble
        || output.input.is_some()
        || output.memory_delta.data.is_some()
    {
        return Err(format!("incorrect indexed output: {output:?}"));
    }
    Ok(())
}

fn restore_mask(
    vm: &mut ProfileMachine,
    guest: &RelocatedRecurrentIndexedSource,
) -> Result<(), String> {
    let base = &guest.capture;
    let seed = super::independent_crazy(ONES, guest.pointer_mask);
    let mut current = seed;
    for (address, site) in [7_175_054, 7_175_056]
        .into_iter()
        .zip([base.crazy, guest.load])
    {
        let rotation = effect(vm, base, base.rotate, b'*')?;
        check_store(&rotation, address, EOF, EOF)?;
        current = fold(vm, base, (site, MASK_SEED), (current, EOF))?;
    }
    if current != seed || word(vm, MASK_SEED)? != seed {
        return Err("pointer seed not restored".to_owned());
    }
    let restored = fold(vm, base, (guest.load, guest.pointer), (ONES, seed))?;
    if restored != guest.pointer_mask {
        return Err("pointer mask not restored".to_owned());
    }
    Ok(())
}

fn byte_lookup(
    vm: &mut ProfileMachine,
    guest: &RelocatedRecurrentIndexedSource,
    byte: u8,
    encoded: u32,
) -> Result<(), String> {
    let base = &guest.capture;
    select(vm, base, 7_180_670, 7_180_999)?;
    let rotation = effect(vm, base, base.rotate, b'*')?;
    check_store(&rotation, 7_175_050, EOF, EOF)?;
    let transformed =
        fold(vm, base, (guest.load, base.capture), (encoded, EOF))?;
    let pointer = fold(
        vm,
        base,
        (base.crazy, guest.pointer),
        (guest.pointer_mask, transformed),
    )?;
    if pointer
        != TABLE_END
            .checked_sub(1)
            .and_then(|value| value.checked_sub(u32::from(byte)))
            .ok_or("pointer")?
    {
        return Err("incorrect complemented nibble pointer".to_owned());
    }
    let rotation = effect(vm, base, base.rotate, b'*')?;
    check_store(&rotation, 7_175_052, EOF, EOF)?;
    lookup(vm, guest, byte, pointer)?;
    reset_operand(vm, base, (base.capture, transformed), CONSTANTS)?;
    reset_operand(vm, base, (guest.pointer, pointer), POINTER_CONSTANTS)?;
    restore_mask(vm, guest)?;
    select(vm, base, 7_175_090, 7_175_199)?;
    Ok(())
}

fn run(
    boot: &ProfileMachine,
    guest: &RelocatedRecurrentIndexedSource,
    stream: &[u8],
) -> Result<(), String> {
    let mut vm = boot
        .fork_with_input(stream.to_vec())
        .map_err(|error| error.to_string())?;
    let base = &guest.capture;
    let mut state = INITIAL;
    if word(&vm, guest.pointer)? != guest.pointer_mask {
        return Err("incorrect initial pointer mask".to_owned());
    }
    for &byte in stream {
        let encoded =
            cycle(&mut vm, base, &mut state, (TraceInput::Byte(byte), BYTE))?;
        byte_lookup(&mut vm, guest, byte, encoded)?;
    }
    let odd = stream.len() & 1 == 1;
    let class = if odd {
        EOF_ODD
    } else {
        EOF_EVEN
    };
    let _ = cycle(&mut vm, base, &mut state, (TraceInput::EndOfInput, class))?;
    if word(&vm, guest.pointer)? != guest.pointer_mask {
        return Err("EOF touched pointer state".to_owned());
    }
    stop(&mut vm, base, class, u8::from(odd))?;
    let expected = stream
        .iter()
        .map(|byte| byte >> 4)
        .chain([u8::from(odd)])
        .collect::<Vec<_>>();
    if vm.input_consumed() != stream.len() || vm.output() != expected {
        return Err("incorrect indexed stream output".to_owned());
    }
    Ok(())
}

#[test]
fn relocated_recurrent_indexed_all_bytes_and_eof() -> Result<(), String> {
    let guest = source()?;
    let boot = enter(&guest.capture, BOOT_BUDGET)?;
    for stream in [
        vec![],
        vec![255],
        vec![0, 16, 31, 0],
        (0..=255).collect(),
        (0..=255).rev().chain([43]).collect(),
    ] {
        run(&boot, &guest, &stream)?;
    }
    Ok(())
}

#[test]
fn relocated_recurrent_indexed_refuses_other_profile() {
    assert_eq!(
        build_relocated_recurrent_indexed_source(historical_profile()),
        Err(ZeroCellSourceError::UnsupportedProfile)
    );
}

#[test]
fn relocated_recurrent_indexed_omitted_restore_refuses() -> Result<(), String> {
    let mut guest = source()?;
    let [_, site] = guest.lookup;
    let noop = (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), site) == Some(b'o')
        })
        .ok_or("missing noop")?;
    *guest
        .capture
        .source
        .get_mut(usize::try_from(site).map_err(|error| error.to_string())?)
        .ok_or("missing restore site")? = noop;
    let boot = enter(&guest.capture, BOOT_BUDGET)?;
    if run(&boot, &guest, &[255, 255]).is_ok() {
        return Err("accepted omitted indexed restore".to_owned());
    }
    Ok(())
}
