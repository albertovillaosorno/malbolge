# Repository Source Provenance And Verification Status

## Status

Active verification ledger, reviewed 2026-07-26.

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

- Record owner: Malbolge repository bibliography.
- Governance:`n
  `docs/bibliography/adr/source-taxonomy-and-citation-provenance.md`.
- Review date: 2026-07-26.
- Git is cataloged separately under `docs/bibliography/tooling/git.md`.

## License Or Terms

This ledger is repository-authored MIT material. External evidence retains its
own copyright, license, publication, and access terms; citation here does not
relicense any external source.

## Evidence

### Current High-Impact Claims

| Claim | Evidence | Verification state |
| --- | --- | --- |
| Written 1998 spec is normative classic authority | Ben spec + commit `fc871a3` | verified |
| Spec defines `<` as input and `/` as output | original specification | verified directly |
| Ben C reverses `<` and `/` | original interpreter C | verified directly |
| Spec terminates on a non-graphical executable cell | original specification | verified directly |
| Ben C can fail to advance on that case | original interpreter C | verified directly |
| Classic words are ten trits; memory is 59,049 words | original specification | verified directly |
| Ben public-domain dedication | original notices | verified directly |
| C is the human-authored application language | repository ADR/contract | accepted decision |
| x86-64 and AArch64 are first-class host targets | repository ADR + vendor docs | accepted decision |
| CUDA is optional, non-semantic capacity | repository ADR + NVIDIA docs | accepted decision |
| ROCm is the AMD GPU runtime adapter identity | repository ADR + AMD docs | accepted decision |
| STOKE is stochastic-superoptimization prior work | STOKE paper | verified prior work |
| Alive2 is translation-validation prior work | Alive2 sources | verified prior work |
| GitHub recognizes root `CITATION.cff` metadata | GitHub + CFF docs | verified |

### Specification Versus Interpreter Divergence

The first major contradiction discovered during documentation promotion
concerned I/O. The written specification states that `<` reads into A and `/`
writes A. The historical C `switch` performs those operations in reverse. A
second observable disagreement exists for non-graphical executable cells: the
prose requires termination while the C implementation can continue without
pointer advancement.

The repository resolved the conflict in favor of the written specification for
modern semantics. The historical interpreter remains unchanged and useful as
implementation evidence on the subset where it agrees with the specification.

The decision entered repository history in:

```text
fc871a3e6510d15e6098d327d9394393a49623a7
docs: make Malbolge specification authoritative
```

That commit is provenance for the repository decision. The historical
specification and interpreter remain the primary evidence for the underlying
facts.

### Research Prior-Work Verification

The initial compiler-research baseline has direct records for STOKE, Souper,
`egg`, and Alive2. Those records establish that the cited techniques exist and
describe what their authors claim or implement. They do not establish that the
same techniques improve Malbolge compilation.

Every transfer claim remains experimental until a Malbolge research capsule
records a falsifiable hypothesis, baseline, configuration, raw evidence,
verification result, and threats to validity.

### Tooling And Publication Verification

The repository records authoritative references for C, Rust, LLVM/Clang,
clang-tidy, CUDA, ROCm, PyTorch, x86-64, AArch64, CommonMark, TOML, LaTeX, Git,
GitHub repository citation metadata, and Citation File Format. Source records
support identity and capabilities without making upstream tools part of runtime
architecture automatically.

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
