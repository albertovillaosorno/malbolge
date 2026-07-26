# Egg Equality Saturation

- Review status: Verified
- Evidence status: Verified
- As-of date: 2026-07-26

## Identity

- Canonical name: egg: Fast and Extensible Equality Saturation
- Subject class: Compiler optimization and e-graph research paper
- Stable identifier: arXiv:2004.03082
- Publisher or authority: Max Willsey, Chandrakana Nandi, Yisu Remy Wang,
  Oliver Flatt, Zachary Tatlock, and Pavel Panchekha

## Repository Relevance

Equality saturation is candidate prior work for representing many equivalent
expressions or state transformations without choosing a rewrite order too early.
It is explicitly research, not an assumed production dependency.

## Source Quality And Provenance

The paper is a primary source from the `egg` authors and was published in the
POPL 2021 research program.

## Verified Claims

- E-graphs represent congruence relations over many expressions.
- Equality saturation applies e-graphs to rewrite-driven optimization and
  synthesis.
- The paper introduces rebuilding and e-class analyses to improve extensibility
  and performance for equality-saturation workloads.

## Unresolved Evidence

Self-modifying Malbolge state is not merely an expression-rewrite problem.
Whether equality saturation is useful must be tested against exact state and
observational-equivalence requirements.

## Sources

- <https://arxiv.org/abs/2004.03082> - accessed 2026-07-26.
