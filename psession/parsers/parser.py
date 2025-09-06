from typing import Callable
from .common import (
    ticks_to_date,
    method_to_dict,
    pick_keys,
    parse_common,
    METHOD_ID,
)


from .eis import (
    METHOD_ID as EIS_METHOD_ID,
    parse_eis,
    METHOD_KEYS as EIS_METHOD_KEYS,
    INFO_KEYS as EIS_INFO_KEYS,
    SORT_KEYS as EIS_SORT_KEYS,
)
from .cv import (
    METHOD_ID as CV_METHOD_ID,
    parse_cv,
    METHOD_KEYS as CV_METHOD_KEYS,
    INFO_KEYS as CV_INFO_KEYS,
    SORT_KEYS as CV_SORT_KEYS,
)
from .lsv import (
    METHOD_ID as LSV_METHOD_ID,
    parse_lsv,
    METHOD_KEYS as LSV_METHOD_KEYS,
    INFO_KEYS as LSV_INFO_KEYS,
    SORT_KEYS as LSV_SORT_KEYS,
)


def parse_method(text, select_keys=None, match_method_id=None):
    m_dict = method_to_dict(text)
    if match_method_id and m_dict.get(METHOD_ID, "").lower() != match_method_id.lower():
        return None

    out = m_dict
    if select_keys is not None:
        out = pick_keys(m_dict, select_keys)

    out[METHOD_ID] = m_dict.get(METHOD_ID, "").lower()

    return out


class BaseParser:
    def __init__(
        self,
        method_id: str,
        parse: Callable,
        sort_keys: list = [],
        method_keys: list = [],
        info_keys: list = [],
    ):
        self.mid = method_id
        self.parse = parse
        self.sort_keys = sort_keys
        self.method_keys = method_keys
        self.info_keys = info_keys

    def __repr__(self):
        return self.mid.upper()

    def parse_method(self, text: str, info: bool = False, data: bool = False):
        select_keys = None
        if info:
            select_keys = self.info_keys
        if data:
            select_keys = self.method_keys

        return parse_method(
            text,
            select_keys=select_keys,
            match_method_id=self.mid,
        )

    def parse_info(self, m: dict):
        method_params = self.parse_method(m.get("Method", ""), info=True)
        if method_params is None:
            return None

        return {
            **parse_common(m),
            **method_params,
        }

    def parse_data(self, m: dict):
        method_params = self.parse_method(m.get("Method", ""), data=True)
        if method_params is None:
            return None

        return self.parse(m, method_info=method_params)


eisParser = BaseParser(
    method_id=EIS_METHOD_ID,
    parse=parse_eis,
    sort_keys=EIS_SORT_KEYS,
    method_keys=EIS_METHOD_KEYS,
    info_keys=EIS_INFO_KEYS,
)
lsvParser = BaseParser(
    method_id=LSV_METHOD_ID,
    parse=parse_lsv,
    sort_keys=LSV_SORT_KEYS,
    method_keys=LSV_METHOD_KEYS,
    info_keys=LSV_INFO_KEYS,
)

cvParser = BaseParser(
    method_id=CV_METHOD_ID,
    parse=parse_cv,
    sort_keys=CV_SORT_KEYS,
    method_keys=CV_METHOD_KEYS,
    info_keys=CV_INFO_KEYS,
)
