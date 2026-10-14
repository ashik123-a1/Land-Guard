# LandGuard Data Directory

This directory stores dataset manifests, metadata, and representative samples.

## Structure
- `manifests/`: Dataset release manifests containing SHA-256 checksum registers and file counts.
  - `dataset_manifest.json`
- `samples/`: Lightweight representative sample JSON files checked into Git for quick inspection.
  - `sample_records.json`
- `full/` (Git-ignored): Full canonical dataset output containing 100,000 structured records and rendered images. Generated via `python scripts/generate_all.py`.
- `pilot/` (Git-ignored): Small pilot dataset used for fast initial testing. Generated via `python scripts/generate_pilot.py`.
