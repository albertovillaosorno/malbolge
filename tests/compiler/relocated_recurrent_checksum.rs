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
//   - Independent execution of the complete physical byte recurrence.
// - Must-Not:
//   - Admit the source-C CFG or claim the publication resource bound.
// - Allows:
//   - Inputs: generated guest and independently computed checksum.
//   - Outputs: normative VM traces and finite evidence.
//   - Side effects: isolated guest execution.
// - Split-When:
//   - Source-bound verifier owns full arithmetic effect admission.
// - Merge-When:
//   - Source-C recurrent compiler regression owns this witness.
// - Summary:
//   - Authenticate carry-aware byte state, EOF and output.

use std::collections::BTreeSet;

use malbolge::{
    ProfileMachine, ProfileStepTrace, StepOutcome, Termination, TraceInput,
    current_profile, decode_profile_instruction, historical_profile,
};

use super::super::super::super::layout::{
    RelocatedRecurrentChecksumSource, ZeroCellSourceError,
    build_relocated_recurrent_checksum_source,
};
use super::{
    BYTE, EOF, EOF_EVEN, EOF_ODD, INITIAL, ONES, check_store, cycle,
    independent_crazy, invariant, plus, routing, step, word,
};

const BOOT_BUDGET: usize = 6_540_044;
const BYTE_BUDGET: usize = 13_000;
const RAW_TABLES: [u32; 2] = [7_208_352, 7_209_081];
const RAW_SEEDS: [u32; 2] = [7_211_000, 7_211_200];
const LOW_TABLE: u32 = 7_242_615;
const LOW_SEEDS: u32 = 7_243_100;
const HIGH_SEEDS: u32 = 7_243_400;
const EOF_SCRATCH: u32 = 7_180_900;

type HighEdge = (u8, u8, u8, u32);
type LowEdge = (u8, u8);
type FactoredEdges = (LowEdge, HighEdge);

struct ByteAudit {
    addresses: [u32; 5],
    commits: Vec<u32>,
    next: u8,
    reads: usize,
    rotations: Vec<u32>,
    sites: Vec<u32>,
}

impl ByteAudit {
    fn finish(
        &self,
        vm: &ProfileMachine,
        guest: &RelocatedRecurrentChecksumSource,
    ) -> Result<(), String> {
        if self.reads != self.sites.len()
            || self.commits != [guest.state[1], guest.state[0]]
            || self.rotations != [guest.scratch[1], guest.scratch[0]]
        {
            return Err(
                "missing or reordered recurrent arithmetic effect".to_owned()
            );
        }
        persistent(vm, guest, self.next)
    }

    fn new(
        guest: &RelocatedRecurrentChecksumSource,
        (prior, byte): (u8, u8),
    ) -> Result<Self, String> {
        let next = checksum(prior, byte);
        let intermediate = low_intermediate(prior, byte)?;
        let sites = guest.lookup.into_iter().flatten().collect::<Vec<_>>();
        let addresses = [
            record(RAW_SEEDS[0], u32::from(byte & 15), 0)?,
            record(LOW_SEEDS, intermediate, 1)?,
            record(
                RAW_SEEDS[1],
                plus(mul(u32::from(byte >> 4u32), 2)?, u32::from(byte & 1))?,
                0,
            )?,
            record(HIGH_SEEDS, u32::from(next >> 4u32), 0)?,
            record(LOW_SEEDS, intermediate, 4)?,
        ];
        Ok(Self {
            addresses,
            commits: Vec::new(),
            next,
            reads: 0,
            rotations: Vec::new(),
            sites,
        })
    }

    fn observe(
        &mut self,
        trace: &ProfileStepTrace,
        guest: &RelocatedRecurrentChecksumSource,
    ) -> Result<(), String> {
        let before = trace.before.registers;
        let site = before.code_pointer;
        let old = trace
            .memory_reads
            .data
            .ok_or("missing arithmetic operand")?
            .value;
        let new = if trace.decoded == Some(b'p') {
            independent_crazy(old, before.accumulator)
        } else {
            rotate_right(old)?
        };
        check_store(trace, before.data_pointer, old, new)?;
        let original = guest
            .capture
            .source
            .get(usize::try_from(site).map_err(|error| error.to_string())?)
            .copied()
            .map(u32::from);
        if trace.fetched_cell != original {
            return Err(format!("dirty arithmetic code C{site}"));
        }
        if self.sites.contains(&site) {
            self.observe_lookup(trace, old == new)?;
        } else if site == guest.capture.reset[2]
            && guest.state.contains(&before.data_pointer)
        {
            self.observe_commit(guest, before.data_pointer, new)?;
        } else if site == guest.scratch_rotate {
            self.rotations.push(before.data_pointer);
        } else if site != guest.capture.crazy
            && site != guest.capture.rotate
            && !guest.capture.reset.contains(&site)
            && !guest.load.contains(&site)
        {
            return Err(format!("unexpected arithmetic site C{site}"));
        }
        Ok(())
    }

    fn observe_commit(
        &mut self,
        guest: &RelocatedRecurrentChecksumSource,
        address: u32,
        new: u32,
    ) -> Result<(), String> {
        let expected = if address == guest.state[0] {
            low_mask(self.next)?
        } else {
            high_mask(self.next)?
        };
        if new != expected {
            return Err("wrong full-byte commit".to_owned());
        }
        self.commits.push(address);
        Ok(())
    }

    fn observe_lookup(
        &mut self,
        trace: &ProfileStepTrace,
        immutable: bool,
    ) -> Result<(), String> {
        let expected = self.sites.get(self.reads).ok_or("extra lookup")?;
        let address = plus(
            *self
                .addresses
                .get(self.reads.div_euclid(2))
                .ok_or("lookup address")?,
            u32::try_from(self.reads.rem_euclid(2))
                .map_err(|error| error.to_string())?,
        )?;
        let before = trace.before.registers;
        if before.code_pointer != *expected
            || before.data_pointer != address
            || !immutable
        {
            return Err(format!(
                "wrong immutable lookup {}: {trace:?}",
                self.reads
            ));
        }
        self.reads = self.reads.checked_add(1).ok_or("read count")?;
        Ok(())
    }
}

fn source() -> Result<RelocatedRecurrentChecksumSource, String> {
    build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("full checksum source: {error:?}"))
}

const fn checksum(state: u8, byte: u8) -> u8 {
    if byte & 1 == 0 {
        state.wrapping_add(byte).wrapping_add(3)
    } else {
        (state ^ byte).wrapping_add(3)
    }
}

fn mul(left: u32, right: u32) -> Result<u32, String> {
    left.checked_mul(right)
        .ok_or_else(|| "multiply overflow".to_owned())
}

fn low_intermediate(state: u8, byte: u8) -> Result<u32, String> {
    let low = u32::from(state & 15);
    let raw = u32::from(byte & 15);
    plus(
        if byte & 1 == 0 {
            plus(low, raw)?
        } else {
            low ^ raw
        },
        3,
    )
}

fn low_mask(state: u8) -> Result<u32, String> {
    plus(
        independent_crazy(
            plus(LOW_TABLE, mul(u32::from(state & 15), 27)?)?,
            EOF,
        ),
        13,
    )
}

fn high_mask(state: u8) -> Result<u32, String> {
    plus(14_329_871, mul(u32::from(state >> 4u32), 729)?)
}

fn raw_mask(table: u32) -> Result<u32, String> {
    plus(independent_crazy(table, EOF), 364)
}

fn record(base: u32, index: u32, offset: u32) -> Result<u32, String> {
    plus(plus(base, mul(index, 8)?)?, offset)
}

fn is_input(
    vm: &ProfileMachine,
    guest: &RelocatedRecurrentChecksumSource,
) -> Result<bool, String> {
    let address = guest.capture.input;
    Ok(vm.registers().code_pointer == address
        && decode_profile_instruction(word(vm, address)?, address)
            == Some(b'/'))
}

fn persistent(
    vm: &ProfileMachine,
    guest: &RelocatedRecurrentChecksumSource,
    state: u8,
) -> Result<(), String> {
    let [low, high] = guest.state;
    if word(vm, low)? != low_mask(state)?
        || word(vm, high)? != high_mask(state)?
    {
        return Err(format!(
            "incorrect full-byte state {state}: low={} high={}",
            word(vm, low)?,
            word(vm, high)?
        ));
    }
    for (pointer, table) in guest.pointers.into_iter().zip(RAW_TABLES) {
        if word(vm, pointer)? != raw_mask(table)? {
            return Err("raw index mask not restored".to_owned());
        }
    }
    for scratch in guest.scratch {
        if word(vm, scratch)? != ONES {
            return Err("scratch not restored".to_owned());
        }
    }
    if !vm.output().is_empty() {
        return Err("premature output".to_owned());
    }
    Ok(())
}

fn boot(
    guest: &RelocatedRecurrentChecksumSource,
) -> Result<ProfileMachine, String> {
    let mut vm = ProfileMachine::from_source(
        current_profile(),
        &guest.capture.source,
        Vec::new(),
    )
    .map_err(|error| error.to_string())?;
    for _ in 0..BOOT_BUDGET {
        if is_input(&vm, guest)? {
            invariant(&vm, &guest.capture, INITIAL)?;
            persistent(&vm, guest, 0)?;
            if vm.input_consumed() != 0
                || word(&vm, 7_174_417)? != 7_174_468
                || word(&vm, 7_174_469)? != ONES
                || word(&vm, 7_174_471)? != 0
                || word(&vm, 7_174_473)? != EOF
            {
                return Err("incorrect bootstrap reset geometry".to_owned());
            }
            return Ok(vm);
        }
        if vm.step().map_err(|error| error.to_string())?
            != StepOutcome::Continued
        {
            return Err("premature bootstrap termination".to_owned());
        }
    }
    Err("missing full checksum input".to_owned())
}

fn rotate_right(word: u32) -> Result<u32, String> {
    plus(word.div_euclid(3), mul(word.rem_euclid(3), 4_782_969)?)
}

fn byte_route(
    vm: &mut ProfileMachine,
    guest: &RelocatedRecurrentChecksumSource,
    (prior, byte): (u8, u8),
) -> Result<(), String> {
    let mut audit = ByteAudit::new(guest, (prior, byte))?;
    for _ in 0..BYTE_BUDGET {
        if is_input(vm, guest)? {
            audit.finish(vm, guest)?;
            return Ok(());
        }
        let trace = step(vm)?;
        match trace.decoded {
            Some(b'p' | b'*') => audit.observe(&trace, guest)?,
            _ => routing(&trace, u32::MAX)?,
        }
    }
    Err("byte route did not return to input".to_owned())
}

fn finish(
    vm: &mut ProfileMachine,
    guest: &RelocatedRecurrentChecksumSource,
    expected: u8,
) -> Result<(), String> {
    let mut output = false;
    let mut staged = false;
    for _ in 0..256u32 {
        let mut record = None;
        let outcome = vm
            .step_traced(&mut |trace| record = Some(*trace))
            .map_err(|error| error.to_string())?;
        let trace = record.ok_or("missing EOF trace")?;
        let before = trace.before.registers;
        if trace.input.is_some() {
            return Err("input after EOF".to_owned());
        }
        if before.data_pointer == EOF_SCRATCH && trace.decoded == Some(b'p') {
            if staged
                && trace.after.registers.accumulator.rem_euclid(256)
                    != u32::from(expected)
            {
                return Err("wrong staged full byte".to_owned());
            }
            staged = true;
        }
        if let Some(byte) = trace.output {
            if output
                || !staged
                || before.code_pointer != guest.capture.output
                || byte != expected
            {
                return Err(format!(
                    "incorrect EOF output {byte}, expected {expected}"
                ));
            }
            output = true;
        }
        if outcome == StepOutcome::Terminated(Termination::HaltInstruction) {
            if !output
                || before.code_pointer != guest.capture.halt
                || word(vm, guest.capture.capture)? != EOF
            {
                return Err("wrong EOF halt".to_owned());
            }
            return Ok(());
        }
    }
    Err("missing terminal halt".to_owned())
}

fn run(
    boot: &ProfileMachine,
    guest: &RelocatedRecurrentChecksumSource,
    stream: &[u8],
) -> Result<(), String> {
    let mut vm = boot
        .fork_with_input(stream.to_vec())
        .map_err(|error| error.to_string())?;
    let mut classifier = INITIAL;
    let mut state = 0u8;
    for &byte in stream {
        persistent(&vm, guest, state)?;
        let _: u32 = cycle(
            &mut vm,
            &guest.capture,
            &mut classifier,
            (TraceInput::Byte(byte), BYTE),
        )?;
        byte_route(&mut vm, guest, (state, byte))?;
        state = checksum(state, byte);
    }
    let class = if stream.len().is_multiple_of(2) {
        EOF_EVEN
    } else {
        EOF_ODD
    };
    let encoded = cycle(
        &mut vm,
        &guest.capture,
        &mut classifier,
        (TraceInput::EndOfInput, class),
    )?;
    if encoded != EOF {
        return Err("lost EOF".to_owned());
    }
    persistent(&vm, guest, state)?;
    finish(&mut vm, guest, state)?;
    if vm.input_consumed() != stream.len() || vm.output() != [state] {
        return Err("wrong final full-byte I/O".to_owned());
    }
    Ok(())
}

fn edges(state: u8, byte: u8) -> Result<FactoredEdges, String> {
    Ok((
        (state & 15, byte & 15),
        (
            state >> 4u32,
            byte >> 4u32,
            byte & 1,
            low_intermediate(state, byte)?.div_euclid(16),
        ),
    ))
}

fn census() -> Result<Vec<u8>, String> {
    let mut low = BTreeSet::new();
    let mut high = BTreeSet::new();
    let mut stream = Vec::new();
    let mut current = 0u8;
    for state in 0..=255u8 {
        for byte in 0..=255u8 {
            let (low_edge, high_edge) = edges(state, byte)?;
            if low.contains(&low_edge) && high.contains(&high_edge) {
                continue;
            }
            if current != state {
                let bridge = (0..=255u8)
                    .find(|candidate| checksum(current, *candidate) == state)
                    .ok_or("unreachable state")?;
                let (bridge_low, bridge_high) = edges(current, bridge)?;
                let _: bool = low.insert(bridge_low);
                let _: bool = high.insert(bridge_high);
                stream.push(bridge);
            }
            let _: bool = low.insert(low_edge);
            let _: bool = high.insert(high_edge);
            stream.push(byte);
            current = checksum(state, byte);
        }
    }
    if low.len() != 256 || high.len() != 1_280 {
        return Err(format!(
            "incomplete factored census: {} {}",
            low.len(),
            high.len()
        ));
    }
    Ok(stream)
}

#[test]
fn relocated_recurrent_checksum_all_factored_edges_and_eof()
-> Result<(), String> {
    let guest = source()?;
    let initial = boot(&guest)?;
    let stream = census()?;
    run(&initial, &guest, &stream)?;
    run(&initial, &guest, &[])?;
    for expected in 0..=255u8 {
        let second = (0..=255u8)
            .find(|byte| checksum(3, *byte) == expected)
            .ok_or("unreachable even EOF")?;
        run(&initial, &guest, &[expected.wrapping_sub(3)])?;
        run(&initial, &guest, &[0, second])?;
    }
    Ok(())
}

#[test]
fn relocated_recurrent_checksum_omitted_effects_refuse() -> Result<(), String> {
    let guest = source()?;
    for site in [
        guest.lookup[1][1],
        guest.scratch_rotate,
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
        let initial = boot(&modified)?;
        if run(&initial, &modified, &[15, 14, 255]).is_ok() {
            return Err(format!("accepted omitted full-byte effect C{site}"));
        }
    }
    Ok(())
}

#[test]
fn relocated_recurrent_checksum_unsupported_profile_refuses() {
    assert_eq!(
        build_relocated_recurrent_checksum_source(historical_profile()),
        Err(ZeroCellSourceError::UnsupportedProfile)
    );
}
