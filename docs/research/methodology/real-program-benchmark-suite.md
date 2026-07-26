# Real-program benchmark suite

- Status: Proposed
- Record type: Methodology
- Planning identity: `real-program-benchmark-suite`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Parametric Multi Objective Algorithm
  Evaluation](../adr/parametric-multi-objective-algorithm-evaluation.md)
- [Research Evidence And Algorithm
  Mirror](../adr/research-evidence-and-algorithm-mirror.md)
- [Verification Trust
  Boundary](../../technical/adr/verification-trust-boundary.md)

## Purpose

Benchmark hello world, byte copying, arithmetic kernels, hashing, parsers,
parametric challenge families, DOOM interoperability, and compiler workloads
across original C, modern C, Rust, CPU batch, JIT, and accelerator paths.

## Evidence Model

- The suite combines fixed real programs with parametric challenges, labels
  which results are demonstrations versus scientific comparisons, and records
  identical compiler/runtime mode for fair cross-version runs.
- The end-to-end fixture demonstrates the intended behavior from admitted
  source/input through the actual generated/executed Malbolge path.
- Performance conclusions use equivalent workloads and report raw-sample
  provenance, resource budgets, dispersion/uncertainty, and failure/success
  behavior rather than only a best-case number.

## Method Or Procedure

Work under this record uses stable identities, explicit inputs and assumptions,
independent correctness evidence where applicable, and retained negative/null
results. Source claims resolve through `docs/bibliography/`.

## Verification And Review

- Expected durable artifact surface: `docs/technical/examples/`,
  `tests/applications/`, `benchmarks/applications/`, `runtime/`.
- Required evidence: reproducible build/run commands, expected outputs or
  interaction traces, artifact hashes, and end-to-end verification.
- Performance evidence pending: raw measurements plus a reproducible
  scaling/statistical summary tied to exact workload and hardware/software
  identity.

## Current Status

No completed research result or implementation claim is made by this proposed
record.
