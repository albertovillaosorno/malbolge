# Effective transcendental separation for binary64 atan2

## Status

Active mathematical study

## Research Question

Does correctly-rounded binary64 `atan2` require a genuinely new effective
transcendental-separation theorem, or can the repository close its finite guest
resource bound with a complete domain-specific certificate?

## Background

The guest implementation already resolves special cases, exact small-ratio
cases, and a large retained kernel corpus. For the remaining adaptive midpoint
comparison, current structural proofs bound the reduced rational input ratio to
at most 108 numerator bits and 106 denominator bits. Candidate binary64 cell
midpoints have dyadic denominator shift at most 107.

Those bounds prove that the unresolved family is finite. Finiteness alone is not
a usable runtime resource proof: public `atan2` needs a deterministic precision
or workspace ceiling that is reached before guest addressability is exhausted.

The current normalized scheduler has a sharper operational ceiling. Its last
representable plan is stage 44,739,239: 44,739,241 fractional limbs provide
1,431,655,712 fractional bits, 178,956,964 Taylor terms are requested, and the
`24*N` scratch occupies `0xffffffc0` bytes. The looser `<2^35` total-storage
bound remains useful only when generously rejecting theorem routes.

- Status: Active mathematical study
- Record type: Study
- Planning identity: `effective-transcendental-separation-paper`
- Last reviewed: 2026-09-10

## Prior Work

<!-- jig-ignore-next-line: canonical bibliography path is indivisible -->
- [Fischler-Rivoal exponential transcendence measure](../../bibliography/publications/fischler-rivoal-exponential-transcendence-measure.md)
  provides a completely explicit general exponential route. The repository has
  instantiated its direct tangent bridge and retained the resulting negative
  resource result.
<!-- jig-ignore-next-line: canonical bibliography path is indivisible -->
- [Liang-Wang tangent irrationality measure](../../bibliography/publications/liang-wang-tangent-irrationality-measure.md)
  gives irrationality measure 2 for tangent at nonzero rational arguments, but
  its power-law statement uses implicit constants that cannot be turned into a
  guest precision ceiling as published.
- Lambert's tangent irrationality argument supplies qualitative non-equality;
  the guest midpoint comparator already relies only on directed rational
  enclosures and does not assume an approximate host `atan2` oracle.

## Hypothesis

### Decision Rule

A new general theorem is **not** required if a finite-domain argument proves the
same operational fact. The product obligation is satisfied by either of these
independent outcomes:

1. an explicit separation bound `|tan(m) - a/b| > 2^-B` for every admitted
   midpoint/ratio geometry, with `B <= 1,431,655,712` or another proven guest
   algorithm whose exact resource projection fits the ABI; or
2. a complete finite certificate that covers every admitted geometry, proves
   the same finite maximum precision, and is independently reproducible without
   using the production `atan2` result as its oracle.

The theorem route is rejected for product use if its instantiated worst-case
precision cannot fit the guest resource model. The finite-certificate route is
rejected if its coverage cannot be proved complete rather than sampled.
Publication quality is a later concern and is not part of this decision rule.

## Method

### Fixed product domain

The proof target is deliberately narrower than an unrestricted transcendence
problem. It consumes the already-proved guest invariants:

- reduced ratio numerator bit length `<= 108`;
- reduced ratio denominator bit length `<= 106`;
- candidate midpoint denominator shift `<= 107`;
- Lambert-normalized midpoint denominator shift `<= 108`; this is the joint
  identity `s + max(2*bitlen(u)-s, 0) = max(s, 2*bitlen(u))`, not the loose
  independent sum `107+56`;
- exact candidate-cell construction and directed tangent comparison;
- finite retry plans whose byte projection fails closed before `uint32_t`
  allocation overflow.

No step may replace these exact integers by host `atan`, `atan2`, or an
uncertified floating approximation.

### Existing explicit-theorem baseline

The direct Fischler-Rivoal Proposition 1 specialization is the baseline, not a
promising result. On the retained deep cell, exact repository arithmetic gives
`2*q*t = 2^107`. Its explicit denominator factor alone has a base-two logarithm
strictly greater than `2^437`, before other positive factors are counted. That
is overwhelmingly larger than the `<2^35`-bit maximum guest block and therefore
cannot establish the required runtime ceiling.

This negative result is important: improving implementation constants around
that direct specialization cannot bridge more than four hundred exponent bits
of scale. Any useful theorem specialization must change the quantitative
structure, not merely tighten a small multiplicative factor.

### Irrationality-measure baseline

Liang-Wang's `mu=2` result has the asymptotic shape that would be attractive for
the denominator bound `q < 2^106`. However, without a concrete positive uniform
constant for this dyadic-midpoint family, the statement does not determine any
finite starting denominator or bit precision. The research task is therefore
not "use mu=2"; it is to make every constant executable or find a different
complete certificate.

### Next proof attempt

The next theorem attempt should specialize the generalized Lambert continued
fraction to the repository's dyadic midpoint family before introducing generic
height bounds. Every recurrence denominator, determinant, tail bound, and
normalization factor must be kept as an explicit integer function of:

- midpoint numerator and shift;
- reduced input numerator and denominator;
- continued-fraction depth.

The first stopping calculation is resource viability. If the smallest proven
depth that dominates every `<=106`-bit rational denominator needs more than
1,431,655,712 fractional bits under the current `24*N` scheduler, the route is
retained as a negative result unless a separately proved lower-memory algorithm
exists. Only a bound with an explicit guest resource projection justifies
product adoption.

The first simplification is already positive: normalization has denominator
shift at most 108, not 163. The previous 163 came from adding the independent
107-shift and 56-halving maxima even though the halving count is itself
`max(2*bitlen(u)-s,0)`. Both the near-four and deep-denominator fixtures attain
108, so the replacement is tight for the admitted structural boundary.

## Evidence

Current executable evidence is already retained by:

- `tests/test_c_math_atan2_separation_parameters.py` for the exact finite
  ratio/midpoint geometry;
- `tests/test_c_math_atan2_exponential_bridge.py` for the structural
  exponential bridge;
- `tests/test_c_math_atan2_exponential_measure_budget.py` for the explicit
  Fischler-Rivoal resource rejection;
- the adaptive refinement and midpoint-certificate suites named in the active
  guest-runtime TODO.

This study adds no new numerical separation claim. It makes the decision
boundary explicit so a qualitative theorem, a sampled hard-case corpus, or an
implicit asymptotic constant cannot accidentally be promoted to product
correctness evidence.

## Results

The present evidence answers the narrow necessity question:

- **Some finite global closure is mandatory** for public correctly-rounded
  `atan2` under the bounded guest-resource contract.
- **A genuinely new theorem is not logically mandatory.** A complete
  finite-domain certificate with a proved maximum precision is an equivalent
  engineering closure.
- The direct explicit Fischler-Rivoal specialization is quantitatively unusable
  for the guest ceiling.
- The retained Liang-Wang result is qualitatively promising but not executable
  as a resource proof until its hidden constants are made explicit for the
  required family.

No claim is made yet that the Lambert specialization will meet the resource
ceiling. That is the active proof attempt.

## Threats to Validity

The finite geometry bounds are product-specific. A proof that closes binary64
`atan2` here need not generalize to arbitrary precision, other rounding modes,
or unrestricted rational tangent approximation.

A computational search over many hard cases is not completeness evidence unless
its reduction from the full admitted geometry is proved. Conversely, a very
weak explicit transcendence theorem may be mathematically global while still
being useless under the guest memory contract.

## Conclusion

The mathematics is promoted to P2 because finite global separation/resource
closure is the remaining correctness gate for public `atan2`. The **paper is
not** the gate: publication waits for `publication-grade-paper-pipeline`, and a
complete independently justified finite-domain certificate may close the
product without a new theorem.

The next accepted result must either instantiate a materially stronger explicit
bound below the guest resource ceiling or prove a complete finite certificate.
Until then, `atan2` remains unavailable rather than weakening correct rounding.

## References

- [Academic research methodology and evidence
  model](../methodology/scientific-method.md)
- [Publication-grade paper pipeline](../methodology/publication-pipeline.md)
- [Research Evidence And Algorithm
  Mirror](../adr/research-evidence-and-algorithm-mirror.md)
