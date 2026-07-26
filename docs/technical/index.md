# Technical Documentation Index

This index catalogs repository-owned technical authority and proposed contracts.
Accepted choices live in family-local ADRs; proposed contracts do not claim that
their implementation already exists.

## Decisions

- [C-Level Source Debugging](adr/c-level-source-debugging.md)
- [Compiler Pipeline And Guest Runtime](adr/compiler-pipeline-and-guest-runtime.md)
- [Deterministic C Surface And Clang Tooling](adr/deterministic-c-surface-and-clang-tooling.md)
- [Documentation Authority Taxonomy](adr/documentation-authority-taxonomy.md)
- [Historical Compatibility And Malbolge
  Evolution](adr/historical-compatibility-and-malbolge-evolution.md)
- [Replaceable Accelerator And Algorithm Ports](adr/replaceable-accelerator-and-algorithm-ports.md)
- [Repository Responsibility Boundaries](adr/repository-responsibility-boundaries.md)
- [Self-Hosting As Conformance Goal](adr/self-hosting-as-conformance-goal.md)
- [Tiered Native Execution](adr/tiered-native-execution.md)
- [Verification Trust Boundary](adr/verification-trust-boundary.md)

## Architecture

- [Repository responsibility scaffold](architecture/repository-responsibility-model.md)

## Specifications

- [Historical undefined-behavior catalogue](specification/historical-undefined-behavior.md)
- [Historical Malbolge semantics specification](specification/malbolge-1998.md)
- [Machine-checked mathematical correspondence](specification/mathematics/correspondence.md)
- [LaTeX mathematical specification framework](specification/mathematics/framework.md)
- [Canonical Malbolge target profile](specification/target-profile.md)

## Compatibility

- [Custom target profile identity](compatibility/custom-target-profile-identity.md)
- [Malbolge 2 extended memory model](compatibility/malbolge-2-extended-memory-model.md)
- [Original-interpreter compatibility
  capsule](compatibility/original-interpreter-compatibility-capsule.md)
- [Required-profile diagnostics](compatibility/required-profile-diagnostics.md)

## Virtual Machine

- [Compatibility and strict execution modes](vm/compatibility-and-strict-execution-modes.md)
- [CPU VM table optimization](vm/cpu-vm-table-optimization.md)
- [Independent pure C Malbolge VM](vm/independent-pure-c-malbolge-vm.md)
- [Safe Rust Malbolge VM](vm/safe-rust-malbolge-vm.md)

## Execution

- [Ahead-of-execution native translation](execution/ahead-of-execution-native-translation.md)
- [Batch VM execution](execution/batch-vm-execution.md)
- [Deterministic logical concurrency](execution/deterministic-logical-concurrency.md)
- [Explicit native-tier execution controls](execution/explicit-native-tier-execution-controls.md)
- [Guarded self-modification JIT](execution/guarded-self-modification-jit.md)
- [Native x86-64 and AArch64 backends](execution/native-x86-64-and-aarch64-backends.md)
- [Tiered native execution engine](execution/tiered-native-execution-engine.md)

## Compiler And C Profile

- [Deterministic C-to-Malbolge ABI](compiler/c-profile/deterministic-c-to-malbolge-abi.md)
- [Guest runtime and allocator](compiler/c-profile/guest-runtime-and-allocator.md)
- [malbolge-tidy clang-tidy plugin](compiler/c-profile/malbolge-tidy-clang-tidy-plugin.md)
- [malbolge-tidy lowerability contract](compiler/c-profile/malbolge-tidy-lowerability-contract.md)
- [Supported libc contract](compiler/c-profile/supported-libc-contract.md)
- [Clang C frontend integration](compiler/clang-c-frontend-integration.md)
- [Malbolge layout and encoding backend](compiler/malbolge-layout-and-encoding-backend.md)
- [Compile c2malbolge.c to Malbolge](compiler/self-hosting/compile-c2malbolge-c-to-malbolge.md)
- [Malbolge compiler compiles C to
  Malbolge](compiler/self-hosting/malbolge-compiler-compiles-c-to-malbolge.md)
- [Portable c2malbolge implementation in
  C](compiler/self-hosting/portable-c2malbolge-implementation-in-c.md)
- [Self-hosting equivalence proof](compiler/self-hosting/self-hosting-equivalence-proof.md)
- [C-level source mapping and debugging](compiler/source-mapping-debugging.md)
- [Ternary machine lowering](compiler/ternary-machine-lowering.md)
- [Typed compiler IR](compiler/typed-compiler-ir.md)

## Runtime

- [Deterministic binary byte-stream runtime](runtime/binary-byte-stream.md)

## Verification

- [Differential VM verification](verifier/differential-vm-verification.md)
- [Emitted Malbolge static analyzer](verifier/emitted-malbolge-static-analyzer.md)
- [Exact and diagnostic cycle detection](verifier/exact-and-diagnostic-cycle-detection.md)
- [Proof-producing lowering](verifier/proof-producing-lowering.md)
- [Property, fuzz, and exhaustive testing](verifier/property-fuzz-and-exhaustive-testing.md)
- [Reference interpreter sanitizer harness](verifier/reference-interpreter-sanitizer-harness.md)
- [Translation validation](verifier/translation-validation.md)

## Accelerators

- [Compilation latency performance budget](accelerator/compilation-latency-performance-budget.md)
- [Configurable accelerator algorithm
  adapters](accelerator/configurable-accelerator-algorithm-adapters.md)
- [CUDA exact VM adapter](accelerator/cuda-exact-vm-adapter.md)
- [CUDA superoptimizer](accelerator/cuda-superoptimizer.md)
- [Deterministic CPU optimizer](accelerator/deterministic-cpu-optimizer.md)
- [Future AMD and non-CUDA adapters](accelerator/future-amd-and-non-cuda-adapters.md)
- [Replaceable accelerator boundary](accelerator/replaceable-accelerator-boundary.md)
- [Reusable block catalogue](accelerator/reusable-block-catalogue.md)

## Interoperability

- [User-supplied DOOM source interoperability generator](interoperability/doom-amalgamation.md)
- [DOOM playable generated-code performance](interoperability/doom-generated-performance.md)
- [DOOM quality and modernization pass](interoperability/doom-modernization.md)

## Contracts And Governance

- [Deterministic cross-backend artifact hashing](contracts/deterministic-artifact-hashing.md)
- [Documentation readiness and implementation gate](contracts/documentation-readiness-gate.md)
- [Jig repository governance](contracts/jig-repository-governance.md)
- [Planning corpus promotion to durable documentation](contracts/planning-corpus-promotion.md)
- [Reuse SHAR legal and interoperability corpus](contracts/shar-documentation-reuse.md)

## Examples

- [Versioned C and Malbolge example corpus](examples/versioned-c-malbolge-corpus.md)
