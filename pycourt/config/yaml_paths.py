"""tools.dev.loader.paths - 配置文件路径解析

统一提供仓库根目录与各配置文件的路径解析逻辑，
避免在多个模块中散落 `Path(__file__)` 推断代码。

当前所有 YAML 文件集中放在 `tools/dev/yaml` 目录下：
- hardcode.yaml : 硬编码/常量相关规则（最高法院 HC 系列法典）
- linter.yaml   : 工具审计（ToolsAudityaml）
- exempt.yaml   : 法院豁免配置
- cli_texts.yaml: CLI 文案配置
- judges_text.yaml: 法院/法官文案配置

如需重命名或继续拆分，只需在此处调整路径函数，无需修改调用方。
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from pycourt.utils import find_project_root


class YamlPathConfig:
    """命名空间：PyCourt 内置 YAML 相关路径常量。"""

    PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent.parent


def quality_yaml_path() -> Path:
    """返回内置 HC 配置文件路径（pycourt/yaml/config.yaml）。"""

    return YamlPathConfig.PACKAGE_ROOT / "yaml" / "config.yaml"


def judges_text_yaml_path(lang: str = "en") -> Path:
    """Return path to courtroom/judge messages YAML for given language.

    当前提供多语言支持：
    - ``lang="en"`` -> pycourt/yaml/judges_text.en.yaml
    - ``lang="zh"`` -> pycourt/yaml/judges_text.zh.yaml
    """

    base = YamlPathConfig.PACKAGE_ROOT / "yaml"
    if lang == "zh":
        return base / "judges_text.zh.yaml"
    # 默认使用英文文案，方便开源用户直接理解
    return base / "judges_text.en.yaml"


def exempt_yaml_path() -> Path:
    """法院文件级豁免配置路径（项目根目录 ./pycourt.yaml）。"""
    return find_project_root() / "pycourt.yaml"
