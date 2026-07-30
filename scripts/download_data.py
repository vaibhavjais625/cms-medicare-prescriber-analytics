"""Stream official CMS bulk CSVs and preserve an exact, reproducibly filtered raw extract.

The full provider-by-drug files are roughly 3–4 GB per year. This script scans each
official CMS file without storing the full file and writes every source row whose
generic name matches the documented diabetes ingredient map, excluding the explicitly
documented weight-management brands. No sampling, imputation, or source-row mutation occurs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from urllib3.exceptions import ProtocolError

from common import DATASETS, EXPECTED_COLUMNS, RAW_DIR, YEARS, load_excluded_brands, load_mapping, normalize_text, write_json


def _matching_terms() -> tuple[str, ...]:
    return tuple(sorted({str(row["match_term"]).lower() for row in load_mapping()}))


def _is_in_scope(brand: str, generic: str, pattern: re.Pattern[str], exclusions: set[str]) -> bool:
    return pattern.search(generic) is not None and normalize_text(brand) not in exclusions


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download_year(year: int, force: bool = False) -> dict[str, object]:
    source = DATASETS[year]
    output_dir = RAW_DIR / "cms_filtered"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"cms_partd_provider_drug_diabetes_{year}.csv"
    manifest_path = output_dir / f"cms_partd_provider_drug_diabetes_{year}.manifest.json"
    if output_path.exists() and manifest_path.exists() and not force:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        print(f"{year}: existing verified extract found ({manifest['filtered_row_count']:,} rows); skipping")
        return manifest

    part_path = output_path.with_suffix(".csv.part")
    state_path = output_path.with_suffix(".csv.part.state.json")
    if force:
        for path in (output_path, manifest_path, part_path, state_path):
            path.unlink(missing_ok=True)
    terms = _matching_terms()
    ingredient_pattern = re.compile("|".join(re.escape(term) for term in terms), re.IGNORECASE)
    exclusions = load_excluded_brands()
    scanned = kept = position = 0
    header: list[str] | None = None
    if state_path.exists() and part_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        scanned, kept, position = int(state["scanned"]), int(state["kept"]), int(state["source_byte_position"])
        header = state["header"]
        with part_path.open("r+b") as partial:
            partial.truncate(int(state["output_byte_position"]))
        print(f"{year}: resuming at source byte {position:,}; scanned {scanned:,}, kept {kept:,}", flush=True)
    elif part_path.exists():
        part_path.unlink()
    started = time.time()
    idx = {name: EXPECTED_COLUMNS.index(name) for name in EXPECTED_COLUMNS}
    total_source_bytes: int | None = None
    retries = 0
    try:
        with part_path.open("a" if position else "w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh, lineterminator="\n")
            def process_complete_line(line: bytes) -> None:
                nonlocal header, scanned, kept, position
                decoded = line.decode("utf-8-sig" if position == 0 else "utf-8")
                row = next(csv.reader([decoded]))
                if position == 0:
                    header = row
                    if header != EXPECTED_COLUMNS:
                        raise ValueError(f"{year}: unexpected CMS schema. Expected {EXPECTED_COLUMNS}; received {header}")
                    writer.writerow(header)
                else:
                    if len(row) != len(EXPECTED_COLUMNS):
                        raise ValueError(f"{year}: malformed source row {scanned + 1} has {len(row)} columns")
                    scanned += 1
                    if _is_in_scope(row[idx["Brnd_Name"]], row[idx["Gnrc_Name"]], ingredient_pattern, exclusions):
                        writer.writerow(row)
                        kept += 1
                position += len(line)
                if scanned and scanned % 100_000 == 0:
                    fh.flush()
                    write_json(state_path, {"scanned": scanned, "kept": kept, "source_byte_position": position, "output_byte_position": fh.buffer.tell(), "header": header})
                if scanned and scanned % 1_000_000 == 0:
                    elapsed = max(time.time() - started, 1)
                    print(f"{year}: scanned {scanned:,}, kept {kept:,} ({scanned/elapsed:,.0f} rows/sec)", flush=True)

            while total_source_bytes is None or position < total_source_bytes:
                request_headers = {
                    "User-Agent": "RxMarketIQ-portfolio-project/1.0 (CMS public data research)",
                    "Accept-Encoding": "identity",
                }
                if position:
                    request_headers["Range"] = f"bytes={position}-"
                try:
                    response = requests.get(source["url"], stream=True, timeout=(30, 300), headers=request_headers)
                    response.raise_for_status()
                    if position and response.status_code != 206:
                        raise RuntimeError(f"{year}: server did not honor byte-range resume (HTTP {response.status_code})")
                    content_range = response.headers.get("Content-Range", "")
                    if "/" in content_range:
                        total_source_bytes = int(content_range.rsplit("/", 1)[1])
                    elif response.headers.get("Content-Length"):
                        total_source_bytes = position + int(response.headers["Content-Length"])
                    raw = response.raw
                    raw.decode_content = False
                    pending = b""
                    while True:
                        chunk = raw.read(4 * 1024 * 1024)
                        if not chunk:
                            break
                        pending += chunk
                        boundary = pending.rfind(b"\n")
                        if boundary < 0:
                            continue
                        complete, pending = pending[: boundary + 1], pending[boundary + 1 :]
                        for line in complete.splitlines(keepends=True):
                            process_complete_line(line)
                    if pending:
                        if total_source_bytes and position + len(pending) < total_source_bytes:
                            raise ProtocolError("connection ended inside a CSV record")
                        process_complete_line(pending)
                    response.close()
                    retries = 0
                    if total_source_bytes is not None and position >= total_source_bytes:
                        break
                    raise ProtocolError("connection closed before advertised source length")
                except (ProtocolError, requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout, requests.exceptions.ChunkedEncodingError) as exc:
                    retries += 1
                    fh.flush()
                    write_json(state_path, {"scanned": scanned, "kept": kept, "source_byte_position": position, "output_byte_position": fh.buffer.tell(), "header": header})
                    if retries > 20:
                        raise RuntimeError(f"{year}: exceeded 20 resumable network retries") from exc
                    wait = min(30, 2 * retries)
                    print(f"{year}: network interruption; resuming from byte {position:,} in {wait}s (retry {retries}/20)", flush=True)
                    time.sleep(wait)
        os.replace(part_path, output_path)
        state_path.unlink(missing_ok=True)
    except Exception:
        print(f"{year}: incomplete extract retained with checkpoint; rerun to resume", flush=True)
        raise

    manifest = {
        "dataset": "CMS Medicare Part D Prescribers - by Provider and Drug",
        "reporting_year": year,
        "source_page": "https://data.cms.gov/provider-summary-by-type-of-service/medicare-part-d-prescribers/medicare-part-d-prescribers-by-provider-and-drug",
        "source_file_url": source["url"],
        "source_file_name": source["file_name"],
        "api_endpoint": f"https://data.cms.gov/data-api/v1/dataset/{source['uuid']}/data",
        "dataset_version_uuid": source["uuid"],
        "source_modified_date": source["modified"],
        "download_completed_utc": datetime.now(timezone.utc).isoformat(),
        "retrieval_method": "streamed official CMS bulk CSV; deterministic ingredient filter; no sampling",
        "filter_terms": list(terms),
        "excluded_brands": sorted(exclusions),
        "source_rows_scanned": scanned,
        "source_bytes_scanned": position,
        "filtered_row_count": kept,
        "column_count": len(header),
        "columns": header,
        "local_file": str(output_path.relative_to(output_path.parents[3])),
        "local_sha256": sha256_file(output_path),
        "suppression_rule": "Provider-drug records with Tot_Clms < 11 are omitted by CMS; Tot_Benes < 11 is blank.",
    }
    write_json(manifest_path, manifest)
    print(f"{year}: complete; retained {kept:,} of {scanned:,} source rows")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", nargs="+", type=int, default=list(YEARS), choices=list(YEARS))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    manifests = [download_year(year, force=args.force) for year in args.years]
    write_json(RAW_DIR / "cms_filtered" / "download_manifest.json", manifests)
    return 0


if __name__ == "__main__":
    sys.exit(main())
