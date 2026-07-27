# Malbolge TODO

## Operating contract

This file contains unfinished work only. Every `### TODO` heading has one typed
record under `docs/todo/open/`. Completed work leaves this file only after its
implementation, specification, tests, and validation evidence are durable.

The repository is organized by responsibility, not implementation language.
Rust, C, Python, CUDA, PyTorch, and Malbolge may coexist inside one component
when they implement the same responsibility. Cargo is a build mechanism, not the
architecture; artificial Rust crates must not become repository boundaries.

The historical Ben Olmstead interpreter is immutable primary implementation
evidence, not semantic authority and not project-owned source. Project code is
MIT licensed; the original interpreter keeps its own public-domain notice and is
explicitly excluded from relicensing. Planning is intentionally front-loaded.
Before implementation begins, TODO work must be decomposed into typed TODOs with
real dependencies, bounded scope, provable acceptance criteria, and named
evidence. Once planning is stable, the next pass promotes settled decisions into
ADRs, specifications, technical docs, research records, and mathematical
contracts; implementation follows those artifacts rather than inventing
architecture opportunistically in source code.

A TODO is not complete because code exists. It is complete only when its
declared behavior, negative/boundary cases, relevant research or mathematical
claims, reproducibility obligations, and owning validation evidence are durable
enough for the TODO heading to disappear without losing unfinished intent.

## Project invariants

- Human-authored application code is C; generated target artifacts use the full
  `.malbolge` extension.
- `tools/tidy` defines the C surface the compiler promises to lower. Guest-C
  validation is manual/opt-in: explicitly named `.c` files are checked, and an
  explicitly named `doom` directory is the sole recursive directory shortcut.
  Rust tests develop and regress the profile; they are not the user-facing
  validator.
- The guest-C profile rejects semantics that cannot be made deterministic on the
  selected Malbolge target; it does not impose unrelated style restrictions or
  inherit arbitrary host-C limitations.
- A clean `tools/tidy` verdict must imply successful compilation for the
  declared target profile; otherwise the defect belongs to our tooling.
- `tools/tidy` constrains source determinism and lowerability; it does not
  make synthesis linear or otherwise prove a compile-time complexity class.
  Search, composition, linking, verification, and reuse costs remain empirical
  properties of their owning algorithms and must be measured separately.
- The host may execute the VM and provide fundamental byte input/output, but it
  may not secretly implement guest algorithms such as PDF writing, hashing,
  allocation, parsing, formatting, or application logic.
- The written 1998 specification defines the frozen `malbolge-1998`
  historical/conformance semantics. Modern historical-conformance backends are
  verified against that specification; Ben's interpreter supplies differential
  evidence only on the documented agreement subset.
- There is one evolving modern Malbolge product. `malbolge-1998` is its frozen
  historical/conformance profile, not the permanent default resource envelope;
  `legacy-ben` behavior is historical evidence, not a semantic product line.
- CPU execution is always available on the declared 64-bit host baseline:
  x86-64 and AArch64 are first-class architectures from the initial
  implementation slice.
- GPU acceleration is optional through a replaceable accelerator boundary. CUDA
  and ROCm are the first GPU runtime adapters; neither is a semantic dependency.
- Optimizers, CUDA kernels, PyTorch models, stochastic search, and other large
  heuristic components may be untrusted. Deterministic verification decides
  whether emitted code is accepted.
- Malbolge guest execution remains deterministic and sequential, including
  both `malbolge-1998` and current profiles unless a future reviewed language
  decision explicitly changes that semantic core. Performance work must not
  invent parallel guest behavior merely to make the compiler, VM, linker, or
  optimizer easier. Parallel host execution is legal only when observationally
  equivalent to the normative logical order.
- Self-modification and post-instruction encryption are fundamental guest
  semantics. Generated code must not become globally immutable merely to make
  linking, JIT, hot reload, or host parallelism easier. Immutable host caches are
  allowed only behind version guards that preserve guest-visible mutation.
- Scaling claims are hypotheses until measured. Report raw search, compositional
  reuse, verification, stitching, cache, and invalidation costs separately so an
  amortized fast path is never presented as the complexity of the full problem.
- Incremental compiler state, resident RAM images, and WAL records are rebuildable
  acceleration evidence rather than semantic authority. Equal byte counts, line
  positions, or textual hashes may be fast paths only after semantic dependency
  and self-modification contracts prove reuse safe.
- Mathematical claims used by compilation and optimization are represented in
  reviewable `.tex` specifications and connected to executable evidence.
- This repository is also a compiler-algorithm laboratory. Experimental IRs,
  lowering strategies, graph reductions, superoptimizers, search algorithms,
  code generators, and execution techniques must be swappable and benchmarkable
  without replacing the trusted semantic baseline.
- Genuine algorithm research uses a semantic mirror: academic evidence under
  `docs/research/algorithms/<id>/` and executable experiments under
  `algorithms/<id>/`. Product algorithms such as DOOM interoperability rewrites
  remain with their owning responsibility and do not require artificial papers.
- Generated experiment artifacts are local to the owning algorithm under
  `algorithms/<id>/out/`; engineering transformations use an analogous local
  `out/`, such as `interop/algorithms/quality/out/doom_fixed/`. Every `out/` is reproducible
  and Git ignored rather than becoming an opaque evidence dump.
- Research claims distinguish hypotheses, correctness evidence, performance
  evidence, negative/null results, and threats to validity. Primary or
  authoritative sources are preferred and cited through the research
  bibliography.
- Native execution acceleration is optional and explicitly controllable. Users
  must be able to disable AOT, JIT, or both and execute through the interpreter
  alone for semantic, research, and benchmark comparisons.
- Accelerator hardware and optimization/search algorithms are independent ports:
  CUDA is one hardware adapter, while stochastic, enumerative, learned, and
  other algorithms are separately selectable strategies.
- The long-term boss fight is self-hosting: a C-to-Malbolge compiler compiled
  into Malbolge and then used to compile another C program into Malbolge.

## Foundation and governance

### TODO - Repository responsibility scaffold

Create the responsibility-oriented topology, mixing implementation languages
inside components and retaining only the minimal root `src/` surface required by
Cargo composition.

### TODO - Compiler algorithm experimentation platform

Make the repository a reproducible laboratory for compiler research, not merely
an implementation of one fixed C-to-Malbolge pipeline. Experimental algorithms
use the `docs/research/algorithms/<id>/` and `algorithms/<id>/` mirror, while
ordinary product algorithms remain inside their owning responsibility. Provide
stable experiment boundaries for alternate IRs, lowering passes, graph
simplifiers, superoptimizers, search strategies, code generators, execution
tiers, and cost models. Experiments must be selectable without editing trusted
semantic code, record exact configuration/seeds/inputs, compare against common
correctness oracles, and emit reproducible evidence so a new algorithm can be
accepted, rejected, or retired without becoming architecture by accident.
### TODO - Jig repository governance

Integrate the evolving Jig validator as repository-local tooling, preserve its
fail-closed rules, and configure only genuine project-specific differences
without weakening unrelated linter contracts.

### TODO - Canonical Malbolge target profile

Define `malbolge.json` as the single target-profile authority consumed by the
VM, compiler, tidy plugin, verifier, optimizer, runtime, and accelerators. Schema
v2 now preserves frozen `malbolge-1998`, retains `malbolge-2026.1`, and selects
the scalable 14-trit `malbolge-2026.2` profile as current; universal consumer
adoption remains open. Evolution is versioned rather than branded "extended".

### TODO - Historical interpreter legal boundary

Keep Ben Olmstead's original interpreter under `tools/malbolge/`, retain its
original notice, document its public-domain status, and state that the
repository MIT license does not relicense that specific file.

### TODO - Historical Malbolge semantics specification

Specify the original 1998 machine: 59,049 ten-trit words, registers, decoding,
crazy operation, rotation, self-encryption, input/output, wraparound, loading,
and termination behavior.

### TODO - Historical undefined-behavior catalogue

Catalogue one-instruction loading, invalid executable cells, platform-dependent
newline behavior, source validation quirks, and other accidental or undefined C
behavior separately from intended Malbolge semantics.

### TODO - Reference interpreter sanitizer harness

Build the historical interpreter under AddressSanitizer and
UndefinedBehaviorSanitizer where supported, preserve failing fixtures, and use
the evidence to distinguish reference semantics from C implementation defects
without editing Ben's source.

## Documentation authority and promotion

### TODO - Documentation authority taxonomy

Define the exact documentation ownership model before the planning corpus is
promoted into durable records. `docs/technical/`, `docs/research/`,
`docs/legal/`, and `docs/bibliography/` are the four documentation authority
families, and each family owns its own `adr/` directory for decisions local to
that family. A global `docs/adr/` is forbidden so unrelated decisions cannot
collapse into an STM-style ADR monolith. ADRs contain bounded decisions and
tradeoffs; technical specifications, research findings, legal analysis, and
bibliography records remain ordinary documentation under their owning family.
`integrations/cspell/` remains the editorial support surface used by CSpell and
is not a fifth authority family. Jig will eventually validate this topology;
Malbolge must not grow a parallel documentation linter to enforce it.

### TODO - Repository bibliography taxonomy and citation provenance

Build `docs/bibliography/` as the repository-wide, non-governing source and
provenance authority, independent from `docs/research/`. Adopt a SHAR-style
subject taxonomy for programming languages, compilers/runtimes, Malbolge and
esolangs, superoptimization/program synthesis, verification/formal methods,
accelerator computing, protocols/standards, validation tooling, research
methodology, AI/code generation, and relevant organizations/projects. Populate a
baseline sufficient to support the first technical, research, and legal records,
preferring primary or authoritative sources and retaining stable identifiers,
versions, publication metadata, retrieval dates, provenance, and explicit
uncertainty. `docs/bibliography/adr/` owns only durable decisions about how
bibliography itself is organized or interpreted; source records never become
repository policy merely because they are cited.

### TODO - Planning corpus promotion to durable documentation

Once ROADMAP and typed TODO coverage are stable, classify every settled planning
choice into its durable owning surface instead of copying TODO prose wholesale.
Create bounded ADRs for decisions, technical specifications/contracts for
repository behavior, research records and `.tex` artifacts for investigations,
legal records for dated source-use/interoperability analysis, and bibliography
records for external evidence. Populate each TODO's `contract` and `adr_paths`
with real authorities as those records are created. Proposed or unresolved
choices remain visibly proposed; implementation details remain in their owning
technical documents. No global catch-all ADR, duplicate authority, or
chat-history archive is created during promotion.

### TODO - Documentation readiness and implementation gate

Establish the documentation baseline that must pass before normal product
implementation history begins. The gate requires the four documentation families
and their local ADR roots, a usable repository bibliography baseline, all
existing TODO decisions routed to an owning durable document or an explicitly
unresolved record, valid local links, and no accidental global `docs/adr/`.
`integrations/cspell/` remains intact as editorial support. Scaffolding,
configuration, and concurrent Jig development may exist before this gate, but
new product implementation work starts only after the documentation baseline is
reviewable. Documentation and planning commits may precede this gate. Passing it
authorizes product implementation commits; subsequent implementation proceeds
TODO by TODO with its governing documents already available.

## Research methodology and experiment infrastructure

### TODO - Academic research methodology and evidence model

Define the repository-wide scientific method for compiler research: falsifiable
questions, preregistered hypotheses where practical, correctness/performance
separation, negative and null result retention, threats to validity,
replication, source quality, experiment provenance, and criteria for claiming
that evidence supports or rejects a technique.

### TODO - Algorithm research mirror and local output contract

Standardize the semantic mirror between `docs/research/algorithms/<id>/` and
`algorithms/<id>/`, including stable algorithm identity, optional
`math/algorithms/<id>.tex`, implementation/test layout, experiment
configuration, and Git-ignored local `out/`. Define the explicit exception for
ordinary product algorithms such as DOOM interoperability transformations, which
require engineering evidence but not artificial academic capsules.

### TODO - Reproducible experiment identity and manifest

Define a versioned experiment manifest that records algorithm identity, exact
implementation/configuration, target profile, workload hashes, seeds, stopping
rules, host/accelerator identity, memory budget, compiler/tool versions, and
output location so any reported experiment can be reconstructed without editing
source constants.

### TODO - Benchmark and statistical evidence protocol

Define fair-comparison workloads, warmup, repetitions, confidence/dispersion
reporting, outlier policy, randomized-search treatment, time/quality tradeoffs,
resource normalization, and raw-sample retention rules. Performance claims must
identify uncertainty and may never substitute for semantic verification.

### TODO - Algorithm promotion rejection and retirement lifecycle

Define how an experimental algorithm becomes eligible for a production compiler
or execution path, how negative results are retained, how superseded algorithms
are retired without deleting scientific history, and how correctness,
reproducibility, complexity, portability, and measured benefit gate promotion.

### TODO - Publication-grade paper pipeline

Create a reproducible LaTeX paper pipeline under `docs/research/papers/` capable
of turning mature investigations into publication-quality papers with canonical
bibliography, equations, figures, tables, experiment provenance, limitations,
and regenerated results without making publication a prerequisite for ordinary
engineering work.
## Virtual machine implementations

### TODO - Safe Rust Malbolge VM

Implement the primary modern VM in safe Rust with explicit errors, deterministic
state transitions, tracing hooks, and instruction-level conformance with the
normative 1998 specification.

### TODO - Specification and legacy-interpreter execution modes

Make specification-conformant execution the default and only normal Malbolge
semantics. Add an explicit `legacy-ben` mode only for archaeology, differential
diagnosis, and historical-corpus study; it never becomes a compiler target or
verification authority.

### TODO - Independent pure C Malbolge VM

Implement a small auditable pure-C VM independently from the stabilized
specification rather than mechanically translating the Rust implementation.

### TODO - CPU VM table optimization

Optimize scalar execution with precomputed rotate tables, position-dependent
decode tables, efficient crazy-operation decomposition, cheap pointer updates,
and benchmarked micro-optimizations without semantic drift.

### TODO - Tiered native execution engine

Build a tiered execution engine instead of choosing between interpretation, AOT,
and JIT. Decode Malbolge into a compact execution IR, simplify that IR through
verified state-graph mathematics, compile demonstrably stable regions to native
machine code before execution, specialize hot or mutation-sensitive regions at
runtime, and deoptimize safely to the interpreter whenever a code-version guard
or speculative assumption fails. The normative VM contract remains the semantic
baseline; native tiers are accelerators of identical observable behavior.

### TODO - Ahead-of-execution native translation

Translate reachable stable Malbolge regions into native code in memory before
guest execution begins. Use a compact portable micro-IR between Malbolge decode
and architecture-specific code generation, cache verified compiled regions by
program identity, target profile, architecture, and code-state assumptions, and
fall back to ordinary VM execution for regions that cannot yet be proven stable.

### TODO - Guarded self-modification JIT

Compile hot mutable regions after observing their concrete code-state versions.
Attach explicit guards to assumptions about self-modifying cells, code/data
aliasing, addressing, and control flow. A failed guard deoptimizes to the
interpreter, updates the observed state graph, and may create a new
specialization without changing observable Malbolge behavior.

### TODO - Native x86-64 and AArch64 backends

Implement native-code emitters for x86-64 and AArch64 behind one execution-IR
backend contract. Architecture-specific register allocation, instruction
selection, calling conventions, executable-memory handling, instruction-cache
synchronization, and hardening remain adapters rather than VM semantics.

### TODO - Deterministic logical concurrency

Define deterministic logical tasks and joins while preserving sequential guest
semantics. The safe Rust execution layer now orders structurally independent
owned VM tasks by explicit logical ID, rejects duplicate identity, and joins
committed outputs only in that order; 1/2/8-worker fixtures match the sequential
full-state/artifact baseline. Logical-layer performance evidence remains open.

### TODO - Batch VM execution

Execute many independent programs or inputs efficiently on CPU and accelerator
backends for fuzzing, exhaustive verification, synthesis, and search workloads.
The CPU baseline now has deterministic sequential and explicit host-parallel
execution plus retained worker-scaling evidence; future accelerator adapters
remain open.

### TODO - Explicit native-tier execution controls

Expose independent `--no-jit` and `--no-aot` runtime controls plus an
`--interpreter-only` shorthand equivalent to disabling both native compilation
tiers and native-code cache reuse. Default execution may use AOT, JIT, graph
optimization, and interpreter fallback, but interpreter-only mode must execute
the Malbolge machine directly without generating host machine code. Use these
modes for differential correctness checks and honest measurements of pure VM,
AOT-only, JIT-only, and fully tiered execution.
## Malbolge evolution and compatibility

### TODO - Scalable Malbolge memory model

Remove the practical 59,049-word ceiling from current Malbolge while retaining
`malbolge-1998` as exact historical conformance. Schema v2 selects the 14-trit
`malbolge-2026.2` geometry with 4,782,969 directly addressed words, and the new
safe-Rust `ProfileMachine` executes that profile explicitly while the classic
facade remains ten-trit. Compiler, tracing, batch/logical, native, and accelerator
consumers still need profile-driven adoption rather than silent fallback.

### TODO - Historical-interpreter fallback capsule

Define a versioned `.malbolge` capsule recognized by modern runtimes while the
1998 loader sees only a safe classic fallback. Version one now uses a fixed
`!`-emitting historical sentinel plus a space/tab `MALBCAP1` sideband carrying
profile ID/fingerprint, payload, lengths, flags, and deterministic checksum.
Current scalable payloads execute through `ProfileMachine`; the classic facade
still rejects them before its ten-trit loader, so runtime choice remains explicit.

### TODO - Required-profile diagnostics

Emit deterministic diagnostics naming required profile/features/capacity and
runtime capability. The safe Rust facade now rejects `malbolge-2026.2` before
loading with exact 14-trit/4,782,969-word requirements and reports classic
capacity overflow as a 59,049-word historical-profile ceiling; propagation into
compiler artifacts and other runtime consumers remains open.

### TODO - Custom target profile identity

Allow user-supplied target profiles with canonical hashing and explicit artifact
identity. `malbolge-profile-v1` fingerprints and the verification CLI now detect
external configuration mismatch; compiler/container propagation and any
profile-dependent encoding research remain open without claiming cryptographic
resistance to reverse engineering.

### TODO - Hexagonal authoring-layout experiment

Research an optional graph or hexagonal authoring representation that lowers to
ordinary linear `.malbolge` output and therefore does not require a special
execution engine for compatible programs.

## Deterministic C surface

### TODO - Deterministic C-to-Malbolge ABI

Specify fixed integer widths, signed behavior, endianness, pointers, alignment,
object representation, stack rules, recursion policy, I/O, and a fail-closed
policy for undefined or target-dependent C behavior.

### TODO - tools/tidy clang-tidy plugin

Build `tools/tidy/` as an out-of-tree clang-tidy plugin compiled against the
pinned LLVM version. Add Malbolge checks without forking Clang or weakening the
existing clang-tidy baseline.

### TODO - tools/tidy lowerability contract

Partition checks into language, ABI, runtime, determinism, and resource families
and enforce the promise that every accepted translation unit is supported by the
compiler for its declared target profile.

### TODO - Supported libc contract

Define the guest C library surface: fixed-width integers, memory primitives,
byte streams, strings, allocation, formatting, and later higher-level routines
without hidden host shortcuts.

### TODO - Guest runtime and allocator

Implement startup, calling convention, frames, allocation, streams, integer
helpers, strings, scheduling primitives, and other runtime facilities as code
that ultimately executes under Malbolge semantics.

## Compiler

### TODO - Clang C frontend integration

Use Clang as the C parser, type system, constant evaluator, source-location
provider, and AST frontend instead of building another C parser.

### TODO - Typed compiler IR

Define a small deterministic IR representing control flow, arithmetic, memory,
calls, byte I/O, target-profile requirements, and proof obligations without
inheriting unnecessary LLVM complexity.

### TODO - Ternary machine lowering

Lower typed C IR into a compact ternary virtual-machine representation suited to
Malbolge instead of translating C operations directly instruction by
instruction.

### TODO - Malbolge layout and encoding backend

Implement address-sensitive instruction layout, self-modification planning,
encoding, jumps, data placement, runtime linkage, and final `.malbolge`
emission.

### TODO - State-aware Malbolge linker

Build a linker that composes independently compiled Malbolge blocks while
resolving symbols, addresses, entry/exit machine-state contracts, positional
decode phase, post-instruction encryption phase, and self-modification footprints.
Relocation is valid only when independent verification proves that stitching the
blocks preserves the same guest-visible transition semantics.

### TODO - Compact guest bytecode strategy

Evaluate a VM-inside-Malbolge strategy where large programs are represented as
compact bytecode interpreted by a reusable Malbolge runtime when that reduces
code-size explosion or compilation cost.

### TODO - C-level source mapping and debugging

Generate source maps from Malbolge addresses through lowered IR back to C source
locations. Expose debugging at the C level; keep low-level VM tracing primarily
for implementation and verification.

### TODO - Resident incremental compiler and WAL

Build a native long-lived compiler service that keeps parsed source, normalized
IR, dependency state, verified block identities, layout evidence, and reusable
artifacts resident in RAM. Persist a deterministic write-ahead log sufficient to
recover or discard cache state after interruption. Recompile and relink only the
semantic invalidation closure of an edit; fixed-width or same-position textual
matches may accelerate lookup but never replace AST/IR dependency evidence.

## Verification and static analysis

### TODO - Differential VM verification

Run specification fixtures through the Rust VM, independent C VM, and
accelerator VM and compare output, termination, state, mutation, and instruction
traces. Run the original C interpreter only on the documented agreement subset
as historical differential evidence.

### TODO - Property, fuzz, and exhaustive testing

Use property testing, fuzzing, sanitizers, regression corpora, and exhaustive
finite-domain verification for small functions and VM primitives such as rotate
and crazy operations.

### TODO - Translation validation

Verify compiled programs and blocks against source IR so optimizer and search
components may remain untrusted. Prefer a small deterministic verifier over
trusting a large heuristic backend.

### TODO - Proof-producing lowering

Investigate compiler outputs carrying compact witnesses or proof material for
local equivalence claims so final acceptance need not trust CUDA, PyTorch,
stochastic search, or superoptimization implementations.

### TODO - Emitted Malbolge static analyzer

Analyze generated Malbolge for lexical and address validity, self-modification,
control-flow reachability, code/data aliasing, wraparound, dataflow, invalid
executable cells, and input-dependent cycles or hangs.

### TODO - Exact and diagnostic cycle detection

Provide optional repeated-state detection using collision-safe confirmation for
exact results and clearly label probabilistic hash-only diagnostics.

## Mathematical specification

### TODO - LaTeX mathematical specification framework

Create a `math/` surface of `.tex` specifications for ternary words,
rotation, crazy operation, decoding, self-modification, memory models, compiler
lowering, equivalence relations, and search cost functions.

### TODO - Machine-checked mathematical correspondence

Connect mathematical specifications to executable tests or proof tooling so the
`.tex` files are reviewable mathematics rather than decorative documentation.

### TODO - Malbolge-specific optimization mathematics

Derive algebraic decompositions, lookup-table factorizations, state reductions,
canonical forms, and lower bounds that reduce synthesis search before brute
force or stochastic optimization begins.
### TODO - Self-modification state-graph optimizer

Model executable Malbolge regions as versioned state-transition graphs whose
nodes capture only semantically relevant code/data state. Derive mathematically
verified reductions that collapse equivalent mutation histories, eliminate
redundant encryption/update work, hoist invariant crazy/rotate computations, and
identify regions safe for direct native execution. Express the equivalence and
reduction rules in `.tex` and validate each admitted rewrite against executable
VM evidence.

## Optimization and accelerator architecture

### TODO - Deterministic CPU optimizer

Implement a correct CPU reference optimizer and search engine that works without
a GPU, even when much slower, and acts as the specification-conformant CPU
baseline on both x86-64 and AArch64 hosts for accelerator implementations.

### TODO - Replaceable accelerator boundary

Define a hardware-neutral interface for candidate evaluation, batch VM
execution, search, and verification. Compiler and verifier code must not depend
directly on CUDA APIs.

### TODO - Configurable accelerator algorithm adapters

Separate optimization/search strategy from accelerator hardware. Define common
algorithm ports for enumerative, stochastic, Monte Carlo, evolutionary, learned,
hybrid, pruning, and future strategies, and let CPU, CUDA, ROCm, or later
hardware adapters provide execution capacity for those strategies. Select
algorithms and hardware through deterministic configuration with optional CLI
overrides, record the exact combination in benchmark evidence, and permit
side-by-side comparison without recompiling or modifying compiler semantics.
### TODO - CUDA exact VM adapter

Implement the first GPU adapter with exact discrete Malbolge semantics and
massively parallel independent VM execution for candidate evaluation and test
batches.

### TODO - CUDA superoptimizer

Implement GPU-parallel candidate synthesis, pruning, equivalence testing, cost
evaluation, and verified block stitching.

### TODO - PyTorch search orchestration

Use PyTorch for batched candidate/state representation, experiment
orchestration, and heuristic models where useful while purpose-built kernels
retain exact semantic execution where tensor operations are a poor fit.

### TODO - Adaptive accelerator resource budgeting

Discover available memory and compute resources at runtime and choose batch
size, state layout, caches, and search breadth accordingly. Tiny devices around
128 MiB must remain usable; devices around 80 GiB should turn additional
resources into measured throughput instead of hitting fixed artificial limits.

### TODO - Compilation latency performance budget

Establish measured compile-time budgets for cold compilation, warm resident
compilation, incremental invalidation, verified block reuse, relinking, and novel
search. Treat "seconds, not hours" as an engineering target rather than a
promise, and never report a cached or compositional fast path as the complexity
of raw synthesis.

### TODO - ROCm accelerator adapter

Add a ROCm accelerator implementation behind the same hardware-neutral port
without changing compiler semantics, target profiles, or verifier contracts.

### TODO - Reusable block catalogue

Build a deterministic catalogue of verified arithmetic, branch, memory, calling
convention, and runtime blocks so common operations are solved once and reused
instead of synthesized from scratch for every compilation. Every reusable block
must carry entry/exit state, layout assumptions, mutation footprint, target
profile, cost, provenance, and verifier evidence required for safe linking.

### TODO - Stochastic and guided search

Evaluate Monte Carlo, evolutionary, STOKE-like stochastic, learned, and hybrid
search with deterministic final verification and reproducible research seeds.

### TODO - Search pruning and state canonicalization

Develop exact pruning, dominance rules, partial-equivalence checks, canonical
states, admissible heuristics, and profile-aware constraints before relying on
raw hardware scale.

## Deterministic real programs

### TODO - Deterministic binary byte-stream runtime

Prove generated programs can consume and emit arbitrary binary byte streams
without host-side format logic, creating the foundation for real deterministic
file transformers.

### TODO - Parametric compiler challenge generator

Build deterministic workload generators whose difficulty can grow continuously
instead of saturating at one application-specific threshold. Generate families
covering arithmetic and ternary transforms, expression DAGs, control flow,
function calls, memory pressure, pointer/alias patterns admitted by the C
profile, streaming state machines, graph problems, layout pressure, Malbolge
self-modification, block synthesis, and whole-program compositions with known
semantic oracles. Every instance is identified by family, version, seed, target
profile, and explicit difficulty parameters so two algorithms can be compared on
exactly the same problem rather than on vaguely similar examples.

### TODO - Multi-objective compiler algorithm evaluation arena

Evaluate compiler and execution algorithms over scalable challenge families and
produce capacity curves and Pareto frontiers rather than one pass/fail score.
Measure time-to-verified-solution, generated-code size, runtime instructions,
peak memory/VRAM, verifier cost, energy or device utilization when available,
success probability for stochastic methods, and maximum solved difficulty under
fixed budgets. Preserve raw evidence so an algorithm that is faster at easy
instances but scales worse than another remains distinguishable instead of both
appearing equally "perfect" after crossing an arbitrary threshold.

### TODO - Machine-readable LLM and compiler challenge corpus

Expose challenge definitions, expected semantics, constraints, oracle behavior,
inputs, difficulty parameters, and evaluation results in a stable
machine-readable format so compiler researchers and LLM-based code/algorithm
agents can generate candidate passes or algorithms and submit them to the same
verifier and benchmark arena. The corpus must test generated ideas without
granting an LLM authority over correctness and must support deterministic replay
of every admitted result.

### TODO - Versioned C and Malbolge example corpus

Publish intentionally selected project-owned examples under
`docs/technical/examples/` with paired `.c` and `.malbolge` artifacts. Include
small teaching examples plus representative fixed instances drawn from the
parametric challenge corpus. Each pair identifies challenge/source identity,
target profile, compiler identity, input/output contract, reproducible build
command, expected behavior, and verification evidence. Documentation examples
are versioned deliberately; normal benchmark outputs remain local under their
owning `out/` directories.

### TODO - DOOM quality and modernization pass

Consume a user-supplied lawful DOOM source tree from the ignored root `doom/`
and use `interop/algorithms/quality/main.rs` to produce a deterministic normalized
source tree under `interop/algorithms/quality/out/doom_fixed/`. Repair repeated
`tools/tidy` diagnostic families with reusable AST transformations, replace
unavailable legacy platform integration through explicit video, input, timing,
audio, and game-data adapters, support scalable modern resolutions and measured
frame-rate targets, and remove stale comments without discarding required legal
provenance. Differential native tests follow every behavior-affecting rewrite.
The user-owned input tree is never modified and remains external to the repo.

### TODO - User-supplied DOOM source interoperability generator

Use `interop/algorithms/amalgamate/main.rs` only after the quality pass has produced
the normalized source tree. Resolve translation-unit boundaries, internal-linkage
collisions, preprocessing environments, includes, declarations, and provenance
through pinned Clang, then emit one deterministic
`interop/algorithms/amalgamate/out/doom_amalgamated.c`. Differentially compare the normalized
multi-file build with the amalgamated build before copying the accepted artifact
byte-for-byte to `tests/applications/doom/out/doom.c`. Plain textual
concatenation and source-specific hand patches are not accepted algorithms.
### TODO - DOOM playable generated-code performance

Optimize lowering, block selection, guest runtime, VM execution, JIT paths, and
accelerator-assisted compilation until the user-supplied DOOM interoperability
pipeline produces a `.malbolge` build that is genuinely interactive and playable
under the modern runtime. Measure compile latency, frame pacing, input latency,
VM instructions per game tick, memory footprint, and generated-code size rather
than declaring success merely because the program eventually runs. Preserve the
same game semantics while optimizing; performance-specific substitutions require
explicit equivalence evidence.
### TODO - Real-program benchmark suite

Benchmark hello world, byte copying, arithmetic kernels, hashing, parsers,
parametric challenge families, DOOM interoperability, and compiler workloads
across original C, modern C, Rust, CPU batch, JIT, and accelerator paths.

### TODO - Deterministic cross-backend artifact hashing

Require byte-identical outputs and hashes across backends for declared
deterministic workloads, including versioned example artifacts and
compiler-produced `.malbolge` artifacts where deterministic builds are promised.

## Self-hosting

### TODO - Portable c2malbolge implementation in C

Keep a path for the essential compiler algorithm to exist in the admitted C
profile without mandatory LLVM runtime, GPU, filesystem complexity, threads, or
other host-only capabilities. Native accelerators remain optional speedups.

### TODO - Compile c2malbolge.c to Malbolge

Compile the portable C compiler implementation with `c2malbolge` itself and run
the resulting `c2malbolge.malbolge` under the modern VM.

### TODO - Malbolge compiler compiles C to Malbolge

Use `c2malbolge.malbolge` to consume C source and emit a new working `.malbolge`
program, proving practical self-hosting of the translation path.

### TODO - Self-hosting equivalence proof

Compare native and Malbolge-hosted compiler outputs or normalized semantic
artifacts and prove self-hosting does not silently change compilation meaning.

## Research and historical demonstration

### TODO - Reuse SHAR legal and interoperability corpus

Adapt the project-owned MIT legal, interoperability, licensing, provenance, and
publication-boundary documentation from `C:/Repos/mit/shar` into
Malbolge-specific contracts. Remove SHAR-specific assumptions, preserve the
common legal reasoning that applies here, and add DOOM-source, generated-code,
public-domain-oracle, compiler-output, and user-supplied-input boundaries
required by this repository.
### TODO - Superoptimization research program

Ask which search strategies find smaller or faster verified Malbolge blocks
under fixed time and evaluation budgets. Build a rigorous research track
covering stochastic superoptimization, enumerative synthesis, equality
saturation where applicable, Monte Carlo and evolutionary search, program-state
canonicalization, pruning, translation validation, learned guidance, GPU batch
evaluation, and prior Malbolge code generation techniques. Maintain a
source-backed bibliography and convert useful results into explicit compiler
hypotheses, benchmarks, and mathematical `.tex` work rather than folklore.

### TODO - Empirical Malbolge synthesis scaling law

Measure how verified synthesis cost grows with block difficulty, target-state
entropy, self-modification footprint, layout coupling, and available reusable
catalogue coverage. Compare blind search, structured search, compositional reuse,
learned guidance, and accelerator-backed evaluation under identical budgets.
Fit competing empirical models rather than assuming exponential, linear, or
sublinear behavior, and report where each model ceases to explain observations.

### TODO - Human-scale Malbolge search study

Create a bounded experiment illustrating why manual Malbolge synthesis is
cognitively impractical even for very capable humans, separating attention and
energy limits from machine-search throughput without bogus IQ or neuroscience
claims.

### TODO - Historical capability demonstration

Produce a reproducible demonstration from the 1998 interpreter through modern
tooling to substantial generated programs and self-hosting while keeping
historical attribution and compatibility evidence explicit.
