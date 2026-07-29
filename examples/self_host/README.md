# Self-hosting examples

`examples/self_host/` holds source fixtures and reserved output locations for the
long-term self-hosting conformance goal.

- `hello-world/` is a deliberately absurd freestanding C example. Its native CLI
  execution proves only debug scaffolding and exact byte preservation; no
  generated Malbolge artifact is checked in.
- `doom/` reserves the future canonical location for `doom.malbolge`. Generated
  products remain local and ignored.

A checked-in source example may exercise the admitted deterministic C surface,
but native execution never counts as C-to-Malbolge lowering, guest-runtime,
self-hosting, or conformance evidence. Generated `.malbolge` products belong here
only after the compiler produces them and independent verification admits them.
