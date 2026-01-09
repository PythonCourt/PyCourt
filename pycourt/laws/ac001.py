"""🦆 鸭子类型审查官（AC001/AC002/AC003）

本模块实现 PyCourt 中的“类型偷懒审查官”，负责在静态代码审计阶段
发现和约束以下三类行为：

- AC001: Any 类型滥用
- AC002: 无契约 dict 类型（裸 dict 或 value 为基础类型/Any 的 dict）
- AC003: typing.cast 滥用

设计要点
- 仅依赖 AST 与静态分析，不执行任何运行时代码；
- 所有违规信息均通过 `judges_text.yaml` 中的模板（AC001/AC002/AC003）渲染；
- 配置来源：
  - 集中豁免：`exempt.yaml` → `CourtConfig.get_exempt_files(...)`；
  - 判决文案：`judges_text.yaml` → `CourtConfig.get_judge_template(...)`。
"""

from __future__ import annotations

import ast
import fnmatch
from pathlib import Path
from typing import Final

from pycourt.config.config import CourtConfig
from pycourt.utils import (
    DictContractTypes,
    Violation,
    is_contracted_dict,
    is_root_model_container,
    normalize_patterns,
)


class AnyCastLawConstants:
    """命名空间常量：AC001/AC002/AC003 类型偷懒法条内部使用。"""

    CODE_AC001: Final[str] = "AC001"
    CODE_AC002: Final[str] = "AC002"
    CODE_AC003: Final[str] = "AC003"


class _AC003Context:
    """AC003 内部助手函数共享的最小上下文。"""

    def __init__(
        self,
        *,
        fp_str: str,
        lines: list[str],
    ) -> None:
        self.fp_str = fp_str
        self.lines = lines


def _is_uncontracted_dict(annotation_str: str) -> bool:
    """判断注解字符串是否表示“无契约 dict”并据此触发 AC002。

    规则概要：
    - `dict`（无泛型参数）视为无契约；
    - `RootModel[dict[...]]` 视为受控容器，不算违规；
    - `dict[...]` 且通过 `is_contracted_dict` 判定为“已契约”时不算违规；
    - 其他 `dict[...]` 且 value 为基础类型/Any/嵌套 dict 时视为无契约。
    """
    # 1. 裸 dict（完全无类型）
    if annotation_str == "dict":
        return True

    # 2. RootModel 包装的 dict 是受控容器，不算违规
    if is_root_model_container(annotation_str):
        return False

    # 3. 有明确契约的 dict 不算违规
    if annotation_str.startswith("dict[") and is_contracted_dict(annotation_str):
        return False

    # 4. 其他 dict[...] 形式，如果 value 类型是基础类型 / Any / 嵌套 dict，则违规
    if annotation_str.startswith("dict["):
        min_dict_parts = 2  # dict 需要至少 2 个泛型参数
        inner = annotation_str[5:-1]
        parts = inner.split(",", 1)

        if len(parts) < min_dict_parts:
            return True  # 不完整的泛型

        value_type = parts[1].strip()

        return (
            value_type in DictContractTypes.BASIC_VALUE_TYPES
            or value_type.startswith("dict[")
        )

    return False


def _inspect_annotation_node(
    node: ast.AST | None,
) -> list[tuple[str, str]]:
    """审查一个AST注解节点，如果发现违规，则返回单一违规代码列表。

    约定：
    - 同一个注解至多触发一条 AC 系列法条；
    - dict 相关优先判为 AC002（无契约 dict），否则再判 AC001（Any 滥用）。

    返回格式: [(违规码, 注解字符串)] 或空列表。
    """
    if node is None:
        return []

    # 使用 ast.unparse 将AST节点转换回字符串形式，以便进行检查
    annotation_str = ast.unparse(node)

    # 1. dict 相关优先：如果是无契约 dict，则只判 AC002
    if _is_uncontracted_dict(annotation_str):
        return [(AnyCastLawConstants.CODE_AC002, annotation_str)]

    # 2. 其他场景下，再检查 Any 滥用 → AC001
    if "Any" in annotation_str:
        return [(AnyCastLawConstants.CODE_AC001, annotation_str)]

    return []


class TheAnyCastLaw:
    """🏛️ 鸭子类型审查官（AC001/AC002/AC003）。

    职责
    - AC001: 检测类型注解中对 Any 的依赖，并引导开发者引入显式契约类型；
    - AC002: 检测无契约的 dict 使用，引导通过 RootModel/DTO/TypedDict 等建模；
    - AC003: 检测滥用 `typing.cast` 的场景，引导从源头修正类型而非强转。

    数据来源
    - 输入：
      - ``file_path``: 当前被审查的文件路径；
      - ``content`` / ``lines``: 文件原始文本及逐行拆分结果；
      - ``tree``: 由法院统一构建的 AST 抽象语法树；
    - 配置：
      - ``self.laws.ac001``: 无结构数据法条配置（边界函数白名单等）；
      - ``self.laws.ac003``: cast 滥用法条配置（证据窗口等）。

    输出
    - 返回一组 :class:`Violation`，每条包含：文件、行列号、法条编号（AC001/2/3）、
      以及由模板渲染的详细说明。
    """

    def __init__(self, config: CourtConfig) -> None:
        """接入 CourtConfig：法典 + 文案 + 集中豁免。"""

        self.config = config
        self.laws = config.laws
        # 预先解析 AC 系列判决模板，避免在违规处重复查表
        self._msg_ac001: str = self.config.get_judge_template(
            AnyCastLawConstants.CODE_AC001
        )
        self._msg_ac002: str = self.config.get_judge_template(
            AnyCastLawConstants.CODE_AC002
        )
        self._msg_ac003: str = self.config.get_judge_template(
            AnyCastLawConstants.CODE_AC003
        )

    def _is_rootmodel_class(self, class_node: ast.ClassDef) -> bool:
        """判断给定类是否继承自 Pydantic 的 ``RootModel``。

        用于在 UD 规则中识别“受控容器”场景：
        - RootModel 本身用于包裹底层 dict/列表等结构，不应被视为“无契约”；
        - 当类继承自 RootModel[T] 时，对应的 `root` 字段可免于 AC002 检查。
        """

        for base in class_node.bases:
            if isinstance(base, ast.Name) and base.id == "RootModel":
                return True
            if (
                isinstance(base, ast.Subscript)
                and isinstance(base.value, ast.Name)
                and base.value.id == "RootModel"
            ):
                return True
        return False

    def _collect_allowed_funcs(self, file_path: Path) -> set[str]:
        """计算当前文件的边界函数白名单。

        历史上曾通过 laws.ac001.payload.boundary_function_allowlist 提供
        细粒度配置；当前系统已移除 laws.yaml，因此这里统一返回空集，
        逻辑上等价于“无边界函数豁免”。
        """

        # 保留参数以兼容调用签名
        _ = file_path
        return set()

    def _handle_function_annotations(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_path: Path,
        allowed_funcs: set[str],
        violations: list[Violation],
    ) -> None:
        """对单个函数的所有参数和返回值执行 AC001/AC002 审查。

        审查逻辑
        - 若函数名位于 ``allowed_funcs`` 中，则视为“边界函数”，整体跳过 AC001/AC002；
        - 否则分别对参数和返回值注解执行审查逻辑。
        """

        if node.name in allowed_funcs:
            return

        self._handle_parameter_annotations(
            node=node,
            file_path=file_path,
            violations=violations,
        )
        self._handle_return_annotation(
            node=node,
            file_path=file_path,
            violations=violations,
        )

    def _handle_parameter_annotations(
        self,
        *,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_path: Path,
        violations: list[Violation],
    ) -> None:
        """对函数参数注解执行 AC001/AC002 审查。"""

        for arg in node.args.args + node.args.kwonlyargs:
            for code, type_hint in _inspect_annotation_node(arg.annotation):
                if code == AnyCastLawConstants.CODE_AC001:
                    base = self._msg_ac001.format(
                        target_name=arg.arg,
                        annotation_str=type_hint,
                    )
                elif code == AnyCastLawConstants.CODE_AC002:
                    base = self._msg_ac002.format(
                        target_name=arg.arg,
                        annotation_str=type_hint,
                    )
                else:
                    # 理论上不会出现其他 code，防御性忽略
                    continue

                message = base + f"\n📌 函数: {node.name}"

                violations.append(
                    Violation(
                        file_path,
                        node.lineno,
                        node.col_offset,
                        code,
                        message,
                    )
                )

    def _handle_return_annotation(
        self,
        *,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_path: Path,
        violations: list[Violation],
    ) -> None:
        """对函数返回值注解执行 AC001/AC002 审查。"""

        for code, type_hint in _inspect_annotation_node(node.returns):
            target_name = f"{node.name}.return"
            if code == AnyCastLawConstants.CODE_AC001:
                base = self._msg_ac001.format(
                    target_name=target_name,
                    annotation_str=type_hint,
                )
            elif code == AnyCastLawConstants.CODE_AC002:
                base = self._msg_ac002.format(
                    target_name=target_name,
                    annotation_str=type_hint,
                )
            else:
                # 理论上不会出现其他 code，防御性忽略
                continue

            message = base + "\n📋 位置: 返回值"

            violations.append(
                Violation(
                    file_path,
                    node.lineno,
                    node.col_offset,
                    code,
                    message,
                )
            )

    def _handle_annassign_annotations(
        self,
        node: ast.AnnAssign,
        file_path: Path,
        in_root_model: bool,
        violations: list[Violation],
    ) -> None:
        """检查带注解赋值（AnnAssign）的类型注解。

        适用范围
        - 模块级常量：``FOO: dict[str, Any] = ...``；
        - 类属性：``class X: data: dict[str, Any]``；
        - 局部变量：``data: dict[str, Any] = ...``。

        特殊规则
        - 若处于 RootModel 派生类内部，且目标名为 ``root``，则跳过 UD 检查；
        - 其余场景根据 `_inspect_annotation_node` 的 AC001/AC002 结果渲染模板。
        """

        target_name = self._resolve_annassign_target_name(node.target)

        if in_root_model and target_name == "root":
            return

        self._record_annassign_violations(
            node=node,
            file_path=file_path,
            target_name=target_name,
            violations=violations,
        )

    def _resolve_annassign_target_name(self, target: ast.expr) -> str:
        """根据 AnnAssign 目标节点推导人类可读的名称。"""

        target_name = "<unknown>"
        match target:
            case ast.Name():
                target_name = target.id
            case ast.Attribute():
                target_name = target.attr
            case ast.Subscript():
                target_name = "subscript"
            case _:
                pass
        return target_name

    def _record_annassign_violations(
        self,
        *,
        node: ast.AnnAssign,
        file_path: Path,
        target_name: str,
        violations: list[Violation],
    ) -> None:
        """根据注解节点产出 AC001/AC002 违规记录。"""

        for code, annotation_str in _inspect_annotation_node(node.annotation):
            if code == AnyCastLawConstants.CODE_AC001:
                message = self._msg_ac001.format(
                    target_name=target_name,
                    annotation_str=annotation_str,
                )
            elif code == AnyCastLawConstants.CODE_AC002:
                message = self._msg_ac002.format(
                    target_name=target_name,
                    annotation_str=annotation_str,
                )
            else:
                # 理论上不会出现其他 code，防御性忽略
                continue

            violations.append(
                Violation(
                    file_path,
                    node.lineno,
                    node.col_offset,
                    code,
                    message,
                )
            )

    def _walk_ast_for_unstructured_data(
        self,
        node: ast.AST,
        file_path: Path,
        allowed_funcs: set[str],
        violations: list[Violation],
        in_root_model: bool,
    ) -> None:
        """在整个 AST 上执行 UD 审查（AC001/AC002）。

        遍历策略
        - 若遇到类定义：先判断是否为 RootModel 子类，再对子节点递归调用；
        - 若遇到函数定义：调用 :meth:`_handle_function_annotations`；
        - 若遇到 AnnAssign：调用 :meth:`_handle_annassign_annotations`；
        - 其他节点：递归遍历子节点。

        该方法不直接产出消息，而是通过传入的 ``violations`` 列表收集
        所有发现的 AC001/AC002 违规。
        """

        if isinstance(node, ast.ClassDef):
            is_root_model = self._is_rootmodel_class(node)
            for child in node.body:
                self._walk_ast_for_unstructured_data(
                    child,
                    file_path,
                    allowed_funcs,
                    violations,
                    in_root_model=is_root_model,
                )
            return

        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            self._handle_function_annotations(
                node, file_path, allowed_funcs, violations
            )

        if isinstance(node, ast.AnnAssign):
            self._handle_annassign_annotations(
                node, file_path, in_root_model, violations
            )

        for child_node in ast.iter_child_nodes(node):
            self._walk_ast_for_unstructured_data(
                child_node,
                file_path,
                allowed_funcs,
                violations,
                in_root_model=in_root_model,
            )

    def _build_ac003_context(
        self,
        *,
        file_path: Path,
        lines: list[str],
    ) -> _AC003Context | None:
        """基于 AC001 配置与豁免信息构造 AC003 执法上下文。

        当前实现仅依赖：
        - laws.ac001.enabled 作为 AC 系列整体开关；
        - AC003 的集中豁免表（exempt.yaml → AC003.files）。
        """

        raw_law_cfg = self.laws.ac001
        enabled = getattr(raw_law_cfg, "enabled", True)
        if not bool(enabled):
            return None

        fp_str = str(file_path)
        if self._is_cast_exempt_file(fp_str):
            return None

        return _AC003Context(fp_str=fp_str, lines=lines)

    def _check_cast_abuse(
        self,
        file_path: Path,
        content: str,
        lines: list[str],
        tree: ast.AST | None,
    ) -> list[Violation]:
        """执行 AC003 审查：根据 AC003 配置检测 ``typing.cast`` 使用。"""
        violations: list[Violation] = []

        ctx = self._build_ac003_context(file_path=file_path, lines=lines)
        if ctx is None:
            return violations

        if tree is None:
            self._scan_cast_in_text_mode(
                file_path=file_path,
                content=content,
                violations=violations,
                ctx=ctx,
            )
            return violations

        cast_lines = self._collect_cast_call_lines(tree)
        self._collect_cast_violations_from_lines(
            file_path=file_path,
            cast_lines=cast_lines,
            violations=violations,
            ctx=ctx,
        )
        return violations

    def _is_cast_exempt_file(self, fp_str: str) -> bool:
        """返回当前文件是否被 AC003 集中豁免表豁免。"""

        patterns = normalize_patterns(
            self.config.get_exempt_files(AnyCastLawConstants.CODE_AC003)
        )
        return any(fnmatch.fnmatch(fp_str, p) or fp_str.endswith(p) for p in patterns)

    def _has_adjacent_evidence(
        self,
        *,
        ctx: _AC003Context,
        idx: int,
    ) -> bool:
        """检查指定行附近是否存在 ``cast justified:`` 证据注释。

        历史上支持 per-file 证据窗口覆盖（evidence_window_overrides），
        但随着 laws.yaml 的移除，目前统一使用固定窗口大小。
        """

        window = 2
        start = max(0, idx - window)
        end = min(len(ctx.lines) - 1, idx + window)
        return any("cast justified:" in ctx.lines[j] for j in range(start, end + 1))

    def _scan_cast_in_text_mode(
        self,
        *,
        file_path: Path,
        content: str,
        violations: list[Violation],
        ctx: _AC003Context,
    ) -> None:
        """在无法获得 AST 时，退化为基于文本的 cast(...) 扫描。"""

        if "cast(" not in content:
            return

        for line_num, line in enumerate(ctx.lines, 1):
            if "cast(" not in line or line.strip().startswith("#"):
                continue

            if self._has_adjacent_evidence(
                ctx=ctx,
                idx=line_num - 1,
            ):
                continue

            stripped = line.strip()
            expr = (
                stripped[stripped.index("cast(") :] if "cast(" in stripped else stripped
            )
            message = self._msg_ac003.format(
                target_name="cast",
                annotation_str=expr,
            )

            violations.append(
                Violation(
                    file_path=file_path,
                    line=line_num,
                    col=0,
                    code=AnyCastLawConstants.CODE_AC003,
                    message=message,
                )
            )

    def _collect_cast_call_lines(self, tree: ast.AST) -> set[int]:
        """从 AST 中收集所有 ``cast(...)`` 调用所在的行号。"""

        cast_lines: set[int] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if (isinstance(func, ast.Name) and func.id == "cast") or (
                isinstance(func, ast.Attribute) and func.attr == "cast"
            ):
                lineno = getattr(node, "lineno", 0)
                if lineno > 0:
                    cast_lines.add(lineno)
        return cast_lines

    def _collect_cast_violations_from_lines(
        self,
        *,
        file_path: Path,
        cast_lines: set[int],
        violations: list[Violation],
        ctx: _AC003Context,
    ) -> None:
        """根据 AST 收集到的 cast 行号生成 AC003 违规记录。"""

        for line_num in sorted(cast_lines):
            idx = line_num - 1
            if self._has_adjacent_evidence(
                ctx=ctx,
                idx=idx,
            ):
                continue

            stripped = (
                ctx.lines[idx].strip() if 0 <= idx < len(ctx.lines) else "cast(...)"
            )
            message = self._msg_ac003.format(
                target_name="cast",
                annotation_str=stripped,
            )

            violations.append(
                Violation(
                    file_path=file_path,
                    line=line_num,
                    col=0,
                    code=AnyCastLawConstants.CODE_AC003,
                    message=message,
                )
            )

    def investigate(
        self, file_path: Path, content: str, lines: list[str], tree: ast.AST | None
    ) -> list[Violation]:
        """对单个 Python 源文件执行 AC 系列审查（AC001/AC002/AC003）。

        检查范围
        - AC001: 函数参数/返回值以及 AnnAssign 中的 Any 类型滥用；
        - AC002: 函数参数/返回值以及 AnnAssign 中的无契约 dict 类型；
        - AC003: 源码中出现的 ``typing.cast`` 调用及相关证据注释。

        执行步骤
        1. 根据 AC001 集中豁免表（exempt.yaml → AC001）跳过特定文件；
        2. 调用 :meth:`_check_cast_abuse` 执行 AC003 审查；
        3. 若 AC001 启用且存在 AST：
           - 计算当前文件中的边界函数集合；
           - 调用 :meth:`_walk_ast_for_unstructured_data` 执行 AC001/AC002 审查；
        4. 返回收集到的所有 :class:`Violation` 实例。
        """
        violations: list[Violation] = []

        # 文件级豁免检查（路径由 AC001 集中豁免表管理）
        config = self.laws.ac001
        fp_str = str(file_path)
        patterns = normalize_patterns(
            self.config.get_exempt_files(AnyCastLawConstants.CODE_AC001)
        )
        if any(fnmatch.fnmatch(fp_str, p) or fp_str.endswith(p) for p in patterns):
            return violations

        # AC003: Cast 滥用检查（尽量依赖 AST，无法解析时回退到文本扫描）
        violations.extend(self._check_cast_abuse(file_path, content, lines, tree))

        # AC001/AC002: Any 和无契约 dict 检查（需要 AST）
        if not config.enabled or tree is None:
            return violations

        allowed_funcs = self._collect_allowed_funcs(file_path)
        self._walk_ast_for_unstructured_data(
            tree,
            file_path,
            allowed_funcs,
            violations,
            in_root_model=False,
        )

        return violations
