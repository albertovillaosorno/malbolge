# Fischler-Rivoal Exponential Transcendence Measure

## Status

Verified for the stated exponential-transcendence theorem, its linear-polynomial
height exponent, and the existence of a completely explicit specialization;
repository-specific constant evaluation remains open.

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

The arXiv record for 2502.17992 was reviewed on 2026-09-08. The current paper
states Theorem 1 for nonzero algebraic `alpha`, number-field coefficient ring
`O_K`, polynomial degree at most `delta`, and a lower bound in polynomial
height.
It states that the constant can be made completely explicit and points to
Proposition 1 in section 3 for that version.

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

The repository has not yet instantiated Proposition 1's completely explicit
constant for the full binary64 bridge bounds. In particular, this record does
not prove that the resulting lower bound is strong enough to certify every
input before the guest allocator's finite `uint32_t` byte ceiling. The source is
also an arXiv research preprint rather than a repository-owned proof.

## Sources

- <https://arxiv.org/abs/2502.17992> - arXiv identity, abstract, and version
  history; accessed 2026-09-08.
- <https://arxiv.org/html/2502.17992> - paper HTML, including Theorem 1 and the
  degree-one specialization discussed in the introduction; accessed 2026-09-08.
