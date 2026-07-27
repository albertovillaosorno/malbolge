# Deterministic logical concurrency

## Status

Active implementation

## Purpose

Define explicit logical task identity and deterministic joins for host work that
is structurally independent while preserving Malbolge's sequential guest
semantics exactly.

This feature does not add guest threads, guest shared-memory concurrency, or a
new scheduling semantic to Malbolge. It is a host orchestration layer over owned
independent VM requests.

## Scope

This contract currently governs:

- `vm/src/logical.rs`
- `vm/src/batch.rs`
- `tests/vm/logical.rs`
- `tests/vm/profile_logical.rs`
- `tests/vm/batch.rs`
- `tests/vm/profile_batch.rs`
- `benchmarks/interpreter/`

## Current Behavior

### Independence Boundary

`LogicalTask` owns one classic `BatchRequest` and one `LogicalTaskId`.
`ProfileLogicalTask` uses the same ID type while owning one
`ProfileBatchRequest`. Those batch requests own either all source/input/profile
construction data or an already constructed machine.

That ownership boundary is the executable independence evidence for the current
CPU implementation: logical tasks do not receive references to shared mutable
machine state, shared input cursors, or shared guest memory. The logical layer
therefore cannot make two guest machines race with one another.

Callers must not use this API as a declaration that arbitrary external side
effects are independent. The current task type contains VM execution requests
only; future task kinds with filesystem, device, or shared-runtime effects need a
separate reviewed independence contract before host parallelism is admitted.

### Logical Ordering

`LogicalTaskId` is an explicit unsigned 64-bit identity. Its numeric ascending
order defines logical result and join order.

Physical input order is not semantic. Before any batch execution begins, the
logical layer sorts tasks by ID and rejects duplicate IDs. Therefore a caller may
supply tasks in any physical order without changing the logical result stream.

Duplicate identity fails before worker-count validation or task execution. This
prevents two independently owned computations from competing for one logical
position.

### Sequential Baseline

`execute_logical_tasks()` is the semantic baseline. It:

1. validates and sorts task identities;
2. delegates owned requests to sequential `execute_batch()`;
3. tags each batch result with the corresponding logical ID; and
4. returns results in strict ascending logical order.

The underlying guest machine remains sequential and unchanged. The profile-driven
counterpart `execute_profile_logical_tasks()` applies the same ID normalization
before `execute_profile_batch()` and retains each task's canonical profile.

### Host-Parallel Execution

`execute_logical_tasks_parallel()` performs the same identity validation and
ordering, then delegates those owned requests to `execute_batch_parallel()` with
an explicit positive worker count.

The batch scheduler may complete chunks on different host threads, but it already
returns results in input order. Because its input has first been normalized to
logical-ID order, host completion order is never observable through the logical
API.

Batch scheduler failures remain typed host failures for both classic and
profile-driven logical tasks. Zero workers, for example, becomes
`LogicalConcurrencyError::Batch(BatchError::ZeroWorkers)` rather than a guest
diagnostic.

### Deterministic Join

`join_logical_outputs()` is a host-side artifact join. It concatenates bytes that
were already committed to each completed machine's output stream, in strict
ascending logical-ID order.

The join does not merge guest memory, registers, input streams, or execution
histories. It therefore creates no guest-visible communication channel.

The function independently validates that supplied results remain in strict
ascending order. Reordered or duplicated result sequences fail rather than
silently producing a different artifact. If any logical task was rejected, the
join fails at the first rejected task in logical order and names that exact task
plus its deterministic `ExecutionError`.

Importantly, one rejected task does not cancel its independent neighbors. Batch
execution still records all per-task results; only construction of a successful
joined artifact is rejected. `join_profile_logical_outputs()` applies the same
rule with `ProfileMachineError` while leaving each machine/profile independent.

### Falsifiable Correctness Question

**Question:** can structurally independent VM requests execute on different host
workers while producing exactly the same logical task order, full final VM
state, I/O, run outcomes, diagnostics, and joined output as the sequential
logical baseline?

**Baseline:** `execute_logical_tasks()` over the same owned tasks, with logical
order defined exclusively by ascending `LogicalTaskId`.

**Rejection observation:** any worker count, physical input permutation, or host
schedule that changes a task's registers, complete classic-memory fingerprint,
input consumption, output, run outcome, diagnostic, logical position, or joined
artifact rejects this technique for that task class. A join whose bytes depend
on completion order also rejects the design.

**Current observation:** the executable fixtures deliberately submit tasks in
physical order `30, 10, 20`; both sequential execution and worker counts 1, 2,
and 8 produce logical order `10, 20, 30`, identical full-state snapshots, and
joined output `ABC`. A rejected middle task does not prevent the later task from
executing, while the artifact join fails deterministically at the rejected task.
Duplicate task IDs and deliberately reordered result sequences also fail closed.

Profile-driven fixtures additionally scramble one `malbolge-2026.1` task and one
`malbolge-2026.2` task. Sequential and two-worker execution both return logical
order `10, 20`, preserve transition/current profile identities respectively, and
join bytes as `AB`. Profile rejection and reordered profile results fail through
the typed profile join errors without cancelling later independent tasks.

This is a correctness observation, not a performance conclusion.

### Performance Position

The underlying batch executor already has retained worker-scaling measurements.
Those measurements establish that independent host execution can benefit some
workloads, but they do not measure the added logical sort/tag/join layer.

No speedup is claimed for deterministic logical concurrency yet. A future
performance claim must benchmark the complete logical path against the
sequential logical baseline with identical tasks and joined artifacts. A result
showing sort/join overhead erases batch parallel gains would materially weaken
the practical value of this layer without changing its correctness contract.

Because the current work is ordinary execution-engine product engineering rather
than a new executable algorithm experiment, it is not mirrored into
`algorithms/` or `docs/research/algorithms/`.

## Invariants

- Guest Malbolge execution remains sequential and deterministic.
- Host parallelism is limited to separately owned VM requests with no shared
  mutable guest state.
- Logical ID order, not physical input or completion order, controls results and
  joined artifacts.
- Duplicate logical IDs fail before execution.
- Worker count cannot change per-task state, I/O, outcomes, diagnostics, or join
  bytes.
- Rejected tasks remain isolated per-task results and make a successful artifact
  join fail explicitly.
- Logical joins concatenate committed output only; they never merge guest state.
- Scheduler failures remain host-level typed diagnostics.

## Failure Behavior

- duplicate task ID -> `LogicalConcurrencyError::DuplicateTaskId`;
- batch scheduler failure -> `LogicalConcurrencyError::Batch`;
- reordered/duplicated result sequence at join ->
  `LogicalJoinError::OutOfOrder`;
- rejected classic task during join -> `LogicalJoinError::RejectedTask`;
- reordered/duplicated profile results -> `ProfileLogicalJoinError::OutOfOrder`;
- rejected profile task -> `ProfileLogicalJoinError::RejectedTask` with exact ID
  and `ProfileMachineError`.

No logical-concurrency failure is translated into a new Malbolge guest
instruction, state transition, or termination reason.

## Verification

- `tests/vm/logical.rs` compares sequential and host-parallel logical execution
  for worker counts 1, 2, and 8 using full classic-memory fingerprints,
  registers, input consumption, output, run outcome, and diagnostics.
- The same tests prove physical task input order does not affect logical order or
  joined output, duplicate IDs fail before worker validation, rejected tasks do
  not cancel neighbors, and reordered results cannot be joined.
- `tests/vm/profile_logical.rs` proves mixed transition/current profile identity,
  sequential/parallel joined-byte equality, duplicate-ID precedence, profile
  rejection isolation, and reordered-result failure.
- `tests/vm/batch.rs` and `tests/vm/profile_batch.rs` remain lower-level evidence
  that independently owned classic/profile machines are isolated by the shared
  scheduler.
- `cargo test --workspace --all-features` is the executable semantic gate.
- `jig validate --root .` remains the repository-wide closure gate.

## References

- [Batch VM execution](batch-vm-execution.md)
- [Tiered Native Execution](../../adr/tiered-native-execution.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/tiered-native-execution.md`
- `docs/technical/adr/verification-trust-boundary.md`
