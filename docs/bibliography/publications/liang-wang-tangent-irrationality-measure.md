# Liang-Wang Tangent Irrationality Measure

## Status

Verified from the publisher PDF for rational-input tangent scope, generalized
continued-fraction method, Theorem 2's irrationality measure 2, and Theorem 3's
asymptotic lower-bound shape; its implicit constants are not repository-usable
resource bounds.

## Subject

- Canonical name: Irrationality measures of several types of irrational numbers
- Subject class: Number-theory research publication
- Stable identifier: DOI 10.19789/j.1004-9398.2024.01.011
- Publisher or authority: Journal of Capital Normal University (Natural Science
  Edition); Zhibin Liang and Yulun Wang

## Repository Use

The guest `atan2` resource proof needs quantitative separation between
`tan(m)` at a nonzero rational dyadic midpoint and a reduced rational input
ratio. The publication specifically treats `tan(r)` for nonzero rational `r`
and states irrationality measure 2, making it a substantially more specialized
candidate than a general exponential-transcendence measure.

The result is retained only as asymptotic number-theory evidence. Irrationality
measure 2 does not by itself give the repository a concrete denominator
threshold or uniform constant for all reduced denominators through the proved
adaptive ceiling `q < 2^106`.

## Provenance

The SciOpen journal page and issue metadata were reviewed on 2026-09-08. They
identify Zhibin Liang and Yulun Wang, Journal of Capital Normal University
(Natural Science Edition) volume 45 issue 1, pages 116-123, publication date
2024-02-01, and DOI 10.19789/j.1004-9398.2024.01.011.

The publisher PDF was also reviewed directly. Theorem 2 states that `tan(r)`
for nonzero rational `r` is irrational with irrationality measure 2. Theorem 3
proves a general lower-bound shape `|alpha-p/q| >> q^-mu` from a Diophantine
approximation sequence, but both its hypotheses and conclusion use Vinogradov
`<<`/`>>` notation with implicit constants.

In the final proof, the authors use factorial asymptotics with arbitrary
positive
epsilon parameters and state in Remark 2 that Theorem 2 is proved similarly. No
explicit value for the hidden constant applicable to the tangent specialization
is supplied there.

## Identity And Version

- Canonical name: Irrationality measures of several types of irrational numbers
- Subject class: Number-theory research publication
- Stable identifier: DOI 10.19789/j.1004-9398.2024.01.011
- Publisher or authority: Journal of Capital Normal University (Natural Science
  Edition); Zhibin Liang and Yulun Wang

## License Or Terms

The journal page marks the article open access under CC BY-NC-ND 4.0. Citation
does not relicense the source or import its terms into the repository MIT
license.

## Evidence

### Verified

- The publication identity is Liang and Wang, volume 45 issue 1, pages 116-123,
  DOI 10.19789/j.1004-9398.2024.01.011.
- Publisher metadata includes `tan(r)` for nonzero rational `r` among the
  quantities approximated by generalized continued fractions.
- Theorem 2 in the publisher PDF states that `tan(r)` has irrationality measure
  2 for every nonzero rational `r`.
- Theorem 3 gives a lower bound of power-law form for every rational `p/q`, but
  uses implicit `<<`/`>>` constants rather than an explicit numerical constant.
- Remark 2 says Theorem 2 is proved similarly to the displayed `e^r` argument,
  whose final factorial estimates also use implicit constants and arbitrary
  positive epsilon parameters.
- This is directly relevant to the adaptive comparator because its candidate
  midpoints are rational dyadics and its reduced input denominator is now
  separately bounded by 106 bits.

### Unresolved

The paper does not instantiate the hidden Vinogradov constants in Theorem 3
for its tangent specialization. The repository therefore still lacks a concrete
positive `C(r)` and any derived bit ceiling valid for all reduced denominators
through `q<2^106`. Consequently irrationality measure 2 remains asymptotic
separation evidence, not a finite correct-rounding resource bound.

## Sources

- <https://www.sciopen.com/article/10.19789/j.1004-9398.2024.01.011> - article
  identity, abstract metadata, DOI, pages, publication date, and license;
  accessed 2026-09-08.
- The publisher PDF linked from the SciOpen article page contains Theorems 2-3
  and the proof remarks; accessed 2026-09-08.
- <https://doi.org/10.19789/j.1004-9398.2024.01.011> - stable publication DOI;
  accessed 2026-09-08.
