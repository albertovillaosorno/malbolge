# Guest C Library Function Boundary

## Purpose

This function owns the guest-visible C library contract and implementations
that execute as ordinary guest code. It separates executable routines from
contracted facilities whose runtime implementation belongs to a later lane.

## Ownership

- Owns: Guest libc declarations and repository-owned guest C implementations.
- Authority: `function.yml` plus the canonical `c-libc-v1.json` specification.

## Prohibitions

- Must not: Resolve guest library calls through host libc or host `libm`.
- Must not: Treat native debug adapters as guest-runtime conformance evidence.

## Navigation

- `contract/include/`: guest headers backed by executable guest code.
- `domain/`: deterministic freestanding implementations of admitted routines.

## Status

Executable v1 memory, narrow-string, exact binary64 math, and canonical
nearest-ties-even `sqrt` are implemented. Allocation
wrappers are now implemented over the one-time startup-bound guest heap core,
but remain unavailable in the canonical libc authority until compiler-generated
startup proves the heap bind before user code. `getchar`/`putchar` wrappers are
also implemented over stable declaration-only byte intrinsics, but remain
unavailable until downstream lowering proves those intrinsic identities execute
selected-profile input/output. Formatting remains unavailable.

Transcendental math is also still unavailable, but an internal raw-bit front
end now resolves proved small-angle `sin`/`cos` results plus the complete
`atan2` zero/infinity matrix. Right-half-plane ratios through `7 * 2^-29` also
resolve when exact binary64
representation or an exact quotient-remainder margin proves the `atan`
alternating-series error cannot cross a rounding midpoint. Normal-binade margins
below the restricted top binade now shrink with the cubic error bound rather
than retaining one fixed threshold.

The entire subnormal ratio range is also resolved, with exact midpoints forced
to the lower neighbor by `atan(r) < r`. Other finite nonzero `atan2` inputs are
reduced exactly to a normalized rational in `[0, 1]` with explicit swap and sign
geometry. A symbolic reconstruction plan then selects base `0`, `pi/2`, or
`pi` plus add/subtract `atan(r)` without using rounded pi bits as authority.

The atan ratio itself is reduced exactly below `169/408` using a symbolic
`pi/4` branch and `(1-r)/(1+r)` when needed. The final `atan2` kernel plan
therefore has the uniform form `k*pi/4 +/- atan(residual)` with `k` in `0..4`,
an explicit sign, and the same exact residual bound. A Machin-series proof also
certifies `pi/4` inside one Q32.192 fixed-point cell.

The C boundary derives all five symbolic bases using 32-bit limb addition only.
Reduced atan residuals enter the same Q32.192 space through directed binary long
division, yielding exact or adjacent floor/ceiling endpoints. A 60-term
alternating-series evaluator then propagates directed fixed-point intervals and
computes the first omitted term `x^121/121` as a directed truncation bound. Its
worst admitted value remains below the proved `2^-160` ceiling; very small
inputs use the direct `x-x^3/3 < atan(x) < x` enclosure instead.

The final finite-nonzero atan2 handoff composes that residual interval with the
certified quarter-pi base into one Q32.192 magnitude plus sign. A nearest-even
endpoint gate publishes an internal binary64 result only when both certified
bounds round to identical bits. That handoff now consults the proved
exact/small-ratio preclassifier first, so values already decided by raw binary64
identities do not fall through merely because Q32.192 cannot represent their
tiny magnitude.

The 64-pair exact-rational authority is therefore 64/64 after composing both
proof paths, while Q32.192 alone still certifies 48/64. A separate Q1152
integer-only oracle directly bounds every series term and certifies the runtime
result bit-for-bit for all 519 deterministic kernel pairs; the 64 shared cases
are cross-checked against the exact `Fraction` authority. A deterministic
continued-fraction proposal search also contributes transformed-branch and
direct-atan sets of eight non-small ratios each. Q1152, not the proposal
arithmetic, certifies both midpoint sides: the transformed set is entirely
within `4e-20` ulp and the direct set within `2e-20` ulp, with each closest case
below `2e-21` ulp.

A Q32.224 integer fallback runs only when Q32.192 cannot publish a unique
binary64 result. It reuses the width-parametric limb core, evaluates 85 atan
terms, and uses a one-cell quarter-pi enclosure derived from Machin 49/14.
Independent `Fraction` evidence encloses and rounds all 16 retained positive
continued-fraction hard cases.

Q32.224 ambiguity now advances to Q32.256. The third stage uses nine limbs,
98 atan terms, and a one-cell Machin 56/16 quarter-pi enclosure. At the directed
Q32.256 ceiling of `169/408`, 97 terms leave more than one Q32.256 cell of
truncation while 98 leave less than one.

A separate authority file checks all 16 hard cases and 512 deterministic
refinements from Q32.224. Q32.256 still fails closed on ambiguity, so the finite
ladder does not prove the full domain.

An independent final-cell certificate avoids the atan evaluator entirely. For
4,164 finite pairs, C supplies only candidate bits; exact dyadic midpoints are
checked with directed rational `sin`/`cos` bounds and exact `y/x` comparison on
the matching tangent branch. Refinement tries 4, 8, 12, 16, 24, 32, then 40
Taylor terms and fails closed while a sign or ratio remains inconclusive.

The deterministic corpus uses all four quadrants of every retained hard ratio,
four near-zero/near-`pi/2` edges, and 4,096 fixed-seed finite nonzero pairs. The
first successful term counts are 1018/13/2080/1053 at 4/8/12/16 terms
respectively;
no retained case needs a later step. Lambert tangent irrationality supplies the
qualitative non-equality needed for eventual exact separation, while guest-C
unbounded refinement storage remains open.

The exact input-ratio height needed by any quantitative separation argument is
now guest-C-owned as well. `malbolge_guest_math_atan2_ratio_reduced_height`
reduces the tangent comparator's actual `|y/x|` geometry with binary GCD and
bitwise exact division, then reports exact numerator, denominator, and maximum
bit lengths without materializing exponent shifts as giant integers. The helper
adds no division-runtime dependency on i686.

There is a tight full-domain structural ceiling of 2,098 bits. Every finite
nonzero binary64 magnitude is an integer multiple `M * 2^-1074`, with
`1 <= M < 2^2098`; reducing a quotient of two such values cannot increase either
integer. The min-subnormal/max-finite orientations attain that ceiling in the
denominator and numerator even though the new axis preproof resolves those
extremes before adaptive refinement.

The adaptive path now has a much smaller tight ceiling. Directed Q256 pi/4
bounds plus `0 < atan(r) < r` resolve `r <= 2^-52` next to pi, `r <= 2^-53`
on the subtracting side of pi/2, and `r <= 2^-55` on its adding side. Together
with the existing zero-axis proof, any remaining kernel input has reduced ratio
height at most 108 bits.

`atan2(1,-nextafter(2^-55,+inf))` attains 108 numerator-height bits. The
reduced rational denominator has a smaller tight ceiling of 106 bits;
`y=0x3ca8000000000001, x=0x3ff0000000000001` attains it. Separation-parameter
publication now fails closed above either ceiling. Across the retained 243
kernel-required refinement cases, the observed maxima are 103 denominator bits
and 102 numerator bits.


Lambert-GCF argument geometry is now explicit as well. For a reduced dyadic cell
boundary `m=u/v`, guest C publishes numerator bits, denominator shift, and a
strict power-of-two ceiling for `u^2/v`. Candidate-cell geometry keeps `u`
within 54 bits and gives the full `<4` angle range `u^2/v < 2^56`; ceiling 56 is
attained structurally near the upper angle binades. A 54-bit numerator over
`2^107` instead has ceiling 1.

This isolates the exponential factor that a future explicit continued-fraction
growth/error proof must dominate. The same query now publishes a canonical
normalization plan: halve the angle `max(E,0)` times when the strict scale
ceiling is `2^E`. At most 56 halvings are required; the normalized denominator
shift remains at most 163 and the resulting Lambert scale ceiling is at most
zero. This is a GCF preparation step, not itself a tangent-separation bound.


A one-step directed transport primitive now backs that finite normalization
route. `malbolge_guest_math_fixed_sincos_double_interval` applies
`sin(2x)=2sin(x)cos(x)` and `cos(2x)=cos(x)^2-sin(x)^2` to signed fixed-point
intervals. It stages all results in caller-owned `12*N` scratch and publishes
only when both input signs are proved; a sign-crossing input returns
`proven=0`, while malformed input, overflow, or short scratch fail without
publication.

Multi-step transport is now caller-owned too:
`malbolge_guest_math_fixed_sincos_double_transport` keeps the four current
endpoints in scratch and reuses the one-step `12*N` operation workspace, for a
`16*N` total. It accepts 0..56 doublings, publishes only after every requested
step succeeds, and returns `proven=0` without touching caller outputs if a later
step loses a proven sign.

Exact evidence covers zero-step copy, three exact steps in both signs,
unresolved-after-progress atomicity, and hard ceilings for 57 steps or short
scratch.

The normalization pipeline is now executable end to end for signed dyadic
midpoints. `malbolge_guest_math_dyadic_normalized_sincos_interval` applies the
Lambert halving plan to the exact dyadic, evaluates directed Taylor sin/cos only
at that normalized small argument, and transports the enclosure back through
all requested doublings. It uses caller-owned `20*N` scratch and keeps
insufficient fixed precision as `proven=0`; malformed terms or short scratch
remain non-mutating hard failures.

Independent `Fraction` Taylor authority at the original angle encloses `+/-3/4`,
a negative 107-bit-shift dyadic, and the structural near-four case that performs
all 56 doublings. Q128/16 resolves those retained cases, including the 56-step
path, but that is bounded coverage rather than a full-domain precision ceiling.


A parallel midpoint comparator now consumes that normalized sin/cos path before
the existing branch-rank and cross-product logic. It requires caller-owned
`24*N` scratch and keeps the same `-1/0/+1` semantics as the direct comparator.
Across 64 signed hard cells Q192/16 agrees exactly with the direct path; the
first hard lower boundary intentionally remains `0` at Q128, preserving retry.

A near-four boundary against `atan2(1,1)` also agrees after all 56 doublings.
The production refinement scheduler still uses the direct comparator.

A parallel normalized refinement scheduler now preserves the same open stage
progression while accounting for its larger workspace. Stage `s` still uses
`fraction_limbs=s+2` and `terms=4s+8`, but requires `24*(s+3)` limbs instead of
`15*(s+3)`. Across the retained 4,164-pair corpus, 3,921 cases remain
special and
all 243 kernel cases certify: 211 first certify at Q128/16 (stage 2) and 32 at
Q192/24 (stage 4), with none first certifying at stages 0, 1, or 3.

The first retained hard seed publishes stage 2/120 limbs when only 119 are
available, advances to stage 4/168 at 167 limbs, and certifies there with 168.
This is fallback-policy evidence; the cheaper direct scheduler remains primary.

Normalized plans have their own allocation-neutral byte query rather than being
reinterpreted by the direct 15*N contract. Stages 0..4 translate to 288, 384,
480, 576, and 672 bytes at alignment 4. The largest normalized plan whose byte
extent fits in `uint32_t` is stage 44,739,239 at `0xffffffc0` bytes; the next
plan remains valid in limbs but its byte conversion fails without publication.

This height bound is exact structural evidence, not yet a quantitative
irrationality measure for `tan(midpoint)`. Lambert still supplies only the
non-equality/qualitative termination fact currently admitted by the repository.

The runtime now packages the two finite inputs to such a future bound in one
atomic query. `malbolge_guest_math_atan2_separation_parameters` validates a
kernel-required `(y,x)` and same-sign candidate cell, then publishes the exact
reduced ratio height together with the denominator shifts of both dyadic cell
midpoints and their maximum. A sign-mismatched candidate rejects without
publication.

Independent `Fraction` evidence covers a hard positive cell, its signed mirror,
and a 108-bit axis-boundary cell that remains kernel-required. Reported ratio
heights and both midpoint shifts agree exactly. These parameters remain
structural inputs only: the existing proof that actual fallback midpoint shifts
are at most 107 is separate from the still-missing quantitative tangent
separation inequality.


A second structural query prepares a route through exponential transcendence.
For a reduced comparator ratio `t=a/b` and midpoint `m`, set `z=e^(2im)` and
`P(X)=(a+ib)X+(a-ib)` over the Gaussian integers. The exact tangent identity
makes `P(z)=b(z+1)(t-tan(m))`, so any explicit lower bound on `|P(e^(2im))|`
would imply `|t-tan(m)| >= |P(e^(2im))|/(2b)`.

`malbolge_guest_math_atan2_exponential_bridge_bounds` publishes only integer
size bounds needed by such a theorem. It gives `H(P)<2^E`, plus per-midpoint
power-of-two ceilings for the minimal-polynomial height of `alpha=2im`, the
algebraic denominator of `1/alpha`, and `max(1,|1/alpha|)`. Combining the exact
2,098-bit ratio-height ceiling with the separately proved fallback midpoint
shift ceiling plus the post-special 108-bit ratio-height ceiling gives
`H(P)<2^109`, `H(alpha)<2^218`, inverse-denominator bit length at most 109, and
inverse-house exponent at most 106. These are resource
parameters only; no transcendence-measure constant is assumed by guest C.


The quantitative source candidate is now canonicalized in
as the Fischler-Rivoal exponential-transcendence record under
`docs/bibliography/publications/`.
For the repository specialization `K=Q(i)`, algebraic degree `d=2`, and linear
polynomial degree `delta=1`, the paper's stated height exponent is 11. Applied
only to the `H(P)` term, that exponent contributes fewer than 1,199 binary
exponent bits. The tight 106-bit rational-denominator ceiling makes the bridge
factor `2b<2^107`, raising the nominal subtotal to 1,306.

The paper's explicit correction and alpha-dependent constant are not yet
instantiated, so this subtotal is not a precision/resource proof.

The C substrate also owns exact candidate-cell geometry before tangent
refinement. `malbolge_guest_math_atan2_cell_midpoints` emits both boundaries as
signed dyadics with a 64-bit numerator plus power-of-two denominator. Both
signed zeros share `[-2^-1075,+2^-1075]`; candidate magnitudes at four or above
reject without publication. Across the same 4,164 candidates, both C dyadics
match independently constructed `Fraction` midpoints exactly.

A real adaptive fallback never needs the zero-cell shift: right-half-plane
kernel-required
ratios have normalized exponent at least `-53`, and the minimum non-dyadic
excess `2^-106` dominates the cubic atan error `<2^-156/3`. Hence the true
angle stays above `2^-53`, whose finest neighboring midpoint uses shift 107;
left-half-plane angles are larger still.

The first caller-owned refinement workspace primitive now converts any exact
midpoint dyadic into little-endian base-`2^32` magnitude limbs at a requested
binary fractional precision. A separate planner returns the exact limb count
before writing; insufficient capacity rejects without touching the buffer, and
no guest heap or startup state is consulted. The retained workspace test checks
exact integer reconstruction through 4,096 fractional bits and separately plans
`UINT32_MAX` fractional bits without allocating that storage.

Variable-width arithmetic now extends beyond input materialization. Fixed-point
multiplication accepts caller-owned `2*N` product scratch, returns a floor plus
an explicit discarded-bit flag, and rejects high product overflow before
publishing output. Small-integer floor division supports in-place quotient
publication and every nonzero `u32` divisor. Exact Python-integer differentials
cover 4, 8, 16, and 128 limbs, including `UINT32_MAX` division; short scratch,
zero divisors, and overflowing products stay fail closed.

Directed interval arithmetic now sits on the same variable-width core. Checked
add/subtract reject carry or underflow before result publication. Product ceil
uses the same caller-owned `2*N` scratch as floor and increments only when
fractional product limbs were discarded; an increment beyond the configured
width rejects atomically. Small division has matching floor/ceil entry points,
and ceil increments exactly when the long-division remainder is nonzero.

Independent integer evidence exercises these operations through 128 limbs,
including in-place division and the ceil-only product-overflow edge.

A variable-width interval layer now composes those primitives without partial
endpoint publication. Nonnegative interval add/subtract prevalidate both bounds;
interval product stages floor(lower*lower) and ceil(upper*upper) in caller-owned
`4*N` scratch before copying either result. Small interval division stages both
bounds in `2*N` scratch. Every operation rejects inverted input intervals, and
integer authority covers 4/8/16/128 limbs plus malformed, overflow, underflow,
and undersized-scratch failures.

The shared Taylor recurrence is now executable at variable width as well.
`malbolge_guest_math_fixed_taylor_term_interval` computes the directed enclosure
of `term*x^2/divisor` with the same caller-owned `4*N` scratch; no additional
workspace is introduced between multiplication and division. Integer authority
covers 4/8/16/128 limbs with the first sine/cosine recurrence divisors
`6/20/42/72` and pins malformed, zero-divisor, short-scratch, and ceil-overflow
rejection. Full summation still needs signed endpoint accumulation because
partial sine/cosine sums over the admitted `|midpoint|<4` range can cross zero.

Signed-magnitude accumulation now handles the sign crossings needed by Taylor
partials. `malbolge_guest_math_fixed_signed_add` adds equal-sign magnitudes,
subtracts the smaller magnitude for opposite signs, and canonicalizes every zero
result to positive zero. Carry overflow and invalid sign selectors reject before
magnitude or sign publication. Integer authority exercises positive/negative
sums, both subtraction directions, exact cancellation, and negative-zero input
through 4/8/16/128 limbs.

Signed interval accumulation now stages both endpoints before publication.
`malbolge_guest_math_fixed_signed_interval_add` orders sign+magnitude endpoints
numerically, computes lower+lower and upper+upper into caller-owned `2*N`
scratch, revalidates the staged result, and only then copies magnitudes and sign
bits. Zero signs are canonicalized by the scalar signed primitive. Independent
fixtures exercise cross-zero intervals through 128 limbs and pin malformed
inputs, short scratch, invalid sign selectors, and upper-only carry overflow as
nonpublishing failures.

Complete variable-width Taylor summation now composes the recurrence and signed
interval layers. For exact/nonnegative `0 <= x < 4`, sine starts from `x` and
cosine from one; each requested term is added with alternating sign, then one
additional directed term supplies the first-omitted remainder interval.
`terms >= 2` is required so the remaining tail is monotonically decreasing over
this range. The implementation uses one caller-owned `10*N` workspace and
publishes only after the complete enclosure succeeds.

Independent `Fraction` authority covers 4/8/12/16 terms at `1/8`, `1`, `5/2`,
and `4 - 2^-224` without host trigonometric functions.

Positive ratio/tangent comparison now avoids fixed/fixed division entirely.
The kernel ratio is reconstructed as `|y/x|` even when its normalized input was
swapped. Exact 53-bit significands multiply directed sin/cos endpoint integers,
with the binary exponent retained as a virtual left shift on the appropriate
cross product.

Each 53-bit significand multiplies into `N+2` limbs. Bit-length and shifted-bit
comparison handle exponent deltas without materializing zero limbs, so a
`2*(N+2)` caller-owned scratch covers the entire finite binary64 ratio span,
including subnormal extremes. Comparison returns `-1`, `0`, or `+1` only when
the ratio lies below, overlaps, or lies above the tangent enclosure.

Algebraic fixtures now cover ratios from `2^-1074` through `2^1074`, both
swapped directions, and the unresolved equality case without host trig.

Positive midpoint orchestration now connects the variable-width proof path end
to end. `malbolge_guest_math_positive_midpoint_compare` requires an exact
positive dyadic boundary, materializes it at caller-selected whole-limb
precision, computes signed sine/cosine Taylor enclosures, then invokes the exact
cross-product ratio comparator only when all four trig endpoints prove the
positive tangent branch. One caller-owned `15*N` workspace covers the dyadic,
four trig endpoints, and reused series/product scratch. If the selected
precision
cannot represent the dyadic denominator exactly, the operation returns
unresolved rather than approximating the boundary.

At eight fractional limbs with 16 Taylor terms, the full C route certifies both
midpoints of all sixteen retained positive hard-rounding cells: each angle is
strictly above its lower boundary and below its upper boundary. A one-limb probe
on the same corpus remains unresolved as expected when the dyadic needs more
fraction bits.

Signed midpoint branch classification now extends the variable-width proof path
to the full principal `atan2` range. Proven sine/cosine signs map boundaries to
quadrant ranks `0..3`; positive midpoints whose signs imply the wrapped negative
quadrant become rank `4`, while negative midpoints whose signs imply the wrapped
positive quadrant become rank `-1`. If the input angle rank differs, ordering is
resolved before any tangent product. Same-rank comparisons reuse exact products
on absolute sine/cosine bounds and reverse the magnitude result when tangent is
negative.

All four sign combinations of each of the sixteen retained hard ratios certify
both binary64 cell boundaries at eight fractional limbs and 16 terms. Synthetic
midpoints `+1`, `-1`, `+3.5`, and `-3.5` independently pin rank ordering
and both
principal-range wrap adjustments without a pi constant.

A full-cell refinement attempt now packages the two boundary checks atomically.
`malbolge_guest_math_atan2_refinement_attempt` accepts only finite non-special
kernel work, reconstructs the candidate cell, and publishes `certified=1` only
when the angle is strictly above the lower midpoint and strictly below the upper
midpoint. Directed overlap or insufficient representable precision succeeds with
`certified=0`, so callers can retry at greater precision. Invalid scratch,
special inputs, or malformed candidates fail without changing the certification
flag.

All 64 signed hard cells certify at eight fractional limbs and 16 terms. A
one-limb request and an adjacent wrong binary64 candidate both remain cleanly
uncertified, while short scratch and the exact `y=x` special case are pinned as
nonpublishing hard failures.

A deterministic retry-distribution corpus now exercises the refinement attempt
across signed hard cells, four edge pairs, and 4,096 finite-nonzero LCG pairs.
Of 4,164 total pairs, 3,921 now resolve before the kernel and 243 require kernel
work. At 16 Taylor terms, Q64 certifies 188 kernel cells and Q96 certifies 211;
Q128 certifies all 243. Holding Q128 fixed, 4/8/12/16 terms certify
21/26/139/243 respectively.

These counts are scheduling evidence, not a precision or termination bound. They
pin that both dimensions can independently cause retries and that a future
policy must grow capacity as well as Taylor depth rather than assuming either
one is sufficient alone.

Refinement scheduling is now executable and stateless. Stage `s` requests
`s+2` fractional limbs, `4s+8` Taylor terms, and `15*(s+3)` caller-owned scratch
limbs, so both numerical dimensions grow on every retry. The driver validates
input and candidate geometry before capacity handling, attempts every stage that
fits the supplied scratch, and returns either the certifying plan or the first
unattempted plan whose exact scratch requirement exceeds capacity.

A retained hard seed therefore reports stage 0/Q64/8 at 44 limbs, stage 1/Q96/12
after exhausting 45 limbs, stage 2/Q128/16 after exhausting 60 limbs, and
certifies stage 2 once 75 limbs are available. An adjacent wrong candidate
remains uncertified and requests stage 3 rather than being accepted.

The Taylor recurrence no longer multiplies `(2n)(2n±1)` into one divisor.
Each directed term first multiplies by `x^2`, then divides successively by the
two positive `u32` factors; repeated floor on the lower endpoint and repeated
ceil on the upper endpoint preserve enclosure. This removes the former stage
8190 divisor-product ceiling without increasing the `4*N` recurrence scratch.

Planning is now limited first by the public `u32` scratch-capacity ABI rather
than a selected numerical precision. Stage 286331150 remains representable,
requesting 286331152 fractional limbs, 1145324608 terms, and exactly
`UINT32_MAX` scratch limbs; the next stage fails before publication because its
scratch requirement is not representable. This is still a finite machine limit,
not a full-domain termination proof.

Q256 can now produce conservative binary64 candidate cells even when endpoint
rounding is not unique. The fixed interval extractor rounds both directed
endpoints with the same integer nearest-even helper used by the unique path and
publishes one cell when they agree or two cells only when the rounded results
are adjacent. Any wider span or malformed interval fails before publication.

A synthetic Q256 interval straddling the exact midpoint `1 + 2^-53` by one Q256
unit yields exactly `1.0` and its next binary64 neighbor. A span whose endpoint
roundings differ by two cells is rejected. Across the retained 4,164 atan2
pairs,
Q256 still produces one candidate matching the existing unique handoff; this is
coverage rather than a claim that all Q256 atan intervals span at most two
cells.

Candidate certification composes that proposal set with the adaptive scheduler.
At every stage all one or two ordered adjacent candidates are attempted; exactly
one certification publishes a result, zero certifications request refinement,
and two certifications are treated as inconsistent hard failure. Positive and
negative hard seeds pin the reversed binary64 ordering for negative angles, and
a manual `{correct, adjacent}` list certifies only the correct cell at Q128/16.

`malbolge_guest_math_atan2_q256_refine_available` joins Q256 extraction and this
multi-candidate scheduler for caller-owned fallback work. No natural two-cell
Q256 atan2 input is retained yet, so the two-cell proposal geometry and the
multi-candidate transcendental certification remain independently evidenced.

Q256 candidate production now also has an unbounded-by-cell-count range form.
`malbolge_guest_math_fixed256_candidate_range` publishes the nearest-even
roundings of the directed endpoints without requiring them to be adjacent; for a
negative atan2 interval the endpoints are reversed into increasing angular
order.
The earlier one/two-cell extractor remains a conservative convenience, not a
completeness requirement.

Adaptive range refinement maps positive binary64 bits directly to monotone keys
and negative bits through bitwise complement, so the same integer binary search
works on both signs. Each probed cell compares the real angle against its lower
and upper dyadic midpoints. Strictly-below/above classifications discard half
the
range at the current stage; an inconclusive directed comparison advances Taylor
precision without discarding cells; strict interior ordering certifies the cell.

A synthetic Q256 interval spanning three rounding cells is represented as the
range `1.0 .. 0x3ff0000000000002` even though the two-candidate extractor
rejects
it. A deliberately skewed 12,289-cell range around a retained hard seed shrinks
to at most five cells at Q64/8 and certifies the exact cell at Q128/16, for both
positive and negative angles. The Q256 range wrapper composes endpoint proposals
with this binary-search scheduler using the same caller-owned scratch.

This removes candidate-count enumeration as an adaptive blocker: any same-sign
finite Q256 endpoint range below four can be searched without materializing its
interior cells. It still does not prove that the directed refinement reaches a
certificate before the finite scratch-capacity ABI ceiling.

The fixed-Q ladder and adaptive range search now compose through a single
caller-owned handoff. Special cases and Q192/Q224/Q256 unique results publish a
`FAST_RESOLVED` result without requiring scratch. Only a genuinely non-unique
Q256 interval enters range refinement; absent or undersized scratch reports
`RETRY` with the exact first required plan instead of converting capacity into
hard failure.

The ambiguous branch is independently injectable through
`malbolge_guest_math_atan2_refine_q256_interval_available`, which consumes an
already-computed directed Q256 interval. A synthetic wide interval around a
retained hard seed pins the complete state sequence: no scratch reports
stage-0/45-limb retry, 60 limbs preserves a narrowed range and requests
stage-2/75 limbs, and 75 limbs publishes `REFINED_RESOLVED` with the retained
binary64 cell. A sign-inconsistent injected interval fails before output
mutation.

The real `malbolge_guest_math_atan2_handoff_available` repeats the current fixed
ladder explicitly so it can distinguish calculable Q256 ambiguity from hard
failure. On 512 deterministic finite pairs it agrees with the existing fixed-Q
handoff while requiring no scratch. No retained natural input enters its
adaptive
branch yet, so the injected interval is integration evidence rather than an
observed Q256-ambiguous atan2 case.

Adaptive handoff retries are now resumable caller-owned state. Progress records
the original raw `(y_bits,x_bits)`, narrowed candidate range, and first
unattempted refinement plan.
`malbolge_guest_math_atan2_resume_handoff_available`
checks the input identity and recomputes the planner tuple before continuing the
saved range, so increasing scratch does not repeat Q192/Q224/Q256 evaluation or
throw away binary-search progress.

The injected hard interval pins an actual three-call ownership sequence: the
first call without scratch returns stage 0; resuming that progress with 60 limbs
narrows the range and returns stage 2; resuming only that saved state with 75
limbs certifies the hard binary64 cell. Tampering with `(y_bits,x_bits)` or the
saved term count is rejected before output publication.

The narrowed range itself remains caller-owned internal state and is expected to
be preserved byte-for-byte between calls; the identity/plan checks prevent
accidental cross-input or stale-plan reuse, not hostile forgery. This is an
internal runtime contract rather than a security boundary.

Refinement plans now expose an allocation-neutral storage projection.
`malbolge_guest_math_atan2_refinement_scratch_requirement` validates a planner
result, returns its exact 32-bit limb count, converts that count to a `u32` byte
extent with checked multiplication by four, and reports 4-byte alignment. The
function never observes startup or heap state.

The guest heap's existing 16-byte payload alignment is therefore sufficient for
all such scratch. Stages 0/1/2 require 180/240/300 bytes. The largest planner
stage whose limb array is still representable as a guest allocation extent is
stage 71,582,785: 1,073,741,820 limbs and `4,294,967,280` (`0xfffffff0`) bytes.
Stage 71,582,786 remains a valid limb plan but byte projection rejects before
publication because the required extent exceeds `UINT32_MAX`.

This is a compatibility/query surface, not permission for math to call `malloc`.
Allocation wrappers remain authority-unavailable until compiler startup proves
heap binding before user code, so caller-owned storage remains the active math
contract.

Test-only integration now proves that the existing explicitly bound guest heap
can satisfy the same caller-owned refinement lifecycle without changing math
ownership. Before binding, a 300-byte runtime allocation reports
`NOT_INITIALIZED`. After binding a 1,024-byte aligned arena, the synthetic hard
retry sequence allocates 180 bytes, resizes to 240 and 300 bytes as plans grow,
certifies the hard cell, releases the block, and successfully allocates again.

The normalized fallback has equivalent test-only heap evidence after the same
explicit bind. Its retained hard seed grows scratch through
288 -> 384 -> 480 -> 576 -> 672 bytes, certifies at normalized stage 4, then
releases and reuses the arena. Production math remains allocator-free.

This evidence links the byte query to real guest-heap semantics, including
resize
and release, but production math still never calls the allocator. The test binds
the heap explicitly inside its own process; compiler-generated startup must
still
prove that equivalent binding occurs before user code before allocator-owned
transcendental scratch or public allocation can be admitted.

Exact normal ratio midpoints are algebraically impossible for valid 53-bit input
geometry: after 52 quotient bits the remainder retains the denominator's full
power-of-two divisor, while `D/2` has one fewer. The defensive midpoint branch
remains fail closed. For `e=-28..-53`, writing `D=2^t*d` with odd `d` gives a
minimum non-midpoint separation of `1/(2d)` ulp.

The runtime now compares that actual odd denominator against `3*2^(m-1)`,
`m=-(2e+55)`, before long division; this strictly dominates the earlier bound
that replaced `D` by `2^53`. A separate integer long-division helper rounds the
original rational to nearest-even binary64 when a later kernel needs a bounded
floating representation.
