"""🏛️ 过度复杂审查官 (LL001/LL002)

本模块实现 LL 系列法条中关于函数长度与圈复杂度的静态审查：
- LL001: 检测函数行数是否超过限制；
- LL002: 检测函数圈复杂度是否超过限制。

设计要点
- 仅依赖 AST 与静态分析，不执行任何运行时代码；
- 所有违规信息均通过 `judges_text.yaml` 中的 LL001/LL002 模板渲染；
- 配置来源：
  - `laws.yaml` → `laws.ll001`: 函数最大行数与最大复杂度阈值等参数；
  - `exempt.yaml` → `exemptions.LL001.files`: 路径/文件级豁免（治外法权）。
"""

from __future__ import annotations

import ast
import fnmatch
from pathlib import Path
from typing import Final, Protocol

from pycourt.config.config import CourtConfig
from pycourt.utils import Violation, normalize_patterns


class _LLConfigLike(Protocol):
    """最小 LL001 配置协定，仅包含本法官实际使用的字段。

    通过 Protocol 避免直接依赖完整 LawsLL001 契约类型，
    同时满足类型系统与 OU001 对 object 的约束。

    注意：
    - 当前 LawsLL001 仅声明 enabled/exempt_files/description，
      因此本 Protocol 只要求 enabled 属性；
    - max_function_lines / max_complexity 作为可选覆盖字段，
      通过 getattr(config, "max_function_lines", ...) 形式获取，
      不需要出现在 Protocol 中。
    """

    enabled: bool


class LineLoopLawConstants:
    """命名空间常量：LL001/LL002 复杂度法条内部使用。"""

    CODE_LL001: Final[str] = "LL001"
    CODE_LL002: Final[str] = "LL002"

    # 过度复杂审查的默认阈值（原 ll001 配置从 YAML 迁移至代码内常量）
    MAX_FUNCTION_LINES_DEFAULT: Final[int] = 50
    MAX_COMPLEXITY_DEFAULT: Final[int] = 10


class TheLineLoopLaw:
    """🏛️ 过度复杂审查官 - LL001/LL002 合并实现。

    职责
    - LL001: 检测函数行数是否超过限制；
    - LL002: 检测函数圈复杂度是否超过限制；
    - 通过同一法典 ``ll001`` 驱动（最大行数、最大复杂度等参数），
      并通过集中豁免表 ``exempt.yaml → LL001.files`` 管理路径级治外法权。
    """

    def __init__(self, config: CourtConfig) -> None:
        self.config = config
        self.laws = config.laws
        self._msg_ll001: str = self.config.get_judge_template(
            LineLoopLawConstants.CODE_LL001
        )
        self._msg_ll002: str = self.config.get_judge_template(
            LineLoopLawConstants.CODE_LL002
        )

    def investigate(
        self, file_path: Path, content: str, lines: list[str], tree: ast.AST | None
    ) -> list[Violation]:
        """遍历 AST 中的函数定义，按 LL001/LL002 规则产出违规。

        检查范围
        - 目标：所有函数定义（同步/异步，包含方法/内部函数等）；
        - LL001: 使用 ``max_function_lines`` 作为函数最大允许行数；
        - LL002: 使用 ``max_complexity`` 作为圈复杂度上限。
        """
        violations: list[Violation] = []
        # 抑制未使用参数警告，对于本实现中未使用的参数
        del content, lines

        config = self.laws.ll001
        if not getattr(config, "enabled", True):
            return violations

        if self._is_file_exempt(file_path):
            return violations

        if tree is None:
            return violations

        max_func_lines, max_complexity = self._resolve_limits(config)

        for func_node in self._iter_function_nodes(tree):
            self._check_function_limits(
                func_node=func_node,
                file_path=file_path,
                max_func_lines=max_func_lines,
                max_complexity=max_complexity,
                violations=violations,
            )

        return violations

    def _is_file_exempt(self, file_path: Path) -> bool:
        """基于集中豁免表判断文件是否豁免 LL001/LL002 审查。"""
        patterns = normalize_patterns(
            self.config.get_exempt_files(LineLoopLawConstants.CODE_LL001)
        )
        fp_str = file_path.as_posix()
        return any(fnmatch.fnmatch(fp_str, p) or fp_str.endswith(p) for p in patterns)

    def _resolve_limits(self, config: _LLConfigLike) -> tuple[int, int]:
        """从配置与默认值中解析函数行数与复杂度阈值。

        约定：
        - LL 系列的具体阈值由本模块内常量提供；
        - `laws.ll001` 契约不再声明 max_function_lines/max_complexity，
          这里只通过 getattr 读取“可选覆盖”，不存在时回退到常量默认值。
        """
        max_func_lines = getattr(
            config,
            "max_function_lines",
            LineLoopLawConstants.MAX_FUNCTION_LINES_DEFAULT,
        )
        max_complexity = getattr(
            config,
            "max_complexity",
            LineLoopLawConstants.MAX_COMPLEXITY_DEFAULT,
        )
        return max_func_lines, max_complexity

    def _iter_function_nodes(
        self, tree: ast.AST
    ) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
        """遍历 AST，收集所有函数/方法定义节点。"""
        return [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]

    def _check_function_limits(
        self,
        *,
        func_node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_path: Path,
        max_func_lines: int,
        max_complexity: int,
        violations: list[Violation],
    ) -> None:
        """对单个函数同时应用 LL001 与 LL002 审查。"""
        self._check_function_length(
            func_node=func_node,
            file_path=file_path,
            max_func_lines=max_func_lines,
            violations=violations,
        )
        self._check_function_complexity(
            func_node=func_node,
            file_path=file_path,
            max_complexity=max_complexity,
            violations=violations,
        )

    def _check_function_length(
        self,
        *,
        func_node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_path: Path,
        max_func_lines: int,
        violations: list[Violation],
    ) -> None:
        """应用 LL001：函数行数审查。"""
        if not hasattr(func_node, "end_lineno") or not func_node.end_lineno:
            return

        func_lines = func_node.end_lineno - func_node.lineno
        if func_lines <= max_func_lines:
            return

        violations.append(
            Violation(
                file_path=file_path,
                line=func_node.lineno,
                col=0,
                code=LineLoopLawConstants.CODE_LL001,
                message=self._msg_ll001.format(
                    func=func_node.name,
                    lines=func_lines,
                    limit=max_func_lines,
                ),
            )
        )

    def _check_function_complexity(
        self,
        *,
        func_node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_path: Path,
        max_complexity: int,
        violations: list[Violation],
    ) -> None:
        """应用 LL002：圈复杂度审查。"""
        complexity = self._calculate_complexity(func_node)
        if complexity <= max_complexity:
            return

        violations.append(
            Violation(
                file_path=file_path,
                line=func_node.lineno,
                col=0,
                code=LineLoopLawConstants.CODE_LL002,
                message=self._msg_ll002.format(
                    func=func_node.name,
                    complexity=complexity,
                    limit=max_complexity,
                ),
            )
        )

    def _calculate_complexity(self, func_node: ast.AST) -> int:
        """计算函数的圈复杂度（支持同步/异步函数节点）。"""
        complexity = 1  # 基础复杂度
        for node in ast.walk(func_node):
            if isinstance(
                node, ast.If | ast.While | ast.For | ast.AsyncFor | ast.ExceptHandler
            ):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
        return complexity
