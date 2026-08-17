# Malbolge TODO

Only unfinished work appears here. P0 is the highest-priority horizon and P5 is
the final documentation and publication horizon. Within each section, active
work appears first and stable task identity breaks ties; typed lanes and
dependencies remain execution authority.

Full metadata, acceptance criteria, dependencies, evidence, and planning notes
remain in typed records under `docs/todo/open/`. Completed records remain under
`docs/todo/completed/`.

**Canonical TODO format:** one `### TODO - ...` title, one synthesis paragraph,
then one direct Markdown link to the complete typed record. No per-item field
labels belong here.

## P0 — Authority and governance

### TODO - Linux development host bootstrap

Make Linux development hosts bootstrap repository-local validation tooling and
run Jig without inheriting Windows executable paths or ambient PATH authority.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/foundation/linux-development-host-bootstrap.mdc](docs/todo/open/foundation/linux-development-host-bootstrap.mdc)

## P1 — Semantic and language foundations

### TODO - Emitted Malbolge static analyzer

Analyze generated Malbolge for lexical and address validity, self-modification,
control-flow reachability, code/data aliasing, wraparound, dataflow, invalid
executable cells, and input-dependent cycles or hangs.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/verification/emitted-malbolge-static-analyzer.mdc](docs/todo/open/verification/emitted-malbolge-static-analyzer.mdc)

### TODO - Malbolge-specific optimization mathematics

Derive algebraic decompositions, lookup-table factorizations, state reductions,
canonical forms, and lower bounds that reduce synthesis search before brute
force or stochastic optimization begins.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/mathematics/malbolge-specific-optimization-mathematics.mdc](docs/todo/open/mathematics/malbolge-specific-optimization-mathematics.mdc)

### TODO - Parametric compiler challenge generator

Build deterministic workload generators whose difficulty can grow continuously
instead of saturating at one application-specific threshold.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/applications/parametric-compiler-challenge-generator.mdc](docs/todo/open/applications/parametric-compiler-challenge-generator.mdc)

### TODO - Required-profile diagnostics

Emit deterministic diagnostics naming the required Malbolge profile/features,
required memory or address capacity, and missing runtime capability.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/compatibility/required-profile-diagnostics.mdc](docs/todo/open/compatibility/required-profile-diagnostics.mdc)

### TODO - Superoptimization research program

Ask which search strategies find smaller or faster verified Malbolge blocks
under fixed time and evaluation budgets.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/research/superoptimization-research-program.mdc](docs/todo/open/research/superoptimization-research-program.mdc)

## P2 — Compiler, runtime, and accelerator core

### TODO - Adaptive accelerator resource budgeting

Discover available memory and compute resources at runtime and choose batch
size, state layout, caches, and search breadth accordingly.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/accelerator/adaptive-accelerator-resource-budgeting.mdc](docs/todo/open/accelerator/adaptive-accelerator-resource-budgeting.mdc)

### TODO - Configurable accelerator algorithm adapters

Separate optimization/search strategy from accelerator hardware.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/accelerator/configurable-accelerator-algorithm-adapters.mdc](docs/todo/open/accelerator/configurable-accelerator-algorithm-adapters.mdc)

### TODO - CUDA exact VM adapter

Implement the first GPU adapter with exact discrete Malbolge semantics and
massively parallel independent VM execution for candidate evaluation and test
batches.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/accelerator/cuda-exact-vm-adapter.mdc](docs/todo/open/accelerator/cuda-exact-vm-adapter.mdc)

### TODO - Guest runtime and allocator

Implement startup, calling convention, frames, allocation, streams, integer
helpers, strings, deterministic math helpers, scheduling primitives, and other
runtime facilities as code that ultimately executes under Malbolge semantics.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/c/guest-runtime-and-allocator.mdc](docs/todo/open/c/guest-runtime-and-allocator.mdc)

### TODO - Historical-interpreter fallback capsule

Design an extended `.malbolge` container recognized by modern runtimes while the
1998 loader sees only a valid classic fallback, ideally using whitespace
metadata that the original loader ignores.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/compatibility/historical-interpreter-fallback-capsule.mdc](docs/todo/open/compatibility/historical-interpreter-fallback-capsule.mdc)

### TODO - Native x86-64 and AArch64 backends

Implement native-code emitters for x86-64 and AArch64 behind one execution-IR
backend contract.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/vm/native-x86-64-and-aarch64-backends.mdc](docs/todo/open/vm/native-x86-64-and-aarch64-backends.mdc)

### TODO - Resumable compilation progress sidecars

Persist an atomic JSON sidecar and compatible checkpoint for long-running
source, block, optimization, verification, and GPU jobs so elapsed time,
scientific provenance, current stage, and recoverable work survive process or
host failure without publishing an incomplete final `.malbolge` artifact.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/compiler/resumable-compilation-progress-sidecars.mdc](docs/todo/open/compiler/resumable-compilation-progress-sidecars.mdc)

### TODO - Self-modification state-graph optimizer

Model executable Malbolge regions as versioned state-transition graphs whose
nodes capture only semantically relevant code/data state.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/mathematics/self-modification-state-graph-optimizer.mdc](docs/todo/open/mathematics/self-modification-state-graph-optimizer.mdc)

### TODO - Tiered native execution engine

Build a tiered execution engine instead of choosing between interpretation, AOT,
and JIT.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/vm/tiered-native-execution-engine.mdc](docs/todo/open/vm/tiered-native-execution-engine.mdc)

### TODO - Compact guest bytecode strategy

Evaluate a VM-inside-Malbolge strategy where large programs are represented as
compact bytecode interpreted by a reusable Malbolge runtime when that reduces
code-size explosion or compilation cost.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/compiler/compact-guest-bytecode-strategy.mdc](docs/todo/open/compiler/compact-guest-bytecode-strategy.mdc)

### TODO - CUDA Linux runtime and hermetic toolchain

Port the exact CUDA runtime and repository-local development toolchains to Linux
while preserving platform-specific ABI loading, exact package identity, CPU
fallback, verifier authority, and existing Windows support.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/accelerator/cuda-linux-runtime-and-hermetic-toolchain.mdc](docs/todo/open/accelerator/cuda-linux-runtime-and-hermetic-toolchain.mdc)

### TODO - Malbolge layout and encoding backend

Implement address-sensitive instruction layout, self-modification planning,
encoding, jumps, data placement, runtime linkage, and final `.malbolge`
emission.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/compiler/malbolge-layout-and-encoding-backend.mdc](docs/todo/open/compiler/malbolge-layout-and-encoding-backend.mdc)

### TODO - Multi-objective compiler algorithm evaluation arena

Evaluate compiler and execution algorithms over scalable challenge families and
produce capacity curves and Pareto frontiers rather than one pass/fail score.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/applications/multi-objective-compiler-algorithm-evaluation-arena.mdc](docs/todo/open/applications/multi-objective-compiler-algorithm-evaluation-arena.mdc)

### TODO - Ternary machine lowering

Lower typed C IR into a compact ternary virtual-machine representation suited to
Malbolge instead of translating C operations directly instruction by
instruction.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/compiler/ternary-machine-lowering.mdc](docs/todo/open/compiler/ternary-machine-lowering.mdc)

## P3 — Optimization, proof, and reusable scale

### TODO - Annotated Malbolge source syntax and formatter

Add an explicit readable Malbolge source form that supports multiline layout,
full-line comments, deterministic automatic formatting, and source maps while
canonicalizing to exactly the same position-sensitive `.malbolge` bytes consumed
by the selected profile loader.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/tools/annotated-malbolge-source-syntax-and-formatter.mdc](docs/todo/open/tools/annotated-malbolge-source-syntax-and-formatter.mdc)

### TODO - Deterministic CPU optimizer

Implement a correct CPU reference optimizer and search engine that works without
a GPU, even when much slower, and acts as the declared-profile-conformant CPU
baseline for accelerator implementations.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/accelerator/deterministic-cpu-optimizer.mdc](docs/todo/open/accelerator/deterministic-cpu-optimizer.mdc)

### TODO - Search pruning and state canonicalization

Develop exact pruning, dominance rules, partial-equivalence checks, canonical
states, admissible heuristics, and profile-aware constraints before relying on
raw hardware scale.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/accelerator/search-pruning-and-state-canonicalization.mdc](docs/todo/open/accelerator/search-pruning-and-state-canonicalization.mdc)

### TODO - Source-bound diff generator

Implement `algorithms/diff/` as a generic deterministic generator that learns a
source-tree transformation from a local source/oracle pair and emits a
distributable transform whose target material remains bound to sufficiently
compatible source input.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/tools/source-bound-diff-generator.mdc](docs/todo/open/tools/source-bound-diff-generator.mdc)

### TODO - Ahead-of-execution native translation

Translate reachable stable Malbolge regions into native code in memory before
guest execution begins.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/vm/ahead-of-execution-native-translation.mdc](docs/todo/open/vm/ahead-of-execution-native-translation.mdc)

### TODO - C-level source mapping and debugging

Generate source maps from Malbolge addresses through lowered IR back to C source
locations.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/compiler/c-level-source-mapping-and-debugging.mdc](docs/todo/open/compiler/c-level-source-mapping-and-debugging.mdc)

### TODO - Compile c2malbolge.c to Malbolge

Compile the portable C compiler implementation with `c2malbolge` itself and run
the resulting `c2malbolge.malbolge` under the modern VM.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/self_hosting/compile-c2malbolge-c-to-malbolge.mdc](docs/todo/open/self_hosting/compile-c2malbolge-c-to-malbolge.mdc)

### TODO - Cross-platform native capability runners

Implement the version-1 host-capability contract for supported 64-bit Windows,
macOS, and Linux runners on x86-64 and AArch64.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/vm/cross-platform-native-capability-runners.mdc](docs/todo/open/vm/cross-platform-native-capability-runners.mdc)

### TODO - Deterministic binary byte-stream runtime

Prove generated programs can consume and emit arbitrary binary byte streams
without host-side format logic, creating the foundation for real deterministic
file transformers.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/applications/deterministic-binary-byte-stream-runtime.mdc](docs/todo/open/applications/deterministic-binary-byte-stream-runtime.mdc)

### TODO - Deterministic cross-backend artifact hashing

Require byte-identical outputs and hashes across backends for declared
deterministic workloads, including versioned example artifacts and compiler-
produced `.malbolge` artifacts where deterministic builds are promised.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/applications/deterministic-cross-backend-artifact-hashing.mdc](docs/todo/open/applications/deterministic-cross-backend-artifact-hashing.mdc)

### TODO - Explicit native-tier execution controls

Expose independent `--no-jit` and `--no-aot` runtime controls plus an
`--interpreter-only` shorthand equivalent to disabling both native compilation
tiers and native-code cache reuse.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/vm/explicit-native-tier-execution-controls.mdc](docs/todo/open/vm/explicit-native-tier-execution-controls.mdc)

### TODO - Guarded self-modification JIT

Compile hot mutable regions after observing their concrete code-state versions.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/vm/guarded-self-modification-jit.mdc](docs/todo/open/vm/guarded-self-modification-jit.mdc)

### TODO - Hexagonal authoring-layout experiment

Research an optional graph or hexagonal authoring representation that lowers to
ordinary linear `.malbolge` output and therefore does not require a special
execution engine for compatible programs.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/compatibility/hexagonal-authoring-layout-experiment.mdc](docs/todo/open/compatibility/hexagonal-authoring-layout-experiment.mdc)

### TODO - Machine-readable LLM and compiler challenge corpus

Expose challenge definitions, expected semantics, constraints, oracle behavior,
inputs, difficulty parameters, and evaluation results in a stable machine-
readable format so compiler researchers and LLM-based code/algorithm agents can
generate candidate passes or algorithms and submit them to the same verifier and
benchmark arena.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/applications/machine-readable-llm-and-compiler-challenge-corpus.mdc](docs/todo/open/applications/machine-readable-llm-and-compiler-challenge-corpus.mdc)

### TODO - Portable c2malbolge implementation in C

Keep a path for the essential compiler algorithm to exist in the admitted C
profile without mandatory LLVM runtime, GPU, filesystem complexity, threads, or
other host-only capabilities.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/self_hosting/portable-c2malbolge-implementation-in-c.mdc](docs/todo/open/self_hosting/portable-c2malbolge-implementation-in-c.mdc)

### TODO - Proof-producing lowering

Investigate compiler outputs carrying compact witnesses or proof material for
local equivalence claims so final acceptance need not trust CUDA, PyTorch,
stochastic search, or superoptimization implementations.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/verification/proof-producing-lowering.mdc](docs/todo/open/verification/proof-producing-lowering.mdc)

### TODO - Reusable block catalogue

Build a deterministic catalogue of verified arithmetic, branch, memory, calling
convention, and runtime blocks so common operations are solved once and reused
instead of synthesized from scratch for every compilation.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/accelerator/reusable-block-catalogue.mdc](docs/todo/open/accelerator/reusable-block-catalogue.mdc)

### TODO - State-aware Malbolge linker

Build a linker that composes independently compiled Malbolge blocks while
resolving symbols, addresses, entry/exit machine-state contracts, positional
decode phase, post-instruction encryption phase, and self-modification
footprints.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/compiler/state-aware-malbolge-linker.mdc](docs/todo/open/compiler/state-aware-malbolge-linker.mdc)

### TODO - Stochastic and guided search

Evaluate Monte Carlo, evolutionary, STOKE-like stochastic, learned, and hybrid
search with deterministic final verification and reproducible research seeds.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/accelerator/stochastic-and-guided-search.mdc](docs/todo/open/accelerator/stochastic-and-guided-search.mdc)

### TODO - tools/tidy lowerability contract

Partition checks into language, ABI, runtime, determinism, and resource families
and enforce the promise that every accepted translation unit is supported by the
compiler for its declared target profile.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/c/tools-tidy-lowerability-contract.mdc](docs/todo/open/c/tools-tidy-lowerability-contract.mdc)

### TODO - Translation validation

Verify compiled programs and blocks against source IR so optimizer and search
components may remain untrusted.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/verification/translation-validation.mdc](docs/todo/open/verification/translation-validation.mdc)

### TODO - Versioned C and Malbolge example corpus

Publish intentionally selected project-owned examples under
`docs/technical/examples/` with paired `.c` and `.malbolge` artifacts.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/applications/versioned-c-and-malbolge-example-corpus.mdc](docs/todo/open/applications/versioned-c-and-malbolge-example-corpus.mdc)

## P4 — Applications, evidence, and self-hosting

### TODO - Compilation latency performance budget

Establish measured compile-time budgets for cold compilation, warm resident
compilation, semantic invalidation, verified block reuse, relinking,
verification, and novel search.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/accelerator/compilation-latency-performance-budget.mdc](docs/todo/open/accelerator/compilation-latency-performance-budget.mdc)

### TODO - CUDA superoptimizer

Implement GPU-parallel candidate synthesis, pruning, equivalence testing, cost
evaluation, and verified block stitching.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/accelerator/cuda-superoptimizer.mdc](docs/todo/open/accelerator/cuda-superoptimizer.mdc)

### TODO - DOOM playable generated-code performance

Optimize lowering, block selection, guest runtime, VM execution, JIT paths, and
accelerator-assisted compilation until the user-supplied DOOM interoperability
pipeline produces a `.malbolge` build that is genuinely interactive and playable
under the modern runtime.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/applications/doom-playable-generated-code-performance.mdc](docs/todo/open/applications/doom-playable-generated-code-performance.mdc)

### TODO - Empirical Malbolge synthesis scaling law

Measure how verified synthesis cost changes with challenge difficulty,
self-modification footprint, layout coupling, target-state entropy, and reusable
catalogue coverage.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/research/empirical-malbolge-synthesis-scaling-law.mdc](docs/todo/open/research/empirical-malbolge-synthesis-scaling-law.mdc)

### TODO - Malbolge compiler compiles C to Malbolge

Use `c2malbolge.malbolge` to consume C source and emit a new working `.malbolge`
program, proving practical self-hosting of the translation path.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/self_hosting/malbolge-compiler-compiles-c-to-malbolge.mdc](docs/todo/open/self_hosting/malbolge-compiler-compiles-c-to-malbolge.mdc)

### TODO - PyTorch search orchestration

Use PyTorch for batched candidate/state representation, experiment
orchestration, and heuristic models where useful while purpose-built kernels
retain exact semantic execution where tensor operations are a poor fit.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/accelerator/pytorch-search-orchestration.mdc](docs/todo/open/accelerator/pytorch-search-orchestration.mdc)

### TODO - Real-program benchmark suite

Benchmark hello world, byte copying, arithmetic kernels, hashing, parsers,
parametric challenge families, DOOM interoperability, and compiler workloads
across original C, modern C, Rust, CPU batch, JIT, and accelerator paths.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/applications/real-program-benchmark-suite.mdc](docs/todo/open/applications/real-program-benchmark-suite.mdc)

### TODO - Resident incremental compiler and WAL

Build a native long-lived compiler service that keeps parsed source, normalized
IR, dependency state, verified blocks, link plans, and reusable artifacts
resident in RAM.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/compiler/resident-incremental-compiler-and-wal.mdc](docs/todo/open/compiler/resident-incremental-compiler-and-wal.mdc)

### TODO - ROCm adapter contract reservation

Reserve a hardware-neutral ROCm adapter identity and capability boundary without
implementing, packaging, benchmarking, or advertising ROCm support until
supported AMD hardware and an explicit maintainer are available.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/accelerator/rocm-accelerator-adapter.mdc](docs/todo/open/accelerator/rocm-accelerator-adapter.mdc)

### TODO - Self-hosting equivalence proof

Compare native and Malbolge-hosted compiler outputs or normalized semantic
artifacts and prove self-hosting does not silently change compilation meaning.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/self_hosting/self-hosting-equivalence-proof.mdc](docs/todo/open/self_hosting/self-hosting-equivalence-proof.mdc)

### TODO - Turnkey C-to-Malbolge toolchain

Deliver the final supported workflow: bootstrap every public project dependency
except Jig, accept an explicitly named C source file, and emit one verified
`.malbolge` artifact through a single documented command on supported Windows
and Linux hosts.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/compiler/turnkey-c-to-malbolge-toolchain.mdc](docs/todo/open/compiler/turnkey-c-to-malbolge-toolchain.mdc)

## P5 — Documentation and publication

### TODO - Historical capability demonstration

Produce a reproducible demonstration from the 1998 interpreter through modern
tooling to substantial generated programs and self-hosting while keeping
historical attribution and compatibility evidence explicit.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/research/historical-capability-demonstration.mdc](docs/todo/open/research/historical-capability-demonstration.mdc)

### TODO - Human-scale Malbolge search study

Create a bounded experiment illustrating why manual Malbolge synthesis is
cognitively impractical even for very capable humans, separating attention and
energy limits from machine-search throughput without bogus IQ or neuroscience
claims.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/research/human-scale-malbolge-search-study.mdc](docs/todo/open/research/human-scale-malbolge-search-study.mdc)

### TODO - Publication-grade paper pipeline

Create a reproducible LaTeX paper pipeline under `docs/research/papers/` capable
of turning mature investigations into publication-quality papers with canonical
bibliography, equations, figures, tables, experiment provenance, limitations,
and regenerated results without making publication a prerequisite for ordinary
engineering work.

<!-- MarkdownLint-disable-next-line MD013 MD044 -->
[docs/todo/open/research/publication-grade-paper-pipeline.mdc](docs/todo/open/research/publication-grade-paper-pipeline.mdc)
