// File:
//   - exact_duplicate.rs
// Path:
//   - algorithms/search-pruning-and-state-canonicalization/tests/
//     exact_duplicate.rs
//
// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Path-Rule:
//   - All paths in this header are repository-root relative.
//
// Boundary-Contract:
// - Owns:
//   - Adversarial correctness evidence for exact duplicate candidate pruning.
// - Must-Not:
//   - Treat near-equality, shared prefixes, or hashes as equivalence evidence.
// - Allows:
//   - Inputs: deterministic duplicate-rich, unique, and near-match corpora.
//   - Outputs: exact representative mappings and retained null-result evidence.
//   - Side effects: test-process allocation only.
// - Split-When:
//   - Split when stronger equivalence rules require separate adversarial
//     suites.
// - Merge-When:
//   - Merge when exact duplicate pruning becomes production search behavior.
// - Summary:
//   - Proves byte equality is the only active pruning relation.
// - Description:
//   - Includes a unique-corpus null result and one-byte counterexample
//     fixtures.
// - Usage:
//   - Composed by `tests/search_pruning_research.rs`.
// - Defaults:
//   - Correctness evidence only; no wall-time speedup claim is made.
//
// Related documents:
// - algorithms/search-pruning-and-state-canonicalization/exact_duplicate.rs
//
// Large file:
//   - false

use crate::exact_duplicate::prune_exact_duplicates;

const DUPLICATE_BASELINE: usize = 8;
const DUPLICATE_RETAINED: usize = 5;

#[test]
fn duplicate_rich_corpus_keeps_first_exact_representatives()
-> Result<(), String> {
    let candidates: &[&[u8]] =
        &[b"a", b"b", b"a", b"c", b"b", b"d", b"d", b"e"];
    let pruning = prune_exact_duplicates(candidates);
    if pruning.representative_indices != [0, 1, 3, 5, 7] {
        return Err(format!(
            "unexpected representatives: {:?}",
            pruning.representative_indices,
        ));
    }
    if pruning.canonical_indices != [0, 1, 0, 3, 1, 5, 5, 7] {
        return Err(format!(
            "unexpected canonical mapping: {:?}",
            pruning.canonical_indices,
        ));
    }
    if candidates.len() != DUPLICATE_BASELINE {
        return Err(String::from("duplicate baseline fixture changed"));
    }
    if pruning.representative_indices.len() != DUPLICATE_RETAINED {
        return Err(String::from("duplicate retained count changed"));
    }
    Ok(())
}

#[test]
fn empty_corpus_has_no_phantom_representative() -> Result<(), String> {
    let pruning = prune_exact_duplicates(&[]);
    if !pruning.representative_indices.is_empty()
        || !pruning.canonical_indices.is_empty()
    {
        return Err(String::from("empty corpus produced a representative"));
    }
    Ok(())
}

#[test]
fn prefix_and_length_similarity_never_define_equivalence() -> Result<(), String>
{
    let candidates: &[&[u8]] = &[b"abc", b"abcd", b"ab", b"abc\0", b"abc"];
    let pruning = prune_exact_duplicates(candidates);
    if pruning.representative_indices != [0, 1, 2, 3]
        || pruning.canonical_indices != [0, 1, 2, 3, 0]
    {
        return Err(String::from(
            "prefix/length similarity collapsed candidates",
        ));
    }
    Ok(())
}

#[test]
fn single_byte_difference_never_collapses() -> Result<(), String> {
    let candidates: &[&[u8]] =
        &[b"prefix-A-suffix", b"prefix-B-suffix", b"prefix-A-suffix"];
    let pruning = prune_exact_duplicates(candidates);
    if pruning.representative_indices != [0, 1]
        || pruning.canonical_indices != [0, 1, 0]
    {
        return Err(String::from(
            "single-byte difference collapsed candidates",
        ));
    }
    Ok(())
}

#[test]
fn unique_corpus_is_retained_as_null_result() -> Result<(), String> {
    let candidates: &[&[u8]] = &[b"a", b"b", b"c", b"d"];
    let pruning = prune_exact_duplicates(candidates);
    if pruning.representative_indices != [0, 1, 2, 3]
        || pruning.canonical_indices != [0, 1, 2, 3]
    {
        return Err(String::from("unique corpus was pruned"));
    }
    Ok(())
}
