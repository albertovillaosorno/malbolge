# CUDA exact accelerator adapter

This directory owns the optional NVIDIA CUDA implementation behind the shared
accelerator contract. It is not a semantic dependency of the compiler, verifier,
or VM.

The active slices evaluate exact classic `rotate`/`crazy` batches, compact
one-step classic transitions, and complete resident bounded runs with integer-only
CUDA kernels. The resident kernel is geometry-bound: classic uses 10 trits and
59,049 words, while `malbolge-2026.2` uses 14 trits and 4,782,969 words. One GPU
thread owns one independent complete memory image and performs its whole step
budget without round-tripping guest state through the host between steps. A narrow
standard-library `ctypes` runtime binds only the reviewed NVRTC and CUDA Driver API
calls needed by the adapter. Normative Rust execution remains the differential
correctness oracle.

Hardware-neutral `evidence-bound-ticket-route-admission-v1` now gives ticket
grouping an explicit evidence gate. It validates exact backend, device, and
workload identity plus exact output, lower candidate median, and a strict
paired-win majority; malformed or duplicate route records fail closed. Plans
preserve input order, minimize chunk count, then measured median cost, and
prefer synchronous ties. Opt-in
`evidence-bound-ticket-route-admission-report-v1` publishes one immutable
assessment per retained route in input order. It distinguishes context
mismatch, inexact results, no median improvement, no paired majority, and a
group larger than the pending queue. Eligible but unused routes remain visible
with zero selected counts; the report also records selected chunks/tickets,
fallback tickets, synchronous/streamed totals, and the unchanged plan. It reads
no additional evidence, performs no online learning, and changes no default.
`bounded-ticket-admission-telemetry-v1` retains completed reports in a
caller-owned positive-capacity FIFO.
`bounded-ticket-admission-failure-telemetry-v1` independently retains failed
accelerator attempts as unavailable, invalid-input, execution, or other stable
categories without exception text. Both immutable snapshots expose monotonic
sequence IDs, eviction counts, measured/estimated duration delta, and exact
selected-route usage. Malformed reports, timings, or foreign failures fail
before mutation. `TicketAdmissionAttemptTelemetry` pairs the two FIFOs, and a
separate retained CUDA attempt executor records exactly one outcome before
returning or re-raising the same accelerator error. The ordinary and existing
completion-only executors remain unchanged.
`ticket-admission-telemetry-document-v1` captures both snapshots as compact,
sorted-key schema-v1 JSON. Decoding defaults to a 1 MiB byte limit and 4,096
observations per FIFO, rejects duplicate, unknown, oversized, and noncanonical
input, and restores exact sequence and eviction state. File reads and writes are
explicit; writes use a same-directory temporary file and atomic replacement.
`offline-ticket-admission-telemetry-summary-v1` validates one explicit document
and groups retained observations by exact backend, device, workload, and ticket
count. It publishes completed/failed integer totals, estimate-comparison counts,
retention ranges, stable failure categories, and sorted selected-evidence
appearances. It does not merge documents, recommend routes, or modify admission.
There is no automatic loading, hidden worker, automatic promotion, or policy
authority. The retained
`rtx4060-full-domain-crazy-ticket-admission-2026-07-29-v1` profile binds the RTX
4060 `sm_89` capability and full-domain CRAZY workload to source commit
`431f542ab6321eeb12b7bcb9195318f25cf376a5`. It admits synchronous groups 2/4/8
and rejects streamed routes 1/2/4/8; a ten-ticket queue therefore selects groups
2+8 at a 7.3271 ms estimated median. The opt-in executor validates the packed
workload SHA-256, reverse-waits each group, restores input order, and closes
every ticket. Sixty-eight admission/telemetry/persistence/summary tests cover fallback, positive/negative
evidence, duplicate/malformed records, exact profile matching, seven isolated
runtime drifts, multi-profile selection, invalid/unknown workloads, ambiguity, and
three live CUDA routes. The seven route records and exact
provenance now live in schema-v4
`accelerator/cuda/ticket_admission_profiles.json`, not Python source.
`benchmarks/accelerator/ticket_admission_profile_manifest.py` reconstructs those
canonical bytes from retained JSON/TOML, source commit, exact raw/structured-output
hashes, the tracked CUDA toolchain manifest, retained driver build, and retained
host/Python context. Twelve manifest tests require byte equality and reject
duplicate or unknown keys, unsupported schema, duplicate routes, malformed display
versions, invalid host fields, exact runtime-context duplicates, and direct
capability/runtime mismatch; distinct runtime variants may coexist for one
capability/workload. Runtime loading reads only the tracked product manifest and
never opens benchmark evidence. `resolve_cuda_ticket_admission_profile` selects at
most one exact workload/capability/runtime record; invalid or ambiguous requests
fail closed, while retained wrappers delegate through the stable workload identity. At adapter
startup, `cuda-runtime-toolchain-identity-v1` requires Driver API 13030 or newer,
exact NVRTC 13.3, the tracked toolchain SHA-256, and NVML display build `610.88`;
`cuda-host-runtime-identity-v1` measures Windows 11 Professional build
`10.0.26200`, `x86_64`, and CPython `3.14.6`. Missing or failed optional NVML or
host measurement leaves ordinary CUDA available but this evidence-bound profile
unmatched. Fourteen runtime-identity tests cover required query/hash failures,
NVML lifetimes, host validation, exact live host measurement, and one live CUDA
route. Other hosts, Python versions, driver builds, devices, and workloads remain
open. The global synchronous default does not change.

The repository pins CUDA 13.3 Update 1 for Windows x86-64 through
`toolchain.json`. Binary redistributables live under ignored
`.dependencies/cuda/13.3.1/`, and every downloaded archive is checked against
the recorded NVIDIA SHA-256. The active adapter requires no third-party Python
packages beyond the repository's pinned Python runtime.

This is not yet a cross-platform runtime. `runtime.py` currently uses
`ctypes.WinDLL`, `nvcuda.dll`, a versioned NVRTC `.dll`, and a literal 13.3.1
repository path. The pending [CUDA Linux runtime and hermetic toolchain
contract](../../docs/technical/integrations/accelerators/cuda-linux-runtime-and-toolchain.md)
requires `ctypes.CDLL` plus reviewed `.so` identities on Linux and moves CUDA
release/path selection into per-platform manifests. The project initializer
reports a non-Windows CUDA manifest mismatch as unsupported rather than claiming
fallback support.

Development evidence on an NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB) runs
NVRTC-generated PTX through the Driver API and matches the CPU reference for
boundary-heavy plus deterministic `rotate`/`crazy` batches. Rust integration also
sends fourteen compact transition fixtures through an external CUDA worker and
requires exact equality with normative `Machine::step_traced()` across all seven
instructions, no-op, EOF, non-graphical termination, rejected jump atomicity,
pointer wrap, data/encryption aliasing, and already-terminated state. A second
Rust integration sends nine complete classic resident states through a binary
worker and compares all 59,049 memory words plus registers, I/O, termination,
step counts, and atomic rejection. A scalable integration separately supplies
canonical geometry from Rust `current_profile()` and compares eight complete
`malbolge-2026.2` outcomes across all 4,782,969 final memory words, including real
I/O, EOF, non-graphical termination, rejected jump atomicity, maximum-pointer
wrap, bounded budget exhaustion, live checkpoint resumption, and
already-terminated execution. This is correctness evidence, not a
speedup claim.

The classic resident path now measures free/total device memory with
`cuMemGetInfo_v2` and SM/thread capacity with `cuDeviceGetAttribute`, then applies
the hardware-neutral resource planner before allocation. There is no fixed
RTX-specific batch ceiling. Classic launches also split before their 32-bit memory-index product can
overflow. Very large VRAM therefore expands total capacity without requiring one
unsafe monolithic launch. Scalable profile execution uses the same live resource
planner and compact contiguous 32-bit host memory representation. Rust product
batch ports now route both classic and current-profile requests through the real
CUDA workers while retaining safe-Rust fallback. The original current-profile
RTX 4060 baseline remains under
`benchmarks/accelerator/evidence/2026-07-27-current-profile-throughput-rtx4060/`.
Post-optimization evidence under
`benchmarks/accelerator/evidence/2026-07-27-current-profile-resident-session-rtx4060/`
uses device-to-device replication for shared initial memory: complete-snapshot
batch 32 reaches about 51.67 VMs/s, about 1.289x the retained baseline, and
median upload time falls about 6.93x. Persistent profile sessions separately
reach about 2.00 million 64-step VM segments/s at batch 128 when setup, compact
observation, and snapshots are outside the timed `advance()` region. Validated
`ProfileMemoryImage` inputs now reuse their geometry/domain proof across calls;
retained complete-snapshot batch 32 reaches about 93.68 VMs/s and median
validation/planning is about 0.23 ms. Complete-snapshot materialization,
asynchronous transfer/stream tuning, broader hardware evidence, and CUDA
superoptimization remain open.

Direct current-profile snapshot evidence is retained under
`benchmarks/accelerator/evidence/2026-07-27-current-profile-direct-snapshot-rtx4060/`.
The adapter downloads complete memory directly into each final `array('I')`;
batch 32 reaches about 93.68 VMs/s and batch 1 about 60.43 VMs/s on the
retained RTX 4060 workload. This removes redundant packed host staging/copying;
it does not remove the requested full-state transfer.

