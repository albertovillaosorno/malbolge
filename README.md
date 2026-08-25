# Malbolge

> Project started: July 2026.

Malbolge is an experimental C-to-Malbolge compiler, execution system,
verification stack, and reproducible compiler-research laboratory built around
the 1998 Malbolge machine. The human-facing source language is C, and generated
programs use the `.malbolge` extension.

The long-term goal is deliberately unreasonable: compile ordinary deterministic
C to Malbolge, execute it with exact semantics, optimize it aggressively, and
eventually compile the compiler itself into Malbolge. Current unfinished work is
tracked in [TODO.md](TODO.md), with full typed records under `docs/todo/open/`.

## Quick start

Bootstrap from the repository root with an exact Python 3.14.6 host interpreter.
The bootstrap creates ignored local state and provisions the repository-owned
validation environment.

```powershell
$env:PYTHONPATH = "$PWD/src/automation/repository/composition"
py -3.14 -B -m scripts.bootstrap.project
```

```sh
export PYTHONPATH=src/automation/repository/composition
python3.14 -B -m scripts.bootstrap.project
```

Optional CUDA, LLVM, diagnostic-only, and host-specific bootstrap behavior is
documented with the tooling rather than duplicated here. Start with the
[automation README](src/automation/repository/README.md) and the bootstrap
records under `docs/technical/tooling/`.

## What this repository is building

The intended developer-facing path is shown below.

```text
program.c
   |
   v
tools/tidy
   |
   v
c2malbolge
   |
   +--> deterministic C IR
   +--> ternary / guest-runtime IR
   +--> verified optimization and block selection
   +--> address and self-modification layout
   |
   v
program.malbolge
   |
   v
Malbolge VM / optional native execution tiers
```

`tools/tidy` owns the admitted deterministic C surface, and `c2malbolge` owns
lowering for the selected target profile. A clean lowerability verdict followed
by a compiler rejection is a tooling defect, not a user-language feature.

The repository is organized by responsibility rather than implementation
language. Rust, C, C++, CUDA, Python, LaTeX, and Malbolge may coexist when they
serve the same subsystem.

- `src/compiler/` owns frontend, IR, lowering, layout, encoding, and source
  maps.
- `src/runtime/` owns VM and execution behavior.
- `src/optimization/` owns production optimization and accelerator integration.
- `verifier/` owns executable deterministic acceptance mechanisms.
- `src/research/` and `docs/research/` own executable and human research
  records.
- `src/interoperability/` owns historical and external-system boundaries.
- `docs/` owns durable technical, research, legal, and bibliography records.

The current implementation map is maintained under
`docs/technical/architecture/`.

## Semantic authority

Defined and reproducible behavior of Ben Olmstead's original interpreter is the
semantic authority for the frozen `malbolge-1998` profile on its documented
portable domain. Historical undefined behavior and host-specific accidents do
not become modern semantics.

Current Malbolge behavior evolves through explicit versioned target profiles.
The historical contract, modern profile model, and interpreter disagreements are
owned by the
[Malbolge specification](docs/technical/specification/malbolge-1998.md), the
[target-profile contract](docs/technical/specification/target-profile.md), and
the relevant technical ADRs.

The original interpreter remains unchanged at
`src/interoperability/historical-malbolge/adapter-outbound/main.c`. Its legal
and historical boundaries are documented under `docs/legal/` and
`docs/bibliography/specifications-and-standards/malbolge/`.

## Verification boundary

Optimization, search, CUDA kernels, learned guidance, and other large heuristic
components are proposal mechanisms, not semantic authorities. Deterministic
verification decides whether a candidate is accepted.

```text
proposal / search / optimization
              |
              v
      independent verifier
              |
              v
       accepted artifact
```

The trust model is defined by the verification-trust ADR under
`docs/technical/adr/`.
Detailed verifier, fuzzing, differential, static-analysis, and proof-producing
contracts live under `docs/technical/verification/`.

## Execution and optimization

Literal interpretation remains the trusted fallback while optional execution
tiers may add AOT, JIT, guarded specialization, or native backends. Those tiers
must preserve guest-observable behavior and must remain independently
verifiable.

Execution controls and architecture live under
`docs/technical/runtime/execution/`. Accelerator contracts and production
optimizer boundaries live under `docs/technical/integrations/accelerators/` and
`src/optimization/`.

Performance numbers, retained benchmark samples, admission telemetry, trust
material, and provider details stay with their owning evidence or subsystem.
They are intentionally not cataloged in this README.

## Compiler-research laboratory

Malbolge is hostile enough to make compiler algorithms easy to stress, so the
repository also uses it as a research instrument. Genuine research uses a stable
ID mirrored between executable work and a human research record.

```text
docs/research/algorithms/<id>/
src/research/algorithms/domain/algorithms/<id>/
```

The documentation side owns questions, hypotheses, prior work, methods, results,
limitations, and conclusions. The executable side owns experiment configuration,
implementations, tests, verifier integration, and ignored local outputs.

Research methodology, challenge design, lifecycle rules, and publication policy
live under [docs/research/methodology/](docs/research/methodology/). The
[research catalog](docs/research/README.md) is the entry point for active
studies and algorithm records.

## Real-world stress tests

DOOM is an optional interoperability stress test, not the benchmark authority
for the project. It exercises a large real C program while parametric research
challenges remain responsible for scientific algorithm comparison.

Exact generated artifact sizes, hashes, regeneration commands, validation
matrices, and source-use boundaries belong in the
DOOM algorithm record under `src/research/algorithms/`. The repository does not
distribute DOOM source or game data.

## Self-hosting

Self-hosting is a long-term conformance goal rather than a shortcut around
verification. A Malbolge-hosted compiler is accepted only when its output
remains semantically equivalent to the native compiler under the declared
comparison contract.

The staged plan and proof obligations live under
[docs/technical/compiler/self-hosting/](docs/technical/compiler/self-hosting/)
and in the
[self-hosting ADR](docs/technical/adr/self-hosting-as-conformance-goal.md).

## Documentation map

Repository knowledge is split into four authority families. Each family owns its
own decisions and evidence instead of turning the root README into a second
specification.

- [Technical](docs/technical/README.md): architecture, specifications,
  contracts, runtime behavior, compiler behavior, verification, and tooling.
- [Research](docs/research/README.md): questions, methodology, experiments,
  results, algorithm records, and studies.
- [Legal](docs/legal/README.md): source-use analysis, licensing boundaries, and
  dated repository legal records.
- [Bibliography](docs/bibliography/README.md): external source identity,
  provenance, versions, and verification state.

Planning is intentionally separate. [TODO.md](TODO.md) is the compact unfinished
work index, while typed active records live under `docs/todo/open/` and
completed records remain under `docs/todo/completed/`.

## Contributing and validation

Read [AGENTS.md](AGENTS.md) before making repository changes. It is a compact
handoff; owning TODOs, specifications, contracts, and ADRs remain authoritative
when they are more specific.

Run the repository-owned validation required by the work you change. The active
mathematics and research work in particular declares the following gate.

```sh
jig validate --root .
```

Do not weaken semantic verification to make an optimization, benchmark, or
experimental result pass. Bounded evidence must remain visibly bounded.

## Citation and license

Use [`CITATION.cff`](CITATION.cff) for the repository's machine-readable
software citation. Citation-format provenance is documented in the
bibliography rather than duplicated here.

Repository-authored material is available under the MIT License in
[`LICENSE-MIT`](LICENSE-MIT). Historical material and third-party boundaries
keep their own licensing records under [docs/legal/](docs/legal/).

This is an experimental research repository, not a compatibility warranty or
service-level commitment. Planned features are claims about intended work only
when their owning records explicitly say so.
