"""🏛️ 疆域边界审查官（BC001）

本模块实现“疆域边界审查官”，负责在预定义的边界层上
审查所有公开函数/方法的参数与返回值，鼓励使用 Pydantic / DTO 契约类型。

设计要点
- 仅依赖 AST 与静态分析，不执行任何运行时代码；
- 所有违规信息均通过 `judges_text.yaml` 中的 BC001 模板渲染；
- 配置来源：
  - 集中豁免：`exempt.yaml` → `exemptions.BC001.files`；
  - 判决文案：`judges_text.yaml` → `judges.BC001.template`；
  - 路由/适配器识别与类型豁免等结构性规则在本模块内以常量形式定义，
    不再通过 Court 契约 (`LawsBC001`) 进行声明。
"""

from __future__ import annotations

import ast
import fnmatch
from pathlib import Path
from typing import ClassVar, Final

from pycourt.config.config import CourtConfig
from pycourt.utils import Violation, normalize_patterns


class BoundaryControlConstants:
    """命名空间常量：BC001 疆域边界审查法条内部使用。"""

    CODE_BC001: Final[str] = "BC001"


# 路由/适配器识别与豁免规则从 YAML 迁移至代码内常量
_DEFAULT_ROUTER_DIR_PATTERNS: Final[tuple[str, ...]] = ("api/routes/",)
_DEFAULT_EXEMPT_ROUTER_PARAM_TYPES: Final[tuple[str, ...]] = (
    "str",
    "int",
    "float",
    "bool",
    "Session",
    "DatabaseSession",
    "Annotated",
    "Depends",
)
_DEFAULT_EXEMPT_FUNCTION_NAME_PATTERNS: Final[tuple[str, ...]] = (
    "get_*",
    "create_*",
    "build_*",
)
_DEFAULT_ADAPTER_DIR_PATTERNS: Final[tuple[str, ...]] = ("infra/adapters/**",)
_DEFAULT_EXEMPT_ADAPTER_PARAM_TYPES: Final[tuple[str, ...]] = (
    "str",
    "int",
    "float",
    "bool",
)


class TheBndCtrlLaw:
    """🏛️ 疆域边界审查官（BC001）。

    职责
    - 识别“边界文件”：HTTP 路由层（`router_dir_patterns`）与 infra 适配器层
      （`adapter_dir_patterns`）；
    - 在这些文件中审查所有顶层公开函数/方法的参数与返回值类型；
    - 要求它们使用来自核心契约模块（如 `core.types`、`core.dto` 等）
      以及（对路由层）API 契约模块的类型，而不是裸基础类型/容器。

    数据来源
    - 输入：
      - ``file_path`` / ``content`` / ``lines`` / ``tree`` 由法院统一构建；
    - 配置：
      - ``self.laws.bc001.enabled``: BC001 是否启用；
      - ``exempt.yaml`` → ``BC001.files``: 整个文件层面的豁免列表；
      - 路由/适配器目录模式、函数级豁免与类型豁免等审计策略由本模块内
        的常量提供，不再通过 Court 契约字段暴露。

    输出
    - 返回一组 :class:`Violation`，每条都使用 BC001 模板渲染，并标注具体
      函数名、参数名与类型字符串。
    """

    def __init__(self, config: CourtConfig) -> None:
        self.config = config
        self.laws = config.laws
        self._msg_bc001: str = self.config.get_judge_template(
            BoundaryControlConstants.CODE_BC001
        )

    _BASIC_TYPES: ClassVar[set[str]] = {
        "str",
        "int",
        "float",
        "bool",
        "bytes",
        "dict",
        "list",
        "set",
        "tuple",
        "object",
        "None",
        "NoneType",
        "Any",
    }
    _ALLOWED_SUFFIXES: ClassVar[tuple[str, ...]] = (
        "Model",
        "Schema",
        "Contract",
        "Params",
        "Request",
        "Response",
        "DTO",
        "map",
    )
    _imported_core_schema_names: ClassVar[set[str]] = set()

    # --- 辅助工具 (Helper Methods) ---
    def _bracket_inner(self, txt: str) -> str:
        """返回类型字符串中最外层方括号内部的子串。

        用于解析诸如 ``list[UserDTO]``、``dict[str, UserDTO]`` 等泛型类型，
        不尝试做语义校验，仅做简单的切片提取。
        """
        start = txt.find("[")
        end = txt.rfind("]")
        return txt[start + 1 : end] if start != -1 and end != -1 and end > start else ""

    def _split_top_level_params(self, params: str) -> list[str]:
        """将泛型参数列表按顶层逗号拆分。

        示例：
        - ``"str, UserDTO"``           → ["str", "UserDTO"]
        - ``"str, list[UserDTO]"``    → ["str", "list[UserDTO]"]

        仅通过简单的括号/方括号深度计数来避免在内部容器上的误切分。
        """
        parts: list[str] = []
        buf: list[str] = []
        depth = 0
        for ch in params:
            if ch == "[":
                depth += 1
            elif ch == "]" and depth > 0:
                depth -= 1
            if ch == "," and depth == 0:
                seg = "".join(buf).strip()
                parts.append(seg) if seg else None
                buf = []
            else:
                buf.append(ch)
        tail = "".join(buf).strip()
        parts.append(tail) if tail else None
        return parts

    # --- 核心审查逻辑 (Core Investigation Logic) ---

    def _collect_core_schema_imports(
        self,
        tree: ast.AST | None,
        *,
        allowed_modules: tuple[str, ...] = (
            "core.base.types",
            "core.dto",
        ),
    ) -> set[str]:
        """根据导入语句收集当前文件中的“契约类型”名称集合。

        - 默认只认可来自 ``<root>.core.base.types`` 与 ``<root>.core.dto`` 的导入；
        - 对于路由层文件，会额外允许 ``<root>.api.http.*`` 作为 HTTP 契约模型；
        - 返回的名称集合会作为 :meth:`_string_is_contract` 的第一层快速判定依据。
        """
        names: set[str] = set()
        if tree is None:
            return names
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and isinstance(node.module, str)
                and any(node.module.endswith(mod) for mod in allowed_modules)
            ):
                for alias in node.names:
                    names.add(alias.asname or alias.name)
        return names

    def _string_is_contract(self, type_str: str) -> bool:
        """根据类型字符串判断其是否可视为“契约类型”。

        判定规则概要：
        - 若名称出现在 ``_imported_core_schema_names`` 中，则直接视为契约类型；
        - 支持 ``Optional``/``Union`` 以及 list/dict/Iterable 等容器的递归判定；
        - 内建基础类型（``_BASIC_TYPES``）一律不是契约类型；
        - 其他情况通过后缀（Model/DTO/...）或包含 ``BaseModel`` 作为兜底启发式。
        """

        s = type_str.replace(" ", "")
        if not s:
            return False

        if s in self._imported_core_schema_names:
            return True

        is_contract = False
        if (
            self._is_union_contract(s)
            or self._is_optional_union_contract(s)
            or self._is_container_contract(s)
        ):
            is_contract = True
        elif s in self._BASIC_TYPES:
            is_contract = False
        else:
            is_contract = self._matches_contract_suffix_or_basemodel(s)

        return is_contract

    def _is_union_contract(self, type_str: str) -> bool:
        """处理 ``T1 | T2 | None`` 形式的 Union 类型。"""

        if "|" not in type_str:
            return False
        parts = [p for p in type_str.split("|") if p not in ("None", "NoneType")]
        return bool(parts) and all(self._string_is_contract(p) for p in parts)

    def _is_optional_union_contract(self, type_str: str) -> bool:
        """处理 ``Optional[T]`` / ``Union[T, None]`` 等泛型联合类型。"""

        if not type_str.startswith(("Optional[", "Union[")):
            return False

        inner = self._bracket_inner(type_str)
        parts = [
            p
            for p in self._split_top_level_params(inner)
            if p not in ("None", "NoneType")
        ]
        return bool(parts) and all(self._string_is_contract(p) for p in parts)

    def _is_container_contract(self, type_str: str) -> bool:
        """处理 list[T] / dict[str, T] / Iterable[T] 等容器类型。"""

        if not any(
            type_str.startswith(p)
            for p in (
                "list[",
                "List[",
                "dict[",
                "Dict[",
                "Iterator[",
                "Iterable[",
                "AsyncIterator[",
                "AsyncIterable[",
            )
        ):
            return False

        inner = self._bracket_inner(type_str)
        if not inner:
            return False

        params = self._split_top_level_params(inner)
        if len(params) == 1:
            return self._string_is_contract(params[0])

        exact_two = 2  # PLR2004: name the magic number
        return (
            len(params) == exact_two
            and params[0] == "str"
            and self._string_is_contract(params[1])
        )

    def _matches_contract_suffix_or_basemodel(self, type_str: str) -> bool:
        """兜底策略：通过后缀或 BaseModel 关键字识别契约类型。"""

        return any(type_str.endswith(suf) for suf in self._ALLOWED_SUFFIXES) or (
            "BaseModel" in type_str
        )

    def investigate(
        self, file_path: Path, content: str, lines: list[str], tree: ast.AST | None
    ) -> list[Violation]:
        """对单个 Python 源文件执行 BC001 边界契约审查。

        检查范围
        - 仅在“边界文件”中生效：
          - HTTP 路由文件（路径包含 ``router_dir_patterns`` 中任一模式）；
          - 第三方适配器文件（路径匹配 ``adapter_dir_patterns`` 的 fnmatch 模式）；
        - 审查对象：
          - 顶层公开函数/协程的所有参数类型；
          - 顶层公开函数/协程的返回值类型。

        执行步骤
        1. 根据集中豁免表（``pycourt.yaml`` → ``BC001.files``）跳过特定文件；
        2. 根据 ``bc001.router_dir_patterns`` / ``bc001.adapter_dir_patterns`` 判定文件角色；
        3. 若既不是路由文件也不是适配器文件，则直接返回空结果；
        4. 收集当前文件中从核心类型模块（如 core/base/types、core/dto）及
           （对路由层）API 契约模块导入的契约类型名称集合；
        5. 对每个顶层函数：
           - 若函数名以下划线开头或匹配 ``exempt_function_name_patterns``，则整体豁免；
           - 否则依次检查参数与返回值：
             - 命中相应层的豁免类型（router/adapter 专用）则跳过；
             - 若最终仍不属于契约类型（``_string_is_contract`` 返回 False），
               则产出一条 BC001 违规记录。
        """
        del content, lines
        if tree is None:
            return []

        # 1. 从法典读取开关，其余结构性规则由代码内常量提供
        law_cfg = self.laws.bc001
        if not getattr(law_cfg, "enabled", True):
            return []

        s_path = str(file_path).replace("\\", "/")

        # 1. 检查是否在豁免名单中（由集中豁免表统一管理）
        patterns = normalize_patterns(
            self.config.get_exempt_files(BoundaryControlConstants.CODE_BC001)
        )
        if any(
            fnmatch.fnmatch(s_path, pattern) or s_path.endswith(pattern)
            for pattern in patterns
        ):
            return []

        return self._investigate_bc001(file_path, s_path, tree)

    def _investigate_bc001(
        self,
        file_path: Path,
        s_path: str,
        tree: ast.AST,
    ) -> list[Violation]:
        """内部实现：在前置条件满足后执行 BC001 全量审查逻辑。"""

        violations: list[Violation] = []

        is_router_file, is_adapter_file = self._classify_boundary_file(
            s_path=s_path,
            tree=tree,
        )

        # 🏛️ 执法范围收敛：BC001 只审查真正的“边界文件”。
        # - API 路由层是对外协议边界；
        # - infra/adapters 是第三方技术边界。
        # 其他目录（尤其是 core/utils 等内部工具）不应被强制 DTO 化。
        if not is_router_file and not is_adapter_file:
            return []

        router_types, adapter_types = self._get_exempt_types_for_file(
            is_router_file=is_router_file,
            is_adapter_file=is_adapter_file,
        )

        if not isinstance(tree, ast.Module):
            return violations

        for stmt in tree.body:
            if isinstance(stmt, ast.FunctionDef | ast.AsyncFunctionDef):
                self._check_single_function(
                    node=stmt,
                    file_path=file_path,
                    is_router_file=is_router_file,
                    is_adapter_file=is_adapter_file,
                    router_types=router_types,
                    adapter_types=adapter_types,
                    violations=violations,
                )

        return violations

    def _classify_boundary_file(
        self,
        *,
        s_path: str,
        tree: ast.AST,
    ) -> tuple[bool, bool]:
        """基于路径判断当前文件是否为路由层或适配器层。

        历史上支持通过 LawsBC001 覆盖路由/适配器目录模式；随着 laws.yaml 的
        移除，目前统一使用本模块内的 `_DEFAULT_*` 常量作为唯一信息来源。
        """

        router_patterns = list(_DEFAULT_ROUTER_DIR_PATTERNS)
        is_router_file = any(pat in s_path for pat in router_patterns)

        # 路由文件与适配器文件的路径识别依赖 BC 配置模型，保留模块内常量作为兜底。
        bc_cfg = getattr(self.config, "bc", None)

        router_patterns = list(_DEFAULT_ROUTER_DIR_PATTERNS)
        if bc_cfg is not None and getattr(bc_cfg, "router_dir_patterns", None):
            router_patterns = list(bc_cfg.router_dir_patterns)
        is_router_file = any(pat in s_path for pat in router_patterns)

        adapter_patterns = list(_DEFAULT_ADAPTER_DIR_PATTERNS)
        if bc_cfg is not None and getattr(bc_cfg, "adapter_dir_patterns", None):
            adapter_patterns = list(bc_cfg.adapter_dir_patterns)
        is_adapter_file = any(fnmatch.fnmatch(s_path, pat) for pat in adapter_patterns)

        # 契约模块来源后缀同样从 BC 配置读取，保持与默认值兼容。
        core_suffixes = ["core.base.types", "core.dto"]
        api_suffixes = ["api.http"]
        if bc_cfg is not None and getattr(
            bc_cfg, "core_contract_module_suffixes", None
        ):
            core_suffixes = list(bc_cfg.core_contract_module_suffixes)
        if bc_cfg is not None and getattr(bc_cfg, "api_contract_module_suffixes", None):
            api_suffixes = list(bc_cfg.api_contract_module_suffixes)

        if is_router_file:
            allowed_modules: tuple[str, ...] = tuple(core_suffixes + api_suffixes)
        else:
            allowed_modules = tuple(core_suffixes)

        type(self)._imported_core_schema_names = self._collect_core_schema_imports(
            tree,
            allowed_modules=allowed_modules,
        )
        return is_router_file, is_adapter_file

    def _get_exempt_types_for_file(
        self,
        *,
        is_router_file: bool,
        is_adapter_file: bool,
    ) -> tuple[list[str], list[str]]:
        """获取当前文件在路由层和适配器层的类型豁免清单。

        当前实现统一使用本模块内的 `_DEFAULT_EXEMPT_*` 常量作为豁免基础，
        不再经由 LawsBC001 暴露细粒度配置。
        """

        if is_router_file:
            router_types: list[str] = list(_DEFAULT_EXEMPT_ROUTER_PARAM_TYPES)
        else:
            router_types = []

        if is_adapter_file:
            adapter_types: list[str] = list(_DEFAULT_EXEMPT_ADAPTER_PARAM_TYPES)
        else:
            adapter_types = []

        return router_types, adapter_types

    def _is_function_exempt(self, func_name: str) -> bool:
        """检查函数是否豁免 BC001 检查。

        当前实现采用统一的内部命名约定：
        - 以下划线开头的函数视为内部实现，整体豁免；
        - 其余函数使用 `_DEFAULT_EXEMPT_FUNCTION_NAME_PATTERNS` 中的模式匹配。
        """

        if func_name.startswith("_"):
            return True

        exempt_patterns: list[str] = list(_DEFAULT_EXEMPT_FUNCTION_NAME_PATTERNS)
        return any(fnmatch.fnmatch(func_name, p) for p in exempt_patterns)

    def _check_single_function(  # noqa: PLR0913
        self,
        *,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_path: Path,
        is_router_file: bool,
        is_adapter_file: bool,
        router_types: list[str],
        adapter_types: list[str],
        violations: list[Violation],
    ) -> None:
        """对单个函数的所有参数和返回值执行 BC001 审查。"""

        if self._is_function_exempt(node.name):
            return

        self._check_function_parameters(
            node=node,
            file_path=file_path,
            is_router_file=is_router_file,
            is_adapter_file=is_adapter_file,
            router_types=router_types,
            adapter_types=adapter_types,
            violations=violations,
        )

        self._check_function_return(
            node=node,
            file_path=file_path,
            is_adapter_file=is_adapter_file,
            adapter_types=adapter_types,
            violations=violations,
        )

    def _check_function_parameters(  # noqa: PLR0913
        self,
        *,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_path: Path,
        is_router_file: bool,
        is_adapter_file: bool,
        router_types: list[str],
        adapter_types: list[str],
        violations: list[Violation],
    ) -> None:
        """审查函数的所有参数类型是否符合 BC001 契约要求。"""

        for arg in node.args.args + node.args.kwonlyargs:
            if arg.arg in {"self", "cls"} or arg.annotation is None:
                continue

            ann_str = ast.unparse(arg.annotation)

            if is_router_file and any(t in ann_str for t in router_types):
                continue
            if is_adapter_file and any(t in ann_str for t in adapter_types):
                continue

            if not self._string_is_contract(ann_str):
                violations.append(
                    Violation(
                        file_path,
                        node.lineno,
                        node.col_offset,
                        BoundaryControlConstants.CODE_BC001,
                        self._msg_bc001.format(
                            func=node.name, name=arg.arg, type=ann_str
                        ),
                    )
                )

    def _check_function_return(
        self,
        *,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_path: Path,
        is_adapter_file: bool,
        adapter_types: list[str],
        violations: list[Violation],
    ) -> None:
        """审查函数返回值类型是否符合 BC001 契约要求。"""

        if not node.returns:
            return

        ret_str = ast.unparse(node.returns)

        if "Protocol" in ret_str:
            return

        if is_adapter_file and any(t in ret_str for t in adapter_types):
            return

        if not self._string_is_contract(ret_str):
            violations.append(
                Violation(
                    file_path,
                    node.lineno,
                    node.col_offset,
                    BoundaryControlConstants.CODE_BC001,
                    self._msg_bc001.format(func=node.name, name="return", type=ret_str),
                )
            )
