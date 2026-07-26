# Stochastic Superoptimization And STOKE

## Status

Verified; evidence verified.

## Subject

- Canonical name: Stochastic Superoptimization
- Subject class: Compiler optimization research paper
- Stable identifier: arXiv:1211.0557
- Publisher or authority: Eric Schkufza, Rahul Sharma, and Alex Aiken

## Repository Use

This paper is foundational prior work for the planned stochastic search research
track and for separating candidate-search quality from final deterministic
verification.

## Provenance

The paper is a primary research source authored by the technique's researchers.
It formulates loop-free binary superoptimization as stochastic search and
describes the STOKE prototype.

## Identity And Version

- Canonical name: Stochastic Superoptimization
- Subject class: Compiler optimization research paper
- Stable identifier: arXiv:1211.0557
- Publisher or authority: Eric Schkufza, Rahul Sharma, and Alex Aiken

## License Or Terms

This is external material. Citation does not relicense the source or import its
terms into the repository MIT license.

## Evidence

### Verified

- The method encodes correctness and performance considerations in a stochastic
  search cost formulation.
- It uses Markov Chain Monte Carlo to explore candidate programs.
- The approach sacrifices completeness in exchange for broader practical search.
- STOKE was evaluated on 64-bit x86 binary code generated from LLVM inputs.

### Unresolved

Malbolge's self-modifying semantics differ materially from the paper's x86
setting. Applicability and search behavior must be established experimentally.

## Sources

- <https://arxiv.org/abs/1211.0557> - accessed 2026-07-26.
