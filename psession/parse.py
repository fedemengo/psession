from __future__ import annotations

import json
import os
import logging
from pprint import pprint
from typing import Iterable, Optional
from .measurements import Measurements, Parsers, CacheParameters

SUPPORTED_VERSION = (5, 11, 1006)


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def multi_encoding_open(fp: str, encodings: Iterable[str]) -> Optional[str]:
    for enc in encodings:
        try:
            with open(fp, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    return None


def find_json_end(content: str) -> int:
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
    v_str = data.get("CoreVersion", "")
    parts = v_str.split(".")

    if len(parts) < 2:
        raise ValueError(f"Could not parse version string: {v_str}")

    major = int(parts[0])
    minor = int(parts[1])

    if major > SUPPORTED_VERSION[0] or minor > SUPPORTED_VERSION[1]:
        v_supp = ".".join(map(str, SUPPORTED_VERSION))
        raise ValueError(f"Version {v_str} is newer than supported {v_supp}")


def parse_pssession_file(
    fp: str,
    encodings: Iterable[str] = ("utf-16", "utf-16-le"),
    force_reload: bool = False,
    cache_path: Optional[str] = None,
) -> dict:
    cache_path = cache_path or os.path.dirname(fp)
    filename = os.path.basename(fp)

    fp_json = os.path.join(cache_path, filename + ".json")
    if os.path.exists(fp_json) and not force_reload:
        with open(fp_json, "r", encoding="utf-8") as f:
            return json.load(f)

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

    # cache parsed json file
    with open(fp_json, "w", encoding="utf-8") as f:
        json.dump(data, f)

    return data


def cache_parameters(
    file_path: str,
    cache_path: Optional[str] = None,
    force_reload: bool = False,
) -> CacheParameters:
    return CacheParameters(
        write_cache=True,
        read_cache=not force_reload,
        cache_path=cache_path or os.path.dirname(file_path),
        cache_prefix=os.path.basename(file_path),
    )


def parse(
    file_path: str,
    enrichments: list = [],
    opts: dict = {},
    force_reload: bool = False,
    cache_path: Optional[str] = None,
) -> Measurements:
    cache_params = cache_parameters(
        file_path,
        cache_path=cache_path,
        force_reload=force_reload,
    )

    data = parse_pssession_file(
        file_path,
        force_reload=force_reload,
        cache_path=cache_params.cache_path,
    )

    return (
        Parsers()
        .cached(cache_params)
        .parse(
            data.get("Measurements", []),
            enrichments=enrichments,
            opts=opts,
        )
    )


def info(
    file_path: str,
    force_reload: bool = False,
    cache_path: Optional[str] = None,
) -> list[dict]:
    cache_params = cache_parameters(
        file_path,
        cache_path=cache_path,
        force_reload=force_reload,
    )

    data = parse_pssession_file(
        file_path,
        force_reload=force_reload,
        cache_path=cache_params.cache_path,
    )
    return Parsers().parse_info(data.get("Measurements", []))
