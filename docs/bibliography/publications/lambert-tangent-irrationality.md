# Lambert Tangent Continued Fraction And Irrationality

## Status

Verified for the cited continued fraction and rational-input irrationality
statement; implementation termination consequences remain repository work.

## Subject

- Canonical name: Lambert tangent continued fraction and irrationality theorem
- Subject class: Classical analysis and number-theory result
- Stable identifier: DLMF 4.25.E1
- Publisher or authority: NIST DLMF; Lambert result corroborated by University
  of Utah mathematical notes and modern Lambert scholarship

## Repository Use

The guest `atan2` midpoint-cell verifier needs to know that a nonzero rational
binary64 cell boundary cannot have rational tangent. Finite binary64 input
ratios are rational, so this non-equality is the qualitative termination fact
needed by a future directed tangent comparison that keeps refining until the
input ratio and boundary tangent are separated.

## Provenance

NIST DLMF version 1.2.7 records Lambert's continued fraction for tangent as
formula 4.25.1 and was reviewed on 2026-09-08. Davar Khoshnevisan's University
of Utah Math 2200 notes state the same continued fraction as Theorem 6.9 and the
nonzero-rational-input irrationality result as Theorem 6.10; they also note the
historical role of Legendre in repairing weaknesses attributed to Lambert's
original proof. The 2024 Springer annotated translation provides modern
publication provenance for Lambert's original works but is not needed as an
implementation formula source.

## Identity And Version

- Canonical name: Lambert tangent continued fraction and irrationality theorem
- Subject class: Classical analysis and number-theory result
- Stable identifier: DLMF 4.25.E1
- Publisher or authority: NIST DLMF; Lambert result corroborated by University
  of Utah mathematical notes and modern Lambert scholarship

## License Or Terms

This is external material. Citation does not relicense the source or import its
terms into the repository MIT license.

## Evidence

### Verified

- DLMF 4.25.1 gives Lambert's continued fraction for `tan(z)` away from tangent
  poles.
- University of Utah Math 2200 notes, Theorem 6.10, state that `tan(theta)` is
  irrational whenever `theta` is a nonzero rational number.
- The same notes identify the continued fraction as Lambert's result and record
  the subsequent historical qualification involving Legendre.
- A binary64 midpoint is dyadic and therefore rational, so the cited theorem
  excludes equality between its tangent and any finite binary64 input ratio
  whenever that midpoint is nonzero and not a tangent pole.

### Unresolved

The repository has not yet promoted this qualitative non-equality into a guest-C
adaptive tangent evaluator with unbounded refinement storage. The sources cited
here do not by themselves provide the repository-specific integer data
structure, resource policy, or a quantitative finite precision ceiling.

## Sources

- <https://dlmf.nist.gov/4.25.E1> - NIST DLMF 4.25.1, version 1.2.7; accessed
  2026-09-08.
- <https://www.math.utah.edu/~davar/math2200/summer2015/Week8.pdf> - Davar
  Khoshnevisan, Math 2200 notes, Theorems 6.9-6.10; accessed 2026-09-08.
- <https://link.springer.com/book/10.1007/978-3-031-52223-9> - annotated
  translation and study of Lambert's works; accessed 2026-09-08.
