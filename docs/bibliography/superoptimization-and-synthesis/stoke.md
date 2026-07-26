# Stochastic Superoptimization And STOKE

- Review status: Verified
- Evidence status: Verified
- As-of date: 2026-07-26

## Identity

- Canonical name: Stochastic Superoptimization
- Subject class: Compiler optimization research paper
- Stable identifier: arXiv:1211.0557
- Publisher or authority: Eric Schkufza, Rahul Sharma, and Alex Aiken

## Repository Relevance

This paper is foundational prior work for the planned stochastic search research
track and for separating candidate-search quality from final deterministic
verification.

## Source Quality And Provenance

The paper is a primary research source authored by the technique's researchers.
It formulates loop-free binary superoptimization as stochastic search and
describes the STOKE prototype.

## Verified Claims

- The method encodes correctness and performance considerations in a stochastic
  search cost formulation.
- It uses Markov Chain Monte Carlo to explore candidate programs.
- The approach sacrifices completeness in exchange for broader practical search.
- STOKE was evaluated on 64-bit x86 binary code generated from LLVM inputs.

## Unresolved Evidence

Malbolge's self-modifying semantics differ materially from the paper's x86
setting. Applicability and search behavior must be established experimentally.

## Sources

- <https://arxiv.org/abs/1211.0557> - accessed 2026-07-26.
