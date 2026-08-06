# Repository Source Provenance And Verification Status

## Status

Active verification ledger, reviewed 2026-08-05.

## Subject

This ledger records which evidence supports high-impact repository claims, what
was checked directly, which sources disagreed, and what remains unresolved.
Polished prose must never be mistaken for verification.

## Repository Use

The ledger is non-governing. Technical decisions live in `docs/technical/`,
research conclusions in `docs/research/`, and legal analysis in `docs/legal/`.
This file preserves the evidence trail that lets those documents be challenged.

## Provenance

For each material claim, prefer the closest primary or authoritative source.
When sources disagree, record the disagreement and resolve only the question the
evidence supports. Contradictory claims are never averaged into a compromise.

Internal Git commits are provenance for repository decisions, not external
academic authority. They may show when policy changed, but they cannot replace
the historical source, standard, paper, or official documentation that motivated
the change.

## Identity And Version

- Stable identifier: Malbolge repository source verification ledger
- Record owner: Malbolge repository bibliography.
- Governance:
  `docs/bibliography/adr/source-taxonomy-and-citation-provenance.md`.
- Review date: 2026-08-05.
- Git is cataloged separately under `docs/bibliography/tooling/git.md`.

## License Or Terms

This ledger is repository-authored MIT material. External evidence retains its
own copyright, license, publication, and access terms; citation here does not
relicense any external source.

## Evidence

### Current High-Impact Claims

- **Claim:** Defined and reproducible interpreter behavior is authoritative for
  `malbolge-1998`
  - **Evidence:** original interpreter, accepted authority ADR, and VM
    mode tests
  - **Verification state:** accepted and verified

- **Claim:** `malbolge-1998` assigns `<` to output and `/` to input
  - **Evidence:** original interpreter C and canonical target profile
  - **Verification state:** verified directly

- **Claim:** The written prose assigns the two I/O characters oppositely
  - **Evidence:** original written specification
  - **Verification state:** verified comparison evidence

- **Claim:** A non-graphical current cell is bounded non-progress in the
  historical profile
  - **Evidence:** original interpreter C and `tests/vm/modes.rs`
  - **Verification state:** verified portable interpretation

- **Claim:** Historical C undefined behavior is not portable semantics
  - **Evidence:** sanitizer catalogue and accepted authority ADR
  - **Verification state:** accepted boundary

- **Claim:** Classic words are ten trits; memory is 59,049 words
  - **Evidence:** original specification
  - **Verification state:** verified directly

- **Claim:** Ben public-domain dedication
  - **Evidence:** original notices
  - **Verification state:** verified directly

- **Claim:** C is the human-authored application language
  - **Evidence:** repository ADR/contract
  - **Verification state:** accepted decision

- **Claim:** x86-64 and AArch64 are first-class host targets
  - **Evidence:** repository ADR + vendor docs
  - **Verification state:** accepted decision

- **Claim:** CUDA is optional, non-semantic capacity
  - **Evidence:** repository ADR + NVIDIA docs
  - **Verification state:** accepted decision

- **Claim:** ROCm is the AMD GPU runtime adapter identity
  - **Evidence:** repository ADR + AMD docs
  - **Verification state:** accepted decision

- **Claim:** STOKE is stochastic-superoptimization prior work
  - **Evidence:** STOKE paper
  - **Verification state:** verified prior work

- **Claim:** Alive2 is translation-validation prior work
  - **Evidence:** Alive2 sources
  - **Verification state:** verified prior work

- **Claim:** GitHub recognizes root `CITATION.cff` metadata
  - **Evidence:** GitHub + CFF docs
  - **Verification state:** verified

### Specification Versus Interpreter Divergence

The first major contradiction discovered during documentation promotion concerns
I/O. The written prose assigns `<` to input and `/` to output, while the
preserved interpreter implements `<` as output and `/` as input. A second
disagreement concerns non-graphical executable cells: the prose describes
termination, while the interpreter performs no state transition and revisits the
same cell.

The repository resolves portable `malbolge-1998` semantics in favor of defined
and reproducible interpreter behavior. The prose remains explicit comparison
evidence through `ExecutionMode::Specification`; it is not verifier eligible.
Undefined C behavior, host locale and text-mode effects, invalid table accesses,
and accidental memory-model behavior remain outside portable semantics. Modern
implementations bound non-progress and fail safely at undefined boundaries.

The accepted authority is recorded in:

```text
docs/technical/adr/specification-authority-and-malbolge-evolution.md
```

The original interpreter and written specification remain primary evidence for
the underlying disagreement. Git history records repository decisions but does
not replace either historical source.

### Research Prior-Work Verification

The initial compiler-research baseline has direct records for STOKE, Souper,
`egg`, and Alive2. Those records establish that the cited techniques exist and
describe what their authors claim or implement. They do not establish that the
same techniques improve Malbolge compilation.

Every transfer claim remains experimental until a Malbolge research capsule
records a falsifiable hypothesis, baseline, configuration, raw evidence,
verification result, and threats to validity.

### Tooling And Publication Verification

The repository records authoritative references for C, Rust, Python, the Rust
1.97.1 toolchain, Node.js 24.16.0, uv, LLVM/Clang, clang-tidy, pytest, Ruff,
BasedPyright, CUDA, ROCm, PyTorch, x86-64, AArch64, CommonMark, TOML,
LaTeX, Git,
GitHub repository citation metadata, and Citation File Format. Source records
support identity and capabilities without making upstream tools part of runtime
architecture automatically.

### Baseline Coverage

The executable bibliography audit currently validates 47 source/provenance
records, 44 required baseline records, nine exact Python validation packages,
and 17 distinct durable external references. Durable coverage scans source,
manifests, technical and research documentation, completed lifecycle evidence,
generated text artifacts, and Jig configuration. Open TODO records, synthetic
tests, and the repository's own canonical URL are excluded deliberately.

- **Required source class:** Historical Malbolge specification/interpreter
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
  - **Canonical records:** `specifications-and-standards/malbolge/malbolge-1998.md`
  - **State:** covered

- **Required source class:** Programming languages
  - **Canonical records:** `languages/c.md`, `languages/python.md`,
                           `languages/rust.md`
  - **State:** covered

- **Required source class:** Host architectures
  - **Canonical records:** `platforms-and-runtimes/x86-64.md`, `aarch64.md`
  - **State:** covered

- **Required source class:** Compiler/toolchain
  - **Canonical records:** `platforms-and-runtimes/compiler/`,
                           `rust-toolchain-1-97-1.md`,
                           `tooling/clang-tidy.md`
  - **State:** covered

- **Required source class:** Validation host runtime
  - **Canonical records:** `platforms-and-runtimes/nodejs-24-16-0.md`,
                           `tooling/uv.md`
  - **State:** covered

- **Required source class:** Accelerator computing
  - **Canonical records:** CUDA, ROCm, and PyTorch records
  - **State:** covered

- **Required source class:** Superoptimization/synthesis
  - **Canonical records:** STOKE, Souper, and egg records
  - **State:** covered

- **Required source class:** Verification/formal methods
  - **Canonical records:** Alive2 record
  - **State:** covered

- **Required source class:** Research methodology
  - **Canonical records:** ACM artifact/empirical-standard records
  - **State:** covered

- **Required source class:** Standards/publication metadata
  - **Canonical records:** CommonMark, TOML, CFF, LaTeX records
  - **State:** covered

- **Required source class:** Validation/provenance tooling
  - **Canonical records:** Git, uv, clang-tidy, pytest, Ruff, and
                           BasedPyright records
  - **State:** covered

The closed bibliography taxonomy still reserves `legal-and-regulatory/` for
future source records. `libraries/` now contains the exact transitive packages
pinned by the Python validation environment. No baseline source is fabricated
merely to make a category non-empty. New material claims must add a canonical
record before relying on an uncovered source class.

### Discarded Or Rejected Evidence Patterns

The repository does not accept the following as sufficient evidence:

- a secondary blog when the primary specification or paper is available;
- a benchmark winner without retained configuration, inputs, and raw samples;
- an optimizer checking its own candidate without independent verification;
- an LLM-generated claim that has not been checked against a source or oracle;
- an implementation quirk promoted to language semantics only because old
  programs depend on it; or
- a bibliography entry that no repository claim, experiment, legal question, or
  tool identity actually uses.

### Unresolved

Coverage is intentionally a baseline rather than a permanently closed corpus.
New dependencies, standards, algorithms, legal authorities, or materially cited
external claims require additional canonical source records and dated review.

### Open Verification Work

The bibliography is a baseline, not a claim of completeness. Each new external
dependency, algorithm family, standard, and materially cited paper must receive
a source record before its claims become durable repository evidence.

Performance hypotheses remain unverified until experiments exist. No current
document proves that GPU superoptimization will compile large C programs in
seconds, that native execution will make DOOM playable, or that one search
strategy dominates another. Those are research and engineering targets.

## Sources

- `docs/bibliography/specifications-and-standards/malbolge/`
- `docs/bibliography/languages/`
- `docs/bibliography/platforms-and-runtimes/`
- `docs/bibliography/publications/`
- `docs/bibliography/tooling/`
- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
- `docs/technical/adr/host-cpu-and-accelerator-runtime-baseline.md`
