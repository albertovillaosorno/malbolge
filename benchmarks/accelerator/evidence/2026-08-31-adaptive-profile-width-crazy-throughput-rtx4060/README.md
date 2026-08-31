# Adaptive profile-width crazy throughput — RTX 4060

This evidence measures the same 16,384 committed `p`/crazy transitions at each
adaptive acceptance width N10 through N14. Code occupies 0 through 16,383 and
data occupies 32,768 through 49,151, so the two spans are disjoint even at N10.
Every data word starts at zero and the accumulator starts at zero.

The end-to-end route times one `CudaProfileRunAdapter.evaluate` call and retains
complete-state upload, execution, download, and materialization costs. The
resident route uploads one fresh state before timing, times only one synchronous
`CudaProfileRunSession.advance`, and snapshots after timing. Adapter
construction and NVRTC compilation are outside both intervals.

One warmup precedes 15 retained samples per route and width. After every timed
operation the full result is checked: exact status, error, step count,
termination, accumulator, C/D, I/O state, memory length, all 16,384 encrypted
code words, and all 16,384 crazy-written data words must match the independent
expected image.

Median end-to-end latency for N10 through N14 is 12.741, 16.283, 15.155,
24.627, and 32.052 ms. Median resident-only latency is 8.177, 8.513, 9.135,
10.986, and 10.212 ms, corresponding to about 2.004M, 1.925M, 1.794M, 1.491M,
and 1.604M VM-steps/s. The N14 resident median beating N13 and the N12
end-to-end median beating N11 are retained non-monotone observations rather than
being discarded.

This is bounded RTX 4060 performance evidence, not semantic width authority or
a universal scaling law. The trusted verifier remains solely responsible for
whether a program may execute at a narrower semantic width.
