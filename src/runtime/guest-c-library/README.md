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
resolve when exact binary64 representation or an exact quotient-remainder
margin proves the `atan` alternating-series error cannot cross a rounding
midpoint.

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
division, yielding exact or adjacent floor/ceiling endpoints. A 48-term
alternating-series evaluator then propagates directed fixed-point intervals and
adds the proved `2^-128` truncation bound; very small inputs use the direct
`x-x^3/3 < atan(x) < x` enclosure instead. A separate integer long-division
helper rounds the original rational to nearest-even binary64 when a later kernel
needs a bounded floating representation.
