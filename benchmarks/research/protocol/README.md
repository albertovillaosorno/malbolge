# Benchmark protocol fixtures

These files are schema fixtures for `benchmark-evidence-v1`. They are not
performance claims about Malbolge implementations.

`deterministic.benchmark.toml` demonstrates equivalent-workload measurement with
explicit
warmup, retained samples, dispersion, uncertainty, resources, and a retain-all
outlier policy. `stochastic.benchmark.toml` additionally fixes one seed per
trial and keeps
a failed trial in the raw data instead of silently dropping it.

The validator is
`src/automation/repository/composition/scripts/validate/benchmark_protocol.py`.
New research
performance evidence may use the same core obligations while keeping
study-specific raw formats and additional metadata.

Each benchmark fixture references a linked `.experiment.toml` with
`record_kind = "run"`. The validator requires host, accelerator, and raw-output
identity to agree across both records, while commit/workload/toolchain identity
comes from the experiment-run manifest.
