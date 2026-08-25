# Executable Algorithm Template

This directory is the executable half of one genuine research algorithm. The
matching academic record lives under `docs/research/algorithms/<id>/`.

Keep implementations from different languages together when they implement the
same algorithm. `experiment.toml` fixes reproducible experiment identity and
`lifecycle.toml` declares the algorithm's research lifecycle state. New research
starts as `experimental`; promotion, rejection, and retirement must satisfy the
methodology contract before changing that state. Put reproducible generated
artifacts in `out/`, which is ignored by Git. Ordinary product transformations

such as DOOM amalgamation and cleanup do not belong here.
