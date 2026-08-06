# Malbolge TODO

Only unfinished work appears here. P0 is the highest-priority horizon and P4
is the latest. Within each P section, work is ordered heuristically by
dependency readiness, active implementation, how many open tasks it unlocks,
and responsibility. Those ranking details remain implicit rather than repeated
in every entry.

Full metadata, acceptance criteria, dependencies, evidence, and migrated
planning notes remain in the typed records under `docs/todo/open/`. Completed
records remain under `docs/todo/completed/`.

**Canonical TODO format:** one `### TODO - ...` title, one synthesis paragraph
of one to four sentences, then one direct Markdown link to the complete typed
record. No per-item field labels belong in this index.

## P0 — Authority and governance

### TODO - Repository responsibility scaffold

Create the responsibility-oriented topology, mixing implementation languages
inside components and retaining only the minimal root `src/` surface required by
Cargo composition.

[docs/todo/open/foundation/repository-responsibility-scaffold.mdc](docs/todo/open/foundation/repository-responsibility-scaffold.mdc)

### TODO - Reuse SHAR legal and interoperability corpus

Adapt the project-owned MIT legal, interoperability, licensing, provenance, and
publication-boundary documentation from `C:/Repos/mit/shar` into
Malbolge-specific contracts.

[docs/todo/open/research/reuse-shar-legal-and-interoperability-corpus.mdc](docs/todo/open/research/reuse-shar-legal-and-interoperability-corpus.mdc)

### TODO - Jig repository governance

Integrate the evolving Jig validator as repository-local tooling, preserve its
fail-closed rules, and configure only genuine project-specific differences
without weakening unrelated linter contracts.

[docs/todo/open/foundation/jig-repository-governance.mdc](docs/todo/open/foundation/jig-repository-governance.mdc)

### TODO - Canonical Malbolge target profile

Define `malbolge.json` as the single target-profile authority consumed by the
VM, compiler, tidy plugin, verifier, optimizer, runtime, and accelerators.

[docs/todo/open/foundation/canonical-malbolge-target-profile.mdc](docs/todo/open/foundation/canonical-malbolge-target-profile.mdc)

### TODO - Planning corpus promotion to durable documentation

Once typed TODO coverage is stable, classify every settled planning choice into
its durable owning surface instead of copying TODO prose wholesale.

[docs/todo/open/documentation/planning-corpus-promotion-to-durable-documentation.mdc](docs/todo/open/documentation/planning-corpus-promotion-to-durable-documentation.mdc)

### TODO - Documentation readiness and implementation gate

Establish the documentation baseline that must pass before normal product
implementation history begins.

[docs/todo/open/documentation/documentation-readiness-and-implementation-gate.mdc](docs/todo/open/documentation/documentation-readiness-and-implementation-gate.mdc)

## P1 — Semantic and language foundations

### TODO - Safe Rust Malbolge VM

Implement the primary modern VM in safe Rust with explicit errors, deterministic
state transitions, tracing hooks, and instruction-level conformance with
defined, reproducible original-interpreter behavior.

[docs/todo/open/vm/safe-rust-malbolge-vm.mdc](docs/todo/open/vm/safe-rust-malbolge-vm.mdc)

### TODO - LaTeX mathematical specification framework

Create a `math/` surface of `.tex` specifications for ternary words, rotation,
crazy operation, decoding, self-modification, memory models, compiler lowering,
equivalence relations, and search cost functions.

[docs/todo/open/mathematics/latex-mathematical-specification-framework.mdc](docs/todo/open/mathematics/latex-mathematical-specification-framework.mdc)

### TODO - Independent pure C Malbolge VM

Implement a small auditable pure-C VM independently from the stabilized
interpreter-authority contract rather than mechanically translating the Rust
implementation.

[docs/todo/open/vm/independent-pure-c-malbolge-vm.mdc](docs/todo/open/vm/independent-pure-c-malbolge-vm.mdc)

### TODO - Custom target profile identity

Allow user-supplied target profiles with canonical hashing and explicit artifact
identity.

[docs/todo/open/compatibility/custom-target-profile-identity.mdc](docs/todo/open/compatibility/custom-target-profile-identity.mdc)

### TODO - Compiler algorithm experimentation platform

Make the repository a reproducible laboratory for compiler research, not merely
an implementation of one fixed C-to-Malbolge pipeline.

[docs/todo/open/foundation/compiler-algorithm-experimentation-platform.mdc](docs/todo/open/foundation/compiler-algorithm-experimentation-platform.mdc)

### TODO - Publication-grade paper pipeline

Create a reproducible LaTeX paper pipeline under `docs/research/papers/` capable
of turning mature investigations into publication-quality papers with canonical
bibliography, equations, figures, tables, experiment provenance, limitations,
and regenerated results without making publication a prerequisite for ordinary
engineering work.

[docs/todo/open/research/publication-grade-paper-pipeline.mdc](docs/todo/open/research/publication-grade-paper-pipeline.mdc)

### TODO - Superoptimization research program

Ask which search strategies find smaller or faster verified Malbolge blocks
under fixed time and evaluation budgets.

[docs/todo/open/research/superoptimization-research-program.mdc](docs/todo/open/research/superoptimization-research-program.mdc)

### TODO - Malbolge-specific optimization mathematics

Derive algebraic decompositions, lookup-table factorizations, state reductions,
canonical forms, and lower bounds that reduce synthesis search before brute
force or stochastic optimization begins.

[docs/todo/open/mathematics/malbolge-specific-optimization-mathematics.mdc](docs/todo/open/mathematics/malbolge-specific-optimization-mathematics.mdc)

### TODO - Scalable Malbolge memory model

Remove the practical 59,049-word ceiling from current Malbolge while retaining
`malbolge-1998` as an exact historical conformance profile.

[docs/todo/open/compatibility/scalable-malbolge-memory-model.mdc](docs/todo/open/compatibility/scalable-malbolge-memory-model.mdc)

### TODO - Batch VM execution

Execute many independent programs or inputs efficiently on CPU and accelerator
backends for fuzzing, exhaustive verification, synthesis, and search workloads.

[docs/todo/open/vm/batch-vm-execution.mdc](docs/todo/open/vm/batch-vm-execution.mdc)

### TODO - Property, fuzz, and exhaustive testing

Use property testing, fuzzing, sanitizers, regression corpora, and exhaustive
finite-domain verification for small functions and VM primitives such as rotate
and crazy operations.

[docs/todo/open/verification/property-fuzz-and-exhaustive-testing.mdc](docs/todo/open/verification/property-fuzz-and-exhaustive-testing.mdc)

### TODO - CPU VM table optimization

Optimize scalar execution with precomputed rotate tables, position-dependent
decode tables, efficient crazy-operation decomposition, cheap pointer updates,
and benchmarked micro-optimizations without semantic drift.

[docs/todo/open/vm/cpu-vm-table-optimization.mdc](docs/todo/open/vm/cpu-vm-table-optimization.mdc)

### TODO - Deterministic logical concurrency

Define deterministic logical tasks and joins that serialize under Malbolge while
allowing proven-independent host work to execute concurrently with identical
observable results.

[docs/todo/open/vm/deterministic-logical-concurrency.mdc](docs/todo/open/vm/deterministic-logical-concurrency.mdc)

### TODO - Interpreter-authority and specification-comparison modes

Make defined original-interpreter behavior the default and verifier-eligible
classic semantics.

[docs/todo/open/vm/specification-and-legacy-interpreter-modes.mdc](docs/todo/open/vm/specification-and-legacy-interpreter-modes.mdc)

### TODO - Malbolge decompiler and reverse engineering

Build a profile-explicit professional Malbolge reverse-engineering tool that can
emit executable readable representations, including C, without claiming to
recover unavailable original source from arbitrary self-modifying programs.

[docs/todo/open/tools/malbolge-decompiler-and-reverse-engineering.mdc](docs/todo/open/tools/malbolge-decompiler-and-reverse-engineering.mdc)

### TODO - Deterministic C-to-Malbolge ABI

Specify fixed integer widths, signed behavior, endianness, pointers, alignment,
object representation, stack rules, recursion policy, I/O, and a fail-closed
policy for undefined or target-dependent C behavior.

[docs/todo/open/c/deterministic-c-to-malbolge-abi.mdc](docs/todo/open/c/deterministic-c-to-malbolge-abi.mdc)

### TODO - Differential VM verification

Run specification fixtures through the Rust VM, independent C VM, and
accelerator VM and compare output, termination, state, mutation, and instruction
traces.

[docs/todo/open/verification/differential-vm-verification.mdc](docs/todo/open/verification/differential-vm-verification.mdc)

### TODO - Emitted Malbolge static analyzer

Analyze generated Malbolge for lexical and address validity, self-modification,
control-flow reachability, code/data aliasing, wraparound, dataflow, invalid
executable cells, and input-dependent cycles or hangs.

[docs/todo/open/verification/emitted-malbolge-static-analyzer.mdc](docs/todo/open/verification/emitted-malbolge-static-analyzer.mdc)

### TODO - Exact and diagnostic cycle detection

Provide optional repeated-state detection using collision-safe confirmation for
exact results and clearly label probabilistic hash-only diagnostics.

[docs/todo/open/verification/exact-and-diagnostic-cycle-detection.mdc](docs/todo/open/verification/exact-and-diagnostic-cycle-detection.mdc)

### TODO - Human-scale Malbolge search study

Create a bounded experiment illustrating why manual Malbolge synthesis is
cognitively impractical even for very capable humans, separating attention and
energy limits from machine-search throughput without bogus IQ or neuroscience
claims.

[docs/todo/open/research/human-scale-malbolge-search-study.mdc](docs/todo/open/research/human-scale-malbolge-search-study.mdc)

### TODO - Replaceable accelerator boundary

Define a hardware-neutral interface for candidate evaluation, batch VM
execution, search, and verification.

[docs/todo/open/accelerator/replaceable-accelerator-boundary.mdc](docs/todo/open/accelerator/replaceable-accelerator-boundary.mdc)

### TODO - Required-profile diagnostics

Emit deterministic diagnostics naming the required Malbolge profile/features,
required memory or address capacity, and missing runtime capability.

[docs/todo/open/compatibility/required-profile-diagnostics.mdc](docs/todo/open/compatibility/required-profile-diagnostics.mdc)

### TODO - Machine-checked mathematical correspondence

Connect mathematical specifications to executable tests or proof tooling so the
`.tex` files are reviewable mathematics rather than decorative documentation.

[docs/todo/open/mathematics/machine-checked-mathematical-correspondence.mdc](docs/todo/open/mathematics/machine-checked-mathematical-correspondence.mdc)

### TODO - tools/tidy clang-tidy plugin

Build `tools/tidy/` as an out-of-tree clang-tidy plugin compiled against the
pinned LLVM version.

[docs/todo/open/c/tools-tidy-clang-tidy-plugin.mdc](docs/todo/open/c/tools-tidy-clang-tidy-plugin.mdc)

### TODO - Parametric compiler challenge generator

Build deterministic workload generators whose difficulty can grow continuously
instead of saturating at one application-specific threshold.

[docs/todo/open/applications/parametric-compiler-challenge-generator.mdc](docs/todo/open/applications/parametric-compiler-challenge-generator.mdc)

### TODO - Supported libc contract

Define the guest C library surface: fixed-width integers, memory primitives,
byte streams, strings, allocation, formatting, `libm`, and later higher-level
routines without hidden host shortcuts.

[docs/todo/open/c/supported-libc-contract.mdc](docs/todo/open/c/supported-libc-contract.mdc)

### TODO - Clang C frontend integration

Use Clang as the C parser, type system, constant evaluator, source-location
provider, and AST frontend instead of building another C parser.

[docs/todo/open/compiler/clang-c-frontend-integration.mdc](docs/todo/open/compiler/clang-c-frontend-integration.mdc)

### TODO - Versioned host-capability call ABI

Generalize the semantic capability-ID pattern proven by the DOOM corpus into the
VM ABI.

[docs/todo/open/c/versioned-host-capability-call-abi.mdc](docs/todo/open/c/versioned-host-capability-call-abi.mdc)

## P2 — Compiler, runtime, and accelerator core

### TODO - Self-modification state-graph optimizer

Model executable Malbolge regions as versioned state-transition graphs whose
nodes capture only semantically relevant code/data state.

[docs/todo/open/mathematics/self-modification-state-graph-optimizer.mdc](docs/todo/open/mathematics/self-modification-state-graph-optimizer.mdc)

### TODO - CUDA exact VM adapter

Implement the first GPU adapter with exact discrete Malbolge semantics and
massively parallel independent VM execution for candidate evaluation and test
batches.

[docs/todo/open/accelerator/cuda-exact-vm-adapter.mdc](docs/todo/open/accelerator/cuda-exact-vm-adapter.mdc)

### TODO - Configurable accelerator algorithm adapters

Separate optimization/search strategy from accelerator hardware.

[docs/todo/open/accelerator/configurable-accelerator-algorithm-adapters.mdc](docs/todo/open/accelerator/configurable-accelerator-algorithm-adapters.mdc)

### TODO - Historical-interpreter fallback capsule

Design an extended `.malbolge` container recognized by modern runtimes while the
1998 loader sees only a valid classic fallback, ideally using whitespace
metadata that the original loader ignores.

[docs/todo/open/compatibility/historical-interpreter-fallback-capsule.mdc](docs/todo/open/compatibility/historical-interpreter-fallback-capsule.mdc)

### TODO - Typed compiler IR

Define a small deterministic IR representing control flow, arithmetic, memory,
calls, byte I/O, target-profile requirements, and proof obligations without
inheriting unnecessary LLVM complexity.

[docs/todo/open/compiler/typed-compiler-ir.mdc](docs/todo/open/compiler/typed-compiler-ir.mdc)

### TODO - Guest runtime and allocator

Implement startup, calling convention, frames, allocation, streams, integer
helpers, strings, deterministic math helpers, scheduling primitives, and other
runtime facilities as code that ultimately executes under Malbolge semantics.

[docs/todo/open/c/guest-runtime-and-allocator.mdc](docs/todo/open/c/guest-runtime-and-allocator.mdc)

### TODO - Multi-objective compiler algorithm evaluation arena

Evaluate compiler and execution algorithms over scalable challenge families and
produce capacity curves and Pareto frontiers rather than one pass/fail score.

[docs/todo/open/applications/multi-objective-compiler-algorithm-evaluation-arena.mdc](docs/todo/open/applications/multi-objective-compiler-algorithm-evaluation-arena.mdc)

### TODO - Tiered native execution engine

Build a tiered execution engine instead of choosing between interpretation, AOT,
and JIT.

[docs/todo/open/vm/tiered-native-execution-engine.mdc](docs/todo/open/vm/tiered-native-execution-engine.mdc)

### TODO - Adaptive accelerator resource budgeting

Discover available memory and compute resources at runtime and choose batch
size, state layout, caches, and search breadth accordingly.

[docs/todo/open/accelerator/adaptive-accelerator-resource-budgeting.mdc](docs/todo/open/accelerator/adaptive-accelerator-resource-budgeting.mdc)

### TODO - Ternary machine lowering

Lower typed C IR into a compact ternary virtual-machine representation suited to
Malbolge instead of translating C operations directly instruction by
instruction.

[docs/todo/open/compiler/ternary-machine-lowering.mdc](docs/todo/open/compiler/ternary-machine-lowering.mdc)

### TODO - CUDA Linux runtime and hermetic toolchain

Port the exact CUDA runtime and repository-local development toolchains to Linux
while preserving platform-specific ABI loading, exact package identity, CPU
fallback, and verifier authority.

[docs/todo/open/accelerator/cuda-linux-runtime-and-hermetic-toolchain.mdc](docs/todo/open/accelerator/cuda-linux-runtime-and-hermetic-toolchain.mdc)

### TODO - Native x86-64 and AArch64 backends

Implement native-code emitters for x86-64 and AArch64 behind one execution-IR
backend contract.

[docs/todo/open/vm/native-x86-64-and-aarch64-backends.mdc](docs/todo/open/vm/native-x86-64-and-aarch64-backends.mdc)

### TODO - Malbolge layout and encoding backend

Implement address-sensitive instruction layout, self-modification planning,
encoding, jumps, data placement, runtime linkage, and final `.malbolge`
emission.

[docs/todo/open/compiler/malbolge-layout-and-encoding-backend.mdc](docs/todo/open/compiler/malbolge-layout-and-encoding-backend.mdc)

### TODO - Compact guest bytecode strategy

Evaluate a VM-inside-Malbolge strategy where large programs are represented as
compact bytecode interpreted by a reusable Malbolge runtime when that reduces
code-size explosion or compilation cost.

[docs/todo/open/compiler/compact-guest-bytecode-strategy.mdc](docs/todo/open/compiler/compact-guest-bytecode-strategy.mdc)

## P3 — Optimization, proof, and reusable scale

### TODO - Annotated Malbolge source syntax and formatter

Add an explicit readable Malbolge source form that supports multiline layout,
full-line comments, deterministic automatic formatting, and source maps while
canonicalizing to exactly the same position-sensitive `.malbolge` bytes consumed
by the selected profile loader.

[docs/todo/open/tools/annotated-malbolge-source-syntax-and-formatter.mdc](docs/todo/open/tools/annotated-malbolge-source-syntax-and-formatter.mdc)

### TODO - Source-bound diff generator

Implement `algorithms/diff/` as a generic deterministic generator that learns a
source-tree transformation from a local source/oracle pair and emits a
distributable transform whose target material remains bound to sufficiently
compatible source input.

[docs/todo/open/tools/source-bound-diff-generator.mdc](docs/todo/open/tools/source-bound-diff-generator.mdc)

### TODO - Translation validation

Verify compiled programs and blocks against source IR so optimizer and search
components may remain untrusted.

[docs/todo/open/verification/translation-validation.mdc](docs/todo/open/verification/translation-validation.mdc)

### TODO - Ahead-of-execution native translation

Translate reachable stable Malbolge regions into native code in memory before
guest execution begins.

[docs/todo/open/vm/ahead-of-execution-native-translation.mdc](docs/todo/open/vm/ahead-of-execution-native-translation.mdc)

### TODO - Cross-platform native capability runners

Implement the version-1 host-capability contract for supported 64-bit Windows,
macOS, and Linux runners on x86-64 and AArch64.

[docs/todo/open/vm/cross-platform-native-capability-runners.mdc](docs/todo/open/vm/cross-platform-native-capability-runners.mdc)

### TODO - Guarded self-modification JIT

Compile hot mutable regions after observing their concrete code-state versions.

[docs/todo/open/vm/guarded-self-modification-jit.mdc](docs/todo/open/vm/guarded-self-modification-jit.mdc)

### TODO - tools/tidy lowerability contract

Partition checks into language, ABI, runtime, determinism, and resource families
and enforce the promise that every accepted translation unit is supported by the
compiler for its declared target profile.

[docs/todo/open/c/tools-tidy-lowerability-contract.mdc](docs/todo/open/c/tools-tidy-lowerability-contract.mdc)

### TODO - C-level source mapping and debugging

Generate source maps from Malbolge addresses through lowered IR back to C source
locations.

[docs/todo/open/compiler/c-level-source-mapping-and-debugging.mdc](docs/todo/open/compiler/c-level-source-mapping-and-debugging.mdc)

### TODO - Deterministic binary byte-stream runtime

Prove generated programs can consume and emit arbitrary binary byte streams
without host-side format logic, creating the foundation for real deterministic
file transformers.

[docs/todo/open/applications/deterministic-binary-byte-stream-runtime.mdc](docs/todo/open/applications/deterministic-binary-byte-stream-runtime.mdc)

### TODO - Deterministic cross-backend artifact hashing

Require byte-identical outputs and hashes across backends for declared
deterministic workloads, including versioned example artifacts and compiler-
produced `.malbolge` artifacts where deterministic builds are promised.

[docs/todo/open/applications/deterministic-cross-backend-artifact-hashing.mdc](docs/todo/open/applications/deterministic-cross-backend-artifact-hashing.mdc)

### TODO - Hexagonal authoring-layout experiment

Research an optional graph or hexagonal authoring representation that lowers to
ordinary linear `.malbolge` output and therefore does not require a special
execution engine for compatible programs.

[docs/todo/open/compatibility/hexagonal-authoring-layout-experiment.mdc](docs/todo/open/compatibility/hexagonal-authoring-layout-experiment.mdc)

### TODO - Deterministic CPU optimizer

Implement a correct CPU reference optimizer and search engine that works without
a GPU, even when much slower, and acts as the declared-profile-conformant CPU
baseline for accelerator implementations.

[docs/todo/open/accelerator/deterministic-cpu-optimizer.mdc](docs/todo/open/accelerator/deterministic-cpu-optimizer.mdc)

### TODO - State-aware Malbolge linker

Build a linker that composes independently compiled Malbolge blocks while
resolving symbols, addresses, entry/exit machine-state contracts, positional
decode phase, post-instruction encryption phase, and self-modification
footprints.

[docs/todo/open/compiler/state-aware-malbolge-linker.mdc](docs/todo/open/compiler/state-aware-malbolge-linker.mdc)

### TODO - Explicit native-tier execution controls

Expose independent `--no-jit` and `--no-aot` runtime controls plus an
`--interpreter-only` shorthand equivalent to disabling both native compilation
tiers and native-code cache reuse.

[docs/todo/open/vm/explicit-native-tier-execution-controls.mdc](docs/todo/open/vm/explicit-native-tier-execution-controls.mdc)

### TODO - Proof-producing lowering

Investigate compiler outputs carrying compact witnesses or proof material for
local equivalence claims so final acceptance need not trust CUDA, PyTorch,
stochastic search, or superoptimization implementations.

[docs/todo/open/verification/proof-producing-lowering.mdc](docs/todo/open/verification/proof-producing-lowering.mdc)

### TODO - Versioned C and Malbolge example corpus

Publish intentionally selected project-owned examples under
`docs/technical/examples/` with paired `.c` and `.malbolge` artifacts.

[docs/todo/open/applications/versioned-c-and-malbolge-example-corpus.mdc](docs/todo/open/applications/versioned-c-and-malbolge-example-corpus.mdc)

### TODO - Portable c2malbolge implementation in C

Keep a path for the essential compiler algorithm to exist in the admitted C
profile without mandatory LLVM runtime, GPU, filesystem complexity, threads, or
other host-only capabilities.

[docs/todo/open/self_hosting/portable-c2malbolge-implementation-in-c.mdc](docs/todo/open/self_hosting/portable-c2malbolge-implementation-in-c.mdc)

### TODO - Machine-readable LLM and compiler challenge corpus

Expose challenge definitions, expected semantics, constraints, oracle behavior,
inputs, difficulty parameters, and evaluation results in a stable machine-
readable format so compiler researchers and LLM-based code/algorithm agents can
generate candidate passes or algorithms and submit them to the same verifier and
benchmark arena.

[docs/todo/open/applications/machine-readable-llm-and-compiler-challenge-corpus.mdc](docs/todo/open/applications/machine-readable-llm-and-compiler-challenge-corpus.mdc)

### TODO - Search pruning and state canonicalization

Develop exact pruning, dominance rules, partial-equivalence checks, canonical
states, admissible heuristics, and profile-aware constraints before relying on
raw hardware scale.

[docs/todo/open/accelerator/search-pruning-and-state-canonicalization.mdc](docs/todo/open/accelerator/search-pruning-and-state-canonicalization.mdc)

### TODO - Stochastic and guided search

Evaluate Monte Carlo, evolutionary, STOKE-like stochastic, learned, and hybrid
search with deterministic final verification and reproducible research seeds.

[docs/todo/open/accelerator/stochastic-and-guided-search.mdc](docs/todo/open/accelerator/stochastic-and-guided-search.mdc)

### TODO - Reusable block catalogue

Build a deterministic catalogue of verified arithmetic, branch, memory, calling
convention, and runtime blocks so common operations are solved once and reused
instead of synthesized from scratch for every compilation.

[docs/todo/open/accelerator/reusable-block-catalogue.mdc](docs/todo/open/accelerator/reusable-block-catalogue.mdc)

### TODO - Compile c2malbolge.c to Malbolge

Compile the portable C compiler implementation with `c2malbolge` itself and run
the resulting `c2malbolge.malbolge` under the modern VM.

[docs/todo/open/self_hosting/compile-c2malbolge-c-to-malbolge.mdc](docs/todo/open/self_hosting/compile-c2malbolge-c-to-malbolge.mdc)

## P4 — Applications, evidence, and self-hosting

### TODO - Resident incremental compiler and WAL

Build a native long-lived compiler service that keeps parsed source, normalized
IR, dependency state, verified blocks, link plans, and reusable artifacts
resident in RAM.

[docs/todo/open/compiler/resident-incremental-compiler-and-wal.mdc](docs/todo/open/compiler/resident-incremental-compiler-and-wal.mdc)

### TODO - DOOM playable generated-code performance

Optimize lowering, block selection, guest runtime, VM execution, JIT paths, and
accelerator-assisted compilation until the user-supplied DOOM interoperability
pipeline produces a `.malbolge` build that is genuinely interactive and playable
under the modern runtime.

[docs/todo/open/applications/doom-playable-generated-code-performance.mdc](docs/todo/open/applications/doom-playable-generated-code-performance.mdc)

### TODO - Empirical Malbolge synthesis scaling law

Measure how verified synthesis cost changes with challenge difficulty,
self-modification footprint, layout coupling, target-state entropy, and reusable
catalogue coverage.

[docs/todo/open/research/empirical-malbolge-synthesis-scaling-law.mdc](docs/todo/open/research/empirical-malbolge-synthesis-scaling-law.mdc)

### TODO - Malbolge compiler compiles C to Malbolge

Use `c2malbolge.malbolge` to consume C source and emit a new working `.malbolge`
program, proving practical self-hosting of the translation path.

[docs/todo/open/self_hosting/malbolge-compiler-compiles-c-to-malbolge.mdc](docs/todo/open/self_hosting/malbolge-compiler-compiles-c-to-malbolge.mdc)

### TODO - CUDA superoptimizer

Implement GPU-parallel candidate synthesis, pruning, equivalence testing, cost
evaluation, and verified block stitching.

[docs/todo/open/accelerator/cuda-superoptimizer.mdc](docs/todo/open/accelerator/cuda-superoptimizer.mdc)

### TODO - PyTorch search orchestration

Use PyTorch for batched candidate/state representation, experiment
orchestration, and heuristic models where useful while purpose-built kernels
retain exact semantic execution where tensor operations are a poor fit.

[docs/todo/open/accelerator/pytorch-search-orchestration.mdc](docs/todo/open/accelerator/pytorch-search-orchestration.mdc)

### TODO - Real-program benchmark suite

Benchmark hello world, byte copying, arithmetic kernels, hashing, parsers,
parametric challenge families, DOOM interoperability, and compiler workloads
across original C, modern C, Rust, CPU batch, JIT, and accelerator paths.

[docs/todo/open/applications/real-program-benchmark-suite.mdc](docs/todo/open/applications/real-program-benchmark-suite.mdc)

### TODO - Self-hosting equivalence proof

Compare native and Malbolge-hosted compiler outputs or normalized semantic
artifacts and prove self-hosting does not silently change compilation meaning.

[docs/todo/open/self_hosting/self-hosting-equivalence-proof.mdc](docs/todo/open/self_hosting/self-hosting-equivalence-proof.mdc)

### TODO - Compilation latency performance budget

Establish measured compile-time budgets for cold compilation, warm resident
compilation, semantic invalidation, verified block reuse, relinking,
verification, and novel search.

[docs/todo/open/accelerator/compilation-latency-performance-budget.mdc](docs/todo/open/accelerator/compilation-latency-performance-budget.mdc)

### TODO - Turnkey C-to-Malbolge toolchain

Deliver the final supported workflow: bootstrap every public project dependency
except Jig, accept an explicitly named C source file, and emit one verified
`.malbolge` artifact through a single documented command on supported Windows
and Linux hosts.

[docs/todo/open/compiler/turnkey-c-to-malbolge-toolchain.mdc](docs/todo/open/compiler/turnkey-c-to-malbolge-toolchain.mdc)

### TODO - ROCm adapter contract reservation

Reserve a hardware-neutral ROCm adapter identity and capability boundary without
implementing, packaging, benchmarking, or advertising ROCm support until
supported AMD hardware and an explicit maintainer are available.

[docs/todo/open/accelerator/rocm-accelerator-adapter.mdc](docs/todo/open/accelerator/rocm-accelerator-adapter.mdc)

### TODO - Historical capability demonstration

Produce a reproducible demonstration from the 1998 interpreter through modern
tooling to substantial generated programs and self-hosting while keeping
historical attribution and compatibility evidence explicit.

[docs/todo/open/research/historical-capability-demonstration.mdc](docs/todo/open/research/historical-capability-demonstration.mdc)
