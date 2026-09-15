# Verified Hello World stress fixture

`hello_world_stress.c` emits exactly `Hello, World!\n`, but only after a set of
self-checks exercises the admitted freestanding C surface. The program has no
headers, hosted libc calls, dynamic allocation, threads, environment state, or
host-side message construction.

The complexity is intentional, but none of the retained layers is decorative.
For every output byte, five encoded replicas are present:

- one canonical replica;
- one replica with a correctable single-bit error in the low SECDED codeword;
- one replica with a correctable single-bit error in the high SECDED codeword;
- one internally valid replica containing a deliberately different byte; and
- one replica with a detected uncorrectable two-bit SECDED error.

A successful decode therefore requires SECDED correction, rejection of the
uncorrectable replica, arithmetic residue and positional-seal validation, and a
three-node quorum. The program validates the expected correction, invalid-vote,
and dissent counts so those paths must actually execute.

The complete message is decoded twice before any byte is emitted. Both passes
must agree and must produce the expected message digest. Two additional checked
kernels exercise long integer dependency chains, multiplication, division,
modulo, bit operations, nested loops, and modular matrix multiplication. Their
results are compared with fixed expected values; failure produces no output.

## Native debug run

The CLI recognizes the exact function-like token `__malbolge_output_byte`
outside comments and literals, then links
`src/interface/command-line/adapter-outbound/adapters/guest/output.c` only into
the temporary native debug executable. On Windows that adapter switches
inherited stdout to binary mode before writing, so byte `10` remains `10`
rather than text translation to `13,10`.

Expected bytes:

```text
72,101,108,108,111,44,32,87,111,114,108,100,33,10
```

## What this proves

- The source passes the explicit guest-C compatibility validator.
- It compiles as C23 freestanding source with no hosted includes.
- Its freestanding object has one unresolved symbol:
  `__malbolge_output_byte`.
- The native CLI debug path preserves the exact output bytes.
- The native run executes the same checked control flow expected of a future
  C-to-Malbolge lowering.

## What this does not prove

This directory does not contain a generated `hello_world_stress.malbolge` yet.
Native execution is scaffolding, not C-to-Malbolge compilation or guest-runtime
evidence. A future compiler must lower `__malbolge_output_byte` to executable
Malbolge semantics; the host adapter must never enter or satisfy that artifact.
