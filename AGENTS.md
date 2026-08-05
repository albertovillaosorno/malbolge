# AGENTS.md

## Purpose

This file is a compact handoff for coding agents working in this repository. It
is not semantic or architectural authority. When this file conflicts with
`TODO.md`, a typed TODO record, an ADR, a technical specification, or a research
record, the owning durable document wins.

Do not copy chat history into the repository. Keep this file free of
credentials,
private machine details, personal paths, tokens, private URLs, or other
sensitive
information.

## Read first

Before changing product code:

1. Read `TODO.md` and the typed TODO that owns the work under `docs/todo/open/`.
2. Read every `contract` and `adr_paths` entry named by that typed TODO.
3. Run `git status --short` and preserve unrelated or concurrent work.
4. Re-run the repository-owned validation commands instead of trusting an old
   chat transcript or a previous agent's claim that a gate is green.

For the first Rust VM slice, the primary authorities are:

- `docs/technical/specification/malbolge-1998.md`
- `docs/technical/runtime/vm/safe-rust-malbolge-vm.md`
- `docs/todo/open/vm/safe-rust-malbolge-vm.mdc`
- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
- `docs/technical/adr/verification-trust-boundary.md`

## Repository model

The repository is organized by responsibility, not by implementation language.
Cargo is a build mechanism and must not create artificial architecture. Keep the
VM under `vm/`; do not move it into a language-shaped path such as
`crates/malbolge-vm/` merely because it is Rust.

Defined and reproducible behavior of Ben Olmstead's original interpreter is
the semantic authority for the frozen `malbolge-1998` historical/conformance
profile. Contradictory prose remains explicit comparison evidence, and
historical C undefined behavior remains outside portable semantics. Current
Malbolge evolves through explicit versioned profiles; do not turn historical
resource ceilings or interpreter defects into permanent current-language
constraints.

Repository-root `malbolge.json` is the target-profile identity authority. Schema
v2 selects the 14-trit `malbolge-2026` profile as current, retains
`malbolge-2026.1`, `malbolge-2026.2`, and `malbolge-2026.3` as immutable
versioned identities,
and preserves `malbolge-1998` as frozen historical conformance. The current
profile uses interpreter-compatible `/` input and `<` output without inheriting
historical undefined behavior or the ten-trit resource ceiling. Validate profile
edits with `python
src/automation/repository/composition/scripts/validate/target_profile.py` and
the Python compatibility tests.
The safe Rust runtime has two explicit interpreters. `Machine` and
`ExecutionMachine` remain classic-capability and preflight against
`safe-rust-classic`; they must never silently execute `malbolge-2026` through
the ten-trit loader. `ProfileMachine` is the normative profile-driven
interpreter
and preflights against `safe-rust-profiled`, currently up to 14 trits and
4,782,969 words. The checked-in Rust descriptors are generated from
`malbolge.json` and must remain byte-exact with the validator renderer.
Profile fingerprints use `malbolge-profile-v1`; profile ID/version/geometry and
semantics are hashed, while registry `kind` is intentionally excluded so a
current-to-versioned transition cannot rewrite historical artifact identity.
The historical Ben Olmstead C interpreter is immutable historical evidence and a
differential oracle only on its documented agreement subset. Do not edit it to
make modern behavior easier to implement.
Version-one extended `.malbolge` capsules use a fixed seven-byte historical
fallback plus a space/tab-only `MALBCAP1` sideband. Modern code must parse and
validate the sideband before payload loading; old tooling sees only the
fallback.
Do not treat the fallback or its isolated H-001 behavior as modern semantics.

Classic self-modification and post-instruction encryption are fundamental guest
semantics. Do not make generated code globally immutable, and do not invent a
parallel or nonlinear classic target as a performance shortcut. Host
parallelism,
JITs, caches, and accelerators are allowed only behind contracts that preserve
the
same observable guest behavior.
Deterministic logical concurrency is host orchestration only: independent
classic
or profile-driven VM requests own disjoint state, explicit `LogicalTaskId` order
controls result/join order, and worker completion order is never semantic. Do
not
add a guest thread model or treat arbitrary shared-effect work as independent by
assertion.

Large or heuristic components are untrusted. CUDA, PyTorch, stochastic search,
learned guidance, superoptimization, and reusable block search may propose code;
independent deterministic verification decides whether that code is accepted.

## Current implementation handoff

The repository contains the first real safe-Rust VM baseline. Its owning TODO
remains open until the complete acceptance evidence is durable. The root
`Cargo.toml` points the library directly at
`src/runtime/virtual-machine/composition/lib.rs`.

Current VM modules include:

- `src/runtime/virtual-machine/contract/word.rs`: ten-trit word domain and
  primitive operations.
- `src/runtime/virtual-machine/domain/memory.rs`: classic 59,049-word memory
  abstraction.
- `src/runtime/virtual-machine/domain/loader.rs`: source validation and
  deterministic memory expansion.
- `src/runtime/virtual-machine/domain/machine.rs`: registers, I/O, termination,
  `step`, and bounded `run`.
- `src/runtime/virtual-machine/composition/lib.rs`: the intentionally small
  public VM surface.

Current VM tests live under `tests/vm/` and cover instruction behavior,
conformance edges, loader behavior, byte I/O, self-encryption, jumps, and
bounded
execution. Treat the tests as evidence, not as authority over the specification.

Important settled VM edges include:

- Output is the accumulator modulo 256.
- The jump instruction updates `C` before post-instruction self-encryption, so
  encryption uses the new `C`.
- When the post-jump `C` points at a non-graphical cell, the modern VM
  terminates
  explicitly before an invalid encryption-table lookup and without partially
  committing an otherwise invalid transition.

Do not mark `Safe Rust Malbolge VM` complete merely because this first slice
passes tests. Its typed TODO still owns tracing, full conformance evidence, and
all remaining acceptance criteria.

## Roadmap decisions already settled

The roadmap intentionally records these decisions:

- Synthesis scaling is an empirical research question. Do not assume the whole
  problem is exponential, linear, or amortized linear before measurements.
- `tools/tidy` guarantees the admitted deterministic/lowerable C surface; it
  does not by itself prove compilation will be cheap. Guest validation is
  explicit/manual, with `doom/` as the sole recursive directory convenience;
  Rust tidy tests are profile-conformance evidence rather than the validator.
- Do not enable repository-wide native clang-format/clang-tidy execution until
  Jig can select authored C independently from immutable historical C and from
  the guest-C compatibility surface. LLVM 22.1.8 remains pinned; use explicit
  formatting where appropriate and
  `src/automation/repository/composition/scripts/validate/main.py` for guest C.
- Reusable blocks must carry state, layout, mutation, target, provenance, cost,
  and verifier evidence before composition is trusted.
- The state-aware linker must verify positional decode, encryption phase,
  entry/exit machine state, relocation, and self-modification footprints.
- A resident compiler may keep source, IR, link plans, and verified artifacts in
  RAM and use a WAL, but text position, equal character counts, regex matches,
  or
  hashes are only lookup accelerators. Semantic dependency analysis controls
  invalidation and reuse.
- Learned or trained search guidance uses versioned verifier-labeled evidence
  and
  remains optional. Training success never replaces verification.
- The DOOM interoperability order is quality/modernization first, then
  deterministic amalgamation. The user-supplied input tree is never modified.

## Language

Use English for source code, identifiers, code comments, technical
documentation,
TODO records, ADRs, specifications, test names, diagnostics, and commit
messages.
The language used to converse with a human operator does not change repository
language or terminology.

## Working rules

Keep changes inside the owning responsibility and avoid opportunistic cleanup.
Never discard unrelated uncommitted work. Do not change
`.jig/lang/python/pytest.ini` or another
concurrently edited configuration merely to make a global gate green unless the
current task explicitly owns that configuration.

Use the repository-pinned Rust toolchain and repository-local Jig installation.
For Rust VM work, the minimum useful checks are formatting, tests, compiler/lint
checks, and Jig validation. Prefer the full repository validation before a
product commit, but report unrelated pre-existing blockers honestly instead of
weakening or bypassing them.

A product commit must not claim more than the evidence demonstrates. Keep TODOs
pending until their implementation, specification, tests, and validation
evidence
are durable enough for the exact TODO heading to disappear without losing
unfinished intent.

## Near-term implementation order

For the safe VM, prefer correctness over optimization:

`Word -> rotate/crazy -> loader -> memory/register state -> single-step ->
self-modification -> byte I/O -> conformance fixtures -> tracing/evidence`.

Do not introduce JIT, CUDA, ROCm, superoptimization, or native-code shortcuts
into
the semantic baseline. First build the small infernal machine correctly; then
accelerate it behind independently verifiable boundaries.
