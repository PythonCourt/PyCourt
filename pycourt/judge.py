#!/usr/bin/env python3
"""
🏛️ PyCourt 首席大法官
"""

from __future__ import annotations

import argparse
import ast
import logging
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Final, Protocol

import pycourt.models as _qschemas
from pycourt.config.config import CourtConfig
from pycourt.config.judges_texts import get_courtroom_text, get_default_lang
from pycourt.laws.ac001 import TheAnyCastLaw
from pycourt.laws.bc001 import TheBndCtrlLaw
from pycourt.laws.di001 import TheDepInvLaw
from pycourt.laws.ds001 import TheDocsStringLaw
from pycourt.laws.dt001 import TheDateTimeLaw
from pycourt.laws.hc001 import TheHardcodingLaw
from pycourt.laws.ll001 import TheLineLoopLaw
from pycourt.laws.ou001 import TheObjectUsageLaw
from pycourt.laws.pc001 import TheParamClassLaw
from pycourt.laws.re001 import TheInitNoReExpLaw
from pycourt.laws.sk001 import TheSkillsUsageLaw
from pycourt.laws.tc001 import TheTypeCheckingLaw
from pycourt.laws.tp001 import TheTestPurityLaw
from pycourt.laws.uw001 import TheUnitOfWorkLaw
from pycourt.laws.vt001 import TheVectorTriggerLaw
from pycourt.loader import load_court_config
from pycourt.models import PyCourtLaws
from pycourt.utils import Violation, get_ast_tree, read_file_content

LOGGER_NAME = __name__
logger = logging.getLogger(LOGGER_NAME)


# =========================
# 首席大法官
# =========================


class _LawJudge(Protocol):
    """首席大法官使用的法官协议

    仅用于类型检查目的，约束每位法官都实现 ``investigate`` 接口。
    """

    def investigate(
        self,
        file_path: Path,
        content: str,
        lines: list[str],
        tree: ast.AST | None,
    ) -> list[Violation]:  # pragma: no cover - 类型检查辅助
        """检查单个文件并返回所有发现的违规项。"""
        ...


class ChiefJustice:
    """首席大法官：统筹唯一法官与全部法律条文，确保规则一体化。

    通过 `pycourt.load_court_config` 一次性接入：
    - laws: CourtLaws 结构法典；
    - texts / exemptions 等法院统一配置。
    """

    laws: PyCourtLaws
    config: CourtConfig

    EXCLUDED_DIRS: Final[tuple[str, ...]] = (
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "node_modules",
        "dist",
        "build",
        ".tox",
        ".idea",
        ".vscode",
    )

    def __init__(self) -> None:
        """初始化首席大法官，接入统一的配置加载入口。

        通过集中配置装载全部法条与文案，避免各处散落的 config loader。
        """
        # 1. 确保 Pydantic 前向引用已正确重建（兼容 Pyright/Mypy + Pydantic v2）
        _rebuilder = getattr(_qschemas.PyCourtLaws, "model_rebuild", None)
        if callable(_rebuilder):  # 运行时保护
            _rebuilder(_types_namespace=vars(_qschemas))

        # 2. 通过中央入口加载并验证最高法院总配置
        config: CourtConfig = load_court_config()

        # 3. 从总法典中获取按编号分组的法律总表
        laws: PyCourtLaws = config.laws
        self.laws = laws
        self.config = config

        # 5. 动态导入所有法律（避免循环导入）

        # 6. 大法官的初始化：唯一法官 + 多条法律
        self.judge: list[_LawJudge] = [
            TheDepInvLaw(self.config),
            TheUnitOfWorkLaw(self.config),
            TheHardcodingLaw(self.config),
            TheAnyCastLaw(self.config),
            TheLineLoopLaw(self.config),
            TheDocsStringLaw(self.config),
            TheBndCtrlLaw(self.config),
            TheObjectUsageLaw(self.config),
            TheTypeCheckingLaw(self.config),
            TheParamClassLaw(self.config),
            TheSkillsUsageLaw(self.config),
            TheInitNoReExpLaw(self.config),
            TheDateTimeLaw(self.config),
            TheTestPurityLaw(self.config),
            TheVectorTriggerLaw(self.config),
        ]

    def conduct_audit(self, target_dir: str) -> list[Violation]:
        """
        执行对目标目录的全量审查，汇总并返回全部违规记录。
        """

        # 1. 准备工作：初始化违规列表
        violations: list[Violation] = []
        target_path = Path(target_dir)
        file_iter: Iterable[Path]
        if target_path.is_file() and target_path.suffix == ".py":
            file_iter = [target_path]
        else:
            file_iter = target_path.rglob("*.py")

        for file_path in file_iter:
            parts = set(file_path.parts)
            if any(ex in parts for ex in self.EXCLUDED_DIRS):
                continue
            content, lines = read_file_content(file_path)
            if not content:
                continue

            tree = get_ast_tree(content, str(file_path))

            for judge in self.judge:
                violations.extend(judge.investigate(file_path, content, lines, tree))

        return violations


def main() -> None:
    """🏛️ PyCourt 最高法院 - 主程序入口"""

    parser = argparse.ArgumentParser(description="PyCourt 最高法院 - 代码合规审查")
    parser.add_argument("target_dir", help="要审查的目录")
    parser.add_argument(
        "--select",
        help="仅审查指定的违宪代码 (例如: BC001,AC001)。默认为全部审查。",
        default=None,
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    args = parser.parse_args()

    # 启用 INFO 日志当提供详细标志时，并统一使用 PyCourt 前缀。
    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="PyCourt:%(message)s")

    selected_codes = set(args.select.split(",")) if args.select else None

    lang = get_default_lang()

    court = ChiefJustice()
    violations = court.conduct_audit(args.target_dir)

    if selected_codes:
        violations = [v for v in violations if v.code in selected_codes]

    if violations:
        logger.error(
            get_courtroom_text("supreme_court.summary_failed", lang=lang).format(
                count=len(violations)
            )
        )
        for v in violations:
            logger.error("  %s", v)
        sys.exit(1)
    else:
        logger.info(get_courtroom_text("supreme_court.summary_passed", lang=lang))
        sys.exit(0)


if __name__ == "__main__":
    main()

__all__ = ["ChiefJustice"]
