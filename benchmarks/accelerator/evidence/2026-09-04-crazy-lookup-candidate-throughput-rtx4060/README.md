# CRAZY lookup candidate throughput - RTX 4060

This retained run compares benchmark-only classic CRAZY arithmetic kernels over
the canonical `classic-crazy-target-full-domain-multiposition-v1` workload. The
ordinary route evaluates all 59,049 data words; the prepared route uses the
production exact 1,024-position projection. The production candidate adapter is
unchanged.

Each route uploads its data once. NVRTC compilation, upload, result download,
and trusted CPU comparison are outside timing. One warmup precedes 15 retained
synchronous `CudaRuntime.launch()` samples per arithmetic geometry, and sample
order alternates which kernel runs first. Every warmup and timed sample is
downloaded afterward and required to equal the trusted CPU CRAZY result.

| Route | Tritwise median us | Lookup median us | Lookup / tritwise | Lookup paired wins |
| --- | ---: | ---: | ---: | ---: |
| ordinary 59,049 | 164.655 | 172.067 | 1.045x | 7 / 15 |
| projected 1,024 | 45.027 | 43.360 | 0.963x | 5 / 15 |

The result is mixed rather than promotional. Ordinary median throughput favors
tritwise, while the projected median narrowly favors lookup; however the paired
sample counts favor neither route consistently, and the projected measurements
contain large outliers relative to their roughly 40-45 microsecond baseline.
This run therefore does not justify changing the production candidate kernel or
selecting lookup deterministically.

The structural fanout record explains one plausible pressure source: both
ordinary and projected order retain maximum 32-address fanout in the low lookup
for every full warp, while the projected middle lookup is uniform. This timing
run does not measure constant-cache hits, misses, or physical traffic. The
hermetic CUDA bundle still provides no Nsight Compute, CUPTI, or NVPerf surface.

`source-commit.txt` identifies the clean benchmark commit. `throughput.json`
preserves all 60 timed samples plus the benchmark, workload, geometry, and GPU
identity emitted by that commit.
