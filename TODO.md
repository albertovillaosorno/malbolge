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
- The canonical executable guest artifact is `.malbolge`. Compiler IR, compact
  bytecode, JIT IR, and native translations are transient or rebuildable
  implementation state, not required published sidecar formats; in particular,
  a DOOM pipeline does not introduce a persistent `doom.bytecode` artifact.
- Guest C code may not escape the Malbolge semantics by linking to the host's
  native libc. Supported memory/string/library operations and allocation are
  guest-runtime semantics that ultimately lower to Malbolge. Compiler intrinsics
  are legal only when they preserve those semantics without hidden host calls.
- An already generated `.malbolge` program must not require Clang or LLVM at
  execution time. LLVM may participate in compilation, research, or an optional
  native acceleration implementation, but the interpreter-only runtime remains a
  standalone supported execution path.
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
  `out/`, such as `algorithms/doom/quality/out/doom_fixed/`. Every `out/` is reproducible
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
Portable effect IR v1 is now product-owned under `execution/ir/`, and the
verifier/deoptimization research boundary exercises it directly. The first
host-code boundary under `execution/native/` lowers verified-effect-shaped IR to
atomic freestanding C23 candidates and pinned Clang 22.1.8 emits real untrusted
Windows COFF objects for both x86-64 and AArch64. Safe-Rust COFF admission now
checks target ISA, executable/non-writable `.text`, exact entry identity,
self-contained relocations, and absence of undefined host dependencies. This is
structural admission only for Clang output. A separate direct deopt backend now
emits canonical x86-64/AArch64 COFF stubs whose complete bytes are independently
verified: they return guard miss without touching state, providing the first
semantically admitted native artifact and deterministic fallback floor. A second
byte-canonical direct backend now admits the exact initial-halt IR subset and
performs the first native guest-state commit: after zero-state preflight it sets
only termination to halt; misses are atomic. `direct-halt-registers` now extends
that exact template to every 32-bit `A/C/D` combination with zero I/O counters,
still with no memory/I/O effects; independent x86-64/AArch64 object fixtures and
x86 execution cover nontrivial values. Direct-template selection is deterministic:
zero-register halt chooses the smallest specialization, other eligible one-step
halts choose register-bound code, and all remaining IR chooses verified deopt;
unsupported host formats fail explicitly.
General region-effect fast paths, cache/orchestration, executable invocation, and
full AOT/JIT tier selection remain open.

Current implementation foundation: portable effect IR v1, verifier admission,
deterministic deoptimization, canonical native cache identity, and an untrusted
cross-ISA bootstrap object boundary are implemented. Direct x86-64/AArch64
instruction selection, executable-memory integration, durable cache storage, and
tier orchestration remain open.

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
classic or profile-driven VM tasks by explicit logical ID and joins committed
outputs only in that order. Classic 1/2/8-worker full-state fixtures and mixed
2026.1/current profile joins match sequential baselines; logical-layer performance
evidence remains open.

### TODO - Batch VM execution

Execute many independent programs or inputs efficiently on CPU and accelerator
backends for fuzzing, exhaustive verification, synthesis, and search workloads.
The CPU baseline now has deterministic sequential and explicit host-parallel
execution for classic and profile-driven machines through one scheduler. Retained
worker-scaling evidence applies to the classic CPU workload only. Retained
current-profile CUDA evidence now covers complete snapshots and persistent
resident segments. Product backend routes additionally expose input-ordered
execution-origin reports distinguishing accepted backend completions, safe-Rust
fallback, and pre-backend admission rejection; live classic/current CUDA tests
require at least one accepted backend completion. Additional hardware adapters
remain separate accelerator work.

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
facade remains ten-trit. Current-profile tracing is also explicit and
profile-aware; the resident CUDA accelerator now has explicit current-profile
adoption, while compiler/native consumers and product-level accelerator routing
still require profile-driven adoption rather than silent fallback.

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

### TODO - Versioned host-capability call ABI

Generalize the semantic capability-ID pattern proven by the DOOM corpus into the
VM ABI. Keep capability identity separate from transport: define versioning,
argument/result types, pointer/range validation, blocking rules, failure
semantics, capability discovery, and a deterministic call-frame representation
without requiring a literal new Malbolge opcode. Interpreters, JITs, and AOT
runners may lower the same call frame differently, but guest-visible behavior and
validation must agree. The DOOM source ABI currently exercises version-1
external capabilities spanning guest-memory provisioning, diagnostics/exit,
video/input, PCM audio, raw file I/O, UDP transport, monotonic time, guest-directed
mouse capture, and optional language-neutral execution telemetry. Telemetry may
identify C source lines or Malbolge cells/instructions for host presentation, but
must never alter guest-visible behavior.

### TODO - Supported libc contract

Define the guest C library surface: fixed-width integers, memory primitives,
byte streams, strings, allocation, formatting, and later higher-level routines.
The contract is deliberately not the host libc ABI: accepted routines either
compile into ordinary guest code or into verified compiler intrinsics with the
same guest-visible semantics. No accepted C program may become dependent on
`msvcrt`, glibc, musl, libSystem, or another native libc merely because the VM
happens to run on that host.

### TODO - Guest runtime and allocator

Implement startup, calling convention, frames, allocation, streams, integer
helpers, strings, scheduling primitives, and other runtime facilities as code
that ultimately executes under Malbolge semantics. The DOOM interoperability
bootstrap already uses the intended memory shape: the host exposes one stable
guest-memory region and the guest zone allocator owns object allocation inside
it; no host malloc-like service remains. Guest-side formatting likewise owns
fatal-message construction before raw diagnostic bytes cross the host boundary.
The DOOM quality corpus now also carries its deterministic memory/string
runtime, including compiler-synthesized standard memory symbols, and passes the
real guest-C validator without a libc shim. Generalize those primitives into the
reusable guest runtime rather than treating the DOOM-local implementation as the
final shared library. The DOOM corpus now also parses/sequences MIDI and MUS and
synthesizes music into guest-owned PCM, so its host ABI no longer contains a
music decoder/player service. Improve guest synthesis fidelity separately without
weakening that boundary. Raw external effects remain behind a narrow
host-capability boundary rather than growing into a shadow libc or hidden
application runtime.

## Compiler

### TODO - Clang C frontend integration

Use Clang as the build-time C parser, type system, constant evaluator,
source-location provider, and AST frontend instead of building another C parser.
Do not make Clang or LLVM a runtime dependency of already generated `.malbolge`
programs; execution must remain possible with the standalone interpreter and
guest runtime alone.

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

### TODO - Annotated Malbolge source syntax and formatter

Define a non-canonical annotated source form for readable Malbolge without
changing executable byte semantics. Canonical `.malbolge` remains the exact
artifact. Annotated source may use arbitrary ASCII whitespace, deterministic
automatic line wrapping, and full-line `#` comments whose marker is the first
non-whitespace byte followed by horizontal space or tab. Bare hash, hash before a
line ending/end of file, `#X`, and inline hashes remain ordinary code, so every
graphical canonical sequence is representable without escapes. The active
safe-Rust frontend now canonicalizes presentation to exact position-sensitive
bytes, records loaded-position source locations, wraps automatically, and has
explicit classic/facade/current-profile constructors while raw loaders remain
unchanged. Compiler/decompiler C/IR-aligned comments and composed source maps
remain follow-on layout work.

### TODO - State-aware Malbolge linker

Build a linker that composes independently compiled Malbolge blocks while
resolving symbols, addresses, entry/exit machine-state contracts, positional
decode phase, post-instruction encryption phase, and self-modification footprints.
Relocation is valid only when independent verification proves that stitching the
blocks preserves the same guest-visible transition semantics.

### TODO - Compact guest bytecode strategy

Evaluate a VM-inside-Malbolge strategy where large programs are represented as
compact internal bytecode interpreted by a reusable Malbolge runtime when that
reduces code-size explosion or compilation cost. If adopted, the bytecode is
embedded inside the final `.malbolge` program or exists transiently during
compilation/execution; it does not create a required published `*.bytecode`
sidecar and never replaces `.malbolge` as the canonical guest artifact.

### TODO - C-level source mapping and debugging

Generate source maps from Malbolge addresses through lowered IR back to C source
locations. Expose debugging at the C level; keep low-level VM tracing primarily
for implementation and verification.

### TODO - Malbolge decompiler and reverse engineering

Build a profile-explicit reverse-engineering tool that turns valid Malbolge into
readable executable representations without pretending arbitrary self-modifying
programs preserve their original C source. The first active backend emits C23
with caller-owned state/I/O and exact profile metadata; `ctO` currently compiles
warning-clean with pinned Clang 22.1.8 for x86-64 and AArch64, and the x86-64
artifact executes with the same input/output/register/step result as the normative
VM. The general CLI requires an explicit representation, while `museum_convert`
is a separate local-only helper pinned to `malbolge-1998`. A richer reverse-
engineering IR and control-flow/state annotations remain open.

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

Use deterministic property, fuzz/replay, sanitizer, regression, and exhaustive
verification. The active Rust harness now has seed+ordinal replay/shrink, 24
classic-versus-profiled-1998 generated differential cases with full final memory
comparison, exhaustive loader byte/94-phase mutation boundaries, and the existing
exhaustive arithmetic tables. Sanitizers and verifier valid/invalid mutation
campaigns remain open.

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

Create a buildable `math/` specification surface with one shared notation
include. The active framework now covers generic profile-width word/memory,
rotate/crazy, decode/self-modification, I/O/EOF, loading, execution equivalence,
lowering, verification, and cost notation; all nine standalone documents compile
into `.cache/latex/`. Machine-checked correspondence remains a separate task.

### TODO - Machine-checked mathematical correspondence

Connect mathematical specifications to executable evidence. The active
correspondence graph now maps seventeen stable `eq:*` labels from the profile model
to explicit exhaustive, seeded-differential, current-profile, and rejection
fixtures; graph validation fails on orphan equations or stale test functions.
Future implementation-relevant compiler/research equations remain open.

### TODO - Malbolge-specific optimization mathematics

Derive Malbolge-specific optimization mathematics. The active first slice now
formalizes and machine-links classic/profile crazy chunking, decode phase
reduction, and classic rotate lookup; versioned CPU evidence shows 10.43x crazy
and 1.50x rotate median speedups on the recorded host with matching checksums.
Canonical forms, lower bounds, and search-space reductions remain open.
### TODO - Self-modification state-graph optimizer

Model self-modifying execution as verified state graphs. The active first slice
now provides a collision-safe exact classic-state baseline and the first proved
reductions: consumed input-prefix contents may be removed while cursor/suffix
stay exact, and terminated states may retain only profile/output/termination.
The input reduction exhausts all 256 first-byte values; terminal fixtures vary
memory/register/input state. Exact identity also consumes validated current
4,782,969-word checkpoints with collision confirmation; measured medians are
7.19 ms snapshot, 26.24 ms insert, and 30.76 ms replay on the recorded host, so
full copy/hash is rejected as the expected per-step representation. Complete
classic/current instruction-family witnesses now prove each step changes at most
two memory cells. The real trace engine exposes those exact final deltas and
full-memory scans cross-check every address/before/after record. A shared-root
persistent memory now reconstructs every current checkpoint exactly from those
patches and rejects forged `before` values. Depth evidence rejects the linked
chain as a general index: latest hits stay near 18 ns but root misses reach
20751.17 ns at depth 4096, and compaction-only remains multi-microsecond
in the recorded lower-bound model. A four-level 64-way persistent radix now
reconstructs current checkpoints exactly and preserves 4096 distinct overrides
with bounded lookup depth. Post-commit evidence keeps indexed reads near
20--25 ns through 4096 distinct overrides and makes the depth-4096 root fallback
about 1165x faster than the linked chain.
The radix is promoted as the current-profile memory candidate. A lineage-bound
incremental state graph now reconstructs every current checkpoint exactly,
deduplicates replay, rejects foreign roots, and keeps forced digest collisions
separate without full-memory hashing per observation. Post-commit identity
measurement is 535.82 ns new-observe and
406.67 ns replay versus
26.29/30.48 ms for
complete checkpoints in the same run. Append-only output now uses a shared
persistent history with exact byte equality and safe iterative destruction for
65,536-byte fixtures. Post-commit append stays near 108--145 ns through 256 KiB
while the prior vector clone reaches 20.83 microseconds. Persistent output is
promoted. Exact-state region certificates now cross the verifier boundary only
after normative replay confirms exact outcome/traces/exit, and runtime reuse
requires exact entry equality; tampered, mutated, or rejected cases fail closed.
Exact guard hit/miss is 55.51/59.09 ns in
post-commit evidence versus 9.09 ms normative
verification, so reduced guards target broader safe reuse rather than guard
latency. Profile traces now record exact semantic fetch/data/encryption reads
from the real transition engine (at most three per step). Verified regions now
derive read-before-write live-ins from those reads and exact writes: an
irrelevant-memory variant fails exact equality but safely reuses the region,
preserves its irrelevant value, and matches direct VM exit exactly; live-in
changes fail closed. Post-commit evidence measures dependency-guard hit at
106.88 ns and verified shortcut application at 6.88
microseconds versus 889.60 microseconds for the prepared direct VM
region, about 129.36x. Tier selection now also has an executable
deoptimization boundary: guard hits use verified effects, while guard misses run
the normative VM for the same region budget and reconstruct the incremental
lineage from real traces; normative rejection is propagated unchanged. A portable effect-IR v1
research artifact now admits only exact verifier reprojections of profile,
live-ins, budget, outcome, and compact state-changing effects; tampering any
field fails and admitted shortcut/deopt results match the existing region
baseline. Product `execution/ir/` now owns effect IR v1, and
`execution/cache/` binds byte-exact IR to host OS/ISA, backend/native ABI
revisions, and required features with full equality after bucket collisions.
`execution/native/` now lowers those effects into atomic C23 host-code candidates,
pinned Clang emits untrusted x86-64/AArch64 COFF objects, and safe-Rust COFF
parsing closes their object-format dependencies before semantic admission.
Semantic admission now exists only for the canonical direct deopt stub;
accelerated native effect execution, wider-profile geometry, broader
mutation-history collapse,
and end-to-end tier performance remain open.

## Optimization and accelerator architecture

### TODO - Deterministic CPU optimizer

Implement a correct CPU reference optimizer and search engine that works without
a GPU, even when much slower, and acts as the specification-conformant CPU
baseline on both x86-64 and AArch64 hosts for accelerator implementations.
The first active strategy, `deterministic-corpus-enumeration-v1`, searches an
explicit canonically encoded finite corpus under deterministic seed/budget
control and submits every proposal to the trusted verifier. Real synthesis
generators, translation-validation integration, AArch64 evidence, and performance
measurement remain open.

### TODO - Replaceable accelerator boundary

Define a hardware-neutral interface for candidate evaluation, batch VM
execution, search, and verification. Compiler and verifier code must not depend
directly on CUDA APIs. The active first slice now provides an immutable exact
primitive request/result protocol with a mandatory scalar CPU implementation and
optional CUDA implementation for classic `rotate`/`crazy`; malformed requests
fail before backend execution. Rust batch APIs now expose replaceable classic and
profile execution ports with deterministic safe-Rust fallback. Reported routes
now distinguish actual accepted backend completions from safe-Rust fallback and
admission rejection, and live CUDA tests require real backend acceptance rather
than inferring acceleration from configuration alone. Hardware-neutral
candidate-evaluation, search, and verification-assist ports preserve algorithm
identity, seed/budget identity,
CPU fallback, and verifier-only acceptance. Exact classic crazy/rotate candidate
evaluation now exercises the same port through CPU and live CUDA backends. The
same exact evidence can now traverse a verification-assist adapter on live CUDA;
hints remain untrusted and malformed optional evidence becomes no hint rather
than admission. `classic-rotate-target-search-v1` now runs the same bounded
seed/budget strategy through CPU or live CUDA candidate evaluation, records CUDA
as the actual backend, and still requires independent CPU admission. Synthesis,
guided/stochastic search, ROCm work ports, and ROCm VM execution remain open.

### TODO - Configurable accelerator algorithm adapters

Separate optimization/search strategy from accelerator hardware. Define common
algorithm ports for enumerative, stochastic, Monte Carlo, evolutionary, learned,
hybrid, pruning, and future strategies, and let CPU, CUDA, ROCm, or later
hardware adapters provide execution capacity for those strategies. Select
algorithms and hardware through deterministic configuration with optional CLI
overrides, record the exact combination in benchmark evidence, and permit
side-by-side comparison without recompiling or modifying compiler semantics.
The active foundation resolves explicit algorithm/backend bindings with a
mandatory CPU reference, optional preferred backend, deterministic overrides, and
configured-versus-actual execution identity. Search configuration v1 now loads
independent algorithm/backend identities from versioned TOML, rejects unknown or
empty configuration, preserves source identity, and applies explicit overrides
without mutating the base selection. The deterministic corpus enumerator is the
first concrete CPU-only strategy. `classic-rotate-target-search-v1` additionally
binds one exact bounded strategy to interchangeable CPU/CUDA evaluators; live CUDA
records configured and actual backend identity and matches CPU proposals before
trusted CPU admission. `python -m optimizer.cli` now loads Search Configuration
v1 plus canonical problem bytes, applies explicit algorithm/backend overrides,
and emits deterministic JSON with problem SHA-256, configured-versus-actual
backend identity, device metadata, seed/budget, and explicitly untrusted
proposals. CUDA setup failure falls back to the registered CPU reference without
rewriting configured intent; unsupported algorithm/backend pairs still fail
explicitly. The first protocol-compliant side-by-side run over the complete
59,049-word classic domain retains 15 CPU and 15 CUDA samples with identical
proposals and independent CPU admission. CPU median is 401.185 ms and CUDA median
is 412.570 ms on the RTX 4060, so the observed CUDA/CPU ratio is 0.972x and the
speedup hypothesis is rejected for this route. A separate 15-sample phase profile
attributes 97.5% of CPU median total time and 99.5% of CUDA median total time to
named phases. CUDA host-side phases account for about 57.0% of the median while
backend evaluation accounts for about 42.5%; batch construction plus proposal
selection consume about 173.081 ms. `PreparedEvaluatedSearch` now builds and
validates immutable request/batch state once, binds it to the exact algorithm,
batch-builder, and selector identities, and permits the same proof to execute
through CPU or CUDA without rebuilding the corpus. Rotate-target selection now
validates only the target/header instead of materializing all candidates a second
time. The retained four-route comparison records CPU ordinary/prepared medians of
293.564/148.590 ms (1.976x) and CUDA ordinary/prepared medians of
306.872/162.693 ms (1.886x). Prepared CUDA remains about 9.5% slower than prepared
CPU (0.913x CPU-prepared/CUDA-prepared). These are amortized repeated-search
measurements with preparation outside the timed interval. A retained prepared-path
phase profile attributes 79.9% of CPU and 81.2% of CUDA median total time to
backend evaluation, with proposal selection at 19.6% and 18.7%. Proof/result
validation is negligible. `PackedCandidateEvidence` now carries fixed-width opaque
payloads in one byte buffer with logical IDs inherited from validated request
order. Generic item-based adapters remain supported, malformed width/size/mixed
forms fail closed, search consumes packed primitive u32 values without per-item
bytes, and verification-assist materializes objects only when hints are requested.
Retained packed evidence lowers CPU ordinary/prepared medians to
211.693/77.309 ms (1.387x/1.922x versus pre-packed) and CUDA medians to
230.144/91.199 ms (1.333x/1.784x). Packed CUDA prepared remains about 18.0%
slower than packed CPU prepared. The packed phase profile lowers CPU/CUDA backend
evaluation to 53.907/67.202 ms (2.326x/2.058x versus pre-packed) and selection to
22.502/22.288 ms. Prepared search state now optionally carries a validated,
decoded candidate execution state bound to the strategy preparer. Rotate search
stores one hardware-neutral `PrimitiveBatch` during preparation and matching CPU or
CUDA adapters reuse it without revalidating candidate IDs or decoding 59,049
payloads. Forged type/kind/evaluator state and different preparer identity fail
closed. Retained evidence records CPU/CUDA prepared medians of 43.129/57.296 ms,
1.792x/1.592x faster than the packed prepared baseline and 5.234x/4.167x faster
than the same implementation's ordinary routes. Ordinary CPU/CUDA medians regress
6.6%/3.7% because they construct the explicit proof locally; this negative
one-shot result is retained. Backend evaluation falls 2.801x CPU and 2.083x CUDA,
while selection remains essentially unchanged. `PreparedPrimitiveBatch` now seals
validated exact input at the primitive boundary. CPU consumes that proof directly;
CUDA prepared execution retains one proof-bound input/output allocation and rebuilds
only for a different proof identity. Ordinary CUDA remains one-shot. Observable
session counters and both prepared benchmarks require one build, 16 evaluations,
15 reuses, and 59,049 resident rotate words. Retained resident evidence records a
46.232 ms CPU prepared median and 34.132 ms CUDA prepared median: CUDA is 1.355x
faster in the same run and 1.679x faster than its 57.296 ms pre-resident baseline.
Control routes are slower by 14.7% CPU ordinary, 7.2% CPU prepared, and 17.2% CUDA
ordinary, so those changes are retained as run-context noise. The CUDA backend
phase falls from 32.264 to 9.922 ms (3.252x), but complete CUDA phase total changes
from 55.300 to 55.910 ms because proposal selection rises from 22.913 to 46.331 ms.
`PreparedEvaluatedSearch` now builds one immutable exact membership index from the
validated `(logical_id, payload)` pairs. Prepared proposal validation reuses that
index without rebuilding a 59,049-entry dictionary; ordinary execution keeps the
one-shot path. Fabricated payloads still fail closed, and both benchmarks require a
59,049-member index alongside exact CUDA session counters. Retained indexed
evidence records CPU/CUDA prepared medians of 26.797/17.970 ms, improvements of
1.725x/1.899x over the resident baseline; CUDA is 1.491x faster in the same run.
Proposal selection falls from 41.529 to 11.801 ms CPU (3.519x) and from 46.331 to
11.761 ms CUDA (3.939x). Ordinary controls and backend medians also improve, so
cross-run total changes are not attributed solely to the index.
`PreparedProposalSelection` now lets a strategy bind selector state to the same
prepared proof. Rotate target preparation uses the exact inverse of the classic
rotate bijection after pruning, seed rotation, and budget selection, retaining only
evaluated preimage positions. Prepared selection reads and validates evidence only
at those positions; ordinary search keeps the full packed scan. Missing/excluded
preimages, forged state, and nonmatching evidence produce no proposal or fail
closed. Both benchmarks require one prepared position for the canonical workload.
Retained direct-selection evidence records CPU/CUDA prepared medians of
15.266/6.182 ms, improvements of 1.755x/2.907x over indexed membership; CUDA is
2.470x faster in the same run. Selection falls from 11.801 ms to 13.2 us CPU
(894.008x) and from 11.761 ms to 12.4 us CUDA (948.452x). Ordinary controls improve
only 1.022x/1.015x and backend phases only 1.034x/1.035x, strongly bounding
attribution to exact prepared selection. Primitive result validation now checks
both tuple extrema instead of scanning every value in Python, preserving rejection
of negative and above-domain evidence before packing. Retained prepared medians
improve 1.086x CPU and 1.254x CUDA; backend evaluation improves 1.091x/1.330x while
ordinary controls remain nearly flat/slightly slower. Prepared CPU rotate now uses
a full 59,049-entry lookup table generated exactly once from the scalar reference
formula. Ordinary CPU execution remains scalar; an exhaustive full-domain test
matches every prepared result, and both benchmarks require 16 prepared evaluations
plus all 59,049 table entries. Retained CPU prepared median falls from 14.058 to
3.313 ms (4.243x), while CPU backend evaluation falls from 13.190 to 2.906 ms
(4.540x). CPU ordinary remains effectively unchanged at 0.9996x. Same-run CPU
prepared is 1.440x faster than CUDA prepared. `PackedPrimitiveResult` now adds a
canonical u32le byte representation alongside tuple results. CUDA prepared returns
the resident host buffer directly as packed bytes; the neutral bridge still checks
capability, exact byte count, and every word's classic-domain bound before evidence
acceptance. Ordinary CUDA and CPU tuple results remain unchanged. Benchmarks require
16 packed CUDA evaluations plus all existing proofs. Retained CUDA prepared median
falls from 4.769 to 2.036 ms (2.343x), while CUDA backend evaluation falls from
3.868 to 1.802 ms (2.147x). CPU prepared changes only 1.004x to 3.300 ms, and
ordinary controls remain effectively flat/slightly slower. CUDA prepared is 1.621x
faster than same-run CPU. Packed-domain validation now uses
`u32le-broadword-domain-v1`: one repeated mask rejects high 16-bit content, and a
per-lane `0xffff - 59048` addition sets bit 16 exactly for words above the classic
maximum without cross-lane carry. Invalid threshold/high-bit words in first and last
lanes fail closed; descriptive scalar fallback runs only on failure. Benchmarks
require the validator identity alongside every existing proof. Retained CUDA
prepared median falls from 2.036 to 1.175 ms (1.733x), while CUDA backend evaluation
falls from 1.802 to 0.860 ms (2.095x) and CUDA total from 1.824 to 0.886 ms (2.057x).
Same-run CUDA prepared is 2.706x faster than CPU. CPU phase regressions are retained
as controls and are not attributed to this CUDA-targeted change. Public diagnostic
profiles now split resident CUDA launch/synchronization, D-to-H transfer, immutable
byte materialization, and total time from neutral packed contract, mask lookup,
integer decode, high-mask, threshold, diagnostic, result-build, and total phases.
The prepared route now replaces hot-path broadword domain scanning with exact
`cpu-reference-packed-equality-v1`. Preparation computes and retains immutable CPU
truth for every candidate once; ordinary execution continues to use
`u32le-broadword-domain-v1`. Prepared execution validates capability, representation,
and exact count before byte-for-byte equality. First and final in-domain corruption
fail closed with the first differing word reported. Generic prepared-search state
counting exposes and requires all 59,049 reference words, while proposal admission
remains independently trusted. The subphase, throughput, and phase benchmarks now
require both validator identities, reference count, resident/session counters,
membership, selector, and CPU-table proofs. Retained full-domain evidence records
CUDA prepared at 0.488 ms, 2.407x better than broadword validation and 6.786x faster
than same-run CPU prepared. CUDA backend evaluation falls from 0.860 to 0.215 ms
(3.999x), and total falls from 0.886 to 0.238 ms (3.729x). Primitive validation
falls from 0.6558 to 0.0278 ms (23.590x), with exact comparison at 0.0180 ms;
primitive end-to-end falls from 0.8684 to 0.1935 ms (4.488x). Ordinary controls move
about 1.5%, while CPU prepared regresses about 4%, so neither is attributed. The
one-time reference generation and 236,196-byte reference image are excluded from
retained intervals. `search_preparation_crossover.py` now preregisters scales 1, 64,
1,024, and 59,049 with fresh-process cold preparation, warm preparation, incremental
Python memory, ordinary CUDA, fresh resident build, and reused resident execution.
It computes the first strictly profitable run count while preserving validator,
proposal, admission, reference/membership/selector, and CUDA-session proofs.
Post-commit evidence is pending; no exploratory crossover or memory result is
promoted yet.
Synthesis/guided
strategies, resident or
fused search, ROCm search implementations, richer orchestration, and broader
representative comparative evidence remain open.
### TODO - CUDA exact VM adapter

Implement the first GPU adapter with exact discrete Malbolge semantics and
massively parallel independent VM execution for candidate evaluation and test
batches. The active CUDA foundation now runs integer-only classic `rotate` and
`crazy` batches through NVRTC/Driver API and differentially matches the CPU
reference; CUDA 13.3 Update 1 is reproducibly pinned under `.dependencies/cuda/`
from a tracked component/hash manifest. Compact one-step classic CUDA execution
returns `StepTrace`-equivalent projections and is checked by Rust across all
instruction families plus rejection/wrap/alias edges. Resident classic execution
now keeps each complete 59,049-word state on GPU for a bounded multi-step run and
matches normative Rust across every final memory word, registers, I/O,
termination, step count, resumption, and atomic rejection. The same geometry-bound
resident kernel now executes `malbolge-2026.2`; Rust compares eight current cases
across all 4,782,969 final words plus complete observable state. Rust product
batches now route classic and current-profile states through hardware-neutral
backend ports with safe-Rust fallback. Current-profile throughput is now
retained through direct complete-snapshot materialization and persistent sessions.
A hardware-neutral exact-primitive candidate bridge now differentially matches
CPU and live CUDA for classic crazy/rotate batches. Candidate evidence can also
feed verification-assist hints through live CUDA while trusted admission remains
CPU-owned. `classic-rotate-target-search-v1` now supplies a concrete live CUDA
search route over a deterministic 257-word corpus and matches the CPU reference
before independent trusted admission. A retained full-domain comparison over
59,049 candidates records identical accepted proposals but a 401.185 ms CPU
median versus 412.570 ms CUDA median on the RTX 4060 (0.972x CUDA/CPU), rejecting
the speedup hypothesis for this host-heavy search route. The retained phase
profile shows that CUDA host-side phases consume about 57.0% of median total time
and backend evaluation about 42.5%; batch construction plus proposal selection
alone consume about 173.081 ms. Hardware-neutral prepared state is now active:
one CPU-built immutable proof can execute through CPU or CUDA only when algorithm,
batch-builder, and selector identities match exactly. Rotate-target selection no
longer decodes the complete corpus a second time. Retained repeated-search evidence
shows 1.976x CPU and 1.886x CUDA same-backend median improvements, while prepared
CUDA remains about 9.5% slower than prepared CPU. Preparation is outside the timed
interval, so the result is not one-shot latency evidence. The retained prepared
phase profile places 81.2% of CUDA median total time in backend evaluation and
18.7% in proposal selection; proof/result validation is negligible. Fixed-width
packed candidate evidence is now active across CPU/CUDA primitive evaluation and
search, avoiding one `CandidateEvidence` plus bytes allocation per candidate while
preserving request-order identity and verifier-only acceptance. Retained packed
CUDA ordinary/prepared medians are 230.144/91.199 ms, improving 1.333x/1.784x
over the pre-packed routes. Backend evaluation falls from 138.320 to 67.202 ms
(2.058x), while selection falls from 31.912 to 22.288 ms (1.432x). Packed CUDA
remains about 18.0% slower than packed CPU prepared. Prepared rotate state now
moves candidate batch validation and payload decode into one-time strategy
preparation, and the same validated `PrimitiveBatch` crosses matching CPU/CUDA
capacity. Forged or mismatched prepared primitive state fails before backend
execution. Retained CUDA prepared median falls from 91.199 to 57.296 ms (1.592x),
and backend evaluation from 67.202 to 32.264 ms (2.083x). Ordinary CUDA regresses
3.7%, and prepared CUDA remains 32.8% slower than CPU prepared. Prepared CUDA now
retains proof-bound input and output buffers across repeated calls; ordinary CUDA
still allocates/transfers per call. Session counters prove build/reuse identity and
benchmarks fail unless one full-domain session is reused exactly. Retained CUDA
prepared throughput is 34.132 ms, 1.679x faster than the pre-resident baseline and
1.355x faster than same-run CPU prepared. CUDA backend evaluation improves 3.252x,
while complete phase total does not improve because selection rises to 46.331 ms.
Prepared search now reuses one exact immutable membership index across CPU/CUDA
selection, eliminating per-call dictionary reconstruction while preserving payload
membership checks. Benchmarks require 59,049 indexed members; fabricated proposals
fail closed. Retained CUDA prepared throughput reaches 17.970 ms versus 26.797 ms
CPU prepared (1.491x), and CUDA selection improves 3.939x to 11.761 ms. Improved
ordinary/backend controls bound attribution to the direct selection phase. Prepared
rotate search now stores exact preimage positions and reads only their packed
backend evidence, while ordinary search retains the full scan. The canonical
benchmarks require exactly one prepared position plus the existing membership and
resident-session proofs. Retained CUDA prepared throughput reaches 6.182 ms versus
15.266 ms CPU prepared (2.470x), while CUDA selection falls to 12.4 us (948.452x).
Backend evaluation remains 5.239 ms and changes only 1.035x versus the indexed run,
so primitive backend execution now precedes resident or fused evaluation-selection.
Primitive result validation now uses exact minimum/maximum bounds and still rejects
negative or above-domain output before evidence packing. Retained CUDA prepared
median falls from 6.182 to 4.929 ms (1.254x), and backend evaluation from 5.239 to
3.940 ms (1.330x). Prepared CPU rotate now uses an exact full-domain lookup table
while ordinary CPU remains scalar; benchmarks expose table/evaluation proof.
Retained CPU/CUDA prepared medians are 3.313/4.769 ms, making CPU prepared 1.440x
faster in the same run. CUDA backend evaluation changes only 1.018x to 3.868 ms and
remains a contextual control. CUDA prepared now returns canonical packed u32le
words directly after D-to-H transfer, eliminating tuple materialization and
repacking while retaining full bridge validation. Benchmarks require 16 packed
prepared evaluations. Retained CUDA prepared median is 2.036 ms, 2.343x faster
than the CPU-table baseline and 1.621x faster than same-run CPU. CUDA backend
evaluation improves 2.147x to 1.802 ms, while CPU phases change about 0.5%.
Packed-domain validation now uses repeated broadword masks and lane-independent
threshold addition under identity `u32le-broadword-domain-v1`; first/last-lane
threshold and high-bit adversaries fail closed. Retained CUDA prepared median is
1.175 ms (1.733x better), backend evaluation is 0.860 ms (2.095x better), and total
is 0.886 ms (2.057x better). CUDA is 2.706x faster than same-run CPU. Public
resident-CUDA and neutral packed-encoding phase profiles now preserve exact output
while decomposing kernel launch/synchronization, D-to-H transfer, immutable byte
copy, contract, masks, integer decode, high-mask, threshold, diagnostics, and result
construction. Prepared CUDA validation now uses immutable CPU-reference packed equality instead
of repeating broadword domain validation. Preparation retains all 59,049 exact words
outside timed execution; prepared CPU and CUDA results must match them byte for byte
after capability/shape checks. Ordinary CUDA retains broadword validation. The
profiler exposes exact-comparison, contract, result-build, public-layer residuals,
and CUDA phases; throughput/phase profiles require both identities, reference count,
1/16/16/15 session proof, CPU table, membership, and selector proofs. In-domain
first/last corruption fails closed. Retained CUDA prepared search is 0.488 ms
(2.407x better), backend evaluation is 0.215 ms (3.999x better), and total is
0.238 ms (3.729x better). Exact prepared validation is 0.0278 ms, including a
0.0180 ms byte comparison, versus 0.6558 ms broadword validation (23.590x). Primitive
end-to-end improves 4.488x to 0.1935 ms. Reference construction remains untimed and
requires 236,196 bytes here. The active preparation-crossover benchmark now measures
cold/warm preparation, incremental Python memory, fresh resident build, reuse, and
strict amortization at four scales with all exact proofs. Post-commit evidence is
pending before selecting the next memory or orchestration optimization.
Broader
hardware evidence,
synthesis/search algorithms, and ROCm implementations remain open.

### TODO - CUDA superoptimizer

Implement GPU-parallel candidate synthesis, pruning, equivalence testing, cost
evaluation, and verified block stitching.

### TODO - PyTorch search orchestration

Use PyTorch for batched candidate/state representation, experiment
orchestration, and heuristic models where useful while purpose-built kernels
retain exact semantic execution where tensor operations are a poor fit.

### TODO - Adaptive accelerator resource budgeting

Discover available memory and compute resources at runtime and choose batch
size, state layout, caches, and search breadth accordingly. The first active
slice now measures CUDA free/total memory, SM count, and maximum threads/block,
then partitions exact resident classic item bytes below a deterministic reserve
without a fixed device-specific batch ceiling. Synthetic 128 MiB/80 GiB capacity
models are example correctness probes only, not supported-range endpoints. No
artificial VRAM maximum is declared; larger addressable devices increase resident
capacity and are automatically split only at backend representation boundaries.
RTX 4060 classic and current-profile throughput evidence is now retained.
Current-profile shared initialization replicates one host image into private
device states, and persistent scalable sessions avoid repeated full-state
movement between bounded segments. `ProfileMemoryImage` now validates and owns
reusable geometry-bound input once, reducing repeated current-profile validation
to sub-millisecond planning in retained evidence. Direct complete snapshots now
download into final result arrays without redundant packed host staging.
Unavoidable final-array transfer/page commitment and broader live-device evidence
remain open.

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
The first active rule removes only byte-identical pre-identity candidates.
Adversarial fixtures preserve one-byte, prefix, and length differences; a
duplicate-rich fixture reduces eight evaluations to five while an all-unique null
fixture remains four-to-four. The deterministic CPU enumerator now applies the
same stable-first relation before logical candidate identity, preserving the
encoded corpus while spending evaluation budget only on exact representatives.
Stronger equivalence, dominance, heuristics, and preregistered performance
evidence remain open.

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

### TODO - Source-bound diff generator

Implement `algorithms/diff/` as a generic deterministic generator that learns a
source-tree transformation from a local source/oracle pair. Canonical structural
similarity, distributed stable anchors, behavior/compatibility probes, and
threshold source binding admit compatible lineage without reducing identity to a
fragile whole-tree hash. The emitted transformation alone must not be sufficient
to materialize target-only source; wrong/no-source and behavior-only clones fail
closed before target publication. Consumer thresholds are calibrated technical
policy, not legal rules. Generic tests use only repository-owned synthetic trees.
The first two exact consumers are `algorithms/doom/generator/quality.py` and
`algorithms/doom/generator/amalgamate.py`. Compatible/fuzzy emission remains open
as generic research infrastructure.

### TODO - Cross-platform native capability runners

Implement the version-1 host-capability contract for supported 64-bit Windows,
macOS, and Linux runners on x86-64 and AArch64. Keep adapters outside the guest
and require the same `.malbolge` payload and guest-visible behavior on every
runner. The normalized DOOM C corpus already passes the strict freestanding
compile gate on all six target/architecture pairs without OS-selection macros;
the remaining platform work is capability implementation and runtime validation,
not guest-source porting. Runners must not require LLVM or an externally installed
multimedia library merely to execute an already generated program. Replace the
non-executable `cli/adapters/doom/abi.malbolge` and
`cli/adapters/doom/windows.malbolge` scaffolds with compiler-generated, verified
modules. When a `.malbolge` capsule explicitly declares `doom.host.v1`,
`malbolge <artifact.malbolge>` must resolve and load the ABI plus current-platform
adapter automatically; ordinary programs receive no implicit DOOM capabilities.

### TODO - DOOM playable generated-code performance

Optimize lowering, block selection, guest runtime, VM execution, JIT paths, and
accelerator-assisted compilation until the user-supplied DOOM interoperability
pipeline produces a `.malbolge` build that is genuinely interactive and playable
under the modern runtime. The same `.malbolge` payload must be portable across
supported x86-64/AArch64 Windows, macOS, and Linux runners; it must not require
LLVM or the host libc at execution time. A redistributable self-contained test
mode may embed Freedoom asset bytes into the guest/data image, while user-owned
commercial IWADs remain external host-provided data. Any compact bytecode or
native translation used for acceleration is transient/rebuildable execution
state rather than a second required DOOM artifact. Measure compile latency, frame
pacing, input latency, VM instructions per game tick, memory footprint, generated
code/data size, and interpreter/AOT/JIT speedups rather than declaring success
merely because the program eventually runs. Preserve the same game semantics
while optimizing; performance-specific substitutions require explicit
equivalence evidence.
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

`examples/museum/` now separates historical provenance from executable product
corpora. It keeps metadata, primary/archived source locations, authorship,
behavior, and locally observed hashes for Cooke's first significant program and
the two historically important Malbolge 99-bottles entries, while intentionally
not vendoring third-party program bytes without explicit redistribution rights.
DOOM, compiler outputs, benchmark algorithms, and generated decompiler views are
outside the museum.
