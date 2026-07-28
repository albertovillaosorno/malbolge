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
records are the pre-change baseline. Retained post-change evidence is under
`evidence/2026-07-28-extrema-validation-search-rtx4060/` and
`evidence/2026-07-28-extrema-validation-search-phase-profile-rtx4060/`. Prepared
CPU/CUDA medians improve 1.086x/1.254x and backend phases improve 1.091x/1.330x;
ordinary controls remain essentially flat/slightly slower.

The active prepared CPU implementation now generates the complete classic rotate
table once from the scalar reference and uses request-order table lookup only for
prepared execution. Ordinary CPU remains scalar. Both benchmark programs emit and
require `cpu_prepared_rotate` with 16 evaluations and 59,049 table entries, in
addition to selector/index/CUDA-session proofs. Retained post-commit evidence is
under `evidence/2026-07-28-cpu-rotate-table-search-rtx4060/` and
`evidence/2026-07-28-cpu-rotate-table-search-phase-profile-rtx4060/`. CPU prepared
reaches 3.313 ms, a 4.243x improvement, and CPU backend evaluation reaches
2.906 ms, a 4.540x improvement. CPU prepared is 1.440x faster than same-run CUDA;
CPU ordinary remains effectively unchanged and CUDA phases move only about 1.8%.

The active prepared CUDA route now emits `PackedPrimitiveResult` directly from the
resident host output buffer. The candidate bridge validates backend capability,
exact byte count, and every packed u32 domain value before reusing those bytes as
candidate evidence. Tuple results remain valid for CPU, ordinary CUDA, and test
adapters. Both benchmark programs now require
`cuda_prepared_session.packed_evaluations=16` together with the resident,
CPU-table, membership, and selector proofs. Retained post-commit evidence is under
`evidence/2026-07-28-packed-cuda-primitive-search-rtx4060/` and
`evidence/2026-07-28-packed-cuda-primitive-search-phase-profile-rtx4060/`. CUDA
prepared reaches 2.036 ms, a 2.343x improvement, and CUDA backend evaluation reaches
1.802 ms, a 2.147x improvement. CUDA prepared is 1.621x faster than same-run CPU;
CPU phases and ordinary controls remain effectively unchanged.

Packed validation now emits and requires
`packed_primitive_validation="u32le-broadword-domain-v1"`. Repeated high-bit,
threshold-delta, and threshold-carry masks validate independent 32-bit lanes; scalar
iteration is retained only to report an invalid maximum after failure. Tests reject
threshold and high-bit corruption in both first and final lanes. Retained evidence
is under `evidence/2026-07-28-broadword-packed-validation-search-rtx4060/` and
`evidence/2026-07-28-broadword-packed-validation-search-phase-profile-rtx4060/`.
CUDA prepared reaches 1.175 ms, a 1.733x improvement, while CUDA backend evaluation
reaches 0.860 ms (2.095x) and CUDA total 0.886 ms (2.057x). CUDA prepared is 2.706x
faster than same-run CPU. CPU phase regressions are retained as controls and are not
attributed to this CUDA-targeted validator change.

Run the active prepared CUDA primitive subphase profiler with:

```powershell
.dependencies/python/3.14.6/Scripts/python.exe -m benchmarks.accelerator.prepared_cuda_primitive_phase_profile
```

The historical retained profile composes public resident-CUDA and neutral
broadword diagnostics. The active prepared route now uses immutable exact CPU truth
under `cpu-reference-packed-equality-v1`; ordinary packed output retains
`u32le-broadword-domain-v1`. Preparation is untimed and retains one expected u32le
word per candidate. Prepared profiling reports launch/sync, D-to-H, immutable byte
creation, capability/shape contract, exact byte comparison, result construction,
visible residuals, layer totals, and end-to-end total. Search throughput and phase
profiles emit and validate both identities plus `prepared_reference_word_count`.
All full-domain runs must observe 59,049 reference words and the existing
CPU-table/session/membership/selector proofs. First/last in-domain corruption tests
fail closed. Retained post-commit evidence is under
`evidence/2026-07-28-prepared-reference-search-rtx4060/`,
`evidence/2026-07-28-prepared-reference-search-phase-profile-rtx4060/`, and
`evidence/2026-07-28-prepared-reference-primitive-phase-profile-rtx4060/`. CUDA
prepared reaches 0.488 ms (2.407x), backend evaluation reaches 0.215 ms (3.999x),
and search total reaches 0.238 ms (3.729x). Exact validation reaches 0.0278 ms
(23.590x), exact compare 0.0180 ms, and primitive end-to-end 0.1935 ms (4.488x).
The one-time 236,196-byte CPU reference is outside retained intervals. A dedicated
preparation/memory/crossover benchmark is the next protocol step.

Run the active preparation, membership-index, and reuse-crossover benchmark with:

```powershell
.dependencies/python/3.14.6/Scripts/python.exe -m benchmarks.accelerator.search_preparation_crossover
```

`search_preparation_crossover.py` measures preregistered candidate counts 1, 64,
1,024, and 59,049. For every scale it retains 15 fresh-process cold preparations,
15 warm-process preparations after the global rotate table is built, five
incremental `tracemalloc` memory observations, 15 ordinary CUDA calls, 15 fresh
resident-build calls, and 15 resident reuses after one build and one warmup. Version
4 retains 15 component preparations and five component memory samples for the active
index and copied-tuple `frozenset`, plus 15 exact hit and miss timing blocks of 4,096
lookups per index. It requires indexed-candidate, membership, and proof-bound packed
primitive-storage identities in the proof record.
Workload construction, CUDA/NVRTC adapter setup, and trusted result admission are
outside timed intervals. Fresh-build timing includes resident allocation/upload and
one exact search. Memory tracing excludes the prebuilt workload, global rotate
table, CUDA allocations, and other native allocations; exact reference, host-output,
and device-buffer byte counts are reported separately.

The strict crossover is the first positive `runs` satisfying
`prepare + first_build + (runs - 1) * reuse < runs * ordinary`. Cold preparation is
sampled in a new Python process each time; warm preparation shares the process-wide
exact rotate table. Every sample preserves ordinary/prepared validator IDs, one
exact admitted proposal, proof-bound reference/membership/selector counts, and
fresh/reused CUDA session counters. Retained evidence is under
`evidence/2026-07-28-prepared-search-crossover-rtx4060/`. Warm crossover is
6/3/2/1 and cold crossover is 106/38/5/2 across the four scales. Full-domain warm
preparation plus first search is 212.140 ms versus 222.842 ms ordinary; cold crosses
on run two. Incremental traced Python state retains 16.063 MiB and peaks at
19.040 MiB, while exact reference/device/host buffers total 0.901 MiB. Component tracing selected the prepared membership frozenset as the first compaction
target. The active index identity is
`identity-sorted-candidate-reference-binary-search-v1`: it stores sorted references
to existing immutable candidate items and checks exact ID/payload membership by
binary search. Retained version-2 evidence is under
`evidence/2026-07-28-compact-membership-crossover-rtx4060/`. At full domain the
compact component retains 473,352 bytes versus 5,876,552 bytes for the copied set
(91.945% lower) and prepares in 15.851 ms versus 18.027 ms (1.137x faster). Complete
prepared state falls from 16.063/19.040 MiB retained/peak to 10.910/14.080 MiB.
Compact hit/miss lookup is 2.625/2.785 microseconds versus 0.265/0.201 microseconds,
9.898x/13.856x slower. Warm crossover is 7/3/2/1 and cold crossover 108/38/5/1.
The result promotes compact membership for scale memory/preparation while retaining
the lookup regression. This is the retained version-2 baseline.

Retained version-3 evidence under
`benchmarks/accelerator/evidence/2026-07-28-indexed-candidate-batch-crossover-rtx4060/`
promotes proof-carrying fixed-width candidate storage for large deterministic
batches. At 59,049 candidates, complete prepared state falls from 10.910 to 2.923
MiB retained (73.211%) and from 14.080 to 8.395 MiB peak (40.378%). Warm/cold
preparation improves from 194.917/207.761 ms to 117.753/132.553 ms
(1.655x/1.567x), while ordinary CUDA search improves from 222.518 to 152.998 ms
(1.454x). Warm/cold preparation plus first resident search is 129.508/144.308 ms,
so both retain one-run crossover with 23.490/8.691 ms observed margins. The
rotation-backed membership component retains 528 bytes versus 473,352 bytes in
version 2 and 11,180,412 bytes for the same-run copied set; its preparation is
0.0177 ms versus 15.8507/155.4303 ms. Exact hit lookup is the retained cost:
17.755 microseconds versus 2.625 microseconds in version 2 and 0.266 microseconds
copied (6.763x/66.844x slower). Exact miss lookup improves to 0.636 microseconds
from 2.785 microseconds in version 2, but remains 3.094x slower than copied-set
miss lookup. The promotion is not universal: one-candidate memory grows slightly,
and 64-candidate cold/warm crossover moves from 38/3 to 45/4. Duplicate or
out-of-domain indexes, malformed widths/sizes, incorrect pivots, forged or
cross-batch proofs, and payload substitution still fail closed. Retained version-4 evidence under
`benchmarks/accelerator/evidence/2026-07-28-packed-prepared-primitive-crossover-rtx4060/`
promotes `proof-bound-u32le-primitive-input-v1`. At 59,049 candidates,
incremental retained prepared state falls from 3,064,623 to 713,791 bytes, a
76.709% reduction and 12.088 bytes per candidate. Peak allocation remains exactly
8,802,328 bytes (8.395 MiB): preparation still builds a temporary CPU
reference/decode tuple, so the result removes retained ownership rather than the
transient peak. Full-domain cold/warm crossover remains 1/1. Against the immediate
clean `81d82cf` baseline, CPU ordinary/prepared improve from 139.517/3.316 ms to
132.848/3.261 ms (1.050x/1.017x), while CUDA ordinary/prepared improve from
152.055/0.449 ms to 144.440/0.429 ms (1.053x/1.047x). Phase totals are 2.9664 ms
CPU (1.006x) and 0.2654 ms CUDA (1.099x). CPU and CUDA both prove one session
build, 16 evaluations, 15 reuses, rotate kind, and 59,049 resident words; CUDA
also proves 16 packed evaluations and CPU proves the full rotate table. The packed
representation is promoted because no clean route regresses. The unchanged
temporary reference/decode tuple is the next peak-memory boundary; it may be
removed only while preserving an independently generated exact reference and the
same first/last corruption, forged-proof, and fabricated-proposal failures.
