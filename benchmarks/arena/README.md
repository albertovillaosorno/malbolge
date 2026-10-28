# Algorithm Evaluation Arena

This directory owns cross-algorithm evaluation definitions and reproducible
comparison reports. Capacity curves and multi-objective Pareto frontiers take
precedence over any convenience score. This is an initial **offline analysis**
slice; it neither runs an experiment nor certifies submitted evidence.

## Analyze retained observations

Run with the repository-pinned Python interpreter:

```sh
python3.14 -B benchmarks/arena/analyze.py path/to/study.json
```

The command prints deterministic JSON, or exits with code 2 without a report
when admission or comparison fails. Its input limit is 16 MiB. Version-one
input has one `study` and a nonempty `observations` array:

```json
{
  "schema_version": 1,
  "study": {
    "id": "study-identity-v1",
    "question": "Does B improve time without increasing code size?",
    "hypothesis": "B has a better time/size frontier than A.",
    "baseline": "A",
    "rejection_observation": "B is dominated or fails verification.",
    "stage": "ternary-ir",
    "target_profile": "malbolge-2026",
    "host": "reviewed-host-identity",
    "toolchain": "reviewed-toolchain-identity",
    "budget": {"time_ns": 1000000000, "memory_bytes": 104857600},
    "objectives": ["elapsed_ns", "artifact_bytes"]
  },
  "observations": [
    {
      "algorithm": "A",
      "case": {
        "family": "arithmetic-dag", "version": 1,
        "difficulty": 1, "seed": 7,
        "workload_sha256":
          "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
      },
      "trial": 0,
      "outcome": "verified",
      "verifier": "independent-verifier-v1",
      "verifier_verdict": "accepted",
      "experiment_manifest": "algorithms/example/experiment.toml",
      "raw_sample": "algorithms/example/out/samples.csv",
      "metrics": {"elapsed_ns": 1000, "artifact_bytes": 4096}
    }
  ]
}
```

This is **an illustrative schema example, not a benchmark result**. A real
comparison needs matched observations from at least two algorithms and the
baseline. All algorithms in each family/version/difficulty cohort must include
the same `(seed, workload_sha256, trial)` combinations. Duplicate trials,
unknown metrics, absent declared successful-run costs, mismatched cohorts,
noncanonical paths, unsupported outcomes, malformed JSON, and an algorithm
claiming to have verified its own successful output are rejected.

Currently recognized costs are `elapsed_ns`, `artifact_bytes`, `runtime_steps`,
`peak_rss_bytes`, `peak_vram_bytes`, and `verifier_ns`. All cost objectives are
minimized; the number of verified trials is maximized. A claimed `verified`
outcome needs a separately named verifier and an `accepted` verdict. Failures
retain their own outcomes (`verifier_rejected`, `no_solution`,
`resource_exhausted`, or `tool_failed`) and at least an elapsed duration.

## Optional linked-run evidence preflight

The standalone analyzer accepts reported records without opening referenced
files. For a stronger **identity-only** preflight, run from the repository root
with the repository-owned validation modules on the Python import path:

```sh
export PYTHONPATH=src/automation/repository/composition
python3.14 -B -m benchmarks.arena.evidence path/to/study.json --root .
```

This optional entrypoint parses each referenced experiment run through the
existing `scripts.validate.experiment_manifest.parse_manifest` authority. It
matches algorithm ID, challenge family, difficulty, seed, target profile,
reported workload SHA-256, host, toolchain, oracle, outcome, and raw-output path
against the arena record. Only bounded regular manifest files and existing,
nonempty raw samples under the supplied root are admitted; symlink hops,
missing artifacts, and identity drift fail closed.

The output includes `evidence_preflight` counts. This check **does not** hash
or parse raw sample contents, rederive challenge bytes, authenticate the Git
commit or device, or replay the independent semantic verifier. A matched
manifest is still a report, not proof of an observed performance result.

## Interpretation and trust boundary

The `capacity_curve` reports attempts, verified attempts, exact success
fractions, failure counts, and the median of **successful** samples for each
objective. A median is `[numerator, denominator]`, not a rounded float.
`pareto_frontiers` compares verified-count and successful-only median costs
within an exactly matched difficulty cohort. Algorithms without a verified
trial remain in the curve but cannot enter the conditional frontier.

The `highest_observed_verified_difficulty` is a measured maximum, not an
interpolated difficulty threshold or a proof of monotonic capacity.

The default analyzer enforces schema and comparison consistency only. It
**does not** open experiment manifests, check raw files, rederive a challenge
source digest, or prove work was completed within the declared resource budget.
It rejects reported successful values above the stated time and resident-memory
limits, but it does not check how those values were measured. An independent
semantic oracle and reviewed raw evidence remain prerequisites for performance
claims under the repository benchmark protocol and experiment-identity
contracts.

Input filenames and reported verdicts must not be treated as evidence of
correctness or authenticated provenance. The sample data in automated tests
is entirely synthetic and must never be cited as Malbolge performance.

Run the self-contained regression suite:

```sh
PYTHONPATH=src/automation/repository/composition python3.14 -B -m pytest \
  benchmarks/arena/tests/ -q
```
