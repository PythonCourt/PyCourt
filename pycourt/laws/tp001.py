"""🏛️ 测试纯净度审查官（TP001）
简介
基于 AST/文本扫描的 Python 法条实现，统一纳入最高法院体系。

职责概览
- 纯净度审查：标记为 ``@pytest.mark.unit`` 的单元测试不得直接依赖 I/O 库
  （redis / sqlalchemy 等）；
- SQLAlchemy 白名单：仅允许在特定 infra/database 测试中直接导入 sqlalchemy；
- 真实度审查：拒绝仅做 "importlib + hasattr" 存在性检查而不调用实际行为的测试。

使用方式
- 通过 ``pycourt.judge.ChiefJustice`` 统一执行：

  >>> from pycourt.judge import ChiefJustice
  >>> cj = ChiefJustice()
  >>> violations = cj.conduct_audit("tests")  # 其中包含 TP001 的裁决

- 或在 CLI 中通过 ``--select TP001`` 仅执行本法条：

  $ python -m pycourt.judge tests --select TP001
"""

from __future__ import annotations

import ast
import fnmatch
import re
from pathlib import Path
from typing import Final

from pycourt.config.config import CourtConfig
from pycourt.utils import Violation


class TestPurityLawConstants:
    """命名空间常量：TP001/TP002/TP003 测试纯净度法条内部使用。"""

    CODE_TP001: Final[str] = "TP001"
    CODE_TP002: Final[str] = "TP002"
    CODE_TP003: Final[str] = "TP003"

    EXEMPT_KEY_TP001_SQLA_WHITELIST: Final[str] = "TP001_SQLA_WHITELIST"


# SQLAlchemy 相关测试文件白名单由 exempt.yaml 的 TP001_SQLA_WHITELIST 提供


class TheTestPurityLaw:
    """🏛️ 帝国测试纯净度审查官（TP001）。

    职责
    - 对 ``tests/`` 目录下的 ``test_*.py`` 文件执行测试纯净度与真实度审查；
    - 遵循集中豁免表提供的路径级豁免；
    - 仅依赖 AST 上游提供的 ``content`` / ``lines``，不执行任何运行时代码。
    """

    def __init__(self, config: CourtConfig) -> None:
        """构造函数接受 `CourtConfig`，当前阶段不读取额外配置字段。"""

        # 保留完整法典引用，便于读取 tp001 的 enabled / exempt_files 等配置
        self.config = config
        self.laws = config.laws
        self._msg_tp001: str = self.config.get_judge_template(
            TestPurityLawConstants.CODE_TP001
        )
        self._msg_tp002: str = self.config.get_judge_template(
            TestPurityLawConstants.CODE_TP002
        )
        self._msg_tp003: str = self.config.get_judge_template(
            TestPurityLawConstants.CODE_TP003
        )

    # =========================
    # 内部工具方法
    # =========================

    def _is_exempt(self, file_path: Path) -> bool:
        """根据集中豁免配置判断文件是否治外法权。"""

        # 这里仍统一按 TP001 维护整条测试纯净度法官的路径豁免
        patterns = self.config.get_exempt_files(TestPurityLawConstants.CODE_TP001)
        if not patterns:
            return False

        fp = file_path.as_posix()
        return any(fnmatch.fnmatch(fp, p) or fp.endswith(p) for p in patterns)

    def _is_test_file(self, file_path: Path) -> bool:
        """仅审查 tests/ 目录下的 test_*.py。"""

        if file_path.suffix != ".py":
            return False
        if not file_path.name.startswith("test_"):
            return False

        parts = set(file_path.parts)
        return "tests" in parts

    def _is_sqlalchemy_whitelisted(self, file_path: Path) -> bool:
        """判断当前测试文件是否在 SQLAlchemy 导入白名单中。

        白名单来源：exempt.yaml → TP001_SQLA_WHITELIST.files
        支持 fnmatch 通配模式与简单的 endswith 匹配，语义与其他法官保持一致。
        """

        fp = file_path.as_posix()
        patterns = self.config.get_exempt_files(
            TestPurityLawConstants.EXEMPT_KEY_TP001_SQLA_WHITELIST
        )
        if not patterns:
            return False
        return any(fnmatch.fnmatch(fp, p) or fp.endswith(p) for p in patterns)

    # =========================
    # 审查主流程
    # =========================

    def investigate(
        self,
        file_path: Path,
        content: str,
        lines: list[str],
        tree: ast.AST | None,
    ) -> list[Violation]:
        """审查单个测试文件的 I/O 纯净度与真实度 (TP001/TP002/TP003)。"""

        del tree  # 当前实现不依赖 AST 结构，仅做文本扫描

        violations: list[Violation] = []

        # 0. 法典总开关：若 tp001 被禁用，则直接跳过
        config = getattr(self.laws, "tp001", None)
        if config is not None and not getattr(config, "enabled", True):
            return violations

        # 1. 过滤范围：仅 tests/ 下的 test_*.py，且不在豁免清单中
        if not self._is_test_file(file_path) or self._is_exempt(file_path):
            return violations

        fp_str = file_path.as_posix()

        # 1. 纯净度审查：仅针对标记为 unit 的测试
        self._check_unit_purity(file_path, fp_str, content, lines, violations)

        # 1.5 SQLAlchemy 全局白名单审查（所有测试均适用）
        self._check_sqlalchemy_usage(file_path, fp_str, lines, violations)

        # 2. 真实度审查：importlib + hasattr 组合但缺少行为调用
        self._check_authenticity(content, lines, fp_str, violations)

        return violations

    def _check_unit_purity(
        self,
        file_path: Path,
        fp_str: str,
        content: str,
        lines: list[str],
        violations: list[Violation],
    ) -> None:
        """检查标记为 unit 的测试是否存在违禁 I/O 导入 (TP001)。"""

        del file_path

        if "@pytest.mark.unit" not in content:
            return

        forbidden_import_patterns: tuple[str, ...] = (
            "import redis",
            "from redis",
            "import sqlalchemy",
            "from sqlalchemy",
        )
        for lineno, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if any(pat in line for pat in forbidden_import_patterns):
                message = self._msg_tp001.format(
                    file=fp_str,
                    line=lineno,
                    import_stmt=stripped,
                )
                violations.append(
                    Violation(
                        file_path=Path(fp_str),
                        line=lineno,
                        col=0,
                        code=TestPurityLawConstants.CODE_TP001,
                        message=message,
                    )
                )

    def _check_sqlalchemy_usage(
        self,
        file_path: Path,
        fp_str: str,
        lines: list[str],
        violations: list[Violation],
    ) -> None:
        """检查非白名单测试中的 SQLAlchemy 导入 (TP002)。"""

        if self._is_sqlalchemy_whitelisted(file_path):
            return

        for lineno, line in enumerate(lines, 1):
            if "import sqlalchemy" in line or "from sqlalchemy" in line:
                stripped = line.strip()
                message = self._msg_tp002.format(
                    file=fp_str,
                    line=lineno,
                    import_stmt=stripped,
                )
                violations.append(
                    Violation(
                        file_path=file_path,
                        line=lineno,
                        col=0,
                        code=TestPurityLawConstants.CODE_TP002,
                        message=message,
                    )
                )

    def _check_authenticity(
        self,
        content: str,
        lines: list[str],
        fp_str: str,
        violations: list[Violation],
    ) -> None:
        """检查仅做存在性检查而缺少行为调用的伪覆盖测试 (TP003)。"""

        if "importlib.import_module" not in content or "hasattr(" not in content:
            return

        # 若源码中完全不存在 ".foo(" 这样的调用模式，认为高度可疑
        if re.search(r"\.\w+\(", content):
            return

        # 粗略选取第一处 importlib 或 hasattr 出现的行号作为定位
        line_no = 1
        for idx, line in enumerate(lines, 1):
            if "importlib.import_module" in line or "hasattr(" in line:
                line_no = idx
                break

        message = self._msg_tp003.format(
            file=fp_str,
            line=line_no,
        )
        violations.append(
            Violation(
                file_path=Path(fp_str),
                line=line_no,
                col=0,
                code=TestPurityLawConstants.CODE_TP003,
                message=message,
            )
        )
