"""tools.config.loader.exempt - 法条豁免配置加载入口

集中管理各法条的“路径/文件级”豁免信息。

当前仅支持：
- 按法条编号（如 "DT001"、"OC001"）查询 files 级豁免列表；

数据来源：tools/config/yaml/exempt.yaml
结构约定：

exemptions:
  DT001:
    files:
      - "tests/**"
      - "tools/**"
  ...

"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from functools import lru_cache
from typing import Final

import yaml
from pydantic.types import JsonValue

from pycourt.config.yaml_paths import exempt_yaml_path

_EXEMPTIONS_KEY: Final[str] = "exemptions"
_FILES_KEY: Final[str] = "files"


@lru_cache(1)
def _load_exempt_raw() -> dict[str, JsonValue]:
    """加载 exempt.yaml，返回顶层映射；出错时返回空字典。"""

    path = exempt_yaml_path()
    try:
        raw_any: JsonValue = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        return {}

    return raw_any if isinstance(raw_any, dict) else {}


def _as_str_list(val: JsonValue) -> list[str]:
    """将任意值安全转换为 list[str]，容错 Mapping/Sequence。"""

    if isinstance(val, str) or not isinstance(val, Sequence):
        return []
    out: list[str] = []
    for item in val:
        if isinstance(item, str):
            out.append(item)
    return out


def get_exempt_files(code: str) -> list[str]:
    """获取给定法条编号的路径/文件级豁免列表。

    - ``code`` 为法条编号，如 "DT001"、"DS001"、"LL001" 等；
    - 若 YAML 中未配置对应条目，返回空列表。
    """

    data = _load_exempt_raw().get(_EXEMPTIONS_KEY, {}) or {}
    if not isinstance(data, Mapping):
        return []

    entry = data.get(code)
    if not isinstance(entry, Mapping):
        return []

    files_val = entry.get(_FILES_KEY, [])
    return _as_str_list(files_val)
