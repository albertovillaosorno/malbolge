// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Boundary-Contract:
// - Owns:
//   - Regression controls for the finite recurrent classifier closure.
// - Must-Not:
//   - Authorize source publication or substitute for guest trace evidence.
// - Allows:
//   - Inputs: fixed classifier seeds and independently chosen mutations.
//   - Outputs: positive and negative classifier closure checks.
//   - Side effects: none.
// - Split-When:
//   - Additional classifier shapes need separate regression controls.
// - Merge-When:
//   - A general source-frame verifier owns these classifier checks.

use std::collections::BTreeSet;

use super::{ClassifierPlan, Error, digit, fold, last};

#[test]
fn source_recurrent_classifier_rejects_bad_byte() -> Result<(), String> {
    let plan = ClassifierPlan {
        byte: 7_180_650,
        eof: [7_178_463, 7_179_921],
        words: [0; 6],
    };
    let valid = [5_832, 5_103, 0, 14_329_224, 728, 13_122];
    plan.verify_seeds(valid)
        .map_err(|error| format!("valid classifier: {error:?}"))?;
    // At trit six, this mutation preserves the first EOF result
    // but incorrectly selects EOF on a real byte. A finite empty
    // trace alone cannot prove the classifier's closure.
    let bad = [5_832, 4_374, 0, 14_329_224, 728, 13_122];
    let place = 729;
    let valid_digit = valid.map(|word| digit(word, place));
    let bad_digit = bad.map(|word| digit(word, place));
    if last(fold(valid_digit, 2)) != last(fold(bad_digit, 2)) {
        return Err("mutation did not preserve first EOF".to_owned());
    }
    if plan.verify_seeds(bad) != Err(Error::GuestTransitionMismatch) {
        return Err("accepted latent bad byte".to_owned());
    }
    Ok(())
}

#[test]
fn source_recurrent_classifier_rejects_delayed_mixed_eof() -> Result<(), String>
{
    let plan = ClassifierPlan {
        byte: 7_180_650,
        eof: [7_178_463, 7_179_921],
        words: [0; 6],
    };
    let valid = [5_832, 5_103, 0, 14_329_224, 728, 13_122];
    // Only the 729-place state changes. Each EOF trit still
    // independently reaches both allowed digits, but after two
    // successful reads they can combine into an unadmitted word.
    let bad = [5_103, 4_374, 0, 14_329_224, 728, 13_122];
    let places = [729, 2_187];
    let mut state = places.map(|place| bad.map(|word| digit(word, place)));
    let allowed = plan.eof.map(|word| places.map(|place| digit(word, place)));
    for _ in 0u32..2 {
        if !allowed.contains(&state.map(|words| last(fold(words, 2)))) {
            return Err("mutation failed before the delayed control".to_owned());
        }
        state = state.map(|words| fold(words, 0));
        if state.map(last) != places.map(|place| digit(plan.byte, place)) {
            return Err("mutation did not preserve byte dispatch".to_owned());
        }
    }
    if allowed.contains(&state.map(|words| last(fold(words, 2)))) {
        return Err("mutation did not mix the two EOF trits".to_owned());
    }
    let [[first_low, first_high], [second_low, second_high]] = allowed;
    for (place, terminals_expected) in places
        .into_iter()
        .zip([[first_low, second_low], [first_high, second_high]])
    {
        let mut words = bad.map(|word| digit(word, place));
        let mut seen = BTreeSet::new();
        let mut terminals = BTreeSet::new();
        while seen.insert(words) {
            let terminal = last(fold(words, 2));
            if !terminals_expected.contains(&terminal) {
                return Err("unexpected marginal EOF result".to_owned());
            }
            let _new = terminals.insert(terminal);
            words = fold(words, 0);
            if last(words) != digit(plan.byte, place) {
                return Err("unexpected marginal byte result".to_owned());
            }
        }
        if terminals.len() != 2 {
            return Err("mutation did not preserve marginal closure".to_owned());
        }
    }
    plan.verify_seeds(valid)
        .map_err(|error| format!("valid classifier: {error:?}"))?;
    if plan.verify_seeds(bad) != Err(Error::GuestTransitionMismatch) {
        return Err(
            "accepted independently valid but mixed EOF digits".to_owned()
        );
    }
    Ok(())
}
