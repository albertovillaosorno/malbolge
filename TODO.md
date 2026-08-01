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
byte streams, strings, allocation, formatting, `libm`, and later higher-level
routines. The contract is deliberately not the host libc ABI: accepted routines
either compile into ordinary guest code or into verified compiler intrinsics with
the same guest-visible semantics. No accepted C program may become dependent on
`msvcrt`, glibc, musl, libSystem, a host math library, or another native runtime
merely because the VM happens to run on that host. Native CLI adapters are
debugging scaffolds only and never count as compiler, lowerability, or conformance
evidence.

### TODO - Guest runtime and allocator

Implement startup, calling convention, frames, allocation, streams, integer
helpers, strings, deterministic math helpers, scheduling primitives, and other
runtime facilities as code that ultimately executes under Malbolge semantics.
Fundamental compiler intrinsics such as byte output require real Malbolge
lowerings. The native CLI adapter may mirror the boundary for debugging but is
not guest-runtime or lowerability evidence. The DOOM interoperability
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
The active `deterministic-corpus-enumeration-v1` strategy searches an explicit
canonically encoded finite corpus under deterministic seed/budget control and
submits every proposal to the trusted verifier. The exact
`classic-crazy-target-search-v1` strategy additionally proves non-invertible,
multi-position search with fixed-accumulator digitwise preimage preparation and
replaceable CPU/CUDA evaluation. Real synthesis generators,
translation-validation integration, AArch64 evidence, and broader cross-device
performance measurement remain open.

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
than admission. `classic-rotate-target-search-v1` runs the same bounded
seed/budget strategy through CPU or live CUDA candidate evaluation. The new
`classic-crazy-target-search-v1` is the first real non-invertible,
multi-position strategy: shared neutral `CRAZY_TRIT_TABLE` semantics derive exact
fixed-accumulator preimage positions before replaceable evaluation. Over the full
59,049-word domain, accumulator zero and target 29,524 retain full membership
while projecting exactly 1,024 candidates. Live CUDA matches CPU and independent
CPU admission remains authoritative. Synthesis, guided/stochastic search, ROCm
work ports, and ROCm VM execution remain open.

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
first concrete CPU-only strategy. `classic-rotate-target-search-v1` binds one
unique-inverse strategy to interchangeable CPU/CUDA evaluators, while
`classic-crazy-target-search-v1` binds exact multiposition preimage preparation to
the same replaceable capacity. Both record configured and actual backend identity
and match CPU proposals before trusted CPU admission. `python -m optimizer.cli`
now loads Search Configuration
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
Retained evidence records warm crossover counts 6/3/2/1 and cold counts
106/38/5/2 across 1/64/1,024/59,049 candidates. At full domain, warm preparation
plus first search is 212.140 ms versus 222.842 ms ordinary, a 10.703 ms one-shot
advantage; cold preparation plus first search is 227.767 ms and crosses on run two.
Incremental traced Python state retains 16.063 MiB and peaks at 19.040 MiB, versus
0.901 MiB of exact reference/device/host buffers. Retained state is 285.249 bytes per
candidate and 71.312x the reference bytes alone. `tracemalloc` excludes the prebuilt
workload, global rotate table, CUDA/native storage, imports, and adapter setup. Component-level tracing identified the historical prepared membership frozenset as
the leading avoidable duplicate: it copied one `(logical_id, payload)` tuple per
candidate in addition to the validated batch. The active
`identity-sorted-candidate-reference-binary-search-v1` index instead retains one
identity-sorted tuple of references to the existing immutable `CandidateWorkItem`
objects. It is proof-bound to the original batch, compares logical ID and payload
exactly, and rejects forged or cross-batch indexes. Generic fabrication checks remain
active. Retained version-2 evidence under
`benchmarks/accelerator/evidence/2026-07-28-compact-membership-crossover-rtx4060/`
compares both membership identities in the same process. At 59,049 candidates the
compact component retains 473,352 bytes versus 5,876,552 bytes for the copied set,
a 91.945% reduction, and prepares in 15.851 ms versus 18.027 ms (1.137x faster).
Complete prepared state falls from 16.063 to 10.910 MiB retained (32.083%) and from
19.040 to 14.080 MiB peak (26.051%). Exact lookup is the retained cost: compact hit
and miss are 2.625/2.785 microseconds versus 0.265/0.201 microseconds, regressions of
9.898x/13.856x. Warm crossover is 7/3/2/1 and cold crossover 108/38/5/1; the
full-domain warm route saves 15.458 ms on its first execution. The compact index is
promoted for scale memory/preparation, not lookup speed. This is the retained
version-2 baseline.
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
representation is promoted because no clean route regresses. Retained version-5 evidence under
`benchmarks/accelerator/evidence/2026-07-28-packed-rotate-batch-builder-crossover-rtx4060/`
promotes `classic-u32le-bitset-first-representatives-v1` with independent
`cpu-scalar-packed-equality-v2`. At 59,049 candidates, cold/warm preparation falls
from 122.990/109.027 ms to 76.130/76.584 ms (1.616x/1.424x), retained state falls
slightly from 713,791 to 710,647 bytes, and peak Python allocation falls from
8,802,328 to 1,183,023 bytes (86.560%). Full-domain crossover remains 1/1. CPU
ordinary/prepared improve from 132.848/3.261 ms to 90.869/3.108 ms
(1.462x/1.049x), while CUDA ordinary improves from 144.440 to 103.562 ms
(1.395x). CUDA prepared throughput is the retained contextual negative at
0.479 versus 0.429 ms (0.896x); the separate prepared CUDA phase total changes
only from 0.2654 to 0.2676 ms (0.992x), so no prepared-execution effect is
attributed to the builder. The fixed bitset raises one-candidate peak from 2,664
to 8,391 bytes and 64-candidate warm crossover from 3 to 4 runs; promotion is for
large deterministic batches, not universal small-batch memory. All builder,
storage, validator, membership, proposal, admission, cardinality, and CPU/CUDA
session proofs pass. Component attribution now places the remaining peak in the
batch builder: it reaches about 1,183,087 bytes while retaining 473,546 bytes as
representative, selected-index, and payload arrays coexist. Retained version-6 evidence under
`benchmarks/accelerator/evidence/2026-07-28-inplace-packed-batch-builder-crossover-rtx4060/`
promotes `classic-u32le-bitset-inplace-first-representatives-v2`. At 59,049
candidates, cold/warm preparation falls from 76.130/76.584 to 64.606/65.101 ms
(1.178x/1.176x), peak Python allocation falls from 1,183,023 to 962,052 bytes
(18.679%), retained state remains 710,647 bytes, and full-domain crossover remains
1/1. CPU/CUDA ordinary routes improve from 90.869/103.562 to 79.943/92.133 ms
(1.137x/1.124x). Prepared controls move in opposite directions: CPU throughput is
3.267 versus 3.108 ms (0.952x), CUDA throughput is 0.385 versus 0.479 ms
(1.245x), and separate CPU/CUDA phase totals are 2.9659/0.2723 ms versus
2.9535/0.2676 ms (0.996x/0.983x). No prepared-execution effect is attributed to
the builder. One-candidate peak stays 8,391 bytes; at 64 candidates peak falls
8,788 to 8,635 bytes while sub-millisecond ordinary timing varies upward; at 1,024
candidates peak falls 22,155 to 19,116 bytes and ordinary CUDA improves. All
builder, storage, validator, membership, proposal, admission, cardinality, and
CPU/CUDA session proofs pass. Component attribution now places the builder phase
near 710,190 bytes peak while retaining 473,546 bytes. The overall ~962 KiB peak
occurs when that retained batch coexists with candidate-state creation (~237 KiB
incremental) or selector creation (~253 KiB incremental). Reducing this post-builder
coexistence without weakening exact reference, selection, membership, or admission
proofs is the next measured boundary.
Retained version-7 evidence under
`benchmarks/accelerator/evidence/2026-07-28-native-view-selector-crossover-rtx4060/`
promotes `classic-u32le-native-view-preimage-v2`. The same-run component
comparison preserves the one exact preimage at all four scales. At 59,049
candidates, selector peak falls from 252,597 to 1,885 bytes (99.254%), while
selector preparation changes from 3.7642 to 3.9644 ms, a retained 5.318%
regression. Complete preparation peak falls from 962,052 to 946,675 bytes
(1.598%); retained state remains 710,647 bytes. Cold/warm preparation changes
from 64.606/65.101 to 64.465/64.780 ms and full-domain crossover remains 1/1.
At one candidate, the native selector retains 56 bytes more and peaks 240 bytes
higher; total one- and 64-candidate peaks are unchanged. CUDA ordinary, fresh
build, and reuse timings remain contextual controls because selector preparation
is outside execution intervals. Candidate-state creation, approximately 237 KiB
incremental beside the retained batch, is the next measured preparation-memory
boundary; exact reference, selection, membership, proposal, and admission proofs
remain mandatory.
Retained version-8 evidence under
`benchmarks/accelerator/evidence/2026-07-28-projected-prepared-rotate-crossover-rtx4060/`
promotes selection-aware exact projection under
`classic-rotate-preimage-projection-v1`. Generic evaluated search prepares the
selector proof first, requires the projected sub-batch to preserve evaluator
identity and exact full-batch membership, binds projection callbacks into strategy
identity, and validates backend evidence against only that sub-batch. Proposal
membership and trusted admission still use all 59,049 evaluated candidates. The
classic rotate inverse has zero or one exact preimage, so the canonical full-domain
prepared state retains one reference word, one selected position, and one resident
CPU/CUDA word while full membership remains 59,049. Empty projections skip backend
execution; wrong evaluator, fabricated member, oversized projection, forged proof,
wrong evidence, and fabricated proposal still fail closed. Against the immediate
clean version-7 baseline, cold/warm preparation improves from 64.4648/64.7804 ms to
46.2706/46.6161 ms (1.393x/1.390x), retained state falls from 710,647 to 475,010
bytes (33.158%), peak allocation falls from 946,675 to 710,126 bytes (24.987%),
and crossover remains 1/1. CPU prepared throughput improves from 3.2402 to 0.0787
ms (41.172x), while CUDA prepared improves from 0.5116 to 0.2743 ms (1.865x).
Prepared backend-phase speedups are 218.4x CPU and 2.366x CUDA; total prepared-phase
speedups are 52.8x and 1.914x. Ordinary CPU/CUDA changes are contextual controls and
are not attributed to projection. Projection is not universal tiny-batch policy: at
one candidate retained state rises from 1,863 to 2,349 bytes and cold/warm crossover
moves from 6/6 to 8/7. The required architectural boundary was an exact projected-subset contract for
strategies without a unique algebraic inverse. The promoted proof retains subset
identity, full membership, exact evidence, proposal validation, and independent
trusted admission rather than introducing heuristic filtering.
Retained version-9 evidence under
`benchmarks/accelerator/evidence/2026-07-28-exact-candidate-subset-crossover-rtx4060/`
promotes neutral `request-order-position-subset-v1` and rotate projection
`classic-rotate-preimage-position-subset-v2`. The proof binds immutable, strictly
increasing request-order positions to the exact full-batch object; empty, one-item,
and multi-item subsets are supported. Mutable, duplicate, reordered, out-of-range,
forged, wrong-type, and cross-batch state fail closed. Generic preparation validates
and unwraps the projection once, stores primitive state directly on the repeated hot
path, and retains the exact projected batch beside full membership authority. Formal
`candidate-subset-proof-tradeoff-v1` medians over 59,049 full-batch items compare
legacy membership revalidation with the proof route: 2.3/4.3 microseconds for empty
(0.535x), 20.0/7.5 microseconds for one item (2.667x), 1.0356/0.1581 ms for
64 items (6.550x), and 16.8647/2.5298 ms for 1,024 items (6.666x). The empty
proof adds 144 retained and 64 peak bytes; from one item upward retained memory is
slightly lower and peak memory is equal. Against the immediate clean version-8
baseline, full-domain cold/warm preparation improves from 46.2706/46.6161 ms to
45.7698/46.2938 ms, retained state falls by 32 bytes to 474,978 bytes, peak stays
710,126 bytes, and crossover remains 1/1. One-candidate crossover improves from
8/7 to 7/6, while 1,024 improves from 2/1 to 1/1. CPU prepared isolated throughput
regresses 2.8% (0.0787 to 0.0809 ms) and remains an explicit tradeoff; CPU prepared
phase total is exactly unchanged at 56.4 microseconds. CUDA prepared throughput
improves 0.5% and phase total improves from 141.4 to 141.1 microseconds. The proof
is promoted for exact authority and multi-item scaling, not as an empty-subset
optimization. That production boundary is now implemented by
`classic-crazy-target-search-v1`. Shared neutral `CRAZY_TRIT_TABLE` semantics and
a fixed accumulator derive every exact request-order preimage position before
backend evaluation. For the complete 59,049-word domain with accumulator zero and
target 29,524, full membership remains authoritative while the prepared subset
contains exactly 1,024 positions. Fourteen strategy tests cover format,
deduplication, seed/budget order, empty and forged state, ordinary/prepared
equality, independent admission, and a live RTX 4060 CPU/CUDA match with resident
cardinality 1,024. Three CLI tests cover CPU registration, CUDA registration, and
setup fallback. `classic-crazy-target-search-submission-v1` now retains the exact
full-batch selector/projection proof while submitting the 1,024-position subset
through a candidate ticket. Seven tests cover identity, full-domain and empty CPU
routes, malformed nested evidence/ticket handling, exact live CUDA publication,
and teardown-driven CPU fallback. Retained evidence under `benchmarks/accelerator/evidence/2026-07-29-crazy-target-performance-matrix-rtx4060/`
records CPU ordinary/prepared medians of 368.3588/22.4264 ms (16.425x, 15/15
paired wins), CUDA ordinary/prepared medians of 235.8490/20.3304 ms (11.601x,
15/15 wins), and a 185.7629 ms one-shot CUDA ticket (1.270x over ordinary,
15/15 wins). CUDA prepared is 1.103x faster than CPU prepared and 9.137x faster
than the ticket. Prepared construction is untimed; ticket preparation and cleanup
are timed. No cross-device, compiler, synthesis, kernel-overlap, or independent-
stream claim is made.
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
strict amortization at four scales with all exact proofs. Retained warm crossover
is 6/3/2/1 and cold crossover 106/38/5/2. Full-domain warm one-shot saves 10.703 ms;
cold crosses on run two. Incremental Python state retains/peaks at
16.063/19.040 MiB versus 0.901 MiB exact reference/device/host buffers. Component tracing selected the duplicate prepared membership frozenset for the first
compaction. The active proof-bound index stores sorted references to existing batch
items and uses binary search plus exact payload equality; forged/cross-batch indexes
and fabricated proposals fail closed. Retained version-2 evidence records the
compact component at 473,352 bytes versus 5,876,552 bytes copied (91.945% lower) and
15.851 ms versus 18.027 ms preparation (1.137x faster) at full domain. Complete
prepared state falls 32.083% retained and 26.051% peak. Binary hit/miss lookup is
9.898x/13.856x slower than the copied set, so this is explicitly a scale-memory and
preparation promotion rather than a lookup-speed claim. Warm/cold crossover is
7/3/2/1 and 108/38/5/1. This is the retained version-2 baseline.
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
representation is promoted because no clean route regresses. Retained version-5 evidence under
`benchmarks/accelerator/evidence/2026-07-28-packed-rotate-batch-builder-crossover-rtx4060/`
promotes `classic-u32le-bitset-first-representatives-v1` with independent
`cpu-scalar-packed-equality-v2`. At 59,049 candidates, cold/warm preparation falls
from 122.990/109.027 ms to 76.130/76.584 ms (1.616x/1.424x), retained state falls
slightly from 713,791 to 710,647 bytes, and peak Python allocation falls from
8,802,328 to 1,183,023 bytes (86.560%). Full-domain crossover remains 1/1. CPU
ordinary/prepared improve from 132.848/3.261 ms to 90.869/3.108 ms
(1.462x/1.049x), while CUDA ordinary improves from 144.440 to 103.562 ms
(1.395x). CUDA prepared throughput is the retained contextual negative at
0.479 versus 0.429 ms (0.896x); the separate prepared CUDA phase total changes
only from 0.2654 to 0.2676 ms (0.992x), so no prepared-execution effect is
attributed to the builder. The fixed bitset raises one-candidate peak from 2,664
to 8,391 bytes and 64-candidate warm crossover from 3 to 4 runs; promotion is for
large deterministic batches, not universal small-batch memory. All builder,
storage, validator, membership, proposal, admission, cardinality, and CPU/CUDA
session proofs pass. Component attribution now places the remaining peak in the
batch builder: it reaches about 1,183,087 bytes while retaining 473,546 bytes as
representative, selected-index, and payload arrays coexist. Retained version-6 evidence under
`benchmarks/accelerator/evidence/2026-07-28-inplace-packed-batch-builder-crossover-rtx4060/`
promotes `classic-u32le-bitset-inplace-first-representatives-v2`. At 59,049
candidates, cold/warm preparation falls from 76.130/76.584 to 64.606/65.101 ms
(1.178x/1.176x), peak Python allocation falls from 1,183,023 to 962,052 bytes
(18.679%), retained state remains 710,647 bytes, and full-domain crossover remains
1/1. CPU/CUDA ordinary routes improve from 90.869/103.562 to 79.943/92.133 ms
(1.137x/1.124x). Prepared controls move in opposite directions: CPU throughput is
3.267 versus 3.108 ms (0.952x), CUDA throughput is 0.385 versus 0.479 ms
(1.245x), and separate CPU/CUDA phase totals are 2.9659/0.2723 ms versus
2.9535/0.2676 ms (0.996x/0.983x). No prepared-execution effect is attributed to
the builder. One-candidate peak stays 8,391 bytes; at 64 candidates peak falls
8,788 to 8,635 bytes while sub-millisecond ordinary timing varies upward; at 1,024
candidates peak falls 22,155 to 19,116 bytes and ordinary CUDA improves. All
builder, storage, validator, membership, proposal, admission, cardinality, and
CPU/CUDA session proofs pass. Component attribution now places the builder phase
near 710,190 bytes peak while retaining 473,546 bytes. The overall ~962 KiB peak
occurs when that retained batch coexists with candidate-state creation (~237 KiB
incremental) or selector creation (~253 KiB incremental). Reducing this post-builder
coexistence without weakening exact reference, selection, membership, or admission
proofs is the next measured boundary.
Retained version-7 evidence under
`benchmarks/accelerator/evidence/2026-07-28-native-view-selector-crossover-rtx4060/`
promotes `classic-u32le-native-view-preimage-v2`. The same-run component
comparison preserves the one exact preimage at all four scales. At 59,049
candidates, selector peak falls from 252,597 to 1,885 bytes (99.254%), while
selector preparation changes from 3.7642 to 3.9644 ms, a retained 5.318%
regression. Complete preparation peak falls from 962,052 to 946,675 bytes
(1.598%); retained state remains 710,647 bytes. Cold/warm preparation changes
from 64.606/65.101 to 64.465/64.780 ms and full-domain crossover remains 1/1.
At one candidate, the native selector retains 56 bytes more and peaks 240 bytes
higher; total one- and 64-candidate peaks are unchanged. CUDA ordinary, fresh
build, and reuse timings remain contextual controls because selector preparation
is outside execution intervals. Candidate-state creation, approximately 237 KiB
incremental beside the retained batch, is the next measured preparation-memory
boundary; exact reference, selection, membership, proposal, and admission proofs
remain mandatory.
Retained version-8 evidence under
`benchmarks/accelerator/evidence/2026-07-28-projected-prepared-rotate-crossover-rtx4060/`
promotes selection-aware exact projection under
`classic-rotate-preimage-projection-v1`. Generic evaluated search prepares the
selector proof first, requires the projected sub-batch to preserve evaluator
identity and exact full-batch membership, binds projection callbacks into strategy
identity, and validates backend evidence against only that sub-batch. Proposal
membership and trusted admission still use all 59,049 evaluated candidates. The
classic rotate inverse has zero or one exact preimage, so the canonical full-domain
prepared state retains one reference word, one selected position, and one resident
CPU/CUDA word while full membership remains 59,049. Empty projections skip backend
execution; wrong evaluator, fabricated member, oversized projection, forged proof,
wrong evidence, and fabricated proposal still fail closed. Against the immediate
clean version-7 baseline, cold/warm preparation improves from 64.4648/64.7804 ms to
46.2706/46.6161 ms (1.393x/1.390x), retained state falls from 710,647 to 475,010
bytes (33.158%), peak allocation falls from 946,675 to 710,126 bytes (24.987%),
and crossover remains 1/1. CPU prepared throughput improves from 3.2402 to 0.0787
ms (41.172x), while CUDA prepared improves from 0.5116 to 0.2743 ms (1.865x).
Prepared backend-phase speedups are 218.4x CPU and 2.366x CUDA; total prepared-phase
speedups are 52.8x and 1.914x. Ordinary CPU/CUDA changes are contextual controls and
are not attributed to projection. Projection is not universal tiny-batch policy: at
one candidate retained state rises from 1,863 to 2,349 bytes and cold/warm crossover
moves from 6/6 to 8/7. The required architectural boundary was an exact projected-subset contract for
strategies without a unique algebraic inverse. The promoted proof retains subset
identity, full membership, exact evidence, proposal validation, and independent
trusted admission rather than introducing heuristic filtering.
Retained version-9 evidence under
`benchmarks/accelerator/evidence/2026-07-28-exact-candidate-subset-crossover-rtx4060/`
promotes neutral `request-order-position-subset-v1` and rotate projection
`classic-rotate-preimage-position-subset-v2`. The proof binds immutable, strictly
increasing request-order positions to the exact full-batch object; empty, one-item,
and multi-item subsets are supported. Mutable, duplicate, reordered, out-of-range,
forged, wrong-type, and cross-batch state fail closed. Generic preparation validates
and unwraps the projection once, stores primitive state directly on the repeated hot
path, and retains the exact projected batch beside full membership authority. Formal
`candidate-subset-proof-tradeoff-v1` medians over 59,049 full-batch items compare
legacy membership revalidation with the proof route: 2.3/4.3 microseconds for empty
(0.535x), 20.0/7.5 microseconds for one item (2.667x), 1.0356/0.1581 ms for
64 items (6.550x), and 16.8647/2.5298 ms for 1,024 items (6.666x). The empty
proof adds 144 retained and 64 peak bytes; from one item upward retained memory is
slightly lower and peak memory is equal. Against the immediate clean version-8
baseline, full-domain cold/warm preparation improves from 46.2706/46.6161 ms to
45.7698/46.2938 ms, retained state falls by 32 bytes to 474,978 bytes, peak stays
710,126 bytes, and crossover remains 1/1. One-candidate crossover improves from
8/7 to 7/6, while 1,024 improves from 2/1 to 1/1. CPU prepared isolated throughput
regresses 2.8% (0.0787 to 0.0809 ms) and remains an explicit tradeoff; CPU prepared
phase total is exactly unchanged at 56.4 microseconds. CUDA prepared throughput
improves 0.5% and phase total improves from 141.4 to 141.1 microseconds. The proof
is promoted for exact authority and multi-item scaling, not as an empty-subset
optimization. That production boundary is now implemented by
`classic-crazy-target-search-v1`. Shared neutral `CRAZY_TRIT_TABLE` semantics and
a fixed accumulator derive every exact request-order preimage position before
backend evaluation. For the complete 59,049-word domain with accumulator zero and
target 29,524, full membership remains authoritative while the prepared subset
contains exactly 1,024 positions. Fourteen strategy tests cover format,
deduplication, seed/budget order, empty and forged state, ordinary/prepared
equality, independent admission, and a live RTX 4060 CPU/CUDA match with resident
cardinality 1,024. Three CLI tests cover CPU registration, CUDA registration, and
setup fallback. `classic-crazy-target-search-submission-v1` now retains the exact
full-batch selector/projection proof while submitting the 1,024-position subset
through a candidate ticket. Seven tests cover identity, full-domain and empty CPU
routes, malformed nested evidence/ticket handling, exact live CUDA publication,
and teardown-driven CPU fallback. Retained evidence under `benchmarks/accelerator/evidence/2026-07-29-crazy-target-performance-matrix-rtx4060/`
records CPU ordinary/prepared medians of 368.3588/22.4264 ms (16.425x, 15/15
paired wins), CUDA ordinary/prepared medians of 235.8490/20.3304 ms (11.601x,
15/15 wins), and a 185.7629 ms one-shot CUDA ticket (1.270x over ordinary,
15/15 wins). CUDA prepared is 1.103x faster than CPU prepared and 9.137x faster
than the ticket. Prepared construction is untimed; ticket preparation and cleanup
are timed. No cross-device, compiler, synthesis, kernel-overlap, or independent-
stream claim is made.
Broader
hardware evidence,
synthesis/search algorithms, and ROCm implementations remain open.

### TODO - CUDA Linux runtime and hermetic toolchain

Port the exact CUDA runtime and repository-local native toolchains to Linux
without weakening the current Windows path. The active runtime still uses
`ctypes.WinDLL`, `nvcuda.dll`, a versioned NVRTC `.dll`, and a literal
`.dependencies/cuda/13.3.1/toolkit` root. The tracked CUDA manifest is exact but
only declares `windows-x86_64`; Rust, Jig, LLVM, and Pyright configuration also
retain Windows-specific paths or targets. Completion requires one reviewed
platform loader (`WinDLL`/`.dll` on Windows, `CDLL`/versioned `.so` on Linux),
manifest-selected CUDA release/library identity, native platform toolchains,
fail-closed CPU fallback, Linux x86-64 differential tests, and retained live-device
evidence. The project initializer already creates Windows/POSIX Python launchers
and reports mismatched manifests as unsupported; that diagnostic surface is not a
Linux CUDA support claim.

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
download into final result arrays without redundant packed host staging. Retained snapshot-phase evidence under
`benchmarks/accelerator/evidence/2026-07-28-current-profile-resident-snapshot-phase-profile-rtx4060/`
uses `ProfileSnapshotPhaseProfile` while leaving ordinary `snapshot()` unchanged.
Batches 1/8/32 retain 15 exact samples after one excluded warmup and measure
3.1616/65.7829/271.1391 ms median total. Batch 1 is 96.489% full-memory D-to-H.
Batches 8/32 are 62.419%/63.872% fresh independent Python array allocation and
37.248%/35.962% memory transfer. Decode is at most 0.105%; named coverage is at
least 99.817%. Pinned memory alone is rejected because it does not remove the dominant
fresh-array ownership requirement. Retained caller-owned workspace evidence under
`benchmarks/accelerator/evidence/2026-07-28-current-profile-snapshot-workspace-tradeoff-rtx4060/`
promotes `caller-owned-independent-u32-arrays-v1`. Ordinary resident `snapshot()`
creates fresh independent mutable `array('I')` results at every batch size;
`allocate_snapshot_workspace()` creates explicit arrays once, and workspace
`snapshot()`/`profile_snapshot()` overwrite and return those same arrays by contract.
Forged, resized, duplicate, wrong-type, wrong-count, and closed-session state fails
closed. Clean batches 1/8/32 improve from 8.1785/65.7327/272.1251 ms ordinary to
3.1631/24.6510/100.3275 ms workspace (2.586x/2.667x/2.712x). One-time allocation
is 4.9179/41.3042/173.7859 ms and median-derived strict crossover is 1/2/2
snapshots. Batch-one crossover is marginal: allocation plus one workspace snapshot
is 8.0810 ms versus 8.1785 ms ordinary, so ordinary remains the simpler one-shot
default. Workspace hot paths are 96.485%/99.389%/99.686% full-memory D-to-H and
retain 18.246/145.965/583.859 MiB. Retained bounded host-registration evidence
under `benchmarks/accelerator/evidence/2026-07-28-current-profile-snapshot-host-registration-tradeoff-rtx4060/` promotes `bounded-all-or-pageable-u32-arrays-v1` only for the
explicit workspace. A 256 MiB all-or-none budget registers batches 1/8 and rejects
batch 32 before Driver registration with `budget-exceeded`. Paired pageable/bounded
medians are 3.4229/3.1718 ms (1.079x, 15/15 faster, crossover 2) and
29.5885/26.7148 ms (1.108x, 14/15 faster, crossover 3). Batch 32 remains pageable
at 99.4115/99.9298 ms and receives no speedup claim. Invalid budgets fail closed;
Driver rejection rolls back prior registrations; workspace/session/runtime close
releases every page lock. Ordinary snapshots and default workspaces remain pageable.
Retained streaming evidence under `benchmarks/accelerator/evidence/2026-07-29-current-profile-snapshot-stream-window-tradeoff-rtx4060/` promotes
`caller-owned-windowed-u32-arrays-v1` as an explicit callback-scoped materialization
contract. On exact batch 32, windows 1/8/32 retain 18.246/145.965/583.859 MiB and
emit 32/4/1 ordered callbacks. Windows 1/8 fit the 256 MiB page-lock budget and
measure 97.5194/96.2771 ms versus 99.7597 ms full pageable (1.023x/1.036x), winning
14/15 and 13/15 paired samples while reducing retained host memory 96.875%/75.000%.
Window 8 is 1.013x faster than window 1 but retains eight times more memory, so both
remain explicit choices. Active streams block session mutation and nested streaming;
consumer failure releases locks for exact retry. The CUDA runtime now exposes
`cuda-ordered-registered-dtoh-stream-v1`: an explicitly ordered Driver stream accepts only
buffers registered by the same context, retains each host lifetime until explicit
`wait()`/`close()`, preserves submission order, blocks unregistration while in flight,
and drains streams before host/context teardown. Seven live RTX 4060 tests cover
exact copy, repeated visibility of prior default-stream uploads, same-host ordering,
ownership rejection, explicit close, runtime close, and stable identity.
`caller-owned-double-window-overlap-u32-arrays-v1` now admits two equal registered
banks only when the total host budget and all-or-none registration succeed. It
prefetches the next memory window before the current exact callback and otherwise
uses the same synchronous callback route with an explicit fallback reason. Six live
CUDA tests cover alternating/partial windows, registration-disabled, one-bank, and
Driver-rejection fallback, prefetched consumer failure/retry, and full bank release.
Retained evidence under `benchmarks/accelerator/evidence/2026-07-29-current-profile-snapshot-double-buffer-overlap-rtx4060/` compares
matched registered windows 1/8. Synchronous/overlap medians are
95.2102/94.9084 ms (1.003x, 14/15 paired wins, 0.2647 ms paired-median saving)
and 94.7627/93.6493 ms (1.012x, 15/15 wins, 1.0636 ms saving). Overlap retains
36.491/291.929 MiB versus 18.246/145.965 MiB and has higher one-time allocation,
so it remains an explicit throughput/memory tradeoff rather than a default.
Hardware-neutral candidate lifetime is now active as
`validated-candidate-submission-v1`. One exact batch binds an optional ticket and
deferred CPU reference; `wait()` validates identity/order before publication,
optional fallback occurs only after cleanup, and malformed tickets or cleanup
failure fail closed. Ten neutral tests cover state, idempotence, deferred CPU,
optional success/fallback, malformed ticket/result, close, cached mandatory
failure, and cleanup failure. The layer creates no hidden threads. CUDA now
implements exact crazy/rotate tickets using
`cuda-independent-stream-kernel-launch-v1`: every one-shot ticket creates one
`CU_STREAM_NON_BLOCKING`, retains exact parameter owners and private buffers, waits
only for that stream, and destroys it before publication or fallback. Launch failure
destroys the new stream; synchronization failure still attempts destruction; runtime
teardown drains every outstanding stream. Five deterministic contract tests cover
identity preservation, distinct stream handles, selected-stream synchronization,
launch cleanup, and synchronization-failure cleanup. Seven live RTX 4060 tests cover
rotate, crazy, empty/idempotent, close-before-wait, adapter-close fallback, and two
tickets waited in reverse order; the reverse-wait route also passes 50/50 stress.
Existing `evaluate`/`evaluate_prepared` calls remain synchronous under
`cuda-default-stream-kernel-launch-v1`. Retained evidence under `benchmarks/accelerator/evidence/2026-07-29-independent-ticket-stream-throughput-rtx4060/` compares
sequential submit/wait with submit-all/reverse-wait for identical groups 2/4/8 of
59,049-word CRAZY tickets. Sequential/grouped medians are 2.1745/1.5970 ms
(1.362x), 3.6403/3.0304 ms (1.201x), and 7.5313/5.6971 ms (1.322x); every group wins
15/15 paired samples. Opt-in `cuda-independent-stream-kernel-timeline-v1`
now records one synchronized origin plus start/end CUDA events around the exact
kernel launch in each ticket stream, with no event cost on ordinary tickets. Three
deterministic tests cover origin/order/overlap, active-lifetime rejection, and
launch-failure cleanup; one live RTX 4060 test preserves CPU-equal bytes and ordered
interval publication. Retained evidence under `benchmarks/accelerator/evidence/2026-07-29-independent-ticket-event-timeline-rtx4060/` reuses the exact workload
SHA and records 45 grouped observations plus 210 intervals. Groups 2/4/8 show
significant overlap in 2/15, 8/15, and 15/15 samples; median overlap is
0/0.006144/0.015360 ms, median interval concurrency is 1.000x/1.072x/1.091x, and
maximum observed peak concurrency is 2/3/5. The preregistered group-eight hypothesis
passes. This attributes origin-relative CUDA-event interval overlap, not pure kernel
duration, SM occupancy, or kernel-transfer overlap. Opt-in
`cuda-independent-stream-ticket-transfer-v1` now registers exact input/output host
buffers and enqueues H-to-D, kernel, and D-to-H work on the ticket's same nonblocking
stream. Five deterministic runtime tests cover ordering, leases, and partial-failure
cleanup; four live candidate routes cover no synchronous-copy use, crazy exactness,
reverse waiting, and teardown fallback. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-29-independent-ticket-transfer-throughput-rtx4060/`
compares 14 routes over groups 1/2/4/8. The group-eight hypothesis fails: streamed
grouped reaches 12.0138 ms versus 5.9408 ms synchronous grouped, a 0.494x ratio and
0/15 paired wins, despite improving 1.118x over streamed sequential with 14/15 wins.
Groups two/four similarly reach only 0.436x/0.478x versus synchronous grouped. The
synchronous ticket therefore remains default; streaming remains an exact explicit
experiment. Wall time alone does not attribute physical transfer/kernel overlap.
Opt-in `cuda-independent-stream-ticket-transfer-timeline-v1` now records four
contiguous CUDA events around upload, exact kernel, and download on each
streamed ticket. Three deterministic tests cover phase order, active lifetime,
and failed-kernel cleanup; one live RTX 4060 test preserves CPU-equal output and
monotonic phases. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-29-independent-ticket-transfer-event-timeline-rtx4060/`
contains 45 grouped observations and 210 ticket phase rows. Groups 2/4/8 record
0.000000 ms median transfer/kernel overlap and 0/15 significant samples each, so
the group-eight hypothesis fails. Group-eight upload/kernel/download sums are
0.956352/0.340768/0.588512 ms versus 12.9495 ms wall time; only about 14.6% of
the instrumented wall interval is represented by those summed device phases.
This closes phase attribution for the retained workload, not a universal claim
that CUDA hardware can never overlap transfers and kernels.
Hardware-neutral search lifetime is now active as
`validated-search-submission-v1`. One exact algorithm/problem/seed/budget request
binds an optional ticket and deferred CPU reference. `wait()` validates capability,
algorithm, seed, and proposal budget before publication; optional cleanup precedes
fallback, malformed tickets fail closed, successful waits are idempotent, and
mandatory failures are cached. Ten tests cover the full state/fallback lifetime.
Proposals remain untrusted and only independent admission may accept them.
`classic-rotate-target-search-submission-v1` is now the first concrete search
ticket: full-batch selector/projection proofs survive while only the exact zero-or-
one preimage sub-batch reaches the candidate ticket. Eight tests cover identity,
projected/empty CPU routes, malformed nested evidence/ticket behavior, and three
live RTX 4060 routes: exact one-position publication, empty projection, and CUDA
teardown followed by CPU fallback. No ticket-specific speedup or independent-
stream claim is made. Hardware-neutral optional hint lifetime is now active as
`validated-verification-assist-submission-v1`. Missing or cleanly failed assistance
completes with no hints only after known-ticket cleanup; malformed tickets and
cleanup failure fail closed. Nine tests cover identity, deferred empty completion,
optional success/failures, malformed result/ticket, close, and cached cleanup
failure. `candidate-evidence-verification-submission-v1` is the first concrete
composition: exact evaluator/verifier identity survives across nested candidate
tickets. Seven tests cover CPU evidence, nested protocol failures, verifier
mismatch, and two live RTX 4060 routes for exact CUDA hints and teardown-driven no
hints. Hints remain untrusted and never acquire acceptance authority. The
multiposition crazy-target strategy now also traverses
`classic-crazy-target-search-submission-v1`: the full selector proof survives while
only the exact projected subset enters the nested CPU/CUDA candidate ticket. Seven
tests include live exact publication and teardown fallback. The retained matrix at
`benchmarks/accelerator/evidence/2026-07-29-crazy-target-performance-matrix-rtx4060/` records 16.425x CPU prepared, 11.601x CUDA prepared, and 1.270x
one-shot CUDA-ticket improvements over their same-run ordinary baselines, all with
15/15 paired wins. CUDA prepared remains 9.137x faster than the one-shot ticket.
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
`bounded-ticket-admission-telemetry-v1` keeps a caller-owned positive-capacity
FIFO for completed reports, while
`bounded-ticket-admission-failure-telemetry-v1` keeps an independent FIFO for
failed accelerator attempts.
Completion snapshots expose monotonic sequence IDs, eviction counts,
measured/estimated duration delta, and exact selected-route usage. Failure
snapshots retain only one stable category (`accelerator-unavailable`,
`invalid-input`, `accelerator-execution`, or `accelerator-error`), never exception
text. Malformed input fails before mutation. The completion-only CUDA executor
remains compatible; the explicit attempt executor records exactly one outcome
after planning and re-raises accelerator failures. The ordinary executor remains
unchanged. `ticket-admission-telemetry-document-v1` captures both snapshots as
compact sorted-key schema-v1 JSON. Decoding defaults to a 1 MiB byte limit and
4,096 observations per FIFO, rejects duplicate, unknown, oversized, and
noncanonical input, and restores exact sequence/eviction state. Explicit file
writes use same-directory temporary files and atomic replacement.
`caller-owned-ticket-admission-telemetry-store-v1` defines an explicit
alternate-store port and bounded memory adapter. It defaults to 4,096 unique
schema-v1 documents, 4,096 observations per FIFO, and 16 MiB of canonical
bytes, reuses the established document
fingerprint, and exposes only put/get/remove/snapshot operations. Exact duplicate
puts are idempotent, limits are immutable after construction, snapshots are sorted,
and removal releases exact budgets. Invalid fingerprints/documents, budget overflow,
collisions, or retained decode failure fail closed without partial mutation. It
performs no filesystem I/O, automatic loading, summaries, merges, recommendations,
or admission changes.
`ticket-admission-telemetry-schema-migration-v1` publishes an explicit lossless
1-to-1, 1-to-2, 2-to-1, and 2-to-2 compatibility matrix. Schema-v2 is canonical
sorted JSON wrapping the exact canonical schema-v1 bytes as standard Base64 plus
the required schema-v1 identity and SHA-256 fingerprint. Versioned decoding
defaults to 2 MiB outer bytes, 1 MiB embedded source bytes, and 4,096 observations
per FIFO. Upgrade and downgrade are caller-invoked; schema-v1 bytes remain
unchanged. Schema-v2 adds no telemetry semantics. There is no automatic migration,
file loading, snapshot reinterpretation, merge, recommendation, lineage inference,
or policy change.
`offline-ticket-admission-telemetry-summary-v1` validates one explicit document
and groups retained observations by exact backend, device, workload, and ticket
count. It publishes only integer outcome totals, estimate-comparison counts,
retention ranges, stable failure categories, and sorted selected-evidence
appearances.
`offline-ticket-admission-telemetry-collection-v1` defaults to explicit
4,096-document and 16 MiB canonical-input bounds. It fingerprints canonical bytes
as `ticket-admission-telemetry-document-v1:sha256:<hex>`, counts byte-identical
occurrences once, publishes input/unique/duplicate byte counts, and orders unique
entries by fingerprint. Distinct snapshots remain separate even when contexts or
sequence ranges overlap, and digest collisions fail closed.
`offline-ticket-admission-telemetry-overlap-v1` compares two validated documents
in fingerprint order. Completed and failed reports expose capacity equality,
retained half-open sequence ranges, exact overlap ranges, matching counts, and
conflicting sequence IDs, with explicit empty and no-overlap classifications. An
exact document match is distinct from matching retained observations.
`offline-ticket-admission-telemetry-overlap-index-v1` deduplicates one bounded
collection before comparing every unique pair. It defaults to a 65,536-pair
budget, fails before comparison when that budget is exceeded, orders reports by
fingerprint, and publishes completed/failed counts for all four overlap classes.
Exact duplicates remain collection occurrences and never create pairs.
`offline-ticket-admission-telemetry-overlap-components-v1` selects an undirected
edge only when the two FIFOs contain at least one exact retained match in total and
neither FIFO reports a conflicting sequence ID. It retains isolated unique
documents, fingerprints each component, and publishes member, direct, possible,
and missing edge counts plus a clique flag. A bridged component may include member
pairs with no direct edge, so connectivity is neither pairwise equivalence nor
recorder lineage. Component fingerprint collisions fail closed.
`authenticated-ticket-admission-telemetry-lineage-v1` separately binds one exact
document fingerprint to caller-supplied recorder, completed/failed stream, capture
sequence, key, and optional immediate-predecessor identities. Canonical
HMAC-SHA-256 uses at least 32 caller-owned secret bytes and never persists the
secret. Verification requires the caller's explicit trusted key identity and
secret. Same-sequence forks, adjacent predecessor mismatch, nonadjacent direct
links, MAC mismatch, and fingerprint collisions fail closed. Different recorder or
stream identities remain separate lineages; ordered gaps retain common lineage
without claiming a direct link. The caller owns key legitimacy.
`caller-owned-ticket-admission-telemetry-lineage-trust-v1` builds an explicit
in-memory trust set of at most 256 unique HMAC keys sorted by `key_id`. Each key
owns an inclusive first/optional-last capture sequence window; empty sets trust
nothing. Verification selects the exact key identity and window, and independently
verified canonical materials may be compared across key rotation. Duplicate key
identities, malformed windows, unknown keys, out-of-window captures, and incorrect
secrets fail closed. Secret fields are hidden from representations.
`ticket-admission-telemetry-lineage-trust-manifest-v1` persists only key identities,
opaque key-reference identities, and inclusive capture windows as canonical
secret-free JSON. It defaults to 256 entries and 64 KiB, orders entries by key ID,
publishes a stable SHA-256 fingerprint, and supports only explicit bounded reads or
atomic replacement. Resolution requires exact caller-supplied key/reference
coverage and returns manifest-bound in-memory trust. A resolved secret remains
unverified until an attestation authenticates. Duplicate identities, malformed or
noncanonical JSON, incomplete or excessive coverage, reference mismatch, and
storage failures fail closed.
`explicit-ticket-admission-telemetry-lineage-secret-provider-v1` accepts one
caller-supplied synchronous provider. It validates the manifest and a default
256-request budget before the first call, emits immutable requests in canonical key
order, and accepts only typed `resolved`, `unavailable`, or `failed` results. Each
entry is called exactly once; non-success stops without retry, while repeated
explicit resolution performs a fresh provider walk. Requests expose only manifest,
provider, key/reference, capture-window, and index metadata. Secret bytes remain
hidden and unverified until an attestation authenticates.
`caller-owned-ticket-admission-telemetry-lineage-signature-v1` defines
algorithm-neutral synchronous detached signer and verifier ports. Canonical
attestations bind the exact schema-v1 document fingerprint, algorithm, recorder,
completed/failed streams, capture sequence, public-key ID, SHA-256 of the exact
caller-owned public-key bytes, and optional HMAC or signature predecessor. Signers
return typed `signed`, `unavailable`, or `failed`; verifiers return `verified`,
`invalid`, `unavailable`, or `failed`. Each explicit operation calls its port once
without retry or cache. Verification checks the exact public-key fingerprint before
the port call, then reuses the common verified-lineage comparison for public-key
rotation and an explicit HMAC-to-signature transition. No concrete signature
algorithm, key generation, private-key storage, certificate chain, PKI, trust
discovery, provider lifecycle, or security claim is supplied by this boundary.
`caller-owned-ticket-admission-telemetry-lineage-signature-trust-v1` builds
an explicit in-memory set of at most 256 unique `(algorithm_id, public_key_id)`
pairs sorted by that composite identity. Each entry binds exact public-key bytes,
their required SHA-256 fingerprint, and an inclusive first/optional-last capture
window. Empty sets trust nothing. Verification selects the exact algorithm, key
identity, fingerprint, and capture window before calling the verifier; independently
verified items preserve same-key, public-key rotation, algorithm rotation, ordered
gap, and fork checks. Duplicate identities, malformed windows, invalid key bytes,
fingerprint mismatch, unknown identities, out-of-window captures, and tampered
trust metadata fail closed. Public-key bytes are hidden from representations. No
manifest, provider, certificate, PKI, trust discovery, algorithm selection, or
policy authority is supplied.
`ticket-admission-telemetry-lineage-signature-trust-manifest-v1` persists
algorithm identity, public-key identity, one opaque public-key reference, the
required exact public-key fingerprint, and inclusive capture windows as canonical
key-free JSON. It defaults to 256 entries and 64 KiB, sorts by composite identity,
requires globally unique references, publishes a stable SHA-256 fingerprint, and
supports only explicit bounded reads or atomic replacement. Resolution requires
exact caller-supplied algorithm/key/reference coverage and exact public-key bytes
matching the persisted fingerprint before building manifest-bound in-memory
signature trust. The same public-key ID may exist under distinct algorithms.
Duplicate identities or references, malformed or noncanonical JSON, incomplete or
excessive coverage, reference or fingerprint mismatch, and storage failures fail
closed. No public-key bytes, provider, certificate, PKI, trust discovery, algorithm
selection, or policy authority are supplied.
`explicit-ticket-admission-telemetry-lineage-public-key-provider-v1` accepts one
caller-supplied synchronous provider. It validates the signature trust manifest and
a default 256-request budget before the first call, then emits immutable requests
in canonical `(algorithm_id, public_key_id)` order. Each request carries only the
manifest/provider identities, algorithm/key/reference identities, required exact
public-key fingerprint, capture window, and request index. Providers return typed
`resolved`, `unavailable`, or `failed` results. Each entry is called exactly once;
non-success stops without retry, while repeated explicit resolution performs a
fresh provider walk. Resolved bytes are hidden from representations and must match
the manifest fingerprint before in-memory signature trust is constructed. No
provider discovery, built-in key service, retry, cache, persistence, hidden worker,
certificate validation, PKI, algorithm selection, or policy authority is supplied.
`explicit-async-ticket-admission-telemetry-lineage-public-key-provider-v1`
accepts one caller-supplied async provider and reuses the synchronous request,
result, and resolved-trust contracts. The caller owns and starts the coroutine and
event loop. Manifest, provider identity, and the default 256-request budget are
validated before the first provider await. Requests are awaited sequentially in
canonical `(algorithm_id, public_key_id)` order, with no task creation or hidden
parallelism; each entry is awaited exactly once and repeated explicit resolution
performs a fresh walk. Typed non-success stops without retry. Ordinary provider
exceptions become stable boundary errors without vendor text, while cancellation
propagates to the caller. Exact public-key fingerprints are checked before trust
construction. This sequential port creates no event loop, task, provider session,
concurrency policy, discovery, retry, cache, persistence, certificate validation,
PKI, algorithm selection, or admission authority.
`explicit-async-batch-ticket-admission-telemetry-lineage-public-key-provider-v1`
accepts one caller-supplied async batch provider. Manifest, provider identity, and
the default 256-request budget are validated before the first await. Empty manifests
make no provider call; nonempty manifests produce one immutable batch containing the
full canonical `(algorithm_id, public_key_id)` request tuple and exactly one provider
await. The provider owns all scheduling and may resolve the batch sequentially or
concurrently. The boundary requires one exact positional result tuple with matching
cardinality, validates every shared typed item result, propagates cancellation, and
converts ordinary provider exceptions to stable errors without vendor text. Reversed,
missing, excessive, foreign, nonresolved-with-bytes, or fingerprint-mismatched results
fail closed before trust is returned. This batch port creates no event loop, task,
concurrency implementation, provider session, discovery, retry, cache, persistence,
certificate validation, PKI, algorithm selection, or admission authority.
`explicit-async-session-ticket-admission-telemetry-lineage-public-key-provider-v1`
accepts one caller-supplied async lifecycle port around the batch provider. Manifest,
provider identity, and the default 256-request budget are validated before opening.
Empty manifests perform no lifecycle calls. Nonempty manifests call `open` exactly
once with immutable manifest fingerprint, provider identity, and request count;
typed outcomes are `opened`, `unavailable`, or `failed`, and only `opened` may carry
a hidden callable batch provider. The existing canonical batch boundary then runs
once. Every opened session receives exactly one `close` request with a stable
`completed`, `failed`, or `cancelled` reason; close outcomes are `closed` or
`failed`. Opening exceptions become stable errors without vendor text and opening
cancellation propagates without closing. After opening, failure or cancellation
attempts one close. Cancellation propagates only after successful close; close
failure replaces the preceding outcome and fails closed. No built-in service,
event loop, task, discovery, retry, cache, persistence, certificate validation,
PKI, algorithm selection, or admission authority is supplied.
`bounded-in-memory-ticket-admission-telemetry-lineage-public-key-provider-v1`
implements the synchronous provider port with one caller-owned immutable key tuple.
Construction accepts at most 256 entries, validates canonical provider, algorithm,
key, and reference identities, validates inclusive capture windows, recomputes every
exact public-key SHA-256 fingerprint, rejects duplicate composite identities and
references, and sorts entries by reference identity. Key bytes are hidden from
representations. Every explicit lookup revalidates service identity, count, tuple,
ordering, metadata, and exact key bytes. An absent reference returns typed
`unavailable`; a known reference with different algorithm, key, fingerprint, or
window returns typed `failed`; only an exact request returns `resolved`. Empty
services are valid and resolve nothing. The object is reusable caller-owned memory,
not an automatic or hidden cache. It performs no file, environment, network,
discovery, mutation, retry, persistence, async adaptation, certificate validation,
PKI, algorithm selection, or admission-policy operation.
`bounded-in-memory-async-ticket-admission-telemetry-lineage-public-key-provider-v1`
adapts one exact bounded memory service to the sequential async provider port.
Construction validates the complete wrapped service and retains only its provider
identity, key count, stable adapter identity, and a hidden service reference. Every
await revalidates the adapter binding and the complete memory service before invoking
the synchronous lookup inline. It returns the same typed `resolved`, `unavailable`,
or `failed` outcome and introduces no internal suspension point; the caller-owned
event loop cannot run another task merely because this adapter was awaited. The
existing sequential async boundary still performs manifest preflight, canonical
ordering, fingerprint checks, stable exception wrapping, and trust construction.
Empty manifests perform no lookup, while explicit adapter construction already
validates the service. The adapter creates no event loop, task, sleep, artificial
yield, batch/session lifecycle, file, environment, network, discovery, retry,
persistence, certificate validation, PKI, algorithm selection, or policy operation.
`bounded-memory-async-batch-ticket-admission-telemetry-lineage-public-key-provider-v1`
adapts one exact bounded memory service to the caller-controlled async batch port.
Construction validates the complete wrapped service and a positive request limit of
at most the caller-selected boundary, defaulting to 256. Every await revalidates the
adapter binding and complete memory service, then validates the exact batch request,
nonempty manifest/provider identities, immutable request tuple, configured count,
positional indices, and every item manifest/provider binding. Requests are resolved
inline in tuple order through the synchronous memory service and returned as one
hidden positional result tuple, preserving typed `resolved`, `unavailable`, and
`failed` outcomes. Direct empty batches are valid. The existing batch trust boundary
still performs manifest preflight, one nonempty provider await, exact cardinality and
fingerprint checks, and trust construction; empty manifests make no provider call.
The adapter creates no event loop, task, concurrency, sleep, artificial yield,
session lifecycle, file, environment, network, discovery, retry, persistence,
certificate validation, PKI, algorithm selection, or policy operation.
`memory-async-session-ticket-admission-telemetry-lineage-public-key-provider-v1`
adapts one exact bounded memory service to the explicit async provider-session port.
Construction validates the memory service, builds its bounded inline batch adapter,
and stores only caller-owned serial lifecycle state. `open` and `close` complete
inline without scheduling. One active lifecycle is allowed: an exact nonempty open
request with matching provider identity and bounded request count returns `opened`
with the hidden memory batch adapter; a second or mismatched open returns `failed`
without replacing active state. Close requests require the exact persisted manifest
fingerprint, provider identity, and request count. A mismatch returns `failed` and
retains active state; an exact close returns `closed`, clears the active request,
increments a nonnegative completed-lifecycle count, and permits serial reuse. The
existing session boundary still preflights manifests and budgets, performs no
lifecycle calls for empty manifests, and closes after success or batch failure. The
adapter creates no event loop, task, lock, concurrency, sleep, artificial yield,
file, environment, network, discovery, retry, persistence, certificate validation,
PKI, algorithm selection, or policy operation.
`ticket-admission-telemetry-lineage-public-key-bundle-v1` persists one explicit
bounded public-key service as canonical compact UTF-8 JSON. Unlike the key-free
trust manifest, this separate document intentionally contains public-key bytes as
lowercase hexadecimal. Construction reuses the memory provider to validate exact
bytes, fingerprints, identities, windows, uniqueness, cardinality, and reference
ordering. Encoding uses sorted keys and one trailing newline; decoding requires byte
identity with that canonical encoding, rejects duplicate or unknown JSON keys, and
is bounded by 256 entries and 1 MiB by default. Explicit writes atomically replace
one caller-selected path. Explicit reads consume at most the configured byte limit.
Each explicit load rereads the path, fingerprints canonical bytes, and builds a new
caller-owned memory provider with hidden key material and stable non-key metadata.
There is no path discovery, automatic loading, watch, retained cache, retry, network
fetch, session creation, certificate validation, PKI, algorithm selection, or policy
operation.
`explicit-ticket-admission-telemetry-lineage-public-key-bundle-fetcher-v1`
defines one synchronous transport-neutral fetch boundary. The caller constructs an
exact immutable request binding source identity, resource identity, provider
identity, expected bundle fingerprint, byte limit, and entry limit. All request
metadata and limits are validated before the first transport call. Each invocation
makes exactly one caller-supplied fetcher call and accepts only the exact typed
`fetched`, `unavailable`, or `failed` result enum. Nonfetched results cannot carry
bytes. A fetched result requires exact nonempty bytes within the requested limit,
canonical bundle decoding, a newly materialized caller-owned memory provider, and
exact matches for the expected bundle fingerprint and provider identity. Repeated
explicit invocations call the transport again and retain no cache. The boundary
implements no HTTP, TLS, endpoint discovery, credential handling, redirect, retry,
watch, persistence, certificate validation, PKI, algorithm selection, or policy
operation.
`explicit-async-ticket-admission-telemetry-lineage-public-key-bundle-fetcher-v1`
defines the caller-driven async form of the same transport-neutral boundary. The
caller owns the coroutine and event loop. The exact shared request is completely
validated before the first await, and each invocation awaits the supplied fetcher
exactly once. The shared typed result, bounded canonical decode, fingerprint and
provider bindings, and caller-owned memory-provider materialization remain the
single synchronous source of validation truth. Ordinary fetcher exceptions become
stable async-boundary errors without vendor text, while cancellation propagates
directly. Repeated explicit invocations await the transport again and retain no
cache. The boundary creates no event loop, task, worker, concurrency policy,
endpoint discovery, credential handling, redirect, retry, watch, persistence,
certificate validation, PKI, algorithm selection, or policy operation.
`explicit-https-ticket-admission-telemetry-lineage-public-key-bundle-fetcher-v1`
implements one concrete synchronous stdlib HTTPS GET transport. Its exact immutable
config binds a canonical lowercase ASCII host, TCP port, origin-form target,
source/resource identities, a positive finite timeout capped at 300 seconds, and a
caller-owned `SSLContext`. Build and every use require hostname checking,
`CERT_REQUIRED`, and TLS 1.2 or newer; the module never creates or loads trust roots.
Each invocation revalidates the config and shared fetch request, requires exact
source/resource matches, opens one new `HTTPSConnection` with the same caller
context, sends only `GET` with JSON/identity/close headers and no credentials, and
closes once. Status 200 may return `fetched`; 404 and 410 return `unavailable`; all
other statuses, including redirects, return `failed`. Successful responses require
JSON content type with optional UTF-8 charset, absent or identity content encoding,
an optional canonical positive content length within the request limit, and an exact
nonempty bytes body read with a `max_bytes + 1` bound. Connection, request, response,
body-read, or close failures return typed `failed` without vendor text. There is no
plaintext HTTP, endpoint discovery, credential handling, redirect following, retry,
watch, cache, persistence, hosted-service API, certificate/PKI ownership, algorithm
selection, or policy operation.
`offloaded-async-https-ticket-admission-lineage-public-key-bundle-fetcher-v1`
adapts the exact synchronous HTTPS fetcher to the shared async port through one
caller-supplied offloader. Construction and every call fully revalidate the wrapped
HTTPS fetcher, stable adapter identity, copied fetcher/source/resource bindings, and
callable offloader. The shared request is validated before the first await; a
source/resource mismatch returns typed `failed` without calling the offloader. A
matched request awaits the offloader exactly once with the same exact fetcher and
request. The caller alone decides whether that await runs inline, in a thread,
through an executor, or through another scheduling mechanism. Cancellation
propagates directly. Ordinary offloader exceptions become stable adapter errors
without vendor text. Returned results are revalidated for exact type, enum, payload
presence, exact bytes, nonempty content, and the request byte limit before they reach
the outer async materialization boundary. Repeated calls revalidate and offload
again. The adapter creates no event loop, task, thread, executor, worker, retry,
redirect, cache, trust root, credential, hosted-service policy, algorithm choice, or
admission-policy operation.
`explicit-ticket-admission-lineage-https-authorization-provider-v1`
defines one synchronous caller-owned port for resolving an opaque HTTPS
`Authorization` value. Preflight validates the exact HTTPS fetcher, exact canonical
bundle-fetch request, source/resource binding, canonical authorization-provider
identity, callable provider, and positive byte limit before the provider is called.
The default limit is 4096 ASCII bytes and the supported maximum is 16384. One
immutable request carries only the bundle fingerprint and nonsecret provider,
resource, and source identities. Each successful preflight makes exactly one
provider call. Stable `resolved`, `unavailable`, and `failed` outcomes carry no
vendor text; nonresolved outcomes cannot carry credential text. A resolved value
must be exact nonempty ASCII field text containing only spaces and visible
characters, with no edge spaces and no normalization. The value is hidden from
representations and returned only in caller-owned state with its exact byte count
and the fixed `Authorization` header name. Repeated explicit resolutions call the
provider again. The port does not choose an authorization scheme, inject a header,
open a connection, discover credentials, retry, cache, persist, log values, create
workers, own a hosted-service API, validate certificates, distribute PKI, select a
signature algorithm, or change admission policy.
`authorized-https-ticket-admission-lineage-public-key-bundle-fetcher-v1`
binds one exact synchronous HTTPS fetcher to one exact caller-owned resolved
Authorization value. Construction and every call revalidate the wrapped HTTPS
fetcher, resolved Authorization value, stable adapter identity, copied byte count,
authorization-provider identity, bundle fingerprint, fetch-provider identity, and
source/resource bindings. A request must exactly match the bound bundle fingerprint,
fetch provider, source, and resource; any mismatch returns typed `failed` before a
connection is opened. A matched call opens one connection, sends one `GET` with the
base JSON/identity/close headers plus exactly one unchanged `Authorization` header,
reuses the base response/status/body validation, and closes once. The explicit
adapter may be reused with the same caller-owned authorization object, but it never
calls a credential provider, refreshes credentials, retries, redirects, caches
hidden state, normalizes or selects a scheme, logs credential text, discovers an
endpoint, creates workers, owns a hosted-service API, validates certificates,
distributes PKI, selects a signature algorithm, or changes admission policy.
`offloaded-async-authorized-https-ticket-admission-lineage-key-bundle-fetcher-v1`
adapts one exact authorized synchronous HTTPS fetcher to the shared async fetch port
through one caller-supplied offloader. Construction and every call fully revalidate
the wrapped authorized fetcher, stable adapter identity, copied authorization byte
count, authorization-provider identity, bundle fingerprint, fetch-provider identity,
and source/resource bindings. The shared request is validated before the first
`await`; any fingerprint/provider/source/resource mismatch returns typed `failed`
without invoking the offloader. A matched request awaits the offloader exactly once
with the same exact authorized fetcher and request, then revalidates the exact typed
result and request byte limit. The caller alone decides whether blocking work runs
inline, in a thread, through an executor, or by another scheduling mechanism.
Cancellation propagates directly. Ordinary offloader exceptions become stable
adapter errors without vendor text. Repeated calls offload again but never resolve or
refresh credentials. The adapter creates no event loop, task, thread, executor,
worker, retry, redirect, cache, trust root, credential provider, hosted-service
policy, certificate rule, PKI operation, algorithm choice, or admission-policy
operation.
The built-in public-key implementations are the bounded caller-owned memory
service, its inline sequential and batch async adapters, its serial session
adapter, explicit canonical file bundles, synchronous plus async
transport-neutral fetch ports, a concrete synchronous HTTPS GET adapter,
a caller-offloaded async HTTPS adapter, an explicit Authorization-provider
port, an explicit authorized HTTPS adapter, and a caller-offloaded async
authorized HTTPS adapter. There is no built-in secret provider implementation,
native nonblocking HTTPS client, concrete credential provider, automatic
credential refresh, or hosted key service.
No bundle or session is loaded automatically;
there is no discovery, retry,
retained cache, persistence, automatic trust
loading, snapshot merge, route recommendation, or policy authority. The retained
`rtx4060-full-domain-crazy-ticket-admission-2026-07-29-v1` profile binds the RTX
4060 `sm_89` capability and full-domain CRAZY workload to source commit
`431f542ab6321eeb12b7bcb9195318f25cf376a5`. It admits synchronous groups 2/4/8
and rejects streamed routes 1/2/4/8; a ten-ticket queue therefore selects groups
2+8 at a 7.3271 ms estimated median. The opt-in executor validates the packed
workload SHA-256, reverse-waits each group, restores input order, and closes
every ticket. One thousand one hundred forty
admission/telemetry/persistence/store/migration/summary/collection/overlap/
index/components/lineage/trust/manifest/provider/signature/signature-trust/
signature-manifest/public-key-bundle/public-key-bundle-fetcher/
async-public-key-bundle-fetcher/https-public-key-bundle-fetcher/
async-https-public-key-bundle-fetcher/https-authorization-provider/
authorized-https-public-key-bundle-fetcher/
async-authorized-https-public-key-bundle-fetcher/
public-key-provider/async-public-key-provider/
async-batch-public-key-provider/provider-session/
memory-public-key-provider/memory-async-public-key-provider/
memory-batch-public-key-provider/
memory-session-public-key-provider tests cover fallback,
positive/negative
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
Other CUDA/ROCm strategies, additional device/workload admission profiles, other
callback or kernel workloads, event/timeline controls, concrete public-key
signature algorithms, native async HTTPS public-key transports,
synchronous or async concrete
Authorization providers, hosted-service integrations,
certificates,
PKI/trust distribution, automatic adaptive feedback, and broader live-device
evidence remain open.

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
