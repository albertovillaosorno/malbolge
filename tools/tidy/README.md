# tools/tidy

`tools/tidy` defines the executable compatibility boundary for C that is
intended to be lowered to Malbolge. It is not the repository-wide C style or
native-code policy.

## Manual validation only

Guest-C validation is deliberately opt-in. The repository does not infer guest
status from the `.c` extension, directory ownership, a magic source comment, or
an exclusion list. Native/reference C such as the VM oracle, conformance
harnesses, historical sources, host tooling, and raw interoperability inputs are
therefore never constrained merely because they are C.

From the repository root, name every candidate translation unit explicitly:

```text
python validate-malbolge-c.py path/to/program.c
```

Several explicitly selected units may be checked in one invocation:

```text
python validate-malbolge-c.py first.c second.c
```

The root validator never scans directories. Passing a directory is an error.
This makes selection a caller decision and prevents the Malbolge guest profile
from contaminating unrelated C/C++ validation.

`validate-malbolge-c.py` uses the repository-pinned LLVM 22.1.8 clang-tidy and
`tools/tidy/malbolge-clang-tidy.yaml`. Once the out-of-tree plugin exists, pass
its built shared library with `--plugin`; the durable CLI may later hide that
implementation detail.

## What the profile means

A clean final `tools/tidy` verdict means that the selected translation unit is
inside the declared deterministic guest-C profile and the compiler promises to
lower it for that target profile. This is a stronger statement than ordinary
code quality.

The final plugin partitions compatibility diagnostics into these families:

- `malbolge-language-*`: C constructs outside the admitted guest language;
- `malbolge-abi-*`: representations or operations outside the declared ABI;
- `malbolge-runtime-*`: unavailable libc, OS, threading, or host facilities;
- `malbolge-determinism-*`: undefined, implementation-defined, or host-dependent
  behavior that cannot receive deterministic guest semantics;
- `malbolge-resource-*`: statically provable target-resource requirements that
  the declared profile cannot satisfy.

The checked language is intentionally much narrower than arbitrary hosted C.
In particular, the compatibility boundary is allowed to reject concurrency,
host I/O, OS APIs, implementation-dependent behavior, and other constructs that
cannot be given the target's sequential deterministic semantics. Exact
restrictions belong to the versioned target profile and the `malbolge-*` plugin
checks rather than ad-hoc source annotations.

`malbolge-clang-tidy.yaml` is currently the executable bootstrap envelope. It
uses stock Clang diagnostics, the static analyzer, bug-prone/CERT/portability
checks, freestanding C23 parsing, and hard warnings. Stock clang-tidy cannot by
itself prove the complete C-to-Malbolge contract; recursion policy, supported
function-pointer forms, the exact guest libc, target ABI, and similar rules need
project-owned `malbolge-*` checks.

## Role of Rust tests

Rust tests are not the user-facing validator and do not decide which repository
files are guest C. They exist to develop and regress the profile itself:

```text
tests/tidy/accepted/*.c  -> tools/tidy must accept
tests/tidy/rejected/*.c  -> tools/tidy must reject with the expected family
```

As the compiler becomes available, accepted fixtures also exercise the stronger
contract:

```text
accepted C -> tools/tidy clean -> c2malbolge succeeds
```

A linter-clean supported program that the compiler later rejects is a
compiler/tooling contract regression.

## Classic Malbolge versus target evolution

The guest-C profile must not inherit accidental limitations or undefined
behavior from Ben Olmstead's historical interpreter. Historical implementation
bugs are evidence, not language authority.

The written classic Malbolge specification remains a separate normative target.
Changing its memory size, word model, or other language semantics would create
an explicit extended target profile rather than silently redefining classic
Malbolge. The compiler and `tools/tidy` may support such extensions later while
keeping classic output independently verifiable.
