# CRAZY geometry failure policy

This directory retains the hardware-free output of
`cuda-profile-width-crazy-geometry-failure-policy-v1` from clean source commit
`fc9638565984ff5ff0e97274a783aabf88df31fc`. The diagnostic reuses the frozen
N10-N14 crazy workload, CUDA resident-footprint authority, and shared resource
planner; it does not create a CUDA context or allocate device memory.

For each width, the synthetic resource snapshot gives the planner exactly one
byte less usable memory than the one-VM chunk requires, records the fail-closed
error, then adds that byte and requires admission of exactly one state. Required
chunk bytes for N10-N14 are 301,804; 774,196; 2,191,372; 6,442,900; and
19,197,484 respectively.

The JSON labels product fallback policy separately from direct planner failure.
The corresponding VM regression in `tests/vm/batch_backend.rs` verifies that an
unavailable optional profile backend yields complete-state equality with
sequential safe Rust for N10-N14 and reports every admitted item as
`SafeRustFallback`. No CUDA performance or geometry-selection claim is derived
from this fallback evidence.
