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
//   - Normative repeated instruction and mutable-state replay.
// - Must-Not:
//   - Claim source CFG admission or an EOF-terminating checksum loop.
// - Allows:
//   - Inputs: fixed graphical source, bytes and omitted-effect controls.
//   - Outputs: actual I/O, code restoration and dirty state effects.
//   - Side effects: isolated normative VM execution.
// - Split-When:
//   - General reusable instruction replay owns these controls.
// - Merge-When:
//   - Complete recurrent checksum execution subsumes this witness.
// - Summary:
//   - Authenticate every transfer in the recurrent four-operation kernel.

#[path = "relocated_reusable_guard.rs"]
mod relocated_reusable_guard;

use malbolge::{
    ProfileMachine, ProfileStepTrace, StepOutcome, TraceInput, current_profile,
    decode_profile_instruction, encrypt_profile_cell, historical_profile,
};

use super::super::crazy as independent_crazy;
use super::super::layout::{
    RelocatedReusableSource, ZeroCellSourceError,
    build_relocated_reusable_source,
};
use super::word;

const BUDGET: usize = 135_000;
const ACTIVE: u32 = 70;
const INACTIVE: u32 = 74;
const EOF: u32 = 14_348_906;

fn source() -> Result<RelocatedReusableSource, String> {
    build_relocated_reusable_source(current_profile())
        .map_err(|error| format!("reusable source: {error:?}"))
}

fn plus(address: u32, offset: u32) -> Result<u32, String> {
    address
        .checked_add(offset)
        .ok_or_else(|| "address overflow".to_owned())
}

fn prev(address: u32) -> Result<u32, String> {
    address
        .checked_sub(1)
        .ok_or_else(|| "address underflow".to_owned())
}

fn step(vm: &mut ProfileMachine) -> Result<ProfileStepTrace, String> {
    let mut record = None;
    let outcome = vm
        .step_traced(&mut |trace| record = Some(*trace))
        .map_err(|error| error.to_string())?;
    if outcome != StepOutcome::Continued {
        return Err(format!("unexpected {outcome:?}"));
    }
    record.ok_or_else(|| "missing trace".to_owned())
}

fn enter(
    vm: &mut ProfileMachine,
    guest: &RelocatedReusableSource,
) -> Result<(), String> {
    for _ in 0..BUDGET {
        if vm.registers().code_pointer == guest.input {
            return Ok(());
        }
        let _: ProfileStepTrace = step(vm)?;
    }
    Err("missing first recurrent input".to_owned())
}

fn invariant(
    vm: &ProfileMachine,
    guest: &RelocatedReusableSource,
    state: u32,
) -> Result<(), String> {
    let route = [
        guest.input,
        prev(guest.input)?,
        0,
        guest.crazy,
        prev(guest.crazy)?,
        state,
        guest.output,
        prev(guest.output)?,
        0,
        guest.relocate,
        prev(guest.relocate)?,
        prev(guest.route)?,
    ];
    for (offset, value) in (0..).zip(route) {
        let address = plus(guest.route, offset)?;
        if word(vm, address)? != value {
            return Err(format!("changed route word M{address}"));
        }
    }
    if vm.registers().code_pointer != guest.input
        || vm.registers().data_pointer != plus(guest.route, 2)?
    {
        return Err("invalid recurrent entry registers".to_owned());
    }
    for (site, expected) in [
        (guest.input, ACTIVE),
        (guest.crazy, INACTIVE),
        (guest.output, INACTIVE),
        (guest.relocate, INACTIVE),
    ] {
        let dispatcher = plus(site, 1)?;
        if word(vm, site)? != expected
            || decode_profile_instruction(word(vm, dispatcher)?, dispatcher)
                != Some(b'i')
        {
            return Err(format!("invalid recurrent code state C{site}"));
        }
    }
    Ok(())
}

fn check_encryption(
    trace: &ProfileStepTrace,
    address: u32,
    before: u32,
    after: u32,
) -> Result<(), String> {
    if trace
        .memory_delta
        .encryption
        .map(|write| (write.address, write.before, write.after))
        != Some((address, before, after))
    {
        return Err(format!("wrong encryption at C{address}: {trace:?}"));
    }
    Ok(())
}

fn active(
    vm: &mut ProfileMachine,
    site: u32,
    opcode: u8,
    data: u32,
) -> Result<ProfileStepTrace, String> {
    let trace = step(vm)?;
    if trace.before.registers.code_pointer != site
        || trace.before.registers.data_pointer != data
        || trace.fetched_cell != Some(ACTIVE)
        || trace.decoded != Some(opcode)
        || trace.after.registers.code_pointer != plus(site, 1)?
    {
        return Err(format!("wrong active step C{site}: {trace:?}"));
    }
    check_encryption(&trace, site, ACTIVE, INACTIVE)?;
    Ok(trace)
}

fn transfer(
    vm: &mut ProfileMachine,
    site: u32,
    data: u32,
    landing: (u32, bool),
) -> Result<(), String> {
    let (target, restore) = landing;
    let old = word(vm, target)?;
    let next = encrypt_profile_cell(old).ok_or("nongraphical jump target")?;
    let trace = step(vm)?;
    if trace.decoded != Some(b'i')
        || trace.before.registers.code_pointer != site
        || trace.before.registers.data_pointer != data
        || trace
            .memory_reads
            .data
            .map(|read| (read.address, read.value))
            != Some((data, target))
        || trace.after.registers.code_pointer != plus(target, 1)?
        || trace.after.registers.data_pointer != plus(data, 1)?
        || trace.after.registers.accumulator
            != trace.before.registers.accumulator
        || trace.memory_delta.data.is_some()
        || trace.input.is_some()
        || trace.output.is_some()
    {
        return Err(format!("wrong indirect transfer: {trace:?}"));
    }
    if restore && (old, next) != (INACTIVE, ACTIVE) {
        return Err(format!("missing instruction restore C{target}"));
    }
    check_encryption(&trace, target, old, next)
}

fn advance_pair(
    vm: &mut ProfileMachine,
    site: u32,
    data: u32,
    target: u32,
) -> Result<(), String> {
    transfer(vm, plus(site, 1)?, data, (target, true))?;
    transfer(vm, plus(target, 1)?, plus(data, 1)?, (prev(target)?, false))
}

fn check_input(
    vm: &mut ProfileMachine,
    guest: &RelocatedReusableSource,
    expected: TraceInput,
) -> Result<u32, String> {
    let trace = active(vm, guest.input, b'/', plus(guest.route, 2)?)?;
    let raw = match expected {
        TraceInput::Byte(byte) => u32::from(byte),
        TraceInput::EndOfInput => EOF,
    };
    if trace.input != Some(expected)
        || trace.output.is_some()
        || trace.memory_delta.data.is_some()
        || trace.after.registers.accumulator != raw
    {
        return Err(format!("wrong recurrent input: {trace:?}"));
    }
    Ok(raw)
}

fn check_crazy(
    vm: &mut ProfileMachine,
    guest: &RelocatedReusableSource,
    old: u32,
    raw: u32,
) -> Result<u32, String> {
    let result = independent_crazy(old, raw);
    let trace = active(vm, guest.crazy, b'p', guest.state)?;
    let change = trace
        .memory_delta
        .data
        .map(|write| (write.address, write.before, write.after));
    if trace.before.registers.accumulator != raw
        || trace
            .memory_reads
            .data
            .map(|read| (read.address, read.value))
            != Some((guest.state, old))
        || trace.after.registers.accumulator != result
        || change != (old != result).then_some((guest.state, old, result))
        || trace.input.is_some()
        || trace.output.is_some()
    {
        return Err(format!("wrong dirty crazy store: {trace:?}"));
    }
    Ok(result)
}

fn check_output(
    vm: &mut ProfileMachine,
    guest: &RelocatedReusableSource,
    value: u32,
) -> Result<(), String> {
    let trace = active(vm, guest.output, b'<', plus(guest.route, 8)?)?;
    let byte = u8::try_from(value & 255).map_err(|error| error.to_string())?;
    if trace.output != Some(byte)
        || trace.input.is_some()
        || trace.memory_delta.data.is_some()
        || trace.before.registers.accumulator != value
        || trace.after.registers.accumulator != value
    {
        return Err(format!("wrong recurrent output: {trace:?}"));
    }
    Ok(())
}

fn check_reset(
    vm: &mut ProfileMachine,
    guest: &RelocatedReusableSource,
) -> Result<(), String> {
    let trace = active(vm, guest.relocate, b'j', plus(guest.route, 11)?)?;
    if trace.after.registers.data_pointer != guest.route
        || trace.memory_reads.data.map(|read| read.value)
            != Some(prev(guest.route)?)
        || trace.before.registers.accumulator
            != trace.after.registers.accumulator
        || trace.memory_delta.data.is_some()
        || trace.input.is_some()
        || trace.output.is_some()
    {
        return Err(format!("wrong recurrent data reset: {trace:?}"));
    }
    Ok(())
}

fn cycle(
    vm: &mut ProfileMachine,
    guest: &RelocatedReusableSource,
    state: u32,
    input: TraceInput,
) -> Result<u32, String> {
    let raw = check_input(vm, guest, input)?;
    advance_pair(vm, guest.input, plus(guest.route, 3)?, guest.crazy)?;
    let next = check_crazy(vm, guest, state, raw)?;
    advance_pair(vm, guest.crazy, plus(guest.route, 6)?, guest.output)?;
    check_output(vm, guest, next)?;
    advance_pair(vm, guest.output, plus(guest.route, 9)?, guest.relocate)?;
    check_reset(vm, guest)?;
    advance_pair(vm, guest.relocate, guest.route, guest.input)?;
    invariant(vm, guest, next)?;
    Ok(next)
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "test assertions distinguish physical witnesses"
)]
fn relocated_reusable_all_bytes_and_eof() -> Result<(), String> {
    let guest = source()?;
    let bytes: Vec<u8> = (0..=255).collect();
    let mut stream = vec![42];
    stream.extend(bytes.iter().copied());
    let mut vm =
        ProfileMachine::from_source(current_profile(), &guest.source, stream)
            .map_err(|error| error.to_string())?;
    enter(&mut vm, &guest)?;
    assert_eq!(vm.input_consumed(), 1);
    assert!(vm.output().is_empty());
    invariant(&vm, &guest, 0)?;
    let mut state = 0;
    let mut expected_output = Vec::new();
    for input in bytes
        .into_iter()
        .map(TraceInput::Byte)
        .chain([TraceInput::EndOfInput; 4])
    {
        state = cycle(&mut vm, &guest, state, input)?;
        expected_output.push(
            u8::try_from(state & 255).map_err(|error| error.to_string())?,
        );
    }
    assert_eq!(vm.input_consumed(), 257);
    assert_eq!(vm.output(), expected_output);
    assert_eq!(word(&vm, guest.state)?, state);
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "test assertions distinguish physical witnesses"
)]
fn relocated_reusable_initial_eof() -> Result<(), String> {
    let guest = source()?;
    let mut vm =
        ProfileMachine::from_source(current_profile(), &guest.source, vec![])
            .map_err(|error| error.to_string())?;
    enter(&mut vm, &guest)?;
    invariant(&vm, &guest, 0)?;
    let mut state = 0;
    for _ in 0..8u32 {
        state = cycle(&mut vm, &guest, state, TraceInput::EndOfInput)?;
    }
    assert_eq!(vm.input_consumed(), 0);
    assert_eq!(vm.output().len(), 8);
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "test assertions distinguish physical witnesses"
)]
fn relocated_reusable_omitted_active_effect() -> Result<(), String> {
    let mut guest = source()?;
    let position =
        usize::try_from(guest.crazy).map_err(|error| error.to_string())?;
    let noop = (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), guest.crazy)
                == Some(b'o')
        })
        .ok_or("no canonical noop")?;
    *guest.source.get_mut(position).ok_or("missing crazy cell")? = noop;
    let mut vm =
        ProfileMachine::from_source(current_profile(), &guest.source, vec![
            42, 7,
        ])
        .map_err(|error| error.to_string())?;
    enter(&mut vm, &guest)?;
    assert!(cycle(&mut vm, &guest, 0, TraceInput::Byte(7)).is_err());
    assert!(vm.output().is_empty());
    Ok(())
}

#[test]
fn relocated_reusable_refuses_other_profile() {
    assert_eq!(
        build_relocated_reusable_source(historical_profile()),
        Err(ZeroCellSourceError::UnsupportedProfile)
    );
}
