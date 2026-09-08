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
