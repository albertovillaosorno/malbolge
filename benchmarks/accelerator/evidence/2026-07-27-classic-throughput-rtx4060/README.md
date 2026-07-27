# Resident classic CUDA throughput evidence

This directory retains the first post-commit end-to-end throughput matrix for
resident classic CUDA execution.

## Provenance

- source commit: `20f8d5798ab637aa7c63aa049387889a9655216d`
- platform: Windows x86-64
- Python: 3.14.6, repository-pinned wrapper
- CUDA: 13.3 Update 1, repository-pinned redistributables
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`)
- samples: 15 per batch size
- batch sizes: 1, 8, 32, 128
- workload: 64 committed no-op transitions per classic VM
- `throughput.json` SHA-256: `12e130af7495c30e466d23afdb6e0412d15a231a79d17715a70a59123894a650`

## Result

The end-to-end adapter does **not** gain throughput from larger batches on this
workload. Median throughput is:

| Batch | Median ns | Median VMs/s |
| ---: | ---: | ---: |
| 1 | 34,332,800 | 29.127 |
| 8 | 284,330,500 | 28.136 |
| 32 | 1,146,059,500 | 27.922 |
| 128 | 4,612,527,500 | 27.751 |

Batch 128 is 4.72% slower than batch 1 by
median items/second. This rejects any current claim that simply increasing
resident classic batch size converts additional GPU capacity into higher
end-to-end throughput.

Every measured result is validated after the timed interval and must report
budget exhaustion after exactly 64 steps with no termination reason. The timed
region includes host batch construction, device allocation/upload, kernel launch,
download, result decoding, and cleanup through the public adapter.

## Interpretation boundary

This evidence identifies a scaling failure but does **not** identify its cause.
Host packing, allocation, transfer, kernel execution, download, decode, and
release are still aggregated. The next experiment must measure those phases
separately before any optimization is selected.
