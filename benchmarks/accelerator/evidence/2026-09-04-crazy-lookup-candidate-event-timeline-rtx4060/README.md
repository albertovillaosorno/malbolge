# CRAZY lookup candidate CUDA-event timeline - RTX 4060

This retained diagnostic measures the exact same benchmark-only tritwise and
five-trit lookup kernels used by `cuda-crazy-lookup-candidate-throughput-v1`.
It reuses the canonical 59,049 ordinary candidates and production exact
1,024-position projection, while keeping the production candidate adapter
unchanged.

Each sample launches one kernel on a fresh isolated nonblocking stream with CUDA
events recorded immediately before and after that kernel. Event-origin setup,
stream creation/destruction, result download, and trusted CPU validation are
outside the reported event duration. Every warmup and retained sample is still
downloaded and required to equal trusted CPU CRAZY semantics.

| Route | Tritwise median us | Lookup median us | Lookup / tritwise | Lookup paired wins |
| --- | ---: | ---: | ---: | ---: |
| ordinary 59,049 | 5.408 | 16.384 | 3.030x | 0 / 15 |
| projected 1,024 | 22.528 | 23.392 | 1.038x | 2 / 15 |

The ordinary route rejects lookup decisively in this isolated-stream device
view. The projected route also favors tritwise by median and paired samples, but
its tritwise event durations are bimodal: several samples are about 3-4 us while
most are about 22-34 us. CUDA event intervals can include scheduling effects
between their markers, so this record does not claim pure instruction duration
or physical constant-cache traffic.

Together with the retained default-stream wall-time run, this evidence supports
keeping the candidate evaluator tritwise. It does not establish a selection rule
for the separate resident VM geometry benchmark, where the workload and retained
throughput evidence differ. `timeline.json` preserves all 60 event durations and
`source-commit.txt` identifies the clean harness commit.
