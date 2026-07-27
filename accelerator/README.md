# Replaceable accelerator boundary

`accelerator/` owns optional execution capacity behind hardware-neutral exact
contracts. Accelerator results never become semantic authority merely because a
GPU produced them.

The first implemented port is `ExactPrimitiveAdapter`, which batches classic
Malbolge `rotate` and `crazy` over the exact 59,049-word domain.
`ClassicStepRequest`/`ClassicStepResult` represents one specification-mode classic
VM transition over at most four explicitly declared memory cells.
`ClassicRunRequest`/`ClassicRunResult` carries one complete 59,049-word classic
state through bounded resident execution. `ProfileRunGeometry` plus
`ProfileRunRequest`/`ProfileRunResult` extends that boundary to validated
single-word-modular ternary profiles without embedding CUDA identity. The current
14-trit/4,782,969-word profile now executes through the same geometry-bound CUDA
kernel model. `accelerator/cpu/` remains the mandatory scalar primitive reference;
CUDA results are checked against normative Rust execution. Compiler and verifier
code do not import CUDA APIs.

Missing accelerator hardware changes availability/performance only. Malformed
requests fail in the shared contract before backend execution; accelerator
runtime failures are explicit and never silently change acceptance rules.
`resource_budget.py` additionally owns hardware-neutral measured resource
snapshots and deterministic resident chunk planning; it does not know CUDA APIs.

Product-level batch routing, current-profile throughput evidence, candidate
evaluation, search/verification ports, ROCm, broader hardware evidence, and
performance orchestration remain follow-on work.
