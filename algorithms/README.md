# Algorithm Implementations

This directory contains executable implementations of algorithms studied or
compared by the compiler research program. It is organized by algorithm
identity, not language or hardware.

```text
algorithms/<id>/
|-- experiment.toml   versioned experiment defaults/matrix
|-- *.rs / *.c / *.py / *.cu
|-- tests/
`-- out/              generated local artifacts; Git ignored
```

Only genuine research algorithms belong here. Product algorithms remain with the
responsibility that owns them, such as `interop/algorithms/` for DOOM source
normalization.
