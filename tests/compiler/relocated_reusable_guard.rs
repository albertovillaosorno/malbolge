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
//   - Independent classifier closure and recurrent physical branch replay.
// - Must-Not:
//   - Claim checksum execution or complete source-frame admission.
// - Allows:
//   - Inputs: actual loaded guest and independent ternary truth table.
//   - Outputs: exact state transitions, I/O and actual EOF halt.
//   - Side effects: isolated normative VM execution.
// - Split-When:
//   - General recurrent branch replay owns these checks.
// - Merge-When:
//   - A complete source checksum witness subsumes this guard.
// - Summary:
//   - Authenticate a dirty five-fold classifier and mixed-phase code cell.

use std::collections::BTreeSet;

use malbolge::{
    ProfileMachine, ProfileStepTrace, StepOutcome, Termination, TraceInput,
    current_profile, decode_profile_instruction, historical_profile,
};

use super::super::super::layout::{
    RelocatedReusableGuardSource, ZeroCellSourceError,
    build_relocated_reusable_guard_source,
};
use super::{
    ACTIVE, EOF, INACTIVE, active, advance_pair, check_encryption,
    independent_crazy, plus, prev, step, transfer, word,
};

const INITIAL: [u32; 5] = [2_916, 5_832, 14_334_327, 728, 7_180_650];
const BYTE: u32 = 7_180_650;
const EOF_LANDINGS: [u32; 2] = [7_178_463, 7_179_921];
const BUDGET: usize = 950_000;

fn source() -> Result<RelocatedReusableGuardSource, String> {
    build_relocated_reusable_guard_source(current_profile())
        .map_err(|error| format!("guard source: {error:?}"))
}

fn fold(mut state: [u32; 5], mut accumulator: u32) -> [u32; 5] {
    for value in &mut state {
        accumulator = independent_crazy(*value, accumulator);
        *value = accumulator;
    }
    state
}

fn digit(word: u32, place: u32) -> u32 {
    word.checked_div(3u32.pow(place))
        .unwrap_or_default()
        .checked_rem(3)
        .unwrap_or_default()
}

fn digit_fold(mut state: [u32; 5], mut accumulator: u32) -> [u32; 5] {
    for value in &mut state {
        accumulator = digit(independent_crazy(*value, accumulator), 0);
        *value = accumulator;
    }
    state
}

const fn last(state: [u32; 5]) -> u32 {
    let [_, _, _, _, value] = state;
    value
}

fn check_constant_digit(place: u32) -> Result<(), String> {
    let start = INITIAL.map(|word| digit(word, place));
    let mut seen = BTreeSet::new();
    let mut pending = vec![start];
    while let Some(state) = pending.pop() {
        if !seen.insert(state) {
            continue;
        }
        for input in 0..3u32 {
            let next = digit_fold(state, input);
            if last(next) != digit(BYTE, place) {
                return Err(format!(
                    "nonconstant trit {place}: {state:?} -> {next:?}"
                ));
            }
            pending.push(next);
        }
    }
    Ok(())
}

#[test]
fn relocated_guard_classifier_is_closed() -> Result<(), String> {
    for place in (0..15u32).filter(|place| ![6, 7].contains(place)) {
        check_constant_digit(place)?;
    }
    let mut high = [
        INITIAL.map(|word| digit(word, 6)),
        INITIAL.map(|word| digit(word, 7)),
    ];
    let mut seen = BTreeSet::new();
    let mut landings = BTreeSet::new();
    let mut odd = false;
    while seen.insert((high, odd)) {
        let eof = high.map(|state| last(digit_fold(state, 2)));
        if eof
            != if odd {
                [1, 0]
            } else {
                [0, 1]
            }
        {
            return Err(format!(
                "EOF trits disagree with length parity: {eof:?}"
            ));
        }
        let _: bool = landings.insert(eof);
        high = high.map(|state| digit_fold(state, 0));
        odd = !odd;
        if high.map(last) != [1, 1] {
            return Err("byte trits changed route".to_owned());
        }
    }
    if landings.len() != 2 {
        return Err("missing EOF landing".to_owned());
    }
    Ok(())
}

fn enter(
    vm: &mut ProfileMachine,
    guest: &RelocatedReusableGuardSource,
) -> Result<(), String> {
    for _ in 0..BUDGET {
        if vm.registers().code_pointer == guest.input {
            return Ok(());
        }
        let trace = step(vm)?;
        if trace.input.is_some() || trace.output.is_some() {
            return Err("bootstrap performed premature I/O".to_owned());
        }
    }
    Err("missing recurrent guard entry".to_owned())
}

fn invariant(
    vm: &ProfileMachine,
    guest: &RelocatedReusableGuardSource,
    state: [u32; 5],
) -> Result<(), String> {
    if vm.registers().code_pointer != guest.input
        || vm.registers().data_pointer != plus(guest.route, 2)?
    {
        return Err("wrong guard entry".to_owned());
    }
    for (address, value) in guest.states.into_iter().zip(state) {
        if word(vm, address)? != value {
            return Err(format!("classifier state M{address}"));
        }
    }
    for (site, expected) in [
        (guest.input, ACTIVE),
        (guest.crazy, INACTIVE),
        (guest.branch, u32::from(b'}')),
        (guest.relocate, INACTIVE),
    ] {
        let dispatcher = plus(site, 1)?;
        if word(vm, site)? != expected
            || decode_profile_instruction(word(vm, dispatcher)?, dispatcher)
                != Some(b'i')
        {
            return Err(format!("guard code phase C{site}"));
        }
    }
    Ok(())
}

fn mixed(
    vm: &mut ProfileMachine,
    site: u32,
    data: u32,
    phase: (u8, u8, u8),
) -> Result<ProfileStepTrace, String> {
    let (before, opcode, after) = phase;
    let trace = step(vm)?;
    if trace.before.registers.code_pointer != site
        || trace.before.registers.data_pointer != data
        || trace.fetched_cell != Some(u32::from(before))
        || trace.decoded != Some(opcode)
        || trace.after.registers.code_pointer != plus(site, 1)?
    {
        return Err(format!("wrong mixed phase: {trace:?}"));
    }
    check_encryption(&trace, site, u32::from(before), u32::from(after))?;
    Ok(trace)
}

fn check_fold(
    trace: &ProfileStepTrace,
    address: u32,
    words: (u32, u32, u32),
) -> Result<(), String> {
    let (old, raw, new) = words;
    let change = trace
        .memory_delta
        .data
        .map(|write| (write.address, write.before, write.after));
    if trace.before.registers.accumulator != raw
        || trace
            .memory_reads
            .data
            .map(|read| (read.address, read.value))
            != Some((address, old))
        || trace.after.registers.accumulator != new
        || trace.after.registers.data_pointer != plus(address, 1)?
        || change != (old != new).then_some((address, old, new))
        || trace.input.is_some()
        || trace.output.is_some()
    {
        return Err(format!("wrong classifier fold: {trace:?}"));
    }
    Ok(())
}

fn first_four(
    vm: &mut ProfileMachine,
    guest: &RelocatedReusableGuardSource,
    state: [u32; 5],
    raw: u32,
) -> Result<u32, String> {
    let mut previous = guest.input;
    let mut data = plus(guest.route, 3)?;
    let mut accumulator = raw;
    for (address, old) in guest.states.into_iter().zip(state).take(4) {
        advance_pair(vm, previous, data, guest.crazy)?;
        let next = independent_crazy(old, accumulator);
        let trace = active(vm, guest.crazy, b'p', address)?;
        check_fold(&trace, address, (old, accumulator, next))?;
        accumulator = next;
        previous = guest.crazy;
        data = plus(address, 1)?;
    }
    Ok(accumulator)
}

fn final_fold(
    vm: &mut ProfileMachine,
    guest: &RelocatedReusableGuardSource,
    old: u32,
    raw: u32,
) -> Result<u32, String> {
    let address = last(guest.states);
    let data = address.checked_sub(3).ok_or("invalid final operand")?;
    if word(vm, guest.branch)? != u32::from(b'}') {
        return Err("missing four-phase predecessor".to_owned());
    }
    transfer(vm, plus(guest.crazy, 1)?, data, (guest.branch, false))?;
    if word(vm, guest.branch)? != u32::from(b'i') {
        return Err("missing intermediate phase".to_owned());
    }
    transfer(
        vm,
        plus(guest.branch, 1)?,
        plus(data, 1)?,
        (guest.branch, false),
    )?;
    transfer(
        vm,
        plus(guest.branch, 1)?,
        prev(address)?,
        (prev(guest.branch)?, false),
    )?;
    let trace = mixed(vm, guest.branch, address, (b'*', b'p', b'r'))?;
    let next = independent_crazy(old, raw);
    check_fold(&trace, address, (old, raw, next))?;
    Ok(next)
}

fn check_relocate(
    trace: &ProfileStepTrace,
    address: u32,
    target: u32,
) -> Result<(), String> {
    if trace
        .memory_reads
        .data
        .map(|read| (read.address, read.value))
        != Some((address, target))
        || trace.after.registers.data_pointer != plus(target, 1)?
        || trace.after.registers.accumulator
            != trace.before.registers.accumulator
        || trace.memory_delta.data.is_some()
        || trace.input.is_some()
        || trace.output.is_some()
    {
        return Err(format!("wrong guard relocation: {trace:?}"));
    }
    Ok(())
}

fn select(
    vm: &mut ProfileMachine,
    guest: &RelocatedReusableGuardSource,
    class: u32,
) -> Result<(), String> {
    let address = last(guest.states);
    advance_pair(vm, guest.branch, plus(address, 1)?, guest.relocate)?;
    let reset = active(vm, guest.relocate, b'j', plus(address, 3)?)?;
    check_relocate(
        &reset,
        plus(address, 3)?,
        address.checked_sub(2).ok_or("class underflow")?,
    )?;
    transfer(
        vm,
        plus(guest.relocate, 1)?,
        prev(address)?,
        (prev(guest.branch)?, false),
    )?;
    let branch = mixed(vm, guest.branch, address, (b'r', b'j', b'}'))?;
    check_relocate(&branch, address, class)
}

fn return_to_input(
    vm: &mut ProfileMachine,
    guest: &RelocatedReusableGuardSource,
) -> Result<(), String> {
    transfer(
        vm,
        plus(guest.branch, 1)?,
        plus(BYTE, 1)?,
        (guest.input, true),
    )?;
    advance_pair(vm, guest.input, plus(BYTE, 2)?, guest.relocate)?;
    let reset = active(vm, guest.relocate, b'j', plus(BYTE, 4)?)?;
    check_relocate(&reset, plus(BYTE, 4)?, guest.route)?;
    transfer(
        vm,
        plus(guest.relocate, 1)?,
        plus(guest.route, 1)?,
        (prev(guest.input)?, false),
    )
}

fn stop(
    vm: &mut ProfileMachine,
    guest: &RelocatedReusableGuardSource,
    class: u32,
) -> Result<(), String> {
    transfer(
        vm,
        plus(guest.branch, 1)?,
        plus(class, 1)?,
        (prev(guest.terminal)?, false),
    )?;
    let [odd, _even] = EOF_LANDINGS;
    let parity = u8::from(class == odd);
    let raw = if parity == 1 {
        3
    } else {
        0
    };
    let address = plus(class, 2)?;
    let load = step(vm)?;
    if load.before.registers.code_pointer != guest.terminal
        || load.before.registers.data_pointer != address
        || load.decoded != Some(b'*')
        || load
            .memory_reads
            .data
            .map(|read| (read.address, read.value))
            != Some((address, raw))
        || load.after.registers.accumulator != u32::from(parity)
        || load
            .memory_delta
            .data
            .map(|write| (write.address, write.before, write.after))
            != (raw != 0).then_some((address, raw, u32::from(parity)))
        || load.input.is_some()
        || load.output.is_some()
    {
        return Err(format!("missing physical parity load: {load:?}"));
    }
    let output = step(vm)?;
    if output.before.registers.code_pointer != guest.output
        || output.decoded != Some(b'<')
        || output.output != Some(parity)
        || output.input.is_some()
        || output.memory_delta.data.is_some()
    {
        return Err(format!("missing physical EOF output: {output:?}"));
    }
    let mut record = None;
    let result = vm
        .step_traced(&mut |trace| record = Some(*trace))
        .map_err(|error| error.to_string())?;
    let trace = record.ok_or("missing halt trace")?;
    if result != StepOutcome::Terminated(Termination::HaltInstruction)
        || trace.before.registers.code_pointer != guest.halt
        || trace.input.is_some()
        || trace.output.is_some()
        || trace.decoded != Some(b'v')
    {
        return Err(format!("missing physical EOF halt: {trace:?}"));
    }
    Ok(())
}

fn cycle(
    vm: &mut ProfileMachine,
    guest: &RelocatedReusableGuardSource,
    state: [u32; 5],
    input: TraceInput,
) -> Result<[u32; 5], String> {
    invariant(vm, guest, state)?;
    let trace = active(vm, guest.input, b'/', plus(guest.route, 2)?)?;
    let raw = match input {
        TraceInput::Byte(byte) => u32::from(byte),
        TraceInput::EndOfInput => EOF,
    };
    if trace.input != Some(input)
        || trace.after.registers.accumulator != raw
        || trace.output.is_some()
        || trace.memory_delta.data.is_some()
    {
        return Err(format!("wrong guard input: {trace:?}"));
    }
    let intermediate = first_four(vm, guest, state, raw)?;
    let class = final_fold(vm, guest, last(state), intermediate)?;
    let next = fold(state, raw);
    if last(next) != class {
        return Err("fold oracle disagreement".to_owned());
    }
    select(vm, guest, class)?;
    if input == TraceInput::EndOfInput {
        if !EOF_LANDINGS.contains(&class) {
            return Err(format!("EOF selected byte route M{class}"));
        }
        stop(vm, guest, class)?;
    } else {
        if class != BYTE {
            return Err(format!("byte selected EOF route M{class}"));
        }
        return_to_input(vm, guest)?;
        invariant(vm, guest, next)?;
    }
    Ok(next)
}

fn run(
    stream: &[u8],
    guest: &RelocatedReusableGuardSource,
) -> Result<u32, String> {
    let mut vm = ProfileMachine::from_source(
        current_profile(),
        &guest.source,
        stream.to_owned(),
    )
    .map_err(|error| error.to_string())?;
    enter(&mut vm, guest)?;
    let mut state = INITIAL;
    for event in stream
        .iter()
        .copied()
        .map(TraceInput::Byte)
        .chain([TraceInput::EndOfInput])
    {
        state = cycle(&mut vm, guest, state, event)?;
    }
    if vm.input_consumed() != stream.len()
        || vm.output() != [u8::from(stream.len() & 1 == 1)]
    {
        return Err("wrong terminal I/O".to_owned());
    }
    Ok(last(state))
}

#[test]
fn relocated_guard_all_bytes_and_both_eof_landings() -> Result<(), String> {
    let guest = source()?;
    let mut classes = BTreeSet::new();
    for stream in [
        vec![],
        vec![255],
        vec![0, 255],
        (0..=255).collect(),
        (0..=255).rev().collect(),
    ] {
        let _: bool = classes.insert(run(&stream, &guest)?);
    }
    if classes != BTreeSet::from(EOF_LANDINGS) {
        return Err(format!("missing EOF landing: {classes:?}"));
    }
    Ok(())
}

#[test]
fn relocated_guard_omitted_terminal_effects_refuse() -> Result<(), String> {
    let guest = source()?;
    for (site, prefix) in [
        (guest.terminal, "missing physical parity load"),
        (guest.output, "missing physical EOF output"),
        (guest.halt, "missing physical EOF halt"),
    ] {
        let mut modified = guest.clone();
        let noop = (33..=126u8)
            .find(|byte| {
                decode_profile_instruction(u32::from(*byte), site) == Some(b'o')
            })
            .ok_or("missing canonical noop")?;
        *modified
            .source
            .get_mut(usize::try_from(site).map_err(|error| error.to_string())?)
            .ok_or("missing terminal cell")? = noop;
        let error = run(&[0, 255], &modified)
            .err()
            .ok_or("accepted omitted terminal effect")?;
        if !error.starts_with(prefix) {
            return Err(format!("wrong refusal: {error}"));
        }
    }
    Ok(())
}

#[test]
fn relocated_guard_refuses_other_profile() {
    assert_eq!(
        build_relocated_reusable_guard_source(historical_profile()),
        Err(ZeroCellSourceError::UnsupportedProfile)
    );
}
