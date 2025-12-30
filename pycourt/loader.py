"""tools.court.loader - 法院配置装载

职责
====
- 从 hardcode.yaml / judges_text.yaml / exempt.yaml 等外部事实中
  构建最高法院的运行期配置快照 :class:`CourtConfig`；
- 为 ChiefJustice 与各 Law 实现提供统一的 `load_court_config` 入口；

依赖
====
- 只依赖 `tools.court.models` / `tools.court.config`
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

import yaml
from pydantic.types import JsonValue

from pycourt.config.config import (
    BCConfig,
    CourtConfig,
    CourtExemptions,
    CourtroomTexts,
    CourtTexts,
    DIDiConfig,
    HCConfig,
    JudgeTemplates,
    PCConfig,
    UWConfig,
    VTConfig,
)
from pycourt.config.judges_texts import get_default_lang, load_judges_text_raw
from pycourt.config.yaml_paths import exempt_yaml_path, quality_yaml_path
from pycourt.models import PyCourtJudge, PyCourtLaws

# 规范化后的文本段映射类型
type SectionTextMap = dict[str, str]


class YamlSectionKeys:
    """命名空间：config/exempt/judges_text 等 YAML 段落键名。"""

    LAWS: Final[str] = "laws"
    EXEMPTIONS: Final[str] = "exemptions"
    FILES: Final[str] = "files"
    COURTROOM: Final[str] = "courtroom"
    JUDGES: Final[str] = "judges"


class LawFamilyKeys:
    """命名空间：各 Law 家族在 YAML 中的小写键名。"""

    HC001: Final[str] = "hc001"
    BC001: Final[str] = "bc001"
    UW001: Final[str] = "uw001"
    VT001: Final[str] = "vt001"
    PC001: Final[str] = "pc001"
    DI001: Final[str] = "di001"


_HC_BASE_KEYS: set[str] = {"enabled", "exempt_files", "description"}


def _split_hc001_law_and_config(
    raw_hc: JsonValue,
) -> tuple[dict[str, JsonValue], dict[str, JsonValue]]:
    """将 laws.hc001 的配置拆分为 Law 基础字段与 HCConfig 字段。

    - Law 部分仅保留 enabled/exempt_files/description 等通用法律字段；
    - HCConfig 部分收集其余所有键，交由 :class:`HCConfig` 解释。
    """

    if not isinstance(raw_hc, dict):
        return {}, {}

    law_part: dict[str, JsonValue] = {}
    cfg_part: dict[str, JsonValue] = {}

    for key, value in raw_hc.items():
        if key in _HC_BASE_KEYS:
            law_part[key] = value
        else:
            cfg_part[key] = value

    return law_part, cfg_part


def _load_laws_from_yaml() -> tuple[PyCourtLaws, HCConfig]:
    """从 config.yaml 加载 CourtLaws 结构法典与 HCConfig。

    - ``laws`` 段承载各法条基础开关/豁免配置；
    - 其中 ``hc001`` 小节的除基础字段外的键统一映射为 :class:`HCConfig`。
    """

    cfg_path = quality_yaml_path()
    try:
        with cfg_path.open(encoding="utf-8") as f:
            raw_any: JsonValue = yaml.safe_load(f) or {}
            # raw_any 在此处预期为 dict[str, JSONRuntimeValue]，但类型上我们
            # 将其视为通用 JSONRuntimeValue 并在后续做收窄。
            # 这避免了在签名中使用裸 dict/list[Any]。
            # pyright: ignore[reportAssignmentType]
    except FileNotFoundError:
        raw_any = {}

    root = raw_any if isinstance(raw_any, dict) else {}

    laws_section = root.get(YamlSectionKeys.LAWS)
    laws_raw = laws_section if isinstance(laws_section, dict) else {}

    # 拆分 hc001 的基础字段与 HCConfig 字段
    hc_law_raw = laws_raw.get(LawFamilyKeys.HC001)
    hc_law_part, hc_cfg_part = _split_hc001_law_and_config(hc_law_raw)

    # 使用仅包含基础字段的 hc001 构建 CourtLaws
    cleaned_laws_raw: dict[str, JsonValue] = {}
    for code, cfg in (laws_raw or {}).items():
        if code == LawFamilyKeys.HC001:
            cleaned_laws_raw[code] = hc_law_part
        else:
            cleaned_laws_raw[code] = cfg

    laws = PyCourtLaws.model_validate(cleaned_laws_raw)
    hc_cfg = HCConfig.model_validate(hc_cfg_part or {})

    return laws, hc_cfg


def _safe_mapping(value: JsonValue) -> Mapping[str, JsonValue]:
    """将任意 JSONRuntimeValue 安全收窄为 Mapping[str, JSONRuntimeValue]。"""

    if isinstance(value, Mapping):
        return value
    return {}


def _normalize_text_section(raw: JsonValue) -> SectionTextMap:
    """将单个 section 映射规范化为 str -> str。"""

    out: SectionTextMap = {}
    mapping = _safe_mapping(raw)
    for key, text in mapping.items():
        if not isinstance(text, str):
            continue
        out[key] = text
    return out


def _normalize_courtroom(raw: JsonValue) -> CourtroomTexts:
    """规范化 courtroom 段为 section -> key -> text 并封装为 CourtroomTexts。

    使用 Mapping 作为值类型以避免无契约 dict 嵌套，保持与 CourtroomTexts
    (RootModel[dict[str, dict[str, str]]]) 的结构语义一致，同时通过局部
    赋值收敛为实际的 dict[str, dict[str, str]]。"""

    result: dict[str, Mapping[str, str]] = {}
    mapping = _safe_mapping(raw)
    for section, sec_val in mapping.items():
        result[section] = _normalize_text_section(sec_val)
    return CourtroomTexts({k: dict(v) for k, v in result.items()})


def _normalize_judges(raw: JsonValue) -> JudgeTemplates:
    """规范化 judges 段为 code -> {template: str, ...} 并封装为 JudgeTemplates。

    与 _normalize_courtroom 一致，内部使用 Mapping 作为值类型，最终在
    返回前统一收敛为实际的 dict[str, dict[str, str]]。"""

    result: dict[str, Mapping[str, str]] = {}
    mapping = _safe_mapping(raw)
    for code, entry in mapping.items():
        result[code] = _normalize_text_section(entry)
    return JudgeTemplates({k: dict(v) for k, v in result.items()})


def _load_texts_from_yaml() -> CourtTexts:
    """加载当前语言下的法院/法官文案配置。

    语言选择遵循 ``PYCOURT_LANG`` 环境变量，解析规则与
    :func:`pycourt.config.judges_texts.get_default_lang` 一致：

    - 未设置或非 "zh*" → 使用英文文案 (judges_text.en.yaml)。
    - 以 "zh" 开头       → 使用中文文案 (judges_text.zh.yaml)。
    """

    lang = get_default_lang()
    # load_judges_text_raw 已经保证返回 dict[str, JsonValue]，无需再做类型收窄。
    root: dict[str, JsonValue] = load_judges_text_raw(lang=lang)

    courtroom = _normalize_courtroom(root.get(YamlSectionKeys.COURTROOM, {}))
    judges = _normalize_judges(root.get(YamlSectionKeys.JUDGES, {}))

    return CourtTexts(courtroom=courtroom, judges=judges)


def _load_exemptions_from_yaml() -> CourtExemptions:
    """从 pycourt.yaml (exemptions 段) 加载各法条的路径/文件级治外法权视图。"""

    path = exempt_yaml_path()
    try:
        raw_any: JsonValue = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        raw_any = {}

    root = raw_any if isinstance(raw_any, dict) else {}
    ex_section = root.get(YamlSectionKeys.EXEMPTIONS, {})

    files_map: dict[str, list[str]] = {}
    if isinstance(ex_section, Mapping):
        for code, entry in ex_section.items():
            if not isinstance(entry, Mapping):
                continue
            files_val = entry.get(YamlSectionKeys.FILES, [])
            if isinstance(files_val, list):
                patterns = [p for p in files_val if isinstance(p, str)]
            else:
                patterns = []
            if patterns:
                files_map[code] = patterns

    return CourtExemptions(files=files_map)


def _load_law_family_overrides_from_pycourt() -> Mapping[str, Mapping[str, JsonValue]]:
    """从 pycourt.yaml.laws 段加载各 Law 家族级配置覆盖。

    结构约定示例::

        laws:
          bc001:
            router_dir_patterns:
              - "api/routes/"
            adapter_dir_patterns:
              - "infra/adapters/**"
          uw001:
            infra_repo_subpath: "infra/database/repository"
            infra_system_repo_subpath: "infra/database/repository/system"
          vt001:
            provider_search_pattern: "infra/vector/providers.py"
          pc001:
            core_constants_subpath: "core/constants/"

    仅过滤出 Mapping[str, JsonValue] 形态的子树，其余内容在调用端静默忽略。
    """

    path = exempt_yaml_path()
    try:
        raw_any: JsonValue = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        raw_any = {}

    root = raw_any if isinstance(raw_any, dict) else {}
    laws_section = root.get(YamlSectionKeys.LAWS, {})

    result: dict[str, Mapping[str, JsonValue]] = {}
    if not isinstance(laws_section, Mapping):
        return result

    for code, cfg in laws_section.items():
        if isinstance(cfg, Mapping):
            result[code] = cfg

    return result


def load_court_config() -> CourtConfig:
    """加载最高法院统一配置快照（结构法典 + 文案 + 豁免 + 家族配置）。"""

    laws, hc_cfg = _load_laws_from_yaml()
    texts = _load_texts_from_yaml()
    exemptions = _load_exemptions_from_yaml()

    family_overrides = _load_law_family_overrides_from_pycourt()

    bc_over = family_overrides.get(LawFamilyKeys.BC001, {}) or {}
    uw_over = family_overrides.get(LawFamilyKeys.UW001, {}) or {}
    vt_over = family_overrides.get(LawFamilyKeys.VT001, {}) or {}
    pc_over = family_overrides.get(LawFamilyKeys.PC001, {}) or {}
    di_over = family_overrides.get(LawFamilyKeys.DI001, {}) or {}

    bc_cfg = BCConfig.model_validate(bc_over)
    uw_cfg = UWConfig.model_validate(uw_over)
    vt_cfg = VTConfig.model_validate(vt_over)
    pc_cfg = PCConfig.model_validate(pc_over)
    di_cfg = DIDiConfig.model_validate(di_over)

    return CourtConfig(
        laws=laws,
        texts=texts,
        exemptions=exemptions,
        hc=hc_cfg,
        bc=bc_cfg,
        uw=uw_cfg,
        vt=vt_cfg,
        pc=pc_cfg,
        di=di_cfg,
    )


def load_court_laws() -> PyCourtJudge:
    """兼容入口：从统一 CourtConfig 构建 CourtJudge。"""

    config = load_court_config()
    return PyCourtJudge(laws=config.laws)
