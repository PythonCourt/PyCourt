"""🏛️ [门面纪律法官] Init Discipline Law (RE001/RE002/RE003)

职责：
- 专门审查所有 __init__.py 文件是否只承担“前台名片”的职责；
- 禁止在 __init__.py 中堆砌业务逻辑或复杂控制流；
- 限制 __init__.py 的行数，避免成为“第二个模块实现”。
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Final

from pycourt.config.config import CourtConfig
from pycourt.utils import Violation


class InitDisciplineConstants:
    """RE001 门面纪律法官内部使用的常量集合。"""

    MAX_INIT_CODE_LINES_DEFAULT: Final[int] = 10


def _is_docstring_only_module(tree: ast.AST | None) -> bool:
    """判断模块是否只包含文档字符串（允许长文档型 __init__）.

    - 允许：仅由模块级字符串常量组成的 __init__（即纯文档说明）。
    - 不允许：出现任何其它语句（导入、赋值、函数/类定义、控制流等）。
    """

    if tree is None or not isinstance(tree, ast.Module):  # 解析失败时保持保守
        return False

    for node in tree.body:
        # 典型的模块 docstring: Expr(Constant(str))
        if isinstance(node, ast.Expr):
            value = node.value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                continue
        return False

    return True


class TheInitNoReExpLaw:
    """🏛️ 门面纪律法官 - 确保 __init__.py 保持精简

    职责：
    - RE001: 检查 __init__.py 行数是否超过限制（默认 10 行）。
    - RE002: 禁止在 __init__.py 中定义函数、类或异步函数。
    - RE003: 禁止在 __init__.py 中使用复杂控制流或相对导入聚合。
    """

    CODE_RE001: Final[str] = "RE001"
    CODE_RE002: Final[str] = "RE002"
    CODE_RE003: Final[str] = "RE003"

    def __init__(self, config: CourtConfig) -> None:
        self.config = config
        self.laws = config.laws
        self._msg_re001: str = self.config.get_judge_template(self.CODE_RE001)
        self._msg_re002: str = self.config.get_judge_template(self.CODE_RE002)
        self._msg_re003: str = self.config.get_judge_template(self.CODE_RE003)

    def investigate(
        self, file_path: Path, content: str, lines: list[str], tree: ast.AST | None
    ) -> list[Violation]:
        """审查单个 __init__.py 文件是否违反门面纪律。"""

        # content 当前未参与检查逻辑，显式标记为已使用以满足 Ruff ARG002。
        del content

        # 1. 验明正身：只审判 __init__.py
        if file_path.name != "__init__.py":
            return []

        # 2. 若是“纯文档型门面”，则完全放行
        #    允许在 __init__.py 中书写较长的包说明文档，而不受行数限制。
        if _is_docstring_only_module(tree):
            return []

        violations: list[Violation] = []
        violations.extend(self._check_init_line_limits(file_path, lines, tree))

        # 4. AST 审判：禁止在门面写业务逻辑 / 聚合导出
        if tree is None:
            return violations

        violations.extend(self._check_ast_facade_rules(file_path, tree))
        return violations

    def _check_init_line_limits(
        self, file_path: Path, lines: list[str], tree: ast.AST | None
    ) -> list[Violation]:
        """执行 RE001：检查 __init__.py 的有效代码行数是否超限。"""

        violations: list[Violation] = []
        # RE001 的最大行数阈值由本模块内部常量提供，不再通过 LawsRE001 暴露。
        max_init_lines = InitDisciplineConstants.MAX_INIT_CODE_LINES_DEFAULT

        code_line_count = len(lines)
        if isinstance(tree, ast.Module) and tree.body:
            first_stmt = tree.body[0]
            # 如果首个语句是模块级 docstring，则扣除其覆盖的行数
            if isinstance(first_stmt, ast.Expr):
                value = first_stmt.value
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    doc_start = getattr(first_stmt, "lineno", 1)
                    doc_end = getattr(first_stmt, "end_lineno", doc_start)
                    # 仅当 docstring 覆盖自文件开头时，才认为是“模块头部文档”
                    if doc_start == 1:
                        covered = max(0, int(doc_end))
                        code_line_count = max(0, len(lines) - covered)

        if code_line_count > max_init_lines:
            violations.append(
                Violation(
                    file_path=file_path,
                    line=max_init_lines + 1,
                    col=0,
                    code=self.CODE_RE001,
                    message=self._msg_re001.format(
                        code_line_count=code_line_count,
                        max_init_lines=max_init_lines,
                    ),
                ),
            )

        return violations

    def _check_ast_facade_rules(
        self, file_path: Path, tree: ast.AST
    ) -> list[Violation]:
        """执行 RE002/RE003：基于 AST 的门面结构约束。"""

        violations: list[Violation] = []

        for node in ast.walk(tree):
            violations.extend(self._check_forbidden_defs(file_path, node))
            violations.extend(self._check_forbidden_control_flow(file_path, node))
            violations.extend(self._check_forbidden_relative_import(file_path, node))
            violations.extend(self._check_forbidden_all_assignment(file_path, node))

        return violations

    def _check_forbidden_defs(self, file_path: Path, node: ast.AST) -> list[Violation]:
        """4.1 禁止在门面中定义函数、类或异步函数（业务逻辑）。"""

        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            return []

        return [
            Violation(
                file_path=file_path,
                line=node.lineno,
                col=node.col_offset,
                code=self.CODE_RE002,
                message=self._msg_re002.format(node_type=type(node).__name__),
            )
        ]

    def _check_forbidden_control_flow(
        self, file_path: Path, node: ast.AST
    ) -> list[Violation]:
        """4.2 禁止复杂控制流（for/while/try）。"""

        if not isinstance(node, ast.For | ast.While | ast.Try):
            return []

        return [
            Violation(
                file_path=file_path,
                line=node.lineno,
                col=node.col_offset,
                code=self.CODE_RE003,
                message=self._msg_re003.format(detail="控制流语句 (for/while/try)"),
            )
        ]

    def _check_forbidden_relative_import(
        self, file_path: Path, node: ast.AST
    ) -> list[Violation]:
        """4.3 禁止相对导入用于聚合导出。"""

        if not (isinstance(node, ast.ImportFrom) and getattr(node, "level", 0) > 0):
            return []

        return [
            Violation(
                file_path=file_path,
                line=node.lineno,
                col=node.col_offset,
                code=self.CODE_RE003,
                message=self._msg_re003.format(detail="相对导入用于聚合导出"),
            )
        ]

    def _check_forbidden_all_assignment(
        self, file_path: Path, node: ast.AST
    ) -> list[Violation]:
        """4.4 禁止通过 __all__ 做聚合导出控制。"""

        if not isinstance(node, ast.Assign | ast.AugAssign | ast.AnnAssign):
            return []

        if isinstance(node, ast.Assign):
            targets: list[ast.expr] = list(node.targets)
        else:
            targets = [node.target]

        for target in targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                return [
                    Violation(
                        file_path=file_path,
                        line=node.lineno,
                        col=node.col_offset,
                        code=self.CODE_RE003,
                        message=self._msg_re003.format(
                            detail="通过 __all__ 聚合子模块符号",
                        ),
                    )
                ]

        return []
