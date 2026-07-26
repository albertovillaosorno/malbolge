# Repository Source Provenance And Verification Status

This ledger records which evidence currently supports high-impact repository
claims, what was checked directly, which sources disagreed, and what remains
unresolved. Its purpose is the same as an experiment log: polished prose must
not be mistaken for verification.

The ledger is non-governing. Technical decisions live in `docs/technical/`,
research conclusions in `docs/research/`, and legal analysis in `docs/legal/`.
This file records the evidence trail that lets those documents be challenged.

## Verification Rule

For each material claim, prefer the closest primary or authoritative source.
When two sources disagree, record the disagreement and resolve only the exact
question supported by the evidence. Do not average contradictory claims.

Internal Git commits are provenance for repository decisions, not external
academic authority. They may show when and why repository policy changed but
cannot replace the historical source that motivated the change.
See the [Git bibliography record](../validation-tooling/git.md) for the tool identity.

## Current High-Impact Claims

| Claim | Evidence | Verification state |
| --- | --- | --- |
| Written 1998 spec is normative classic authority | Ben spec + commit `236e75b` | verified |
| Spec defines `<` as input and `/` as output | original specification | verified directly |
| Ben C reverses `<` and `/` | original interpreter C | verified directly |
| Spec terminates on a non-graphical executable cell | original specification | verified directly |
| Ben C can fail to advance on that case | original interpreter C | verified directly |
| Classic words are ten trits; memory is 59,049 words | original specification | verified directly |
| Ben public-domain dedication | original notices | verified directly |
| C is the human-authored application language | repository ADR/contract | accepted decision |
| Clang LibTooling is suitable AST tooling prior art | official Clang docs | verified capability |
| STOKE is stochastic-superoptimization prior work | STOKE paper | verified prior work |
| Alive2 is translation-validation prior work | Alive2 sources | verified prior work |
| CUDA is optional, non-semantic capacity | ADR + CUDA docs | accepted decision |
| GitHub recognizes root `CITATION.cff` metadata | GitHub + CFF docs | verified |

## Specification Versus Interpreter Divergence

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
236e75bb38d96d71d2dc3d0f3a5ed70af7710c61
docs: make Malbolge specification authoritative
```

That commit is provenance for the repository decision. The historical
specification and interpreter remain the primary evidence for the underlying
facts.

## Research Prior-Work Verification

The initial compiler-research baseline has direct records for STOKE, Souper,
`egg`, and Alive2. Those records establish that the cited techniques exist and
describe what their authors claim or implement. They do not establish that the
same techniques will improve Malbolge compilation.

Every transfer claim remains experimental until a Malbolge research capsule
records a falsifiable hypothesis, baseline, configuration, raw evidence,
verification result, and threats to validity.

## Tooling And Publication Verification

The repository records authoritative references for C, Rust, LLVM/Clang,
clang-tidy, CUDA, PyTorch, CommonMark, TOML, LaTeX, Git, GitHub repository
citation metadata, and Citation File Format. These records support tool identity,
configuration syntax, documentation format, and publication mechanics; they do
not make upstream tools part of runtime architecture automatically.

## Discarded Or Rejected Evidence Patterns

The repository does not accept the following as sufficient evidence:

- a secondary blog when the primary specification or paper is available;
- a benchmark winner without retained configuration, inputs, and raw samples;
- an optimizer checking its own candidate without independent verification;
- an LLM-generated claim that has not been checked against a source or oracle;
- a historical implementation quirk promoted to language semantics solely
  because old programs depend on it; or
- a bibliography entry that no repository claim, experiment, legal question, or
  tool identity actually uses.

## Open Verification Work

The bibliography is a baseline, not a claim of completeness. As implementation
begins, each new external dependency, algorithm family, standard, and materially
cited paper must receive a source record before its claims become durable
repository evidence.

Performance hypotheses remain unverified until experiments exist. In particular,
no current document proves that GPU superoptimization will compile large C
programs in seconds, that native execution will make DOOM playable, or that any
specific search strategy will dominate another. Those are research and
engineering targets, not established results.
