"""🏛️ DI001 依赖倒置审查官 (Dependency Injection Inquisitor)

本模块实现依赖倒置审查官，用于在静态代码审计阶段
发现并约束违反依赖倒置原则的跨组件引用。

设计要点
- 仅依赖 AST 与静态分析，不执行任何运行时代码；
- 所有违规信息均通过 `judges_text.yaml` 中的 DI001 模板渲染；
- 配置来源：
  - `laws.yaml` → `laws.di001`: API 外交特区允许的前缀/精确模块名；
  - `exempt.yaml` → `exemptions.DI001.files`: 路径/文件级豁免（治外法权）。

法条：依赖倒置原则 - 高层模块不应该依赖低层模块，两者都应该依赖抽象。
"""

import ast
import fnmatch
from pathlib import Path
from typing import Final

from pycourt.config.config import CourtConfig
from pycourt.utils import Violation, find_project_root, normalize_patterns


class DepInvLawConstants:
    """命名空间常量：DI001 依赖倒置法条内部使用。"""

    MIN_MODULE_PARTS_FOR_COMPONENT: Final[int] = 3
    CODE_DI001: Final[str] = "DI001"


# =============================================================================
# 🏛️ 依赖倒置审查官
# =============================================================================


class TheDepInvLaw:
    """🏛️ 依赖倒置审查官（DI001）。

    职责
    - 根据路径与模块名识别组件边界（如 ``engines.expert``、``infra.memory`` 等）；
    - 审查跨组件导入是否遵守依赖倒置原则：高层只能依赖抽象（core），
      组件之间不得直接互相引用实现层；
    - 对依赖注入容器（如应用的组合根目录）执行更严格的专门规则。

    数据来源
    - 输入：``file_path`` / ``content`` / ``lines`` / ``tree`` 由法院统一构建；
    - 配置：
      - ``self.laws.di001``: API 外交特区允许的模块前缀与精确模块名；
      - ``exempt.yaml`` → ``DI001.files``: 文件级豁免列表，由最高法院集中管理。

    核心规则（以任意应用根包 ``<root>`` 为例）
    - 普通业务代码：跨组件导入必须通过 ``<root>.core`` 暴露的抽象接口；
    - DI 容器：只能导入核心抽象、对应引擎模块以及 DI 系统内部模块
      （如 ``<root>.app.di.*``）；
    - API 外交特区：``<root>/api`` 目录在配置声明的白名单前缀/模块内享有更
      宽鬆的导入权限。
    """

    def __init__(self, config: CourtConfig) -> None:
        """初始化依赖倒置审查官，接入集中配置快照。"""

        self.config = config
        self.laws = config.laws
        # 预先解析 DI001 判决模板，避免在每次违规时重复查表
        self._template = config.get_judge_template(DepInvLawConstants.CODE_DI001)

    def investigate(
        self, file_path: Path, content: str, lines: list[str], tree: ast.AST | None
    ) -> list[Violation]:
        """对单个 Python 源文件执行 DI001 依赖倒置审查。

        检查范围
        - 仅对主应用源码生效（工具/测试通常通过集中豁免表排除）；
        - 通过集中豁免表（``exempt.yaml`` → ``DI001.files``）排除特权文件；
        - 可根据路径约定区分组合根与普通业务代码，应用不同的依赖倒置规则。
        """
        # 压制未使用参数警告
        del lines

        # AST 缺失或非模块节点直接跳过
        if tree is None or not isinstance(tree, ast.Module):
            return []

        root_package = self._get_root_package_for_file(file_path)
        if root_package is None:
            # 非主应用源码（如 tools/tests 等）或项目根未能识别，统一跳过
            return []

        if self._should_skip_file(file_path=file_path, content=content):
            return []

        violations: list[Violation] = []

        # 获取当前文件所属组件
        current_component = self._get_component_from_path(file_path, root_package)

        # 遍历所有导入语句
        for node in ast.walk(tree):
            if isinstance(node, ast.Import | ast.ImportFrom):
                violation = self._check_cross_component_import(
                    node=node,
                    file_path=file_path,
                    current_component=current_component,
                    root_package=root_package,
                )
                if violation:
                    violations.append(violation)

        return violations

    def _should_skip_file(self, *, file_path: Path, content: str) -> bool:
        """根据配置与集中豁免表判定是否跳过当前文件。"""

        # 配置驱动的顶层豁免与手动排除
        config = self.laws.di001
        if not getattr(config, "enabled", True):
            return True

        p_str = file_path.as_posix()
        patterns = normalize_patterns(
            self.config.get_exempt_files(DepInvLawConstants.CODE_DI001)
        )
        if any(fnmatch.fnmatch(p_str, p) or p_str.endswith(p) for p in patterns):
            return True

        # 检查文件级 pragma 豁免标记
        return "pragma: exclude file" in content

    def _get_root_package_for_file(self, file_path: Path) -> str | None:
        """推断当前文件所属的应用根包名（例如某项目中的 ``timeos`` 主包）。

        - 通过 `find_project_root()` 取得仓库根目录；
        - 使用相对于仓库根目录的首级目录作为根包；
        - 常见的非应用顶层目录（如 ``tools`` / ``tests`` / ``alembic``）将被视为
          非主应用代码并整体跳过。
        """

        try:
            project_root = find_project_root()
        except FileNotFoundError:
            return None

        try:
            rel = file_path.resolve().relative_to(project_root)
        except ValueError:
            return None

        parts = rel.parts
        if not parts:
            return None

        top_level = parts[0]
        if top_level in {"tools", "tests", "alembic"}:
            return None

        return top_level

    def _get_component_from_path(self, file_path: Path, root_package: str) -> str:
        """从文件路径提取组件标识。

        例如（相对于仓库根目录）：
        - ``<root>/infra/memory/cache.py``   → "infra.memory"；
        - ``<root>/engines/expert/planner.py`` → "engines.expert"；
        - ``<root>/api/routes.py``            → 视具体项目约定解析为应用/API 组件。
        """

        try:
            project_root = find_project_root()
        except FileNotFoundError:
            return str(file_path)

        try:
            rel = file_path.resolve().relative_to(project_root)
        except ValueError:
            return str(file_path)

        path_parts = rel.parts

        if len(path_parts) < DepInvLawConstants.MIN_MODULE_PARTS_FOR_COMPONENT:
            return str(file_path)

        if path_parts[0] != root_package:
            return str(file_path)

        first_level = path_parts[1]
        second_level = path_parts[2]

        return f"{first_level}.{second_level}"

    def _check_cross_component_import(
        self,
        *,
        node: ast.Import | ast.ImportFrom,
        file_path: Path,
        current_component: str,
        root_package: str,
    ) -> Violation | None:
        """检查是否存在非法的跨组件导入。

        【三权分立架构】
        - 立法权（Core）：定义所有 Ports；
        - 行政权（Infra）：实现所有 Ports；
        - 司法权（DI）：组装所有依赖。

        【普通业务代码的法律】
        - 组件之间不得直接互相依赖实现层，跨组件依赖必须通过核心抽象层
          （如 ``<root>.core``）暴露的契约完成；

        组合根/DI 系统入口等特殊路径目前统一交由集中豁免表管理，不在此处再做
        额外路径分支判断。
        """

        return self._check_regular_code_imports(
            node=node,
            file_path=file_path,
            current_component=current_component,
            root_package=root_package,
        )

    def _check_regular_code_imports(
        self,
        *,
        node: ast.Import | ast.ImportFrom,
        file_path: Path,
        current_component: str,
        root_package: str,
    ) -> Violation | None:
        """检查普通业务代码的导入是否遵守依赖倒置原则。

        聚焦“普通代码”的跨组件导入场景：
        - 首先识别 API 外交特区的合法导入（由 `_is_api_diplomatic_import` 负责）；
        - 然后检查是否通过 core 抽象、同组件内部或 DI 系统内部完成依赖；
        - 其余跨组件实现层直接互相引用的行为则视为 DI001 违规。
        """

        p_str = file_path.as_posix()
        imported_modules = self._extract_imported_modules(node)

        if self._is_api_diplomatic_import(
            p_str=p_str,
            imported_modules=imported_modules,
            root_package=root_package,
        ):
            return None

        return self._first_cross_component_violation(
            imported_modules=imported_modules,
            current_component=current_component,
            root_package=root_package,
            file_path=file_path,
            node=node,
        )

    def _first_cross_component_violation(
        self,
        *,
        imported_modules: list[str],
        current_component: str,
        root_package: str,
        file_path: Path,
        node: ast.Import | ast.ImportFrom,
    ) -> Violation | None:
        """返回首个跨组件导入违规（若不存在则返回 None）。"""

        project_prefix = f"{root_package}."
        core_prefix = f"{root_package}.core."
        di_internal_prefix = f"{root_package}.app.di"

        for module_name in imported_modules:
            # 只关心当前应用根包下的导入
            if not module_name.startswith(project_prefix):
                continue

            # ✅ 通过 core 的导入（合法）
            if module_name.startswith(core_prefix):
                continue

            # ✅ 同组件内的导入（合法）
            imported_component = self._get_component_from_module_name(
                module_name, root_package
            )
            if imported_component == current_component:
                continue

            # ✅ DI 系统内部引用（合法）
            if module_name.startswith(di_internal_prefix):
                continue

            # ❌ 非法的跨组件导入
            return Violation(
                file_path=file_path,
                line=node.lineno,
                col=node.col_offset,
                code=DepInvLawConstants.CODE_DI001,
                message=self._template.format(imported_module=module_name),
            )

        return None

    def _is_api_diplomatic_import(
        self,
        *,
        p_str: str,
        imported_modules: list[str],
        root_package: str,
    ) -> bool:
        """API 外交特区判定：检查当前导入是否在 DI001 的“外交白名单”内。

        规则概要
        - 仅当当前文件位于 ``<root>/api`` 目录下时才生效；
        - 允许导入 ``api_allowed_prefixes`` 中声明的前缀（如 ``<root>.api.*``、
          ``<root>.core.*``）；
        - 允许导入 ``api_allowed_exact`` 中声明的精确模块名
          （如 ``<root>.app.dependencies``）；
        - 一旦发现不在白名单内的 ``<root>.*`` 导入，即视为不在外交特区内，
          由普通依赖倒置规则继续审查。
        """

        api_marker = f"/{root_package}/api/"
        if api_marker not in p_str:
            return False

        # DI 系列家族配置：允许 API 外交特区下哪些模块前缀/精确模块名作为白名单。
        di_cfg = getattr(self.config, "di", None)

        if di_cfg is not None and getattr(di_cfg, "api_allowed_prefixes", None):
            allowed_prefixes = tuple(di_cfg.api_allowed_prefixes)
        else:
            allowed_prefixes = (
                f"{root_package}.api.",
                f"{root_package}.core.",
            )

        if di_cfg is not None and getattr(di_cfg, "api_allowed_exact", None):
            allowed_exact = set(di_cfg.api_allowed_exact)
        else:
            allowed_exact = {f"{root_package}.app.dependencies"}

        project_prefix = f"{root_package}."
        for module_name in imported_modules:
            if not module_name.startswith(project_prefix):
                continue
            if module_name.startswith(allowed_prefixes):
                continue
            if module_name in allowed_exact:
                continue
            return False

        return True

    def _extract_imported_modules(self, node: ast.Import | ast.ImportFrom) -> list[str]:
        """从导入节点中提取所有被导入的模块名。"""
        modules: list[str] = []

        if isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name)

        return modules

    def _get_component_from_module_name(
        self,
        module_name: str,
        root_package: str,
    ) -> str:
        """从模块名提取组件标识，例如 ``<root>.engines.expert`` → "engines.expert"。"""

        parts = module_name.split(".")

        if (
            len(parts) >= DepInvLawConstants.MIN_MODULE_PARTS_FOR_COMPONENT
            and parts[0] == root_package
        ):
            return f"{parts[1]}.{parts[2]}"

        # 如果格式不符合预期，返回原始模块名
        return module_name
