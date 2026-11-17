# Malbolge delivery roadmap: P2 through P10

## Why this roadmap exists

As of 2026-11-16, the unfinished [TODO index](../../TODO.md) groups
**51 open typed records**.
They represent real work but are not 51 equally urgent steps. The old P2
mixed compiler correctness with native execution and benchmark research.
This plan makes the earliest product milestone explicit: **a CPU-only
compiler that actually executes a useful C program inside Malbolge**.

The phase numbers are ordered delivery horizons, **not deadlines, percentages,
promises of broad C support, or a mandate to do each phase serially**. Typed
TODOs retain exact acceptance, dependencies and contract ownership. A phase
gate may be ready while an optional, separately tracked task remains open;
no task is silently declared complete to create a cosmetic green phase.

Historical P0/P1 groundwork is retained in completed records. The former
P0 byte-emission effort is the first P2 blocker. Dated references to "P0"
inside prior experiment evidence remain historical, not new scheduling.

## The first usable product: critical path

```text
P2: guest state, arithmetic, dynamic branch, EOF and real compound C
                         |
P3: supported deterministic-C subset and binary stream semantics
                         |
P4: independent source-to-guest verification and reproducibility
                         |
P5: CPU-first one-command release  <-- FIRST USABLE DELIVERY
                         |
       +-----------------+-----------------+
       |                 |                 |
P6: CPU search       P7: native tiers    P9: self-hosting
       |                 |                 |
       +-------> P8: large-programs        |
                      |                    |
                      +--------+-----------+
                               |
                       P10: verified papers
```

Safety, memory correctness, target-profile identity and verifier authority
apply **in every phase**. Native tiers, accelerators, DOOM, research papers
and all optional edge-case permutations do **not** block P5.

## Immediate execution queue (P2, not another fixture ladder)

1. **Freeze one demanding complete C source** with initialized mutable
   locals, a running checksum, integer arithmetic, an input-dependent
   branch, `getchar()` until EOF and `putchar()`. Keep a separately computed
   native C23 oracle. First attempt the unmodified source through the
   pinned frontend, typed adapter, ternary lowering, layout and normative VM.
2. **Repair the earliest stage that rejects this same program.** The
   current recorded first refusal is the initial automatic declaration;
   subsequent expected blockers are guest-resident mutable state,
   input-dependent arithmetic/branching, and EOF-driven loop execution.
   Do not predetermine which lower layer is responsible before reproducing
   it. Every repair must preserve actual guest effects and provide a minimal
   red-first regression.
3. **Rerun that exact compound program after each repair.** Publish no
   artifact after a failed stage. Report which constructs now execute in the
   guest versus which remain compile-time static proofs. Do not count an
   additional byte-preserving `if`, `switch`, or `emit-N` source as P2
   progress without a new capability on this critical path.
4. **Prove the phase exit**, then broaden the matrix: empty input, one byte,
   NUL, `0xff`, mixed binary and EOF, output/state mutation controls,
   defined C23 native controls at `-O0`/`-O2`, finite VM instruction budgets
   and independently reproducible artifacts. Add a seeded matrix only
   after the general behavior works.

The active typed record is the
[byte-stream task](open/compiler/parametric-guest-byte-stream-emission.mdc).
The backend owners are
[ternary lowering](open/compiler/ternary-machine-lowering.mdc) and
[layout/encoding](open/compiler/malbolge-layout-and-encoding-backend.mdc).

## Phase gates and evidence requirements

### P2 — Execute real stateful C

**Gate:** one ordinary compound C program with mutable locals,
input-dependent arithmetic and a branch, an EOF-driven loop, and binary
output executes in the normative guest VM. For independently chosen inputs
its bytes and termination match the native C23 oracle, under finite
resources. Demonstrate that those operations run in the guest, not by
host-time folding. Retain failing-stage diagnostics and a no-artifact
negative control. Also keep the compiler's resumption/progress evidence
honest for expensive jobs.

**Current blocker:** the complete EOF checksum still refuses at the first
declaration; finite constant-state and byte-preserving probes are not
evidence that dynamic C state/branch/EOF semantics exist. **Gate: open.**

### P3 — Complete supported C I/O semantics

**Gate:** publish an exact *supported subset* of deterministic C; every
accepted `tools/tidy` lowerability verdict compiles for the declared
profile, with explicit refusals outside the subset. Verify variable-length
binary I/O including zero bytes, high-bit bytes, empty input, multiple
reads/writes and EOF; never use a host-managed output transcript as the
guest program. Preserve source locations and a verifier-replay route.

**Status:** open; P2 compound-program semantics are a prerequisite.

### P4 — Verify, link, and inspect generated programs

**Gate:** source/typed IR/target correspondence has an independently
checkable acceptance trace, including state, positional decode, relocation
and self-modification. Verify at least two behaviorally distinct complete
source programs, repeat builds under declared deterministic conditions and
retain artifact identities, source maps and negative cases. Make a small
versioned example set with exact oracles. Verification must not trust the
optimizer/search process that proposed the layout.

**Status:** open. CPU optimization, annotated source ergonomics and
proof-carrying experiments may proceed in parallel, but a bounded
independent verifier is the P5 blocker.

### P5 — Ship the CPU-first compiler

**Gate:** satisfy the
[CPU release](../technical/compiler/cpu-first-c-to-malbolge-release.md).
From a clean checkout on a declared supported Linux host, the documented
pinned bootstrap and a single stable command compile two real supported C
programs to verified `.malbolge` artifacts. The real guest VM matches
independent native C23 oracles over binary/EOF controls. Unsupported code,
profile mismatch and interrupted/invalid publications fail without
clobbering outputs. Publish the precise supported subset and limits.

**Status:** not yet ready; this is the **first product-release milestone**.
It is narrower than the P7 multi-host turnkey contract.

### P6 — Scale compilation with verified reuse

**Gate:** measure CPU-only compile time, memory, target size, verifier cost
and success rate on an explicitly chosen seeded challenge family. Establish
a reference search, semantic pruning, verified reusable blocks and a
bounded algorithm evaluation arena. Separate cold, warm, reused and novel
work; record Pareto/latency evidence. Try compact guest bytecode and a
resident compiler only if they improve the measured bottleneck. Every
candidate must pass the same deterministic verifier; no raw CPU/GPU speed
claim becomes correctness evidence.

**Status:** conditional on working program classes; none of this blocks P5.

### P7 — Native execution and turnkey packaging

**Gate:** retain the literal interpreter as normative fallback; verify
native x86-64/AArch64 AOT and guarded JIT equivalence across
self-modification, I/O, halting and state transitions. Expose independently
testable tier controls and supported host capability runners. Close the
[turnkey contract](../technical/compiler/turnkey-c-to-malbolge-toolchain.md)
on its declared Windows/Linux host matrix, including CPU fallback and
optional CUDA setup. Do not claim native performance without measured tests.

**Status:** later delivery; the CPU-only P5 product does not wait for it.

### P8 — Accelerators and substantial programs

**Gate:** compare verified CUDA and optional model-guided proposals against
the P6 CPU baseline, reporting unavailable hardware honestly. Demonstrate
a substantial real program beyond small examples. For DOOM specifically,
native C debug playability is **not** proof that generated Malbolge code is
playable; measure guest execution, correctness and frame/latency behavior.
Only after prerequisite evidence pursue Apollo AGC and reproducible
cross-application benchmarks.

**Status:** hardware-conditional and downstream of P5/P6/P7 capabilities.

### P9 — Self-hosting and guest-machine applications

**Gate:** implement the essential compiler in the admitted portable C
subset, compile that implementation into actual Malbolge, then make the
resulting guest compiler compile another supported C input. Compare its
output with the native toolchain using independently checked semantic
equivalence, not only equal hashes. The RV32I guest runner is a separate
large-program proof after its AGC and binary-stream prerequisites.

**Status:** blocked on working general guest runtime functionality;
a host interpreter or a precomputed artifact does not count. The portable
self-hosting path need not wait for CUDA or DOOM; only the separate RV32I
runner retains its Apollo/large-program dependency.

### P10 — Publication and conditional research

**Gate:** publish only verified, reproducible claims with fixed evidence
identities, bibliography, generated figures, benchmark limitations and
applicable hardening checks. Historical demonstrations, human-search
studies and the systems/compiler paper follow product and self-hosting
results. Effective transcendental mathematics is an independent paper,
not a shipping prerequisite.

**Optional, not part of the first release:** hexagonal authoring, the
source-bound diff generator, ROCm reservation, and higher-arity symmetry
work. Promote a task from this parking area only with measured impact,
supported hardware and maintainership, a reproducible defect or a paper
claim that requires it. ROCm does not require owning AMD hardware today.

## Progress accounting and stop rules

Use a short evidence ledger with each **substantive compiler change**:

- **Program and oracle:** fixed source hash, input set, independent C
  behavior and declared target profile.
- **Before:** exact first failing stage, diagnostic, unmodified-program
  result, and whether any guest artifact was published.
- **Change:** one actual compiler/runtime capability or correctness defect,
  with a minimal red-first regression and the responsible component.
- **After:** recompile the original source, run the actual normative VM,
  compare bytes and termination, report steps/resources and negative cases.
- **Gate:** list specifically which acceptance item passed and which
  remains open. Never upgrade a gate from a collection of static
  simplification examples or an unfinished all-target test run.

**Work in progress limit:** prefer one core P2/P3/P4 blocker and one
independent verifier/tooling task at a time. Do not launch a new optional
native/accelerator/research subproject while the first real guest program
still fails. If blocked, name the owner and reproducer, avoid looping on
similar small examples, and continue the nearest independent dependency.

**Closure:** update the typed record's evidence, its governing contract and
the index only after acceptance and declared validation; move the record
to `docs/todo/completed/` using the repository's completion conventions.
The index shows open tasks, not fictional percent-complete estimates.
