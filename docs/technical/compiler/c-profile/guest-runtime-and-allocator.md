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
to C `int` values, EOF word `14,348,906` maps to `-1`, impossible intermediate
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
population now splits into 3,921 pre-kernel resolutions and 243
kernel-required cases. With 16 terms, Q64/Q96/Q128 certify 188/211/243 kernel
cells. At Q128, 4/8/12/16 terms certify 21/26/139/243 cells.

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

The fixed-Q and adaptive paths now meet at a caller-owned internal handoff.
Special results and Q192/Q224/Q256 uniqueness are reported as `FAST_RESOLVED`
and do not require a scratch pointer. When Q256 is calculable but non-unique,
its endpoint range feeds adaptive search; insufficient capacity reports `RETRY`
with the exact next plan, while a unique midpoint-cell certificate reports
`REFINED_RESOLVED`.

An injectable Q256-interval entry point provides independent evidence for this
otherwise-unobserved branch. A synthetic wide interval enclosing a retained hard
seed reports stage 0/45 limbs with no scratch, narrows and requests stage 2/75
with 60 limbs, and certifies the retained result with 75 limbs. The real handoff
resolves a deterministic 512-pair corpus through its fixed fast path with
`scratch == NULL`, matching the current unique result exactly.

This closes the internal control-flow gap between fixed-Q ambiguity and adaptive
range certification without changing public libc availability. The synthetic
ambiguous interval is deliberately not presented as a naturally observed atan2
input; public exposure still depends on full-domain termination/resource
closure.

Caller-owned retry progress is now resumable without replaying the fixed ladder.
The handoff state includes raw input identity, the narrowed binary64 candidate
range, and the first unattempted plan. Resume validates `(y_bits,x_bits)` and
recomputes the exact stage tuple before invoking range refinement on the saved
range. Capacity that is still too small simply republishes the same retry state.

Synthetic ambiguous evidence runs the ownership chain across three capacities:
no scratch returns stage 0, 60 limbs advances to a narrowed stage-2 retry, and
75
limbs certify the retained hard cell from that saved state. Mutating the stored
input identity or planner terms produces a nonpublishing hard failure. The range
payload is trusted caller-owned runtime state, not an authenticated object.

This completes the internal no-allocator control flow from fixed-Q evaluation to
capacity query, narrowed retry, and resumed certification. Public integration
still needs a policy for who supplies/grows that scratch and, independently, the
full-domain resource/termination proof.

The caller-owned scratch plan now has a byte/alignment projection compatible
with the guest allocator without depending on it. A validated refinement plan
maps to exact `u32` limb and byte counts plus 4-byte alignment; multiplication
by
four is checked before output publication. The guest heap's 16-byte payload
alignment strictly satisfies that requirement.

Stages 0/1/2 project to 180/240/300 bytes. Stage 71,582,785 is the largest
current
plan whose limb workspace also fits the guest allocator's `u32` extent: it needs
1,073,741,820 limbs or `0xfffffff0` bytes. Stage 71,582,786 still plans in limbs
but byte projection rejects because the allocation extent would exceed
`UINT32_MAX`.

This projection does not make math allocator-owned. Allocation wrappers remain
unavailable in canonical libc until lane-9 startup proves heap binding before
user code, so the production math path still consumes caller-supplied storage.
The byte query exists so that later startup/allocator integration can request
the
same proven workspace geometry without duplicating arithmetic.

A test-only cross-domain integration now exercises the projected scratch against
the actual startup-bound guest heap. Allocation before an explicit bind returns
`NOT_INITIALIZED`. After binding a 1,024-byte aligned arena, the synthetic hard
handoff allocates its 180-byte stage-0 buffer, resizes it to 240 and 300 bytes
for
later retries, reaches `REFINED_RESOLVED`, releases the allocation, and confirms
that a fresh allocation succeeds afterward.

The same explicitly bound heap also drives the normalized fallback without any
production allocator dependency. The retained hard seed allocates 288 bytes,
resizes through 384, 480, 576, and 672 bytes, certifies at normalized stage 4,
then releases and reuses the allocation. Pre-bind allocation remains
`NOT_INITIALIZED`.

The harness calls `malbolge_guest_runtime_bind_heap`, allocation, resize, and
release directly; the math implementation remains allocator-free. This evidence
therefore proves compatibility with the existing guest heap once binding exists,
but it does not satisfy the separate lane-9 obligation to emit/prove that bind
before user code or make canonical `malloc` available.

The rational height of every finite input ratio is now bounded exactly rather
than by normalized-significand heuristics. A finite binary64 value is
`M * 2^-1074` for an integer `M` in `[1, 2^2098)`, so after reducing `|y/x|`
both numerator and denominator have at most 2,098 bits. The two extreme
min-subnormal/max-finite orientations attain that ceiling respectively in the
denominator and numerator. They are general input-geometry witnesses; the new
axis preproof resolves them before adaptive refinement.

`malbolge_guest_math_atan2_ratio_reduced_height` computes the exact reduced bit
lengths from kernel geometry without constructing the potentially 2,098-bit
integers. It uses Stein binary GCD plus exact shift/subtract division so the new
path does not introduce an i686 64-bit division helper. Python `Fraction`
independently matches all 243 kernel-required retained cases; their sampled
maxima are 103 denominator bits and 102 numerator bits.

Directed Q256 pi/4 bounds and `0 < atan(r) < r` now resolve tiny-ratio cells
around pi and both sides of pi/2 before the kernel. Together with the existing
zero-axis proof this gives a tight post-special height ceiling of 108 bits; the
cell immediately above the `2^-55` adding-side cutoff attains it. The reduced
rational denominator has a separate tight ceiling of 106 bits. The congruence
witness `y=0x3ca8000000000001, x=0x3ff0000000000001` remains kernel-required
with a 53-bit numerator and 106-bit denominator.

Separation-parameter publication fails closed above either ceiling. These
smaller bounds, rather than 2,098, are the relevant rational parameters
for any adaptive separation theorem.


Lambert-specific argument geometry is now executable too. For a reduced dyadic
candidate midpoint `m=u/v`, the runtime publishes a strict power-of-two ceiling
for `u^2/v`. Candidate-cell numerators fit in 54 bits, and the exact dyadic
shifts imply `u^2/v < 2^56` throughout `|m|<4`; ceiling 56 is attained near the
upper angle binades. Deep 107-bit midpoint denominators have a much smaller
scale.

This is the exponential factor in the Lambert-GCF recurrence and is kept
separate from the input rational denominator bound `q<2^106`. The query also
publishes the canonical halving count `max(E,0)`: no candidate boundary needs
more than 56 halvings, the normalized dyadic shift stays at most 108, and the
normalized `u^2/v` scale ceiling is at most one (`E<=0`). Transporting a future
normalized proof back through those angle doublings remains a separate
obligation.


The first transport step is executable. A caller-owned signed sin/cos interval
can be doubled atomically with the algebraic double-angle identities. The
primitive requires `12*N` scratch, stages sine product and both squares before
publication, and returns `proven=0` when either input interval still crosses
zero.

Exact dyadic evidence covers 4/8/16/128 limbs, positive and negative quadrants,
a zero-touching cosine output, and non-mutating unresolved/error paths.
The transport scheduler now iterates that step across the complete structural
ceiling. It stores four current endpoints plus the reusable `12*N` one-step
workspace, so total caller-owned scratch is `16*N`. Counts 0..56 are accepted;
all output publication is deferred until the final step, and any intermediate
`proven=0` preserves caller outputs while requesting more precision.

Exact three-step positive/negative cases and an unresolved second step pin both
transport arithmetic and atomicity. Supplying 57 steps or `16*N-1` scratch is a
non-mutating hard failure.

The complete dyadic-normalization path now composes that transport with the
small-angle Taylor evaluator. Guest C takes a reduced signed midpoint, applies
its canonical Lambert halving count, materializes the normalized magnitude
exactly, encloses sine and cosine there, and doubles those signed intervals back
to the original angle. Caller-owned scratch is `20*N`; insufficient fractional
precision is a retry (`proven=0`) rather than a guessed enclosure.

Independent rational Taylor bounds at the original angle enclose positive and
negative 3/4, a negative denominator-shift-107 dyadic, and the structural
near-four case that uses the full 56-step transport. Q128 with 16 Taylor terms
resolves those fixtures, including all 56 doublings, as coverage only. No fixed
Q/term pair is promoted to a full-domain resource bound.

Normalized dyadic sin/cos is now independently schedulable as well. Stage `s`
requests `s+2` fractional limbs, `4s+8` terms, `s+3` limbs for each of the four
signed endpoints, and `20*(s+3)` reusable scratch limbs. The driver tries every
fitting stage and reports the first pending plan on output or scratch exhaustion
without publishing partial endpoint state.

The first five scratch requirements are 60, 80, 100, 120, and 140 limbs, which
project to 240, 320, 400, 480, and 560 bytes at alignment 4. Stage 53,687,088 is
the last plan whose scratch byte extent fits in `uint32_t` (`0xfffffff0`); stage
53,687,089 remains a valid limb plan but its storage query rejects byte
publication. `3/4` resolves at Q64/8, while the structural near-four and
negative deep dyadics advance to Q128/16. This boundary consumes reduced dyadics
only; full binary64 range reduction and final correct rounding remain open.

The reduced-dyadic boundary is now reachable exactly from raw binary64 values
with magnitude below four whenever the existing SIN/COS small-angle preproof for
the requested operation returns kernel-required. The bridge decodes the raw
significand and binary exponent, removes powers of two from the denominator,
and publishes the signed dyadic without floating arithmetic. Resolved special
inputs, non-finite values, zero, and magnitudes at least four reject without
mutation.

The cosine cutoff is the tight input for this geometry: its next binary64 value
has an odd significand at power `-79`, so the accepted reduced denominator shift
is globally at most 79 and the ceiling is attained. A deterministic 520-case
`Fraction` differential spans both operations, signs, multiple binades, and the
value immediately below four. This bridge is exact input conversion only; it
does not implement periodic range reduction beyond the sub-four domain.

A sub-four raw-input wrapper now composes this exact bridge with the dyadic
scheduler. Its endpoint limbs, signs, proven flag, and selected stage match the
manual two-call composition on retained SIN/COS cases. The near-four input with
four output limbs and 80 scratch limbs reports the pending Q128/16 plan
requiring five output limbs and 100 scratch limbs without publication; that
exact capacity then certifies the same interval.

The wrapper rejects preproof-resolved inputs deliberately. It remains an
internal kernel boundary until a public sin/cos handoff dispatches those special
results, performs periodic reduction for `|x|>=4`, and proves final binary64
rounding.

Final rounding now has a signed variable-width primitive. The gate accepts an
ordered signed-magnitude interval at whole-limb binary precision and rounds each
endpoint independently with integer nearest-ties-even arithmetic. Normal results
use a 53-bit significand plus guard/sticky bits; values below `2^-1022` are
quantized directly in `2^-1074` units, including half-min-subnormal underflow
and the carry from maximum subnormal to minimum normal.

A result publishes only when both rounded endpoint words are identical. Exact
nonzero negative magnitudes retain the sign bit even when they underflow to
negative zero, while an exact zero magnitude canonicalizes to positive zero.
Independent `Fraction` cases cover normal parity ties, both signed underflow
sides, subnormal ties, the normal/subnormal boundary, and ambiguous cross-zero
or adjacent-cell intervals.

The complete sub-four path now reaches final raw binary64 publication. A single
caller-owned workspace reserves four `N`-limb endpoint arrays followed by the
existing `20*N` normalization/refinement scratch, so stage `s` requires exactly
`24*(s+3)` limbs. Special/preproof results bypass workspace entirely; finite
kernel inputs below four advance through retry plans until the selected SIN or
COS interval rounds uniquely.

Independent 40-term rational Taylor bounds certify twelve final results spanning
`0.5`, `1`, `2`, `3`, `nextdown(4)`, and negative symmetry without host trig.
The retained stage distribution is 0/72 limbs for common cases, 1/96 for
`cos(2)` and `sin(3)`, and 2/120 for both near-four outputs. With no workspace
the near-four input reports stage 0/72; 96 limbs exhaust stages 0 and 1 and
report stage 2/120; 120 limbs publishes the certified result. Magnitudes at
least four remain outside this handoff; the independent Payne-Hanek path owns
periodic evaluation.

A fixed Q512/64 direct-Taylor gate now closes the sub-four resource ceiling. The
exact input occupies a 17-limb Q512 value and the evaluator uses 187
caller-owned scratch limbs. Conservative integer width propagation gives at
most 135 sine
and 139 cosine ulps of directed roundoff. Including the first omitted term,
both final intervals are strictly narrower than `2^-460`; product code enforces
the equivalent `<2^52` Q512-ulp bound.

The same global binary64 TMD authority also closes final rounding here. Exact
Machin bounds place every binary64 input more than `2^-53` from `pi` and more
than `2^-54` from `pi/2` at the relevant zeros. Combined with the small-angle
preproof, every non-special sub-four sine/cosine output has magnitude above
`2^-55`, so its ulp is at least `2^-107`. The 68/66 TMD maxima therefore give
absolute midpoint floors `2^-177` and `2^-175`; Q512 leaves at least 283 bits of
margin before either boundary.

A bounded periodic-reduction boundary now handles the next magnitude region.
For finite `4 <= |x| < 2^64`, the exact binary64 dyadic is represented in
Q32.256 and multiplied by a directed Q256 `2/pi` interval. That reciprocal is
the exact floor/ceil cell implied by the independently certified Q256 `pi/4`
cell; the runtime does not admit a rounded host `2/pi` constant as authority.
Both quotient endpoints must select the same nearest-even integer multiple.

Within this bound the selected multiple fits `uint64_t`; its directed product
with `pi/2` fits the widened fixed-point workspace used by the bounded reducer.
Subtraction publishes an ordered signed residual around the
nearest `q*pi/2`, bounded by `pi/4`, plus `q mod 4` and the original input sign.
A deterministic 512-case corpus plus exact binary64 neighbors around selected
multiples from 3 through `11,000,000,000,000,000,000` matches an independent
Machin/`Fraction` reconstruction limb-for-limb. Inputs at or above `2^64` use
Payne-Hanek-style quotient/constant geometry.

That wider constant geometry now has a certified Q2112 reciprocal table. Exact
Machin arithmetic encloses pi tightly enough to determine both endpoints of the
66-limb `2/pi` interval, whose width is two ulps. Starting at `2^31`, a finite
binary64 has dyadic power at least `-21`; therefore a quotient half-boundary
would approximate pi by a rational with denominator below `2^1044`.

The authority computes the common continued-fraction prefix of both directed pi
bounds and checks 626 convergents through that denominator ceiling. By
Legendre, every closer rational would have to occur in that checked set; the
minimum certified separation still exceeds `20*2^-2112`. This leaves roughly
nineteen bits of safety after accounting conservatively for the reciprocal
width and half-boundary scaling. The proof establishes quotient sufficiency of
the Q2112 constant; the product bit extraction and Q256 residual formation are
validated independently.

The corresponding full-domain extractor now covers every finite magnitude from
`2^64` through maximum binary64. It performs an exact 53-by-2112-bit product in
68 limbs for each reciprocal endpoint, extracts nearest-even `q mod 4` directly
around the binary point, and derives the signed fractional distance without
storing the high quotient bits. The Q2112 interval is narrow enough that both
endpoints must select the same quotient by the preceding certificate.

That fractional enclosure is quantized outward to Q256 and scaled by the
existing directed `pi/2` cell, yielding a residual in `+/-pi/4`. Independent
Machin `Fraction` arithmetic checks 320 deterministic inputs spread across the
remaining exponent range, including maximum finite, and matches the quadrant
while lying inside every returned residual. This closes full-domain quotient
and residual geometry; it does not by itself prove Q256 final-rounding
sufficiency for all inputs.

Both periodic reducers now compose with the same Q32.256 trig evaluator. The
bounded path is selected below `2^64`; Payne-Hanek is selected at or above it.
Their signed residual is converted to a nonnegative magnitude interval for the
directed Taylor kernel; negative and cross-zero residuals use exact symmetry,
and `q mod 4` rotates sine/cosine before the original sign is applied. The path
reuses 90 caller-owned scratch limbs and stages its signed outputs.

Independent rational Taylor authority encloses both final intervals for 83
bounded `pi/2` neighbors. A separate high-range composition consumes the
already certified Payne-Hanek residual interval and proves that the entire Q256
interval rounds to the published sine and cosine words for eight retained
inputs through maximum finite. The unique gate remains fail closed for any Q256
ambiguity. These retained successes do not establish a global binary64
precision/resource ceiling.

A stronger active table removes the bounded-path residual-width growth. The
production periodic evaluator now uses Q2176 Payne-Hanek for every finite
`|x|>=4`. Its 68-limb `2/pi` interval is one ulp wide. Because such a binary64
has dyadic power at least `-50`, a nearest-quotient half-boundary induces a
reduced rational approximation to pi with denominator below `2^1073`.

The Q2176 authority retains 641 common pi convergents through that ceiling and,
with Legendre, proves the conservative `30*2^-2176` uncertainty is below every
relevant half-boundary separation, leaving about 25 bits of margin. The old
bounded reducer remains separately callable evidence, but Q256 trig evaluation
no longer accumulates a multiple-scaled `pi/2` cell width before Taylor.

Residual width is now independently bounded as well. One Q2176 reciprocal ulp
multiplied by any finite binary64 is below `2^-1152`, far below one Q256 cell.
Directed fractional quantization can therefore span at most two Q256 ulps.
Because the certified `pi/2` interval is two ulps wide, has upper endpoint below
two, and multiplies a nearest fraction of magnitude at most one half, the exact
scaled interval is strictly narrower than five Q256 ulps.

Directed product floor/ceil then gives an integer-grid width of at most six
ulps. Product code checks that bound fail-closed before publication.

The same quotient geometry now supports a fixed Q512 refinement residual. A
17-limb directed `pi/2` interval regenerated from Machin arithmetic is one Q512
ulp wide. The Q2176 reciprocal uncertainty remains below one Q512 cell after
any binary64 multiplication, so directed extraction and scaling preserve a
six-ulp Q512 residual ceiling.

A 96-case `Fraction` corpus through maximum finite reaches four ulps. This
creates a higher-precision periodic retry layer; it is not a proof that Q512 is
sufficient for every final rounding cell.

The Q512 residual also has an executable trig image. Forty-eight Taylor terms
make both first omitted terms smaller than `2^-512` throughout `|r|<4/5`, and
the variable-width interval kernel requires 170 caller-owned limbs. Quadrant
rotation and input-sign transport are staged before publication. The Q512
binary64 gate remains conservative: only identical nearest-even endpoint words
publish; any ambiguity returns without claiming a result.

Periodic precision selection now has an explicit fixed handoff. Q256/32 is the
90-limb first attempt; only an ambiguous Q256 interval advances to Q512/48 and
its 170-limb requirement. A companion entry point accepts a staged Q256
interval so resource retry can resume without repeating that first evaluation.

Lifecycle evidence resolves real `sin(4)` at Q256, then injects a deliberately
wide Q256 interval solely to exercise retry at 169 limbs and Q512 resolution at
170. This is synthetic transition evidence, not a discovered table-maker case.
Q512 ambiguity has its own unresolved status and never publishes a result.


The fixed periodic gate now uses 32 Taylor terms with no scratch increase.
Because `|r|<4/5`, term 32 is already below one Q256 ulp for both series.
Starting from the six-ulp residual, directed squaring is at most eleven ulps;
propagating integer widths through every multiply and the two recurrence
divisors yields a 74-ulp sine bound and a 71-ulp cosine bound including the
omitted-term enclosure.

The Q256/32 path rejects anything wider than 74 ulps before publication. A
2,052-case retained corpus reaches 40 ulps.


Finite binary64 Table Maker's Dilemma evidence now closes the periodic precision
ceiling without requiring a new effective transcendence theorem. The exhaustive
ARITH 2026 result of Lefevre, Ly, and Zimmermann gives maximal post-round-bit
runs of 68 for sine and 66 for cosine. The repository binds the reviewed
CORE-MATH snapshot by commit and SHA-256 and reproduces its continued-fraction
`wc(e, parity)` construction across all 1,022 periodic binary64 binades.

That reproduction places every relevant closest-to-`pi/2` residual above
`2^-61`. Since `|sin(r)|>|r|/2` on the reduced interval, any periodic output
near zero has magnitude above `2^-62`, so its binary64 ulp is at least `2^-114`.
The TMD separation is consequently at least `2^-184` for sine and `2^-182` for
cosine. The Q256/32 directed interval is narrower than `2^-249`, giving at
least 65 bits of margin before the nearest rounding boundary.

This is a finite-domain engineering certificate backed by an exhaustive
published TMD computation, not an empirical random-search assumption. It closes
the periodic sine/cosine precision question. Public libc wiring now composes
that proof with the fixed sub-four Q512 certificate; the bivariate `atan2`
resource proof remains separate.

The table-maker boundary now has a separate exponential-polynomial parameter
surface. Let a kernel-required binary64 input be rational `x`, let an output
rounding midpoint be `m=a/b`, and put `z=e^(ix)`. For sine,
`P_s(X)=bX^2-2iaX-b` gives `P_s(z)=2ibz(sin(x)-m)`; for cosine,
`P_c(X)=bX^2-2aX+b` gives `P_c(z)=2bz(cos(x)-m)`. Since `|z|=1`, a lower bound
for either nonzero `P(e^(ix))` transfers exactly after division by `2b`.

Guest C exposes the algebraic sizes without constructing the potentially
1,024-bit numerator of `x`. After unary special cases, reduced input numerators
have at most 1,024 bits and denominator shift at most 79. For `alpha=ix`, the
published ceilings are `H(alpha)<2^2048`, at most 1,024 bits for the algebraic
denominator of `1/alpha`, inverse-house exponent at most 27, and
`d(1/alpha)*max(1,|1/alpha|)<=2^1024`.

The candidate result lies in `[-1,1]`. Its exact signed cell midpoints have at
most 54 numerator bits and denominator shift at most 1,075, so the integral
quadratic has `H(P)<2^1076`. `+0` and `-0` intentionally use the one-sided
cells `[0,2^-1075]` and `[-2^-1075,0]`.

Exact `Fraction` checks pin separate tight witnesses for every global ceiling.
The bridge does not yet instantiate a quantitative theorem strongly enough to
prove a finite precision ceiling.

Theorem 1 of the retained Fischler-Rivoal source already gives qualitative
non-equality: for nonzero rational `x`, the degree-two polynomial over `Z[i]` is
nonzero, hence its value at `e^(ix)` cannot vanish. Arbitrarily precise directed
refinement therefore eventually separates every rational binary64 midpoint.

The direct explicit constant remains unusable as a finite guest ceiling. In the
`d=2`, `delta=2` specialization Proposition 1 requires `p>=4`. At
`x=max-finite`, `d(1/alpha)` has 1,024 bits and `t=1`, so `2qt>2^1024` for every
admissible `p`. The proposition's `b` and `v` factors alone imply
`log2(D)>2^8206`, whereas all bits in a maximum `uint32_t` byte block are fewer
than `2^35`.

This is a theorem-selection result, not a claim about actual separation. A
stronger sin/cos-specific quantitative measure or another finite table-maker
argument is still required.


A normalized midpoint comparator now composes those enclosures with the existing
quadrant ordering and exact ratio cross-products. Its caller-owned scratch is
`24*N`, and its result contract remains `-1/0/+1`. Q192/16 matches the direct
comparator on both cell boundaries for all 64 signed retained hard cases, while
a known hard lower boundary remains inconclusive at Q128 and therefore exercises
retry.

A near-four boundary also agrees after the full 56-step transport. This is
differential evidence; the production scheduler has not switched paths.

The normalized comparator also has a caller-owned refinement driver with the
same
open stage sequence as direct refinement. Its plan uses `24*(s+3)` scratch limbs
for stage `s`; the first five requirements are 72, 96, 120, 144, and 168 limbs.
On the retained 4,164-pair corpus, 3,921 cases are special and all 243 kernel
cases certify through the normalized path: 211 first at Q128/16 and 32 first at
Q192/24. No case first certifies at Q64/8, Q96/12, or Q160/20.

A retained hard seed demonstrates resource-driven retry: 119 limbs publishes the
Q128/16 120-limb plan, 167 publishes Q192/24 at 168 limbs, and 168 certifies.
The direct scheduler remains the production path because it is cheaper on much
of this corpus.

A separate scratch-requirement query validates normalized plans against the
24*N planner before translating them to guest byte extents. Stages 0..4 require
288, 384, 480, 576, and 672 bytes with alignment 4. Stage 44,739,239 is the last
normalized plan representable in a `uint32_t` byte extent (`0xffffffc0`); the
next plan is still valid in limbs but byte conversion fails atomically. Direct
and normalized plans are intentionally rejected by each other's byte query.

This supplies the finite rational-height parameter required by any future
quantitative Lambert/Lindemann separation bound. It does not itself lower-bound
`|tan(midpoint)-p/q|`, so the finite resource proof remains open.

A composed separation-parameter query now joins that height to exact candidate
cell geometry. For a kernel-required input and a candidate whose sign matches
the
principal atan2 result, it returns the reduced numerator/denominator/height bit
counts plus the lower and upper dyadic midpoint denominator shifts and their
maximum. Publication is atomic, including rejection of a sign-mismatched cell.

Exact `Fraction` checks cover a retained hard cell, its negative mirror, and a
108-bit axis-boundary kernel cell. Both rational height and
midpoint shifts match independently. The already-proved fallback midpoint-shift
ceiling of 107 therefore has an executable parameter surface ready for a future
quantitative theorem, but the theorem/inequality itself remains open.


The runtime also exposes the algebraic-size bridge to a linear exponential
form. For reduced `t=a/b`, midpoint `m`, `z=e^(2im)`, and
`P(X)=(a+ib)X+(a-ib)` in `Z[i][X]`, the tangent identity gives
`P(z)=b(z+1)(t-tan(m))`. Since `|z+1|<=2`, a lower bound for the nonzero linear
form immediately gives a tangent-separation lower bound after division by
`2b`.

The bridge does not construct Gaussian big integers. From reduced ratio height
`h` it publishes the strict ceiling `H(P)<2^(h+1)` and separately preserves the
reduced rational denominator bit length. For each reduced dyadic midpoint it
also bounds the usual height of `alpha=2im`, the bit length of the algebraic
denominator of `1/alpha`, and a power-of-two ceiling for
`max(1,|1/alpha|)`. Under the already-proved full fallback geometry these become
`H(P)<2^109`, rational denominator bits <=106, `H(alpha)<2^218`,
inverse-denominator bit length <=54, and inverse-house exponent <=106.

The paired quantity needed by the explicit exponential theorem is tighter
still: `d(1/alpha)*max(1,|1/alpha|) <= 2^106`.

Those finite parameters are small enough to make an explicit exponential
transcendence measure a concrete candidate for the remaining resource proof.
The repository has not yet instantiated the theorem-specific constant, so no
precision ceiling follows from this bridge alone.


A quantitative candidate now has canonical provenance in
as the Fischler-Rivoal exponential-transcendence record under
`docs/bibliography/publications/`.
For `K=Q(i)`, `alpha=2im`, algebraic degree `d=2`, and polynomial degree
`delta=1`, the publication's stated height exponent specializes to 11. The
known `H(P)<2^109` ceiling therefore makes the bare `H(P)^-11` contribution
less than 1,199 binary exponent bits. The tight 106-bit rational denominator
makes the additional bridge factor `2b` contribute less than 107, for a nominal
subtotal of 1,306.

The current author manuscript's Proposition 1 now supplies the completely
explicit version. A retained deep cell has `2*q*t=2^107` for `p=2`, and the
least-common-multiple factor prevents larger admissible `p` from reducing it.
For `d=2`, `delta=1`, the proposition's `b` and `v` terms alone give
`log2(D) > 6*107*2^428 > 2^437` for every `p>=2`.

Even the entire maximum normalized guest allocation contains fewer than `2^35`
bits. Therefore this direct Proposition 1 specialization is too weak to prove
the finite guest resource ceiling. This is a statement about the theorem's
guarantee, not about the true midpoint separation or necessary precision.

A more specialized asymptotic result is now retained from Liang-Wang (2024).
Theorem 2 of the publisher PDF states irrationality measure 2 for `tan(r)` at
nonzero rational `r`. Theorem 3 supplies a general power-law lower-bound shape,
but its quantitative hypotheses and conclusion use Vinogradov `<<`/`>>` with
implicit constants; Remark 2 transfers the displayed argument to Theorem 2.

That is directly aligned with the adaptive midpoint problem and its tight
`q<2^106` denominator ceiling, but the paper does not instantiate the hidden
constant for tangent. The result therefore narrows the mathematical target
without closing the finite correct-rounding obligation.

The qualitative termination fact for an adaptive version now has durable
external provenance in
`docs/bibliography/publications/lambert-tangent-irrationality.md`.
Every nonzero binary64 rounding midpoint is rational, while Lambert's theorem
excludes rational `tan(midpoint)`. Since every finite nonzero binary64 input
ratio is rational, exact equality at a same-branch midpoint is impossible.
This proves eventual separation for a correctly directed refinement sequence;
it does not supply the unbounded guest-C storage policy needed to implement
that sequence.

`sin` and `cos` are now source-available and implemented entirely as guest C.
They use fixed automatic scratch and never depend on guest heap initialization
or host libm. `atan2` remains source-unavailable pending its bivariate finite
resource proof.

Version one needs no separate guest scheduler or ordinary-integer-helper API:
integer operations are explicit typed-IR semantics for lane-9 lowering, and the
selected target profile is sequential with no guest thread surface. Allocation
startup binding and byte-I/O intrinsic realization are likewise lane-9 target
work over the stable identities defined here. The canonical promoted-block
varargs cursor is now implemented; source `va_list` bridging remains lane-9
compiler-lowering work. Remaining lane-8 algorithm work is correctly-rounded
`atan2`.

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
