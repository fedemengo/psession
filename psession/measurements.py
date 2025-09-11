from dataclasses import dataclass, field
from typing import List, Optional
from .parsers.parser import BaseParser, eisParser, lsvParser, cvParser
import pandas as pd


@dataclass
class Measurements:
    EIS: pd.DataFrame = field(default_factory=pd.DataFrame)
    LSV: pd.DataFrame = field(default_factory=pd.DataFrame)
    CV: pd.DataFrame = field(default_factory=pd.DataFrame)


def enrich_df(df: pd.DataFrame, enrichments: list) -> pd.DataFrame:
    out = df.copy()
    for match_fn, upd_fn in enrichments:
        m = out.apply(match_fn, axis=1)
        if not m.any():
            continue
        upd = out.loc[m].apply(upd_fn, axis=1).apply(pd.Series)
        out.loc[m, upd.columns] = upd.values

    return out


@dataclass
class CacheParameters:
    write_cache: bool = True
    read_cache: bool = True
    cache_path: Optional[str] = None
    cache_prefix: Optional[str] = None

    def read_fp(self, suffix: str) -> Optional[str]:
        if not self.read_cache:
            return None
        if self.cache_path is None or self.cache_prefix is None:
            return None
        return f"{self.cache_path}/{self.cache_prefix}_{suffix}"

    def write_fp(self, suffix: str) -> Optional[str]:
        if not self.write_cache:
            return None
        if self.cache_path is None or self.cache_prefix is None:
            return None
        return f"{self.cache_path}/{self.cache_prefix}_{suffix}"


@dataclass
class Parsers:
    eisParser: BaseParser = field(default=eisParser)
    lsvParser: BaseParser = field(default=lsvParser)
    cvParser: BaseParser = field(default=cvParser)

    cache_params: CacheParameters = field(default_factory=CacheParameters)

    def parse_measurement_info(self, measurement: dict) -> Optional[dict]:
        for p in [self.eisParser, self.lsvParser, self.cvParser]:
            out = p.parse_info(measurement)
            if out is not None:
                return out
        return None

    def parse_info(self, measurements: list[dict]) -> list[dict]:
        info = []
        for m in measurements:
            out = self.parse_measurement_info(m)
            if out is None:
                continue
            info.append(out)
        return info

    def parse_measurement_data(
        self,
        parser: BaseParser,
        measurements: List[dict],
        enrichments: list,
        opts: dict,
    ):
        read_cached_path = self.cache.read_fp(str(parser) + ".csv")
        if read_cached_path is not None:
            try:
                df = pd.read_csv(read_cached_path)
                return df
            except Exception:
                pass

        out = []
        for i, measurement in enumerate(measurements):
            try:
                data = parser.parse_data(measurement)
                if data is None:
                    continue
                out.append(data)
            except Exception as e:
                print(f"Error parsing {parser} measurement #{i}: {e}")

        if len(out) == 0:
            return pd.DataFrame()

        print(f"Parsed {len(out)} {parser} measurements")

        df = pd.concat(out)
        df = enrich_df(df, enrichments)

        sort_keys = opts.get("presort", []) + parser.sort_keys + opts.get("sort", [])
        df = df.sort_values(sort_keys, kind="mergesort").reset_index(drop=True)

        write_cached_path = self.cache.write_fp(str(parser) + ".csv")
        if write_cached_path is not None:
            try:
                df.to_csv(write_cached_path, index=False)
            except Exception:
                pass

        return df

    def parse(
        self,
        measurements: list[dict],
        enrichments: list,
        opts: dict,
    ) -> Measurements:
        return Measurements(
            EIS=self.parse_measurement_data(
                self.eisParser,
                measurements,
                enrichments=enrichments,
                opts=opts,
            ),
            LSV=self.parse_measurement_data(
                self.lsvParser,
                measurements,
                enrichments=enrichments,
                opts=opts,
            ),
            CV=self.parse_measurement_data(
                self.cvParser,
                measurements,
                enrichments=enrichments,
                opts=opts,
            ),
        )

    def cached(self, cache_params: CacheParameters) -> "Parsers":
        self.cache = cache_params
        return self
