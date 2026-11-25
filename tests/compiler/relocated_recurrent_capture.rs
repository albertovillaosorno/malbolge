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
//   - Recurrent raw-capture and dirty-reset physical replay.
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
//   - Prove one dirty capture slot survives dispatch and is reused.

#[path = "relocated_recurrent_indexed.rs"]
mod relocated_recurrent_indexed;
#[path = "relocated_recurrent_mod4.rs"]
mod relocated_recurrent_mod4;
#[path = "relocated_recurrent_nibble.rs"]
mod relocated_recurrent_nibble;
#[path = "relocated_recurrent_parity.rs"]
mod relocated_recurrent_parity;
#[path = "relocated_recurrent_reload.rs"]
mod relocated_recurrent_reload;

use std::collections::BTreeSet;

use malbolge::{
    ProfileMachine, ProfileStepTrace, StepOutcome, Termination, TraceInput,
    current_profile, decode_profile_instruction, encrypt_profile_cell,
    historical_profile,
};

use super::super::super::layout::{
    RelocatedRecurrentCaptureSource, ZeroCellSourceError,
    build_relocated_recurrent_capture_source,
};
use super::{EOF, independent_crazy, plus, prev, step, word};

const ONES: u32 = 7_174_453;
const INITIAL: [u32; 6] = [5_832, 5_103, 0, 14_329_224, 728, 13_122];
const BYTE: u32 = 7_180_650;
const EOF_ODD: u32 = 7_178_463;
const EOF_EVEN: u32 = 7_179_921;
const CONSTANTS: [u32; 3] = [7_175_040, 7_175_042, 7_175_044];
const BOOT_BUDGET: usize = 1_400_000;
const EFFECT_BUDGET: usize = 2_048;

fn source() -> Result<RelocatedRecurrentCaptureSource, String> {
    build_relocated_recurrent_capture_source(current_profile())
        .map_err(|error| format!("capture source: {error:?}"))
}

fn enter(
    guest: &RelocatedRecurrentCaptureSource,
    budget: usize,
) -> Result<ProfileMachine, String> {
    let mut vm = ProfileMachine::from_source(
        current_profile(),
        &guest.source,
        Vec::new(),
    )
    .map_err(|error| error.to_string())?;
    for _ in 0..budget {
        if vm.registers().code_pointer == guest.input
            && decode_profile_instruction(word(&vm, guest.input)?, guest.input)
                == Some(b'/')
        {
            invariant(&vm, guest, INITIAL)?;
            check_bootstrap_anchors(&vm)?;
            return Ok(vm);
        }
        let trace = step(&mut vm)?;
        if trace.input.is_some() || trace.output.is_some() {
            return Err(format!("premature bootstrap I/O: {trace:?}"));
        }
    }
    Err("missing first recurrent capture".to_owned())
}

fn check_bootstrap_anchors(vm: &ProfileMachine) -> Result<(), String> {
    if word(vm, 7_174_471)? != 0
        || word(vm, 7_174_473)? != EOF
        || word(vm, 7_174_483)? != 7_174_610
        || word(vm, 7_174_487)? != 7_174_999
    {
        return Err("incorrect near-frame constants or anchors".to_owned());
    }
    let first = word(vm, 7_174_475)?;
    if ![7_183_000, 7_186_000, 7_190_000, 7_201_000].contains(&first) {
        return Err("incorrect first tape anchor".to_owned());
    }
    let mut prior = first;
    for address in [7_174_477, 7_174_479, 7_174_481] {
        let next = word(vm, address)?;
        if next <= prior
            || next >= 7_280_001
            || !next
                .checked_sub(prior)
                .ok_or("tape anchor order")?
                .is_multiple_of(4)
        {
            return Err("incorrect aligned tape anchor".to_owned());
        }
        prior = next;
    }
    Ok(())
}

fn invariant(
    vm: &ProfileMachine,
    guest: &RelocatedRecurrentCaptureSource,
    state: [u32; 6],
) -> Result<(), String> {
    if word(vm, guest.capture)? != ONES {
        return Err("capture slot not restored".to_owned());
    }
    for (address, expected) in guest.states.into_iter().zip(state) {
        if word(vm, address)? != expected {
            return Err(format!("classifier state M{address}"));
        }
    }
    for (address, expected) in CONSTANTS.into_iter().zip([ONES, EOF, 0]) {
        if word(vm, address)? != expected {
            return Err(format!("reset constant M{address}"));
        }
    }
    Ok(())
}

// Preparation may encrypt arbitrary graphical cells, but must not execute
// any unexpected arithmetic, I/O or halt. Authenticate each intervening
// transfer and its actual selected memory operand.
fn successor(address: u32) -> Result<u32, String> {
    if address == EOF {
        Ok(0)
    } else {
        plus(address, 1)
    }
}

fn routing(trace: &ProfileStepTrace, branch: u32) -> Result<(), String> {
    let before = trace.before.registers;
    let after = trace.after.registers;
    let (code, data, encrypted) = match trace.decoded {
        Some(b'i') => {
            let read = trace.memory_reads.data.ok_or("missing code pointer")?;
            if read.address != before.data_pointer {
                return Err("wrong code pointer operand".to_owned());
            }
            (
                successor(read.value)?,
                successor(before.data_pointer)?,
                read.value,
            )
        },
        Some(b'j') if before.code_pointer != branch => {
            let read = trace.memory_reads.data.ok_or("missing data pointer")?;
            if read.address != before.data_pointer {
                return Err("wrong data pointer operand".to_owned());
            }
            (
                successor(before.code_pointer)?,
                successor(read.value)?,
                before.code_pointer,
            )
        },
        Some(b'p' | b'*' | b'/' | b'<' | b'v' | b'j') | None => {
            return Err(format!("unexpected physical effect: {trace:?}"));
        },
        Some(_) => (
            successor(before.code_pointer)?,
            successor(before.data_pointer)?,
            before.code_pointer,
        ),
    };
    let read = trace
        .memory_reads
        .encryption
        .ok_or("missing encryption read")?;
    let next =
        encrypt_profile_cell(read.value).ok_or("invalid encryption word")?;
    if after.code_pointer != code
        || after.data_pointer != data
        || before.accumulator != after.accumulator
        || trace.input.is_some()
        || trace.output.is_some()
        || trace.memory_delta.data.is_some()
        || read.address != encrypted
        || trace
            .memory_delta
            .encryption
            .map(|write| (write.address, write.before, write.after))
            != (read.value != next).then_some((encrypted, read.value, next))
    {
        return Err(format!("invalid preparation step: {trace:?}"));
    }
    Ok(())
}

fn effect(
    vm: &mut ProfileMachine,
    guest: &RelocatedRecurrentCaptureSource,
    site: u32,
    opcode: u8,
) -> Result<ProfileStepTrace, String> {
    for _ in 0..EFFECT_BUDGET {
        let trace = step(vm)?;
        if trace.before.registers.code_pointer == site
            && trace.decoded == Some(opcode)
        {
            let initial = guest
                .source
                .get(usize::try_from(site).map_err(|error| error.to_string())?)
                .copied()
                .map(u32::from);
            if trace.fetched_cell != initial {
                return Err(format!("unrestored active code C{site}"));
            }
            return Ok(trace);
        }
        routing(&trace, guest.branch)?;
    }
    Err(format!("missing effect C{site}"))
}

fn check_store(
    trace: &ProfileStepTrace,
    address: u32,
    old: u32,
    new: u32,
) -> Result<(), String> {
    if trace.before.registers.data_pointer != address
        || trace
            .memory_reads
            .data
            .map(|read| (read.address, read.value))
            != Some((address, old))
        || trace
            .memory_delta
            .data
            .map(|write| (write.address, write.before, write.after))
            != (old != new).then_some((address, old, new))
        || trace.after.registers.accumulator != new
        || trace.after.registers.data_pointer != plus(address, 1)?
        || trace.input.is_some()
        || trace.output.is_some()
    {
        return Err(format!("wrong physical store M{address}: {trace:?}"));
    }
    Ok(())
}

fn fold(
    vm: &mut ProfileMachine,
    guest: &RelocatedRecurrentCaptureSource,
    target: (u32, u32),
    words: (u32, u32),
) -> Result<u32, String> {
    let (site, address) = target;
    let (old, accumulator) = words;
    let trace = effect(vm, guest, site, b'p')?;
    let new = independent_crazy(old, accumulator);
    if trace.before.registers.accumulator != accumulator {
        return Err(format!("wrong fold accumulator: {trace:?}"));
    }
    check_store(&trace, address, old, new)?;
    Ok(new)
}

fn select(
    vm: &mut ProfileMachine,
    guest: &RelocatedRecurrentCaptureSource,
    address: u32,
    expected: u32,
) -> Result<(), String> {
    let trace = effect(vm, guest, guest.branch, b'j')?;
    if trace
        .memory_reads
        .data
        .map(|read| (read.address, read.value))
        != Some((address, expected))
        || trace.before.registers.data_pointer != address
        || trace.after.registers.data_pointer != plus(expected, 1)?
        || trace.before.registers.accumulator
            != trace.after.registers.accumulator
        || trace.memory_delta.data.is_some()
        || trace.input.is_some()
        || trace.output.is_some()
    {
        return Err(format!("wrong captured dispatch: {trace:?}"));
    }
    Ok(())
}

fn cycle(
    vm: &mut ProfileMachine,
    guest: &RelocatedRecurrentCaptureSource,
    state: &mut [u32; 6],
    event: (TraceInput, u32),
) -> Result<u32, String> {
    let (input, expected_class) = event;
    invariant(vm, guest, *state)?;
    let raw = match input {
        TraceInput::Byte(byte) => u32::from(byte),
        TraceInput::EndOfInput => EOF,
    };
    let trace = effect(vm, guest, guest.input, b'/')?;
    if trace.input != Some(input)
        || trace.after.registers.accumulator != raw
        || trace.output.is_some()
        || trace.memory_delta.data.is_some()
    {
        return Err(format!("wrong recurrent input: {trace:?}"));
    }
    let encoded = fold(vm, guest, (guest.crazy, guest.capture), (ONES, raw))?;
    if independent_crazy(ONES, encoded) != raw {
        return Err("capture is not lossless".to_owned());
    }
    let mut accumulator = encoded;
    for (address, old) in guest.states.into_iter().zip(state.iter_mut()) {
        accumulator =
            fold(vm, guest, (guest.crazy, address), (*old, accumulator))?;
        *old = accumulator;
    }
    if accumulator != expected_class {
        return Err("wrong dirty classifier landing".to_owned());
    }
    select(
        vm,
        guest,
        *guest.states.last().ok_or("no class word")?,
        expected_class,
    )?;
    if word(vm, guest.capture)? != encoded {
        return Err("raw capture destroyed during dispatch".to_owned());
    }
    Ok(encoded)
}

fn reset(
    vm: &mut ProfileMachine,
    guest: &RelocatedRecurrentCaptureSource,
    encoded: u32,
) -> Result<(), String> {
    select(vm, guest, 7_180_670, 7_176_999)?;
    let mut current = encoded;
    for ((site, address), constant) in
        guest.reset.into_iter().zip(CONSTANTS).zip([ONES, EOF, 0])
    {
        let trace = effect(vm, guest, guest.rotate, b'*')?;
        check_store(&trace, address, constant, constant)?;
        current = fold(vm, guest, (site, guest.capture), (current, constant))?;
    }
    if current != ONES || word(vm, guest.capture)? != ONES {
        return Err("dirty capture reset failed".to_owned());
    }
    Ok(())
}

fn stop(
    vm: &mut ProfileMachine,
    guest: &RelocatedRecurrentCaptureSource,
    class: u32,
    parity: u8,
) -> Result<(), String> {
    let load = effect(vm, guest, prev(guest.output)?, b'*')?;
    check_store(
        &load,
        plus(class, 2)?,
        u32::from(parity).checked_mul(3).ok_or("parity overflow")?,
        u32::from(parity),
    )?;
    let output = effect(vm, guest, guest.output, b'<')?;
    if output.output != Some(parity)
        || output.input.is_some()
        || output.memory_delta.data.is_some()
    {
        return Err(format!("wrong terminal output: {output:?}"));
    }
    let mut record = None;
    let outcome = vm
        .step_traced(&mut |entry| record = Some(*entry))
        .map_err(|error| error.to_string())?;
    let trace = record.ok_or("missing halt trace")?;
    if outcome != StepOutcome::Terminated(Termination::HaltInstruction)
        || trace.before.registers.code_pointer != guest.halt
        || trace.decoded != Some(b'v')
        || trace.input.is_some()
        || trace.output.is_some()
        || trace.memory_delta.data.is_some()
        || word(vm, guest.capture)? != EOF
    {
        return Err(format!("wrong physical EOF halt: {trace:?}"));
    }
    Ok(())
}

fn run(
    boot: &ProfileMachine,
    guest: &RelocatedRecurrentCaptureSource,
    stream: &[u8],
) -> Result<(), String> {
    let mut vm = boot
        .fork_with_input(stream.to_vec())
        .map_err(|error| error.to_string())?;
    let mut state = INITIAL;
    for byte in stream {
        let encoded =
            cycle(&mut vm, guest, &mut state, (TraceInput::Byte(*byte), BYTE))?;
        reset(&mut vm, guest, encoded)?;
    }
    let odd = stream.len() & 1 == 1;
    let class = if odd {
        EOF_ODD
    } else {
        EOF_EVEN
    };
    let encoded =
        cycle(&mut vm, guest, &mut state, (TraceInput::EndOfInput, class))?;
    if encoded != EOF {
        return Err("lost EOF word".to_owned());
    }
    stop(&mut vm, guest, class, u8::from(odd))?;
    if vm.input_consumed() != stream.len() || vm.output() != [u8::from(odd)] {
        return Err("wrong terminal I/O".to_owned());
    }
    Ok(())
}

#[test]
fn relocated_recurrent_capture_all_bytes_and_both_eof_landings()
-> Result<(), String> {
    let guest = source()?;
    if guest.source.len() != 1_660_196 {
        return Err("recurrent capture image size regressed".to_owned());
    }
    let boot = enter(&guest, BOOT_BUDGET)?;
    for stream in [
        vec![],
        vec![255],
        vec![0, 255],
        (0..=255).collect(),
        (0..=255).rev().chain([42]).collect(),
    ] {
        run(&boot, &guest, &stream)?;
    }
    Ok(())
}

fn digit(value: u32, place: u32) -> u32 {
    value
        .checked_div(3u32.pow(place))
        .unwrap_or_default()
        .checked_rem(3)
        .unwrap_or_default()
}

fn digit_fold(mut state: [u32; 6], mut input: u32) -> [u32; 6] {
    for value in &mut state {
        input = digit(independent_crazy(*value, input), 0);
        *value = input;
    }
    state
}

const fn last(state: [u32; 6]) -> u32 {
    let [_, _, _, _, _, last] = state;
    last
}

fn check_constant_digit(place: u32) -> Result<(), String> {
    let mut seen = BTreeSet::new();
    let mut pending = vec![INITIAL.map(|word| digit(word, place))];
    while let Some(state) = pending.pop() {
        if !seen.insert(state) {
            continue;
        }
        for input in 0..3u32 {
            let next = digit_fold(state, input);
            if last(next) != digit(BYTE, place) {
                return Err(format!("nonconstant classifier trit {place}"));
            }
            pending.push(next);
        }
    }
    Ok(())
}

#[test]
fn relocated_recurrent_capture_classifier_is_closed() -> Result<(), String> {
    for place in (0..15u32).filter(|place| ![6, 7].contains(place)) {
        check_constant_digit(place)?;
    }
    let mut high = [
        INITIAL.map(|word| digit(word, 6)),
        INITIAL.map(|word| digit(word, 7)),
    ];
    let mut odd = false;
    let mut seen = BTreeSet::new();
    let mut landings = BTreeSet::new();
    while seen.insert((high, odd)) {
        let eof = high.map(|state| last(digit_fold(state, 2)));
        let class = if odd {
            EOF_ODD
        } else {
            EOF_EVEN
        };
        if eof != [digit(class, 6), digit(class, 7)] {
            return Err("wrong encoded EOF parity trits".to_owned());
        }
        let _: bool = landings.insert(class);
        high = high.map(|state| digit_fold(state, 1));
        odd = !odd;
        if high.map(last) != [1, 1] {
            return Err("encoded byte changed route".to_owned());
        }
    }
    if landings != BTreeSet::from([EOF_ODD, EOF_EVEN]) {
        return Err("missing EOF landing".to_owned());
    }
    for input in 0..3u32 {
        let encoded = digit(independent_crazy(1, input), 0);
        let decoded = digit(independent_crazy(1, encoded), 0);
        let reset = [1, 2, 0].into_iter().fold(encoded, |old, accumulator| {
            digit(independent_crazy(old, accumulator), 0)
        });
        if decoded != input || reset != 1 {
            return Err("capture inverse or dirty reset failed".to_owned());
        }
    }
    Ok(())
}

#[test]
fn relocated_recurrent_capture_omitted_output_refuses() -> Result<(), String> {
    let mut guest = source()?;
    let noop = (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), guest.output)
                == Some(b'o')
        })
        .ok_or("missing canonical noop")?;
    *guest
        .source
        .get_mut(
            usize::try_from(guest.output).map_err(|error| error.to_string())?,
        )
        .ok_or("missing output cell")? = noop;
    let boot = enter(&guest, BOOT_BUDGET)?;
    if run(&boot, &guest, &[0, 255]).is_ok() {
        return Err("accepted omitted physical EOF output".to_owned());
    }
    Ok(())
}

#[test]
fn relocated_recurrent_capture_refuses_other_profile() {
    assert_eq!(
        build_relocated_recurrent_capture_source(historical_profile()),
        Err(ZeroCellSourceError::UnsupportedProfile)
    );
}
