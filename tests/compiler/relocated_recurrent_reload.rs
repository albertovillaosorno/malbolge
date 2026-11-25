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
//   - Independent physical recovery and byte-output replay.
// - Must-Not:
//   - Claim source-frame admission or C checksum execution.
// - Allows:
//   - Inputs: graphical source, binary streams and independent ternary oracle.
//   - Outputs: actual input, classifier, reset, branch and terminal effects.
//   - Side effects: isolated normative VM execution.
// - Split-When:
//   - General recurrent access replay owns these checks.
// - Merge-When:
//   - Complete source checksum execution subsumes this witness.
// - Summary:
//   - Prove the guest recovers every byte after its dirty EOF classifier.

use malbolge::{
    ProfileMachine, TraceInput, current_profile, decode_profile_instruction,
    historical_profile,
};

use super::super::super::super::layout::{
    RelocatedRecurrentCaptureSource, RelocatedRecurrentReloadSource,
    ZeroCellSourceError, build_relocated_recurrent_reload_source,
};
use super::{
    BYTE, CONSTANTS, EOF, EOF_EVEN, EOF_ODD, INITIAL, ONES, check_store, cycle,
    effect, enter, fold, select, stop, word,
};

const RELOAD_BOOT_BUDGET: usize = 5_800_000;
const LOAD_CONSTANTS: [u32; 2] = [7_175_050, 7_175_052];
const RAW_CONSTANTS: [u32; 3] = [7_175_060, 7_175_062, 7_175_064];

fn reload_source() -> Result<RelocatedRecurrentReloadSource, String> {
    build_relocated_recurrent_reload_source(current_profile())
        .map_err(|error| format!("reload source: {error:?}"))
}

fn reload_word(
    vm: &mut ProfileMachine,
    guest: &RelocatedRecurrentReloadSource,
    encoded: u32,
) -> Result<u32, String> {
    let base = &guest.capture;
    select(vm, base, 7_180_670, 7_180_999)?;
    let mut current = encoded;
    for (site, address) in guest.load.into_iter().zip(LOAD_CONSTANTS) {
        let trace = effect(vm, base, base.rotate, b'*')?;
        check_store(&trace, address, EOF, EOF)?;
        current = fold(vm, base, (site, base.capture), (current, EOF))?;
    }
    if current != encoded || word(vm, base.capture)? != encoded {
        return Err("reversible guest reload lost capture".to_owned());
    }
    if word(vm, guest.raw)? != ONES {
        return Err("raw slot not reset".to_owned());
    }
    fold(vm, base, (base.crazy, guest.raw), (ONES, encoded))
}

fn reset_operand(
    vm: &mut ProfileMachine,
    guest: &RelocatedRecurrentCaptureSource,
    operand: (u32, u32),
    constants: [u32; 3],
) -> Result<(), String> {
    let (target, mut current) = operand;
    for ((site, address), constant) in
        guest.reset.into_iter().zip(constants).zip([ONES, EOF, 0])
    {
        let trace = effect(vm, guest, guest.rotate, b'*')?;
        check_store(&trace, address, constant, constant)?;
        current = fold(vm, guest, (site, target), (current, constant))?;
    }
    if current != ONES || word(vm, target)? != ONES {
        return Err(format!("dirty reload reset M{target} failed"));
    }
    Ok(())
}

fn reload_byte(
    vm: &mut ProfileMachine,
    guest: &RelocatedRecurrentReloadSource,
    byte: u8,
    encoded: u32,
) -> Result<(), String> {
    let raw = reload_word(vm, guest, encoded)?;
    if raw != u32::from(byte)
        || word(vm, guest.raw)? != raw
        || word(vm, guest.capture.capture)? != encoded
    {
        return Err("guest did not recover raw byte".to_owned());
    }
    let base = &guest.capture;
    let output = effect(vm, base, guest.echo, b'<')?;
    if output.output != Some(byte)
        || output.before.registers.accumulator != raw
        || output.after.registers.accumulator != raw
        || output.input.is_some()
        || output.memory_delta.data.is_some()
    {
        return Err(format!("missing physical reloaded byte: {output:?}"));
    }
    reset_operand(vm, base, (base.capture, encoded), CONSTANTS)?;
    reset_operand(vm, base, (guest.raw, raw), RAW_CONSTANTS)?;
    select(vm, base, 7_175_090, 7_175_199)?;
    Ok(())
}

fn run_reload(
    boot: &ProfileMachine,
    guest: &RelocatedRecurrentReloadSource,
    stream: &[u8],
) -> Result<(), String> {
    let mut vm = boot
        .fork_with_input(stream.to_vec())
        .map_err(|error| error.to_string())?;
    let base = &guest.capture;
    let mut state = INITIAL;
    for &byte in stream {
        let encoded =
            cycle(&mut vm, base, &mut state, (TraceInput::Byte(byte), BYTE))?;
        reload_byte(&mut vm, guest, byte, encoded)?;
    }
    let odd = stream.len() & 1 == 1;
    let class = if odd {
        EOF_ODD
    } else {
        EOF_EVEN
    };
    let encoded =
        cycle(&mut vm, base, &mut state, (TraceInput::EndOfInput, class))?;
    if encoded != EOF || word(&vm, guest.raw)? != ONES {
        return Err("EOF modified raw slot".to_owned());
    }
    stop(&mut vm, base, class, u8::from(odd))?;
    let mut expected = stream.to_vec();
    expected.push(u8::from(odd));
    if vm.input_consumed() != stream.len() || vm.output() != expected {
        return Err("wrong reloaded stream I/O".to_owned());
    }
    Ok(())
}

#[test]
fn relocated_recurrent_reload_all_bytes_and_eof() -> Result<(), String> {
    let guest = reload_source()?;
    if guest.capture.source.len() != 5_920_182 {
        return Err("recurrent reload image size regressed".to_owned());
    }
    let boot = enter(&guest.capture, RELOAD_BOOT_BUDGET)?;
    for stream in [
        vec![],
        vec![255],
        vec![0, 255],
        (0..=255).collect(),
        (0..=255).rev().chain([42]).collect(),
    ] {
        run_reload(&boot, &guest, &stream)?;
    }
    Ok(())
}

#[test]
fn relocated_recurrent_reload_omitted_load_and_echo_refuse()
-> Result<(), String> {
    let guest = reload_source()?;
    for site in guest.load.into_iter().chain([guest.echo]) {
        let mut modified = guest.clone();
        let noop = (33..=126u8)
            .find(|byte| {
                decode_profile_instruction(u32::from(*byte), site) == Some(b'o')
            })
            .ok_or("missing canonical noop")?;
        *modified
            .capture
            .source
            .get_mut(usize::try_from(site).map_err(|error| error.to_string())?)
            .ok_or("missing reload cell")? = noop;
        let boot = enter(&modified.capture, RELOAD_BOOT_BUDGET)?;
        if run_reload(&boot, &modified, &[0, 255]).is_ok() {
            return Err(format!("accepted omitted reload effect C{site}"));
        }
    }
    Ok(())
}

#[test]
fn relocated_recurrent_reload_refuses_other_profile() {
    assert_eq!(
        build_relocated_recurrent_reload_source(historical_profile()),
        Err(ZeroCellSourceError::UnsupportedProfile)
    );
}
