# Malbolge

> Project started: July 2026.

Malbolge is an experimental C-to-Malbolge compiler, execution system,
verification stack, and reproducible compiler-research laboratory built around
the 1998 Malbolge machine.

The human-facing source language is C. The generated target uses the full
`.malbolge` extension. The long-term objective is deliberately unreasonable:
make ordinary deterministic C programs compile to Malbolge, execute them with
exact semantics, optimize the translation aggressively, and eventually compile
the compiler itself into Malbolge.

## Project status

The repository is currently in the specification, research-design, and
infrastructure phase. The normative 1998 machine specification, documentation
authority model, research methodology, legal boundaries, bibliography baseline,
and 85 typed TODO records exist. The production Rust VM, C VM, C frontend,
compiler backend, optimizer, JIT/AOT engine, and accelerator implementations are
still planned work.

[`TODO.md`](TODO.md) contains unfinished work only. Every TODO heading has one
typed record under [`docs/todo/open/`](docs/todo/). A TODO disappears only after
its contract, implementation or research result, tests, and evidence are
durable.

## Semantic authority

The written 1998 Malbolge specification is the normative definition of the
classic machine. Ben Olmstead's original C interpreter is preserved unchanged
under [`tools/malbolge/main.c`](tools/malbolge/main.c) as historical evidence,
not as semantic authority when it contradicts the specification.

This distinction is intentional. The specification defines `<` as input and `/`
as output, while the historical interpreter implements them in reverse. The
specification also requires immediate termination on a non-graphical executable
cell, while the C implementation can remain stuck without advancing its
pointers. Modern VMs, compilers, verifiers, native backends, and accelerators
follow the specification. A future explicitly named `legacy-ben` mode is kept
only for archaeology and differential diagnosis.

See the specification-authority ADR under `docs/technical/adr/`, the [normative
machine specification][machine-spec], and
`docs/technical/specification/historical-undefined-behavior.md`.

## Target workflow

The intended developer-facing path is:

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
   +--> verified optimizer and block selection
   +--> address and self-modification layout
   |
   v
program.malbolge
   |
   v
Malbolge VM / native execution tiers
```

`tools/tidy` is planned as an out-of-tree clang-tidy plugin. Its central
contract is stronger than ordinary linting:

```text
tools/tidy accepts P
        =>
c2malbolge(P) succeeds for the declared target profile
```

A compiler rejection after a clean lowerability verdict is a tooling defect, not
a user mistake.

## Engineering model

The repository is organized by responsibility, never by implementation language.
Rust, C, C++, CUDA, Python, LaTeX, and Malbolge may live beside one another when
they implement the same capability. Cargo is a build mechanism, not the
architecture, and the project deliberately avoids turning Rust crates into
artificial system boundaries.

The major responsibility surfaces are:

- `compiler/` for frontend, IR, lowering, layout, encoding, and source mapping;
- `vm/` for exact Malbolge state-machine execution;
- `execution/` for optional interpreter, AOT, JIT, deoptimization, and native
  x86-64/AArch64 execution tiers;
- `runtime/` and `libc/` for guest facilities that ultimately execute under
  Malbolge semantics instead of becoming host shortcuts;
- `verifier/` for translation validation, static analysis, differential checks,
  fuzzing, exhaustive checks, and proof material;
- `accelerator/` for CPU, CUDA, ROCm, and other replaceable execution capacity;
- `optimizer/` for optimization responsibilities promoted from verified
  research;
- `algorithms/` for executable research algorithms with mirrored academic
  records under `docs/research/algorithms/`;
- `interop/` for product interoperability engineering such as the optional
  user-supplied DOOM experiment; and
- `tools/` for repository tools including the untouched historical interpreter
  and the planned clang-tidy plugin.

Empty or speculative language-owned roots are not architecture.

## Execution and performance

Literal interpretation remains the trusted fallback, but it is not the only
planned execution strategy. The execution engine may decode Malbolge into a
small internal execution IR, simplify verified state graphs, compile stable
regions ahead of execution, specialize hot mutable regions with guards, and
deoptimize safely to the interpreter when an assumption fails.

Native tiers are optional. The planned controls include `--no-jit`, `--no-aot`,
and `--interpreter-only` so benchmarks can compare pure Malbolge execution,
AOT-only, JIT-only, and fully tiered execution without hidden native-code reuse.

Accelerator hardware and search algorithms are separate ports. CUDA is the first
GPU adapter, not a semantic dependency. The same stochastic, enumerative,
learned, hybrid, or future search algorithm should be runnable on CPU, CUDA,
AMD, or another backend where practical. Resource scheduling is intended to
adapt to the available machine rather than assume one fixed VRAM budget.

## Verification model

Large heuristic components are not trusted merely because they are fast.
Stochastic search, CUDA kernels, learned guidance, state-graph optimization, and
layout solvers may propose candidates; small deterministic verification decides
whether a candidate is admitted.

The repository therefore separates:

```text
proposal / search / optimization
              |
              v
      independent verifier
              |
              v
       accepted artifact
```

The modern Rust VM, independent C VM, bounded exhaustive checks, mathematical
contracts, and the historical interpreter on its documented agreement subset
provide overlapping evidence rather than one monolithic oracle.

## Compiler-research laboratory

Malbolge is intentionally hostile enough to make compiler algorithms easy to
stress. The repository uses that hostility as a research instrument rather than
as an excuse for opaque benchmarks.

Genuine research algorithms use a semantic mirror:

```text
docs/research/algorithms/<id>/
algorithms/<id>/
```

The documentation side records question, hypothesis, prior work, mathematical
model, experiment design, evidence, limitations, and conclusion. The executable
side contains the implementation, verifier boundary, experiment manifest, tests,
and a Git-ignored local `out/` directory.

Ordinary engineering algorithms are not forced into fake papers. For example,
DOOM amalgamation and modernization remain under `interop/algorithms/` because
they are interoperability engineering, not research claims.

Research comparison uses scalable parametric challenge families and
multi-objective evidence instead of one magic score. The intended outputs are
capacity curves and Pareto frontiers over metrics such as time to a verified
solution, generated-code size, runtime instructions, peak RAM/VRAM, verifier
cost, stochastic success probability, and maximum solved difficulty.

Machine-readable challenges are also planned so LLM or compiler agents can
propose algorithms or passes without becoming authorities on correctness:

```text
agent proposes
     |
     v
repository verifier
     |
     v
benchmark arena
     |
     v
reproducible evidence
```

## Research discipline

A polished paragraph is not evidence. Repository research is expected to make
the source trail inspectable: what claim came from which source, what was
verified directly, what remains secondary or unresolved, which sources
contradicted one another, how the contradiction was resolved, and what evidence
was discarded.

This method is adapted from the provenance discipline used in the author's
Ameyalli research repository. Malbolge keeps the structure appropriate to a
software project: canonical external source records live under
`docs/bibliography/`, research conclusions under `docs/research/`, technical
behavior under `docs/technical/`, and legal analysis under `docs/legal/`.

See the source-verification ledger under
`docs/bibliography/provenance-and-methodology/repository/` and the
[scientific-method contract][scientific-method].

## Real-world stress tests

DOOM is an optional interoperability and performance demonstration, not the
scientific benchmark authority. A user may place a lawful source checkout in the
ignored `doom/` input directory. Planned tooling then produces:

```text
user DOOM source
      |
      v
amalgamate.rs
      |
      v
interop/algorithms/out/doom_amalgamated.c
      |
      v
quality.rs
      |
      v
interop/algorithms/out/doom_fixed.c
      |
      v
tools/tidy + c2malbolge
      |
      v
doom.malbolge
```

The repository does not distribute DOOM source or game data. Generated artifacts
retain whatever upstream obligations apply to their inputs. DOOM exists to prove
that the pipeline can survive a large, old, inconvenient real C codebase; the
parametric benchmark arena exists to distinguish algorithms scientifically.

## Self-hosting

The long-term conformance goal is:

```text
c2malbolge.c
    |
    v
c2malbolge.malbolge
    |
    v
compile another C program
    |
    v
new .malbolge artifact
```

A self-hosted compiler is accepted only if native and Malbolge-hosted
compilation remain semantically equivalent under the declared comparison
contract.

## Documentation

Repository knowledge is split into four authority families:

- [`docs/technical/`](docs/technical/) owns architecture, contracts,
  specifications, examples, and implementation-facing behavior;
- [`docs/research/`](docs/research/) owns questions, hypotheses, methodology,
  algorithms, experiments, results, and future papers;
- [`docs/legal/`](docs/legal/) owns dated legal/source-use analysis and
  repository boundaries; and
- [`docs/bibliography/`](docs/bibliography/) owns non-governing external source
  identity, provenance, versions, and verification state.

Each family has its own `adr/` for decisions local to that family. There is no
global `docs/adr/`. [`docs/todo/open/`](docs/todo/) is planning infrastructure
and [`integrations/cspell/`](integrations/cspell/) is validation integration
support; neither is a fifth authority family.

Start with the four documentation-family catalogs:

- [technical catalog](docs/technical/README.md);
- [research catalog](docs/research/README.md);
- [legal catalog](docs/legal/README.md); and
- [bibliography catalog](docs/bibliography/README.md).

## Historical material and license boundary

`tools/malbolge/main.c` is Ben Olmstead's original 1998 interpreter and remains
under its original public-domain dedication. The project does not modify or
relicense that file. Repository-authored wrappers, tests, specifications,
research, compiler code, and other material are MIT licensed unless a narrower
record says otherwise.

The written Malbolge specification and historical interpreter are themselves
historical primary sources. The repository preserves their disagreements rather
than rewriting history to make them look consistent.

See the [Ben Olmstead boundary][ben-boundary], [repository MIT
boundary][mit-boundary], and [legal disclaimer][legal-disclaimer].

## How to cite

A machine-readable [`CITATION.cff`](CITATION.cff) is provided for GitHub and
citation tooling. Its format and provenance are cataloged in
`docs/bibliography/specifications-and-standards/citation-file-format.md`. The
citation date is deliberately frozen at **July 26, 2026**. It is the
repository's stable citation epoch, not a moving "last modified" date. Git
history may continue indefinitely without silently changing the year or date in
citations already used by readers.

```text
Villa Osorno, Alberto. (2026, July 26). Malbolge: C-to-Malbolge compiler and
compiler-algorithm research platform. GitHub.
https://github.com/albertovillaosorno/malbolge
```

Research papers produced from individual algorithm capsules may later define
their own preferred citations without replacing the software citation.

## Maintenance and license

This is an experimental research repository, not a compatibility warranty or
service-level commitment. Planned features are explicitly marked as proposed in
their owning records and must not be inferred to exist from documentation alone.

Repository-authored material is available under the MIT License in
[`LICENSE`](LICENSE). The license applies only to material the repository owner
has authority to license.

[ben-boundary]: docs/legal/licenses/ben-olmstead-malbolge-public-domain.md
[legal-disclaimer]: docs/legal/repository/disclaimer.md
[machine-spec]: docs/technical/specification/malbolge-1998.md
[mit-boundary]: docs/legal/licenses/repository-mit-license-boundary.md
[scientific-method]: docs/research/methodology/scientific-method.md
