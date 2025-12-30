"""🏛️ 灰色迷雾审查官（OU001）

本模块实现 OU001 法条，对裸 ``object`` 类型的使用进行静态审查，防止在核心
代码中出现毫无契约的 "灰色迷雾" 类型。

设计要点
- 仅依赖正则与 AST，不执行任何运行时代码；
- 所有违规信息均通过 `judges_text.yaml` 中的 OU001 模板渲染；
- 配置来源：
  - 集中豁免：`exempt.yaml` → `exemptions.OU001.files`；
  - 判决文案：`judges_text.yaml` → `judges.OU001.template`；
  - 函数级边界豁免策略由本模块内常量提供，不再通过 Court 契约字段暴露。
"""

from __future__ import annotations

import ast
import fnmatch
import re
from pathlib import Path
from typing import Final

from pycourt.config.config import CourtConfig
from pycourt.utils import Violation, normalize_patterns


class TheObjectUsageLaw:
    """🏛️ 灰色迷雾审查官 - 禁止使用裸 object 类型（OU001）。

    职责
    - 检测代码中的裸 ``object`` 类型使用，防止在核心代码中引入无契约的灰色类型；
    - 通过 boundary_function_allowlist 在少数边界函数中精细豁免 ``object`` 使用；
    - 建议在 core/dto 或 core/port 中定义明确的基类 / 协议接口替代裸 object。
    """

    # 由法典（YAML）提供 boundary_function_allowlist，移除硬编码映射

    CODE_OU001: Final[str] = "OU001"

    def __init__(self, config: CourtConfig) -> None:
        self.config = config
        self.laws = config.laws
        self._msg_ou001: str = self.config.get_judge_template(self.CODE_OU001)

    def _is_file_exempt(self, file_path: Path) -> bool:
        """根据 OU001.files 配置判断文件是否治外法权。"""

        patterns = normalize_patterns(self.config.get_exempt_files(self.CODE_OU001))
        fp_str = file_path.as_posix()
        return any(fnmatch.fnmatch(fp_str, p) or fp_str.endswith(p) for p in patterns)

    def _compute_boundary_ranges(
        self,
        file_path: Path,
        tree: ast.AST | None,
    ) -> list[tuple[int, int]]:
        """计算需要豁免 object 检查的边界函数范围。

        当前实现统一认为“不存在函数级边界豁免配置”，即返回空列表，
        逻辑上等价于“所有命中的 object 使用都参与审查”。如需在未来扩展，
        可以在本模块内引入私有配置模型或常量表，而无需修改 Court 契约。
        """

        _ = file_path, tree
        return []

    OBJECT_PATTERN: Final[str] = r"[:\->]\s*object\b|\[object\]"

    def _scan_lines_for_object_usage(
        self,
        *,
        file_path: Path,
        lines: list[str],
        boundary_ranges: list[tuple[int, int]],
    ) -> list[Violation]:
        """遍历文件内容，基于 OBJECT_PATTERN 正则产出 OU001 违规记录。"""

        pattern = self.OBJECT_PATTERN

        def _in_boundary(line_no: int) -> bool:
            return any(start <= line_no <= end for start, end in boundary_ranges)

        violations: list[Violation] = []
        for line_num, line in enumerate(lines, 1):
            if not re.search(pattern, line):
                continue
            if "class" in line and "object" in line:
                # 兼容 "class Foo(object):" 继承声明
                continue
            if _in_boundary(line_num):
                continue

            violations.append(
                Violation(
                    file_path=file_path,
                    line=line_num,
                    col=0,
                    code=self.CODE_OU001,
                    message=self._msg_ou001,
                )
            )

        return violations

    def investigate(
        self,
        file_path: Path,
        content: str,
        lines: list[str],
        tree: ast.AST | None,
    ) -> list[Violation]:
        """审查代码中的 object 类型使用（OU001）。

        检查范围
        - 通过正则匹配裸 ``object`` 使用，排除 ``class Foo(object):`` 等继承声明；
        - 目前不再支持函数级边界豁免，所有命中的 object 使用均纳入审查；
        - 仅在未被集中豁免表标记的文件上执法。

        执行步骤
        1. 读取 ``laws.ou001.enabled`` 配置，若为 False 则整体禁用；
        2. 根据集中豁免表（``exempt.yaml`` → ``OU001.files``）跳过特定文件；
        3. 在存在 AST 的情况下，计算需要豁免的函数范围（当前统一为空）；
        4. 遍历文件的每一行，使用 OBJECT_PATTERN 正则检测裸 object 使用：
           - 若该行位于边界函数范围内，则跳过；
           - 否则使用 OU001 模板产出违规记录。
        """

        # 该法官未直接使用 AST 树参数，显式删除以满足 Ruff ARG002
        del content

        # 🏛️ 规则驱动逻辑 - 检查是否启用
        config = self.laws.ou001
        if not getattr(config, "enabled", True):
            return []

        if self._is_file_exempt(file_path):
            return []

        boundary_ranges = self._compute_boundary_ranges(file_path, tree)
        return self._scan_lines_for_object_usage(
            file_path=file_path,
            lines=lines,
            boundary_ranges=boundary_ranges,
        )
