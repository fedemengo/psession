import argparse
import json
import os
from pprint import pprint
import pandas as pd

from .parsers.common import parse_method
from .parsers.eis import parse_eis, SORT_KEYS as SORT_KEYS_EIS
from .parsers.cv import parse_cv
from .parsers.lsv import parse_lsv


def multi_encoding_open(file_path, encodings):
    content = None
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    return content


def find_json_end(content):
    brace_count, json_end = 0, -1
    for i, char in enumerate(content):
        if char == "{":
            brace_count += 1
        elif char == "}":
            brace_count -= 1
            if brace_count == 0:
                json_end = i + 1
                break

    if json_end > 0:
        return json_end

    raise ValueError("Could not find valid JSON structure")


def parse_pssession_file(fp, encodings=["utf-16", "utf-16-le"]):
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
        except json.JSONDecodeError as e:
            raise e

    envPrint = os.getenv("PRINT", "")
    if envPrint in ("1", "true", "yes", "t", "y"):
        pprint(data)

    return data


def parse_eis_data(measurements, enrichments=[], opts={}):
    out = []
    for i, measurement in enumerate(measurements):
        method_params = parse_method(measurement.get("Method", ""))
        mid = method_params.get("METHOD_ID", "").lower()
        if mid != "eis":
            continue

        out.append(parse_eis(measurement))

    if len(out) == 0:
        return None

    df = pd.concat(out)
    df = enrich_df(df, enrichments)

    sort_keys = opts.get("presort", []) + SORT_KEYS_EIS + opts.get("sort", [])
    df = df.sort_values(sort_keys, kind="mergesort").reset_index(drop=True)

    return df


def enrich_df(df, enrichments):
    out = df.copy()
    for match_fn, upd_fn in enrichments:
        m = out.apply(match_fn, axis=1)
        if not m.any():
            continue
        upd = out.loc[m].apply(upd_fn, axis=1).apply(pd.Series)  # dicts → columns
        out.loc[m, upd.columns] = upd.values

    return out


def parse_data(data, enrichments=[], opts={}):
    measurements = data.get("Measurements", [])

    eis = parse_eis_data(measurements, enrichments=enrichments, opts=opts)
    cv = None
    lsv = None

    return eis, cv, lsv


def parse_info(data):
    info = []
    for measurement in data.get("Measurements", []):
        method_params = parse_method(measurement.get("Method", ""))
        mid = method_params.get("METHOD_ID", "").lower()
        info.append(
            {
                "title": measurement.get("Title", ""),
                "method_id": mid,
            }
        )

    return info


def parse(file_path, enrichments=[], opts={}):
    data = parse_pssession_file(file_path)
    return parse_data(data, enrichments=enrichments, opts=opts)


def info(file_path):
    data = parse_pssession_file(file_path)
    return parse_info(data)


def gen_annotation(file_path, fn):
    out = []
    for minfo in info(file_path):
        out.append({**minfo, **fn(minfo)})
    return out
