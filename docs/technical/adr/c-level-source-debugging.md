# C-Level Source Debugging

## Status

Accepted.

## Context

Generated Malbolge may be extremely large and position-dependent. Requiring an
application developer to debug through raw A/C/D registers and self-modifying
cells would defeat the purpose of providing C as the human authoring surface.

## Decision

The primary developer debugging model is source-level C.

Compiler stages retain source maps from C locations and values through IR,
runtime lowering, layout, and encoded target locations. Debugger operations may
inspect raw VM state for implementation work, but normal application debugging
supports C file/line breakpoints, stepping, frames, variables, and lowering
traces where representable.

## Alternatives Considered

### Raw Malbolge debugger only

Rejected as the public developer interface. It remains useful for VM and backend
validation.

### No debugger to preserve historical difficulty

Rejected because the target language remains difficult; providing tooling does
not change target semantics.

## Consequences

- Source provenance becomes part of compiler contracts.
- Optimization must preserve enough mapping information for useful diagnostics.
- Debug builds may trade output size or optimization quality for source
  observability.

## Implementation Notes

The source-map file format is versioned and deterministic. Debugger support must
not require host implementations of guest application logic.
