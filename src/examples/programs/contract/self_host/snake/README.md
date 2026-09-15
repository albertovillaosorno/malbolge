# Classic-budget Snake

`snake_classic.c` is a deliberately small playable program intended to stress
real guest behavior without depending on the DOOM ABI, libc, allocation,
clocks, files, threads, or host services. The game owns its complete board,
snake, food, collision, scoring, rendering, and command state.

The only external declarations are compiler intrinsics for the two fundamental
Malbolge I/O operations:

- `__malbolge_input_word()` must lower directly to classic `/` input and returns
  the classic EOF word `59048` when input is exhausted;
- `__malbolge_output_byte()` must lower directly to classic `<` output modulo
  256.

Those declarations are not a hosted runtime ABI. The CLI's C adapters exist only
to make native debug runs possible before C-to-Malbolge lowering exists. They
must never be linked into or called by a generated `.malbolge` artifact.

## Linux-only playable contract

This example is supported as an interactive game only on Linux ANSI-compatible
terminals. It emits ANSI cursor-home and clear-screen bytes itself; it does not
call `termios`, `ioctl`, `stty`, or any terminal library. Input intentionally
uses ordinary canonical stdin for compatibility with the historical byte-input
model, so enter a command and press Enter:

```text
w + Enter    move up
s + Enter    move down
a + Enter    move left
d + Enter    move right
q + Enter    quit
```

The board is 12 by 8, the snake is bounded to 24 cells, and food placement uses
a deterministic recurrence rather than `rand()`. Moving, growing, collision
checking, food placement, score formatting, and rendering are all implemented
inside the guest source.

For native debugging from the repository root:

```text
malbolge src/examples/programs/contract/self_host/snake/snake_classic.c
```

A future classic compiler artifact should be runnable through the same byte I/O
semantics as a normal `.malbolge` program. No generated artifact or 59,049-word
fit claim is made yet; that must be measured after classic lowering exists.

## Deterministic parity harness

`snake_parity.c` is a second freestanding guest program that includes the game
implementation and checks its internal semantics without requiring an
interactive terminal. It covers exact initialization and render bytes, opposite
turn rejection, deterministic growth and food placement, all four wall
collisions, self-collision, and the legal move into a vacating tail cell.

```text
malbolge src/examples/programs/contract/self_host/snake/snake_parity.c
```

The exact transcript is:

```text
SNAKE-PARITY-v1
OK
```

The same parity source is intended to be compiled to a future `.malbolge`
artifact. Native C and generated Malbolge must then produce byte-identical
transcripts; no host-side Snake model is needed for that comparison.
