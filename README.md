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

The repository now contains an executable and tested foundation rather than
only a design skeleton. Durable work includes interpreter-authority 1998
semantics, classic and scalable-profile Rust VMs, an independent C VM, capsules
and traces,
execution IR, optional native execution tiers, exact CPU/CUDA primitive paths,
resident CUDA classic/profile sessions, validated asynchronous submissions, and
bounded evidence-based accelerator admission.

Repository-root `malbolge.json` selects `malbolge-2026` as the official current
language profile. The published `malbolge-2026.1`, `malbolge-2026.2`, and
`malbolge-2026.3` identities remain immutable compatibility and test evidence;
none replaces the year-only current name.

The CUDA path remains optional and fail-closed. Retained ticket profiles bind to
an exact capability, workload, host/runtime identity, driver API, display-driver
build, NVRTC version, and tracked toolchain manifest. Opt-in admission reports
and bounded completion/failure telemetry explain what ran without changing the
selected route, retaining exception text, or learning new policy online. The two
FIFOs can be captured as canonical bounded JSON and explicitly restored without
automatic loading. `caller-owned-ticket-admission-telemetry-store-v1` adds an
explicit alternate-store port plus a bounded memory adapter. It retains exact
schema-v1 canonical bytes under the established SHA-256 document identity,
defaults
to 4,096 unique documents and 16 MiB, treats exact duplicate puts as idempotent,
and exposes only explicit put/get/remove/snapshot operations. Limits are
immutable,
removal releases budget, snapshots are fingerprint-ordered, and collisions or
corrupted retained bytes fail closed. It performs no filesystem I/O, automatic
loading, summaries, merging, recommendations, or policy changes.
`ticket-admission-telemetry-schema-migration-v1` publishes a fixed lossless
1-to-1, 1-to-2, 2-to-1, and 2-to-2 compatibility matrix. Schema-v2 is canonical
sorted JSON containing the exact canonical schema-v1 bytes as standard Base64,
plus the required schema-v1 document identity and SHA-256 fingerprint. Versioned
decoding defaults to 2 MiB outer bytes, 1 MiB embedded source bytes, and 4,096
observations per FIFO. Upgrade and downgrade are explicit; schema-v1 bytes
remain
unchanged. There is no automatic migration, file loading, snapshot
reinterpretation, merge, recommendation, lineage inference, or policy change.
A deterministic offline summary groups one document by exact
execution context and exposes only integer totals, retention ranges, stable
failure categories, and selected-evidence appearance counts. Explicit document
collections assign canonical SHA-256 identities and deduplicate only
byte-identical
JSON while retaining separate summaries for every distinct snapshot. Collection
limits default to 4,096 documents and 16 MiB of canonical input. A
pairwise report compares completed and failed retained ranges, exact matching
observations, and conflicting sequence IDs without claiming common lineage. A
collection-wide index deduplicates first, rejects more than 65,536 unique pairs
before comparison, orders pair reports by fingerprint, and counts all four
overlap
classifications independently for completed and failed FIFOs. A compatibility
graph selects only nonconflicting pairs with at least one exact retained match,
retains isolated documents, and distinguishes direct cliques from transitive
bridges. Connectivity is not pairwise equivalence or recorder lineage.
`authenticated-ticket-admission-telemetry-lineage-v1` separately binds one exact
document fingerprint to caller-supplied recorder, completed/failed stream,
capture
sequence, key, and optional immediate-predecessor identities with canonical
HMAC-SHA-256. The secret is never stored; verification requires the caller to
select the trusted key identity and provide at least 32 secret bytes. Capture
forks, adjacent predecessor mismatch, and nonadjacent direct links fail closed.
`caller-owned-ticket-admission-telemetry-lineage-trust-v1` adds an explicit
in-memory trust set of at most 256 unique HMAC keys. Keys are selected by exact
identity and inclusive capture-sequence windows, allowing independently verified
comparisons across rotations. Empty sets trust nothing; secrets are not
displayed,
loaded, or persisted.
`ticket-admission-telemetry-lineage-trust-manifest-v1` persists only key
identities,
opaque external reference identities, and inclusive capture windows. Canonical
sorted JSON is bounded to 256 entries and 64 KiB, has a stable SHA-256
fingerprint,
and is read or atomically written only through explicit calls. Secret resolution
requires exact caller-supplied coverage; resolving a reference does not certify
the
secret until an attestation verifies.
`explicit-ticket-admission-telemetry-lineage-secret-provider-v1` accepts one
caller-supplied synchronous provider and validates the manifest plus a default
256-request budget before the first call. It emits immutable requests in
canonical
key order and accepts only typed `resolved`, `unavailable`, or `failed`
outcomes.
Each entry is requested exactly once. There is no discovery, retry, cache,
persistence, provider lifecycle, or hidden worker.

`bounded-in-memory-ticket-admission-telemetry-lineage-secret-provider-v1`
implements one reusable bounded caller-owned synchronous provider over explicit
immutable secret entries. Each hidden key is bound to one canonical manifest
fingerprint, key reference, key identity, and inclusive capture window. The
service
permits 256 entries by default and 4096 at the supported maximum, sorts entries
by
manifest fingerprint and reference, and rejects duplicate manifest/reference
bindings. Construction and every call revalidate the exact service type and
identity, provider identity, configured limit, secret count, entry tuple,
canonical
ordering, shared 32-to-4096-byte key rules, request metadata, and each hidden
key. A
different provider identity returns typed `failed`; an unknown
manifest/reference
returns `unavailable`; a known binding with conflicting key/window metadata
returns
`failed`; and an exact binding returns `resolved` with unchanged hidden bytes.
Request index remains ordering context rather than a secret binding. Repeated
calls
validate and resolve again without mutation or an external cache. The service
reads
no environment, file, network, process credential state, secret store, or hosted
API
and performs no discovery, refresh, retry, persistence, logging, worker
creation,
certificate rule, PKI operation, algorithm choice, or admission-policy
operation.

`explicit-async-ticket-admission-telemetry-lineage-secret-provider-v1`
defines one caller-driven sequential async port over the same manifest-bound
requests and typed outcomes. The synchronous port exposes one immutable
nonsecret
preflight, exact request/result validators, one result materializer, and one
final
trust materializer; both routes share those contracts. Manifest validation,
provider identity, and the request budget complete before the first `await`. The
provider is awaited once per entry in canonical order and never concurrently.
Cancellation propagates directly; ordinary provider exceptions become stable
errors
without vendor text; typed non-success stops the walk without retry. Repeated
explicit resolutions await again. The port creates no event loop, task, thread,
executor, worker, cache, lifecycle, discovery, refresh, persistence,
secret-store
access, certificate rule, PKI operation, algorithm choice, or policy operation.
`bounded-in-memory-async-ticket-admission-telemetry-lineage-secret-provider-v1`
adapts one exact bounded memory secret provider to that async port. Construction
and
every call revalidate the adapter identity, hidden wrapped service, provider
identity, secret count, and entry limit. Each await delegates exactly once to
the
synchronous memory lookup and completes inline without an internal suspension or
hidden task. Repeated calls reuse only explicit immutable caller-owned memory
and
validate it again. The adapter reads no environment, file, network, process
credential state, external secret store, or hosted API and adds no retry, cache,
refresh, persistence, logging, worker, certificate, PKI, algorithm, or policy.

`explicit-file-ticket-admission-telemetry-lineage-secret-provider-v1`
implements one bounded read-only provider over caller-supplied absolute
raw-secret
paths. Every hidden path is bound to an exact manifest fingerprint, key
reference,
key identity, and capture window. Construction and validation perform no file
I/O.
A provider mismatch returns typed `failed`; an unknown manifest/reference
returns
`unavailable`; conflicting key/window metadata returns `failed`; all three
outcomes
occur before any open. An exact match opens the selected path once and reads at
most
`max_secret_bytes + 1` bytes. A missing file returns `unavailable`; other read
errors, oversized files, and bytes outside the shared 32-to-4096-byte key
contract
return `failed` without operating-system text. Exact raw bytes, including
trailing
newlines, are preserved. Repeated calls reopen and reread the file, so rotation
is
caller-controlled and no secret cache exists. The provider does not discover
paths,
write files, scan directories, inspect ownership or permissions, validate
symlinks,
decrypt values, create workers, retry, persist, log paths or secrets, choose
algorithms, or change admission policy.

`offloaded-async-file-ticket-admission-telemetry-lineage-secret-provider-v1`
adapts one exact explicit file provider through a caller-supplied async
offloader.
Construction and every call revalidate the adapter identity, hidden wrapped
provider, copied provider identity, secret count, entry and byte limits, and
callable offloader. Each request is fully validated before the first await; a
provider-identity mismatch returns typed `failed` without awaiting. An exact
request awaits the offloader once with the same immutable provider and request.
The caller alone chooses whether that await completes inline, uses a thread or
executor, or suspends by another mechanism. Cancellation propagates directly;
ordinary offloader exceptions become stable adapter errors without vendor text.
Returned results reuse the shared exact type and enum validation; nonresolved
results cannot carry secret bytes, while resolved bytes must use the exact bytes
type and remain within the wrapped provider's 32-to-4096-byte bound. Repeated
calls offload and reread again. The adapter creates no event loop, task, thread,
executor, worker, path discovery, retry, cache, persistence, environment access,
external-store integration, secret logging, algorithm choice, or policy action.

The full developer promise is not complete. Ordinary C-to-Malbolge lowering,
the complete compiler backend, generated `.malbolge` artifacts for general C,
self-hosting, Linux CUDA support, ROCm, and broad cross-device evidence remain
open work. The repository therefore describes implemented behavior and planned
behavior separately.

[`TODO.md`](TODO.md) contains unfinished work only. Its 85 headings each have
one
typed record under [`docs/todo/open/`](docs/todo/open/). A TODO disappears only
after its contract, implementation or research result, tests, and evidence are
durable.

## Initialize a checkout

The repository bootstrap creates ignored local state, provisions the exact
Python 3.14.6 validation environment, and reports the readiness of pinned Rust,
Jig, and CUDA components. Run it from the repository root with an exact Python
3.14.6 host interpreter:

```powershell
py -3.14 -m scripts.bootstrap.project
```

```sh
python3.14 -m scripts.bootstrap.project
```

Use `--skip-python` for diagnostics without installing Python packages, or
`--require-cuda` when a missing or platform-mismatched CUDA bundle must fail the
initialization. Optional native components are never downloaded implicitly.
The current tracked CUDA 13.3.1 manifest and runtime are Windows x86-64 only;
Linux CUDA loading and per-platform hermetic toolchains remain an explicit TODO.

## Semantic authority

Defined and reproducible behavior of Ben Olmstead's original interpreter is the
semantic authority for the frozen `malbolge-1998` profile. The interpreter is
preserved unchanged under
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
[`src/interoperability/historical-malbolge/adapter-outbound/main.c`](src/interoperability/historical-malbolge/adapter-outbound/main.c)
and supplies primary executable evidence.

This choice preserves the historical ecosystem where the prose and interpreter
disagree. Classic `<` writes the low byte of `A`, `/` reads input, and a current
cell outside `33..126` performs bounded non-progress rather than terminating.
Ben Olmstead later described that graphical-range behavior as intended and said
the corresponding defect was in the specification.

The authority is deliberately limited to portable, defined behavior. Historical
C undefined behavior, locale dependence, text-mode translation, and host memory
or integer assumptions are rejected safely or governed by an explicit versioned
profile. `ExecutionMode::Specification` remains available for comparison but is
not the default and is not verifier eligible.

See the interpreter-authority ADR under `docs/technical/adr/`, the [historical
machine contract][machine-spec], the historical C-boundary catalogue, and the
Ben Olmstead interview record under
`docs/bibliography/specifications-and-standards/malbolge/`.

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
- `algorithms/doom/` for the optional user-supplied DOOM interoperability
  suite;
- `examples/` for project-owned examples plus a provenance-only historical
  museum that does not vendor unlicensed third-party programs; and
- `tools/` for repository tools including the untouched historical interpreter,
  guest-C validation, and reverse-engineering/decompilation utilities.

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

Ticket concurrency is conservative: missing or mismatched evidence keeps
singleton synchronous execution. Exact retained profiles may opt into measured
groups, immutable admission reports explain every eligible or rejected route,
and caller-owned bounded telemetry can record completed durations or stable
accelerator-failure categories. Failure observations omit exception text. An
explicit schema-v1 document can atomically persist and restore both bounded
FIFOs;
duplicate, unknown, oversized, or noncanonical input fails closed. Offline
summaries never recommend routes or modify admission. Pairwise, indexed, and
component overlap review never infers common lineage or merges nonidentical
snapshots. A transitive component is only a review aid, not pairwise
equivalence.
Authenticated lineage requires caller-selected trust and still grants no merge,
route, or admission authority. Caller-owned HMAC rotation, secret-free
manifests,
explicit synchronous and sequential async secret-provider ports with bounded
caller-owned memory implementations, detached public-key signer/verifier
ports, bounded in-memory public-key trust, a canonical key-free public-key trust
manifest, explicit synchronous, sequential async, caller-controlled async batch,
and one-use provider-session ports, plus a bounded caller-owned in-memory
synchronous
key service with inline sequential and batch async adapters plus a serial
session
adapter, an explicit canonical file bundle for public-key bytes, synchronous and
async transport-neutral bundle-fetch ports, a concrete synchronous HTTPS GET
adapter, a caller-offloaded async HTTPS adapter, explicit bounded synchronous
and
async Authorization-provider ports, a bounded caller-owned memory Authorization
provider with an inline async adapter, an explicit environment Authorization
provider, an explicit authorized HTTPS adapter, and a caller-offloaded async
authorized HTTPS adapter, a caller-owned alternate telemetry store, and lossless
explicit schema-v1/schema-v2 migration exist. No concrete
public-key signature algorithm, native async file-secret I/O, native
nonblocking HTTPS client, external secret-store credential provider, automatic
credential refresh, hosted key service, certificate-chain or PKI
ownership, automatic discovery, retry, hidden cache, library-owned concurrency,
or
automatic trust loading is supplied.
Observations do not promote routes automatically and never replace retained
benchmark evidence.

Possible future inference integrations include TensorRT, cuDNN frontend, ONNX
Runtime, TensorRT-LLM, and tokenizer/model tooling. They are not current runtime
dependencies, verifier authorities, or evidence that LLM workloads are already
supported. Any such integration must remain optional, version-bound,
replaceable,
and downstream of deterministic validation where correctness is claimed.

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

Ordinary engineering algorithms are not forced into fake papers. Reusable
generator infrastructure and application suites may share `algorithms/` with
research implementations while remaining explicitly outside the academic mirror.
For example, `algorithms/diff/` is generic generation infrastructure and
`algorithms/doom/` is the DOOM application suite.

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

DOOM is an optional interoperability stress test, not the project's scientific
benchmark authority or primary architecture. It demonstrates progress on a
large real C program while the parametric benchmark arena remains responsible
for comparing compiler algorithms scientifically.

The current source-level result is complete:

```text
lawful user DOOM source
      |
      v
source-bound quality transform -> normalized 151-file C tree
      |
      v
source-bound amalgamation transform -> canonical doom.c
      |
      v
future C-to-Malbolge lowering -> doom.malbolge
```

Current durable generated algorithms:

- `src/research/algorithms/composition/algorithms/doom/quality/main.rs`:
  5,228,952 bytes (4.99 MiB),
  SHA-256 `83f9c400ffd7ca17c75cc1cbc7a654794452ef37eac2adbf21af42a335766bd8`;
- `src/research/algorithms/composition/algorithms/doom/amalgamate/main.rs`:
  5,748,320 bytes (5.48 MiB),
  SHA-256 `7bcd19b073c5839c4c9119a0b871e4e4cd6e63dbedeb7571b6099f234e92f439`.

The ignored canonical output is `doom.c`: 2,507,561 bytes (2.39 MiB),
79,336 lines, with SHA-256:

`a7fbecc1a6faba9fb974399d2b1def32c52734f1a557c0d8dbcdbc9357daab80`

It passes the current guest-C profile, a strict
six-target Clang matrix, sanitizer builds, deterministic multi-TU/single-TU
comparison, and native manual play.

That is not yet complete Malbolge compatibility. The remaining work begins at
C-to-Malbolge lowering, capability linking, generation of `doom.malbolge`, and
execution/performance verification under Malbolge semantics.

The repository does not distribute DOOM source or game data. See
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
[`src/research/algorithms/domain/algorithms/doom/README.md`](src/research/algorithms/domain/algorithms/doom/README.md)
for responsibilities,
exact regeneration commands, artifact sizes, and validation evidence.

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
and [`.jig/cspell/`](.jig/cspell/) is validation integration
support; neither is a fifth authority family.

Start with the four documentation-family catalogs:

- [technical catalog](docs/technical/README.md);
- [research catalog](docs/research/README.md);
- [legal catalog](docs/legal/README.md); and
- [bibliography catalog](docs/bibliography/README.md).

## Historical material and license boundary

`src/interoperability/historical-malbolge/adapter-outbound/main.c` is Ben
Olmstead's original 1998 interpreter and remains
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
[`LICENSE-MIT`](LICENSE-MIT). The license applies only to material the
repository owner
has authority to license.

[ben-boundary]: docs/legal/licenses/ben-olmstead-malbolge-public-domain.md
[legal-disclaimer]: docs/legal/repository/disclaimer.md
[machine-spec]: docs/technical/specification/malbolge-1998.md
[mit-boundary]: docs/legal/licenses/repository-mit-license-boundary.md
[scientific-method]: docs/research/methodology/scientific-method.md
