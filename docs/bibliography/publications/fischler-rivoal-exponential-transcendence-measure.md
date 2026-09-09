# Fischler-Rivoal Exponential Transcendence Measure

## Status

Verified for the exponential-transcendence theorem, its linear-polynomial
height exponent, and Proposition 1's completely explicit specialization. The
direct repository bridge has also been evaluated and is too weak for the finite
guest resource ceiling.

## Subject

- Canonical name: A new transcendence measure for the values of the exponential
  function at algebraic arguments
- Subject class: Number-theory research publication
- Stable identifier: arXiv:2502.17992
- Publisher or authority: Stéphane Fischler and Tanguy Rivoal; arXiv preprint

## Repository Use

The adaptive guest `atan2` proof rewrites tangent separation at a rational
dyadic midpoint `m` as a nonzero linear form in `e^(2im)` over the Gaussian
integers. This publication supplies a quantitative transcendence-measure family
for `e^alpha` at nonzero algebraic `alpha`, including polynomials with
coefficients in the ring of integers of a number field.

For the repository bridge, take `K=Q(i)`, `alpha=2im`, and the degree-one
polynomial `P(X)=(a+ib)X+(a-ib)` associated with reduced rational `a/b`. Then
`[K(alpha):Q]=2` for nonzero rational `m`, and the publication's degree-one
height exponent is `4d^2-2d-1=11` when `d=2`.

## Provenance

The arXiv record for 2502.17992 was reviewed on 2026-09-08. The current author
manuscript dated 2025-11-02 was reviewed on 2026-09-09. Proposition 1 gives the
completely explicit lower bound together with explicit `q`, `t`, `a`, `b`, `u`,
`v`, and `psi` definitions.

The introduction separately records that, for degree-one polynomials and
`d>=2`, the smallest height exponent in this method is `4d^2-2d-1`; substituting
`d=2` gives 11. This record does not infer the omitted repository-specific
constant from that exponent.

## Identity And Version

- Canonical name: A new transcendence measure for the values of the exponential
  function at algebraic arguments
- Subject class: Number-theory research publication
- Stable identifier: arXiv:2502.17992
- Publisher or authority: Stéphane Fischler and Tanguy Rivoal; arXiv preprint

## License Or Terms

This is external material. Citation does not relicense the paper or import its
terms into the repository MIT license.

## Evidence

### Verified

- Theorem 1 gives a lower bound for `|P(e^alpha)|` when `alpha` is nonzero
  algebraic and `P` has coefficients in `O_K`.
- The theorem's introduction states that its constant can be made completely
  explicit and refers to Proposition 1 in section 3 for the explicit version.
- For a degree-one polynomial with algebraic degree `d>=2`, the stated height
  exponent is `4d^2-2d-1`.
- For the repository specialization `K=Q(i)` and rational nonzero midpoint `m`,
  `alpha=2im` has degree 2 over `Q`, so the stated exponent specializes to 11.

### Unresolved

Proposition 1 is not strong enough, under the direct repository specialization,
to prove certification before the finite guest allocation ceiling. This does
not rule out a stronger specialized transcendence measure or say that actual
midpoint separation is comparably small. The external theorem remains
source-owned rather than a repository-owned proof.

## Sources

- <https://arxiv.org/abs/2502.17992> - arXiv identity, abstract, and version
  history; accessed 2026-09-08.
- <https://arxiv.org/html/2502.17992> - paper HTML, including Theorem 1 and the
  degree-one specialization discussed in the introduction; accessed 2026-09-08.
- <https://rivoal.perso.math.cnrs.fr/articles/mesureexp.pdf> - current author
  manuscript, including Proposition 1 and its explicit constants; accessed
  2026-09-09.
