# Replaceable accelerator boundary

`accelerator/` owns optional execution capacity behind hardware-neutral exact
contracts. Accelerator results never become semantic authority merely because a
GPU produced them.

The first implemented port is `ExactPrimitiveAdapter`, which batches classic
Malbolge `rotate` and `crazy` over the exact 59,049-word domain.
`ClassicStepRequest`/`ClassicStepResult` represents one specification-mode classic
VM transition over at most four explicitly declared memory cells.
`ClassicRunRequest`/`ClassicRunResult` now carries one complete 59,049-word classic
state through a bounded multi-step run while keeping the full memory image resident
on the accelerator. `accelerator/cpu/` remains the mandatory scalar primitive
reference. `accelerator/cuda/` is optional; VM results are checked directly against
normative Rust execution. Compiler and verifier code do not import CUDA APIs.

Missing accelerator hardware changes availability/performance only. Malformed
requests fail in the shared contract before backend execution; accelerator
runtime failures are explicit and never silently change acceptance rules.
`resource_budget.py` additionally owns hardware-neutral measured resource
snapshots and deterministic resident chunk planning; it does not know CUDA APIs.

Current-profile resident execution, product-level batch routing, candidate
evaluation, search/verification ports, ROCm, adaptive resource policy, and
performance orchestration remain follow-on work.
