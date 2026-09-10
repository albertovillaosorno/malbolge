# Nesterenko-Waldschmidt Exponential Approximation

## Status

Verified for the explicit main theorem and its specialization to algebraic
approximations of exponential values.

## Subject

- Canonical name: On the approximation of the values of exponential function
  and logarithm by algebraic numbers
- Subject class: Number-theory research publication
- Stable identifier: arXiv:math/0002047
- Publisher or authority: Yuri Nesterenko and Michel Waldschmidt

## Repository Use

The guest `atan2` midpoint comparison reduces exact rational tangent separation
to algebraic approximation of `e^(2im)`. For a reduced rational ratio `a/b`, set
`alpha=-(a-ib)/(a+ib)` and `beta=2im`. Then
`P(X)=(a+ib)X+(a-ib)` satisfies
`|P(e^beta)|=2|a*cos(m)-b*sin(m)|` and
`|P(e^beta)|=|a+ib|*|e^beta-alpha|`.

The publication's Main Theorem 1 gives an entirely explicit lower bound for
`|e^theta-alpha|+|theta-beta|` for algebraic `alpha,beta`. Taking `theta=beta`
therefore gives a direct product-specific lower bound without a hidden
asymptotic constant. Under the repository ceilings, deliberately coarse
parameters `D=2`, `log A=109`, `log B=107`, and `E=e` imply a binary separation
exponent below `338,383,232` bits.

## Provenance

The arXiv source for `math/0002047` was reviewed directly on 2026-09-10. Main
Theorem 1 and Theorem 5 were checked in the source TeX. The retained product
certificate uses Main Theorem 1 because its smaller explicit constant is
material to the finite guest resource bound.

## Identity And Version

- Canonical name: On the approximation of the values of exponential function
  and logarithm by algebraic numbers
- Subject class: Number-theory research publication
- Stable identifier: arXiv:math/0002047
- Authors: Yuri Nesterenko and Michel Waldschmidt
- Original proceedings record: Mat. Zapiski 2 (1996), 23-42

## License Or Terms

This is external material. Citation does not relicense the source or import its
terms into the repository MIT license.

## Evidence

### Verified

- Main Theorem 1 is stated for arbitrary nonzero complex `theta` and algebraic
  `alpha,beta`, with explicit parameters `A`, `B`, `E`, and field degree `D`.
- Setting `theta=beta` removes the second approximation term exactly.
- The theorem constant is `211D` times three displayed factors and
  `(log E)^-2`.
- For the guest bridge, nonzero dyadic `beta=2im` generates `Q(i)`, so
  `D=2`; the target `alpha` also lies in `Q(i)`.
- The repository's 108/106-bit reduced ratio and 107-bit midpoint-shift
  ceilings admit `log A=109` and `log B=107`.
- With `E=e` and `|beta|<8`, elementary upper bounds make the theorem's natural
  exponent smaller than `169,191,616`; since `log 2>1/2`, the corresponding
  binary exponent is smaller than `338,383,232`.

### Unresolved

The theorem closes separation for midpoint cells satisfying the proved fallback
height ceiling. Product integration must additionally show that every midpoint
probe retained by the Q256 candidate-range handoff stays in that same bounded
family, or narrow the range before relying on the global stage ceiling.

## Sources

- <https://arxiv.org/abs/math/0002047> - identity and abstract; accessed
  2026-09-10.
- <https://export.arxiv.org/e-print/math/0002047> - source TeX containing Main
  Theorem 1 and Theorem 5; accessed 2026-09-10.
