# Versioned host-capability call ABI

## Status

Proposed

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

The DOOM interoperability work currently supplies design evidence for a narrow
external-effect boundary and a version-1 capability-ID pattern. Its current
capability set is evidence to generalize, not an already standardized VM ABI.
This contract does not freeze those application-local spellings or require a new
Malbolge opcode.

### Implementation Status

Not implemented. No generic VM capability frame, discovery protocol, or accepted
versioned capability registry is claimed yet.

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
- The same frame vectors are executed through interpreter and every admitted
  native tier and compared for guest memory, returned values, diagnostics, and
  externally observable ordering.
- Cross-platform runner tests prove that capability identity does not change
  when
  the host adapter changes.
- Prerequisite completion evidence: `deterministic-c-to-malbolge-abi` and
  `canonical-malbolge-target-profile`.

## References

- [Deterministic C Surface And Clang
  Tooling](../../adr/deterministic-c-surface-and-clang-tooling.md)
- [Compiler Pipeline And Guest
  Runtime](../../adr/compiler-pipeline-and-guest-runtime.md)
- [Tiered Native Execution](../../adr/tiered-native-execution.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)
