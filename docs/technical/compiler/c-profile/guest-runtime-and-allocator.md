# Guest runtime and allocator

## Status

Active implementation

## Purpose

Implement startup, calling convention, frames, allocation, streams, integer
helpers, strings, deterministic math helpers, scheduling primitives, and other
runtime facilities as code that ultimately executes under Malbolge semantics.

## Scope

This document governs the following declared TODO scope:

- `tools/tidy/`
- `src/runtime/`
- `docs/technical/specification/`
- `tests/tidy/`
- `tests/runtime/`
- `tests/test_guest_runtime_c.py`

## Current Behavior

### Versioned runtime authority

`src/runtime/guest-runtime/contract/guest-runtime-v1.json` is the
runtime-specific
version-one authority layered on top of the existing C ABI and target profile.
It freezes status identities, guest-heap metadata geometry/policy, startup
binding behavior, the canonical-frame authority reference, byte-I/O intrinsic
symbols, and the prohibition on host fallback. It does not duplicate the full C
ABI or target profile; tests require its C projection to match those
authorities.

`tests/test_guest_runtime_authority.py` checks the C status/heap constants and
metadata offsets against this runtime contract, frame fields against
`c-abi-v1.json`, EOF/alignment against the selected `malbolge.json` profile/ABI,
and confirms that implemented allocation/byte wrappers remain source-unavailable
until their integration gates complete.

### Implemented runtime core

`src/runtime/guest-runtime/` is a governed C function that owns the first stable
lane-8 runtime semantics. `contract/guest_runtime.h` defines fixed status
values,
16-byte heap alignment/header geometry, the current profile EOF word, a caller-
owned heap state, and byte-stream conversion entry points. The contract uses
fixed `uint32_t` extents so guest semantics do not inherit native `size_t` or
pointer serialization.

The heap domain is a deterministic first-fit arena allocator. Every block begins
with a canonical 16-byte little-endian header containing span, requested extent,
allocation state, and a zero reserved word. Allocation uses checked 32-bit
extent
arithmetic and 16-byte payload alignment, splits useful free remainders,
coalesces adjacent free blocks, and trims a free tail. Every public heap
operation validates the complete canonical block chain before mutation, so even
a corrupt later header prevents an earlier allocation/free/resize from changing
state or publishing a result. Zero-size allocation has

the implementation-defined C choice of deterministic null. Zeroed allocation
checks multiplication overflow before publication. Resize preserves the old
allocation on exhaustion and either changes the block in place or copies the
lesser of old/new requested bytes before releasing the old block. A nonnull
zero-size resize is outside this contracted path because C23 makes that call
undefined; the core reports an invalid request rather than defining guest C
semantics for undefined behavior.

The frame domain consumes the canonical `malbolge-c32-v1` hidden call-frame
layout without inventing another runtime ABI. It encodes/decodes the exact
32-byte little-endian field sequence, requires a 16-byte-aligned frame extent of
at least 32 bytes, requires the ABI-mandated argument-block pointer, and rejects
nonzero version-one flags. Encoding validates and stages bytes before publishing
them; decoding stages all fields and validates before mutating its output.
Native return addresses and native stack metadata never enter this codec.

The byte-stream domain has no host I/O. Current-profile input words `0..255` map
to C `int` values, EOF word `4,782,968` maps to `-1`, impossible intermediate
words are rejected, and output is the low eight bits of the supplied C value.

Guest startup now has an explicit one-time heap-binding domain. Allocation
requests before binding fail as `NOT_INITIALIZED`; an invalid bind leaves state
uninitialized; the first successful bind initializes/zeroes the guest arena; and
later rebind attempts fail as `ALREADY_INITIALIZED`. The four public allocation
wrappers (`malloc`, `calloc`, `realloc`, and `free`) delegate only to these
startup-bound guest-runtime entry points. Their wasm32 source compiles under the
strict guest profile and their native relocatable object has exactly the four
expected guest-runtime undefined symbols and no host allocation dependency.

These allocation functions intentionally remain *unavailable* in the canonical
`malbolge-libc-v1` authority until compiler-generated startup proves the heap
bind occurs before user code.

Byte I/O now has stable declaration-only compiler intrinsic identities and
public `getchar`/`putchar` wrapper source. The input wrapper invokes the
intrinsic word, uses the pure profile-word decoder, and returns byte-or-`EOF`;
output reduces the C value to its low eight bits, invokes the output-byte
intrinsic, and returns the emitted unsigned byte. The selected profile output
effect is infallible, so its `putchar` specialization always returns that
emitted byte. Independent test intrinsics execute these wrappers without host
streams. The production object depends only on the two intrinsic symbols plus

the pure mapping helpers. The routines intentionally remain
*unavailable* until `ternary-machine-lowering` proves the intrinsic identities
realize the selected-profile `/` and `<` operations.

### Typed bounded-formatting kernel

`src/runtime/guest-runtime/contract/guest_format.h` and `domain/format.c`
implement an internal, typed formatting kernel below the public printf family.
The kernel owns exact signed/unsigned integer conversion for bases 2, 8, 10,
and 16, sign/prefix/width/precision padding, narrow-string precision, character
fields, bounded destination writes, final-null reservation, and an exact
would-have-written `u32` count. Large discarded width/precision is accounted in
constant work per emitted segment rather than by looping over bytes that cannot
fit the destination.

The typed kernel deliberately does not consume `va_list` or format floating
values. `guest_format_parse.h` and `format_parse.c` now own a separate C23
narrow
format tokenizer. Literal spans, escaped percent, flags, literal/dynamic width
and precision, classic and `wN`/`wfN` length modifiers, and closed conversion
tags are preserved without consuming arguments. Decimal overflow, incomplete
directives, and unknown specifiers fail before token publication. A separate
directive-admission step then enforces C23 conversion/length/precision/flag

relationships and limits guest `wN`/`wfN` support to 8, 16, 32, and 64 bits.

The canonical promoted-block vararg cursor and transactional argument resolver
consume dynamic width/precision plus the main promoted value without partial
cursor advancement. A scalar executor completes `d/i/u/o/x/X/b/B/c/p/%`
through the typed kernel, including post-promotion `hh`/`h`/`wN` narrowing by
explicit bits. C permits `%p` output to be implementation-defined, so the guest
contract fixes null as `0` and non-null object pointers as lowercase `0x` plus
the canonical 32-bit guest pointer encoding. No host address is exposed.

`%lc` fails closed because version one defines `wchar_t` but has no `wint_t`
authority.

`guest_format_memory.h` and `format_memory.c` add the separate guest-memory
execution boundary required by narrow `%s` and integer `%n`. One caller-proven
live object supplies backing bytes, an extent, and its encoded object-pointer
base. Every supplied pointer is decoded by the ABI's logical-byte-offset-plus-
one rule and must remain inside that object. Count stores additionally require
the destination type's natural alignment and complete byte extent.

Narrow `%s` scans only within the proven object and may stop at precision before
a null byte. Without that precision stop, a missing in-object terminator fails
before sink publication. `%n` first proves the current would-have-written count
fits the signed destination selected by the admitted integer length modifier.
It then writes canonical little-endian bytes without changing the sink count.

Invalid, null, one-past, misaligned, or overflowing accesses leave the owned
state unchanged. Wide `%ls` remains fail-closed and no host pointer is exposed.

`guest_format_float.h` and `format_float.c` own hexadecimal floating execution
for binary64 `%a`/`%A` and binary128 `%La`/`%LA`. The implementation consumes
resolved raw 64/128-bit representations directly and performs no floating
arithmetic or `__int128` operations. Every nonzero finite value is normalized
to a leading hexadecimal `1`; subnormal exponents can therefore extend through
`-1074` for binary64 and `-16494` for binary128.

Missing precision emits the minimum trailing-zero-trimmed hexadecimal fraction
needed for the exact value. Binary64 has 13 exact hexadecimal fraction digits
and binary128 has 28. Smaller explicit precision rounds discarded nibbles with
the ABI-fixed nearest-ties-even rule; larger precision appends exact zero digits
without iterating over bytes that cannot fit the sink.

`#` forces the point, `0` pads after sign/base for finite values, and special
values use deterministic `inf`/`nan` or `INF`/`NAN` spelling. Negative zero and
the sign bit of NaNs are preserved textually. Length `l` has the C-defined no-op
meaning for binary64; `L` selects the binary128 path.

`guest_decimal_exact.h` and `format_decimal_exact.c` provide bounded exact
sources for decimal binary64 and binary128 formatting. A finite magnitude is
represented as a canonical nonzero decimal digit sequence times
`10^decimal_shift`; removable trailing zeroes move into the shift. Binary64
retains its fixed 768-byte result and 192 base-10000 limbs.

Binary128 uses a separate 11,564-byte result and 2,891-limb scratch: the true
worst case is the minimum-normal exponent with the maximum 113-bit significand,
whose exact numerator has 11,563 decimal digits at shift `-16494`. Shared
multiplication operates through an explicit-capacity limb view, so the larger
binary128 bound does not inflate binary64 scratch. Power-of-two and
power-of-five scaling uses only 32-bit multiply/carry operations, avoiding
64-bit division and host
floating helpers.

`format_float_decimal.c` consumes either exact representation for scientific
`%e`/`%E`. Omitted precision means six digits after the decimal
point; explicit precision is rounded decimal nearest-ties-even, and carry may
advance the scientific exponent. The exponent always has a sign and at least
two digits.

`#` forces the decimal point, finite `0` padding follows the sign, and special
values ignore zero padding just like the hexadecimal path. Precision beyond the
exact digit sequence becomes virtual zeroes, so truncation work is bounded by
the actual sink rather than requested discarded output.

Fixed `%f`/`%F` uses the selected binary64 or binary128 source. It rounds
`value * 10^precision` to an integer with decimal nearest-ties-even and then
places exactly `precision` fractional digits. Cases whose requested precision
extends beyond the exact value use virtual trailing zeroes; values that round to
zero, cross an integer power of ten, or have no retained pre-rounding digit are
handled explicitly without host arithmetic.

General `%g`/`%G` rounds to the requested significant-digit precision
before selecting the C general style. Precision zero becomes one significant
digit. A rounded exponent below `-4` or greater than or equal to the precision
selects scientific notation; otherwise fixed notation is used. Unless `#` is
present, trailing fractional zeroes and a now-unused decimal point are removed
without removing zeroes required by the integer magnitude.

The C23 `snprintf`/`vsnprintf` contract still requires full formatted-output
semantics, including the same would-have-written result under truncation. These
formatting layers are implementation substrate only; public routines remain
contracted-unavailable while compiler lowering has not bridged source `va_list`
state into the canonical promoted-block cursor and wide `%ls` remains without a
completed execution policy.

Independent C vectors lock decimal/hex/octal/binary integer output,
INT64_MIN, alternate prefixes, precision-versus-zero padding, left/right width,
string precision, character fields, truncation, null-capacity behavior,
count-overflow rejection, and corrupted-sink rejection. Parser vectors cover
literal/conversion streaming, `%b`/`%B`, dynamic fields, classic and specific-
width modifiers, decimal-overflow rejection, malformed directives, and error
non-publication.

Vararg/resolution vectors cover natural guest alignment, 32/64/128-bit promoted
values, negative dynamic fields, rollback on late failure, promotion-aware
scalar narrowing, and exact guest-pointer `%p` text. Guest-memory vectors cover
bounded precision without a terminator, required termination, logical-pointer
range, `%n` width/alignment, little-endian stores, count representability, and
rejection atomicity. Hexadecimal-floating vectors cover exact/default precision,
`#`, sign/zero/left padding, normalized subnormals, signed zero, infinity/NaN,
explicit precision beyond exact binary width, ties-to-even, truncation,
binary128 extremes, and fail-closed decimal/dynamic-field inputs.

Windows i686/x64/ARM64 syntax checks, native execution, and wasm32 symbol
inspection keep the formatting layers independent of host formatting. The typed
vectors also pass pinned ASan/UBSan and path-sensitive Clang analysis where
those host assets are available.

### Exact binary64 math

`src/runtime/guest-c-library/domain/math_exact.c` implements `fabs`, `floor`,
`ceil`, and `trunc` directly from the ABI-fixed binary64 representation. WG14
records these operations as exact and independent of the current rounding
mode. The implementation uses representation-level masks only: signed zeros,
subnormals, integral values, and infinities retain their required semantics,
and every NaN publishes the ABI canonical quiet payload-zero NaN.

The no-CRT guest-libc harness locks exact result bits for positive/negative
zero, fractional boundaries, minimum subnormals, infinities, quiet NaNs, and
signaling NaNs. A separate fixed-seed 274-pattern differential reconstructs each
finite input as an exact rational and independently derives the expected result
bits. The wasm32 guest object has no library dependency beyond target
stack machinery at unoptimized codegen. Windows MSVC objects expose only the
compiler's `_fltused` marker; the test harness supplies that marker without
adding a host `libm` implementation.

`fabs`, `floor`, `ceil`, and `trunc` are therefore executable in
`malbolge-libc-v1`. Canonical `sqrt` is executable as well: `math_sqrt.c`
normalizes the binary64 significand, streams the conceptual 106-bit scaled
radicand through a restoring integer square-root recurrence, and rounds the
53-bit result to the ABI-fixed nearest-ties-even policy without floating
arithmetic. It preserves signed zero, passes positive infinity, rejects negative
nonzero values as canonical NaN, and canonicalizes every NaN input.

A separate 532-pattern differential derives expected `sqrt` bits with Python
arbitrary-precision `isqrt`, including subnormal and exponent-boundary cases.
Cross-ABI object inspection proves the implementation adds no callable host or
compiler helper beyond the same target float/stack markers already allowed for
ordinary guest math.

The internal transcendental front end resolves only cases whose rounded result
is proved without a numerical kernel. The `sin` interval is
`|x| <= 23 * 2^-30`; the stricter `cos` interval is
`|x| <= 181 * 2^-34`.

The Taylor bounds `|x - sin(x)| < |x|^3 / 6` and
`0 <= 1 - cos(x) <= |x|^2 / 2` fit strictly inside the relevant binary64
nearest-even midpoints, including the subnormal spacing case. At the new
boundaries those error-to-midpoint ratios are exactly `12167/12288` for `sin`
and `32761/32768` for `cos`. The front end therefore returns the input bits for
`sin` and binary64 one for `cos` in those proved intervals. It also owns the
complete
`atan2` zero/infinity matrix using reviewed nearest-even binary64 constants for
`pi/4`, `pi/2`, `3*pi/4`, and `pi`, with sign taken from `y` and canonical NaN
publication.

Finite nonzero pairs with equal magnitudes also resolve directly to `pi/4` or
`3*pi/4` by quadrant, independent of their exponent. In the right half-plane,
a second conservative identity handles small ratios.
The admitted limit is `r = |y/x| <= 7 * 2^-29`, which is 1.75 times the
earlier `2^-27` boundary. The alternating-series bound
`0 <= r - atan(r) < r^3 / 3` remains below one-half ulp for exact binary64
ratios throughout that interval.

For non-dyadic normal ratios in the restricted top binade, the maximum error is
`343/768 ulp`. A quotient below the midpoint is always safe; an upper-rounded
quotient is admitted only when its exact fractional remainder is at least
`727/768 ulp`.

Lower normal binades use the tighter exponent-scaled cubic bound. For normalized
exponent `e <= -28`, the maximum error is strictly below `2^(2e+55)/3` ulp, so
the required distance above a midpoint shrinks by a factor of four per binade.
The rule uses only the 53-bit denominator and exact remainder, never the rounded
ratio as an accuracy oracle.

Subnormal ratios are fully decidable under the same bound. Their worst-case
`atan` error is below `2^-1993` subnormal ulp, while a non-midpoint rational
with
a 53-bit denominator is separated from the nearest midpoint by more than
`2^-54` ulp. Exact midpoint ratios are directional: because `atan(r) < r`, the
lower binary64 neighbor is selected even when rounding the ratio itself would
choose the even upper neighbor.

The narrow ambiguous normal-remainder interval, `r > 2^-27`, swapped
magnitudes, and negative `x` remain unresolved. This keeps failure closed while
range-reduction and numerical-kernel evidence is absent.

Every ordinary finite case outside those proofs still reports
`kernel-required`. For finite nonzero `atan2(y, x)` inputs, a second exact stage
orders the magnitudes and normalizes both operands to 53-bit integer
significands. It emits the exact ratio
`numerator / denominator * 2^exponent_delta` in `[0, 1]`, a swap bit recording
whether `|y| > |x|`, and both original signs. The full binary64 exponent span is
representable (`exponent_delta` reaches `-2097` for minimum-subnormal versus
maximum-finite input), and rejected special inputs do not mutate caller output.

No floating division occurs in this stage. A bit-at-a-time integer long-division
step can additionally round that exact ratio to binary64 nearest-ties-even,
including zero, subnormal, minimum-normal carry, and ordinary normal results.
Its remainder never exceeds 54 bits, so the implementation needs neither
`__int128` nor integer division/remainder operators.

A separate reconstruction stage maps the exact ratio geometry to one symbolic
base (`0`, `pi/2`, or `pi`), one add/subtract operation for `atan(r)`, and the
final result sign. The base remains symbolic so rounded binary64 pi constants do
not become range-reduction authority. A deterministic 519-pair differential
locks all four quadrant formulas, while fixed C vectors prove special-input
rejection leaves caller-owned reconstruction state untouched.

The ordinary `atan(r)` kernel input now has one additional exact rational
reduction. Ratios below `169/408` remain unchanged; ratios at or above that cut
use `atan(r) = pi/4 - atan((1-r)/(1+r))`. The cut is the last simple Pell
convergent that keeps the required 53-bit cross-products inside `uint64_t`.
At the cut the transformed residual is `239/577`, and
`239 * 408 = 97512 < 97513 = 169 * 577`, so both branches leave a residual
strictly below `169/408` without floating arithmetic or rounded pi constants.

The 519-pair exact-rational differential checks the emitted numerator,
denominator, exponent, symbolic base, and add/subtract operation against Python
`Fraction`. Native `-O0` object inspection continues to show no callable helper
symbols, while strict Windows i686/x64/ARM64 and wasm32 compilation lock the
freestanding geometry.

The `atan2` kernel handoff now composes quadrant reconstruction with that atan
reduction. Every finite nonzero pair becomes one symbolic expression
`k*pi/4 +/- atan(residual)`, where `k` is an integer from zero through four, the
residual is exact and below `169/408`, and the final sign is explicit. For
`r=1/2`, the four quadrant representatives reduce respectively to
`pi/4-atan(1/3)`, `pi/4+atan(1/3)`, `3*pi/4+atan(1/3)`, and
`3*pi/4-atan(1/3)` before sign application.

The same deterministic 519-pair differential independently composes the
quarter-pi coefficient and residual operation. Fixed C vectors lock all four
quadrants, the direct `r=1/4` branch, and complete output nonmutation for
rejected special inputs. Clang path analysis is clean after the alignment shift
is expressed only as the literal-safe cases zero, one, or two.

For a prospective alternating-series kernel on the bounded residual, exact
rational analysis now fixes one useful truncation budget. With 60 included
terms, the first omitted term has power 121 and bounds truncation strictly below
`2^-160` over the full `169/408` envelope; 59 terms do not meet that uniform
bound. This is only a truncation result: arithmetic-evaluation error, symbolic
pi reconstruction error, and hard-to-round detection still require independent
interval evidence before any public result can be admitted.

A separate Q32.192 interval now gives the symbolic pi reconstruction numerical
authority without treating a binary64 constant as exact. The Machin identity
`pi/4 = 4*atan(1/5) - atan(1/239)` is bounded with exact rational alternating
series: 42 terms for `atan(1/5)` and 12 for `atan(1/239)` leave a combined
interval narrower than `2^-200`. That proof places `pi/4 * 2^192` strictly
between the adjacent integers ending in hexadecimal `...8a67cc74` and
`...8a67cc75`.

The C boundary publishes those adjacent endpoints and forms `k*pi/4`, for
`k=0..4`, by fixed-width 32-bit limb addition only. The result is an enclosing
Q32.192 interval whose width is exactly `k` fixed-point units; invalid base IDs
and null outputs reject without mutation. No host floating arithmetic, libm, or
rounded pi value participates in the proof.

The exact residual is now projected into the same Q32.192 domain by streaming
binary long division. Residuals representable at that scale produce identical
lower and upper endpoints; every other nonzero residual produces adjacent floor
and ceiling endpoints. Ratios smaller than one fixed-point unit become
`[0, 2^-192]`, preserving enclosure without inventing a rounded input value.

The converter accepts only the two geometries emitted by the exact reduction:
normalized 53-bit significands with a negative power-of-two exponent, or the
bounded exponent-zero transformed fraction. A 519-pair `Fraction` differential
checks exact floor/ceiling integers for the full atan2 kernel-plan corpus.
Invalid geometry and null outputs reject without publication.

The first numerical atan kernel now evaluates 60 alternating-series terms in
that Q32.192 domain with directed interval arithmetic. Fixed-point products use
7-by-7 32-bit limbs and floor the discarded 192 fractional bits; upper products
round upward when any discarded bit is nonzero. Division by the odd
coefficients `3..95` is bit-at-a-time and similarly floors the lower endpoint
and ceilings the upper endpoint. Interval addition and subtraction preserve the
usual monotone bounds.

The series accepts only residual intervals no larger than the Q32.192 ceiling
of `169/408`. Exact rational evidence proves the first omitted term at even that
slightly larger fixed-point endpoint is below `2^-160`. After 60 terms the
evaluator now advances the same directed recurrence once more and adds only the
upper endpoint of `x^121/121`, so smaller residuals no longer inherit the
uniform worst-case widening.

A 64-pair stratified `Fraction` corpus checks the C lower endpoint is below the
exact rational partial and the upper endpoint is above the partial plus its next
term. The earlier 519-pair differential continues to cover exact residual
projection itself.

Very small inputs use a separate monotone enclosure instead of repeatedly
rounding terms smaller than one fixed-point unit. When the Q32.192 upper input
is below `2^-64`, `x^3/3 < 2^-192`, so `atan(x)` is enclosed by one unit below
the input lower endpoint and the input upper endpoint. If the lower endpoint is
zero, positivity gives the tighter direct enclosure `[0, upper]`. This avoids
artificial interval dependency without relaxing the proof.

The raw-bit small-ratio preclassifier also scales its normal-binade rounding
margin with the same cubic bound. For normalized exponent `e <= -28`, the
maximum error is `2^(2e+55)/3` ulp. If the exact quotient lies above a midpoint,
writing `gap = 2*remainder-denominator` turns the safety test into
`3*gap >= ceil(2*denominator / 2^(-(2e+55)))`.

All products stay within 64 bits; large right shifts collapse the threshold to
one. Two fixed top-binade vectors straddle the `727/768` gate within `10^-5`
ulp: the lower vector stays fail closed in the preclassifier and the upper
vector resolves there, while the independent Q1152 oracle proves the final
binary64 result for both.

Exact normal midpoint ratios are now proved unreachable for valid binary64
input geometry. If the normalized denominator has `t` trailing zero bits, then
`t <= 52`; after 52 quotient bits the remainder is divisible by `2^t`, whereas
an exact midpoint remainder `D/2` has only `t-1` trailing zero bits. Odd
denominators cannot have an integer `D/2` at all.

The C midpoint branch remains fail closed as a defensive invariant check rather
than an admitted runtime case. This closes the normal exact-midpoint obligation
without choosing a neighbor for malformed geometry.

That exclusion also closes the lower normal binades without quotient-margin
work. At normalized exponent `e=-54`, the cubic atan error is less than
`1/(3*2^53)` ulp, while any non-midpoint ratio is separated from a midpoint by
more than `2^-54` ulp; lower binades reduce the error by another factor of four
per exponent. The runtime therefore admits `e<=-54` immediately instead of
executing 52 fractional long-division steps.

For `-53<=e<=-28`, denominator divisibility can prove the same result early.
At `e=-28`, the scaled remainder rule has exact threshold `2/3` of the rounding
cell. Two fixed non-dyadic vectors straddle that boundary within `1/40000` ulp.

At `e=-29`, the next scaled threshold is `13/24`; a second pair straddles it
within `1/30000` ulp. Q1152 confirms all four final result bits while each lower
vector remains fail closed and each upper vector resolves early.

A tighter denominator-spacing proof now uses the actual normalized
denominator.
Write `D=2^t*d` with odd `d`. The post-52-bit remainder is divisible by `2^t`,
so every non-midpoint is separated by at least `1/(2d)` ulp.

For `m=-(2e+55)`, the cubic error is strictly below `2^-m/3` ulp, so the
quotient loop is unnecessary whenever `d <= 3*2^(m-1)`.
Equality is safe because the cubic error bound is strict.

The runtime strips powers of two with shifts and compares the remaining odd
factor directly; it still uses no `/`, `%`, floating arithmetic, or `__int128`.
This exact-denominator criterion contains every case admitted by the older
`D<2^53` trailing-zero bound and admits additional valid geometries. A
fixed-seed 4,320-pair differential spans all 27 normal margin binades from
`e=-27` through `e=-53`, with 160 independent 53-bit numerator/denominator
geometries per binade. Exact `Fraction` expectations match the C preclassifier
across both early-resolved and kernel-required cases.

A fixed-seed million-pair stress run sampled 999,006 finite raw-word pairs after
this change and the combined exact-plus-Q32.192 handoff resolved every one. The
same generator and finite count are now retained as a compiled C regression,
while an independent Python counter reproduces the finite population. The
measurement is diagnostic coverage, not exhaustive correct-rounding authority.

The finite-nonzero atan2 handoff now composes the certified base and residual
intervals directly. Add branches use endpoint-wise addition; subtract branches
use `[base.lower-residual.upper, base.upper-residual.lower]`. The result remains
an unsigned principal-angle magnitude plus the already-derived sign, so no
signed fixed-point overflow is introduced. Publication is atomic on invalid or
special inputs.

A second 64-pair stratified oracle constructs the expected principal-angle
interval from the exact Machin bounds and the exact 60-term atan rational
bounds. The composed C magnitude encloses that authority for all sampled
quadrants and exponent geometries, while fixed C vectors pin all four equal-
magnitude quadrants and rejected-input nonmutation.

A nearest-even binary64 gate now rounds the two Q32.192 endpoints independently
and publishes only when both land on the same bit pattern. Endpoint rounding is
integer-only: it finds the leading fixed-point bit, extracts 53 significand
bits,
and applies guard/sticky ties-to-even. Tracked C conformance pins both even- and
odd-lower midpoint ties plus the significand carry that rounds a midpoint to the
next power of two. Because every nonzero Q32.192 value is at least `2^-192`,
this path needs only normal binary64 encoding; intervals that include zero and
one fixed-point unit naturally disagree and stay unresolved.

Against the same exact 64-pair Machin-plus-Fraction authority, all 64 true
principal-angle intervals round uniquely. The Q32.192 enclosure by itself
certifies 48; the other 16 are tiny right-half-plane ratios already resolved by
the exact/small-ratio preclassifier. The combined internal handoff now checks
that authority first and certifies all 64 bit-for-bit.

A second Q1152 oracle avoids repeated `Fraction` summation by dividing every
alternating-series term directly with arbitrary-size integers and directed
floor/ceiling rounding. It certifies unique expected binary64 bits for all 519
deterministic kernel pairs in about two seconds, and its 64 shared intervals
enclose the exact Machin-plus-Fraction authority.

An eight-vector non-small kernel neighborhood found by deterministic local
refinement exercises both sides of binary64 midpoints. Every vector is within
`1/5000` ulp of its nearest midpoint, and the closest remains within `1/60000`
ulp. Q1152 certifies every result and the Q32.192 handoff publishes those same
bits. This remains bounded corpus evidence rather than an exhaustive full-domain
proof.

A separate deterministic continued-fraction proposal search targets binary64
angle midpoints directly. One retained eight-vector set exercises the
`pi/4-atan(residual)` branch and another exercises direct `atan(r)`. The
proposal arithmetic is not an oracle: Q1152 independently certifies both
midpoint sides, places the transformed set within `4e-20` ulp and the direct set
within `2e-20` ulp, and places each closest case below `2e-21` ulp. Q32.192
still publishes the same certified bits for all sixteen.

The fixed-point limb primitives are width-parametric through nine limbs. The
combined handoff first retries Q32.192 ambiguity at Q32.224, using 85 atan terms
and a Machin 49/14 quarter-pi enclosure whose exact rational width is below
`2^-232` and whose encoded bounds occupy one Q32.224 cell. Its truncation proof
is evaluated at the directed Q32.224 ceiling of `169/408`.

A third Q32.256 stage now follows Q32.224 ambiguity. It uses 98 atan terms and a
Machin 56/16 quarter-pi enclosure whose exact width is below `2^-264` and whose
encoded bounds again occupy one fixed-point cell. At `ceil-Q256(169/408)`, 97
terms fail the one-cell truncation target while 98 terms satisfy it.

Independent evidence files keep both wider stages separate from prior-precision
oracles. Q32.256 encloses and rounds the 16 retained positive hard pairs and is
a subinterval of Q32.224 over 512 deterministic finite pairs. Q32.256 still
fails closed on disagreement, so a quantitative termination proof or further
adaptive precision remains required for the full domain.

A second final-rounding authority now works from candidate binary64 cells rather
than atan intervals. It constructs both neighboring dyadic midpoints exactly,
bounds their sine and cosine with 40 rational Taylor terms, proves the tangent
branch from directed signs, and compares exact `y/x` only when the branch
matches. Quadrant order handles boundaries that cross zero or a tangent pole.

That midpoint certificate now accepts 4,164 finite pairs: all 64 signed quadrant
variants of the 16 retained hard ratios, four near-zero/near-`pi/2` edges, and
4,096 fixed-seed finite nonzero pairs. It uses neither a pi constant nor any
Q32.192/Q32.224/Q32.256/Q1152 rounding oracle.

The reference refines fail-closed through 4, 8, 12, 16, 24, 32, and 40 Taylor
terms. Exactly 1018/13/2080/1053 cases certify first at 4/8/12/16 terms; none
of the retained corpus needs a later step. This explicitly exercises precision
growth
instead of validating only one preselected Taylor width.


Candidate-cell construction is now guest-C-owned rather than test-only.
`malbolge_guest_math_atan2_cell_midpoints` decodes each adjacent binary64 pair
into exact signed dyadics with a 64-bit numerator and explicit denominator
shift. Both signed zeros map to `[-2^-1075,+2^-1075]`; candidate magnitudes at
four or above reject without mutating caller output. The 4,164-candidate test
compares both C boundaries exactly against independent `Fraction` midpoints.

For the actual fallback path, midpoint denominator shift is globally at most
107: `e<=-54` right-half-plane ratios resolve before the kernel, while at
`e=-53` a non-dyadic ratio exceeds `2^-53` by at least `2^-106`; its cubic atan
error is below `2^-156/3`, so the exact angle remains above `2^-53`. The lower
rounding boundary there is the finest possible one, at denominator `2^107`.

Variable-precision input materialization now has a caller-owned contract rather
than an allocator dependency. `malbolge_guest_math_dyadic_fixed_limb_count`
plans the exact number of little-endian 32-bit limbs for a requested fractional
precision, and `malbolge_guest_math_dyadic_write_fixed` writes only after the
caller supplies that capacity. Short buffers reject before mutation; sign stays
in the source dyadic and the written limbs are its exact magnitude.

Tests cover 107, 128, 256, and 4,096 fractional bits and plan a `UINT32_MAX`-bit
request without allocating it. Neither function observes guest heap/startup
state.

The same caller-owned binary core now provides variable-width floor product and
small division. A product requires exactly `2*N` scratch limbs for `N` input
limbs, reports whether discarded fractional limbs were nonzero, and rejects any
high overflow before result/discarded publication. Division uses bitwise
long-division with a 64-bit remainder, accepts every nonzero `u32` divisor, and
supports `input == output`. Independent integer fixtures cover 4/8/16/128 limbs
and `UINT32_MAX`; insufficient product scratch and divisor zero are nonmutating.

Directed rounding no longer depends on the fixed Q192/Q224/Q256 structs.
Checked variable-width add/subtract preflight carry/underflow before
publication.
Product floor/ceil share caller-owned `2*N` scratch; ceil adds one unit only
when
discarded low limbs are nonzero and rejects if that increment would overflow.
Small division similarly exposes floor/ceil, with ceil selected by its exact
remainder.

Integer authority exercises 4/8/16/128 limbs and pins a product whose floor is
the all-ones maximum but whose nonzero remainder makes ceil unrepresentable,
requiring a nonmutating rejection.

A composed interval layer now makes publication atomic across both endpoints.
For nonnegative intervals, add/subtract preflight both endpoint operations.
Multiplication stages directed lower/upper results in caller-owned `4*N`
scratch,
while small division needs `2*N`; outputs are copied only after both bounds
succeed. Malformed intervals are rejected before arithmetic.

Independent integer evidence covers 4/8/16/128 limbs and pins upper-bound
overflow after a valid lower product as a nonpublishing failure.

The repeated Taylor-term recurrence now composes the interval core directly.
For a nonnegative term and `x^2` interval it evaluates directed
`term*x^2/divisor` with the existing `4*N` workspace, then publishes only after
both product and division bounds succeed. Fixtures at 4/8/16/128 limbs use
recurrence divisors 6/20/42/72 and match exact integer composition.

This closes variable-width term generation but not full sine/cosine summation:
partial alternating sums for `|midpoint|<4` can cross zero, so the next runtime
primitive must carry signed endpoints rather than forcing unsigned underflow.

Signed accumulation now removes the scalar sign-crossing blocker.
`malbolge_guest_math_fixed_signed_add` keeps a one-bit sign separate from the
variable-width magnitude. Equal signs use checked addition; opposite signs use
magnitude comparison plus subtraction, and exact cancellation canonicalizes to
positive zero. Overflow or invalid sign selectors reject before publishing
magnitude or sign.

Independent fixtures cover 4/8/16/128 limbs and both sign orders without
introducing two's-complement width policy.

Signed interval accumulation now closes the alternating-sum representation
boundary. Endpoints are ordered with sign-aware magnitude comparison, then the
monotone lower/lower and upper/upper sums stage in caller-owned `2*N` scratch.
Both staged endpoints and their signs are published only after the complete
operation succeeds. Cross-zero fixtures cover 4/8/16/128 limbs and pin malformed
ordering, short scratch, invalid signs, and an upper-only carry overflow as
atomic rejection.

Full directed sine/cosine Taylor summation now executes over the variable-width
core. On nonnegative `x<4`, each recurrence term is accumulated as a signed
interval; one extra term becomes `[0,+t]` or `[-t,0]` according to parity and
therefore encloses the alternating tail. At least two retained terms are
required, after which the omitted-tail magnitudes decrease for both series on
this domain. One caller-owned `10*N` workspace holds square, term, sum, and the
reused operation scratch.

Exact `Fraction` authority checks 4/8/12/16 terms at four dyadics through
`4-2^-224`, with no host sin/cos or pi authority.

The same-branch positive tangent comparison now uses exact cross products rather
than a fixed/fixed division surface. Kernel normalization is inverted when
`swapped` so the comparator sees `|y/x|`; its 53-bit numerator and denominator
multiply directed sin/cos endpoint integers exactly. `exponent_delta` becomes a
left shift on the corresponding side, bounded to plus/minus 53 for the fallback
path. `2*(N+2)` caller-owned limbs hold the two products.

Synthetic algebraic evidence covers `2^-53`, `1/4`, `1/2`, `1`, `2`, and
`2^53`, including the unresolved overlap/equality result.

The positive same-branch midpoint path is now orchestrated in guest C.
An exact positive dyadic boundary is materialized only when the caller-selected
fractional limb count can represent its denominator. Sine/cosine Taylor
intervals then feed the exact cross-product comparator; negative or zero-lower
branch evidence stays unresolved rather than being coerced into a tangent
ordering. A single `15*N` caller-owned workspace holds the input, four trig
bounds, and reusable operation scratch.

With eight fractional limbs and 16 terms, this route proves strict lower/upper
midpoint ordering for all sixteen retained positive hard cells. A deliberately
coarse one-limb invocation remains unresolved, pinning refinement rather than
implicit rounding as the precision policy.

Signed branch/pole classification now covers the full principal atan2 range.
Directed sine/cosine signs assign each midpoint a quadrant rank. The two
principal-range wrap cases extend that rank to `4` for positive boundaries past
pi and `-1` for negative boundaries below negative pi, so different ranks are
ordered without a tangent comparison. Same-rank cases compare absolute
sine/cosine products and reverse the magnitude comparison when tangent is
negative.

The 16 retained hard ratios now pass through all four input sign combinations,
for 64 signed cells whose lower and upper boundaries are both certified. Exact
synthetic dyadics at `±1` and `±3.5` separately pin ordinary rank ordering
and the
principal wrap adjustments without importing pi as authority.

Cell certification now has an atomic retry surface.
`malbolge_guest_math_atan2_refinement_attempt` owns candidate-cell construction
and both signed midpoint comparisons. It distinguishes mathematical overlap from
operational failure: unresolved directed bounds publish `certified=0`, whereas
invalid scratch, special inputs, or malformed candidates return failure without
mutating the caller's status. Only strict lower-positive plus upper-negative
ordering publishes certification.

The 64 signed hard cells certify at eight fractional limbs and 16 terms. Coarse
one-limb precision and an adjacent wrong candidate are explicitly uncertified,
which pins retry semantics independently from the current fixed-Q handoff.

Bounded scheduler evidence now runs the atomic refinement attempt over 4,164
pairs: signed hard cells, four edges, and 4,096 finite-nonzero LCG pairs. The
population splits into 997 pre-kernel resolutions and 3,167 kernel-required
cases. With 16 terms, Q64/Q96/Q128 certify 3,112/3,135/3,167 kernel cells. At
Q128, 4/8/12/16 terms certify 21/26/2,107/3,167 cells.

The distribution is intentionally coverage-only. It demonstrates independent
precision and truncation retries but does not turn Q128/16 into a full-domain
bound or discharge the unbounded refinement/termination obligation.

A stateless caller-owned scheduler now composes the atomic refinement attempt.
Stage `s` uses `s+2` fractional limbs, `4s+8` Taylor terms, and
`15*(s+3)` scratch limbs. Input/candidate validation precedes capacity
checks, so
special or malformed work remains a hard nonpublishing failure even when scratch
is too small. The driver executes all stages that fit and, on capacity
exhaustion,
publishes the first unattempted plan and its exact requirement rather than
conflating memory with numerical failure.

A hard retained seed pins the sequence Q64/8 -> Q96/12 -> Q128/16 and certifies
only at the third stage with 75 limbs. A neighboring wrong candidate requests
the
next stage instead of certifying.

Taylor recurrence division is now factorized. Rather than store
`(2n)(2n±1)` in one `u32`, each directed term divides successively by the two
positive factors. Successive lower floors and upper ceils remain valid directed
bounds, and the existing `4*N` recurrence scratch is unchanged. The old stage
8190 divisor-product ceiling therefore disappears.

The first planner ceiling is now the `u32` scratch-capacity ABI itself. Stage
286331150 requests 286331152 fractional limbs, 1145324608 terms, and exactly
`UINT32_MAX` scratch limbs; stage 286331151 is rejected before publication. This
removes a policy-sized numerical ceiling but remains a finite machine-capacity
limit, not a proof that every binary64 input certifies before it.

Candidate production no longer requires fixed-Q uniqueness. A conservative Q256
extractor rounds the directed lower and upper endpoints independently with the
integer nearest-even endpoint helper. Equal endpoint roundings produce one
candidate; adjacent roundings produce two ordered candidates; wider spans fail
closed rather than omitting possible cells. An exact synthetic midpoint straddle
at `1 + 2^-53` pins the two-cell path, while all 4,164 retained atan2 pairs
remain
on the one-cell path matching the current handoff.

A multi-candidate scheduler now attempts every proposed cell at each refinement
stage. Exactly one certified cell publishes; zero certified cells advance to the
next plan; multiple certified cells are an invariant failure. Positive and
negative hard seeds independently pin adjacent ordering and show that Q128/16
selects the correct cell while rejecting its neighbor. The combined
`malbolge_guest_math_atan2_q256_refine_available` path therefore supplies a
caller-owned proposal-plus-certification surface even when Q256 uniqueness would
fail, subject to the conservative two-cell span check.

No natural retained atan2 input currently exercises a two-cell Q256 interval, so
that branch is not presented as observed-domain closure. Candidate extraction
and two-cell certification are separately exact, while full-domain evidence must
still show either that Q256 cannot span more than two cells for kernel work or
provide a broader proposal mechanism.

Candidate proposal is no longer bounded to one or two cells. Q256 endpoint
roundings also define an ordered binary64 range; negative intervals reverse
their
magnitude endpoints into angular order. A monotone integer key (`bits` for
positive cells, complemented bits for negative cells) supports one binary-search
implementation for both signs.

At each probed cell, directed comparisons against its two dyadic midpoints yield
four outcomes: below, certified interior, above, or inconclusive. Below/above
strictly shrink the candidate range at the current stage. Inconclusive bounds
preserve the narrowed range and advance the precision/depth plan. Certification
publishes only the single cell whose lower midpoint is strictly below the angle
and whose upper midpoint is strictly above it.

Synthetic evidence uses a Q256 interval whose endpoint roundings differ by two,
so the one/two-cell extractor rejects it while range extraction retains all
three
possible cells. A skewed 12,289-cell range around a hard input is reduced to at
most five cells by Q64/8 and reaches the exact result at Q128/16 in both angle
signs. The Q256 range wrapper then composes endpoint extraction and adaptive
binary search directly.

Candidate-count closure is therefore no longer required. The remaining global
obligation is to connect this caller-owned range search to the eventual product
handoff and justify that increasing directed precision reaches certification
before the finite workspace-capacity representation is exhausted.

The qualitative termination fact for an adaptive version now has durable
external provenance in
`docs/bibliography/publications/lambert-tangent-irrationality.md`.
Every nonzero binary64 rounding midpoint is rational, while Lambert's theorem
excludes rational `tan(midpoint)`. Since every finite nonzero binary64 input
ratio is rational, exact equality at a same-branch midpoint is impossible.
This proves eventual separation for a correctly directed refinement sequence;
it does not supply the unbounded guest-C storage policy needed to implement
that sequence.

`sin`, `cos`, and `atan2` remain source-unavailable until range reduction,
numerical approximation, and final correct-rounding evidence close the full
binary64 domain.

Version one needs no separate guest scheduler or ordinary-integer-helper API:
integer operations are explicit typed-IR semantics for lane-9 lowering, and the
selected target profile is sequential with no guest thread surface. Allocation
startup binding and byte-I/O intrinsic realization are likewise lane-9 target
work over the stable identities defined here. The canonical promoted-block
varargs cursor is now implemented; source `va_list` bridging remains lane-9
compiler-lowering work. Remaining lane-8 algorithm work is correctly-rounded
`sin`, `cos`, and `atan2`.

## Invariants

- Allocation, streams, arithmetic/math helpers, calling-convention support,
  and other runtime facilities have deterministic guest-owned semantics and
  freestanding implementations. Hidden host callbacks cannot define guest
  computation.
- Fundamental compiler intrinsics have explicit versioned guest-runtime
  contracts. Native debug adapters may mirror them but cannot define them.
- Executable ternary/Malbolge realization is owned by the downstream
  `ternary-machine-lowering` stage, which consumes these runtime identities
  unchanged. This separation preserves the eventual Malbolge-semantics invariant
  without making lane 8 depend on lane 9.
- Accepted and rejected C fixtures exercise the boundary, and diagnostics
  identify the unsupported construct/profile requirement at source level.

## Failure Behavior

Unsupported or nondeterministic C is rejected at source locations rather than
lowered through host-dependent behavior.

## Verification

- Expected durable artifact surface: `tools/tidy/`, `src/runtime/`,
  `docs/technical/specification/`, `tests/tidy/`, `tests/runtime/`, and
  `tests/test_guest_runtime_c.py`.
- Required evidence: accepted/rejected source fixtures, source-located
  diagnostics, runtime semantic/conformance fixtures, and compiler/runtime
  regression tests that prove guest computation has no host-defined fallback.
- Current executable evidence: `tests/test_guest_runtime_c.py` compiles strict
  C23 conformance vectors for i686, x86-64, and AArch64 Windows ABIs and
  executes
  them natively. It locks frame wire bytes, heap metadata bytes/alignment,
  allocation lifecycle, zeroing/overflow, resize/tail-growth preservation,
  corruption rejection including late-corruption nonmutation, and byte
  mapping. A deterministic 4,000-operation
  allocator stress sequence independently parses the raw heap chain after every
  operation. The same vectors pass pinned ASan/UBSan and Clang static analysis.
  Freestanding runtime objects are checked under all three reviewed Windows ABIs

  so compiler-injected library helpers cannot silently enter the runtime core.
- Dependency boundary: executable ternary/Malbolge lowering is intentionally
  downstream under `ternary-machine-lowering`; this contract supplies its stable
  runtime semantic identities and implementation inputs.
- Prerequisite completion evidence: `supported-libc-contract`,
  `safe-rust-malbolge-vm`.

## References

- [Deterministic C Surface And Clang
  Tooling](../../adr/deterministic-c-surface-and-clang-tooling.md)
- [Compiler Pipeline And Guest
  Runtime](../../adr/compiler-pipeline-and-guest-runtime.md)

### Governing ADR Paths

- `docs/technical/adr/deterministic-c-surface-and-clang-tooling.md`
- `docs/technical/adr/compiler-pipeline-and-guest-runtime.md`
