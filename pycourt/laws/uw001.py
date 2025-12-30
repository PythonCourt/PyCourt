"""🏛️ Unit of Work 法官 (UW001/UW002/UW003)

职责：
1. UW001: 禁止胶囊发行链路使用 RepositoryFactory
2. UW002: 禁止 business repositories 内部调用 commit()
3. UW003: 禁止 business repositories 内部调用 rollback()

立法目的：
- UoW 的原子性必须由 UnitOfWork 控制
- business repositories 必须是 flush-only
- commit/rollback 的唯一合法入口是 UnitOfWork
"""

from __future__ import annotations

import ast
import fnmatch
from pathlib import Path
from typing import Final

from pycourt.config.config import CourtConfig
from pycourt.utils import Violation, find_project_root, normalize_patterns


class UnitOfWorkLawConstants:
    """命名空间常量：UW001–UW004 UoW 法条内部使用。"""

    CODE_UW001: Final[str] = "UW001"
    CODE_UW002: Final[str] = "UW002"
    CODE_UW003: Final[str] = "UW003"
    CODE_UW004: Final[str] = "UW004"


_FORBIDDEN_REPO_FACTORY_METHODS: Final[set[str]] = {
    "create_time_capsule_repository",
    "create_time_capsule_edge_repository",
    "create_capsule_raw_memory_map",
    "create_capsule_asset_store",
}


class TheUnitOfWorkLaw:
    """🏛️ Unit of Work 法官 (UW001/UW002/UW003)

    备注：
    - 本法官不依赖 quality.yaml 开关：UW 系列属于系统级强制法条。
    """

    def __init__(self, config: CourtConfig) -> None:
        self.config = config
        self.laws = config.laws
        self._msg_uw001: str = self.config.get_judge_template(
            UnitOfWorkLawConstants.CODE_UW001
        )
        self._msg_uw002: str = self.config.get_judge_template(
            UnitOfWorkLawConstants.CODE_UW002
        )
        self._msg_uw003: str = self.config.get_judge_template(
            UnitOfWorkLawConstants.CODE_UW003
        )
        self._msg_uw004: str = self.config.get_judge_template(
            UnitOfWorkLawConstants.CODE_UW004
        )

    def _check_repo_factory_usage(
        self, file_path: Path, tree: ast.AST
    ) -> list[Violation]:
        """UW001: 检查胶囊发行链路是否使用了 RepositoryFactory"""
        violations: list[Violation] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute):
                continue

            method = func.attr
            if method not in _FORBIDDEN_REPO_FACTORY_METHODS:
                continue

            violations.append(
                Violation(
                    file_path=file_path,
                    line=getattr(node, "lineno", 1),
                    col=getattr(node, "col_offset", 0),
                    code=UnitOfWorkLawConstants.CODE_UW001,
                    message=self._msg_uw001.format(method=method),
                )
            )

        return violations

    def _check_uow_time_capsule_bypass(
        self, file_path: Path, tree: ast.AST
    ) -> list[Violation]:
        """UW004: 禁止业务层直接调用 uow.repos.time_capsule.* 绕过发行官。"""

        violations: list[Violation] = []

        forbidden_methods: set[str] = {
            "create",
            "get_by_dedupe_key",
            "issue_session_slice",
        }

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            func = node.func
            if not isinstance(func, ast.Attribute):
                continue

            if func.attr not in forbidden_methods:
                continue

            # Match: <something>.repos.time_capsule.<method>(...)
            v = func.value
            if not isinstance(v, ast.Attribute):
                continue
            if v.attr != "time_capsule":
                continue

            vv = v.value
            if not isinstance(vv, ast.Attribute):
                continue
            if vv.attr != "repos":
                continue

            violations.append(
                Violation(
                    file_path=file_path,
                    line=getattr(node, "lineno", 1),
                    col=getattr(node, "col_offset", 0),
                    code=UnitOfWorkLawConstants.CODE_UW004,
                    message=self._msg_uw004,
                )
            )

        return violations

    def _check_forbidden_method_in_repo(
        self, file_path: Path, tree: ast.AST, method_name: str, code: str, message: str
    ) -> list[Violation]:
        """检查 repositories 内是否出现禁止的方法调用"""
        violations: list[Violation] = []

        p = file_path.as_posix()

        # 审查 infra database repositories（排除 system 子目录）
        uw_cfg = getattr(self.config, "uw", None)
        if uw_cfg is None:
            return []

        infra_repo_subpath = uw_cfg.infra_repo_subpath
        infra_system_repo_subpath = uw_cfg.infra_system_repo_subpath

        is_in_infra_repo = f"/{infra_repo_subpath}" in p
        is_in_system_repo = f"/{infra_system_repo_subpath}" in p
        if not is_in_infra_repo or is_in_system_repo:
            return []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            func = node.func
            if not isinstance(func, ast.Attribute):
                continue

            if func.attr != method_name:
                continue

            violations.append(
                Violation(
                    file_path=file_path,
                    line=getattr(node, "lineno", 1),
                    col=getattr(node, "col_offset", 0),
                    code=code,
                    message=message,
                )
            )

        return violations

    def investigate(
        self, file_path: Path, content: str, lines: list[str], tree: ast.AST | None
    ) -> list[Violation]:
        """执行 UoW 相关审查（UW001–UW004）。"""

        del content, lines

        if tree is None:
            return []
        if not self._is_main_app_file(file_path):
            return []
        if not self._is_uw_enabled():
            return []
        if self._is_exempt_file(file_path):
            return []

        violations: list[Violation] = []
        self._apply_all_uow_checks(
            file_path=file_path, tree=tree, violations=violations
        )
        return violations

    def _is_main_app_file(self, file_path: Path) -> bool:
        """仅对主应用代码生效（工具/测试/迁移脚本等默认不在审查范围内）。"""

        try:
            project_root = find_project_root()
        except FileNotFoundError:
            return False

        try:
            rel = file_path.resolve().relative_to(project_root)
        except ValueError:
            return False

        parts = rel.parts
        if not parts:
            return False

        # 常见的非主应用顶层目录
        return parts[0] not in {"tools", "tests", "alembic"}

    def _is_uw_enabled(self) -> bool:
        """检查 UoW 法条是否在集中法典中启用。"""

        config = self.laws.uw001
        return getattr(config, "enabled", True)

    def _is_exempt_file(self, file_path: Path) -> bool:
        """根据集中豁免表判断文件是否治外法权。"""

        fp_str = file_path.as_posix()
        patterns = normalize_patterns(
            self.config.get_exempt_files(UnitOfWorkLawConstants.CODE_UW001)
        )
        return any(fnmatch.fnmatch(fp_str, p) or fp_str.endswith(p) for p in patterns)

    def _apply_all_uow_checks(
        self,
        *,
        file_path: Path,
        tree: ast.AST,
        violations: list[Violation],
    ) -> None:
        """依次应用所有 UoW 相关检查，将结果写入 violations 列表。"""

        # UW001: RepositoryFactory 禁令
        violations.extend(self._check_repo_factory_usage(file_path, tree))

        # UW004: 禁止绕过发行官直接触碰 uow.repos.time_capsule.*
        violations.extend(self._check_uow_time_capsule_bypass(file_path, tree))

        # UW002: commit() 禁令
        violations.extend(
            self._check_forbidden_method_in_repo(
                file_path,
                tree,
                "commit",
                UnitOfWorkLawConstants.CODE_UW002,
                self._msg_uw002,
            )
        )

        # UW003: rollback() 禁令
        violations.extend(
            self._check_forbidden_method_in_repo(
                file_path,
                tree,
                "rollback",
                UnitOfWorkLawConstants.CODE_UW003,
                self._msg_uw003,
            )
        )
