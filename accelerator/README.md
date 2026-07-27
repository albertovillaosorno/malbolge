# Replaceable accelerator boundary

`accelerator/` owns optional execution capacity behind hardware-neutral exact
contracts. Accelerator results never become semantic authority merely because a
GPU produced them.

The first implemented port is `ExactPrimitiveAdapter`, which batches classic
Malbolge `rotate` and `crazy` over the exact 59,049-word domain. A second shared
contract, `ClassicStepRequest`/`ClassicStepResult`, represents one specification-
mode classic VM transition over at most four explicitly declared memory cells.
`accelerator/cpu/` is the mandatory scalar primitive reference. `accelerator/cuda/`
is optional; compact VM transitions are checked directly against normative Rust
`Machine::step_traced()` evidence. Compiler and verifier code do not import CUDA
APIs.

Missing accelerator hardware changes availability/performance only. Malformed
requests fail in the shared contract before backend execution; accelerator
runtime failures are explicit and never silently change acceptance rules.

Resident/full-memory multi-step VM batching, candidate evaluation, search,
verification ports, ROCm, and performance orchestration remain follow-on work.
