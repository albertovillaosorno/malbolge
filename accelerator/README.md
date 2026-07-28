# Replaceable accelerator boundary

`accelerator/` owns optional execution capacity behind hardware-neutral exact
contracts. Accelerator results never become semantic authority merely because a
GPU produced them.

The first implemented port is `ExactPrimitiveAdapter`, which batches classic
Malbolge `rotate` and `crazy` over the exact 59,049-word domain.
`ClassicStepRequest`/`ClassicStepResult` represents one specification-mode classic
VM transition over at most four explicitly declared memory cells.
`ClassicRunRequest`/`ClassicRunResult` carries one complete 59,049-word classic
state through bounded resident execution. `ProfileRunGeometry` plus
`ProfileRunRequest`/`ProfileRunResult` extends that boundary to validated
single-word-modular ternary profiles without embedding CUDA identity. The current
14-trit/4,782,969-word profile now executes through the same geometry-bound CUDA
kernel model. `accelerator/cpu/` remains the mandatory scalar primitive reference;
CUDA results are checked against normative Rust execution. Compiler and verifier
code do not import CUDA APIs.

Missing accelerator hardware changes availability/performance only. Malformed
requests fail in the shared contract before backend execution; accelerator
runtime failures are explicit and never silently change acceptance rules.
`resource_budget.py` additionally owns hardware-neutral measured resource
snapshots and deterministic resident chunk planning; it does not know CUDA APIs.

Rust product batches now route through hardware-neutral optional backends with
safe-Rust fallback. RTX 4060 current-profile evidence now includes device-side
shared-state replication and persistent scalable sessions. Complete-snapshot
batch 32 reaches about 51.67 VMs/s, while resident batch 128 reaches about
2.00 million 64-step segments/s when setup and snapshots are outside the timed
region. `ProfileMemoryImage` now carries reusable geometry-bound validation proof;
retained batch-32 complete-snapshot throughput reaches about 93.68 VMs/s and
validation/planning falls to about 0.23 ms. Direct complete-snapshot materialization now downloads into final result
arrays without redundant packed host staging; full-state transfer/page commitment
remains a measured cost. `work_ports.py` now defines hardware-neutral candidate
evaluation, search execution, verification-assist, and trusted-admission
boundaries. CPU callback adapters provide mandatory candidate/search execution
capacity while search proposals and verification hints remain untrusted.
`search_selection.py` independently resolves algorithm and backend bindings,
requires a CPU reference, supports explicit overrides, and records configured
versus actual backend identity after fallback. `search_config.py` adds versioned
TOML base selection with fail-closed schema/identity validation and durable source
identity; explicit overrides produce a new effective selection without mutating
the loaded configuration. `primitive_candidates.py` binds
classic crazy/rotate candidate payloads to any exact primitive adapter; the same
bridge is differentially exercised through CPU and live CUDA backends.
`evidence_verification.py` reuses candidate evidence as optional verification
hints without introducing backend acceptance authority, and live CUDA hints match
the CPU reference over a deterministic 257-item corpus. `evaluated_search.py`
adds a bounded map/select search adapter that only proposes members of the exact
evaluated batch. `classic-rotate-target-search-v1` uses that adapter with identical
CPU/CUDA strategy logic; live CUDA records actual backend identity, matches CPU
proposals over 257 candidates, and remains subject to independent CPU admission.
`python -m optimizer.cli` is the first external search runner: it reads Search
Configuration v1 plus canonical problem bytes, accepts explicit algorithm/backend
overrides, and emits deterministic JSON containing problem SHA-256,
configured-versus-actual backend identity, device metadata, seed/budget, and only
untrusted proposals. Supported CUDA setup failure preserves configured CUDA intent
while safely falling back to CPU; unsupported algorithm/backend pairs fail
explicitly. The retained full-domain comparison at
`benchmarks/accelerator/evidence/2026-07-27-rotate-target-search-rtx4060/`
contains 15 samples per backend under Benchmark Protocol v1. CPU median is
401.185 ms and CUDA median is 412.570 ms over all 59,049 classic words, yielding a
0.972x CUDA/CPU ratio and rejecting the speedup hypothesis for this complete
host-heavy route. Proposals remain identical and independently admitted. This
negative result motivates larger or resident search designs rather than hidden
benchmark filtering. The retained phase profile at
`benchmarks/accelerator/evidence/2026-07-27-rotate-target-search-phase-profile-rtx4060/`
shows 97.5% CPU and 99.5% CUDA named-phase coverage. CUDA host-side phases account
for about 57.0% of median total time, backend evaluation about 42.5%, and batch
construction plus proposal selection about 173.081 ms.
`PreparedEvaluatedSearch` now carries immutable validated request/batch state bound
to exact algorithm, batch-builder, and selector identity. It can be prepared once
through CPU and reused unchanged through matching CPU or CUDA adapters; forged or
mismatched strategy state fails closed. Prepared execution and diagnostics avoid
repeated batch construction/validation, while rotate-target selection decodes only
the validated header target instead of rebuilding the complete corpus. The
ordinary-versus-prepared evidence is retained under
`benchmarks/accelerator/evidence/2026-07-28-prepared-search-rtx4060/`. CPU median
falls from 293.564 to 148.590 ms (1.976x), and CUDA median falls from 306.872 to
162.693 ms (1.886x). Prepared CUDA remains about 9.5% slower than prepared CPU
(0.913x CPU-prepared/CUDA-prepared). These are amortized repeated-search results;
preparation is outside the timed interval. The retained prepared phase profile at
`benchmarks/accelerator/evidence/2026-07-28-prepared-search-phase-profile-rtx4060/`
shows backend evaluation consuming 79.9% of CPU and 81.2% of CUDA median total
time; proposal selection consumes 19.6% and 18.7%. Proof/result validation is
negligible. `PackedCandidateEvidence` now implements that boundary with one
fixed-width opaque payload buffer whose logical identities are inherited from the
validated batch order. Generic item results remain compatible; width, size, and
mixed-form drift fail closed. Primitive search iterates packed u32 values without
per-candidate bytes/objects, while verification-assist materializes only at the hint
boundary. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-packed-search-rtx4060/` lowers CPU
ordinary/prepared medians to 211.693/77.309 ms and CUDA medians to
230.144/91.199 ms, improvements of 1.387x/1.922x and 1.333x/1.784x over the
pre-packed routes. The sibling packed phase profile lowers backend evaluation to
53.907 ms CPU and 67.202 ms CUDA. Packed CUDA prepared remains about 18.0% slower
than packed CPU prepared. `PreparedCandidateExecution` now lets a strategy attach
hardware-neutral decoded candidate state to the existing proof. Rotate search
prepares one validated `PrimitiveBatch`; matching CPU/CUDA adapters consume it
without repeated candidate batch validation or payload decode. The preparer is
part of strategy identity, and forged type/kind/evaluator state fails closed.
Ordinary one-shot search still prepares locally. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-prepared-primitive-search-rtx4060/`
records 43.129 ms CPU and 57.296 ms CUDA prepared medians, 1.792x/1.592x faster
than the packed baseline. Ordinary routes regress 6.6%/3.7%, and prepared CUDA
remains 32.8% slower than prepared CPU. The phase bundle lowers backend evaluation
2.801x CPU and 2.083x CUDA. `PreparedPrimitiveBatch` now carries reusable exact
validation proof. CPU consumes it directly; CUDA prepared execution keeps one
proof-bound input/output allocation resident and rebuilds only when proof identity
changes. Ordinary CUDA stays one-shot. `CudaPreparedPrimitiveStats` and the prepared
benchmarks require one build, 16 evaluations, 15 reuses, and 59,049 resident rotate
words. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-resident-primitive-search-rtx4060/`
records 34.132 ms CUDA prepared versus 46.232 ms CPU prepared: a 1.355x same-run
CUDA advantage and 1.679x CUDA improvement over the pre-resident baseline. The
phase sibling lowers CUDA backend evaluation 3.252x to 9.922 ms, but complete phase
total stays at 55.910 ms because selection rises to 46.331 ms. Proposal
selection/membership validation selected the next boundary.
`PreparedEvaluatedSearch` now stores a `frozenset` of exact `(logical_id, payload)`
pairs built after batch validation. Prepared CPU/CUDA validation reuses it; ordinary
search remains one-shot, and forged payloads fail closed. Both prepared benchmarks
require exactly 59,049 indexed members. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-indexed-membership-search-rtx4060/`
records 26.797 ms CPU prepared and 17.970 ms CUDA prepared, 1.725x/1.899x faster
than the resident baseline. CUDA prepared is 1.491x faster than same-run CPU. The
phase sibling lowers proposal selection 3.519x CPU and 3.939x CUDA to
11.801/11.761 ms. Improved controls bound total attribution.
`PreparedProposalSelection` now binds strategy-specific selector state into the
prepared proof. Rotate target preparation computes the unique classic rotate
preimage after pruning/seed/budget and retains its evaluated positions. Prepared
selection validates only those packed evidence words; ordinary search keeps the
full scan. Missing/excluded positions, forged state, and nonmatching evidence fail
closed, and benchmarks require one prepared position. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-direct-rotate-selection-rtx4060/`
records 15.266 ms CPU prepared and 6.182 ms CUDA prepared, improvements of
1.755x/2.907x over indexed membership. CUDA is 2.470x faster in the same run. The
phase sibling lowers selection to 13.2/12.4 us (894.008x/948.452x), while backend
phases change only 1.034x/1.035x. Primitive result validation now checks exact
minimum/maximum tuple bounds rather than a Python per-value loop, preserving
negative/overflow rejection before packing. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-extrema-validation-search-rtx4060/`
records 14.058 ms CPU prepared and 4.929 ms CUDA prepared, improvements of
1.086x/1.254x over direct selection. Backend phases improve 1.091x/1.330x while
ordinary controls remain nearly flat. Prepared CPU rotate now reuses a cached
59,049-entry table generated from the scalar reference formula. Ordinary CPU stays
scalar, the exhaustive test compares every classic word, and benchmarks require
16 prepared evaluations plus the full table cardinality. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-cpu-rotate-table-search-rtx4060/`
records 3.313 ms CPU prepared, 4.243x faster than extrema validation and 1.440x
faster than same-run CUDA. The phase sibling lowers CPU backend evaluation 4.540x
to 2.906 ms while CUDA changes only 1.018x. `PackedPrimitiveResult` now carries
canonical little-endian u32 words alongside tuple results. Prepared CUDA returns the
resident host buffer as bytes after D-to-H transfer; the candidate bridge validates
capability, exact byte count, and every classic-domain word before forwarding those
same bytes. Ordinary CUDA and CPU tuple routes remain unchanged. Benchmarks require
`packed_evaluations=16` with the existing proofs. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-packed-cuda-primitive-search-rtx4060/`
records 2.036 ms CUDA prepared, 2.343x faster than the CPU-table baseline and
1.621x faster than same-run CPU. The phase sibling lowers CUDA backend evaluation
2.147x to 1.802 ms while CPU changes only about 0.5%. CPU result validation/packing
and packed-domain validation are the next backend subphases.
Synthesis/guided search, ROCm work ports and VM execution, broader hardware
evidence, richer orchestration, and additional representative comparisons remain
follow-on work. `optimizer/enumerative.py` supplies the first concrete CPU-only
search strategy: deterministic finite-corpus enumeration with canonical replay
identity and independent trusted verification.
