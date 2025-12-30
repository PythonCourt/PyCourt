# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
# ==============================================================================
# 🏛️ 帝国配置规划署 V2.3 - CI 配置专用装置
# 说明：
#   - 提供给 QA 脚本的统一配置入口（覆盖率阈值与审计范围）；
# ==============================================================================

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from collections.abc import Mapping
from typing import Final

from pycourt.utils import ProjectFiles, find_project_root

# 本工具链直接从 pyproject.toml 读取配置，避免依赖核心 config 常量

_TOOL_SECTION: Final[str] = "tool"
_TIMEOS_SECTION: Final[str] = "pycourt"
_KEY_COVERAGE: Final[str] = "coverage"
_KEY_CIVILIZED_PATHS: Final[str] = "civilized_paths"


def load_and_prepare_config_for_ci() -> Mapping[str, object]:
    """从 pyproject.toml 读取 [tool.pycourt] 并返回 CI 准备好的配置。

    返回一个包含以下键的映射：

    - fail_under：覆盖率阈值（仅打印）；
    - civilized_paths：所有审计路径；
    - coverage_paths：覆盖率路径（排除 tests/*）。
    """
    project_root = find_project_root()
    pyproject_path = project_root / ProjectFiles.PYPROJECT_FILENAME

    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    tool_config = data.get(_TOOL_SECTION, {})
    timeos_config = tool_config.get(_TIMEOS_SECTION, {})

    fail_under = timeos_config.get(_KEY_COVERAGE, 85)
    all_paths = timeos_config.get(_KEY_CIVILIZED_PATHS, [])

    # Exclude tests/* from coverage paths
    coverage_paths = [
        p
        for p in all_paths
        if not (p == "tests" or (isinstance(p, str) and p.startswith("tests/")))
    ]

    return {
        "fail_under": fail_under,
        "civilized_paths": all_paths,
        "coverage_paths": coverage_paths,
    }


def main() -> None:
    """CLI entry point for CI scripts.

    当前仅支持 `--for-ci`，用于 `qa.sh` 从 pyproject.toml 提取：
    - 覆盖率阈值；
    - 审计路径列表；
    - 覆盖率收集路径列表（排除 tests/*）。
    """
    parser = argparse.ArgumentParser(description="TimeOS帝国配置规划署")
    parser.add_argument(
        "--for-ci",
        action="store_true",
        help="以JSON格式输出 CI/CD 所需的战略配置。",
    )

    args = parser.parse_args()

    if args.for_ci:
        config = load_and_prepare_config_for_ci()
        json.dump(config, sys.stdout)


if __name__ == "__main__":
    main()
