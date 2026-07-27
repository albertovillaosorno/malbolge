# Tiered execution fixtures

`region-effect-v1.hex` is an independently rendered byte-exact vector for the
portable effect-IR v1 encoding exercised by `tests/tiered_execution.rs`. The
fixture is textual hexadecimal so repository hygiene can inspect it, while the
test reconstructs the exact bytes before comparing them to Rust canonicalization.
