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

Rust product batches now route through hardware-neutral optional backends with
safe-Rust fallback. RTX 4060 current-profile evidence now includes device-side
shared-state replication and persistent scalable sessions. Complete-snapshot
batch 32 reaches about 51.67 VMs/s, while resident batch 128 reaches about
2.00 million 64-step segments/s when setup and snapshots are outside the timed
region. `ProfileMemoryImage` now carries reusable geometry-bound validation proof;
retained batch-32 complete-snapshot throughput reaches about 93.68 VMs/s and
validation/planning falls to about 0.23 ms. Direct complete-snapshot materialization now downloads into final result
arrays without redundant packed host staging; full-state transfer/page commitment
remains a measured cost. `work_ports.py` now defines hardware-neutral candidate
evaluation, search execution, verification-assist, and trusted-admission
boundaries. CPU callback adapters provide mandatory candidate/search execution
capacity while search proposals and verification hints remain untrusted.
`search_selection.py` independently resolves algorithm and backend bindings,
requires a CPU reference, supports explicit overrides, and records configured
versus actual backend identity after fallback. `search_config.py` adds versioned
TOML base selection with fail-closed schema/identity validation and durable source
identity; explicit overrides produce a new effective selection without mutating
the loaded configuration. `primitive_candidates.py` binds
classic crazy/rotate candidate payloads to any exact primitive adapter; the same
bridge is differentially exercised through CPU and live CUDA backends.
`evidence_verification.py` reuses candidate evidence as optional verification
hints without introducing backend acceptance authority, and live CUDA hints match
the CPU reference over a deterministic 257-item corpus. Additional search
strategies, CLI front-end wiring, CUDA search execution, ROCm work ports and VM
execution, broader hardware evidence, and orchestration remain follow-on work. `optimizer/enumerative.py` supplies the first concrete CPU-only
search strategy: deterministic finite-corpus enumeration with canonical replay
identity and independent trusted verification.
