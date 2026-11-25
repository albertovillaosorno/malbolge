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
    ProfileMachine, ProfileStepTrace, RunOutcome, StepOutcome, Termination,
    TraceInput, current_profile, decode_profile_instruction,
    historical_profile,
};

use super::super::super::super::layout::{
    RelocatedRecurrentChecksumSource, ZeroCellSourceError,
    build_relocated_recurrent_checksum_source,
};
use super::{
    BYTE, EOF, EOF_EVEN, EOF_ODD, INITIAL, ONES, check_store, cycle,
    independent_crazy, invariant, plus, routing, step, word,
};

const BOOT_BUDGET: usize = 4_000_000;
const BYTE_BUDGET: usize = 13_000;
const PUBLICATION_BUDGET: usize = 100_000;
const RAW_TABLES: [u32; 2] = [7_208_352, 7_209_081];
const RAW_SEEDS: [u32; 2] = [7_211_000, 7_211_200];
const LOW_TABLE: u32 = 7_242_615;
const LOW_SEEDS: u32 = 7_243_100;
const HIGH_SEEDS: u32 = 7_243_400;
const HIGH_TABLE: u32 = 7_223_661;
const EOF_SCRATCH: u32 = 7_180_900;

type ArithmeticVisit = (u32, u32);
type BootReplay = (ProfileMachine, usize);
type HighEdge = (u8, u8, u8, u32);
type LowEdge = (u8, u8);
type FactoredEdges = (LowEdge, HighEdge);
type FrozenVectors = [(&'static [u8], usize); 5];

struct ByteAudit {
    addresses: [u32; 5],
    commits: Vec<u32>,
    effects: Vec<ArithmeticVisit>,
    next: u8,
    observed: usize,
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
        if self.observed != self.effects.len()
            || self.reads != self.sites.len()
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
            effects: expected_arithmetic(guest, addresses)?,
            next,
            observed: 0,
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
        let visit = (site, before.data_pointer);
        if self.effects.get(self.observed) != Some(&visit) {
            return Err(format!(
                "unexpected arithmetic visit C{} M{}",
                visit.0, visit.1
            ));
        }
        self.observed = self.observed.checked_add(1).ok_or("effect count")?;
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

// Enumerate exact arithmetic visits independently of the route builder.
// Any extra write, even through a legitimate reusable instruction, refuses.
fn expected_arithmetic(
    guest: &RelocatedRecurrentChecksumSource,
    addresses: [u32; 5],
) -> Result<Vec<ArithmeticVisit>, String> {
    let capture = &guest.capture;
    let [low, high] = guest.state;
    let [pl, ph] = guest.pointers;
    let [first, second] = guest.load;
    let mut visits = vec![
        (capture.rotate, 7_180_800),
        (first, capture.capture),
        (first, pl),
        (capture.rotate, 7_180_812),
    ];
    lookup_visits(&mut visits, guest.lookup[0], addresses[0])?;
    visits.extend([(first, low), (capture.rotate, 7_180_816)]);
    lookup_visits(&mut visits, guest.lookup[1], addresses[1])?;
    visits.extend([
        (first, high),
        (capture.rotate, 7_180_804),
        (capture.reset[2], capture.capture),
        (capture.rotate, 7_180_808),
        (second, capture.capture),
        (first, ph),
        (capture.rotate, 7_180_820),
    ]);
    lookup_visits(&mut visits, guest.lookup[2], addresses[2])?;
    visits.extend([(second, high), (capture.rotate, 7_180_824)]);
    lookup_visits(&mut visits, guest.lookup[3], addresses[3])?;
    commit_visits(&mut visits, guest, (high, guest.scratch[1]), [
        7_180_836, 7_180_844,
    ]);
    visits.push((capture.rotate, 7_180_828));
    lookup_visits(&mut visits, guest.lookup[4], addresses[4])?;
    commit_visits(&mut visits, guest, (low, guest.scratch[0]), [
        7_180_832, 7_180_840,
    ]);
    reset_visits(&mut visits, guest, capture.capture, 7_175_040);
    for (pointer, constant, prefix, seed) in [
        (pl, 7_180_848, 7_180_872, 7_180_876),
        (ph, 7_180_852, 7_180_880, 7_180_884),
    ] {
        reset_visits(&mut visits, guest, pointer, constant);
        visits.extend([
            (capture.crazy, prefix),
            (capture.crazy, seed),
            (capture.crazy, pointer),
        ]);
    }
    Ok(visits)
}

fn lookup_visits(
    visits: &mut Vec<ArithmeticVisit>,
    sites: [u32; 2],
    address: u32,
) -> Result<(), String> {
    visits.extend([(sites[0], address), (sites[1], plus(address, 1)?)]);
    Ok(())
}

fn reset_visits(
    visits: &mut Vec<ArithmeticVisit>,
    guest: &RelocatedRecurrentChecksumSource,
    address: u32,
    constant: u32,
) {
    let capture = &guest.capture;
    visits.extend([
        (capture.rotate, constant),
        (capture.reset[0], address),
        (capture.reset[1], address),
    ]);
}

fn commit_visits(
    visits: &mut Vec<ArithmeticVisit>,
    guest: &RelocatedRecurrentChecksumSource,
    (state, scratch): (u32, u32),
    [state_constant, scratch_constant]: [u32; 2],
) {
    let capture = &guest.capture;
    visits.push((capture.crazy, scratch));
    reset_visits(visits, guest, state, state_constant);
    visits.extend([(guest.scratch_rotate, scratch), (capture.reset[2], state)]);
    reset_visits(visits, guest, scratch, scratch_constant);
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
    boot_with_steps(guest).map(|(vm, _)| vm)
}

fn boot_with_steps(
    guest: &RelocatedRecurrentChecksumSource,
) -> Result<BootReplay, String> {
    let mut vm = ProfileMachine::from_source(
        current_profile(),
        &guest.capture.source,
        Vec::new(),
    )
    .map_err(|error| error.to_string())?;
    for steps in 0..BOOT_BUDGET {
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
            return Ok((vm, steps));
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

fn check_pointer(
    vm: &ProfileMachine,
    address: u32,
    landing: u32,
) -> Result<(), String> {
    if plus(word(vm, address)?, 1)? != landing {
        return Err(format!("wrong materialized table pointer M{address}"));
    }
    Ok(())
}

fn immutable_value(vm: &ProfileMachine, address: u32) -> Result<u32, String> {
    let prefix = word(vm, address)?;
    let value = word(vm, plus(address, 1)?)?;
    if independent_crazy(prefix, ONES) != prefix
        || independent_crazy(value, prefix) != value
    {
        return Err(format!("unstable materialized pair M{address}"));
    }
    Ok(value)
}

fn high_table_address(
    (state, raw, parity, carry): HighEdge,
) -> Result<u32, String> {
    let row = mul(u32::from(state), 729)?;
    let column = plus(
        mul(carry, 81)?,
        plus(mul(u32::from(parity), 27)?, u32::from(raw))?,
    )?;
    plus(plus(HIGH_TABLE, 487)?, plus(row, column)?)
}

fn check_materialized_transition(
    vm: &ProfileMachine,
    (prior, raw): (u8, u8),
) -> Result<(), String> {
    let update = checksum(prior, raw);
    let intermediate = low_intermediate(prior, raw)?;
    let low = plus(LOW_TABLE, mul(plus(u32::from(prior & 15), 1)?, 27)?)?
        .checked_sub(u32::from(raw & 15))
        .ok_or("low table address")?;
    let low_record = record(LOW_SEEDS, intermediate, 0)?;
    check_pointer(vm, low, low_record)?;
    check_pointer(vm, low_record, plus(low_record, 4)?)?;
    let high = high_table_address(edges(prior, raw)?.1)?;
    let high_record = record(HIGH_SEEDS, u32::from(update >> 4u32), 0)?;
    check_pointer(vm, high, high_record)?;
    let low_result = rotate_right(immutable_value(vm, plus(low_record, 4)?)?)?;
    let high_result = rotate_right(immutable_value(vm, high_record)?)?;
    if low_result != low_mask(update)? || high_result != high_mask(update)? {
        return Err(
            "materialized transition does not commit the full checksum"
                .to_owned(),
        );
    }
    let carry = intermediate.div_euclid(16);
    let expected_carry = match carry {
        0 => EOF.checked_sub(81).ok_or("carry zero")?,
        1 => EOF,
        2 => EOF.checked_sub(162).ok_or("carry two")?,
        _ => return Err("impossible carry".to_owned()),
    };
    if immutable_value(vm, plus(low_record, 1)?)? != expected_carry {
        return Err("materialized carry differs from full checksum".to_owned());
    }
    Ok(())
}

fn check_materialized_tables(vm: &ProfileMachine) -> Result<(), String> {
    // Every raw selector and every full-state/raw-byte combination is
    // checked against actual guest memory, not a copy of the host plan.
    for raw in 0..=255u8 {
        for (table, seeds, index) in [
            (RAW_TABLES[0], RAW_SEEDS[0], u32::from(raw & 15)),
            (
                RAW_TABLES[1],
                RAW_SEEDS[1],
                plus(mul(u32::from(raw >> 4u32), 2)?, u32::from(raw & 1))?,
            ),
        ] {
            let address = plus(table, 729)?
                .checked_sub(u32::from(raw))
                .ok_or("raw table address")?;
            check_pointer(vm, address, record(seeds, index, 0)?)?;
        }
        for state in 0..=255u8 {
            check_materialized_transition(vm, (state, raw))?;
        }
    }
    // The 256 impossible odd-byte carry-two slots remain loader words.
    for state in 0..16u8 {
        for raw in 0..16u8 {
            let address = high_table_address((state, raw, 1, 2))?;
            let virgin = if address.is_multiple_of(2) {
                7_174_416
            } else {
                37
            };
            if word(vm, address)? != virgin {
                return Err(format!(
                    "impossible carry slot materialized M{address}"
                ));
            }
        }
    }
    Ok(())
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

// Independent physical audit of the two-hop seed directory. The address
// bank is intentionally not obtained from the production planner.
fn check_seed_directory(vm: &ProfileMachine) -> Result<(), String> {
    let mut address = 7_176_721;
    if word(vm, 7_174_489)? != 7_176_720 {
        return Err("missing seed directory root".to_owned());
    }
    for (start, end) in
        [(7_174_611u32, 7_174_970u32), (7_175_601u32, 7_176_600u32)]
    {
        for base in (start..end).step_by(32) {
            if word(vm, address)?
                != base.checked_sub(1).ok_or("directory base")?
                || word(vm, plus(address, 1)?)? != 7_174_416
            {
                return Err(format!("incorrect seed directory M{address}"));
            }
            address = plus(address, 2)?;
        }
    }
    Ok(())
}

// The target pages point at distinct bases within the recurrent data
// plan, not at their own bank or the bootstrap scratch space.
fn check_target_directory(vm: &ProfileMachine) -> Result<(), String> {
    let mut targets = BTreeSet::new();
    for (root, bank) in [(7_174_491u32, 7_300_001u32), (7_174_493, 7_300_201)] {
        if word(vm, root)? != bank.checked_sub(1).ok_or("target root")? {
            return Err("incorrect target directory root".to_owned());
        }
        for offset in 0..48u32 {
            let slot = plus(bank, mul(offset, 2)?)?;
            let target = plus(word(vm, slot)?, 1)?;
            if !(7_175_000..7_244_000).contains(&target)
                || !targets.insert(target)
                || word(vm, plus(slot, 1)?)? != 7_174_416
            {
                return Err(format!("incorrect target directory M{slot}"));
            }
        }
    }
    for root in (7_174_495..7_174_601).step_by(2) {
        let target = plus(word(vm, root)?, 1)?;
        if !(7_175_000..7_244_000).contains(&target)
            || !targets.insert(target)
            || word(vm, plus(root, 1)?)? != 7_174_416
        {
            return Err(format!("incorrect direct target M{root}"));
        }
    }
    if targets.len() != 149 {
        return Err("missing target directory partition".to_owned());
    }
    Ok(())
}

#[test]
fn relocated_recurrent_checksum_all_factored_edges_and_eof()
-> Result<(), String> {
    let guest = source()?;
    let initial = boot(&guest)?;
    check_materialized_tables(&initial)?;
    check_seed_directory(&initial)?;
    check_target_directory(&initial)?;
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
fn relocated_recurrent_checksum_frozen_vectors_and_step_budget()
-> Result<(), String> {
    // The exact binary vectors from tests/test_eof_checksum_pipeline.py.
    // These budgets exclude the bootstrap and are not publication limits.
    let vectors: FrozenVectors = [
        (&[], 446),
        (&[0], 11_859),
        (&[255], 11_859),
        (&[1, 0, 128, 254], 46_098),
        (&[5, 0, 129], 34_685),
    ];
    let guest = source()?;
    if guest.capture.source.len() != 4_091_694 {
        return Err("unexpected recurrent source extent".to_owned());
    }
    let (initial, bootstrap_steps) = boot_with_steps(&guest)?;
    check_seed_directory(&initial)?;
    check_target_directory(&initial)?;
    // This is a physical witness, not yet source-C publication.
    if bootstrap_steps <= PUBLICATION_BUDGET {
        return Err("publication budget evidence must be revisited".to_owned());
    }
    let mut limited = ProfileMachine::from_source(
        current_profile(),
        &guest.capture.source,
        Vec::new(),
    )
    .map_err(|error| error.to_string())?;
    if limited
        .run(PUBLICATION_BUDGET)
        .map_err(|error| error.to_string())?
        != (RunOutcome::BudgetExhausted {
            steps: PUBLICATION_BUDGET,
        })
        || limited.input_consumed() != 0
        || !limited.output().is_empty()
    {
        return Err("publication budget must exhaust before I/O".to_owned());
    }
    for (stream, budget) in vectors {
        let mut vm = initial
            .fork_with_input(stream.to_vec())
            .map_err(|error| error.to_string())?;
        let expected = stream.iter().copied().fold(0u8, checksum);
        let outcome = vm.run(budget).map_err(|error| error.to_string())?;
        if !matches!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            ..
        }) || vm.input_consumed() != stream.len()
            || vm.output() != [expected]
        {
            return Err(format!(
                "frozen vector failed: {stream:?}: {outcome:?}"
            ));
        }
    }
    Ok(())
}

fn omit_site(
    guest: &RelocatedRecurrentChecksumSource,
    site: u32,
) -> Result<RelocatedRecurrentChecksumSource, String> {
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
    Ok(modified)
}

fn materialization_site(
    guest: &RelocatedRecurrentChecksumSource,
    (address, value): (u32, u32),
) -> Result<u32, String> {
    let mut vm = ProfileMachine::from_source(
        current_profile(),
        &guest.capture.source,
        Vec::new(),
    )
    .map_err(|error| error.to_string())?;
    for _ in 0..BOOT_BUDGET {
        let registers = vm.registers();
        let candidate = registers.data_pointer == address
            && decode_profile_instruction(
                word(&vm, registers.code_pointer)?,
                registers.code_pointer,
            ) == Some(b'p')
            && word(&vm, address)? != value;
        if vm.step().map_err(|error| error.to_string())?
            != StepOutcome::Continued
        {
            return Err("premature bootstrap termination".to_owned());
        }
        if candidate && word(&vm, address)? == value {
            return Ok(registers.code_pointer);
        }
    }
    Err("missing materialized table store".to_owned())
}

#[test]
fn relocated_recurrent_checksum_omitted_target_page_refuses()
-> Result<(), String> {
    let guest = source()?;
    let initial = boot(&guest)?;
    check_target_directory(&initial)?;
    let page = 7_300_001;
    let site = materialization_site(&guest, (page, word(&initial, page)?))?;
    let modified = omit_site(&guest, site)?;
    if let Ok(mutated) = boot(&modified) {
        if check_target_directory(&mutated).is_ok() {
            return Err("accepted omitted target page".to_owned());
        }
        if check_materialized_tables(&mutated).is_ok()
            && run(&mutated, &modified, &[0, 255]).is_ok()
        {
            return Err(
                "target page mutation did not affect a used route".to_owned()
            );
        }
    }
    Ok(())
}

#[test]
fn relocated_recurrent_checksum_omitted_directory_store_refuses()
-> Result<(), String> {
    let guest = source()?;
    // Second near seed page: it is actually selected by the shorter
    // two-hop path, not merely allocated as unused bootstrap data.
    let site = materialization_site(&guest, (7_176_723, 7_174_642))?;
    let modified = omit_site(&guest, site)?;
    if let Ok(initial) = boot(&modified) {
        if check_seed_directory(&initial).is_ok() {
            return Err("accepted omitted seed-directory store".to_owned());
        }
        if check_materialized_tables(&initial).is_ok()
            && run(&initial, &modified, &[0, 255]).is_ok()
        {
            return Err(
                "directory mutation did not affect used route".to_owned()
            );
        }
    }
    Ok(())
}

#[test]
fn relocated_recurrent_checksum_omitted_table_store_refuses()
-> Result<(), String> {
    let guest = source()?;
    let target = high_table_address((0, 0, 0, 0))?;
    let landing = record(HIGH_SEEDS, 0, 0)?;
    let site = materialization_site(
        &guest,
        (target, landing.checked_sub(1).ok_or("table pointer")?),
    )?;
    let modified = omit_site(&guest, site)?;
    let initial = boot(&modified)?;
    // The mutated guest reaches its normal first input, but the missing
    // high-table store must invalidate both the table audit and execution.
    if check_pointer(&initial, target, landing).is_ok()
        || check_materialized_tables(&initial).is_ok()
        || run(&initial, &modified, &[0]).is_ok()
    {
        return Err("accepted omitted high-table materialization".to_owned());
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
        let modified = omit_site(&guest, site)?;
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
