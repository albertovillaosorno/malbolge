# Search pruning and state canonicalization

This directory is the executable mirror for research ID
`search-pruning-and-state-canonicalization`. The human research record uses the
same ID under `docs/research/algorithms/`, and its mathematical contract, when
present, uses the same ID under `math/algorithms/`.

Implementations in Rust, C, CUDA, Python, or another justified language live
together here because the algorithm, not the language, owns the research.
Regenerable results belong in `out/` and remain Git ignored.

`exact_duplicate.rs` is the first executable research slice. It operates before
logical candidate identity is assigned and merges only complete byte-identical
inputs. Hashes, prefixes, nearby lengths, and one-byte differences never establish
equivalence. The unique-corpus fixture is retained as a null result: when no
duplicates exist, this rule saves zero candidate evaluations.
