"""🏛️ 向量事务法官

目的
- 将 Vector 的“触发协议”从文档要求提升为可执行的静态宪法审计。
- 防止发行方（capsule issuer）发出 `asset.materialized` / `capsule.materialized`，
  但 VectorMaterialProvider 未提供对应取材能力，导致运行时才暴露缺口。

裁决范围（强制）
- 仅审查主应用代码（项目根下的主包目录）；
- 排除：tests/**、tools/** 以及通过 VT001 文件级豁免声明的基础设施/核心目录。

执法逻辑（强制）
1) 解析 Vector 提供商模块的路由表（例如 ``<root>/infra/vector/providers.py``）：
   - self._asset_text_routes 的 keys 视为“支持的 asset_type 集合”；
   - self._capsule_text_routes 的 keys 视为“支持的 capsule_kind 集合”。

2) 扫描发行方代码中对 `uow.stage_public_event(event=...)` 的调用：
   - 捕获 AssetMaterializedEvent / CapsuleMaterializedEvent 的构造
   - 提取字段：asset_type / issuer / capsule_kind

3) 判案：
   - AssetMaterializedEvent.asset_type 必须被 provider 的 asset routes 覆盖
   - CapsuleMaterializedEvent.capsule_kind 必须被 provider 的 capsule routes 覆盖
   - 两类事件均必须显式携带 issuer + capsule_kind（E2/F2 纪律）

备注
- 本法官不依赖运行时代码执行，以保持纯静态审计。
- 为兼容开发者写法，asset_type/capsule_kind 支持：
  - 字符串字面量（例如 "gold" / "gold_memory"）
  - 枚举表达式（例如 CapsuleIssuer.GOLD / CapsuleAssetType.GOLD_MEMORY.value）
  - 模块内常量别名（例如 _GoldCommitConst.CAPSULE_KIND）
"""

from __future__ import annotations

import ast
import fnmatch
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pycourt.config.config import CourtConfig
from pycourt.utils import (
    Violation,
    find_project_root,
    get_ast_tree,
    normalize_patterns,
    read_file_content,
)


class VectorTriggerLawConstants:
    """命名空间常量：VT001/VT002/VT003 向量触发法条内部使用。"""

    CODE_VT001: Final[str] = "VT001"
    CODE_VT002: Final[str] = "VT002"
    CODE_VT003: Final[str] = "VT003"


@dataclass(frozen=True, slots=True)
class _ProviderRoutes:
    """向量提供商路由表 - 存储支持的资产类型和胶囊类型

    属性：
    - asset_type_keys: 支持的资产类型集合（来自 _asset_text_routes）
    - capsule_kind_keys: 支持的胶囊类型集合（来自 _capsule_text_routes）
    """

    asset_type_keys: frozenset[str]
    capsule_kind_keys: frozenset[str]


@dataclass(frozen=True, slots=True)
class _EventAnalysisContext:
    """VT001 事件分析上下文，减少辅助方法参数数量。"""

    tree: ast.Module
    file_path: Path
    content: str
    alias: AliasMap
    routes: _ProviderRoutes


def _find_repo_root(start: Path) -> Path | None:
    """定位仓库根目录。

    当前实现委托给 ``find_project_root``，保持与其他法条一致的根目录推断方式。
    若无法定位，则返回 ``None``，上层逻辑会整体跳过 VT001 审查。
    """

    del start  # 路径从调用点传入，仅为兼容旧签名而保留
    try:
        return find_project_root()
    except FileNotFoundError:
        return None


def _norm_token(s: str) -> str:
    return "".join(str(s).split())


def _expr_to_value_candidates(expr: str) -> set[str]:
    """将表达式片段归一化为一组可比较的值。

    示例：

    - CapsuleAssetType.GOLD_MEMORY.value -> {"CapsuleAssetType.GOLD_MEMORY.value", "gold_memory"}

    - CapsuleIssuer.GOLD -> {"CapsuleIssuer.GOLD", "gold"}

    - "gold" -> {"gold"}

    对于未知表达式，返回 {expr}。
    """

    raw = expr.strip()
    out: set[str] = set()
    if not raw:
        return out

    out.add(_norm_token(raw))

    if _try_handle_string_literal(raw, out):
        return out
    if _try_handle_capsule_asset_type(raw, out):
        return out
    if _try_handle_capsule_issuer(raw, out):
        return out

    return out


def _try_handle_string_literal(raw: str, out: set[str]) -> bool:
    """处理纯字符串字面量形式的表达式。"""

    if (raw.startswith('"') and raw.endswith('"')) or (
        raw.startswith("'") and raw.endswith("'")
    ):
        out.add(raw[1:-1])
        return True
    return False


def _try_handle_capsule_asset_type(raw: str, out: set[str]) -> bool:
    """处理 CapsuleAssetType.X.value 形式的表达式。"""

    if not (raw.startswith("CapsuleAssetType.") and raw.endswith(".value")):
        return False

    mid = raw[len("CapsuleAssetType.") : -len(".value")]
    if mid:
        out.add(mid.lower())
    return True


def _try_handle_capsule_issuer(raw: str, out: set[str]) -> bool:
    """处理 CapsuleIssuer.X 形式的表达式。"""

    if not raw.startswith("CapsuleIssuer."):
        return False

    mid = raw[len("CapsuleIssuer.") :]
    if mid:
        out.add(mid.lower())
    return True


def _source_segment(content: str, node: ast.AST) -> str:
    seg = ast.get_source_segment(content, node)
    if isinstance(seg, str) and seg.strip():
        return seg.strip()
    return ast.dump(node)


AliasMap = dict[str, str]
EventBindings = dict[str, ast.Call]


def _build_alias_map(content: str, tree: ast.AST) -> AliasMap:
    """构建一个简单的别名映射，用于模块局部常量。"""

    if not isinstance(tree, ast.Module):
        return {}

    alias: AliasMap = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            _collect_aliases_from_class(node=node, content=content, alias=alias)
    return alias


def _collect_aliases_from_class(
    *, node: ast.ClassDef, content: str, alias: AliasMap
) -> None:
    """从单个类定义中收集常量别名。"""

    class_name = node.name
    for stmt in node.body:
        if _try_register_simple_assign(stmt, class_name, content, alias):
            continue
        _try_register_annotated_assign(stmt, class_name, content, alias)


def _try_register_simple_assign(
    stmt: ast.stmt, class_name: str, content: str, alias: AliasMap
) -> bool:
    """处理形如 ``CONST = <expr>`` 的简单赋值。"""

    if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1):
        return False

    target = stmt.targets[0]
    if not isinstance(target, ast.Name):
        return False

    key = f"{class_name}.{target.id}"
    alias[key] = _source_segment(content, stmt.value)
    return True


def _try_register_annotated_assign(
    stmt: ast.stmt, class_name: str, content: str, alias: AliasMap
) -> None:
    """处理形如 ``CONST: Final[...] = <expr>`` 的注解赋值。"""

    if not (isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)):
        return
    if stmt.value is None:
        return

    key = f"{class_name}.{stmt.target.id}"
    alias[key] = _source_segment(content, stmt.value)


def _resolve_alias(expr: str, alias: AliasMap) -> str:
    # Most common form in codebase: _SomeConst.FOO
    if expr in alias:
        return alias[expr]
    return expr


def _is_self_attr_assign(node: ast.AST) -> tuple[str, ast.Dict] | None:
    """检查节点是否为 `self.<attr> = <dict>` 并返回 (attr, dict) 或 None。"""
    if not isinstance(node, ast.Assign) or len(node.targets) != 1:
        return None
    target = node.targets[0]
    if not isinstance(target, ast.Attribute):
        return None
    if not isinstance(target.value, ast.Name) or target.value.id != "self":
        return None
    if not isinstance(node.value, ast.Dict):
        return None
    return (target.attr, node.value)


def _extract_dict_keys(content: str, d: ast.Dict) -> set[str]:
    """从字典键中提取所有候选值。"""
    keys: set[str] = set()
    for k in d.keys:
        if k is None:
            continue
        expr = _source_segment(content, k)
        keys.update(_expr_to_value_candidates(expr))
    return keys


def _load_provider_routes(repo_root: Path, search_pattern: str) -> _ProviderRoutes:
    """从 Vector 提供商模块中加载资产/胶囊路由表。

    旧实现依赖固定路径 ``timeos/infra/vector/providers.py``；为提升复用性，
    现改为：
    - 在仓库根目录下递归查找形如 ``*/infra/vector/providers.py`` 的文件；
    - 命中第一个候选文件后解析其 AST，提取 `_asset_text_routes` /
      `_capsule_text_routes` 的字典键作为支持集合。
    """

    pattern = search_pattern or "infra/vector/providers.py"

    try:
        candidates: list[Path] = [
            p for p in repo_root.rglob("providers.py") if pattern in p.as_posix()
        ]
    except OSError:  # pragma: no cover - 文件系统异常容错
        candidates = []

    if not candidates:
        return _ProviderRoutes(
            asset_type_keys=frozenset(), capsule_kind_keys=frozenset()
        )

    provider_path = sorted(candidates)[0]
    content, _lines = read_file_content(provider_path)
    tree = get_ast_tree(content, str(provider_path))
    if tree is None or not isinstance(tree, ast.Module):
        return _ProviderRoutes(
            asset_type_keys=frozenset(), capsule_kind_keys=frozenset()
        )

    asset_keys: set[str] = set()
    capsule_keys: set[str] = set()

    for node in ast.walk(tree):
        result = _is_self_attr_assign(node)
        if result is None:
            continue
        attr, dict_node = result

        if attr == "_asset_text_routes":
            asset_keys.update(_extract_dict_keys(content, dict_node))
        elif attr == "_capsule_text_routes":
            capsule_keys.update(_extract_dict_keys(content, dict_node))

    return _ProviderRoutes(
        asset_type_keys=frozenset(asset_keys),
        capsule_kind_keys=frozenset(capsule_keys),
    )


def _is_target_code_file(file_path: Path) -> bool:
    """粗粒度范围：仅审查主应用代码，其它（工具/测试等）视为域外代码。

    通过相对于仓库根目录的首级目录进行粗粒度筛选，约定：
    - ``tools`` / ``tests`` / ``alembic`` 等目录默认不属于主应用代码；
    - 其他顶层目录（例如某项目中的主业务包 ``timeos``）视为主应用包，默认纳入 VT001 审查候选范围。
    """

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

    return parts[0] not in {"tools", "tests", "alembic"}


def _call_name(call: ast.Call) -> str | None:
    fn = call.func
    if isinstance(fn, ast.Name):
        return fn.id
    if isinstance(fn, ast.Attribute):
        return fn.attr
    return None


def _extract_kw_expr(
    *, content: str, call: ast.Call, key: str, alias: AliasMap
) -> str | None:
    for kw in call.keywords:
        if kw.arg != key:
            continue
        if kw.value is None:  # pyright: ignore[reportUnnecessaryComparison]
            return None
        raw = _source_segment(content, kw.value)
        return _resolve_alias(raw, alias)
    return None


def _build_event_bindings(
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
) -> EventBindings:
    """构建一个函数内变量名到事件构造函数调用的映射图。"""
    bindings: EventBindings = {}
    for stmt in ast.walk(fn):
        if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
            continue
        if not isinstance(stmt.targets[0], ast.Name):
            continue
        if not isinstance(stmt.value, ast.Call):
            continue
        cname = _call_name(stmt.value)
        if cname in {"AssetMaterializedEvent", "CapsuleMaterializedEvent"}:
            bindings[stmt.targets[0].id] = stmt.value
    return bindings


def _extract_event_call(stmt: ast.Call, bindings: EventBindings) -> ast.Call | None:
    """从 stage_public_event 调用中提取事件调用。"""
    for kw in stmt.keywords:
        if kw.arg != "event" or kw.value is None:  # pyright: ignore[reportUnnecessaryComparison]
            continue
        if isinstance(kw.value, ast.Call):
            return kw.value
        if isinstance(kw.value, ast.Name) and kw.value.id in bindings:
            return bindings[kw.value.id]
    return None


def _make_violation(
    file_path: Path, event_call: ast.Call, code: str, message: str
) -> Violation:
    """创建一个事件调用的违规记录。"""
    return Violation(
        file_path=file_path,
        line=getattr(event_call, "lineno", 1),
        col=getattr(event_call, "col_offset", 0),
        code=code,
        message=message,
    )


def _check_required_fields(
    *,
    ctx: _EventAnalysisContext,
    event_call: ast.Call,
    event_name: str,
    msg_vt003: str,
) -> tuple[list[Violation], str | None, str | None]:
    """检查必填字段并返回违规项及提取的表达式。

    使用 `_EventAnalysisContext` 承载文件级上下文，避免辅助函数参数过多。
    """
    violations: list[Violation] = []
    issuer_expr = _extract_kw_expr(
        content=ctx.content, call=event_call, key="issuer", alias=ctx.alias
    )
    capsule_kind_expr = _extract_kw_expr(
        content=ctx.content, call=event_call, key="capsule_kind", alias=ctx.alias
    )

    if issuer_expr is None:
        violations.append(
            _make_violation(
                ctx.file_path,
                event_call,
                VectorTriggerLawConstants.CODE_VT003,
                msg_vt003.format(event_name=event_name, field="issuer"),
            )
        )
    if capsule_kind_expr is None:
        violations.append(
            _make_violation(
                ctx.file_path,
                event_call,
                VectorTriggerLawConstants.CODE_VT003,
                msg_vt003.format(event_name=event_name, field="capsule_kind"),
            )
        )
    return violations, issuer_expr, capsule_kind_expr


def _check_asset_coverage(  # noqa: PLR0913
    file_path: Path,
    event_call: ast.Call,
    event_name: str,
    content: str,
    alias: AliasMap,
    routes: _ProviderRoutes,
    msg_vt001: str,
) -> list[Violation]:
    """检查AssetMaterializedEvent的资产类型覆盖情况。"""
    violations: list[Violation] = []
    asset_type_expr = _extract_kw_expr(
        content=content, call=event_call, key="asset_type", alias=alias
    )

    if asset_type_expr is None:
        violations.append(
            _make_violation(
                file_path,
                event_call,
                VectorTriggerLawConstants.CODE_VT003,
                msg_vt001.format(event_name=event_name, field="asset_type"),
            )
        )
        return violations

    candidates = _expr_to_value_candidates(asset_type_expr)
    if not (candidates & set(routes.asset_type_keys)):
        violations.append(
            _make_violation(
                file_path,
                event_call,
                VectorTriggerLawConstants.CODE_VT001,
                msg_vt001.format(asset_type=asset_type_expr),
            )
        )
    return violations


def _check_capsule_coverage(
    file_path: Path,
    event_call: ast.Call,
    capsule_kind_expr: str | None,
    routes: _ProviderRoutes,
    msg_vt002: str,
) -> list[Violation]:
    """检查CapsuleMaterializedEvent的胶囊类型覆盖范围。"""
    if capsule_kind_expr is None:
        return []

    candidates = _expr_to_value_candidates(capsule_kind_expr)
    if not (candidates & set(routes.capsule_kind_keys)):
        return [
            _make_violation(
                file_path,
                event_call,
                VectorTriggerLawConstants.CODE_VT002,
                msg_vt002.format(capsule_kind=capsule_kind_expr),
            )
        ]
    return []


class TheVectorTriggerLaw:
    """🏛️ VT001 Vector Trigger 契约法官"""

    def __init__(self, config: CourtConfig) -> None:
        self.config = config
        self.laws = config.laws
        self._routes_cache: dict[Path, _ProviderRoutes] = {}
        self._msg_vt001: str = self.config.get_judge_template(
            VectorTriggerLawConstants.CODE_VT001
        )
        self._msg_vt002: str = self.config.get_judge_template(
            VectorTriggerLawConstants.CODE_VT002
        )
        self._msg_vt003: str = self.config.get_judge_template(
            VectorTriggerLawConstants.CODE_VT003
        )

    def _get_routes(self, file_path: Path) -> _ProviderRoutes | None:
        """获取提供商路由，如果可用则使用缓存。"""
        repo_root = _find_repo_root(file_path)
        if repo_root is None:
            return None
        routes = self._routes_cache.get(repo_root)
        if routes is None:
            vt_cfg = getattr(self.config, "vt", None)
            if vt_cfg is None:
                return None
            search_pattern = vt_cfg.provider_search_pattern
            routes = _load_provider_routes(repo_root, search_pattern)
            self._routes_cache[repo_root] = routes
        return routes

    def _process_event_call(
        self,
        *,
        ctx: _EventAnalysisContext,
        event_call: ast.Call,
    ) -> list[Violation]:
        """处理单个事件调用并返回任何违规行为。"""
        event_name = _call_name(event_call)
        if event_name not in {
            "AssetMaterializedEvent",
            "CapsuleMaterializedEvent",
        }:
            return []

        violations, _issuer, capsule_kind_expr = _check_required_fields(
            ctx=ctx,
            event_call=event_call,
            event_name=event_name,
            msg_vt003=self._msg_vt003,
        )

        if event_name == "AssetMaterializedEvent":
            violations.extend(
                _check_asset_coverage(
                    file_path=ctx.file_path,
                    event_call=event_call,
                    event_name=event_name,
                    content=ctx.content,
                    alias=ctx.alias,
                    routes=ctx.routes,
                    msg_vt001=self._msg_vt001,
                )
            )
        elif event_name == "CapsuleMaterializedEvent":
            violations.extend(
                _check_capsule_coverage(
                    file_path=ctx.file_path,
                    event_call=event_call,
                    capsule_kind_expr=capsule_kind_expr,
                    routes=ctx.routes,
                    msg_vt002=self._msg_vt002,
                )
            )

        return violations

    def investigate(
        self, file_path: Path, content: str, lines: list[str], tree: ast.AST | None
    ) -> list[Violation]:
        """审查向量事务触发协议 - 确保发行方事件被 VectorMaterialProvider 支持。"""

        del lines

        if not self._should_analyze_file(
            file_path=file_path, tree=tree, content=content
        ):
            return []

        if not isinstance(tree, ast.Module):
            # 理论上不会触发：_should_analyze_file 已经保证 tree 为 Module
            raise TypeError(
                "VT001 investigate expects an ast.Module tree after pre-check"
            )
        module_tree: ast.Module = tree

        routes = self._get_routes(file_path)
        if routes is None:
            return []

        alias = _build_alias_map(content, module_tree)
        violations: list[Violation] = []

        ctx = _EventAnalysisContext(
            tree=module_tree,
            file_path=file_path,
            content=content,
            alias=alias,
            routes=routes,
        )

        self._collect_event_violations(ctx=ctx, violations=violations)

        return violations

    def _should_analyze_file(
        self,
        *,
        file_path: Path,
        tree: ast.AST | None,
        content: str,
    ) -> bool:
        """统一执行 VT001 的文件级预检查。"""

        if not _is_target_code_file(file_path):
            return False
        if tree is None or not isinstance(tree, ast.Module):
            return False

        config = self.laws.vt001
        if not getattr(config, "enabled", True):
            return False

        fp_str = str(file_path).replace("\\", "/")
        patterns = normalize_patterns(
            self.config.get_exempt_files(VectorTriggerLawConstants.CODE_VT001)
        )
        if any(fnmatch.fnmatch(fp_str, p) or fp_str.endswith(p) for p in patterns):
            return False

        # 若文件完全不包含 stage_public_event 关键字，可直接跳过，减少遍历
        return "stage_public_event" in content

    def _collect_event_violations(
        self,
        *,
        ctx: _EventAnalysisContext,
        violations: list[Violation],
    ) -> None:
        """遍历模块内所有函数，收集 stage_public_event 相关违规。"""

        for fn in ast.walk(ctx.tree):
            if not isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef):
                continue

            bindings = _build_event_bindings(fn)
            self._collect_function_event_violations(
                fn=fn,
                ctx=ctx,
                bindings=bindings,
                violations=violations,
            )

    def _collect_function_event_violations(
        self,
        *,
        fn: ast.FunctionDef | ast.AsyncFunctionDef,
        ctx: _EventAnalysisContext,
        bindings: EventBindings,
        violations: list[Violation],
    ) -> None:
        """在单个函数体内查找并判定所有 stage_public_event 调用。"""

        for stmt in ast.walk(fn):
            if not isinstance(stmt, ast.Call):
                continue
            if not (
                isinstance(stmt.func, ast.Attribute)
                and stmt.func.attr == "stage_public_event"
            ):
                continue

            event_call = _extract_event_call(stmt, bindings)
            if event_call is None:
                continue

            violations.extend(
                self._process_event_call(
                    ctx=ctx,
                    event_call=event_call,
                )
            )
