# Accelerator benchmark tooling

This directory owns reproducible accelerator measurement entry points and
retained evidence. It does not define VM correctness.

`resource_budget_measure.py` emits two explicitly synthetic capacity scenarios
and, with `--cuda`, one live CUDA resource snapshot plus classic/current resident
capacity plans. Synthetic rows are planning-model evidence only; they are never
hardware throughput claims.

Run from the repository root with the pinned Python wrapper:

```powershell
.dependencies/python/3.14.6/Scripts/python-jig.cmd `
  -m benchmarks.accelerator.resource_budget_measure --cuda
```

Retained evidence belongs under `benchmarks/accelerator/evidence/` with exact
commit/toolchain/device/command provenance.

`classic_run_throughput.py` measures 15 raw samples for batch sizes 1, 8, 32,
and 128. Each resident classic VM commits exactly 64 no-op transitions and must
finish by budget exhaustion; validation occurs outside the timed interval. This
is an end-to-end adapter measurement including host packing, transfer, kernel,
copy-back, and decode costs.

Run with:

```powershell
.dependencies/python/3.14.6/Scripts/python-jig.cmd `
  -m benchmarks.accelerator.classic_run_throughput
```

`classic_run_phase_profile.py` uses the adapter's diagnostic
`profile_evaluate()` path to retain wall-clock totals for validation/planning,
host batch construction, device allocation, upload, kernel+sync, download,
result decode, and release. The ordinary `evaluate()` path does not collect these
timings.

Run with:

```powershell
.dependencies/python/3.14.6/Scripts/python-jig.cmd `
  -m benchmarks.accelerator.classic_run_phase_profile
```

`profile_run_throughput.py` measures 15 end-to-end samples for batch sizes 1, 2,
4, 8, 16, and 32. The fixture derives current memory width from `3**14`; each VM
commits exactly 64 no-op transitions and materializes the complete 4,782,969-word
result. The timed region includes validation/planning, host assembly, allocation,
transfers, kernel execution, full result decode, and release.

Run with:

```powershell
.dependencies/python/3.14.6/Scripts/python-jig.cmd `
  -m benchmarks.accelerator.profile_run_throughput
```

`profile_run_phase_profile.py` measures the same current-profile workload with
adapter diagnostics split into validation/planning, host construction,
allocation, upload, kernel+sync, download, full result decode, and release. It
uses batch sizes 1, 8, and 32 with 15 samples each so phase evidence remains
comparable with the end-to-end throughput run without retaining redundant large
batch points.

Run with:

```powershell
.dependencies/python/3.14.6/Scripts/python-jig.cmd `
  -m benchmarks.accelerator.profile_run_phase_profile
```

`profile_resident_session_throughput.py` measures the steady-state launch boundary
for current-profile states that remain in device memory across repeated bounded
segments. Session setup, final compact observation, and optional full snapshots
are outside the timed `advance()` region by design. The benchmark prepares 960
no-op cells, executes fifteen 64-step resident segments, and records batch sizes
1, 8, 32, and 128.

Run with:

```powershell
.dependencies/python/3.14.6/Scripts/python-jig.cmd `
  -m benchmarks.accelerator.profile_resident_session_throughput
```

This session benchmark answers a different question from
`profile_run_throughput.py`: it measures continuation when a caller can keep
complete VM state resident, not end-to-end complete-snapshot latency. Do not use
its launch-only rate as a direct CPU-relative or complete-run speedup claim.

`search_throughput.py` compares the identical
`classic-rotate-target-search-v1` strategy on the mandatory CPU reference and
live CUDA candidate evaluator over the complete 59,049-word classic domain. One
untimed warmup per backend precedes 15 fixed interleaved CPU-then-CUDA retained
samples. Adapter construction/NVRTC setup is outside the timed region; each timed
search still includes canonical problem decode, exact-duplicate pruning, batch
construction, candidate evaluation, and proposal selection. Proposal equality and
independent CPU admission are checked after every timed call.

Run with:

```powershell
.dependencies/python/3.14.6/Scripts/python-jig.cmd `
  -m benchmarks.accelerator.search_throughput
```

Do not interpret the resulting ratio as compiler or superoptimizer speedup. It is
one bounded exact-search workload comparing replaceable execution capacity under
identical strategy semantics.

The retained RTX 4060 run is under
`evidence/2026-07-27-rotate-target-search-rtx4060/`. Its protocol-compliant result
is intentionally negative: CPU median 401.185 ms, CUDA median 412.570 ms, and
0.972x CUDA/CPU. Every sample preserves exact proposal equality and independent
CPU admission, so the evidence rejects a performance hypothesis without weakening
correctness.

`search_phase_profile.py` runs the same complete-domain workload through the
adapter diagnostic path and retains request validation, batch construction, batch
validation, backend evaluation, proposal selection, result validation, and total
wall time separately. It uses the same one-warmup/15-sample policy and validates
exact proposals plus independent CPU admission after every profile.

Run with:

```powershell
.dependencies/python/3.14.6/Scripts/python-jig.cmd `
  -m benchmarks.accelerator.search_phase_profile
```

Phase diagnostics are attribution evidence only. They do not change search
semantics and must not be compared with the ordinary throughput run unless the
workload, commit, device, warmup, and sample policy are identical.

The retained phase evidence is under
`evidence/2026-07-27-rotate-target-search-phase-profile-rtx4060/`. Named phases
explain 97.5% of CPU median total time and 99.5% of CUDA median total time. For
CUDA, host-side phases account for about 57.0% while backend evaluation accounts
for about 42.5%; batch construction plus proposal selection consume about
173.081 ms at their medians. This attribution motivates reusable prepared search
state before additional kernel work.

`search_prepared_throughput.py` compares four routes over the same complete-domain
workload: ordinary CPU, prepared CPU, ordinary CUDA, and prepared CUDA. One CPU
adapter prepares and validates immutable request/batch state before timing; the
identical strategy-bound proof is then reused by both CPU and CUDA. Preparation,
adapter construction, and NVRTC setup are outside timed intervals. One warmup
precedes 15 fixed interleaved samples of all four routes. Every sample still
checks exact proposal identity and independent CPU admission.

Run with:

```powershell
.dependencies/python/3.14.6/Scripts/python-jig.cmd `
  -m benchmarks.accelerator.search_prepared_throughput
```

Prepared measurements answer an amortized repeated-search question. They must not
be substituted for one-shot ordinary search latency.

The retained RTX 4060 evidence is under
`evidence/2026-07-28-prepared-search-rtx4060/`. CPU ordinary/prepared medians are
293.564/148.590 ms (1.976x), while CUDA ordinary/prepared medians are
306.872/162.693 ms (1.886x). Prepared CUDA remains about 9.5% slower than prepared
CPU. Preparation is outside all timed samples, and every route preserves exact
proposal identity plus independent CPU admission.
`search_prepared_phase_profile.py` attributes the amortized prepared path after
request/batch construction and validation have already completed. It retains
strategy-proof validation, backend evaluation, proposal selection, result
validation, and inclusive total time for 15 fixed interleaved CPU-then-CUDA
samples. Preparation, CUDA adapter construction, and NVRTC setup remain outside
timed intervals; every profile still checks exact proposals and independent CPU
admission.

Run with:

```powershell
.dependencies/python/3.14.6/Scripts/python-jig.cmd `
  -m benchmarks.accelerator.search_prepared_phase_profile
```

This diagnostic answers where prepared repeated-search time remains. It is not a
one-shot latency measurement and must not be used to count preparation as free in
workloads that cannot reuse immutable state.

The retained RTX 4060 evidence is under
`evidence/2026-07-28-prepared-search-phase-profile-rtx4060/`. CPU median total is
156.935 ms with 125.412 ms in backend evaluation and 30.796 ms in proposal
selection. CUDA median total is 170.276 ms with 138.320 ms in backend evaluation
and 31.912 ms in proposal selection. Named phases cover at least 99.6% of both
medians; candidate-evaluation result transport/materialization selected the next
measured optimization boundary. The active implementation now supports fixed-width
packed candidate evidence. The retained post-change throughput and phase bundles
are under `evidence/2026-07-28-packed-search-rtx4060/` and
`evidence/2026-07-28-packed-search-phase-profile-rtx4060/`. The active prepared
rotate path now also stores one validated decoded `PrimitiveBatch`. Retained
post-change throughput and phase evidence is under
`evidence/2026-07-28-prepared-primitive-search-rtx4060/` and
`evidence/2026-07-28-prepared-primitive-search-phase-profile-rtx4060/`. Prepared
CPU/CUDA medians improve 1.792x/1.592x, while ordinary routes regress 6.6%/3.7%.

The active prepared CUDA implementation now retains one proof-bound input/output
allocation across repeated calls. Both prepared benchmark programs emit and check
`cuda_prepared_session`: the full-domain protocol must observe one build, 16
successful evaluations, 15 identity reuses, and 59,049 resident rotate words.
Retained post-commit evidence is under
`evidence/2026-07-28-resident-primitive-search-rtx4060/` and
`evidence/2026-07-28-resident-primitive-search-phase-profile-rtx4060/`. CUDA
prepared reaches 34.132 ms versus 46.232 ms CPU prepared, while CUDA backend
evaluation falls to 9.922 ms. The complete CUDA phase profile does not improve
because proposal selection rises to 46.331 ms; that negative result is retained.

The active prepared-search proof now also carries an immutable exact membership
index. Both benchmark programs emit and validate `prepared_membership_count=59049`
so prepared proposal checks cannot silently rebuild the full candidate dictionary.
Retained post-commit evidence is under
`evidence/2026-07-28-indexed-membership-search-rtx4060/` and
`evidence/2026-07-28-indexed-membership-search-phase-profile-rtx4060/`. Prepared
CPU/CUDA medians reach 26.797/17.970 ms, and proposal selection reaches
11.801/11.761 ms. Ordinary/backend controls also improve, so the phase comparison
is the direct membership-index evidence.

The active rotate prepared selector now records the exact evaluated position of the
unique classic rotate preimage after pruning, seed rotation, and budget selection.
Both benchmark programs emit and require `prepared_selection_count=1` together with
`prepared_membership_count=59049` and the CUDA session counters. Prepared selection
still reads/validates backend evidence at that position; ordinary search retains the
full scan. Retained post-commit evidence is under
`evidence/2026-07-28-direct-rotate-selection-rtx4060/` and
`evidence/2026-07-28-direct-rotate-selection-phase-profile-rtx4060/`. Prepared
CPU/CUDA medians reach 15.266/6.182 ms, while selection reaches 13.2/12.4 us.
Backend phases move only about 3.5%, identifying primitive execution as the next
boundary. The active bridge now validates primitive result domain through exact
tuple extrema while preserving negative/overflow failure. These direct-selection
records remain the pre-change baseline until a post-commit rerun is retained.
