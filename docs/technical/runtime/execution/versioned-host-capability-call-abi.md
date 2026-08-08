# Versioned host-capability call ABI

## Status

Implemented version-one semantic ABI. Generated-artifact lowering and the
cross-platform production runner matrix remain downstream work owned by
`cross-platform-native-capability-runners`.

## Purpose

Define one versioned semantic call ABI for guest requests that require an
external host capability without exposing the host operating-system ABI, libc,
multimedia stack, or transport implementation to guest code. Capability identity
and guest-visible semantics remain stable while interpreters, JITs, AOT runners,
and later execution tiers may use different host-side adapters.

## Scope

This document governs the following declared TODO scope:

- `runtime/`
- `execution/`
- `vm/`
- `tools/tidy/`
- `tests/vm/`

## Current Behavior

### Proposed Model

A capability call is identified by a stable capability family, explicit ABI
version, deterministic argument/result schema, and one validated call frame.
Transport is not identity: direct host calls, interpreter dispatch, JIT/AOT
lowering, IPC, or another adapter may implement the same capability without
changing its guest-visible contract.

The DOOM interoperability work supplies design evidence for a narrow external-
effect boundary and a version-1 capability-ID pattern. The broader DOOM host
surface remains application-local evidence rather than a standardized VM ABI.
This contract promotes four opaque version-one families: monotonic time,
relative-duration sleep, the historically reserved execution-telemetry family,
and guest-directed relative mouse capture. It does not freeze other
`DoomHost_*` spellings or require a new Malbolge opcode.

### Implementation Status

A transport-independent version-one framing foundation is implemented in both
safe Rust and independent pure C. It defines the canonical frame, registry
metadata, discovery categories, range admission, and response-state validation.
The two implementations share fixed byte vectors, but neither calls the other.

The version-one semantic ABI is implemented. Four capability-specific schemas,
one transport-neutral safe-Rust dispatch coordinator, independent Rust/C wire
contracts, and one production standard-library timing transport are executable.
The deterministic C ABI prerequisite is complete.

This contract deliberately stops before generated-artifact capability lowering
and the supported Windows/macOS/Linux runner matrix. That work is owned by the
downstream `cross-platform-native-capability-runners` contract, which depends on
this semantic ABI and must consume its identities and vectors unchanged.

The implementation surfaces are:

- `src/runtime/virtual-machine/contract/host_capability.rs` for generic safe-
  Rust framing and payload-span primitives;
- `src/runtime/virtual-machine/contract/host_capability_mouse.rs`,
  `host_capability_telemetry.rs`, and `host_capability_time.rs` for safe-Rust
  built-in schemas;
- `src/runtime/virtual-machine/port-outbound/host_capability.rs` for the
  transport-neutral effect port;
- `src/runtime/virtual-machine/application/host_capability_dispatch.rs` for
  validate-effect-commit orchestration and the sorted built-in registry;
- `src/runtime/virtual-machine/adapter-outbound/host_capability_time.rs` for a
  production standard-library monotonic-time/sleep transport;
- `src/runtime/virtual-machine/adapter-outbound/c/malbolge_host_capability*.h`
  and matching `.c` files for independent pure-C codecs, validators, and
  canonical built-in registry assembly;
- `tests/vm/host_capability*.rs` for safe-Rust vectors; and
- `tests/vm/host_capability*_conformance.c` plus
  `tests/test_host_capability_c_abi.py` for independent C vectors on reviewed
  Windows ABI targets.

### Transport-neutral dispatch

The safe-Rust VM now exposes one synchronous application dispatcher shared by
all future runner adapters. It validates the request and guest ranges before the
outbound transport can observe the call. The transport receives only immutable
request payload bytes plus the admitted frame; it never receives mutable guest
memory or a host pointer.

A transport returns a response frame and host-owned staged result bytes. The
dispatcher validates response identity, status, blocking/partial-progress rules,
and staged-result length before atomically copying any result into guest memory.
An invalid response or transport failure leaves guest memory unchanged.

`host_builtin_capability_registry()` returns the currently implemented built-in
descriptors in canonical semantic-ID order: monotonic time `0x00000400`, sleep
`0x00000401`, execution telemetry `0x00000600`, then relative mouse capture
`0x00000601`. Typed availability state is transport policy and does not change
identity, version ranges, behavior flags, or ordering. Pure C exposes the
same typed-availability registry constructor and rejects invalid enum values or
wrong registry extent before writing descriptors. Additional production families
may be added only through explicit versioned schema work.

Three independent test transports model interpreter-, JIT-, and AOT-style
adapter strategies through this same dispatcher. One uses the semantic frame
directly, one performs a canonical wire encode/decode round trip, and one
reconstructs the response field by field. Two-call vectors prove identical
response bytes, guest memory, and effect ordering across those distinct paths.
These are tier-neutral semantic-ABI fixtures, not claims that production native
runners are already implemented.

The standard-library timing transport is a concrete production implementation
of the same port. It creates one private `Instant` origin per transport, returns
nondecreasing nanosecond observations, maps unrepresentable/regressing clock
state to `HOST_ERROR`, uses host thread sleep only for positive blocking
requests, returns `WOULD_BLOCK` for positive `NONBLOCKING` sleeps, and completes
a zero-duration sleep without waiting. It exposes no wall-clock epoch or native
timer handle.

### Version-one call frame

The canonical call frame is exactly 72 bytes and uses little-endian integers.
It contains no native pointer, handle, function address, or transport identity.
A decoder recognizes the magic and ABI-version prefix before interpreting
version-one payload fields; an unsupported future version is therefore reported
as version drift even if its record size or later field encodings differ.
The byte layout is:

- offset 0: `magic`, unsigned 32-bit value `0x4348424d` (`MBHC` on the wire);
- offset 4: `abi_version`, unsigned 16-bit value `1`;
- offset 6: `frame_size`, unsigned 16-bit value `72`;
- offset 8: `capability_id`, unsigned 32-bit semantic family identity;
- offset 12: `capability_version`, unsigned 16-bit semantic version;
- offset 14: `operation`, unsigned 16-bit capability-defined operation;
- offset 16: `flags`, unsigned 32-bit call behavior flags;
- offset 20: `status`, unsigned 32-bit completion state;
- offset 24: `request_offset`, unsigned 64-bit guest-memory byte offset;
- offset 32: `request_length`, unsigned 64-bit guest-memory byte length;
- offset 40: `result_offset`, unsigned 64-bit guest-memory byte offset;
- offset 48: `result_capacity`, unsigned 64-bit writable byte capacity;
- offset 56: `result_length`, unsigned 64-bit produced byte length; and
- offset 64: `call_id`, unsigned 64-bit guest-selected request identity.

Capability ID zero and capability version zero are reserved and invalid. Version
one defines request flag bit `0x00000001` as `NONBLOCKING`; unknown call-flag
bits fail closed. A request enters validation with status `PENDING` and zero
result length.

Status values are fixed as `PENDING = 0`, `COMPLETE = 1`, `PARTIAL = 2`,
`WOULD_BLOCK = 3`, `HOST_ERROR = 4`, and `CANCELLED = 5`. Unknown status values
fail closed. The immutable request identity fields must match the admitted
request exactly.

### Version-one capability descriptor

Each registry descriptor is exactly 16 bytes and uses little-endian integers:

- offset 0: `capability_id`, unsigned 32-bit semantic identity;
- offset 4: `minimum_version`, unsigned 16-bit inclusive version;
- offset 6: `maximum_version`, unsigned 16-bit inclusive version;
- offset 8: `flags`, unsigned 32-bit availability/behavior flags;
- offset 12: `abi_version`, unsigned 16-bit value `1`; and
- offset 14: `descriptor_size`, unsigned 16-bit value `16`.

Descriptors therefore reject ABI-version or record-size drift before their
semantic fields are admitted. Registry entries are strictly ordered by nonzero
capability ID, so duplicate or ambiguous identities are invalid. Version one
descriptor flag bit `0x00000001` declares `AVAILABLE`, bit `0x00000002`
declares `MAY_BLOCK`, and bit `0x00000004` declares `PARTIAL_PROGRESS`;
unknown bits fail closed. Each descriptor represents one contiguous supported
version interval. A family with intentionally discontinuous compatibility must
use a new family identity rather than imply support for the hole. Discovery
distinguishes an unknown family, an unsupported semantic version, and a known
but unavailable capability. A serialized registry is the concatenation of zero
or more complete 16-byte version-one descriptors; trailing partial records are
malformed. Registry scanning inspects each descriptor's version prefix before
assuming the version-one stride, preserving an unsupported-version diagnostic
for future descriptor sizes. Discovery validates the entire serialized registry
before returning a match, so a malformed later record cannot be hidden by an
earlier requested identity.

### Canonical capability payload primitives

Capability IDs are opaque unsigned identities. Numeric adjacency, high bits, or
any other bit pattern does not imply a category, transport, privilege, or native
backend. A registry generator must reject duplicate allocation rather than infer
meaning from an ID's numeric shape.

Capability payload integers use the same little-endian fixed-width convention as
the outer frame. A canonical payload-relative byte span is exactly 16 bytes:
`offset: u64` followed by `length: u64`. The offset is relative to the beginning
of the containing capability payload, never a host pointer or guest-machine
absolute address. A schema supplies a minimum payload-data offset so a span
cannot point back into its fixed header. The shared validators reject overflow,
out-of-record ranges, and schema-specific noncanonical layouts as
`INVALID_PAYLOAD`/`InvalidPayload` before a host effect.

Booleans are not an implicit C representation. A capability that declares a
byte boolean must define `0` and `1` explicitly and reject every other value.
Likewise, text encoding is capability-specific; no payload inherits a host
locale, C-string terminator, or native `wchar_t` representation by default.

`NONBLOCKING` is canonical only for a descriptor that declares `MAY_BLOCK`.
Setting the request flag for a capability that cannot block is rejected rather
than creating two encodings for identical behavior.

### Built-in version-one extension schemas

The following four IDs are opaque VM capability identities. Numeric adjacency
carries no family or category semantics. The timing families generalize timing
needs already present at the DOOM boundary; telemetry and mouse retain their
historically reserved identities.

#### Monotonic time `0x00000400`

Version `1`, operation `0`, observes a runner monotonic clock. The request is
empty and reserves exactly eight result bytes. `COMPLETE` returns one
little-endian `u64` nanosecond count. The clock origin is intentionally
unspecified and inaccessible: the value is not Unix time, local time, a calendar
clock, or evidence about a host wall-clock epoch.

Within one production runner execution context, successful observations must not
decrease. A host counter failure, regression that the adapter cannot safely
normalize, or conversion that cannot be represented as `u64` fails with
`HOST_ERROR` instead of publishing a wrapped or wall-clock-derived value. The
schema codec itself does not maintain clock history; that monotonicity
obligation
belongs to the production runner adapter.

Monotonic-time observations are explicit external inputs, not deterministic
pure-computation results. Differential or replay validation therefore supplies
the same recorded response sequence to each compared tier. Tier equivalence is
agreement for the same capability responses, not an assertion that two live
clock reads must return equal numbers.

#### Relative-duration sleep `0x00000401`

Version `1`, operation `0`, requests one little-endian `u64` duration in
nanoseconds and reserves no result bytes. Its descriptor declares `MAY_BLOCK`.
A zero duration may complete immediately. A blocking request uses flags zero;
a production adapter may report `COMPLETE` only after the requested duration has
elapsed according to its monotonic timing source, subject to later scheduling.

A request with `NONBLOCKING` asks the adapter not to wait. If the requested wait
cannot complete without blocking, `WOULD_BLOCK` is the canonical response and
carries no result bytes. `PARTIAL` is never valid for version one. Host timer
failure and cancellation use the generic `HOST_ERROR` and `CANCELLED` statuses.
No sleep request exposes a native timer handle or host scheduler identity.

#### Execution telemetry `0x00000600`

Version `1`, operation `0`, is optional execution-activity observation. Its
registry descriptor may declare only `AVAILABLE`; it never declares `MAY_BLOCK`
or `PARTIAL_PROGRESS`, and the request reserves no result bytes. The request
payload has a 64-byte fixed header:

- offset 0: `flags: u32`, exactly zero in version one;
- offset 4: reserved `u32`, exactly zero;
- offset 8: `location: u64`;
- offset 16: canonical span for `language`;
- offset 32: canonical span for `source`; and
- offset 48: canonical span for `instruction`.

The three span targets follow the header contiguously in exactly
`language`, `source`, `instruction` order with no gaps, overlaps, alternate
ordering, or trailing bytes. Each string is nonempty, length-delimited UTF-8 and
must not contain U+0000. No NUL terminator is encoded. The UTF-8 decoder rejects
overlong sequences, surrogate encodings, values above U+10FFFF, stray
continuations, and truncated sequences.

`location` is interpreted by `language`: native C instrumentation reports the
source location promised by its compiler/debug mapping, while Malbolge reports a
cell or instruction address. `source` is the corresponding source/artifact
identity and `instruction` is the active instruction text. Observation must not
change guest memory, scheduling, diagnostics, or external-effect ordering.
Instrumentation first discovers the capability; if it is absent or unavailable,
it omits telemetry instead of submitting a required call. Once a telemetry frame
is submitted, ordinary fail-closed admission rules apply.

#### Relative mouse capture `0x00000601`

Version `1`, operation `0`, records the guest's desired relative-mouse capture
state. Its descriptor may declare only `AVAILABLE`; it is synchronous and
reserves no result bytes. The request is exactly eight bytes: byte 0 is `0` to
request release or `1` to request relative capture, and bytes 1 through 7 are
zero. Every other boolean or reserved-byte value is invalid.

Capture is a desired runner state, not a promise that a native window system
will
hold capture while focus is absent. A successful `capture=1` request records the
desire for relative capture while the runner's interactive surface is eligible;
focus loss may release native capture and focus regain may restore it. A
`capture=0` request clears that desire and requests release. Native inability to
accept the requested state is reported through the ordinary response status, not
through hidden platform-specific bytes.

### Guest range and completion rules

Offsets are byte offsets into the selected guest-memory domain rather than host
addresses. A nonempty range must fit without integer wrap, while a zero-length
range may point exactly at the end of guest memory. Request and result ranges
must not overlap when both are nonempty. These checks occur before a host effect
is eligible to run.

`PARTIAL` is accepted only for a descriptor that declares partial progress and
only when at least one result byte was produced. `WOULD_BLOCK` is accepted only
when the capability declares that it may block and the request explicitly used
`NONBLOCKING`. Generic host-error and cancellation statuses do not carry result
bytes. Capability-defined semantic failures that need guest-visible detail use
the capability's versioned result schema rather than overloading `HOST_ERROR`.

A host adapter must stage result bytes outside the guest-memory domain while the
external operation is in flight. Guest result memory is published only after the
response frame is validated and the staged byte count exactly matches
`result_length`. The shared C and safe-Rust primitives implement that
validate-then-publish sequence; the C boundary additionally rejects a staged
buffer that aliases guest memory. Rejected responses leave guest memory
unchanged.

The framing layer validates retry/completion identity through `call_id`, but it
does not provide a replay cache or transport lifecycle. Capability-specific
contracts remain responsible for defining whether a retry is legal and how an
adapter obtains or preserves any host-side operation state. A runner therefore
retains the admitted request snapshot until the final response is validated;
the mutable response frame is not itself the authority for original identity.

## Invariants

- Capability identity, semantic version, and guest-visible argument/result types
  are independent from the host transport or native backend that services them.
- Every call frame has one deterministic encoding with explicit integer widths,
  byte order, pointer/range representation, result status, and failure
  semantics.
- Guest pointers and byte ranges are validated against the selected guest memory
  domain before a host-side effect observes or mutates them.
- Unknown capability families, unsupported versions, invalid frames, invalid
  ranges, and unavailable capabilities fail explicitly rather than falling back
  to an unrelated host service.
- Blocking, partial-progress, cancellation, retry, and completion behavior are
  capability semantics where applicable and cannot vary silently by runner.
- Capability discovery reports semantic availability; it does not expose host
  library names, file descriptors, native pointers, calling conventions, or
  another host ABI as guest-visible state.
- Accepted guest C may lower a declared external effect to this ABI, but the ABI
  never turns host libc or platform APIs into an implicit guest runtime.
- Interpreter, JIT, AOT, and other execution tiers must produce equivalent
  guest-visible memory, results, diagnostics, and external-effect ordering for
  the same validated call frame.
- A literal new Malbolge instruction is not required. Any eventual encoding or
  lowering mechanism must be versioned and verified independently from the
  semantic capability identity.

## Failure Behavior

Malformed frames, unsupported capability/version pairs, invalid guest ranges,
and unavailable required capabilities fail before the prohibited host effect is
performed. A runner must not reinterpret an unknown request, truncate an invalid
range, substitute a host ABI default, or silently change blocking/failure
semantics to keep execution moving.

## Verification

- Required fixtures cover canonical frame encoding, every argument/result type,
  pointer/range boundaries, capability discovery, unsupported versions,
  malformed frames, host failures, and blocking/partial-progress rules.
- `tests/vm/host_capability_dispatch.rs` proves pre-effect rejection, atomic
  response publication, schema-aware clock result admission, canonical built-in
  registry order, and equal observations across three independently labeled
  recording transports.
- `tests/vm/host_capability_time.rs` and the independent pure-C timing harness
  prove identical little-endian clock/sleep vectors, descriptor behavior,
  exact clock result width, and blocking/nonblocking sleep status rules.
- Rust and independent C registry fixtures encode the same exact 64-byte
  four-family descriptor vector; the C constructor also proves invalid
  availability/extent rejection occurs before descriptor publication.
- `tests/vm/host_capability_time_transport.rs` exercises the production
  standard-library timing transport through schema-aware dispatch without
  wall-clock assertions or positive blocking sleeps in the test process.
- Three distinct interpreter/JIT/AOT-style transport fixtures execute the same
  ordered call vectors and compare complete responses, guest memory, and effect
  order at the semantic ABI boundary.
- Downstream cross-platform runner tests must reuse these identities and vectors
  when generated-artifact lowering and platform adapters are implemented; that
  runner matrix is not duplicated in this prerequisite contract.
- Prerequisite completion evidence: `deterministic-c-to-malbolge-abi` and
  `canonical-malbolge-target-profile`.

## References

- [Deterministic C Surface And Clang
  Tooling](../../adr/deterministic-c-surface-and-clang-tooling.md)
- [Compiler Pipeline And Guest
  Runtime](../../adr/compiler-pipeline-and-guest-runtime.md)
- [Tiered Native Execution](../../adr/tiered-native-execution.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)
- [Rust Toolchain 1.97.1](
  ../../../bibliography/platforms-and-runtimes/rust-toolchain-1-97-1.md)
- [Cross-platform Native Capability Runners](
  cross-platform-native-capability-runners.md)
