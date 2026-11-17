# Malbolge TODO

## Delivery strategy — working compiler first (rephased 2026-11-16)

P0/P1 foundation work is historical and tracked in completed records. The
**unfinished roadmap now runs P2 through P10**. Phase labels are delivery
order, not artificial dates or estimates; typed acceptance and dependency
contracts remain authoritative. "Active" means implementation has started,
not that an optional task outranks the P2 critical path. Open-record
`lane` and `priority` agree with the current P2-P10 phase. Dated evidence
and completed records retain their historical lane labels.

**Critical path to a usable compiler:** P2 guest-executed mutable C and EOF
control -> P3 an explicitly supported deterministic-C/byte-stream surface ->
P4 independent translation verification -> **P5 CPU-only release**. Native
AOT/JIT, CUDA, DOOM, resident scaling, self-hosting, and papers do not block
this first usable delivery. CUDA is nevertheless required for P8 scaling
evidence on ambitious programs; CPU remains the reference for correctness.
The final cross-platform turnkey toolchain is P7, distinct from the P5 release.
The **CPU optimizer must remain CUDA-projectable**: common indexed candidate
batches, exact pruning/cost semantics, bounded state and one independent
verifier. A small CPU/CUDA parity experiment belongs before P6 representation
lock-in wherever hardware exists; P8 still owns live-device throughput and
large-program performance acceptance. Do not treat translating an arbitrary
CPU call graph to a CUDA kernel as an architecture plan.

**Start here:** compile the complete mutable EOF checksum, capture the first
real compiler failure, fix that capability, and rerun the *same* source on the
normative VM against independent native-C controls. Do not replace progress
with more fixed-length byte-identity examples. Once it executes, exercise
binary stream edge cases, verify supported lowerability and advance the P5
single-command acceptance. Never fake guest output or defer safety,
correctness, or source/guest verification.

**Phase exit is evidence-based.** A gate passes only with the exact source,
guest artifact, independent oracle, validation receipt and known limits under
its owning typed TODO. Optional tasks do not block a proven earlier release.
This `TODO.md` is the **sole roadmap**; typed task contracts hold the detailed
acceptance and the status of each experiment.

The optional hexagonal and human-search studies and the separate mathematical
paper are removed. The delivered source-bound diff generator is completed;
its DOOM integration and regression tests remain. Apollo and RV32I use the
ordinary C compiler, while CUDA is needed for later large-program scaling.

Only unfinished work appears below. Each entry keeps one title, one synthesis
paragraph and one link to its typed authority. Completed work stays under
`docs/todo/completed/`. Correctness and memory safety are never deferred.

## Finite acceptance and stopping rules for every open TODO

Every typed TODO has one **finite acceptance witness**. Before executing that
witness, freeze its exact source/profile/compiler/algorithm identity, named
fixtures and admissible grammar or ISA, deterministic seeds, resource class,
number of runs, and finite ceilings for applicable memory, search nodes,
compilation/guest steps, wall time, input bytes and artifact size. Record the
positive success predicate and negative/error expectations before running.
A test must terminate successfully, fail explicitly, or exhaust a specified
limit; a timeout is a **non-pass**, not a success or a reason to relax limits.
Unbounded C source sets, all possible binary streams, every imaginable host,
and infinite random testing are never hidden acceptance obligations.

**Work stops at the frozen evidence boundary.** A verified pass permits
completion only of that declared capability. A failed or unavailable run
receives an exact bounded failure/unavailable receipt, with the target still
open if its promised capability was not delivered. Conditional research can
finish with a documented reject/no-adoption result, but may not claim the
rejected technique works. Address newly found safety/correctness regressions
as owned defects; don't silently add more experiment families or fixtures to
the TODO just to keep it alive. Any deliberate expansion needs an explicit
change to the owning acceptance contract, not another open-ended iteration.

Later CUDA, AOT/JIT, DOOM, Apollo, RV32I and guest self-hosting trials must
report genuine target execution or an honest failed/untested result. A P4 CPU
artifact or P6 block catalogue must not require P8 CUDA hardware. Early P9
portable-C/compiled-compiler stages must not require the subsequent hosted
compiler's output. The final P10 paper is still one last task, based on a
finite outcome ledger of successes **and** failed/unavailable ambitious
experiments; their success is not a publication prerequisite.

## Delivery phase gates

- **P2 — Real guest C:** one complete C checksum program with mutable state,
  input-driven arithmetic and branching, and EOF loop must execute in the
  normative Malbolge VM. Start with the recorded automatic-declaration
  refusal, fix the actual compiler stage and compare with native C23 on
  NUL, high bytes and EOF; guest stdout cannot be host-simulated.
- **P3 — Supported deterministic C:** accepted tidy source always lowers;
  variable-length binary byte I/O, EOF and negative cases match native
  controls with explicit limitations and reproducible source locations.
- **P4 — Verified translation:** independent bounded source-to-guest
  checking, layout/self-modification proof obligations, repeatable build
  identities, and a GPU-projectable CPU candidate batch. Different valid
  algorithms may emit different hashes while preserving verified semantics.
- **P5 — First usable release:** a pinned Linux bootstrap and one stable
  compile command produce safe, verified Malbolge artifacts for two distinct
  real C programs; native oracles match on binary/EOF inputs. CPU only.
- **P6 — Scaling and reuse:** measure CPU search success, latency, memory,
  target size and verifier work. Add exact pruning, reusable blocks and
  resident compilation where evidence demonstrates benefit; no GPU required.
- **P7 — Native execution:** x86-64/AArch64 AOT plus guarded JIT remain
  equivalent to the interpreter on mutable-code and I/O tests. Final
  turnkey Windows/Linux packaging preserves deterministic CPU fallback.
- **P8 — CUDA and large programs:** **real NVIDIA CUDA acceleration is
  mandatory for the scaling goal**, independently of stochastic/PyTorch
  research. Compare >= 3 difficulty/batch points and >= 15 paired samples;
  a predeclared large class must demonstrate >= 1.25x end-to-end speedup
  including transfer and verification. Retain source/IR equivalence and CPU
  fallback. Test actual generated DOOM playability and the ordinary Apollo
  AGC C runner. PyTorch, stochastic search and symmetry remain optional.
- **P9 — Self-hosting and applications:** the Malbolge-hosted compiler must
  compile another supported C program with independent equivalence proof.
  Independently compile the ordinary RV32I C runner; prove its real guest
  ISA execution with bounded binary/state evidence. Retain historical
  demonstration and risk-ranked prepublication hardening here.
- **P10 — One final paper:** **the final open task** is a single
  reproducible systems paper covering the historical machine model,
  compiler/verification, CPU/CUDA algorithms, native tiers, DOOM,
  Apollo, RV32I, self-hosting, performance, caveats, bibliography and
  regeneration scripts. No separate mathematical or methodology paper.

**Current execution queue:** compile the *same* complete EOF-checksum C
source repeatedly, repair its first real failure, compare guest bytes and
termination with independently executed native C23 at `-O0` and `-O2`, and
record exact before/after source and artifact identities. Add seeded
boundary cases only after that full program works. Do not replace general
compiler progress with more literal `emit-N` examples.

**Scope control:** CPU is the correctness baseline, not an intentionally
unportable algorithm prototype. CUDA is required for P8 performance, not P5
correctness. Identical artifact bytes are promised for identical compiler,
algorithm, seed, backend policy and source/profile, not across different
valid CPU/GPU algorithms. Checkpoints may retain backend-specific opaque
continuation state; verified semantics remain portable. The accepted
source-bound diff generator remains completed and maintained for DOOM, with
no open generic expansion. Apollo and RV32I each
have only one C **guest compilation target**; their parity and whole-program
tests are separate host validation inputs, never special translators. Only
one final P10 paper is planned.

## P2 — Execute real stateful C

### TODO - Generalize guest byte-stream emission instead of emit-N fixtures

**First experiment, then verify.** Attempt one compact, demanding C program
through the real compiler and guest VM before extending literal byte-count
fixtures or a generated verification matrix.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/compiler/parametric-guest-byte-stream-emission.mdc](docs/todo/open/compiler/parametric-guest-byte-stream-emission.mdc)

### TODO - Ternary machine lowering

Lower typed C IR into a compact ternary virtual-machine representation suited
to Malbolge instead of translating C operations directly instruction by
instruction.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/compiler/ternary-machine-lowering.mdc](docs/todo/open/compiler/ternary-machine-lowering.mdc)

### TODO - Malbolge layout and encoding backend

Implement address-sensitive instruction layout, self-modification planning,
encoding, jumps, data placement, runtime linkage, and final `.malbolge`
emission.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/compiler/malbolge-layout-and-encoding-backend.mdc](docs/todo/open/compiler/malbolge-layout-and-encoding-backend.mdc)

### TODO - Resumable compilation progress sidecars

Persist an atomic JSON sidecar and compatible checkpoint for long-running
source, block, optimization, verification, and GPU jobs so elapsed time,
scientific provenance, current stage, and recoverable work survive process or
host failure without publishing an incomplete final `.malbolge` artifact.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/compiler/resumable-compilation-progress-sidecars.mdc](docs/todo/open/compiler/resumable-compilation-progress-sidecars.mdc)

## P3 — Complete supported C I/O semantics

### TODO - Deterministic binary byte-stream runtime

Prove generated programs can consume and emit arbitrary binary byte streams
without host-side format logic, creating the foundation for real deterministic
file transformers.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/applications/deterministic-binary-byte-stream-runtime.mdc](docs/todo/open/applications/deterministic-binary-byte-stream-runtime.mdc)

### TODO - tools/tidy lowerability contract

Partition checks into language, ABI, runtime, determinism, and resource
families and enforce the promise that every accepted translation unit is
supported by the compiler for its declared target profile.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/c/tools-tidy-lowerability-contract.mdc](docs/todo/open/c/tools-tidy-lowerability-contract.mdc)

### TODO - Translation validation

Verify compiled programs and blocks against source IR so optimizer and search
components may remain untrusted.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/verification/translation-validation.mdc](docs/todo/open/verification/translation-validation.mdc)

### TODO - C-level source mapping and debugging

Generate source maps from Malbolge addresses through lowered IR back to C
source locations.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/compiler/c-level-source-mapping-and-debugging.mdc](docs/todo/open/compiler/c-level-source-mapping-and-debugging.mdc)

## P4 — Verify, link, and inspect generated programs

### TODO - Deterministic CPU optimizer

Implement a correct CPU reference optimizer and search engine that works
without a GPU, even when much slower, and acts as the
declared-profile-conformant CPU baseline for accelerator implementations.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/accelerator/deterministic-cpu-optimizer.mdc](docs/todo/open/accelerator/deterministic-cpu-optimizer.mdc)

### TODO - Deterministic cross-backend artifact hashing

Require byte-identical outputs and hashes across backends for declared
deterministic workloads, including versioned example artifacts and compiler-
produced `.malbolge` artifacts where deterministic builds are promised.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/applications/deterministic-cross-backend-artifact-hashing.mdc](docs/todo/open/applications/deterministic-cross-backend-artifact-hashing.mdc)

### TODO - State-aware Malbolge linker

Build a linker that composes independently compiled Malbolge blocks while
resolving symbols, addresses, entry/exit machine-state contracts, positional
decode phase, post-instruction encryption phase, and self-modification
footprints.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/compiler/state-aware-malbolge-linker.mdc](docs/todo/open/compiler/state-aware-malbolge-linker.mdc)

### TODO - Proof-producing lowering

Investigate compiler outputs carrying compact witnesses or proof material for
local equivalence claims so final acceptance need not trust CUDA, PyTorch,
stochastic search, or superoptimization implementations.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/verification/proof-producing-lowering.mdc](docs/todo/open/verification/proof-producing-lowering.mdc)

### TODO - Versioned C and Malbolge example corpus

Publish intentionally selected project-owned examples under
`docs/technical/examples/` with paired `.c` and `.malbolge` artifacts.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/applications/versioned-c-and-malbolge-example-corpus.mdc](docs/todo/open/applications/versioned-c-and-malbolge-example-corpus.mdc)

### TODO - Annotated Malbolge source syntax and formatter

Add an explicit readable Malbolge source form that supports multiline layout,
full-line comments, deterministic automatic formatting, and source maps while
canonicalizing to exactly the same position-sensitive `.malbolge` bytes
consumed by the selected profile loader.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/tools/annotated-malbolge-source-syntax-and-formatter.mdc](docs/todo/open/tools/annotated-malbolge-source-syntax-and-formatter.mdc)

## P5 — Ship the CPU-first compiler

### TODO - CPU-first C-to-Malbolge release

Ship a reproducible CPU-only C-to-Malbolge command that compiles a useful
documented deterministic-C subset and proves real guest execution without
waiting for native acceleration, CUDA, DOOM, self-hosting or publication.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/compiler/cpu-first-c-to-malbolge-release.mdc](docs/todo/open/compiler/cpu-first-c-to-malbolge-release.mdc)

## P6 — Scale compilation with verified reuse

### TODO - Reusable block catalogue

Build a deterministic catalogue of verified arithmetic, branch, memory, calling
convention, and runtime blocks so common operations are solved once and reused
instead of synthesized from scratch for every compilation.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/accelerator/reusable-block-catalogue.mdc](docs/todo/open/accelerator/reusable-block-catalogue.mdc)

### TODO - Compact guest bytecode strategy

Evaluate a VM-inside-Malbolge strategy where large programs are represented as
compact bytecode interpreted by a reusable Malbolge runtime when that reduces
code-size explosion or compilation cost.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/compiler/compact-guest-bytecode-strategy.mdc](docs/todo/open/compiler/compact-guest-bytecode-strategy.mdc)

### TODO - Search pruning and state canonicalization

Develop exact pruning, dominance rules, partial-equivalence checks, canonical
states, admissible heuristics, and profile-aware constraints before relying on
raw hardware scale.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/accelerator/search-pruning-and-state-canonicalization.mdc](docs/todo/open/accelerator/search-pruning-and-state-canonicalization.mdc)

### TODO - Multi-objective compiler algorithm evaluation arena

Evaluate compiler and execution algorithms over scalable challenge families and
produce capacity curves and Pareto frontiers rather than one pass/fail score.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/applications/multi-objective-compiler-algorithm-evaluation-arena.mdc](docs/todo/open/applications/multi-objective-compiler-algorithm-evaluation-arena.mdc)

### TODO - Resident incremental compiler and WAL

Build a native long-lived compiler service that keeps parsed source, normalized
IR, dependency state, verified blocks, link plans, and reusable artifacts
resident in RAM.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/compiler/resident-incremental-compiler-and-wal.mdc](docs/todo/open/compiler/resident-incremental-compiler-and-wal.mdc)

### TODO - Machine-readable LLM and compiler challenge corpus

Expose challenge definitions, expected semantics, constraints, oracle behavior,
inputs, difficulty parameters, and evaluation results in a stable machine-
readable format so compiler researchers and LLM-based code/algorithm agents can
generate candidate passes or algorithms and submit them to the same verifier
and benchmark arena.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/applications/machine-readable-llm-and-compiler-challenge-corpus.mdc](docs/todo/open/applications/machine-readable-llm-and-compiler-challenge-corpus.mdc)

### TODO - Empirical Malbolge synthesis scaling law

Measure how verified synthesis cost changes with challenge difficulty,
self-modification footprint, layout coupling, target-state entropy, and
reusable catalogue coverage.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/research/empirical-malbolge-synthesis-scaling-law.mdc](docs/todo/open/research/empirical-malbolge-synthesis-scaling-law.mdc)

### TODO - Compilation latency performance budget

Establish measured compile-time budgets for cold compilation, warm resident
compilation, semantic invalidation, verified block reuse, relinking,
verification, and novel search.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/accelerator/compilation-latency-performance-budget.mdc](docs/todo/open/accelerator/compilation-latency-performance-budget.mdc)

## P7 — Native execution and turnkey packaging

### TODO - Tiered native execution engine

Build an AOT-first tiered execution engine over one exact VM contract.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/vm/tiered-native-execution-engine.mdc](docs/todo/open/vm/tiered-native-execution-engine.mdc)

### TODO - Native x86-64 and AArch64 backends

Implement native-code emitters for x86-64 and AArch64 behind one execution-IR
backend contract.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/vm/native-x86-64-and-aarch64-backends.mdc](docs/todo/open/vm/native-x86-64-and-aarch64-backends.mdc)

### TODO - Ahead-of-execution native translation

Make verified ahead-of-execution translation the primary native path.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/vm/ahead-of-execution-native-translation.mdc](docs/todo/open/vm/ahead-of-execution-native-translation.mdc)

### TODO - Guarded self-modification JIT

Use JIT compilation as a latency-bounded rescue tier for hot mutable code-state
versions that were not covered by verified AOT artifacts.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/vm/guarded-self-modification-jit.mdc](docs/todo/open/vm/guarded-self-modification-jit.mdc)

### TODO - Explicit native-tier execution controls

Expose independent `--no-jit` and `--no-aot` runtime controls plus an
`--interpreter-only` shorthand equivalent to disabling both native compilation
tiers and native-code cache reuse.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/vm/explicit-native-tier-execution-controls.mdc](docs/todo/open/vm/explicit-native-tier-execution-controls.mdc)

### TODO - Cross-platform native capability runners

Implement the version-1 host-capability contract for supported 64-bit Windows,
macOS, and Linux runners on x86-64 and AArch64.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/vm/cross-platform-native-capability-runners.mdc](docs/todo/open/vm/cross-platform-native-capability-runners.mdc)

### TODO - Turnkey C-to-Malbolge toolchain

Deliver the final supported workflow: bootstrap every public project dependency
except Jig, accept an explicitly named C source file, and emit one verified
`.malbolge` artifact through a single documented command on supported Windows
and Linux hosts.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/compiler/turnkey-c-to-malbolge-toolchain.mdc](docs/todo/open/compiler/turnkey-c-to-malbolge-toolchain.mdc)

## P8 — Accelerators and large-program validation

### TODO - Stochastic and guided search

Evaluate Monte Carlo, evolutionary, STOKE-like stochastic, learned, and hybrid
search with deterministic final verification and reproducible research seeds.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/accelerator/stochastic-and-guided-search.mdc](docs/todo/open/accelerator/stochastic-and-guided-search.mdc)

### TODO - CUDA superoptimizer

Implement GPU-parallel candidate synthesis, pruning, equivalence testing, cost
evaluation, and verified block stitching.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/accelerator/cuda-superoptimizer.mdc](docs/todo/open/accelerator/cuda-superoptimizer.mdc)

### TODO - DOOM playable generated-code performance

The source-level baseline is ready: the normalized single-player C tree and
canonical `doom.c` are reproducible, validate cleanly, and are interactively
playable through the native Windows/Linux debug boundary.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/applications/doom-playable-generated-code-performance.mdc](docs/todo/open/applications/doom-playable-generated-code-performance.mdc)

### TODO - Apollo 11 Luminary AGC in Malbolge

Execute the pinned Apollo 11 Luminary 099 software inside a project-authored
Block II AGC interpreter that is itself compiled to and executed as
`malbolge-2026`.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/applications/apollo-11-luminary-agc-malbolge-demonstration.mdc](docs/todo/open/applications/apollo-11-luminary-agc-malbolge-demonstration.mdc)

### TODO - Real-program benchmark suite

Benchmark hello world, byte copying, arithmetic kernels, hashing, parsers,
parametric challenge families, DOOM interoperability, and compiler workloads
across original C, modern C, Rust, CPU batch, JIT, and accelerator paths.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/applications/real-program-benchmark-suite.mdc](docs/todo/open/applications/real-program-benchmark-suite.mdc)

### TODO - PyTorch search orchestration

Use PyTorch for batched candidate/state representation, experiment
orchestration, and heuristic models where useful while purpose-built kernels
retain exact semantic execution where tensor operations are a poor fit.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/accelerator/pytorch-search-orchestration.mdc](docs/todo/open/accelerator/pytorch-search-orchestration.mdc)

### TODO - High-arity synthesis symmetry pruning

Extend exact tuple-quotient and stabilizer mathematics only when measured
synthesis traces show symmetry-related residual branching is eroding pruning
effectiveness.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/mathematics/high-arity-synthesis-symmetry-pruning.mdc](docs/todo/open/mathematics/high-arity-synthesis-symmetry-pruning.mdc)

## P9 — Self-hosting, machine runners and final evidence

### TODO - Portable c2malbolge implementation in C

Keep a path for the essential compiler algorithm to exist in the admitted C
profile without mandatory LLVM runtime, GPU, filesystem complexity, threads, or
other host-only capabilities.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/self_hosting/portable-c2malbolge-implementation-in-c.mdc](docs/todo/open/self_hosting/portable-c2malbolge-implementation-in-c.mdc)

### TODO - Compile c2malbolge.c to Malbolge

Compile the portable C compiler implementation with `c2malbolge` itself and run
the resulting `c2malbolge.malbolge` under the modern VM.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/self_hosting/compile-c2malbolge-c-to-malbolge.mdc](docs/todo/open/self_hosting/compile-c2malbolge-c-to-malbolge.mdc)

### TODO - Malbolge compiler compiles C to Malbolge

Use `c2malbolge.malbolge` to consume C source and emit a new working
`.malbolge` program, proving practical self-hosting of the translation path.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/self_hosting/malbolge-compiler-compiles-c-to-malbolge.mdc](docs/todo/open/self_hosting/malbolge-compiler-compiles-c-to-malbolge.mdc)

### TODO - Self-hosting equivalence proof

Compare native and Malbolge-hosted compiler outputs or normalized semantic
artifacts and prove self-hosting does not silently change compilation meaning.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/self_hosting/self-hosting-equivalence-proof.mdc](docs/todo/open/self_hosting/self-hosting-equivalence-proof.mdc)

### TODO - RV32I runner in Malbolge

Execute standard RV32I machine code inside a project-authored deterministic
RV32I interpreter that is itself compiled to and executed as `malbolge-2026`.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/applications/rv32i-malbolge-runner.mdc](docs/todo/open/applications/rv32i-malbolge-runner.mdc)

### TODO - Historical capability demonstration

Produce a reproducible demonstration from the 1998 interpreter through modern
tooling to substantial generated programs and self-hosting while keeping
historical attribution and compatibility evidence explicit.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/research/historical-capability-demonstration.mdc](docs/todo/open/research/historical-capability-demonstration.mdc)

### TODO - Prepublication hardening

Before publication-grade claims, execute one risk-ranked ledger of nonessential
rare inputs and research-evidence failure modes previously preventing delivery
of the real supported C-to-Malbolge path.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/research/prepublication-hardening.mdc](docs/todo/open/research/prepublication-hardening.mdc)

## P10 — Final comprehensive paper

### TODO - Final comprehensive Malbolge paper

Publish **one** reproducible, publication-grade paper containing the complete
verified Malbolge project: its historical machine model, deterministic C-to-
Malbolge compiler, semantics and translation verification, CPU and CUDA
optimization, native AOT/JIT execution, DOOM, Apollo AGC, RV32I and self-hosting
results, including real measurements, negative evidence and limitations.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/research/malbolge-machine-model-and-c-compilation-paper.mdc](docs/todo/open/research/malbolge-machine-model-and-c-compilation-paper.mdc)
