# Ernvall-Hytonen Leppala Matala-aho Exponential Lower Bound

## Status

Verified for the explicit imaginary-quadratic Baker-type theorem, its height
threshold, and the definitions needed to evaluate that threshold for the guest
`atan2` exponential bridge.

## Subject

- Canonical name: An explicit Baker type lower bound of exponential values
- Subject class: Number-theory research publication
- Stable identifier: arXiv:1309.6053
- Publisher or authority: Anne-Maria Ernvall-Hytonen, Kalle Leppala, and Tapani
  Matala-aho; Proceedings of the Royal Society of Edinburgh Section A

## Repository Use

The guest `atan2` midpoint bridge has `alpha=2im` in the imaginary quadratic
field `Q(i)`. The paper gives a completely explicit lower bound for linear
forms in `1,e^alpha_1,...,e^alpha_m` over an imaginary quadratic field for
`m>=2`. A two-term guest bridge can be embedded formally by adding a distinct
second exponential with coefficient zero, so the published threshold can be
tested as a conservative product candidate without claiming an `m=1` theorem.

The retained deep binary64 midpoint has `alpha=2im` with denominator `2^105`.
With the minimal admitted `m=2`, the paper defines
`log(gamma)=(3*m*e0)^2` and
`e0>=3*sqrt(log(g2))`. Since `g2>=2^105`, this already gives
`log(gamma)>=34020*log(2)`. Its threshold
`H0>=exp(gamma*log(gamma)/2)` therefore has
`log2(H0)>(2^34020)`, overwhelmingly beyond the guest precision budget.

## Provenance

The arXiv record and experimental HTML for version 1 were reviewed on
2026-09-10. Theorem 2.1, equations (8)-(12), and Corollary 2.3 were checked
directly. The paper requires `m>=2`; this record does not promote its result to
a missing two-term theorem.

## Identity And Version

- Canonical name: An explicit Baker type lower bound of exponential values
- Subject class: Number-theory research publication
- Stable identifier: arXiv:1309.6053v1
- Publisher or authority: Proceedings of the Royal Society of Edinburgh Section
  A, volume 145 issue 6, 2015, pages 1153-1182

## License Or Terms

This is external material. Citation does not relicense the paper or import its
terms into the repository MIT license.

## Evidence

### Verified

- Theorem 2.1 applies over `Q` or an imaginary quadratic field for `m>=2`.
- Coefficients in the linear form may be zero provided the coefficient vector
  is not identically zero.
- The paper defines `g2=max(|x_j|+|y_j|)`,
  `e0=3*sqrt(log(g2))+log(g4)/(2*sqrt(log(g2)))`, and
  `log(gamma)=(3*m*e0)^2`.
- Its admissibility threshold includes
  `H0>=exp(gamma*log(gamma)/2)`.
- The retained deep guest midpoint makes this threshold alone require a
  base-two exponent larger than `2^34020`, before the theorem's additional
  positive factors are counted.

### Unresolved

The publication does not state its main theorem for `m=1`. Padding the guest
linear form to `m=2` is valid but quantitatively unusable. A genuinely
specialized two-term result would need its own explicit threshold evaluation
before it could become runtime correctness evidence.

## Sources

- <https://arxiv.org/abs/1309.6053> - identity and version history; accessed
  2026-09-10.
- <https://arxiv.org/html/1309.6053> - Theorem 2.1, equations (8)-(12), and
  Corollary 2.3; accessed 2026-09-10.
- <https://doi.org/10.1017/S0308210515000049> - published article identity;
  accessed 2026-09-10.
