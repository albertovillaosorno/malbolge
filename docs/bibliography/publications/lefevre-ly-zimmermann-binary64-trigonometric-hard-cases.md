# Lefevre-Ly-Zimmermann Binary64 Trigonometric Hard Cases

## Status

Verified for exhaustive binary64 sine/cosine/tangent hard-to-round search,
global Table Maker's Dilemma ceilings for sine and cosine, and the associated
CORE-MATH hard-case artifacts and closest-to-reduction-boundary generator.

## Subject

- Canonical name: Computing hard-to-round cases of sin, cos, tan in double
  precision
- Subject class: Computer-arithmetic research publication
- Stable identifier: HAL hal-05593313v2
- Publisher or authority: Vincent Lefevre, Tue Ly, and Paul Zimmermann; ARITH
  2026, 33rd IEEE International Symposium on Computer Arithmetic

## Repository Use

The guest binary64 sine/cosine rounding proof consumes the source-owned finite
Table Maker's Dilemma result rather than requiring a new universal
transcendence measure. The exhaustive search gives the maximal number of
identical bits after the round bit, while CORE-MATH retains the corresponding
hard cases and its continued-fraction `wc()` generator for inputs closest to
multiples of `pi/2` in each binary64 binade.

The repository combines those finite-domain facts with its independently
proved directed interval widths. This use is specific to univariate binary64
sine/cosine and does not transfer to bivariate `atan2`.

## Provenance

The ARITH 2026 program, HAL version 2 metadata, Paul Zimmermann's publication
page and training module, and CORE-MATH snapshot were reviewed on 2026-09-09.
The CORE-MATH `main` snapshot used for artifact identity is commit
`887cab6f26c5c40a5d03ce4b5968d3e15e29d884`.

At that snapshot, the retained binary64 files have these SHA-256 digests:

- `sin.wc`: `013adf95805ebc1d4fecdaddf547f3a89a370f7082e2be68d1ed33fa7aee2fa1`;
- `cos.wc`: `cebe5847c66ed6e2cc4cc1a2cb74cd141d434504773b4b40800abe8392ae54f8`.

The training module states the binary64 maxima, excluding separately handled
special inputs, as 68 identical bits for sine and 66 for cosine. It also states
the standard implication that a `p+m+2`-bit approximation with a smaller
certified error cannot cross a rounding boundary.

## Identity And Version

- Canonical name: Computing hard-to-round cases of sin, cos, tan in double
  precision
- Subject class: Computer-arithmetic research publication
- Stable identifier: HAL hal-05593313v2
- Publisher or authority: Vincent Lefevre, Tue Ly, and Paul Zimmermann; ARITH
  2026

## License Or Terms

The publication, training material, and CORE-MATH artifacts remain external
material under their respective terms. Citation and digest verification do not
relicense them into this repository's MIT license.

## Evidence

### Verified

- The authors describe an exhaustive algorithm over the remaining binary64
  binades and state that the Table Maker's Dilemma is fully solved for the
  common univariate binary64 functions.
- For `x >= 2^10`, the paper searches all 1,014 remaining binades and reports
  1,048,756 sine and 1,049,705 cosine hard cases at its retained threshold.
- The hardest retained high-range sine case has 68 identical bits after the
  round bit at `0x1.6ac5b262ca1ffp+849`.
- The hardest retained high-range cosine case has 66 identical bits after the
  round bit at `0x1.6ac5b262ca1ffp+850`.
- Zimmermann's training module gives the global binary64 maxima as 68 for sine
  and 66 for cosine and derives the `p+m+2` correct-rounding precision rule.
- The paper states that full hard-case sets are retained in CORE-MATH. The
  snapshot digests above bind the exact `sin.wc` and `cos.wc` artifacts reviewed
  by this repository.
- CORE-MATH `sin.sage` documents `wc(e, parity)` as returning the binary64 value
  in one binade closest to a multiple of `pi/2`, with even/odd parity selecting
  the near-zero/near-one trigonometric branches.

### Unresolved

This source does not solve bivariate `atan2`, and the repository does not infer
an `atan2` resource ceiling from the univariate result. Product availability
still requires the repository's own range-reduction, interval-width, ABI, and
source-integration evidence to compose with the external finite TMD result.

## Sources

- <https://inria.hal.science/hal-05593313v2> - ARITH 2026 paper identity and
  version; accessed 2026-09-09.
- <https://members.loria.fr/PZimmermann/papers/> - author publication summary
  describing the exhaustive search and full TMD result; accessed 2026-09-09.
- <https://homepages.loria.fr/PZimmermann/talks/module4.pdf> - binary64 TMD
  maxima and precision implication; accessed 2026-09-09.
- <https://github.com/Cactus-proj/core-math/tree/887cab6f26c5c40a5d03ce4b5968d3e15e29d884> - exact CORE-MATH snapshot used
  for artifact and generator provenance; accessed 2026-09-09.
