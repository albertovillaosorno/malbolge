# Command Line

## Purpose

The user-facing Malbolge command-line interface.

## Ownership

This boundary is owned by `function:command-line`.

## Prohibitions

It must not bypass another function or architectural kind boundary.

## Navigation

- [`contract/reference.md`](contract/reference.md): detailed
  pre-migration reference.
- `adapter-outbound/`: governed `adapter-outbound` parts.
- `application/`: governed `application` parts.
- `composition/`: governed `composition` parts.
- `contract/`: governed `contract` parts.

## Exact guest byte input

`malbolge program.malbolge` retains its existing deterministic empty-input
behavior: each `/` instruction observes the selected profile's EOF value.
`malbolge program.malbolge --input-stdin` explicitly reads at most 256 raw
bytes from standard input before loading the VM, then passes the complete byte
vector to the normative classic or capsule-selected profile VM. NUL, `0xA8`,
`0xFF`, and any other byte are data, not delimiters; after consumption the
profile's defined EOF value applies. This mode is bounded to 257 read bytes
for limit admission, then rejects overlong inputs before executing any guest
instruction. The input stream must close to signal EOF. The flag is not
forwarded to native C debug runs, which retain their existing argument model.

Example (the source must itself read and output bytes):

```sh
printf '\000A' | malbolge program.malbolge --input-stdin
```

The CLI does not authenticate the origin of supplied bytes or enforce a whole
process resource budget. It does not change interpreter semantics, restore
program state between runs, or claim that an arbitrary program reads stdin.
