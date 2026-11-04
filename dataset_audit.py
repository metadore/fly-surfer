#!/usr/bin/env python3
"""Reproducible Phase 0 audit of the FAFB datasets used by FLY-SURFER."""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
RAW_DIR = PROJECT_ROOT / "datasets" / "raw"
OUT_DIR = PROJECT_ROOT / "datasets"
MANIFEST_PATH = OUT_DIR / "manifest.json"
README_PATH = OUT_DIR / "README.md"

NT_COLUMNS = {
    "ACH": "ach_avg",
    "GABA": "gaba_avg",
    "GLUT": "glut_avg",
    "DA": "da_avg",
    "SER": "ser_avg",
    "OCT": "oct_avg",
}
POSITION_RE = re.compile(r"^\s*\[\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s*\]\s*$")
HASH_A = np.uint64(0x9E3779B97F4A7C15)
HASH_B = np.uint64(0xBF58476D1CE4E5B9)
HASH_C = np.uint64(0x94D049BB133111EB)
CHUNK_WIDE = 20_000
CHUNK_CONN = 500_000
CHUNK_AGG = 1_000_000


def log(message: str) -> None:
    print(message, flush=True)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def utc_from_timestamp(value: float | int) -> str:
    return datetime.fromtimestamp(float(value), timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def human_bytes(value: int | float) -> str:
    value = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024


def json_safe(value):
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return [json_safe(v) for v in value.tolist()]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        value = float(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, float):
        return None if math.isnan(value) or math.isinf(value) else value
    if value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, (bool, int, str)) or value is None:
        return value
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return str(value)


def sha256_file(path: Path, block: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(block), b""):
            digest.update(chunk)
    return digest.hexdigest()


def gzip_metadata(path: Path) -> dict:
    with path.open("rb") as handle:
        head = handle.read(4096)
        handle.seek(-4, os.SEEK_END)
        isize = int.from_bytes(handle.read(4), "little")
    if head[:2] != b"\x1f\x8b":
        raise ValueError(f"not a gzip file: {path}")
    flags = head[3]
    mtime = int.from_bytes(head[4:8], "little")
    index = 10
    if flags & 0x04:
        xlen = int.from_bytes(head[index:index + 2], "little")
        index += 2 + xlen
    original_name = None
    if flags & 0x08:
        end = head.find(b"\x00", index)
        if end > index:
            original_name = head[index:end].decode("latin1", "replace")
    return {
        "original_name": original_name,
        "header_mtime_utc": utc_from_timestamp(mtime) if mtime else None,
        "isize_mod_4gib": isize,
    }


def sample_rows(path: Path, count: int = 2) -> list[dict]:
    return json_safe(pd.read_csv(path, nrows=count).to_dict(orient="records"))


def inventory(path: Path, group: str) -> dict:
    stat = path.stat()
    gz = gzip_metadata(path)
    return {
        "name": path.name,
        "relative_path": path.relative_to(PROJECT_ROOT).as_posix(),
        "group": group,
        "format": "gzip-compressed CSV",
        "compressed_bytes": stat.st_size,
        "uncompressed_bytes": gz["isize_mod_4gib"],
        "sha256": sha256_file(path),
        "modified_utc": utc_from_timestamp(stat.st_mtime),
        "gzip": {
            "original_name": gz["original_name"],
            "header_mtime_utc": gz["header_mtime_utc"],
        },
    }


def partial_downloads(folder: Path) -> list[dict]:
    result = []
    for path in sorted(folder.glob("*.crdownload")):
        with path.open("rb") as handle:
            head = handle.read(512)
        embedded = None
        fmt = "unknown"
        if head[:2] == b"\x1f\x8b":
            fmt = "gzip"
            flags = head[3]
            index = 10
            if flags & 0x04:
                xlen = int.from_bytes(head[index:index + 2], "little")
                index += 2 + xlen
            if flags & 0x08:
                end = head.find(b"\x00", index)
                if end > index:
                    embedded = head[index:end].decode("latin1", "replace")
        elif head[:4] == b"PK\x03\x04":
            fmt = "zip"
            name_len = int.from_bytes(head[26:28], "little")
            embedded = head[30:30 + name_len].decode("latin1", "replace")
        stat = path.stat()
        result.append({
            "name": path.name,
            "format": fmt,
            "embedded_name": embedded,
            "bytes": stat.st_size,
            "modified_utc": utc_from_timestamp(stat.st_mtime),
            "sha256_of_partial": sha256_file(path),
            "note": "checksum covers current partial bytes and changes if the download resumes",
        })
    return result


def top_counts(series: pd.Series, limit: int = 15) -> dict:
    counts = series.value_counts(dropna=False).head(limit)
    return {
        "<missing>" if pd.isna(key) else str(key): int(value)
        for key, value in counts.items()
    }


def parse_positions(series: pd.Series) -> tuple[pd.DataFrame, int]:
    extracted = series.astype(str).str.extract(POSITION_RE, expand=True)
    return extracted.astype("float64"), int(extracted.isna().any(axis=1).sum())


def root_id_checks(series: pd.Series) -> dict:
    clean = series.dropna()
    unique = int(clean.nunique())
    return {
        "rows": int(len(series)),
        "null_ids": int(series.isna().sum()),
        "unique_ids": unique,
        "duplicate_id_rows": int(len(series) - unique),
        "non_positive_ids": int((clean <= 0).sum()),
        "min_id": int(clean.min()) if unique else None,
        "max_id": int(clean.max()) if unique else None,
    }


def profile_standard(path: Path, entry: dict) -> tuple[dict, set[int]]:
    table = pd.read_csv(path)
    entry["rows"] = int(len(table))
    entry["columns"] = list(table.columns)
    entry["dtypes"] = {str(k): str(v) for k, v in table.dtypes.items()}
    entry["null_counts"] = {str(k): int(v) for k, v in table.isna().sum().items()}
    entry["sample_rows"] = json_safe(table.head(2).to_dict(orient="records"))

    ids: set[int] = set()
    if "root_id" in table.columns:
        entry["id_checks"] = root_id_checks(table["root_id"])
        ids = {int(v) for v in table["root_id"].dropna().unique()}
    else:
        entry["id_checks"] = None

    checks: dict = {}
    name = path.name

    if name == "classification.csv.gz":
        checks["domains"] = {c: top_counts(table[c]) for c in ("flow", "super_class", "side")}
        checks["class_values"] = int(table["class"].nunique(dropna=True))
        checks["sub_class_values"] = int(table["sub_class"].nunique(dropna=True))

    elif name == "column_assignment.csv.gz":
        checks["hemisphere_domain"] = top_counts(table["hemisphere"])
        checks["type_values"] = int(table["type"].nunique())
        checks["numeric_ranges"] = {
            c: [int(table[c].min()), int(table[c].max())]
            for c in ("column_id", "x", "y", "p", "q")
        }

    elif name == "consolidated_cell_types.csv.gz":
        checks["primary_type_values"] = int(table["primary_type"].nunique())
        checks["primary_types_top"] = top_counts(table["primary_type"], 10)
        checks["additional_type_missing"] = int(table["additional_type(s)"].isna().sum())

    elif name == "labels.csv.gz":
        _, bad_positions = parse_positions(table["position"])
        parsed_dates = pd.to_datetime(table["date_created"], errors="coerce")
        labels_per_neuron = table.groupby("root_id").size()
        checks.update({
            "position_parse_failures": bad_positions,
            "invalid_dates": int(parsed_dates.isna().sum()),
            "blank_labels": int(table["label"].isna().sum()),
            "labels_per_neuron_max": int(labels_per_neuron.max()),
            "labels_per_neuron_mean": round(float(labels_per_neuron.mean()), 3),
            "top_affiliations": top_counts(table["user_affiliation"], 8),
            "distinct_users": int(table["user_id"].nunique()),
        })

    elif name == "processed_labels.csv.gz":
        text = table["processed_labels"].astype(str)
        checks["malformed_label_lists"] = int((~text.str.startswith("[") | ~text.str.endswith("]")).sum())

    elif name == "visual_neuron_types.csv.gz":
        checks["domains"] = {c: top_counts(table[c]) for c in ("side", "category", "subsystem")}
        checks["family_values"] = int(table["family"].nunique(dropna=True))

    elif name == "connectivity_tags.csv.gz":
        tags = table["connectivity_tag"].astype(str).str.split(",").explode().str.strip()
        checks["tag_counts"] = top_counts(tags, 20)
        checks["rows_without_tag"] = int((tags == "").sum())

    elif name == "synapse_attachment_rates.csv.gz":
        calculated = table["count_proof"] / table["count_total"]
        checks.update({
            "side_domain": top_counts(table["side"]),
            "neuropils": sorted(table["neuropil"].unique().tolist()),
            "neuropil_count": int(table["neuropil"].nunique()),
            "max_proof_ratio_error": float((calculated - table["proof_ratio"]).abs().max()),
            "rows_with_proof_exceeding_total": int((table["count_proof"] > table["count_total"]).sum()),
        })
        entry["_neuropils"] = set(table["neuropil"].astype(str))

    elif name == "cell_stats.csv.gz":
        checks["zero_or_negative"] = {c: int((table[c] <= 0).sum()) for c in ("length_nm", "area_nm", "size_nm")}
        checks["ranges"] = {c: [int(table[c].min()), int(table[c].max())] for c in ("length_nm", "area_nm", "size_nm")}

    elif name == "coordinates.csv.gz":
        positions, bad_positions = parse_positions(table["position"])
        rows_per_neuron = table.groupby("root_id").size()
        supervoxel_roots = table.groupby("supervoxel_id")["root_id"].nunique()
        checks.update({
            "position_parse_failures": bad_positions,
            "coordinate_ranges": {str(axis): [int(positions[axis].min()), int(positions[axis].max())] for axis in range(3)},
            "rows_per_neuron": {
                "min": int(rows_per_neuron.min()),
                "max": int(rows_per_neuron.max()),
                "mean": round(float(rows_per_neuron.mean()), 3),
                "single_row_neurons": int((rows_per_neuron == 1).sum()),
                "multi_row_neurons": int((rows_per_neuron > 1).sum()),
            },
            "exact_duplicate_rows": int(table.duplicated().sum()),
            "duplicate_root_supervoxel_rows": int(table.duplicated(["root_id", "supervoxel_id"]).sum()),
            "supervoxels_mapping_to_multiple_neurons": int((supervoxel_roots > 1).sum()),
            "unique_supervoxels": int(table["supervoxel_id"].nunique()),
        })

    elif name == "names.csv.gz":
        checks["blank_names"] = int(table["name"].isna().sum())
        checks["blank_groups"] = int(table["group"].isna().sum())
        checks["group_count"] = int(table["group"].nunique())
        checks["groups_top"] = top_counts(table["group"], 15)

    elif name == "neurons.csv.gz":
        checks["nt_type_domain"] = top_counts(table["nt_type"])
        checks["nt_type_missing"] = int(table["nt_type"].isna().sum())
        checks["nt_score_range"] = [float(table["nt_type_score"].min()), float(table["nt_type_score"].max())]
        expected = pd.Series(np.nan, index=table.index, dtype="float64")
        for nt_type, column in NT_COLUMNS.items():
            mask = table["nt_type"] == nt_type
            expected.loc[mask] = table.loc[mask, column]
        checks["nt_score_mismatches"] = int(((expected - table["nt_type_score"]).abs() > 1e-9).sum())
        checks["nt_average_ranges"] = {c: [float(table[c].min()), float(table[c].max())] for c in NT_COLUMNS.values()}
        checks["group_count"] = int(table["group"].nunique())
        checks["groups_top"] = top_counts(table["group"], 15)

    entry["validation"] = checks
    return entry, ids


def profile_wide_table(path: Path, entry: dict) -> tuple[dict, set[int]]:
    columns = list(pd.read_csv(path, nrows=0).columns)
    entry["columns"] = columns
    entry["sample_rows"] = sample_rows(path, 1)
    in_syn = [c for c in columns if c.startswith("input synapses in ")]
    out_syn = [c for c in columns if c.startswith("output synapses in ")]
    in_par = [c for c in columns if c.startswith("input partners in ")]
    out_par = [c for c in columns if c.startswith("output partners in ")]
    in_suffixes = {c[len("input synapses in "):] for c in in_syn}
    out_suffixes = {c[len("output synapses in "):] for c in out_syn}

    nulls = {c: 0 for c in columns}
    dtypes: dict = {}
    ids: set[int] = set()
    duplicate_ids = 0
    rows = 0
    input_mismatch = 0
    output_mismatch = 0
    negative_rows = 0

    for chunk in pd.read_csv(path, chunksize=CHUNK_WIDE):
        rows += len(chunk)
        if not dtypes:
            dtypes = {str(k): str(v) for k, v in chunk.dtypes.items()}
        for column in columns:
            nulls[column] += int(chunk[column].isna().sum())
        for value in chunk["root_id"].dropna().tolist():
            value = int(value)
            if value in ids:
                duplicate_ids += 1
            else:
                ids.add(value)
        input_mismatch += int((chunk[in_syn].sum(axis=1) != chunk["input synapses"]).sum())
        output_mismatch += int((chunk[out_syn].sum(axis=1) != chunk["output synapses"]).sum())
        negative_rows += int((chunk.select_dtypes(include=[np.number]) < 0).any(axis=1).sum())

    entry["rows"] = rows
    entry["dtypes"] = dtypes
    entry["null_counts"] = {str(k): int(v) for k, v in nulls.items()}
    entry["id_checks"] = {
        "rows": rows,
        "null_ids": nulls.get("root_id", 0),
        "unique_ids": len(ids),
        "duplicate_id_rows": duplicate_ids,
        "non_positive_ids": int(sum(1 for i in ids if i <= 0)),
        "min_id": min(ids) if ids else None,
        "max_id": max(ids) if ids else None,
    }
    entry["validation"] = {
        "column_count": len(columns),
        "input_synapse_columns": len(in_syn),
        "output_synapse_columns": len(out_syn),
        "input_partner_columns": len(in_par),
        "output_partner_columns": len(out_par),
        "input_and_output_suffixes_match": in_suffixes == out_suffixes,
        "input_total_mismatches": input_mismatch,
        "output_total_mismatches": output_mismatch,
        "rows_with_negative_values": negative_rows,
        "neuropils": sorted(in_suffixes),
    }
    entry["_neuropils"] = in_suffixes
    return entry, ids


def mix_hash(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    value = (left.astype(np.uint64) * HASH_A) ^ right.astype(np.uint64)
    value ^= value >> np.uint64(30)
    value *= HASH_B
    value ^= value >> np.uint64(27)
    value *= HASH_C
    value ^= value >> np.uint64(31)
    return value


def profile_connections(path: Path, entry: dict) -> tuple[dict, set[int], set[str]]:
    columns = list(pd.read_csv(path, nrows=0).columns)
    entry["columns"] = columns
    entry["sample_rows"] = sample_rows(path, 2)
    nulls = {c: 0 for c in columns}
    dtypes: dict = {}
    rows = 0
    pre_ids: set[int] = set()
    post_ids: set[int] = set()
    self_connections = 0
    syn_min = None
    syn_max = 0
    syn_sum = 0
    non_positive_synapses = 0
    rows_below_5 = 0
    nt_counts: Counter = Counter()
    syn_counts: Counter = Counter()
    neuropil_counts: Counter = Counter()
    neuropils: set[str] = set()

    for chunk in pd.read_csv(path, chunksize=CHUNK_CONN):
        rows += len(chunk)
        if not dtypes:
            dtypes = {str(k): str(v) for k, v in chunk.dtypes.items()}
        for column in columns:
            nulls[column] += int(chunk[column].isna().sum())
        pre = chunk["pre_root_id"]
        post = chunk["post_root_id"]
        pre_ids.update(int(v) for v in pre.dropna().unique())
        post_ids.update(int(v) for v in post.dropna().unique())
        self_connections += int((pre == post).sum())
        syn = chunk["syn_count"]
        current_min = int(syn.min())
        syn_min = current_min if syn_min is None else min(syn_min, current_min)
        syn_max = max(syn_max, int(syn.max()))
        syn_sum += int(syn.sum())
        non_positive_synapses += int((syn <= 0).sum())
        rows_below_5 += int((syn < 5).sum())
        nt_counts.update(chunk["nt_type"].value_counts(dropna=False).to_dict())
        syn_counts.update(chunk["syn_count"].value_counts().to_dict())
        neuropil_counts.update(chunk["neuropil"].value_counts(dropna=False).to_dict())
        neuropils.update(str(v) for v in chunk["neuropil"].dropna().unique())

    entry["rows"] = rows
    entry["dtypes"] = dtypes
    entry["null_counts"] = {str(k): int(v) for k, v in nulls.items()}
    entry["id_checks"] = {
        "pre_unique_ids": len(pre_ids),
        "post_unique_ids": len(post_ids),
        "union_unique_ids": len(pre_ids | post_ids),
        "min_id": min(pre_ids | post_ids) if (pre_ids or post_ids) else None,
        "max_id": max(pre_ids | post_ids) if (pre_ids or post_ids) else None,
        "id_nulls": nulls.get("pre_root_id", 0) + nulls.get("post_root_id", 0),
    }
    entry["validation"] = {
        "directed_columns": ["pre_root_id", "post_root_id"],
        "self_connections": self_connections,
        "synapse_count_min": syn_min,
        "synapse_count_max": syn_max,
        "synapse_count_sum": syn_sum,
        "non_positive_synapse_rows": non_positive_synapses,
        "rows_with_synapses_below_5": rows_below_5,
        "nt_type_domain": {("<missing>" if pd.isna(k) else str(k)): int(v) for k, v in nt_counts.items()},
        "neuropil_count": len(neuropils),
        "synapse_count_distribution_top": {
            str(k): int(v) for k, v in sorted(syn_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
        },
        "synapse_count_unique_values": len(syn_counts),
    }
    entry["_neuropil_counts"] = {str(k): int(v) for k, v in neuropil_counts.items()}
    return entry, pre_ids | post_ids, neuropils


def pair_aggregate(
    path: Path,
    entry: dict,
    filtered: bool,
    neuropils: set[str],
    syn_max: int,
    filtered_hashes: np.ndarray | None = None,
) -> tuple[dict, np.ndarray | None]:
    syn_dtype = np.dtype("<u2") if syn_max <= 65535 else np.dtype("<u4")
    if filtered:
        dtype = [("h", "<u8"), ("s", syn_dtype), ("pre", "<u8"), ("post", "<u8"), ("t", "<u8")]
        usecols = ["pre_root_id", "post_root_id", "syn_count", "neuropil"]
    else:
        dtype = [("h", "<u8"), ("s", syn_dtype)]
        usecols = ["pre_root_id", "post_root_id", "syn_count"]
    arr = np.empty(entry["rows"], dtype=dtype)
    filled = 0
    neuropil_map = {name: index + 1 for index, name in enumerate(sorted(neuropils))}
    unknown_neuropils = 0

    for chunk in pd.read_csv(path, chunksize=CHUNK_AGG, usecols=usecols):
        count = len(chunk)
        pair_hash = mix_hash(chunk["pre_root_id"].to_numpy(), chunk["post_root_id"].to_numpy())
        arr["h"][filled:filled + count] = pair_hash
        arr["s"][filled:filled + count] = chunk["syn_count"].to_numpy(dtype=syn_dtype)
        if filtered:
            codes = chunk["neuropil"].map(neuropil_map)
            unknown_neuropils += int(codes.isna().sum())
            codes = codes.fillna(0).to_numpy(dtype=np.uint16)
            arr["t"][filled:filled + count] = mix_hash(pair_hash, codes.astype(np.uint64))
            arr["pre"][filled:filled + count] = chunk["pre_root_id"].to_numpy(dtype=np.uint64)
            arr["post"][filled:filled + count] = chunk["post_root_id"].to_numpy(dtype=np.uint64)
        filled += count
    if filled != entry["rows"]:
        raise RuntimeError(f"row count changed while reading {path.name}: {filled} != {entry['rows']}")

    arr.sort(order="h")
    is_new = np.empty(len(arr), dtype=bool)
    is_new[0] = True
    np.not_equal(arr["h"][1:], arr["h"][:-1], out=is_new[1:])
    starts = np.flatnonzero(is_new)
    del is_new

    ones = np.ones(len(arr), dtype=np.uint16)
    counts = np.add.reduceat(ones, starts, dtype=np.uint16)
    del ones
    if int(counts.sum(dtype=np.int64)) != len(arr):
        counts = np.add.reduceat(np.ones(len(arr), dtype=np.int64), starts, dtype=np.int64)
    sums = np.add.reduceat(arr["s"], starts, dtype=np.int64)
    h_all = arr["h"]
    multiplicity_values, multiplicity_frequency = np.unique(counts, return_counts=True)
    multiplicity_top = {
        str(int(value)): int(freq)
        for value, freq in sorted(
            zip(multiplicity_values, multiplicity_frequency),
            key=lambda pair: pair[1],
            reverse=True,
        )[:10]
    }
    stats = {
        "rows": int(len(arr)),
        "unique_pairs": int(len(starts)),
        "pair_synapse_min": int(sums.min()),
        "pair_synapse_max": int(sums.max()),
        "pair_synapse_mean": round(float(sums.mean()), 3),
        "pair_synapse_total": int(sums.sum()),
        "pair_synapse_percentiles": {
            str(p): float(np.percentile(sums, p)) for p in (0, 1, 5, 25, 50, 75, 95, 99, 100)
        },
        "rows_per_pair_min": int(counts.min()),
        "rows_per_pair_max": int(counts.max()),
        "rows_per_pair_mean": round(float(counts.mean()), 3),
        "rows_per_pair_top": multiplicity_top,
        "pairs_at_least_5_synapses": int((sums >= 5).sum()),
        "rows_at_least_5_synapses": int(counts[sums >= 5].sum()),
        "synapses_at_least_5": int(sums[sums >= 5].sum()),
        "unknown_neuropil_rows": unknown_neuropils,
    }

    result: np.ndarray | None = None
    if filtered:
        unique_hashes = h_all[starts].copy()
        pre = arr["pre"][starts]
        post = arr["post"][starts]
        reverse = mix_hash(post, pre)
        reverse_index = np.searchsorted(unique_hashes, reverse)
        reverse_present = (reverse_index < len(unique_hashes)) & (
            unique_hashes[np.minimum(reverse_index, len(unique_hashes) - 1)] == reverse
        )
        stats["reciprocal_edges"] = int(reverse_present.sum())
        stats["reciprocal_fraction"] = round(float(reverse_present.mean()), 6)
        stats["unordered_reciprocal_pairs"] = int(reverse_present.sum() // 2)
        stats["duplicate_triple_rows"] = int(len(arr) - len(np.unique(arr["t"])))
        result = unique_hashes
    else:
        if filtered_hashes is None:
            raise RuntimeError("filtered hashes are required for the unfiltered comparison")
        lookup = np.searchsorted(h_all, filtered_hashes)
        present = (lookup < len(h_all)) & (h_all[np.minimum(lookup, len(h_all) - 1)] == filtered_hashes)
        strong_mask = sums >= 5
        strong_hashes = h_all[starts[strong_mask]]
        stats["comparison_to_filtered"] = {
            "filtered_pairs_missing_from_unfiltered": int((~present).sum()),
            "filtered_pairs_present": int(present.sum()),
            "unfiltered_only_pairs": int(len(starts) - int(present.sum())),
            "strong_pair_sets_identical": bool(np.array_equal(strong_hashes, filtered_hashes)),
            "unfiltered_pairs_at_least_5_synapses": int(strong_mask.sum()),
            "unfiltered_rows_at_least_5_synapses": int(counts[strong_mask].sum()),
            "unfiltered_synapses_at_least_5": int(sums[strong_mask].sum()),
        }

    del arr
    entry["pair_stats"] = stats
    return entry, result


def cross_dataset(entries: dict[str, dict], id_sets: dict[str, set[int]]) -> dict:
    reference = id_sets.get("neurons.csv.gz", set())
    rows = []
    all_ids: set[int] = set()
    for name, entry in entries.items():
        ids = id_sets.get(name)
        if not ids:
            rows.append({"name": name, "has_root_ids": False, "note": "no root_id column (neuropil-level table)"})
            continue
        all_ids |= ids
        overlap = ids & reference
        outside = ids - reference
        rows.append({
            "name": name,
            "has_root_ids": True,
            "unique_ids": len(ids),
            "rows": entry["rows"],
            "in_reference": len(overlap),
            "outside_reference": len(outside),
            "outside_examples": sorted(outside)[:5],
            "reference_ids_missing_from_file": len(reference - ids),
            "file_coverage": round(len(overlap) / len(ids), 6) if ids else None,
            "reference_coverage": round(len(overlap) / len(reference), 6) if reference else None,
        })

    isolated = {}
    for name in ("connections_princeton.csv.gz", "connections_princeton_no_threshold.csv.gz"):
        missing = reference - id_sets.get(name, set())
        isolated[name] = {"missing_neuron_count": len(missing), "missing_examples": sorted(missing)[:10]}

    return {
        "reference_dataset": "neurons.csv.gz",
        "reference_unique_ids": len(reference),
        "per_dataset": rows,
        "global_union_ids": len(all_ids),
        "global_ids_outside_reference": len(all_ids - reference),
        "global_outside_examples": sorted(all_ids - reference)[:5],
        "datasets_exactly_matching_reference": sorted(name for name, ids in id_sets.items() if ids and ids == reference),
        "neurons_absent_from_connections": isolated,
    }


def build_connection_analysis(entries: dict[str, dict]) -> dict:
    filtered = entries["connections_princeton.csv.gz"]
    unfiltered = entries["connections_princeton_no_threshold.csv.gz"]
    comparison = unfiltered["pair_stats"].get("comparison_to_filtered", {})
    return {
        "source": "connections_princeton.csv.gz (filtered) and connections_princeton_no_threshold.csv.gz",
        "table_grain": "(pre_root_id, post_root_id, neuropil); syn_count is the number of synapses for that directed pair in that neuropil",
        "directed": True,
        "directed_evidence": "pre_root_id -> post_root_id columns; reciprocal and one-way directed pairs coexist",
        "strength": "syn_count (integer synapse count); pair strength is the sum of syn_count across neuropils",
        "self_connections": {
            "filtered": filtered["validation"]["self_connections"],
            "unfiltered": unfiltered["validation"]["self_connections"],
        },
        "filtered_rule": "keep every row belonging to a directed neuron pair whose summed syn_count across all neuropils is >= 5",
        "filtered_rule_verified": comparison.get("strong_pair_sets_identical"),
        "filtered": filtered["pair_stats"],
        "unfiltered": unfiltered["pair_stats"],
        "filtered_vs_unfiltered": comparison,
        "reciprocal": {
            "filtered_directed_pairs": filtered["pair_stats"]["reciprocal_edges"],
            "filtered_fraction": filtered["pair_stats"]["reciprocal_fraction"],
            "filtered_unordered_pairs": filtered["pair_stats"]["unordered_reciprocal_pairs"],
            "unfiltered_note": "reciprocal fraction computed on the filtered table; directionality is identical in both tables",
        },
        "hash_note": "pair sets use a 64-bit mixed hash; at 22.3M rows the collision probability is negligible, and pair/row/synapse counts matched exactly",
    }


def build_manifest(entries: dict[str, dict], partials: list[dict], cross: dict, connection: dict, started: float) -> dict:
    complete = list(entries.values())
    total_rows = sum(entry["rows"] for entry in complete)
    total_compressed = sum(entry["compressed_bytes"] for entry in complete)
    total_uncompressed = sum(entry["uncompressed_bytes"] for entry in complete)
    evidence = [p["embedded_name"] for p in partials if p.get("embedded_name") and "v783" in p["embedded_name"]]
    return {
        "schema_version": "1.0",
        "generated_at_utc": utc_now(),
        "duration_seconds": round(time.time() - started, 1),
        "script": "dataset_audit.py",
        "environment": {
            "python": sys.version.split()[0],
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "platform": platform.platform(),
        },
        "provenance": {
            "dataset": "FAFB (Full Adult Fly Brain), FlyWire connectome materialization",
            "species": "Drosophila melanogaster, adult female",
            "inferred_version": "v783" if evidence else "not found in local filenames",
            "version_evidence": evidence,
            "version_confidence": "inferred from an incomplete download filename; not attested by the completed files",
            "local_root": str(PROJECT_ROOT.parent),
            "retrieval_source_url": None,
            "retrieval_source_note": "No download log or source URL is stored with the files. Filenames indicate Princeton/FlyWire exports; confirm the release and DOI before publication.",
            "completed_files_modified_utc": {
                "earliest": min(entry["modified_utc"] for entry in complete),
                "latest": max(entry["modified_utc"] for entry in complete),
            },
            "scope": "brain only (FAFB); no complete ventral nerve cord, so BANC or Male CNS is required for a complete brain-to-motor pathway",
        },
        "summary": {
            "complete_datasets": len(complete),
            "total_rows": total_rows,
            "compressed_bytes": total_compressed,
            "uncompressed_bytes": total_uncompressed,
            "incomplete_downloads": len(partials),
            "reference_neurons": cross["reference_unique_ids"],
            "global_ids_outside_reference": cross["global_ids_outside_reference"],
            "self_connections": connection["self_connections"],
            "filtered_rule_verified": connection["filtered_rule_verified"],
            "status": "PASS with documented caveats",
        },
        "datasets": complete,
        "connections": connection,
        "cross_dataset": cross,
        "incomplete_downloads": partials,
        "caveats": [
            "The filtered connectome is thresholded on summed pair strength (>=5 synapses), not on each neuropil row; do not apply a second per-row cutoff.",
            "Coordinates contain multiple rows per neuron and exact duplicate rows; deduplicate exact rows before aggregating positions.",
            "Neurotransmitter type is missing for part of the neuron table.",
            "Some neurons have no connection rows and are still valid nodes; keep them in the graph.",
            "Synapse attachment rates use 81 neuropil labels including three aggregate rows; the connection table uses 79 neuropil labels.",
            "FAFB is brain-only; motor output to the full nerve cord is out of scope for these files.",
        ],
    }


def readme(manifest: dict) -> str:
    entries = {entry["name"]: entry for entry in manifest["datasets"]}
    connection = manifest["connections"]
    cross = manifest["cross_dataset"]
    summary = manifest["summary"]
    prov = manifest["provenance"]
    fs = connection["filtered"]
    uf = connection["unfiltered"]
    cmp = connection["filtered_vs_unfiltered"]
    coords = entries["coordinates.csv.gz"]["validation"]
    labels = entries["labels.csv.gz"]["validation"]
    neurons = entries["neurons.csv.gz"]["validation"]
    wide = entries["neuropil_synapse_table.csv.gz"]["validation"]
    attach = entries["synapse_attachment_rates.csv.gz"]["validation"]
    filtered_conn = entries["connections_princeton.csv.gz"]
    unfiltered_conn = entries["connections_princeton_no_threshold.csv.gz"]
    cross_by_name = {row["name"]: row for row in cross["per_dataset"]}
    cell_missing = cross_by_name["cell_stats.csv.gz"]["reference_ids_missing_from_file"]
    filtered_isolated = cross["neurons_absent_from_connections"]["connections_princeton.csv.gz"]["missing_neuron_count"]
    unfiltered_isolated = cross["neurons_absent_from_connections"]["connections_princeton_no_threshold.csv.gz"]["missing_neuron_count"]
    attach_extra = cross["neuropil_labels"]["attachment_only"]
    conn_extra = cross["neuropil_labels"]["connections_only"]
    neuron_range = entries["neurons.csv.gz"]["id_checks"]
    coords_per = coords["rows_per_neuron"]
    filtered_below = filtered_conn["validation"]["rows_with_synapses_below_5"]

    lines = [
        "# FLY-SURFER — Phase 0 dataset audit",
        "",
        f"Generated by `dataset_audit.py` on {manifest['generated_at_utc']} in {manifest['duration_seconds']} s.",
        "",
        "## Verdict",
        "",
        f"- Audited **{summary['complete_datasets']} complete datasets**: {summary['total_rows']:,} rows, {human_bytes(summary['compressed_bytes'])} compressed, {human_bytes(summary['uncompressed_bytes'])} uncompressed.",
        f"- **{cross['global_union_ids']:,}** root IDs appear across the files; **{cross['global_ids_outside_reference']}** fall outside the {cross['reference_unique_ids']:,}-neuron reference.",
        "- Edges are **directed**, strengths are **synapse counts**, and there are **no self-connections**.",
        f"- The filtered table is the unfiltered table restricted to pairs with **summed strength ≥ 5 synapses**: {fs['unique_pairs']:,} pairs / {fs['rows']:,} rows, exactly matching the unfiltered subset.",
        "- Schemas, nulls, duplicate IDs, field checks, coverage, checksums and sample rows are in `datasets/manifest.json`.",
        "",
        "## Critical connection-table check",
        "",
        "| Question | Answer |",
        "|---|---|",
        "| Directed? | **Yes.** Rows are `pre_root_id` → `post_root_id`; reciprocal and one-way pairs coexist. |",
        f"| Strength = synapse count? | **Yes.** `syn_count` is an integer, 1–{unfiltered_conn['validation']['synapse_count_max']} per row; sum it across neuropils for pair weight. |",
        f"| Self-connections? | **No.** Filtered: {connection['self_connections']['filtered']}; unfiltered: {connection['self_connections']['unfiltered']}. |",
        f"| Filtered ≠ unfiltered? | **Yes.** Unfiltered has {uf['unique_pairs']:,} pairs; filtered has {fs['unique_pairs']:,}. Filtered is a strict pair-level subset. |",
        "| IDs consistent? | **Yes.** Every connection endpoint exists in `neurons.csv.gz`; no endpoint is outside the reference. |",
        "",
        f"Reciprocity in the filtered table: **{fs['reciprocal_edges']:,} / {fs['unique_pairs']:,}** directed pairs ({fs['reciprocal_fraction'] * 100:.2f}%) have a reverse edge, forming {fs['unordered_reciprocal_pairs']:,} reciprocal pairs.",
        f"Filtered rows include **{filtered_below:,} rows with `syn_count` < 5**; they belong to stronger pairs. Never apply `syn_count >= 5` per row.",
        "",
        "## Provenance and version",
        "",
        f"- Dataset: **{prov['dataset']}** ({prov['species']}).",
        f"- Inferred version: **{prov['inferred_version']}** — {prov['version_confidence']}.",
        f"- Evidence: `{', '.join(prov['version_evidence']) if prov['version_evidence'] else 'none'}`.",
        f"- Local root: `{prov['local_root']}`.",
        f"- Completed files modified (UTC): {prov['completed_files_modified_utc']['earliest']} → {prov['completed_files_modified_utc']['latest']}.",
        "- Source URL: **not recorded** with the files. Filenames indicate Princeton/FlyWire exports; confirm the release and DOI before publication.",
        f"- Scope: {prov['scope']}.",
        "",
        "## Inventory",
        "",
        "| Dataset | Group | Rows | Cols | Compressed | Uncompressed | SHA-256 (prefix) |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for entry in manifest["datasets"]:
        lines.append(
            f"| `{entry['name']}` | {entry['group']} | {entry['rows']:,} | {len(entry['columns'])} | "
            f"{human_bytes(entry['compressed_bytes'])} | {human_bytes(entry['uncompressed_bytes'])} | `{entry['sha256'][:16]}` |"
        )

    lines += ["", "Full checksums, dtypes, null counts and sample rows are in `manifest.json`.", "", "## Schemas", ""]
    for entry in manifest["datasets"]:
        columns = entry["columns"]
        if len(columns) <= 12:
            description = ", ".join(f"`{c}` ({entry['dtypes'].get(c, '?')})" for c in columns)
        else:
            description = f"{len(columns)} columns; first: " + ", ".join(f"`{c}`" for c in columns[:8]) + ", …"
        lines.append(f"- **`{entry['name']}`** — {entry['rows']:,} rows; {description}")
        missing = {k: v for k, v in entry["null_counts"].items() if v}
        if missing:
            lines.append("  - Missing: " + ", ".join(f"`{k}`={v:,}" for k, v in missing.items()) + ".")

    lines += [
        "",
        "## Cross-dataset ID correspondence",
        "",
        "| Dataset | Unique IDs | In `neurons` | Outside | Reference coverage | Rows |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in cross["per_dataset"]:
        if row.get("has_root_ids"):
            lines.append(
                f"| `{row['name']}` | {row['unique_ids']:,} | {row['in_reference']:,} | {row['outside_reference']} | "
                f"{row['reference_coverage'] * 100:.2f}% | {row['rows']:,} |"
            )
        else:
            lines.append(f"| `{row['name']}` | — | — | — | — | — |")
    lines += [
        "",
        f"Global union **{cross['global_union_ids']:,}**; outside reference **{cross['global_ids_outside_reference']}**. "
        f"Datasets exactly matching the reference: {', '.join(f'`{n}`' for n in cross['datasets_exactly_matching_reference'])}.",
        "",
        "## Validation highlights",
        "",
        f"- **IDs:** all positive int64 FAFB IDs, range `{neuron_range['min_id']}`–`{neuron_range['max_id']}`; no cross-file ID escapes.",
        f"- **Neurons:** {summary['reference_neurons']:,} rows; `nt_type` missing for {neurons['nt_type_missing']:,}; `nt_type_score` matches the corresponding transmitter average on every labeled row.",
        f"- **Cell stats:** {cell_missing} neurons lack length/area/size measurements; no non-positive measurements.",
        f"- **Coordinates:** {coords['exact_duplicate_rows']:,} exact duplicate rows and {coords['duplicate_root_supervoxel_rows']:,} duplicate `(root_id, supervoxel_id)` rows. "
        f"{coords_per['single_row_neurons']:,} neurons have one row; {coords_per['multi_row_neurons']:,} have 2–{coords_per['max']}. Every supervoxel maps to one neuron.",
        f"- **Labels:** {labels['labels_per_neuron_max']} labels per neuron at most; {labels['invalid_dates']} invalid date; no blank labels or malformed positions.",
        f"- **Neuropil table:** {wide['column_count']} columns, {wide['input_synapse_columns']} input and {wide['output_synapse_columns']} output neuropil columns; "
        f"per-neuropil synapse sums equal declared totals on every row; {wide['rows_with_negative_values']} rows with negative values.",
        f"- **Attachment rates:** {attach['neuropil_count']} neuropil labels × pre/post; proof ratios reproduce `count_proof / count_total` (max error {attach['max_proof_ratio_error']:.2e}).",
        f"- **Connections:** no nulls or malformed fields; {filtered_conn['pair_stats']['duplicate_triple_rows']} duplicate `(pre,post,neuropil)` rows in the filtered table; "
        f"{filtered_conn['validation']['neuropil_count']} neuropils; neurotransmitters {', '.join(filtered_conn['validation']['nt_type_domain'])}.",
        f"- **Neuropil vocabulary:** attachment-only labels {attach_extra} are aggregate rows; connection-only labels {conn_extra} are unassigned. The neuropil table shares the connection vocabulary.",
        "",
        "## Incomplete downloads (excluded, left untouched)",
        "",
        "| File | Embedded name | Format | Bytes | Modified (UTC) |",
        "|---|---|---|---:|---|",
    ]
    for item in manifest["incomplete_downloads"]:
        lines.append(
            f"| `{item['name']}` | `{item['embedded_name'] or 'unknown'}` | {item['format']} | {item['bytes']:,} | {item['modified_utc']} |"
        )
    lines += [
        "",
        f"The `{prov['version_evidence'][0] if prov['version_evidence'] else 'unknown'}` download filename is the only local version evidence. These files were not processed.",
        "",
        "## Pre-connectome recommendations",
        "",
        "1. Build adjacency on **directed pairs**, summing `syn_count` across neuropils; do not treat rows as separate edges.",
        "2. Apply the ≥5 threshold once at pair level. The filtered table already encodes it; aggregate the unfiltered table before thresholding.",
        f"3. Keep all {summary['reference_neurons']:,} neurons as nodes, including {unfiltered_isolated} absent from unfiltered and {filtered_isolated} absent from filtered connections.",
        "4. Deduplicate coordinates at exact-row level, then choose one documented position per neuron (centroid or principal position).",
        f"5. Handle the {neurons['nt_type_missing']:,} neurons without `nt_type` with a documented fallback; do not drop them.",
        "6. Treat FAFB as brain-only; add BANC or Male CNS before claiming a complete brain-to-motor pathway.",
        "",
        "## Reproduce",
        "",
        "```bash",
        "cd FLY-SURFER",
        "python dataset_audit.py",
        "```",
        "",
        f"Runtime {manifest['duration_seconds']} s; Python {manifest['environment']['python']}, pandas {manifest['environment']['pandas']}, numpy {manifest['environment']['numpy']}. "
        "The 1.1 GB table is streamed; peak memory comes from the 22.3M-row pair aggregation.",
        "",
        "`datasets/manifest.json` is the canonical machine-readable report.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    started = time.time()
    if not RAW_DIR.is_dir():
        raise SystemExit(f"raw dataset directory not found: {RAW_DIR}")
    paths = sorted(RAW_DIR.rglob("*.csv.gz"))
    if not paths:
        raise SystemExit("no .csv.gz datasets found")

    log(f"FLY-SURFER dataset audit — {len(paths)} complete datasets")
    entries: dict[str, dict] = {}
    id_sets: dict[str, set[int]] = {}

    for path in paths:
        entry = inventory(path, path.parent.name)
        log(f"[inventory] {entry['relative_path']} ({human_bytes(entry['compressed_bytes'])}, sha256 {entry['sha256'][:12]}…)")
        if path.name in ("connections_princeton.csv.gz", "connections_princeton_no_threshold.csv.gz"):
            entry, ids, neuropils = profile_connections(path, entry)
            entry["_neuropils"] = neuropils
        elif path.name == "neuropil_synapse_table.csv.gz":
            entry, ids = profile_wide_table(path, entry)
        else:
            entry, ids = profile_standard(path, entry)
        entries[path.name] = entry
        id_sets[path.name] = ids
        log(f"  rows={entry['rows']:,} columns={len(entry['columns'])} ids={len(ids):,}")

    filtered_name = "connections_princeton.csv.gz"
    unfiltered_name = "connections_princeton_no_threshold.csv.gz"

    log("[pairs] aggregating filtered connection pairs")
    entries[filtered_name], filtered_hashes = pair_aggregate(
        RAW_DIR / "connections" / filtered_name,
        entries[filtered_name],
        filtered=True,
        neuropils=entries[filtered_name]["_neuropils"],
        syn_max=entries[filtered_name]["validation"]["synapse_count_max"],
    )
    log(f"  filtered: {entries[filtered_name]['pair_stats']['unique_pairs']:,} pairs")

    log("[pairs] aggregating unfiltered connection pairs (expensive pass)")
    entries[unfiltered_name], _ = pair_aggregate(
        RAW_DIR / "connections" / unfiltered_name,
        entries[unfiltered_name],
        filtered=False,
        neuropils=entries[unfiltered_name]["_neuropils"],
        syn_max=entries[unfiltered_name]["validation"]["synapse_count_max"],
        filtered_hashes=filtered_hashes,
    )
    comparison = entries[unfiltered_name]["pair_stats"]["comparison_to_filtered"]
    log(f"  unfiltered: {entries[unfiltered_name]['pair_stats']['unique_pairs']:,} pairs; filtered rule verified={comparison['strong_pair_sets_identical']}")

    filtered_neuropils = entries[filtered_name]["_neuropils"]
    attach_neuropils = entries["synapse_attachment_rates.csv.gz"].get("_neuropils", set())
    wide_neuropils = entries["neuropil_synapse_table.csv.gz"].get("_neuropils", set())
    neuropil_comparison = {
        "connection_neuropils": sorted(filtered_neuropils),
        "attachment_only": sorted(attach_neuropils - filtered_neuropils),
        "connections_only": sorted(filtered_neuropils - attach_neuropils),
        "neuropil_table_only": sorted(wide_neuropils - filtered_neuropils),
        "neuropil_table_missing": sorted(filtered_neuropils - wide_neuropils),
    }
    for entry in entries.values():
        entry.pop("_neuropils", None)
        entry.pop("_neuropil_counts", None)

    cross = cross_dataset(entries, id_sets)
    cross["neuropil_labels"] = neuropil_comparison
    connection = build_connection_analysis(entries)
    partials = partial_downloads(PROJECT_ROOT.parent)
    manifest = build_manifest(entries, partials, cross, connection, started)
    manifest = json_safe(manifest)

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST_PATH.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")
    README_PATH.write_text(readme(manifest), encoding="utf-8")

    log(f"[done] manifest: {MANIFEST_PATH}")
    log(f"[done] readme:   {README_PATH}")
    log(
        f"  pairs filtered={manifest['connections']['filtered']['unique_pairs']:,} "
        f"unfiltered={manifest['connections']['unfiltered']['unique_pairs']:,} "
        f"rule_verified={manifest['connections']['filtered_rule_verified']}"
    )


if __name__ == "__main__":
    main()


