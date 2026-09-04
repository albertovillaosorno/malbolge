# CRAZY lookup address fanout

This structural evidence applies the five-trit CUDA lookup-table address formula
to the existing `classic-crazy-target-full-domain-multiposition-v1` search
workload. It preserves the canonical ordinary order of all 59,049 candidates and
the exact production-selected order of the 1,024 projected preimage positions.
No CUDA execution, timing, profiler, or hardware counter is part of this record.

CUDA Best Practices Guide 13.3 states that constant-memory requests to distinct
addresses within a warp are serialized and that the cost scales with the number
of unique addresses. `fanout.json` therefore retains every per-warp
unique-address count for the low and middle five-trit lookup, using 32 active
lanes per full warp. These counts model serialization pressure only; they are not
constant-cache hit or miss measurements.

For ordinary full-domain order, the low lookup requests 32 unique addresses in
1,845 of 1,846 warps; the final nine-lane warp requests nine. The middle lookup
requests one unique address in 1,611 warps and two in 235. The exact 1,024-item
projection has 32 unique low addresses and one unique middle address in each of
its 32 warps. Projection therefore preserves maximum low-lookup fanout while
making the middle lookup uniform.

The current CUDA candidate-search CRAZY kernel remains tritwise. This record is
prospective lookup-layout evidence and does not establish hardware cache traffic,
a lookup candidate-search speedup, or a production route-selection decision.
`source-commit.txt` identifies the clean generator commit.
