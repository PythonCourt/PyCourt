"""🏛️ [时间法官] DateTimeNow Abuse Inquisitor (DT001)

职责：
- 在全仓范围内禁止直接使用 ``datetime.now()`` 和 ``datetime.utcnow()``；
- 强制所有时间获取通过 TimeProvider/UTC 统一入口完成；
- 为未来的 TimeTown/虚拟时间预留演进空间。

实现策略：
- 简单基于源码文本扫描，避免过度依赖 AST；
- 忽略注释行和字符串字面量内的匹配；
- 只对真正的代码行中出现的调用进行裁决。
"""

from __future__ import annotations

import ast
import fnmatch
from pathlib import Path
from typing import Final

from pycourt.config.config import CourtConfig
from pycourt.utils import Violation, normalize_patterns


class DateTimeLawConstants:
    """命名空间常量：DT001 时间法官法条内部使用。"""

    CODE_DT001: Final[str] = "DT001"


class TheDateTimeLaw:
    """🏛️ **[时间法官]** 禁止 datetime.now()/utcnow 滥用的审查官"""

    def __init__(self, config: CourtConfig) -> None:
        self.config = config
        self.laws = config.laws
        self._msg_dt001: str = self.config.get_judge_template(
            DateTimeLawConstants.CODE_DT001
        )

    def investigate(
        self,
        file_path: Path,
        content: str,
        lines: list[str],
        tree: ast.AST | None,
    ) -> list[Violation]:
        """审查单个 Python 源文件中对 datetime.now()/utcnow() 的直接调用。"""

        if not self._is_enabled():
            return []

        if self._is_file_exempt(file_path):
            return []

        if "datetime" not in content:
            return []

        if tree is not None:
            return self._collect_violations_from_ast(
                file_path=file_path,
                lines=lines,
                tree=tree,
            )

        return self._collect_violations_from_text(
            file_path=file_path,
            lines=lines,
        )

    def _is_enabled(self) -> bool:
        """返回 DT001 是否开启。

        通过 ``laws.dt001.enabled`` 控制整体开关，缺省视为启用。
        """

        config = self.laws.dt001
        return bool(getattr(config, "enabled", True))

    def _is_file_exempt(self, file_path: Path) -> bool:
        """根据集中豁免表判断文件是否免于 DT001 审查。"""

        patterns = normalize_patterns(
            self.config.get_exempt_files(DateTimeLawConstants.CODE_DT001)
        )
        path_str = str(file_path)
        return any(
            fnmatch.fnmatch(path_str, pattern) or path_str.endswith(pattern)
            for pattern in patterns
        )

    def _collect_violations_from_ast(
        self,
        *,
        file_path: Path,
        lines: list[str],
        tree: ast.AST,
    ) -> list[Violation]:
        """使用 AST 精确识别 datetime.now()/utcnow() 调用位置。"""

        violations: list[Violation] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute):
                continue
            if not isinstance(func.value, ast.Name):
                continue
            if func.value.id != "datetime":
                continue
            if func.attr not in ("now", "utcnow"):
                continue

            lineno = node.lineno
            col = node.col_offset
            if 1 <= lineno <= len(lines):
                line = lines[lineno - 1]
                idx = line.find("datetime")
                if idx >= 0:
                    col = idx

            violations.append(
                Violation(
                    file_path=file_path,
                    line=lineno,
                    col=col,
                    code=DateTimeLawConstants.CODE_DT001,
                    message=self._msg_dt001,
                )
            )

        return violations

    def _collect_violations_from_text(
        self,
        *,
        file_path: Path,
        lines: list[str],
    ) -> list[Violation]:
        """在 AST 不可用时退化为按行文本扫描。"""

        violations: list[Violation] = []

        for lineno, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            if "datetime.now(" in stripped or "datetime.utcnow(" in stripped:
                col = stripped.find("datetime.")
                col = max(col, 0)
                violations.append(
                    Violation(
                        file_path=file_path,
                        line=lineno,
                        col=col,
                        code=DateTimeLawConstants.CODE_DT001,
                        message=self._msg_dt001,
                    )
                )

        return violations
