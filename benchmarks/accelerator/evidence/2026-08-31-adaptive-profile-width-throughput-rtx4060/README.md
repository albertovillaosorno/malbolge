# Adaptive profile-width throughput — RTX 4060

This evidence measures the same 64 committed no-op VM transitions at each
product-reviewed `ProfileRunGeometry` width N10 through N15. Batch size is one,
so the varying quantity is the complete resident/result memory geometry rather
than semantic step count.

The timed region is one end-to-end `CudaProfileRunAdapter.evaluate` call.
Adapter construction and NVRTC compilation happen before timing. One warmup is
followed by 15 retained samples per width; complete status, pointers, step
count,
I/O state, and materialized memory length are validated after each timed call.

`throughput.json` contains every raw nanosecond sample, median, population
standard deviation, exact ternary memory size, backend/device identity, and
median VM-step throughput. `source-commit.txt` names the clean harness commit;
`environment.txt` records the live host/GPU runtime identity.

Observed median end-to-end latency was 0.858, 1.062, 2.393, 4.772, 13.359, and
71.145 milliseconds for N10 through N15 respectively. This is memory-bound
full-snapshot evidence only. It does not satisfy the separate compute/search-
heavy performance evidence requirement and does not grant width-selection
correctness authority.
