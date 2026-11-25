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
//   - Independent recurrent parity selection and state replay.
// - Must-Not:
//   - Claim source-frame admission or complete C checksum execution.
// - Allows:
//   - Inputs: graphical source and independent binary stream oracle.
//   - Outputs: actual physical branch, arithmetic, reset and EOF effects.
//   - Side effects: isolated normative VM execution.
// - Split-When:
//   - General recurrent access replay owns these checks.
// - Merge-When:
//   - Complete source checksum execution subsumes this witness.
// - Summary:
//   - Authenticate every parity-selected mutable guest transition.

use malbolge::{
    ProfileMachine, StepOutcome, Termination, TraceInput, current_profile,
    decode_profile_instruction, historical_profile,
};

use super::super::super::super::layout::{
    RelocatedRecurrentParitySource, ZeroCellSourceError,
    build_relocated_recurrent_parity_source,
};
use super::relocated_recurrent_reload::reset_operand;
use super::{
    BYTE, CONSTANTS, EOF, EOF_EVEN, EOF_ODD, INITIAL, ONES, check_store, cycle,
    effect, enter, fold, plus, prev, routing, select, word,
};

const BOOT_BUDGET: usize = 6_400_000;
const POINTER_CONSTANTS: [u32; 3] = [7_175_060, 7_175_062, 7_175_064];

fn source() -> Result<RelocatedRecurrentParitySource, String> {
    build_relocated_recurrent_parity_source(current_profile())
        .map_err(|error| format!("parity source: {error:?}"))
}

fn parity_byte(
    vm: &mut ProfileMachine,
    guest: &RelocatedRecurrentParitySource,
    byte: u8,
    encoded: u32,
    parity: &mut u32,
) -> Result<(), String> {
    let base = &guest.capture;
    select(vm, base, 7_180_670, 7_180_999)?;
    let trace = effect(vm, base, base.rotate, b'*')?;
    check_store(&trace, 7_175_050, EOF, EOF)?;
    let transformed =
        fold(vm, base, (guest.load, base.capture), (encoded, EOF))?;
    let pointer =
        fold(vm, base, (base.crazy, guest.pointer), (ONES, transformed))?;
    if pointer != EOF.checked_sub(u32::from(byte)).ok_or("complement")? {
        return Err("wrong complemented input pointer".to_owned());
    }
    let lookup = if byte == 0 {
        0
    } else {
        plus(pointer, 1)?
    };
    let odd = byte & 1 != 0;
    let loader_word = if odd {
        7_174_416
    } else {
        37
    };
    let dispatch = if odd {
        7_174_417
    } else {
        38
    };
    let route = if odd {
        7_181_799
    } else {
        7_181_819
    };
    for (site, (address, value)) in guest.selector.into_iter().zip([
        (guest.pointer, pointer),
        (lookup, loader_word),
        (dispatch, route),
    ]) {
        let trace = effect(vm, base, site, b'j')?;
        if trace
            .memory_reads
            .data
            .map(|read| (read.address, read.value))
            != Some((address, value))
        {
            return Err(format!("wrong parity route: {trace:?}"));
        }
        routing(&trace, base.branch)?;
    }
    if !odd {
        let load = effect(vm, base, base.rotate, b'*')?;
        check_store(&load, 7_175_052, EOF, EOF)?;
        let actual = fold(vm, base, (base.crazy, guest.state), (*parity, EOF))?;
        *parity = if *parity == 334_080 {
            462_339
        } else {
            334_080
        };
        if actual != *parity {
            return Err("wrong persistent even update".to_owned());
        }
    }
    select(
        vm,
        base,
        if odd {
            7_175_112
        } else {
            7_175_110
        },
        7_182_099,
    )?;
    if word(vm, guest.state)? != *parity {
        return Err("unselected parity state update".to_owned());
    }
    reset_operand(vm, base, (base.capture, transformed), CONSTANTS)?;
    reset_operand(vm, base, (guest.pointer, pointer), POINTER_CONSTANTS)?;
    select(vm, base, 7_175_090, 7_175_199)?;
    Ok(())
}

// The source-level checksum oracle computes all eight bits, then the test
// compares the independently executed guest's single-bit projection.
fn checksum(stream: &[u8]) -> u8 {
    stream.iter().fold(0u8, |acc, &byte| {
        let combined = if byte & 1 == 1 {
            acc ^ byte
        } else {
            acc.wrapping_add(byte)
        };
        combined.wrapping_add(3)
    })
}

fn run_parity(
    boot: &ProfileMachine,
    guest: &RelocatedRecurrentParitySource,
    stream: &[u8],
) -> Result<(), String> {
    let mut vm = boot
        .fork_with_input(stream.to_vec())
        .map_err(|e| e.to_string())?;
    let base = &guest.capture;
    let mut classifier = INITIAL;
    let mut parity = 334_080;
    for (address, expected) in [
        (guest.pointer, ONES),
        (guest.state, parity),
        (0, 37),
        (38, 7_181_819),
        (7_174_417, 7_181_799),
    ] {
        if word(&vm, address)? != expected {
            return Err(format!("incorrect parity bootstrap M{address}"));
        }
    }
    for &byte in stream {
        let encoded = cycle(
            &mut vm,
            base,
            &mut classifier,
            (TraceInput::Byte(byte), BYTE),
        )?;
        parity_byte(&mut vm, guest, byte, encoded, &mut parity)?;
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
        || word(&vm, guest.pointer)? != ONES
        || word(&vm, guest.state)? != parity
    {
        return Err("EOF mutated byte arm state".to_owned());
    }
    let expected = checksum(stream) & 1;
    let rotated = if expected == 0 {
        111_360
    } else {
        154_113
    };
    let load = effect(&mut vm, base, prev(base.output)?, b'*')?;
    check_store(&load, guest.state, parity, rotated)?;
    let output = effect(&mut vm, base, base.output, b'<')?;
    if output.output != Some(expected)
        || output.input.is_some()
        || output.memory_delta.data.is_some()
    {
        return Err("wrong parity output effect".to_owned());
    }
    let mut record = None;
    let outcome = vm
        .step_traced(&mut |entry| record = Some(*entry))
        .map_err(|e| e.to_string())?;
    let trace = record.ok_or("missing halt trace")?;
    if outcome != StepOutcome::Terminated(Termination::HaltInstruction)
        || trace.before.registers.code_pointer != base.halt
        || trace.decoded != Some(b'v')
        || trace.input.is_some()
        || trace.output.is_some()
        || trace.memory_delta.data.is_some()
        || vm.input_consumed() != stream.len()
        || vm.output() != [expected]
    {
        return Err(format!("wrong parity termination: {trace:?}"));
    }
    Ok(())
}

#[test]
fn relocated_recurrent_parity_all_bytes_and_eof() -> Result<(), String> {
    let guest = source()?;
    if guest.capture.source.len() != 6_420_168 {
        return Err("parity source size regressed".to_owned());
    }
    let boot = enter(&guest.capture, BOOT_BUDGET)?;
    for stream in [
        vec![],
        vec![0],
        vec![255],
        vec![2, 1],
        vec![1, 1],
        (0..=255).collect(),
        (0..=255).rev().chain([43]).collect(),
    ] {
        run_parity(&boot, &guest, &stream)?;
    }
    Ok(())
}

#[test]
fn relocated_recurrent_parity_refuses_other_profile() {
    assert_eq!(
        build_relocated_recurrent_parity_source(historical_profile()),
        Err(ZeroCellSourceError::UnsupportedProfile)
    );
}

#[test]
fn relocated_recurrent_parity_omitted_effects_refuse() -> Result<(), String> {
    let guest = source()?;
    for site in guest.selector.into_iter().chain([
        guest.load,
        prev(guest.capture.output)?,
        guest.capture.output,
    ]) {
        let mut modified = guest.clone();
        let noop = (33..=126u8)
            .find(|byte| {
                decode_profile_instruction(u32::from(*byte), site) == Some(b'o')
            })
            .ok_or("missing noop")?;
        *modified
            .capture
            .source
            .get_mut(usize::try_from(site).map_err(|e| e.to_string())?)
            .ok_or("missing selector")? = noop;
        let boot = enter(&modified.capture, BOOT_BUDGET)?;
        if run_parity(&boot, &modified, &[0, 255]).is_ok() {
            return Err(format!("accepted omitted parity effect C{site}"));
        }
    }
    Ok(())
}

#[test]
fn relocated_recurrent_parity_is_checksum_projection() {
    for prior in 0..=u8::MAX {
        for byte in 0..=u8::MAX {
            let combined = if byte & 1 == 1 {
                prior ^ byte
            } else {
                prior.wrapping_add(byte)
            };
            assert_eq!(
                combined.wrapping_add(3) & 1,
                (prior & 1) ^ u8::from(byte & 1 == 0)
            );
        }
    }
}
