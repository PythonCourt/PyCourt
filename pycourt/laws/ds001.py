"""🏛️ 文档字符串审查官（Docstring Law）

- DS001: 公开函数必须提供 docstring；
- DS002: 类必须提供且满足最小长度的 docstring。

设计要点
- 仅依赖 AST 与静态分析，不执行任何运行时代码；
- 所有违规信息均通过 `judges_text.yaml` 中的 DS001/DS002 模板渲染；
- 配置来源：
  - `laws.yaml` → `laws.ds001`: enabled / min_docstring_length 等法条参数；
  - `exempt.yaml` → `exemptions.DS001.files`: 路径/文件级豁免（治外法权）。
"""

from __future__ import annotations

import ast
import fnmatch
from pathlib import Path
from typing import Final

from pycourt.config.config import CourtConfig
from pycourt.utils import Violation, normalize_patterns


class DocsStringLawConstants:
    """DS001/DS002 内部使用的常量集合。"""

    MIN_DOCSTRING_LENGTH_DEFAULT: Final[int] = 20


class TheDocsStringLaw:
    """🏛️ 文档字符串审查官 - 统一管理 DS001/DS002 两条法案。

    职责
    - DS001: 检测公开函数（不以 ``_`` 开头，包括同步/异步函数）是否缺少 docstring；
    - DS002: 检测类 docstring 是否缺失或长度小于法典规定阈值；
    - 通过同一法典 ``ds001`` 驱动（enabled / min_docstring_length），
      并通过集中豁免表 ``exempt.yaml → DS001.files`` 管理路径级治外法权。
    """

    CODE_DS001: Final[str] = "DS001"  # 函数缺少 docstring
    CODE_DS002: Final[str] = "DS002"  # 类 docstring 过短/缺失

    def __init__(self, config: CourtConfig) -> None:
        """接入 CourtConfig，初始化法典与判决文案。"""

        self.config = config
        self.laws = config.laws
        self._msg_ds001: str = self.config.get_judge_template(self.CODE_DS001)
        self._msg_ds002: str = self.config.get_judge_template(self.CODE_DS002)

    def investigate(
        self, file_path: Path, content: str, lines: list[str], tree: ast.AST | None
    ) -> list[Violation]:
        """审查函数与类的 docstring 合规性（DS001/DS002）。

        检查范围
        - DS001: 所有公开函数（不以 ``_`` 开头，包含 ``def`` 与 ``async def``）；
        - DS002: 所有类定义的 docstring 是否存在且长度满足最小要求。

        执行步骤
        1. 读取 ``laws.ds001.enabled`` 配置，若为 False 则整体禁用；
        2. 根据集中豁免表（``exempt.yaml`` → ``DS001.files``）跳过特定文件；
        3. 若 AST 缺失则直接返回空结果；
        4. 遍历 AST：
           - 对函数节点执行 DS001 检查；
           - 对类节点执行 DS002 检查；
        5. 汇总并返回所有 :class:`Violation` 实例。
        """
        violations: list[Violation] = []
        # 抑制未使用参数警告，对于本实现中未使用的参数
        del content, lines

        law_cfg = self.laws.ds001
        if not getattr(law_cfg, "enabled", True):
            return violations

        if self._is_file_exempt(file_path):
            return violations

        min_length = DocsStringLawConstants.MIN_DOCSTRING_LENGTH_DEFAULT

        if tree is None:
            return violations

        violations.extend(
            self._collect_docstring_violations(
                file_path=file_path,
                tree=tree,
                min_length=min_length,
            )
        )

        return violations

    def _is_file_exempt(self, file_path: Path) -> bool:
        """返回给定文件是否被 DS001 豁免。

        路径/文件级豁免统一由集中豁免表管理，
        依然保持原先的 ``fnmatch`` + ``endswith`` 匹配语义。
        """
        patterns = normalize_patterns(self.config.get_exempt_files(self.CODE_DS001))
        fp_str = file_path.as_posix()
        return any(fnmatch.fnmatch(fp_str, p) or fp_str.endswith(p) for p in patterns)

    def _collect_docstring_violations(
        self, *, file_path: Path, tree: ast.AST, min_length: int
    ) -> list[Violation]:
        """从 AST 中收集 DS001/DS002 相关违规信息。"""
        violations: list[Violation] = []
        for node in ast.walk(tree):
            # DS001: 公开函数必须有 docstring（同步/异步统一处理）
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and not node.name.startswith("_")
                and not ast.get_docstring(node)
            ):
                violations.append(
                    Violation(
                        file_path=file_path,
                        line=node.lineno,
                        col=0,
                        code=self.CODE_DS001,
                        message=self._msg_ds001.format(func=node.name),
                    )
                )

            # DS002: 类 docstring 必须存在且长度达到阈值
            if isinstance(node, ast.ClassDef):
                docstring = ast.get_docstring(node)
                if not docstring or len(docstring.strip()) < min_length:
                    violations.append(
                        Violation(
                            file_path=file_path,
                            line=node.lineno,
                            col=0,
                            code=self.CODE_DS002,
                            message=self._msg_ds002.format(
                                klass=node.name,
                                min_len=min_length,
                            ),
                        )
                    )

        return violations
