# Secondary Linux native-backend phase evidence

This directory retains release-profile phase-attribution measurements from
`native_backend_pipeline` at clean producer commit
`60f08086de07a434cf8892d8db386794aeb70cd0`. The workload and ISA/scale
matrix match the
earlier uninstrumented backend-pipeline evidence: one VM-derived current-profile
`rotate/jump-code` two-step trace, 15 retained samples per ISA at scales 1, 2,
and 4, one untimed warmup, alternating ISA order, and retain-all outlier policy.

Each sample records end-to-end time plus accumulated direct-selection, fused-
admission, COFF-emission, and semantic-verification nanoseconds. Per-stage
`Instant` calls add measurement overhead, so this bundle is phase-attribution
evidence. Use the earlier uninstrumented bundle for total-pipeline latency.

| ISA | Scale | Total median ns | Select ns | Admit ns | Emit ns | Verify ns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| x86_64 | 1 | 58,371 | 20,057 | 7,044 | 11,063 | 14,346 |
| x86_64 | 2 | 118,862 | 38,196 | 13,775 | 21,786 | 28,166 |
| x86_64 | 4 | 221,791 | 72,739 | 26,896 | 42,212 | 55,753 |
| aarch64 | 1 | 58,709 | 19,998 | 6,920 | 11,170 | 14,399 |
| aarch64 | 2 | 115,495 | 38,587 | 13,665 | 22,138 | 28,666 |
| aarch64 | 4 | 223,927 | 74,083 | 26,879 | 43,021 | 56,332 |

Median phase shares of the summed phase medians are:

- `x86_64` scale 1: select 38.2%, admit 13.4%, emit 21.1%, verify 27.3%.
- `x86_64` scale 2: select 37.5%, admit 13.5%, emit 21.4%, verify 27.6%.
- `x86_64` scale 4: select 36.8%, admit 13.6%, emit 21.4%, verify 28.2%.
- `aarch64` scale 1: select 38.1%, admit 13.2%, emit 21.3%, verify 27.4%.
- `aarch64` scale 2: select 37.4%, admit 13.3%, emit 21.5%, verify 27.8%.
- `aarch64` scale 4: select 37.0%, admit 13.4%, emit 21.5%, verify 28.1%.

The retained Cargo invocation completed all 90 samples with zero benchmark-
stage failures in 10.84 s wall time and reached 588,368 KiB maximum resident
set size. `raw.csv` retains every sample, `metadata.json` binds source/raw
hashes and statistical policy, and `source-commit.txt` records the producer.

Generated code is still not loaded or executed. These measurements therefore
do not support an interpreter-to-native execution speedup claim, and AArch64
rows remain target generation/verification measurements on an x86-64 host.
