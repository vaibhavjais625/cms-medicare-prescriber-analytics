# Data directory

- `raw/metadata/cms_data_catalog.json`: official CMS DCAT catalog captured on 2026-07-30.
- `raw/cms_filtered/*.csv`: exact source rows retained by the documented ingredient filter.
- `raw/cms_filtered/*.manifest.json`: source URL, endpoint UUID, reporting year, file, download time, scanned/retained rows, columns, suppression rule, and SHA-256.
- `processed/year=YYYY/provider_drug.parquet`: typed analytical layer.

To retrieve from scratch, activate the project environment and run `python scripts/download_data.py`. The process scans approximately 11–12 GB across three official annual files and may take substantial time depending on the connection. Interrupted `.part` files are never treated as complete; the downloader records validated byte/row checkpoints and resumes the unfinished year. No source records are synthesized or imputed.
