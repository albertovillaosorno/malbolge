# Absurdly Assured Hello World

`main.c` emits exactly `Hello, World!\n` while intentionally overengineering a
fourteen-byte payload with replicated encoded storage, SECDED correction,
residue checks, positional seals, quorum voting, bounded audit records, a toy
lattice attestation, transactional staging, cooperative events, checkpoints,
and a tiny guarded virtual machine.

The excess is deliberate and the safety/compliance language in the source is
explicit parody. The implementation is still deterministic: it uses no headers,
hosted libc calls, dynamic allocation, threads, environment state, or hidden
message construction.

```c
#include <stdio.h>

int main(
    void
    )
    {
    printf(
        "Hello, World!\n"
        );
    return 0;
}

```

That'd've'en easy.

## Native debug run

The CLI recognizes the exact function-like token `__malbolge_output_byte`
outside
comments and literals, then links
`src/interface/command-line/adapter-outbound/adapters/guest/output.c` only into
the
temporary native debug executable. On Windows that adapter switches inherited
stdout to binary mode before writing, so byte `10` remains `10` rather than text
translation to `13,10`.

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

## What this does not prove

This directory does not contain a generated `main.malbolge` yet. Native
execution
is scaffolding, not C-to-Malbolge compilation or guest-runtime evidence. A
future
compiler must lower `__malbolge_output_byte` to executable Malbolge semantics;
the host adapter must never enter or satisfy that artifact.
