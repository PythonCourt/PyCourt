"""
🏛️ 循环依赖审查官 (TC001)

职责：在全仓代码中，严格禁止任何形式的 `TYPE_CHECKING:` 结构，
以根除通过类型存根别名来掩盖循环依赖的违法行为。
"""

from __future__ import annotations

import ast
import fnmatch
from pathlib import Path
from typing import Final

from pycourt.config.config import CourtConfig
from pycourt.utils import Violation, normalize_patterns


class TypeCheckingLawConstants:
    """命名空间常量：TC001 循环依赖审查法条内部使用。"""

    CODE_TC001: Final[str] = "TC001"


class TheTypeCheckingLaw:
    """🏛️ 循环依赖审查官

    职责：在全仓代码中，严格禁止任何形式的 `TYPE_CHECKING:` 结构，
    以根除通过类型存根别名来掩盖循环依赖的违法行为。
    """

    def __init__(self, config: CourtConfig) -> None:
        """接入集中法典配置。"""

        self.config = config
        self.laws = config.laws
        self._msg_tc001: str = self.config.get_judge_template(
            TypeCheckingLawConstants.CODE_TC001
        )

    def investigate(
        self, file_path: Path, content: str, lines: list[str], tree: ast.AST | None
    ) -> list[Violation]:
        """扫描源码内容，查找 'if TYPE_CHECKING:' 的使用。"""
        violations: list[Violation] = []
        # 该法官不使用 AST，显式删除
        del tree

        # 规则驱动逻辑 - 从法典获取规则
        config = self.laws.tc001
        if not config.enabled:
            return violations

        # 文件级豁免
        patterns = normalize_patterns(
            self.config.get_exempt_files(TypeCheckingLawConstants.CODE_TC001)
        )
        fp_str = str(file_path)
        if any(
            fnmatch.fnmatch(fp_str, pattern) or fp_str.endswith(pattern)
            for pattern in patterns
        ):
            return []

        # 核心审查逻辑：极其简单和高效
        # 最严格模式：任何出现 TYPE_CHECKING 的地方一律视为违规，
        # 无论是导入、条件判断还是注释中的使用。
        if "TYPE_CHECKING" in content:
            for line_num, line in enumerate(lines, 1):
                if "TYPE_CHECKING" in line:
                    violations.append(
                        Violation(
                            file_path=file_path,
                            line=line_num,
                            col=line.find("TYPE_CHECKING"),
                            code=TypeCheckingLawConstants.CODE_TC001,
                            message=self._msg_tc001,
                        )
                    )
        return violations
