# Benchmarks

Benchmarks measure compiler, optimizer, verifier, VM, native-execution, and
accelerator behavior without becoming correctness authorities.

- `challenges/` owns deterministic parametric challenge definitions.
- `arena/` owns cross-algorithm comparison and Pareto/capacity analysis.
- subject-specific benchmark directories own reproducible workload definitions
  for their subsystem.

Raw or regenerable run output stays local and Git ignored. Correctness verdicts
come from the applicable semantic oracle or verifier, not from benchmark success.
