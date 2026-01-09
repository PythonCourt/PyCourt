"""🏛️ 参数分类审查官（PC001/PC002）

本模块实现参数分类审查官，负责在常量与规则访问层面区分“运营参数”与
技术常量：
- PC001: 在 core/constants 层识别疑似运营参数的常量（特别是长中文字符串与
  可调规则结构），提示迁移到 assets/ 由 RuleProvider 统一管理；
- PC002: 检测绕过 RuleProvider 直接访问 assets/ 等规则目录的行为。

设计要点
- 仅依赖 AST 与静态分析，不执行任何运行时代码；
- 所有违规信息均通过 `judges_text.yaml` 中的 PC001/PC002 模板渲染；
- 配置来源：
  - `laws.yaml` → `laws.pc001`: enabled 等法条开关；
  - `exempt.yaml` → `exemptions.PC001.files`: 路径/文件级豁免（治外法权）。
"""

from __future__ import annotations

import ast
import fnmatch
import re
from pathlib import Path
from typing import ClassVar, Final

from pycourt.config.config import CourtConfig
from pycourt.utils import Violation, normalize_patterns


class TheParamClassLaw:
    """🏛️ 调参分类审查官 - 识别运营参数并约束规则访问（PC001/PC002）。

    职责
    - PC001: 在 core/constants 层识别疑似运营参数的常量（长中文字符串、可调
      规则结构等），建议迁移到 assets/ 由 RuleProvider 统一管理；
    - PC002: 在全局范围内检测绕过 RuleProvider 直接访问 assets/ 等规则目录的
      行为，并给出整改建议。
    """

    CODE_PC001: Final[str] = "PC001"
    CODE_PC002: Final[str] = "PC002"

    # 规则目录关键词（仅针对 rules/config 相关资产，技能资产由 SK 系列负责）
    RULE_DIR_KEYWORDS: Final[tuple[str, ...]] = (
        "assets/rules",
        "rules/",
        "configs/",
        "config/",
    )

    # 文件操作关键词
    FILE_OP_KEYWORDS: Final[tuple[str, ...]] = (
        "open(",
        "Path(",
        "rglob(",
        "glob(",
        ".read",
        ".load",
    )

    _SOUL_PARAM_KEYWORDS: ClassVar[list[str]] = [
        "MESSAGE",
        "PROMPT",
        "TEXT",
        "TEMPLATE",
        "STYLE",
        "TONE",
        "PERSONALITY",
        "GREETING",
        "FAREWELL",
    ]
    _PHYSICAL_PARAM_KEYWORDS: ClassVar[list[str]] = [
        "URL",
        "HOST",
        "PORT",
        "PATH",
        "TIMEOUT",
        "SIZE",
        "LIMIT",
        "COUNT",
        "KEY",
        "ID",
        "PREFIX",
        "SUFFIX",
    ]
    _SUSPICION_THRESHOLD: ClassVar[int] = 10

    def __init__(self, config: CourtConfig) -> None:
        self.config = config
        self.laws = config.laws
        self._msg_pc001: str = self.config.get_judge_template(self.CODE_PC001)
        self._msg_pc002: str = self.config.get_judge_template(self.CODE_PC002)

    def _calculate_suspicion_score(
        self, const_name: str, const_value_node: ast.AST
    ) -> int:
        """基于命名和值类型，计算一个常量的“参数嫌疑分”。"""
        score = 0

        # 1. 命名审查
        upper_name = const_name.upper()
        if any(keyword in upper_name for keyword in self._SOUL_PARAM_KEYWORDS):
            score += 5
        if any(keyword in upper_name for keyword in self._PHYSICAL_PARAM_KEYWORDS):
            score -= 5

        # 2. 值类型审查
        if isinstance(const_value_node, ast.Constant):
            value = const_value_node.value
            # 中文长字符串是高度可疑的"灵魂参数"
            if (
                isinstance(value, str)
                and len(value) > self._SUSPICION_THRESHOLD
                and re.search(r"[\u4e00-\u9fa5]", value)
            ):
                score += 5
            # 字典或列表，可能是可调整的规则
            elif isinstance(value, (dict | list | set | tuple)):
                score += 2

        return score

    def _check_rule_provider_bypass(
        self, file_path: Path, lines: list[str]
    ) -> list[Violation]:
        """检查绕过 RuleProvider 直接访问 assets/ 等规则目录的行为 (PC002)。"""
        violations: list[Violation] = []
        fp_str = file_path.as_posix()

        # 路径级豁免：由全局豁免表控制（PC001 -> files）
        patterns = normalize_patterns(self.config.get_exempt_files(self.CODE_PC001))
        if any(fnmatch.fnmatch(fp_str, p) or fp_str.endswith(p) for p in patterns):
            return violations

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            # 跳过空行和注释
            if not stripped or stripped.startswith("#"):
                continue
            # 跳过 import 语句
            if "import" in line:
                continue

            # 检查是否包含规则目录关键词
            has_rule_dir = any(kw in line for kw in self.RULE_DIR_KEYWORDS)
            if not has_rule_dir:
                continue

            # 检查是否包含文件操作关键词
            has_file_op = any(kw in line for kw in self.FILE_OP_KEYWORDS)
            if not has_file_op:
                continue

            # 发现违规
            violations.append(
                Violation(
                    file_path=file_path,
                    line=line_num,
                    col=0,
                    code=self.CODE_PC002,
                    message=self._msg_pc002.format(snippet=stripped[:60]),
                )
            )

        return violations

    def investigate(
        self, file_path: Path, content: str, lines: list[str], tree: ast.AST | None
    ) -> list[Violation]:
        """审查参数分类违规（PC001/PC002）。

        检查范围
        - PC001: 仅在约定的核心常量目录内识别疑似运营参数常量；
        - PC002: 在全局范围内检测绕过规则提供方直接访问规则目录的行为。

        执行步骤
        1. 读取 ``laws.pc001`` 配置，若 ``enabled`` 为 False 则整体禁用；
        2. 先执行 PC002 检查（不依赖 AST，仅基于源代码行）；
        3. 若当前文件不在 ``<root>/core/constants/`` 下，直接返回；
        4. 若 AST 缺失则无法进行 PC001 检查，直接返回；
        5. 在 constants 目录中遍历顶级常量定义，对疑似运营参数产出 PC001 违规。
        """
        del content  # 未使用

        # 全局开关
        config = self.laws.pc001
        if not getattr(config, "enabled", True):
            return []

        violations: list[Violation] = []

        # PC002: 检查绕过 RuleProvider 的行为（全局检查）
        violations.extend(self._check_rule_provider_bypass(file_path, lines))

        # PC001: 只审查核心常量目录（例如 ``<root>/core/constants/``）
        pc_cfg = getattr(self.config, "pc", None)
        if pc_cfg is None:
            return violations
        subpath = pc_cfg.core_constants_subpath
        if subpath not in file_path.as_posix():
            return violations

        if tree is None:
            return violations

        # PC001: 审查常量定义，只关心顶级赋值语句
        violations.extend(self._check_constants_module_for_params(file_path, tree))
        return violations

    def _check_constants_module_for_params(
        self, file_path: Path, tree: ast.AST
    ) -> list[Violation]:
        """在 constants 模块中识别疑似运营参数常量 (PC001)。"""

        violations: list[Violation] = []

        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
            ):
                continue

            const_name = node.targets[0].id
            const_value_node = node.value

            # 只审查全大写的常量
            if not const_name.isupper():
                continue

            score = self._calculate_suspicion_score(const_name, const_value_node)

            # 最终审判
            suspicion_threshold = 5
            if score >= suspicion_threshold:
                violations.append(
                    Violation(
                        file_path=file_path,
                        line=node.lineno,
                        col=node.col_offset,
                        code=self.CODE_PC001,
                        message=self._msg_pc001.format(const_name=const_name),
                    )
                )

        return violations
