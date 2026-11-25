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

use std::collections::{BTreeMap, BTreeSet};

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

const BOOT_BUDGET: usize = 1_156_000;
const SEED_RETURN_BASE: u32 = 7_174_614;
const SEED_RETURN_END: u32 = 7_174_930;
const SEED_RETURN_TARGET: u32 = 7_174_491;
const BYTE_BUDGET: usize = 13_000;
const PUBLICATION_BUDGET: usize = 100_000;
const RAW_TABLES: [u32; 2] = [7_208_352, 7_209_081];
const RAW_SEEDS: [u32; 2] = [7_211_000, 7_211_200];
const LOW_TABLE: u32 = 7_242_615;
const LOW_SEEDS: u32 = 7_243_100;
const HIGH_SEEDS: u32 = 7_243_400;
const HIGH_TABLE: u32 = 7_223_661;
const EOF_SCRATCH: u32 = 7_180_900;
const SHORTCUT_ADDRESS: u32 = 7_174_447;
const SHORTCUT_PREDECESSOR: u32 = 7_174_468;

type ArithmeticVisit = (u32, u32);
type DirectoryPage = (u32, u32);
type LocalColumnSites = BTreeMap<u32, u32>;
type BootReplay = (ProfileMachine, usize);
type HighEdge = (u8, u8, u8, u32);
type LowEdge = (u8, u8);
type FactoredEdges = (LowEdge, HighEdge);
type FrozenVectors = [(&'static [u8], usize); 5];
type DirectTargetReceipt = (usize, [u32; 2]);
type ShortcutReceipt = ([u32; 3], usize);
type SharedReadReceipt = ([usize; 3], [u32; 3]);
type VirginSeedCommits = BTreeMap<u32, (u32, u32)>;

#[derive(Clone, Copy)]
enum TargetRouteProgress {
    Page(u32),
    Walk(TargetRoute),
}

#[derive(Clone, Copy)]
struct TargetRoute {
    base: u32,
    cost: u32,
    root: u32,
    slot: Option<u32>,
}

impl TargetRoute {
    fn cost_at(self, address: u32) -> Option<u32> {
        self.cost.checked_add(address.checked_sub(self.base)?)
    }
}

#[derive(Default)]
struct TargetRouteAudit {
    entries: usize,
    installed: BTreeSet<u32>,
    normalization_site: Option<u32>,
    normalization_visits: usize,
    normalized: BTreeSet<u32>,
    page_site: Option<u32>,
    pending: Option<TargetRouteProgress>,
    root_site: Option<u32>,
    selections: usize,
    zero_site: Option<u32>,
    zeroed: BTreeSet<u32>,
}

impl TargetRouteAudit {
    fn end_walk(
        &mut self,
        vm: &mut ProfileMachine,
        routes: &[TargetRoute],
        (route, address, opcode): (TargetRoute, u32, Option<u8>),
    ) -> Result<(), String> {
        let selected = route.cost_at(address).ok_or("backward target route")?;
        let cheapest = routes
            .iter()
            .filter_map(|candidate| candidate.cost_at(address))
            .min()
            .ok_or("uncovered target")?;
        if selected != cheapest || !matches!(opcode, Some(b'p' | b'i')) {
            return Err("nonminimum or unfinished target walk".to_owned());
        }
        if opcode == Some(b'i') {
            routing(&step(vm)?, u32::MAX)?;
            self.entries = self.entries.saturating_add(1);
        } else {
            advance_boot(vm)?;
        }
        self.selections = self.selections.saturating_add(1);
        self.pending = None;
        Ok(())
    }

    fn finish(self) -> Result<[u32; 4], String> {
        if self.entries != 1
            || self.installed.len() != 288
            || self.normalized.len() != 288
            || !self.zeroed.is_empty()
            || self.normalization_visits != 552
            || self.selections != 8_734
            || self.pending.is_some()
        {
            return Err(format!(
                "incomplete target route audit: {}",
                self.selections
            ));
        }
        Ok([
            self.root_site.ok_or("missing target root selection")?,
            self.page_site.ok_or("missing target page selection")?,
            self.normalization_site
                .ok_or("missing page normalization")?,
            self.zero_site.ok_or("missing page zeroing")?,
        ])
    }

    fn install(
        &mut self,
        vm: &mut ProfileMachine,
        routes: &[TargetRoute],
        (address, opcode): (u32, Option<u8>),
    ) -> Result<(), String> {
        if opcode != Some(b'p') {
            return advance_boot(vm);
        }
        let Some(route) =
            routes.iter().find(|route| route.slot == Some(address))
        else {
            return advance_boot(vm);
        };
        let trace = step(vm)?;
        let acc = trace.before.registers.accumulator;
        if !self.normalized.contains(&address) {
            return self.normalize(&trace, address, acc);
        }
        let expected = route.base.checked_sub(1).ok_or("page base")?;
        if self.normalized.len() != 288
            || acc != independent_crazy(ONES, expected)
            || !self.installed.insert(address)
        {
            return Err("invalid target page commit".to_owned());
        }
        check_store(&trace, address, ONES, expected)
    }

    fn normalize(
        &mut self,
        trace: &ProfileStepTrace,
        address: u32,
        acc: u32,
    ) -> Result<(), String> {
        if !self.installed.is_empty() {
            return Err("late target page normalization".to_owned());
        }
        let old = if self.zeroed.contains(&address) {
            0
        } else {
            37
        };
        let site = trace.before.registers.code_pointer;
        match acc {
            0 => {
                check_store(trace, address, old, ONES)?;
                let _removed = self.zeroed.remove(&address);
                let _added = self.normalized.insert(address);
                let _site = self.normalization_site.get_or_insert(site);
            },
            ONES => {
                check_store(trace, address, old, 0)?;
                let _added = self.zeroed.insert(address);
                let _site = self.zero_site.get_or_insert(site);
            },
            _ => {
                return Err(
                    "wrong target page normalization producer".to_owned()
                );
            },
        }
        self.normalization_visits = self.normalization_visits.saturating_add(1);
        Ok(())
    }

    fn observe(
        &mut self,
        vm: &mut ProfileMachine,
        routes: &[TargetRoute],
    ) -> Result<(), String> {
        let registers = vm.registers();
        let address = registers.data_pointer;
        let opcode = decode_profile_instruction(
            word(vm, registers.code_pointer)?,
            registers.code_pointer,
        );
        if self.installed.len() < 288 {
            return self.install(vm, routes, (address, opcode));
        }
        match (self.pending, opcode) {
            (Some(_), Some(b'o')) => routing(&step(vm)?, u32::MAX),
            (Some(TargetRouteProgress::Page(root)), Some(b'j')) => {
                self.page(vm, routes, (root, address))
            },
            (Some(TargetRouteProgress::Page(_)), _) => {
                Err("unfinished target page selection".to_owned())
            },
            (Some(TargetRouteProgress::Walk(route)), _) => {
                self.end_walk(vm, routes, (route, address, opcode))
            },
            (None, Some(b'j')) => {
                if let Some(route) =
                    routes.iter().find(|route| route.root == address)
                {
                    self.root(vm, *route)
                } else {
                    advance_boot(vm)
                }
            },
            (None, _) => advance_boot(vm),
        }
    }

    fn page(
        &mut self,
        vm: &mut ProfileMachine,
        routes: &[TargetRoute],
        (root, address): (u32, u32),
    ) -> Result<(), String> {
        let route = routes
            .iter()
            .find(|route| route.root == root && route.slot == Some(address))
            .ok_or("unlisted target page selection")?;
        let trace = step(vm)?;
        routing(&trace, u32::MAX)?;
        if trace.after.registers.data_pointer != route.base {
            return Err("incorrect target page landing".to_owned());
        }
        let _site = self
            .page_site
            .get_or_insert(trace.before.registers.code_pointer);
        self.pending = Some(TargetRouteProgress::Walk(*route));
        Ok(())
    }

    fn root(
        &mut self,
        vm: &mut ProfileMachine,
        route: TargetRoute,
    ) -> Result<(), String> {
        let trace = step(vm)?;
        routing(&trace, u32::MAX)?;
        let _site = self
            .root_site
            .get_or_insert(trace.before.registers.code_pointer);
        self.pending = Some(if let Some(slot) = route.slot {
            // The roots of the page banks select their respective first
            // entry, before walking to a specific installed slot.
            if trace.after.registers.data_pointer != slot {
                return Err("incorrect target page root".to_owned());
            }
            TargetRouteProgress::Page(route.root)
        } else {
            if trace.after.registers.data_pointer != route.base {
                return Err("incorrect direct target root".to_owned());
            }
            TargetRouteProgress::Walk(route)
        });
        Ok(())
    }
}

#[derive(Clone, Copy)]
struct ClusterVisit {
    accumulator: u32,
    address: u32,
    old: u32,
    site: u32,
}

#[derive(Default)]
struct TargetClusterAudit {
    commits: BTreeSet<u32>,
    even_site: Option<u32>,
    even_targets: BTreeSet<u32>,
    groups: usize,
    normalized: BTreeSet<u32>,
    ones_site: Option<u32>,
    pending_target: Option<u32>,
    reset_site: Option<u32>,
    resets: usize,
    run: Vec<ClusterVisit>,
    visits: usize,
    zero_site: Option<u32>,
    zeroed: BTreeSet<u32>,
}

impl TargetClusterAudit {
    fn finish(mut self, vm: &ProfileMachine) -> Result<[u32; 4], String> {
        self.flush()?;
        check_materialized_tables(vm)?;
        if self.groups != 318
            || self.visits != 8_216
            || self.even_targets.len() != 2_202
            || self.zeroed.len() != 646
            || self.resets != 8_268
            || self.normalized.len() != 4_194
            || self.commits != self.normalized
            || self.pending_target.is_some()
        {
            return Err(
                "missing clustered normalization or final commit".to_owned()
            );
        }
        Ok([
            self.ones_site.ok_or("missing clustered one store")?,
            self.zero_site.ok_or("missing clustered zero store")?,
            self.reset_site.ok_or("missing shared reset")?,
            self.even_site.ok_or("missing clustered even store")?,
        ])
    }

    fn flush(&mut self) -> Result<(), String> {
        if self.run.len() < 2 {
            self.run.clear();
            return Ok(());
        }
        if self.run.len() < 3 {
            return Err("incomplete normalization cluster".to_owned());
        }
        let mut previous = None;
        for (index, visit) in self.run.drain(..).enumerate() {
            if previous.is_some_and(|last: u32| {
                visit.address <= last || visit.address.saturating_sub(last) > 16
            }) || self.normalized.contains(&visit.address)
                || visit.old
                    != if self.zeroed.contains(&visit.address) {
                        0
                    } else if visit.address.is_multiple_of(2) {
                        7_174_416
                    } else {
                        37
                    }
            {
                return Err("invalid normalization cluster operand".to_owned());
            }
            previous = Some(visit.address);
            if visit.address.is_multiple_of(2) {
                let _inserted = self.even_targets.insert(visit.address);
                let _site = self.even_site.get_or_insert(visit.site);
            }
            if index.is_multiple_of(2) && visit.accumulator == 0 {
                let _inserted = self.normalized.insert(visit.address);
                let _removed = self.zeroed.remove(&visit.address);
                let _site = self.ones_site.get_or_insert(visit.site);
            } else if !index.is_multiple_of(2) && visit.accumulator == ONES {
                let _inserted = self.zeroed.insert(visit.address);
                let _site = self.zero_site.get_or_insert(visit.site);
            } else {
                return Err("nonalternating normalization cluster".to_owned());
            }
            self.visits = self.visits.saturating_add(1);
        }
        self.groups = self.groups.saturating_add(1);
        Ok(())
    }

    fn reset(&mut self, vm: &mut ProfileMachine) -> Result<(), String> {
        let target = self
            .pending_target
            .take()
            .ok_or("missing shared reset target")?;
        let trace = step(vm)?;
        let address = trace.before.registers.data_pointer;
        if address <= target
            || !address.is_multiple_of(2)
            || self.even_targets.contains(&address)
            || trace
                .memory_reads
                .data
                .map(|read| (read.address, read.value))
                != Some((address, 7_174_416))
            || trace.after.registers.data_pointer != 7_174_417
        {
            return Err("incorrect shared virgin reset".to_owned());
        }
        routing(&trace, u32::MAX)?;
        let _site = self
            .reset_site
            .get_or_insert(trace.before.registers.code_pointer);
        self.resets = self.resets.saturating_add(1);
        Ok(())
    }

    fn store(&mut self, vm: &mut ProfileMachine) -> Result<(), String> {
        let trace = step(vm)?;
        let address = trace.before.registers.data_pointer;
        let accumulator = trace.before.registers.accumulator;
        let old = trace
            .memory_reads
            .data
            .ok_or("missing cluster operand")?
            .value;
        let new = independent_crazy(old, accumulator);
        check_store(&trace, address, old, new)?;
        self.pending_target = Some(address);
        if matches!(old, 0 | 37 | 7_174_416) && matches!(accumulator, 0 | ONES)
        {
            self.run.push(ClusterVisit {
                accumulator,
                address,
                old,
                site: trace.before.registers.code_pointer,
            });
        } else {
            self.flush()?;
            if self.normalized.contains(&address)
                && (old != ONES || !self.commits.insert(address))
            {
                return Err("incorrect clustered target commit".to_owned());
            }
        }
        Ok(())
    }
}

// The new scratch-to-constants root is installed before its first use.
// Observe every actual selection and require its adjacent reset to stay virgin.
#[derive(Default)]
struct ScratchConstantsAudit {
    commit: Option<u32>,
    jump: Option<u32>,
    normalize: Option<u32>,
    selections: usize,
}

impl ScratchConstantsAudit {
    fn finish(&self, vm: &ProfileMachine) -> Result<ShortcutReceipt, String> {
        if word(vm, SHORTCUT_ADDRESS)? != SHORTCUT_PREDECESSOR
            || word(vm, plus(SHORTCUT_ADDRESS, 1)?)? != 7_174_416
        {
            return Err("scratch constants root changed".to_owned());
        }
        Ok((
            [
                self.normalize.ok_or("missing shortcut normalization")?,
                self.commit.ok_or("missing shortcut commit")?,
                self.jump.ok_or("missing shortcut selection")?,
            ],
            self.selections,
        ))
    }

    fn jump(&mut self, vm: &mut ProfileMachine) -> Result<(), String> {
        let trace = step(vm)?;
        if trace
            .memory_reads
            .data
            .map(|read| (read.address, read.value))
            != Some((SHORTCUT_ADDRESS, SHORTCUT_PREDECESSOR))
            || trace.after.registers.data_pointer
                != plus(SHORTCUT_PREDECESSOR, 1)?
            || trace.after.registers.accumulator
                != trace.before.registers.accumulator
            || trace.memory_delta.data.is_some()
        {
            return Err("incorrect scratch constants jump".to_owned());
        }
        let _first =
            self.jump.get_or_insert(trace.before.registers.code_pointer);
        self.selections = self.selections.saturating_add(1);
        Ok(())
    }

    fn observe(&mut self, vm: &mut ProfileMachine) -> Result<bool, String> {
        let registers = vm.registers();
        if registers.data_pointer != SHORTCUT_ADDRESS {
            return Ok(false);
        }
        match decode_profile_instruction(
            word(vm, registers.code_pointer)?,
            registers.code_pointer,
        ) {
            Some(b'p') if self.normalize.is_none() => {
                if registers.accumulator != 0 {
                    return Err("wrong shortcut normalization".to_owned());
                }
                check_store(&step(vm)?, SHORTCUT_ADDRESS, 37, ONES)?;
                self.normalize = Some(registers.code_pointer);
            },
            Some(b'p') if self.commit.is_none() => {
                let inverse = independent_crazy(ONES, SHORTCUT_PREDECESSOR);
                if registers.accumulator != inverse
                    || word(vm, 7_174_441)? != inverse
                {
                    return Err("wrong shortcut producer".to_owned());
                }
                check_store(
                    &step(vm)?,
                    SHORTCUT_ADDRESS,
                    ONES,
                    SHORTCUT_PREDECESSOR,
                )?;
                self.commit = Some(registers.code_pointer);
            },
            Some(b'j') if self.commit.is_some() => self.jump(vm)?,
            Some(b'o') => return Ok(false),
            _ => return Err("unexpected scratch constants effect".to_owned()),
        }
        Ok(true)
    }
}

// Authenticate the two actual stores at every root, and every page
// selection after initialization, not just the final memory snapshot.
#[derive(Default)]
struct ChunkPageAudit {
    commit_site: Option<u32>,
    installed: BTreeSet<u32>,
    jump_site: Option<u32>,
    normalized: BTreeSet<u32>,
    selected: BTreeSet<u32>,
}

impl ChunkPageAudit {
    fn finish(&self, vm: &ProfileMachine) -> Result<[u32; 2], String> {
        check_chunk_pages(vm)?;
        if self.normalized.len() != 7
            || self.installed.len() != 7
            || self.selected.len() != 7
        {
            return Err("missing chunk page effects".to_owned());
        }
        Ok([
            self.commit_site.ok_or("missing chunk page commit")?,
            self.jump_site.ok_or("missing chunk page jump")?,
        ])
    }

    fn jump(
        &mut self,
        vm: &mut ProfileMachine,
        address: u32,
        expected: u32,
    ) -> Result<(), String> {
        if !self.installed.contains(&address) {
            return Err("uninitialized chunk page jump".to_owned());
        }
        let trace = step(vm)?;
        if trace.memory_reads.data.map(|read| read.value) != Some(expected)
            || trace.after.registers.data_pointer != plus(expected, 1)?
            || trace.after.registers.accumulator
                != trace.before.registers.accumulator
            || trace.memory_delta.data.is_some()
        {
            return Err("wrong chunk page jump".to_owned());
        }
        let _selected = self.selected.insert(address);
        let _site = self
            .jump_site
            .get_or_insert(trace.before.registers.code_pointer);
        Ok(())
    }

    fn observe(&mut self, vm: &mut ProfileMachine) -> Result<bool, String> {
        let registers = vm.registers();
        let address = registers.data_pointer;
        if !(7_176_587..=7_176_599).contains(&address)
            || address.is_multiple_of(2)
        {
            return Ok(false);
        }
        let page = address.saturating_sub(7_176_587).div_euclid(2);
        let expected = plus(7_176_600, mul(page, 16)?)?;
        match decode_profile_instruction(
            word(vm, registers.code_pointer)?,
            registers.code_pointer,
        ) {
            Some(b'p') => self.store(vm, address, expected)?,
            Some(b'j') => self.jump(vm, address, expected)?,
            Some(b'*') => return Err("rotated chunk page".to_owned()),
            _ => return Ok(false),
        }
        Ok(true)
    }

    fn store(
        &mut self,
        vm: &mut ProfileMachine,
        address: u32,
        expected: u32,
    ) -> Result<(), String> {
        let (old, new, acc) = if self.normalized.insert(address) {
            (37, ONES, 0)
        } else if self.installed.insert(address) {
            (ONES, expected, independent_crazy(ONES, expected))
        } else {
            return Err("rewritten chunk page".to_owned());
        };
        let registers = vm.registers();
        if registers.accumulator != acc {
            return Err("wrong chunk page producer".to_owned());
        }
        check_store(&step(vm)?, address, old, new)?;
        if new == expected {
            let _site = self.commit_site.get_or_insert(registers.code_pointer);
        }
        Ok(())
    }
}

#[derive(Default)]
struct DirectSeedAudit {
    installed: BTreeSet<u32>,
    selected: BTreeSet<u32>,
}

impl DirectSeedAudit {
    fn finish(&self, vm: &ProfileMachine) -> Result<(), String> {
        if self.selected.len() != 8 || self.installed.len() != 8 {
            return Err("missing executed direct seed root".to_owned());
        }
        check_seed_directory(vm)
    }

    fn jump(
        &mut self,
        vm: &mut ProfileMachine,
        address: u32,
    ) -> Result<(), String> {
        let expected = if self.installed.contains(&address) {
            let _added = self.selected.insert(address);
            direct_seed_landing(address)?
        } else if address.is_multiple_of(2) {
            7_174_417
        } else {
            return Err("uninitialized odd seed root jump".to_owned());
        };
        let trace = step(vm)?;
        if trace.memory_reads.data.map(|read| read.value)
            != expected.checked_sub(1)
            || trace.after.registers.data_pointer != expected
            || trace.after.registers.accumulator
                != trace.before.registers.accumulator
            || trace.memory_delta.data.is_some()
        {
            return Err(format!("wrong direct seed jump M{address}"));
        }
        Ok(())
    }

    fn store(
        &mut self,
        vm: &mut ProfileMachine,
        address: u32,
    ) -> Result<(), String> {
        if self.installed.contains(&address) {
            return Err("rewritten installed seed root".to_owned());
        }
        let predecessor = direct_seed_landing(address)?
            .checked_sub(1)
            .ok_or("direct predecessor")?;
        let _trace = step(vm)?;
        if word(vm, address)? == predecessor {
            let _added = self.installed.insert(address);
        }
        Ok(())
    }
}

#[derive(Default)]
struct DirectTargetAudit {
    commits: BTreeMap<u32, u32>,
    last_producer: Option<u32>,
    mutation: Option<u32>,
    normalized: BTreeSet<u32>,
    pending_reset: Option<u32>,
    reset_mutation: Option<u32>,
    resets: BTreeSet<u32>,
    targets: BTreeMap<u32, u32>,
}

impl DirectTargetAudit {
    fn direct_store(
        &mut self,
        trace: &ProfileStepTrace,
        (old, value): (u32, u32),
    ) -> Result<(), String> {
        let address = trace.before.registers.data_pointer;
        let acc = trace.before.registers.accumulator;
        if self.commits.contains_key(&address) {
            return Err("repeated direct target commit".to_owned());
        }
        let virgin = if address.is_multiple_of(2) {
            7_174_416
        } else {
            37
        };
        match self.last_producer {
            Some(7_174_471) if acc == 0 && old == virgin && value == ONES => {
                if !self.normalized.insert(address) {
                    return Err("repeated direct normalization".to_owned());
                }
            },
            Some(7_174_441) if acc == independent_crazy(ONES, value) => {
                let expected = if self.normalized.remove(&address) {
                    ONES
                } else {
                    virgin
                };
                if old != expected {
                    return Err(
                        "incorrect direct target predecessor".to_owned()
                    );
                }
                let _committed = self.commits.insert(address, value);
                if old != value {
                    let _site = self
                        .mutation
                        .get_or_insert(trace.before.registers.code_pointer);
                }
            },
            _ => {
                return Err(format!(
                    "wrong direct producer M{address}: {:?}",
                    self.last_producer
                ));
            },
        }
        self.pending_reset = Some(address);
        Ok(())
    }

    fn finish(
        &self,
        vm: &ProfileMachine,
    ) -> Result<DirectTargetReceipt, String> {
        if self.pending_reset.is_some() || !self.normalized.is_empty() {
            return Err("unfinished direct materialization".to_owned());
        }
        for (&address, &value) in &self.commits {
            if word(vm, address)? != value
                || self.targets.get(&address) != Some(&value)
                || self
                    .targets
                    .values()
                    .filter(|&&target| target == value)
                    .count()
                    != 1
            {
                return Err(format!("nonunique direct target M{address}"));
            }
        }
        for &reset in &self.resets {
            if self.targets.contains_key(&reset)
                || word(vm, reset)? != 7_174_416
            {
                return Err(format!("nonvirgin direct reset M{reset}"));
            }
        }
        Ok((self.commits.len(), [
            self.mutation.ok_or("missing direct commit")?,
            self.reset_mutation.ok_or("missing direct reset")?,
        ]))
    }

    fn reset(&mut self, vm: &mut ProfileMachine) -> Result<(), String> {
        let target = self.pending_reset.take().ok_or("missing reset target")?;
        let trace = step(vm)?;
        let address = trace.before.registers.data_pointer;
        if address <= target
            || !address.is_multiple_of(2)
            || trace
                .memory_reads
                .data
                .map(|read| (read.address, read.value))
                != Some((address, 7_174_416))
            || trace.after.registers.data_pointer != 7_174_417
            || trace.after.registers.accumulator
                != trace.before.registers.accumulator
            || trace.memory_delta.data.is_some()
        {
            return Err(format!(
                "incorrect virgin reset M{address} after M{target}"
            ));
        }
        let _added = self.resets.insert(address);
        let _previous = self
            .reset_mutation
            .get_or_insert(trace.before.registers.code_pointer);
        Ok(())
    }

    fn scratch(
        &mut self,
        vm: &mut ProfileMachine,
        opcode: Option<u8>,
    ) -> Result<(), String> {
        let trace = step(vm)?;
        let old = trace
            .memory_reads
            .data
            .ok_or("missing scratch operand")?
            .value;
        let address = trace.before.registers.data_pointer;
        let value = if opcode == Some(b'p') {
            independent_crazy(old, trace.before.registers.accumulator)
        } else {
            rotate_right(old)?
        };
        check_store(&trace, address, old, value)?;
        self.last_producer = Some(address);
        Ok(())
    }

    fn store(
        &mut self,
        vm: &mut ProfileMachine,
        address: u32,
        early: bool,
    ) -> Result<(), String> {
        let trace = step(vm)?;
        let old = trace
            .memory_reads
            .data
            .ok_or("missing target operand")?
            .value;
        let acc = trace.before.registers.accumulator;
        let value = independent_crazy(old, acc);
        check_store(&trace, address, old, value)?;
        if early {
            self.direct_store(&trace, (old, value))?;
        } else if self.commits.contains_key(&address) {
            return Err("direct target overwritten by shared phase".to_owned());
        }
        let _previous = self.targets.insert(address, value);
        self.last_producer = Some(address);
        Ok(())
    }
}

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
// Authenticate the shorter reads using actual operand and accumulator
// values. A pair may skip its prefix only when the inverse itself is a
// fixed point of the observed fold. A non-ones prefix read must likewise
// leave the prefix intact. Neither case may rely on emitter metadata.
#[derive(Default)]
struct SharedReadAudit {
    direct_reads: usize,
    installed: BTreeSet<u32>,
    last_producer: Option<u32>,
    pending_restore: Option<(u32, u32)>,
    prefix_reads: usize,
    reversible_reads: usize,
    sites: [Option<u32>; 3],
}

impl SharedReadAudit {
    fn finish(self) -> Result<SharedReadReceipt, String> {
        if self.installed.len() != 80 || self.pending_restore.is_some() {
            return Err("incomplete shared seed reads".to_owned());
        }
        let [Some(direct), Some(prefix), Some(reversible)] = self.sites else {
            return Err("missing shortened seed read".to_owned());
        };
        Ok((
            [self.direct_reads, self.prefix_reads, self.reversible_reads],
            [direct, prefix, reversible],
        ))
    }

    fn install_return(
        &mut self,
        vm: &mut ProfileMachine,
        address: u32,
        opcode: Option<u8>,
    ) -> Result<(), String> {
        if opcode != Some(b'p') || !seed_return_address(address) {
            return advance_boot(vm);
        }
        let _trace = step(vm)?;
        if word(vm, address)? == SEED_RETURN_TARGET.saturating_sub(1) {
            let _inserted = self.installed.insert(address);
        }
        Ok(())
    }

    fn observe(
        &mut self,
        vm: &mut ProfileMachine,
        opcode: Option<u8>,
    ) -> Result<(), String> {
        let address = vm.registers().data_pointer;
        if self.installed.len() != 80 {
            return self.install_return(vm, address, opcode);
        }
        if opcode == Some(b'p') && !address.is_multiple_of(2) {
            if (7_174_611..=7_174_929).contains(&address) {
                self.paired_read(vm, address)?;
            } else if (7_174_931..7_174_970).contains(&address)
                || (7_175_601..7_176_586).contains(&address)
            {
                self.reversible_read(vm, address)?;
            } else {
                self.other_effect(vm, opcode)?;
            }
        } else {
            self.other_effect(vm, opcode)?;
        }
        if matches!(opcode, Some(b'p' | b'*')) {
            self.last_producer = Some(address);
        }
        Ok(())
    }

    fn other_effect(
        &self,
        vm: &mut ProfileMachine,
        opcode: Option<u8>,
    ) -> Result<(), String> {
        if self.pending_restore.is_some() && opcode == Some(b'p') {
            return Err("unrestored seed before another fold".to_owned());
        }
        advance_boot(vm)
    }

    fn paired_read(
        &mut self,
        vm: &mut ProfileMachine,
        address: u32,
    ) -> Result<(), String> {
        let registers = vm.registers();
        let old = word(vm, address)?;
        if independent_crazy(old, registers.accumulator) != old
            || self.pending_restore.is_some()
        {
            return Err("invalid immutable seed read".to_owned());
        }
        check_store(&step(vm)?, address, old, old)?;
        if address.rem_euclid(4) == 1
            && self.last_producer != address.checked_sub(2)
        {
            self.direct_reads = self.direct_reads.saturating_add(1);
            let _site = self.sites[0].get_or_insert(registers.code_pointer);
        } else if address.rem_euclid(4) == 3 && registers.accumulator != ONES {
            self.prefix_reads = self.prefix_reads.saturating_add(1);
            let _site = self.sites[1].get_or_insert(registers.code_pointer);
        }
        Ok(())
    }

    fn reversible_read(
        &mut self,
        vm: &mut ProfileMachine,
        address: u32,
    ) -> Result<(), String> {
        let registers = vm.registers();
        let old = word(vm, address)?;
        let new = independent_crazy(old, registers.accumulator);
        check_store(&step(vm)?, address, old, new)?;
        if let Some((pending, original)) = self.pending_restore.take() {
            if pending != address
                || new != original
                || registers.accumulator != EOF
            {
                return Err("reversible seed was not restored".to_owned());
            }
        } else if old == new {
            if registers.accumulator == EOF {
                return Err("unexpected uniform reversible seed".to_owned());
            }
            self.reversible_reads = self.reversible_reads.saturating_add(1);
            let _site = self.sites[2].get_or_insert(registers.code_pointer);
        } else {
            if registers.accumulator != EOF {
                return Err("incorrect reversible seed reload".to_owned());
            }
            self.pending_restore = Some((address, old));
        }
        Ok(())
    }
}

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
                || word(&vm, 7_174_447)? != 7_174_468
                || word(&vm, 7_174_448)? != 7_174_416
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

// The local marker and its two single-trit columns must survive the
// complete bootstrap. Verify both immutable reads and their effect on an
// all-one target using the independent trit table, not the emitter.
fn check_bootstrap_columns(vm: &ProfileMachine) -> Result<(), String> {
    if word(vm, 7_174_427)? != 2
        || word(vm, 7_174_488)? != 6
        || word(vm, 7_174_490)? != 7_174_456
    {
        return Err("wrong local marker or reserved reset geometry".to_owned());
    }
    for (address, digit, expected_prefix) in
        [(7_174_429, 2u32, 2u32), (7_174_433, 0u32, 0u32)]
    {
        let prefix = word(vm, address)?;
        let value = word(vm, plus(address, 2)?)?;
        let selected =
            independent_crazy(value, independent_crazy(prefix, ONES));
        let result = independent_crazy(independent_crazy(ONES, selected), EOF);
        if prefix != expected_prefix
            || value
                != EOF
                    .checked_sub(if digit == 2 {
                        2
                    } else {
                        1
                    })
                    .ok_or("column")?
            || independent_crazy(prefix, ONES) != prefix
            || selected != value
            || result != plus(ONES.checked_sub(1).ok_or("target")?, digit)?
        {
            return Err(format!("wrong local immutable column M{address}"));
        }
    }
    Ok(())
}

// Independent directory geometry: all seven roots are immutable
// predecessors of four consecutive mask pairs, with virgin resets.
fn check_chunk_pages(vm: &ProfileMachine) -> Result<(), String> {
    if word(vm, 7_174_487)? != 7_176_586 {
        return Err("wrong chunk directory root".to_owned());
    }
    for page in 0..7u32 {
        let slot = plus(7_176_587, mul(page, 2)?)?;
        let predecessor = plus(7_176_600, mul(page, 16)?)?;
        if word(vm, slot)? != predecessor
            || word(vm, plus(slot, 1)?)? != 7_174_416
        {
            return Err(format!("wrong chunk page M{slot}"));
        }
    }
    Ok(())
}

// Every mask remains immutable after synthesizing the page and seed
// banks, including the special return-pointer mask at the final pair.
fn check_chunk_mask_bank(vm: &ProfileMachine) -> Result<(), String> {
    check_bootstrap_columns(vm)?;
    check_chunk_pages(vm)?;
    if word(vm, 7_174_442)? != 7_174_440 || word(vm, 7_174_445)? != 7_174_440 {
        return Err("incorrect scratch return pointers".to_owned());
    }
    for index in 0..28u32 {
        let address = plus(7_176_601, mul(index, 4)?)?;
        let prefix = word(vm, address)?;
        let value = word(vm, plus(address, 2)?)?;
        let expected = if index == 27 {
            independent_crazy(ONES, 7_174_440)
        } else {
            plus(EOF.checked_sub(26).ok_or("mask base")?, index)?
        };
        if value != expected
            || independent_crazy(prefix, ONES) != prefix
            || independent_crazy(value, prefix) != value
            || word(vm, plus(address, 1)?)? != 7_174_416
            || word(vm, plus(address, 3)?)?
                != if index == 27 {
                    7_174_416
                } else {
                    7_174_440
                }
        {
            return Err(format!("wrong immutable chunk mask M{address}"));
        }
    }
    Ok(())
}

// Independent physical audit of the two-hop seed directory. The address
// bank is intentionally not obtained from the production planner.
fn check_seed_directory(vm: &ProfileMachine) -> Result<(), String> {
    for root in 7_174_475..=7_174_482 {
        let predecessor = direct_seed_landing(root)?
            .checked_sub(1)
            .ok_or("direct predecessor")?;
        if word(vm, root)? != predecessor {
            return Err(format!("incorrect direct seed root M{root}"));
        }
    }
    if word(vm, 7_174_484)? != 7_174_416 {
        return Err("missing retained seed root reset".to_owned());
    }
    let mut address = 7_176_721;
    if word(vm, 7_174_489)? != 7_176_720 {
        return Err("missing seed directory root".to_owned());
    }
    for (start, end) in
        [(7_174_611u32, 7_174_970u32), (7_175_601u32, 7_176_586u32)]
    {
        for base in (start..end).step_by(48) {
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

fn seed_return_address(address: u32) -> bool {
    (SEED_RETURN_BASE..=SEED_RETURN_END).contains(&address)
        && address.saturating_sub(SEED_RETURN_BASE).is_multiple_of(4)
}

fn check_seed_returns(vm: &ProfileMachine) -> Result<(), String> {
    for address in (SEED_RETURN_BASE..=SEED_RETURN_END).step_by(4) {
        if word(vm, address)? != SEED_RETURN_TARGET.saturating_sub(1)
            || word(vm, address.saturating_sub(2))? != 7_174_416
        {
            return Err(format!("incorrect inverse-seed return M{address}"));
        }
    }
    Ok(())
}

// The target pages point at distinct bases within the recurrent data
// plan, not at their own bank or the bootstrap scratch space.
fn check_target_directory(vm: &ProfileMachine) -> Result<(), String> {
    let _routes = target_directory(vm)?;
    Ok(())
}

fn target_directory(vm: &ProfileMachine) -> Result<Vec<TargetRoute>, String> {
    let mut targets = BTreeSet::new();
    let mut routes = Vec::new();
    for (root, bank) in [
        (7_174_491u32, 7_300_001u32),
        (7_174_493u32, 7_300_201u32),
        (7_174_495u32, 7_300_401u32),
        (7_174_497u32, 7_300_601u32),
        (7_174_499u32, 7_300_801u32),
        (7_174_501u32, 7_301_001u32),
        (7_174_503u32, 7_301_201u32),
        (7_174_505u32, 7_301_401u32),
        (7_174_507u32, 7_301_601u32),
        (7_174_509u32, 7_301_801u32),
        (7_174_511u32, 7_302_001u32),
        (7_174_513u32, 7_302_201u32),
    ] {
        if word(vm, root)? != bank.checked_sub(1).ok_or("target root")? {
            return Err("incorrect target directory root".to_owned());
        }
        for offset in 0..24u32 {
            let slot = plus(bank, mul(offset, 2)?)?;
            let target = plus(word(vm, slot)?, 1)?;
            if !(7_175_000..7_244_000).contains(&target)
                || !targets.insert(target)
                || word(vm, plus(slot, 1)?)? != 7_174_416
            {
                return Err(format!("incorrect target directory M{slot}"));
            }
            routes.push(TargetRoute {
                base: target,
                cost: plus(plus(root, mul(offset, 2)?)?, 1)?,
                root,
                slot: Some(slot),
            });
        }
    }
    for root in (7_174_515..7_174_601).step_by(2) {
        let target = plus(word(vm, root)?, 1)?;
        if !(7_175_000..7_244_000).contains(&target)
            || !targets.insert(target)
            || word(vm, plus(root, 1)?)? != 7_174_416
        {
            return Err(format!("incorrect direct target M{root}"));
        }
        routes.push(TargetRoute {
            base: target,
            cost: root,
            root,
            slot: None,
        });
    }
    if targets.len() != 331 {
        return Err("missing target directory partition".to_owned());
    }
    Ok(routes)
}

fn advance_boot(vm: &mut ProfileMachine) -> Result<(), String> {
    if vm.step().map_err(|error| error.to_string())? != StepOutcome::Continued {
        return Err("premature bootstrap termination".to_owned());
    }
    Ok(())
}

fn audit_target_routes(
    guest: &RelocatedRecurrentChecksumSource,
    routes: &[TargetRoute],
) -> Result<[u32; 4], String> {
    let mut vm = ProfileMachine::from_source(
        current_profile(),
        &guest.capture.source,
        Vec::new(),
    )
    .map_err(|error| error.to_string())?;
    let mut audit = TargetRouteAudit::default();
    for _ in 0..BOOT_BUDGET {
        if is_input(&vm, guest)? {
            return audit.finish();
        }
        audit.observe(&mut vm, routes)?;
    }
    Err("missing target-route first input".to_owned())
}

#[test]
fn relocated_recurrent_checksum_omitted_target_route_refuses()
-> Result<(), String> {
    let guest = source()?;
    let routes = target_directory(&boot(&guest)?)?;
    for site in audit_target_routes(&guest, &routes)? {
        let modified = omit_site(&guest, site)?;
        if audit_target_routes(&modified, &routes).is_ok() {
            return Err("accepted omitted target route".to_owned());
        }
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
    check_seed_returns(&initial)?;
    check_target_directory(&initial)?;
    check_chunk_mask_bank(&initial)?;
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
    if guest.capture.source.len() != 2_318_854 {
        return Err("unexpected recurrent source extent".to_owned());
    }
    let (initial, bootstrap_steps) = boot_with_steps(&guest)?;
    check_seed_directory(&initial)?;
    check_seed_returns(&initial)?;
    check_target_directory(&initial)?;
    check_chunk_mask_bank(&initial)?;
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

// The two physical writes use the first result as the second
// accumulator; the second result must be all ones for any dirty word.
fn audit_chunk_reset(
    guest: &RelocatedRecurrentChecksumSource,
) -> Result<u32, String> {
    let mut vm = ProfileMachine::from_source(
        current_profile(),
        &guest.capture.source,
        Vec::new(),
    )
    .map_err(|error| error.to_string())?;
    let address = 7_174_441;
    let mut accumulator = ONES;
    let mut folds = 0u8;
    for _ in 0..BOOT_BUDGET {
        let registers = vm.registers();
        if registers.data_pointer == address
            && decode_profile_instruction(
                word(&vm, registers.code_pointer)?,
                registers.code_pointer,
            ) == Some(b'p')
        {
            let old = word(&vm, address)?;
            if registers.accumulator != accumulator {
                return Err("incorrect chunk reset accumulator".to_owned());
            }
            let new = independent_crazy(old, accumulator);
            check_store(&step(&mut vm)?, address, old, new)?;
            accumulator = new;
            folds = folds.saturating_add(1);
            if folds == 2 && new != ONES {
                return Err("incorrect two-fold reset".to_owned());
            }
            if folds == 2 {
                return Ok(registers.code_pointer);
            }
        } else if vm.step().map_err(|error| error.to_string())?
            != StepOutcome::Continued
        {
            return Err("premature chunk reset termination".to_owned());
        }
    }
    Err("missing chunk reset".to_owned())
}

#[test]
fn relocated_recurrent_checksum_omitted_chunk_reset_refuses()
-> Result<(), String> {
    let guest = source()?;
    let site = audit_chunk_reset(&guest)?;
    let modified = omit_site(&guest, site)?;
    if audit_chunk_reset(&modified).is_ok() {
        return Err("accepted omitted second chunk reset fold".to_owned());
    }
    Ok(())
}

fn check_patch_prefix(acc: u32, before: u32, after: u32) -> Result<(), String> {
    if acc != EOF || after.div_euclid(27) != before.div_euclid(27) {
        return Err("dirty chunk patch changed its prefix".to_owned());
    }
    Ok(())
}

// Observe a patch that starts from a previous root's committed
// inverse, not from the all-one scratch reset. A pair of mask folds
// changes only the low three trits and leaves the high prefix intact.
fn audit_chunk_reuse(
    guest: &RelocatedRecurrentChecksumSource,
) -> Result<u32, String> {
    let vm = ProfileMachine::from_source(
        current_profile(),
        &guest.capture.source,
        Vec::new(),
    )
    .map_err(|error| error.to_string())?;
    find_dirty_patch(vm)
}

fn find_dirty_patch(mut vm: ProfileMachine) -> Result<u32, String> {
    let scratch = 7_174_441;
    let mut prior = None;
    let mut first: Option<u32> = None;
    for _ in 0..BOOT_BUDGET {
        let registers = vm.registers();
        let data = registers.data_pointer;
        let opcode = decode_profile_instruction(
            word(&vm, registers.code_pointer)?,
            registers.code_pointer,
        );
        if opcode == Some(b'p')
            && (7_174_491..7_174_601).contains(&data)
            && !data.is_multiple_of(2)
        {
            let old = word(&vm, data)?;
            let new = independent_crazy(old, registers.accumulator);
            check_store(&step(&mut vm)?, data, old, new)?;
            if old == ONES && (7_174_999..7_302_300).contains(&new) {
                prior = Some(word(&vm, scratch)?);
                first = None;
            }
            continue;
        }
        let Some(old) = prior
            .filter(|_| data == scratch && matches!(opcode, Some(b'p' | b'*')))
        else {
            let _: ProfileStepTrace = step(&mut vm)?;
            continue;
        };
        if word(&vm, scratch)? != old {
            return Err("untracked scratch mutation".to_owned());
        }
        if opcode == Some(b'*') {
            let new = rotate_right(old)?;
            check_store(&step(&mut vm)?, scratch, old, new)?;
            prior = Some(new);
            continue;
        }
        let acc = registers.accumulator;
        let new = independent_crazy(old, acc);
        check_store(&step(&mut vm)?, scratch, old, new)?;
        if let Some(before) = first {
            check_patch_prefix(acc, before, new)?;
            if new != old {
                return Ok(registers.code_pointer);
            }
            prior = None;
            first = None;
        } else if (EOF.saturating_sub(26)..EOF).contains(&acc) {
            first = Some(old);
            prior = Some(new);
        } else {
            // This candidate used a fresh reset instead.
            prior = None;
        }
    }
    Err("missing previous-word chunk patch".to_owned())
}

#[test]
fn relocated_recurrent_checksum_omitted_dirty_patch_refuses()
-> Result<(), String> {
    let guest = source()?;
    let site = audit_chunk_reuse(&guest)?;
    let modified = omit_site(&guest, site)?;
    if let Ok(mutated) = boot(&modified)
        && check_target_directory(&mutated).is_ok()
        && check_materialized_tables(&mutated).is_ok()
    {
        return Err("accepted omitted dirty chunk patch".to_owned());
    }
    Ok(())
}

#[test]
fn relocated_recurrent_checksum_omitted_bootstrap_column_refuses()
-> Result<(), String> {
    let guest = source()?;
    for (address, value) in [
        (7_174_427, 54),
        (7_174_431, EOF.checked_sub(2).ok_or("column")?),
        (7_174_435, EOF.checked_sub(1).ok_or("column")?),
    ] {
        let site = materialization_site(&guest, (address, value))?;
        let modified = omit_site(&guest, site)?;
        if let Ok(mutated) = boot(&modified)
            && check_chunk_mask_bank(&mutated).is_ok()
            && check_materialized_tables(&mutated).is_ok()
        {
            return Err(format!("accepted omitted local column M{address}"));
        }
    }
    Ok(())
}

// The local columns are used again after the fast scratch-return bank
// has been installed. Authenticate both immutable reads and the actual
// forward walk to their consuming scratch fold.
fn local_column_effect(
    vm: &mut ProfileMachine,
    address: u32,
) -> Result<u32, String> {
    let prefix = if address == 7_174_429 {
        2
    } else {
        0
    };
    let mask = EOF
        .checked_sub(if prefix == 2 {
            2
        } else {
            1
        })
        .ok_or("local column mask")?;
    let first = step(vm)?;
    if first.decoded != Some(b'p') || first.before.registers.accumulator != ONES
    {
        return Err("wrong fast local prefix input".to_owned());
    }
    check_store(&first, address, prefix, prefix)?;
    let between = step(vm)?;
    if between.decoded != Some(b'o') {
        return Err("nonlinear local prefix walk".to_owned());
    }
    routing(&between, u32::MAX)?;
    let second = step(vm)?;
    if second.decoded != Some(b'p')
        || second.before.registers.accumulator != prefix
    {
        return Err("wrong fast local column input".to_owned());
    }
    check_store(&second, plus(address, 2)?, mask, mask)?;
    for _ in plus(address, 3)?..7_174_441 {
        let walk = step(vm)?;
        if walk.decoded != Some(b'o') {
            return Err("nonlinear local column walk".to_owned());
        }
        routing(&walk, u32::MAX)?;
    }
    let scratch = word(vm, 7_174_441)?;
    let fold = step(vm)?;
    if fold.decoded != Some(b'p') || fold.before.registers.accumulator != mask {
        return Err("wrong fast local scratch input".to_owned());
    }
    check_store(&fold, 7_174_441, scratch, independent_crazy(scratch, mask))?;
    Ok(second.before.registers.code_pointer)
}

fn fast_local_column_sites(
    guest: &RelocatedRecurrentChecksumSource,
) -> Result<LocalColumnSites, String> {
    let mut vm = ProfileMachine::from_source(
        current_profile(),
        &guest.capture.source,
        Vec::new(),
    )
    .map_err(|error| error.to_string())?;
    let mut sites = BTreeMap::new();
    for _ in 0..BOOT_BUDGET {
        let registers = vm.registers();
        let address = registers.data_pointer;
        if matches!(address, 7_174_429 | 7_174_433)
            && word(&vm, 7_176_604)? == 7_174_440
            && decode_profile_instruction(
                word(&vm, registers.code_pointer)?,
                registers.code_pointer,
            ) == Some(b'p')
        {
            let site = local_column_effect(&mut vm, address)?;
            let _previous = sites.insert(address, site);
            if sites.len() == 2 {
                return Ok(sites);
            }
        } else if vm.step().map_err(|error| error.to_string())?
            != StepOutcome::Continued
        {
            return Err("premature local column termination".to_owned());
        }
    }
    Err("missing fast local column reads".to_owned())
}

#[test]
fn relocated_recurrent_checksum_omitted_fast_local_column_read_refuses()
-> Result<(), String> {
    let guest = source()?;
    for site in fast_local_column_sites(&guest)?.into_values() {
        let modified = omit_site(&guest, site)?;
        if fast_local_column_sites(&modified).is_ok() {
            return Err("accepted omitted fast local column read".to_owned());
        }
    }
    Ok(())
}

#[test]
fn relocated_recurrent_checksum_omitted_derived_chunk_mask_refuses()
-> Result<(), String> {
    let guest = source()?;
    // Column zero is not an elementary single-trit column.
    let site =
        materialization_site(&guest, (7_176_603, EOF.saturating_sub(26)))?;
    let modified = omit_site(&guest, site)?;
    if let Ok(mutated) = boot(&modified)
        && check_chunk_mask_bank(&mutated).is_ok()
    {
        return Err("accepted omitted derived chunk mask".to_owned());
    }
    Ok(())
}

fn audit_chunk_pages(
    guest: &RelocatedRecurrentChecksumSource,
) -> Result<[u32; 2], String> {
    let mut vm = ProfileMachine::from_source(
        current_profile(),
        &guest.capture.source,
        Vec::new(),
    )
    .map_err(|error| error.to_string())?;
    let mut audit = ChunkPageAudit::default();
    for _ in 0..BOOT_BUDGET {
        if is_input(&vm, guest)? {
            return audit.finish(&vm);
        }
        if audit.observe(&mut vm)? {
            continue;
        }
        if vm.step().map_err(|error| error.to_string())?
            != StepOutcome::Continued
        {
            return Err("premature chunk page termination".to_owned());
        }
    }
    Err("missing first input after chunk pages".to_owned())
}

#[test]
fn relocated_recurrent_checksum_omitted_chunk_page_refuses()
-> Result<(), String> {
    let guest = source()?;
    for site in audit_chunk_pages(&guest)? {
        let modified = omit_site(&guest, site)?;
        if audit_chunk_pages(&modified).is_ok() {
            return Err("accepted omitted chunk page effect".to_owned());
        }
    }
    Ok(())
}

fn audit_target_clusters(
    guest: &RelocatedRecurrentChecksumSource,
) -> Result<[u32; 4], String> {
    let mut vm = ProfileMachine::from_source(
        current_profile(),
        &guest.capture.source,
        Vec::new(),
    )
    .map_err(|error| error.to_string())?;
    let mut audit = TargetClusterAudit::default();
    let mut shared = false;
    for _ in 0..BOOT_BUDGET {
        if is_input(&vm, guest)? {
            return audit.finish(&vm);
        }
        let registers = vm.registers();
        let address = registers.data_pointer;
        let opcode = decode_profile_instruction(
            word(&vm, registers.code_pointer)?,
            registers.code_pointer,
        );
        if opcode == Some(b'p') && seed_return_address(address) {
            shared = true;
        }
        if shared && opcode == Some(b'p') && materialized_target(address) {
            audit.store(&mut vm)?;
            continue;
        }
        if opcode != Some(b'o') {
            audit.flush()?;
        }
        if audit.pending_target.is_some() && opcode != Some(b'o') {
            if opcode != Some(b'j') {
                return Err("missing shared reset jump".to_owned());
            }
            audit.reset(&mut vm)?;
            continue;
        }
        if opcode == Some(b'o') && !audit.run.is_empty() {
            routing(&step(&mut vm)?, u32::MAX)?;
            continue;
        }
        if vm.step().map_err(|error| error.to_string())?
            != StepOutcome::Continued
        {
            return Err("premature bootstrap termination".to_owned());
        }
    }
    Err("missing clustered first input".to_owned())
}

#[test]
fn relocated_recurrent_checksum_omitted_target_cluster_effects_refuse()
-> Result<(), String> {
    let guest = source()?;
    for site in audit_target_clusters(&guest)? {
        let modified = omit_site(&guest, site)?;
        if audit_target_clusters(&modified).is_ok() {
            return Err("accepted omitted cluster normalization".to_owned());
        }
    }
    Ok(())
}

fn audit_scratch_constants(
    guest: &RelocatedRecurrentChecksumSource,
) -> Result<ShortcutReceipt, String> {
    let mut vm = ProfileMachine::from_source(
        current_profile(),
        &guest.capture.source,
        Vec::new(),
    )
    .map_err(|error| error.to_string())?;
    let mut audit = ScratchConstantsAudit::default();
    for _ in 0..BOOT_BUDGET {
        if is_input(&vm, guest)? {
            return audit.finish(&vm);
        }
        if audit.observe(&mut vm)? {
            continue;
        }
        if vm.step().map_err(|error| error.to_string())?
            != StepOutcome::Continued
        {
            return Err("premature shortcut termination".to_owned());
        }
    }
    Err("missing first input after shortcut".to_owned())
}

#[test]
fn relocated_recurrent_checksum_omitted_scratch_constants_refuses()
-> Result<(), String> {
    let guest = source()?;
    let (sites, selections) = audit_scratch_constants(&guest)?;
    if selections != 1_338 {
        return Err(format!("unexpected shortcut count: {selections}"));
    }
    for site in sites {
        let modified = omit_site(&guest, site)?;
        if audit_scratch_constants(&modified).is_ok() {
            return Err("accepted omitted scratch constants effect".to_owned());
        }
    }
    Ok(())
}

// Find both kinds of direct scratch returns from actual executed jumps.
fn audit_scratch_returns(
    guest: &RelocatedRecurrentChecksumSource,
) -> Result<[u32; 2], String> {
    let mut vm = ProfileMachine::from_source(
        current_profile(),
        &guest.capture.source,
        Vec::new(),
    )
    .map_err(|error| error.to_string())?;
    let mut adjacent = None;
    let mut mask = None;
    for _ in 0..BOOT_BUDGET {
        let registers = vm.registers();
        let address = registers.data_pointer;
        let adjacent_candidate = address == 7_174_442;
        let mask_candidate = (7_176_604..=7_176_708).contains(&address)
            && address.is_multiple_of(4);
        let direct = (adjacent_candidate || mask_candidate)
            && word(&vm, address)? == 7_174_440
            && decode_profile_instruction(
                word(&vm, registers.code_pointer)?,
                registers.code_pointer,
            ) == Some(b'j');
        if vm.step().map_err(|error| error.to_string())?
            != StepOutcome::Continued
        {
            return Err("premature bootstrap termination".to_owned());
        }
        if direct {
            if vm.registers().data_pointer != 7_174_441 {
                return Err("wrong direct scratch destination".to_owned());
            }
            if adjacent_candidate {
                adjacent = Some(address);
            } else {
                mask = Some(address);
            }
            if let (Some(adjacent_address), Some(mask_address)) =
                (adjacent, mask)
            {
                return Ok([adjacent_address, mask_address]);
            }
        }
    }
    Err("missing executed scratch return".to_owned())
}

#[test]
fn relocated_recurrent_checksum_omitted_scratch_returns_refuse()
-> Result<(), String> {
    let guest = source()?;
    for address in audit_scratch_returns(&guest)? {
        let site = materialization_site(&guest, (address, 7_174_440))?;
        let modified = omit_site(&guest, site)?;
        if let Ok(mutated) = boot(&modified)
            && check_chunk_mask_bank(&mutated).is_ok()
        {
            return Err(format!("accepted omitted scratch return M{address}"));
        }
    }
    Ok(())
}

fn materialized_target(address: u32) -> bool {
    (7_175_000..7_244_000).contains(&address)
        && !(7_175_601..=7_176_900).contains(&address)
}

// Paired-return installation separates the early, value-ordered direct
// materialization from the shared, address-ordered stores.
fn audit_direct_targets(
    guest: &RelocatedRecurrentChecksumSource,
) -> Result<DirectTargetReceipt, String> {
    let mut vm = ProfileMachine::from_source(
        current_profile(),
        &guest.capture.source,
        Vec::new(),
    )
    .map_err(|error| error.to_string())?;
    let mut audit = DirectTargetAudit::default();
    let mut early = true;
    for _ in 0..BOOT_BUDGET {
        if is_input(&vm, guest)? {
            return audit.finish(&vm);
        }
        let registers = vm.registers();
        let address = registers.data_pointer;
        let opcode = decode_profile_instruction(
            word(&vm, registers.code_pointer)?,
            registers.code_pointer,
        );
        if audit.pending_reset.is_some() {
            match opcode {
                Some(b'j') => {
                    audit.reset(&mut vm)?;
                    continue;
                },
                Some(b'o') => {},
                _ => return Err("missing virgin target reset".to_owned()),
            }
        }
        if opcode == Some(b'p') && seed_return_address(address) {
            early = false;
        }
        if opcode == Some(b'p') && materialized_target(address) {
            audit.store(&mut vm, address, early)?;
        } else if early
            && address == 7_174_441
            && matches!(opcode, Some(b'p' | b'*'))
        {
            audit.scratch(&mut vm, opcode)?;
        } else {
            if matches!(opcode, Some(b'p' | b'*')) {
                audit.last_producer = Some(address);
            }
            if vm.step().map_err(|error| error.to_string())?
                != StepOutcome::Continued
            {
                return Err("premature bootstrap termination".to_owned());
            }
        }
    }
    Err("missing direct-materialization input".to_owned())
}

#[test]
fn relocated_recurrent_checksum_omitted_direct_target_effects_refuse()
-> Result<(), String> {
    let guest = source()?;
    let (count, sites) = audit_direct_targets(&guest)?;
    if count != 254 {
        return Err(format!("expected 254 direct targets, observed {count}"));
    }
    for site in sites {
        let modified = omit_site(&guest, site)?;
        if audit_direct_targets(&modified)
            .is_ok_and(|(actual, _)| actual == count)
        {
            return Err(
                "accepted omitted direct materialization effect".to_owned()
            );
        }
    }
    Ok(())
}

// Independently trace the initialized returns; earlier virgin reset
// jumps through the same slots are not evidence of a direct return.
fn audit_seed_returns(
    guest: &RelocatedRecurrentChecksumSource,
) -> Result<(), String> {
    let mut vm = ProfileMachine::from_source(
        current_profile(),
        &guest.capture.source,
        Vec::new(),
    )
    .map_err(|error| error.to_string())?;
    let mut visited = BTreeSet::new();
    for _ in 0..BOOT_BUDGET {
        let registers = vm.registers();
        let address = registers.data_pointer;
        let direct = seed_return_address(address)
            && word(&vm, address)? == SEED_RETURN_TARGET.saturating_sub(1)
            && decode_profile_instruction(
                word(&vm, registers.code_pointer)?,
                registers.code_pointer,
            ) == Some(b'j');
        if direct {
            let trace = step(&mut vm)?;
            if trace.after.registers.data_pointer != SEED_RETURN_TARGET
                || trace.after.registers.accumulator != registers.accumulator
                || trace.memory_delta.data.is_some()
            {
                return Err("incorrect direct inverse-seed jump".to_owned());
            }
            let _: bool = visited.insert(address);
            if visited.len() == 80 {
                return Ok(());
            }
        } else if vm.step().map_err(|error| error.to_string())?
            != StepOutcome::Continued
        {
            return Err("premature bootstrap termination".to_owned());
        }
    }
    Err(format!(
        "only {} inverse-seed returns executed",
        visited.len()
    ))
}

fn audit_shared_reads(
    guest: &RelocatedRecurrentChecksumSource,
) -> Result<SharedReadReceipt, String> {
    let mut vm = ProfileMachine::from_source(
        current_profile(),
        &guest.capture.source,
        Vec::new(),
    )
    .map_err(|error| error.to_string())?;
    let mut audit = SharedReadAudit::default();
    for _ in 0..BOOT_BUDGET {
        if is_input(&vm, guest)? {
            check_materialized_tables(&vm)?;
            return audit.finish();
        }
        let code = vm.registers().code_pointer;
        let opcode = decode_profile_instruction(word(&vm, code)?, code);
        audit.observe(&mut vm, opcode)?;
    }
    Err("missing shared-read first input".to_owned())
}

fn check_virgin_seed_commits(
    vm: &ProfileMachine,
    commits: &VirginSeedCommits,
) -> Result<(), String> {
    for (&address, &(value, _)) in commits {
        if word(vm, address)? != value {
            return Err("virgin seed commit not preserved".to_owned());
        }
    }
    Ok(())
}

// A virgin odd seed holds the loader marker 37. A nonzero accumulator
// may commit its final inverse directly only if the executed fold produces
// the same word that is still present after all bootstrap seed reads.
fn audit_virgin_seed_commits(
    guest: &RelocatedRecurrentChecksumSource,
) -> Result<VirginSeedCommits, String> {
    let mut vm = ProfileMachine::from_source(
        current_profile(),
        &guest.capture.source,
        Vec::new(),
    )
    .map_err(|error| error.to_string())?;
    let mut visited = BTreeSet::new();
    let mut commits = BTreeMap::new();
    for _ in 0..BOOT_BUDGET {
        if is_input(&vm, guest)? {
            check_virgin_seed_commits(&vm, &commits)?;
            return Ok(commits);
        }
        let registers = vm.registers();
        let address = registers.data_pointer;
        let seed = (7_174_611..=7_174_970).contains(&address)
            || (7_175_601..=7_176_586).contains(&address);
        if seed
            && !address.is_multiple_of(2)
            && decode_profile_instruction(
                word(&vm, registers.code_pointer)?,
                registers.code_pointer,
            ) == Some(b'p')
            && visited.insert(address)
        {
            let old = word(&vm, address)?;
            let value = independent_crazy(old, registers.accumulator);
            if old != 37 {
                return Err("nonvirgin seed first store".to_owned());
            }
            check_store(&step(&mut vm)?, address, old, value)?;
            if registers.accumulator != 0 {
                let _old =
                    commits.insert(address, (value, registers.code_pointer));
            }
        } else {
            advance_boot(&mut vm)?;
        }
    }
    Err("missing first input after virgin seed commits".to_owned())
}

#[test]
fn relocated_recurrent_checksum_virgin_seed_commits_preserved()
-> Result<(), String> {
    let guest = source()?;
    let commits = audit_virgin_seed_commits(&guest)?;
    if commits.len() != 26 {
        return Err(format!(
            "unexpected virgin seed commits: {}",
            commits.len()
        ));
    }
    let &(_, site) = commits.values().next().ok_or("no virgin seed commits")?;
    let modified = omit_site(&guest, site)?;
    if audit_virgin_seed_commits(&modified)
        .is_ok_and(|actual| actual == commits)
    {
        return Err("accepted omitted virgin seed commit".to_owned());
    }
    Ok(())
}

#[test]
fn relocated_recurrent_checksum_shared_reads_preserve_seeds()
-> Result<(), String> {
    let guest = source()?;
    let (counts, sites) = audit_shared_reads(&guest)?;
    if counts != [328, 2, 12] {
        return Err(format!(
            "incorrect shortened seed read census: {counts:?}"
        ));
    }
    for site in sites {
        let modified = omit_site(&guest, site)?;
        if audit_shared_reads(&modified)
            .is_ok_and(|(actual, _)| actual == counts)
        {
            return Err("accepted omitted shortened seed read".to_owned());
        }
    }
    Ok(())
}

#[test]
fn relocated_recurrent_checksum_omitted_seed_return_refuses()
-> Result<(), String> {
    let guest = source()?;
    audit_seed_returns(&guest)?;
    let site = materialization_site(
        &guest,
        (SEED_RETURN_BASE, SEED_RETURN_TARGET.saturating_sub(1)),
    )?;
    let modified = omit_site(&guest, site)?;
    if audit_seed_returns(&modified).is_ok()
        || boot(&modified).is_ok_and(|vm| check_seed_returns(&vm).is_ok())
    {
        return Err("accepted omitted inverse-seed return".to_owned());
    }
    Ok(())
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

fn direct_seed_landing(address: u32) -> Result<u32, String> {
    plus(
        7_174_647,
        mul(address.checked_sub(7_174_475).ok_or("direct root")?, 36)?,
    )
}

// Observe the entire bootstrap. Earlier even roots may act as virgin
// frame resets, but once their final pointer has been written they must
// only jump to the selected seed page, preserving A and the operand.
fn audit_direct_seed_roots(
    guest: &RelocatedRecurrentChecksumSource,
) -> Result<(), String> {
    let mut vm = ProfileMachine::from_source(
        current_profile(),
        &guest.capture.source,
        Vec::new(),
    )
    .map_err(|error| error.to_string())?;
    let mut audit = DirectSeedAudit::default();
    for _ in 0..BOOT_BUDGET {
        if is_input(&vm, guest)? {
            return audit.finish(&vm);
        }
        let registers = vm.registers();
        let address = registers.data_pointer;
        if (7_174_475..=7_174_482).contains(&address) {
            match decode_profile_instruction(
                word(&vm, registers.code_pointer)?,
                registers.code_pointer,
            ) {
                Some(b'j') => {
                    audit.jump(&mut vm, address)?;
                    continue;
                },
                Some(b'p' | b'*') => {
                    audit.store(&mut vm, address)?;
                    continue;
                },
                _ => (),
            }
        }
        if vm.step().map_err(|error| error.to_string())?
            != StepOutcome::Continued
        {
            return Err("premature bootstrap termination".to_owned());
        }
    }
    Err("missing first input after direct seed routes".to_owned())
}

#[test]
fn relocated_recurrent_checksum_omitted_direct_seed_root_refuses()
-> Result<(), String> {
    let guest = source()?;
    audit_direct_seed_roots(&guest)?;
    let site = materialization_site(&guest, (7_174_476, 7_174_682))?;
    let modified = omit_site(&guest, site)?;
    if let Ok(mutated) = boot(&modified)
        && (check_seed_directory(&mutated).is_ok()
            || check_materialized_tables(&mutated).is_ok())
    {
        return Err("accepted omitted direct seed root".to_owned());
    }
    Ok(())
}

// Choose a directory pointer from a real paged seed lookup, rather
// than a fixed slot whose direct alternative may have become cheaper.
fn executed_directory_page(
    guest: &RelocatedRecurrentChecksumSource,
) -> Result<DirectoryPage, String> {
    let mut vm = ProfileMachine::from_source(
        current_profile(),
        &guest.capture.source,
        Vec::new(),
    )
    .map_err(|error| error.to_string())?;
    for _ in 0..BOOT_BUDGET {
        if is_input(&vm, guest)? {
            break;
        }
        let registers = vm.registers();
        let address = registers.data_pointer;
        if (7_176_721..=7_176_777).contains(&address)
            && !address.is_multiple_of(2)
            && decode_profile_instruction(
                word(&vm, registers.code_pointer)?,
                registers.code_pointer,
            ) == Some(b'j')
        {
            let value = word(&vm, address)?;
            let trace = step(&mut vm)?;
            if trace.after.registers.data_pointer != plus(value, 1)?
                || trace.after.registers.accumulator != registers.accumulator
                || trace.memory_delta.data.is_some()
            {
                return Err("incorrect paged seed jump".to_owned());
            }
            return Ok((address, value));
        }
        if vm.step().map_err(|error| error.to_string())?
            != StepOutcome::Continued
        {
            return Err("premature bootstrap termination".to_owned());
        }
    }
    Err("no executed seed directory page".to_owned())
}

#[test]
fn relocated_recurrent_checksum_omitted_directory_store_refuses()
-> Result<(), String> {
    let guest = source()?;
    let site = materialization_site(&guest, executed_directory_page(&guest)?)?;
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
