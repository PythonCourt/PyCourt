"""PyCourt courtroom & judges messages loader.

Central place for user-facing texts of the PyCourt "Supreme Court", including:
- Courtroom process texts (start/summary/messages from the audit clerk).
- Judgement templates for each law code (used to render violation reports).

中文摘要：集中管理 PyCourt 最高法院的对外文案（庭审流程 + 各位大法官的判决模板），
并通过 YAML 外部化，便于多语言支持与语气统一管理。
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from functools import lru_cache

import yaml
from pydantic.types import JsonValue

from pycourt.config.yaml_paths import judges_text_yaml_path

# 环境变量名：用于控制 PyCourt 文案语言
_DEFAULT_LANG_ENV = "PYCOURT_LANG"


def get_default_lang() -> str:
    """Return default language code for PyCourt messages.

    优先读取环境变量 ``PYCOURT_LANG``，目前支持：
    - "en" / 其他: 英文（默认）
    - "zh" / "zh_CN" / "zh-Hans" 等以 "zh" 开头的值：中文
    """

    raw = os.getenv(_DEFAULT_LANG_ENV, "en").strip().lower()
    if raw.startswith("zh"):
        return "zh"
    return "en"


@lru_cache(maxsize=4)
def load_judges_text_raw(lang: str = "en") -> dict[str, JsonValue]:
    """Load language-specific judges_text YAML; return top-level mapping.

    出错时返回空字典，调用方再根据 key 抛出更具体的 KeyError。
    """

    path = judges_text_yaml_path(lang=lang)
    try:
        raw_any: JsonValue = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        return {}

    return raw_any if isinstance(raw_any, dict) else {}


_COURTROOM_KEY_PARTS = 2  # key 格式: "section.subkey"


def get_courtroom_text(key: str, lang: str = "en") -> str:
    """Return courtroom-process message text for the given key and language.

    ``key`` examples:
    - "supreme_court.start"
    - "supreme_court.summary_failed"
    - "supreme_court.summary_passed"
    - "audit_clerk.deps_missing_title"

    若 YAML 中未配置对应 key，将抛出 KeyError，
    以便在测试阶段尽早暴露配置问题。
    """

    data = load_judges_text_raw(lang=lang).get("courtroom", {}) or {}
    if not isinstance(data, Mapping):  # 保护性检查
        raise KeyError("courtroom section missing in judges_text.yaml")

    parts = key.split(".", 1)
    if len(parts) != _COURTROOM_KEY_PARTS:
        raise KeyError(f"invalid courtroom key: {key!r}")

    section_obj = data.get(parts[0])
    if not isinstance(section_obj, Mapping):
        raise KeyError(f"courtroom section not found: {parts[0]!r}")

    val = section_obj.get(parts[1])
    if not isinstance(val, str):
        raise KeyError(f"courtroom text not found: {key!r}")
    return val


def get_judge_template(code: str, lang: str = "en") -> str:
    """Return judge template text for a given law code and language.

    - ``code`` is normally a violation code like "HC001", "LL001", "AC002".
    - For sub-cases under the same law, extended keys may be used, e.g.
      "VT001_UNSUPPORTED_ASSET", "RE003_CTRL_FLOW".

    若 YAML 中未配置对应条目，将抛出 KeyError，
    以便在测试阶段尽早暴露配置问题。
    """

    data = load_judges_text_raw(lang=lang).get("judges", {}) or {}
    if not isinstance(data, Mapping):
        raise KeyError("judges section missing in judges_text.yaml")

    entry_obj = data.get(code)
    if not isinstance(entry_obj, Mapping):
        raise KeyError(f"judge template entry not found for code: {code!r}")

    tpl = entry_obj.get("template")
    if not isinstance(tpl, str):
        raise KeyError(f"judge template missing 'template' field for code: {code!r}")
    return tpl
