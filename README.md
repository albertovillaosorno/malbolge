# Malbolge

Malbolge is an experimental compiler, execution, verification, and research
platform built around the 1998 Malbolge machine.

The project treats C as the primary human-authored application language and
`.malbolge` as the generated target. It preserves well-defined historical
behavior through an untouched Ben Olmstead interpreter oracle while exploring
modern virtual machines, deterministic C lowering, verification,
superoptimization, accelerator adapters, native execution, and self-hosting.

This repository is also a reproducible compiler-algorithm laboratory. Research
algorithms are measured against deterministic semantic oracles and scalable
challenge families rather than accepted on performance claims alone.

## Documentation

Repository knowledge is split into four authority families:

- `docs/technical/` - repository-owned architecture, contracts,
  specifications, and implementation-facing behavior;
- `docs/research/` - hypotheses, experiments, algorithms, methodology, and
  publication artifacts;
- `docs/legal/` - dated legal/source-use research and repository boundaries;
- `docs/bibliography/` - non-governing external evidence and provenance.

Each family owns its own `adr/` directory. A global `docs/adr/` is intentionally
not used.

`docs/cspell/` is editorial tooling support and remains under `docs/` without
becoming a fifth authority family.

See [`ROADMAP.md`](ROADMAP.md) for unfinished work and [`todo/roadmap/`](todo/roadmap/)
for typed execution records.

## Historical interpreter

`tools/malbolge/main.c` is Ben Olmstead's original 1998 interpreter retained as
an immutable compatibility oracle. Its own source notice places that interpreter
in the public domain. The repository MIT license does not relicense that file.

## License

Repository-authored material is licensed under the MIT License unless a file or
record states a different applicable boundary. See [`LICENSE`](LICENSE).
