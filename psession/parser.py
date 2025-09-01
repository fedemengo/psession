from __future__ import annotations

import json
import os
import logging
from pprint import pprint
from typing import Iterable, List, Optional, Tuple
import pandas as pd

from .parsers.common import parse_method, parse_common
from .parsers.eis import parse_eis, SORT_KEYS as SORT_KEYS_EIS
from .parsers.cv import parse_cv
from .parsers.lsv import parse_lsv

SUPPORTED_VERSION = (5, 11, 1006)

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def multi_encoding_open(file_path: str, encodings: Iterable[str]) -> Optional[str]:
    """Read text trying multiple encodings, returning the first success."""
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    return None


def find_json_end(content: str) -> int:
    """Find the end index of the first complete JSON object in content."""
    brace_count, json_end = 0, -1
    for i, char in enumerate(content):
        if char == "{":
            brace_count += 1
        elif char == "}":
            brace_count -= 1
            if brace_count == 0:
                json_end = i + 1
                break

    if json_end <= 0:
        raise ValueError("Could not find valid JSON structure")
    return json_end


def check_support(data: dict):
    version_string = data.get("CoreVersion", "")
    parts = version_string.split(".")

    if len(parts) < 2:
        raise ValueError(f"Could not parse version string: {version_string}")

    major = int(parts[0])
    minor = int(parts[1])

    if major > SUPPORTED_VERSION[0] or minor > SUPPORTED_VERSION[1]:
        supp_v = ".".join(map(str, SUPPORTED_VERSION))
        raise ValueError(f"Version {version_string} is newer than supported {supp_v}")


def parse_pssession_file(
    fp: str, encodings: Iterable[str] = ("utf-16", "utf-16-le")
) -> dict:
    """Parse a .pssession file into a Python dict, handling encoding fallbacks
    and potential trailing bytes past the JSON root object.
    """
    content = multi_encoding_open(fp, encodings)
    if content is None:
        raise ValueError(f"Could not read {fp} with encodings {encodings}")

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        json_end = find_json_end(content)
        try:
            json_content = content[:json_end]
            data = json.loads(json_content)
            fp_json = fp + ".json"
            if not os.path.exists(fp_json):
                with open(fp_json, "w", encoding="utf-8") as f:
                    f.write(json_content)
        except json.JSONDecodeError as e:
            raise e

    envPrint = os.getenv("PRINT", "")
    if envPrint in ("1", "true", "yes", "t", "y"):
        pprint(data)

    try:
        check_support(data)
    except ValueError as e:
        log.warning("Support check failed: %s", e)

    return data


def parse_measurement_data(
    method_id: str,
    parse_fn,
    measurements: List[dict],
    enrichments: list = [],
    opts: dict = {},
):
    out = []
    for i, measurement in enumerate(measurements):
        method_params = parse_method(measurement.get("Method", ""))
        mid = method_params.get("method_id", "")
        if mid != method_id:
            continue

        try:
            data = parse_fn(measurement, method_info=method_params)
        except Exception as e:
            log.error(f"Error parsing {method_id} measurement #{i}: {e}")
            continue

        out.append(data)

    if len(out) == 0:
        return None

    print(f"Parsed {len(out)} {method_id.upper()} measurements")

    df = pd.concat(out)
    df = enrich_df(df, enrichments)

    sort_keys = opts.get("presort", []) + SORT_KEYS_EIS + opts.get("sort", [])
    df = df.sort_values(sort_keys, kind="mergesort").reset_index(drop=True)

    return df


def enrich_df(df: pd.DataFrame, enrichments: list) -> pd.DataFrame:
    out = df.copy()
    for match_fn, upd_fn in enrichments:
        m = out.apply(match_fn, axis=1)
        if not m.any():
            continue
        upd = out.loc[m].apply(upd_fn, axis=1).apply(pd.Series)  # dicts → columns
        out.loc[m, upd.columns] = upd.values

    return out


def parse_data(
    data: dict, enrichments: list = [], opts: dict = {}
) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    measurements = data.get("Measurements", [])

    eis = parse_measurement_data(
        "eis", parse_eis, measurements, enrichments=enrichments, opts=opts
    )
    lsv = parse_measurement_data(
        "lsv", parse_lsv, measurements, enrichments=enrichments, opts=opts
    )
    cv = parse_measurement_data(
        "cv", parse_cv, measurements, enrichments=enrichments, opts=opts
    )

    return eis, cv, lsv


def parse_info(data: dict) -> list:
    info = []
    for measurement in data.get("Measurements", []):
        method_params = parse_method(measurement.get("Method", ""))
        info.append(
            {
                **parse_common(measurement),
                "method_id": method_params.get("method_id", ""),
            }
        )

    return info


def parse(file_path: str, enrichments: list = [], opts: dict = {}):
    data = parse_pssession_file(file_path)
    return parse_data(data, enrichments=enrichments, opts=opts)


def info(file_path: str) -> list:
    data = parse_pssession_file(file_path)
    return parse_info(data)


def gen_annotation(file_path: str, fn):
    out = []
    for minfo in info(file_path):
        out.append({**minfo, **fn(minfo)})
    return out
