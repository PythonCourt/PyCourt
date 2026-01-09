"""🏛️ HC 系列法官（配置优先 / 单一豁免 / 精简版草稿）

目标设计：
- 所有可调参数（名称 token、阈值、字符串豁免片段等）全部 YAML 化，
  由 `tools/court/yaml/config.yaml -> laws.hc001.*` 提供；
- Python 代码只保留算法和结构性规则，不再写死任何“业务含义”的常量；
- 路径豁免只有一种视角：`HC001` 治外法权文件 → 整个 HC 系列(001–007) 全部不审；
- 只有一个路径豁免方法 `_is_file_exempt`，且只在总入口 `investigate` 顶部调用一次；
- 公共工具方法集中放在一处，HC001/HC002/HC003/HC004/HC005 全部复用。

YAML 期望结构（示意）：

.. code-block:: yaml

   laws:
     hc001:
       enabled: true
       exempt_files: []
       description: "HC 系列（硬编码/常量/数值魔法）统一配置入口"

       # constants 相关
       module_patterns: ["constants.py", "constants/", "/constants/"]
       naked_const_exempt_patterns: ["__init__.py", "conftest.py", "test_", "_test.py"]
       system_const_prefixes: ["Final", "Literal", "TypeVar", "Generic", "Protocol", "Callable", "ClassVar", "Annotated"]
       allowed_naked_patterns: ["_LOGGER", "_LOG", "LOGGER_NAME"]
       typevar_pattern: "^[A-Z]$"

       # strings 相关
       exclude_substrings: ["test", "example", "debug", "log"]
       report_generator_files: []
       exempt_strings: ["..."]
       logger_prefixes: ["logger.", "logging.", "log."]
       exception_call_prefixes: ["raise "]
       typealias_keywords: ["TypeAlias"]
       fstring_prefixes: ["f\"", "f'"]

       # numeric_params 相关
       int_max: 5000
       min_control_value: 2
       strong_name_tokens: ["label_threshold_", "high_score_threshold", "score_threshold"]
       weak_name_tokens: ["threshold", "weight", "ratio", "score", "prob", "confidence"]
       control_tokens: ["retry", "retries", "attempt", "attempts", "top_", "max_", "min_", "limit", "window", "size", "timeout", "batch"]
       exempt_names: ["_NUMERIC_MIN_CONTROL_VALUE"]

填满 HCConfig 所需字段后，本文件作为 HC 系列法官的统一实现，
用于替换历史版 `hc001.py`，实现更简洁且配置驱动的 HC 审计逻辑。
"""

from __future__ import annotations

import ast
import fnmatch
import re
from pathlib import Path
from typing import Final

from pycourt.config.config import (
    CourtConfig,
    HCConfig,
)
from pycourt.utils import Violation, normalize_patterns

# ============================================================================
# 一、配置契约：强类型描述 laws.hc001.config
# （具体模型定义集中在 tools.court.config 中，这里只做导入使用）
# ============================================================================


# ============================================================================
# 二、HC 法官：单一路径豁免 + 共享工具 + 多条法则
# ============================================================================


class TheHardcodingLaw:
    """🏛️ HC 系列法官（001–005）统一实现（新版草稿）。

    - HC001: 硬编码字符串检测
    - HC002: 裸常量导入检测
    - HC003: 裸常量定义检测
    - HC004: 跨引擎常量导入检测
    - HC005: 数值魔法（可调业务参数）检测

    兼容性约定（与旧版 `hc001.py` 行为对齐）：
    - 路径豁免仍按法条编号拆分：HC001 / HC001_COMPAT_FILES /
      HC001_REPORT_GENERATOR_FILES / HC005 等；
    - 本实现仅调整配置来源（改为 `config.yaml -> laws.hc001.*` + HCConfig），
      不改变这些法条级豁免语义与审计算法的 1:1 行为。
    """

    CODE_HC001: Final[str] = "HC001"
    CODE_HC002: Final[str] = "HC002"
    CODE_HC003: Final[str] = "HC003"
    CODE_HC004: Final[str] = "HC004"
    CODE_HC005: Final[str] = "HC005"

    KEY_HC001_REPORT_GENERATOR_FILES: Final[str] = "HC001_REPORT_GENERATOR_FILES"
    KEY_HC001_COMPAT_FILES: Final[str] = "HC001_COMPAT_FILES"

    # 非业务含义的算法常量：mapping.get(key, default) 的典型参数个数。
    _MAPPING_GET_ARG_COUNT: Final[int] = 2

    def __init__(self, config: CourtConfig) -> None:
        self.config = config
        self.laws = config.laws

        # 判决模板由 CourtConfig 提供，不走 HC 配置。
        self._msg_hc001 = self.config.get_judge_template(self.CODE_HC001)
        self._msg_hc002 = self.config.get_judge_template(self.CODE_HC002)
        self._msg_hc003 = self.config.get_judge_template(self.CODE_HC003)
        self._msg_hc004 = self.config.get_judge_template(self.CODE_HC004)
        self._msg_hc005 = self.config.get_judge_template(self.CODE_HC005)

        # === 核心：从 CourtConfig.hc 读取 HC 系列家族配置 ===
        self._payload: HCConfig = config.hc

    # ------------------------------------------------------------------
    # 路径豁免：HC001 顶层 + 法条级豁免（保持旧版行为）
    # ------------------------------------------------------------------

    def _match_file_patterns(self, file_path: Path, patterns: list[str]) -> bool:
        """在给定路径上应用统一的 fnmatch/endswith 模式匹配逻辑。"""

        if not patterns:
            return False

        fp_str = str(file_path)
        normalized = normalize_patterns(patterns)
        return any(
            fnmatch.fnmatch(fp_str, pattern) or fp_str.endswith(pattern)
            for pattern in normalized
        )

    def _is_file_exempt(self, file_path: Path) -> bool:
        """根据 HC001.files 路径豁免，判断文件是否在整个 HC 系列下治外法权。

        与旧版一致：这里只处理“完全不审”的文件集合，其余 HC00x 级别的
        豁免（例如 HC001_COMPAT_FILES、HC001_REPORT_GENERATOR_FILES、HC005）
        仍由各自规则内部处理。
        """

        patterns = self.config.get_exempt_files(self.CODE_HC001)
        return self._match_file_patterns(file_path, patterns)

    # ------------------------------------------------------------------
    # 对外总入口：统一执行 HC001–HC007
    # ------------------------------------------------------------------

    def investigate(
        self,
        file_path: Path,
        content: str,
        lines: list[str],
        tree: ast.AST | None,
    ) -> list[Violation]:
        """审查代码中的 HC001–HC005 相关违规。

        - 唯一路径豁免 `_is_file_exempt` 在这里统一处理；
        - 之后 HC001–HC005 都只依赖 AST 与 HCConfig，不再使用路径级特殊逻辑。
        """

        del content  # HC 系列不直接使用整文件文本

        if self._is_file_exempt(file_path):
            return []

        violations: list[Violation] = []

        # HC002–HC007: 基于 AST 的结构性检查
        if tree is not None:
            violations.extend(self._check_hc002_naked_imports(file_path, tree))
            violations.extend(self._check_hc003_naked_defs(file_path, tree))
            violations.extend(self._check_hc004_cross_engine(file_path, tree))
            violations.extend(
                self._check_hc005_numeric_magic(
                    file_path=file_path,
                    tree=tree,
                    lines=lines,
                )
            )

        # 硬编码字符串逐行检查（HC001）
        violations.extend(self._check_hc001_strings(file_path, lines, tree))

        return violations

    # =====================================================================
    # 共享工具：AST / 数值 / 命名模式
    # =====================================================================

    # ---- 常量配置访问 ----

    # 以下三个 property 保留原有语义，仅作为命名分区帮助阅读。

    @property
    def _const_cfg(self) -> HCConfig:
        return self._payload

    @property
    def _str_cfg(self) -> HCConfig:
        return self._payload

    @property
    def _num_cfg(self) -> HCConfig:
        return self._payload

    # ---- 命名模式 & 裸常量相关 ----

    def _is_constants_module(self, file_path: Path) -> bool:
        fp_str = str(file_path)
        return any(pattern in fp_str for pattern in self._const_cfg.module_patterns)

    def _is_naked_const_exempt_file(self, file_path: Path) -> bool:
        fp_str = str(file_path)
        return any(
            pattern in fp_str for pattern in self._const_cfg.naked_const_exempt_patterns
        )

    def _is_upper_snake_case(self, name: str) -> bool:
        if not name:
            return False
        return bool(re.match(r"^[A-Z][A-Z0-9_]*$", name)) or name.isupper()

    def _is_system_typing_const(self, name: str) -> bool:
        return name in self._const_cfg.system_const_prefixes

    def _should_skip_naked_const(self, name: str) -> bool:
        cfg = self._const_cfg

        if name.startswith("__") and name.endswith("__"):
            return True
        if name.startswith("_"):
            return True
        if not self._is_upper_snake_case(name):
            return True
        if name in cfg.system_const_prefixes:
            return True
        if re.match(cfg.typevar_pattern, name):
            return True
        return any(pat in name for pat in cfg.allowed_naked_patterns)

    def _extract_naked_const_name(self, node: ast.stmt) -> str | None:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name = target.id
                    if not self._should_skip_naked_const(name):
                        return name
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
            if self._should_skip_naked_const(name):
                return None
            if isinstance(node.annotation, ast.Subscript):
                ann_str = ast.unparse(node.annotation)
                if "Final[Literal[" in ann_str:
                    return None
            return name
        return None

    # ---- AST & 数值工具 ----

    @staticmethod
    def _eval_numeric_literal(expr: ast.AST) -> float | int | None:
        try:
            value = ast.literal_eval(expr)
        except Exception:  # pragma: no cover - 防御性
            return None
        return value if isinstance(value, (int, float)) else None

    @staticmethod
    def _get_assign_target_name(target: ast.expr) -> str | None:
        if isinstance(target, ast.Name):
            return target.id
        if isinstance(target, ast.Attribute):
            return target.attr
        if isinstance(target, ast.Subscript):
            base = None
            index = None

            value = target.value
            if isinstance(value, ast.Name):
                base = value.id
            elif isinstance(value, ast.Attribute):
                base = value.attr

            slc = target.slice
            if isinstance(slc, ast.Constant) and isinstance(slc.value, str):
                index = slc.value
            if base and index:
                return f"{base}.{index}"
            return base
        return None

    # ---- HC005 名称 token & 豁免工具（与旧版兼容） ----

    def _get_numeric_param_tokens(self) -> tuple[list[str], list[str]]:
        """从 payload.numeric_params 中读取名称 token 配置。

        完全 YAML 驱动：
        - strong_name_tokens: 强语义 label/score 名称 token；
        - weak_name_tokens: 其余用于数值启发式判断的通用 token（同时服务于
          浮点与整型场景）。
        """

        strong_tokens = list(self._num_cfg.strong_name_tokens)
        weak_tokens = list(self._num_cfg.weak_name_tokens)
        return strong_tokens, weak_tokens

    def _get_numeric_param_exemptions(self) -> tuple[list[str], list[str]]:
        """读取 HC005 数值豁免配置（文件级 + 名称级）。

        与旧版约定保持一致：
        - 文件级豁免：`exempt.yaml` → CourtConfig.get_exempt_files("HC005")；
        - 名称级豁免：payload.numeric_params.exempt_names。
        """

        file_patterns = self.config.get_exempt_files(self.CODE_HC005)
        exempt_names = list(self._num_cfg.exempt_names)
        return file_patterns, exempt_names

    def _is_strong_label_param(self, lowered: str, value: float | int) -> bool:
        """强语义 label/score 阈值，只看名称即可视为可调参数。

        名称 token 完全由 YAML 的 numeric_params.strong_name_tokens 提供。
        """

        del value  # 当前仅依赖名称进行判断
        strong_tokens, _ = self._get_numeric_param_tokens()
        return any(tok.lower() in lowered for tok in strong_tokens)

    def _is_float_threshold_param(self, lowered: str, value: float | int) -> bool:
        """0~1 之间的浮点阈值/权重（以名称 token 辅助判断）。"""

        if not (isinstance(value, float) and 0.0 < value < 1.0):
            return False

        _, weak_tokens = self._get_numeric_param_tokens()
        return any(tok.lower() in lowered for tok in weak_tokens)

    def _is_int_limit_param(self, lowered: str, value: float | int) -> bool:
        """整型上限/窗口/批大小等启发式参数（以名称 token 辅助判断）。"""

        int_max = self._get_numeric_int_max()
        if not (isinstance(value, int) and 1 <= value <= int_max):
            return False

        # 这里沿用 weak_name_tokens 作为整型场景的主名称 token 集合，具体
        # token 由 YAML 控制（默认值与旧版 _NUMERIC_INT_KEYS 对齐）。
        _, weak_tokens = self._get_numeric_param_tokens()
        return any(tok.lower() in lowered for tok in weak_tokens)

    def _build_numeric_token_context(
        self,
    ) -> tuple[list[str], list[str], list[str], int]:
        """构建数值检测所需的名称 token 集合与整型上限。

        完全 YAML 驱动：
        - strong_name_tokens/weak_name_tokens 由 numeric_params 提供；
        - 整型上限由 numeric_params.int_max 提供。
        """

        strong_cfg, weak_cfg = self._get_numeric_param_tokens()
        strong_tokens = [t.lower() for t in strong_cfg]
        float_tokens = [t.lower() for t in weak_cfg]
        int_tokens = [t.lower() for t in weak_cfg]
        int_max = self._get_numeric_int_max()
        return strong_tokens, float_tokens, int_tokens, int_max

    def _get_numeric_int_max(self) -> int:
        """从配置中读取 HC005 的整型上限阈值。

        约束交由 Pydantic 模型保证（int_max > 0），此处直接返回。
        """

        return self._num_cfg.int_max

    def _get_min_control_value(self) -> int:
        return self._num_cfg.min_control_value

    def _get_control_tokens(self) -> list[str]:
        return [t.lower() for t in self._num_cfg.control_tokens]

    @staticmethod
    def _is_name_exempt_for_numeric(name: str, exempt_names: list[str]) -> bool:
        return any(token and token in name for token in exempt_names)

    # =====================================================================
    # 裸常量导入（HC002）
    # =====================================================================

    def _check_hc002_naked_imports(
        self, file_path: Path, tree: ast.AST
    ) -> list[Violation]:
        violations: list[Violation] = []

        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.ImportFrom)
                and node.module
                and "constants" in node.module
            ):
                continue

            for alias in node.names:
                name = alias.name
                if self._is_system_typing_const(name):
                    continue
                if name == "*":
                    continue
                if self._is_upper_snake_case(name):
                    violations.append(
                        Violation(
                            file_path=file_path,
                            line=node.lineno,
                            col=node.col_offset,
                            code=self.CODE_HC002,
                            message=self._msg_hc002.format(name=name),
                        )
                    )

        return violations

    # =====================================================================
    # 裸常量定义（HC003）
    # =====================================================================

    def _check_hc003_naked_defs(
        self, file_path: Path, tree: ast.AST
    ) -> list[Violation]:
        if self._is_constants_module(file_path):
            return []
        if self._is_naked_const_exempt_file(file_path):
            return []
        if not isinstance(tree, ast.Module):
            return []

        violations: list[Violation] = []
        for node in tree.body:
            name = self._extract_naked_const_name(node)
            if name is None:
                continue
            violations.append(
                Violation(
                    file_path=file_path,
                    line=getattr(node, "lineno", 1),
                    col=getattr(node, "col_offset", 0),
                    code=self.CODE_HC003,
                    message=self._msg_hc003.format(name=name),
                )
            )

        return violations

    # =====================================================================
    # 跨引擎常量导入（HC004）
    # =====================================================================

    @staticmethod
    def _extract_engine_name(file_path: Path) -> str | None:
        parts = file_path.parts
        for i, part in enumerate(parts):
            if part == "engines" and i + 1 < len(parts):
                return parts[i + 1]
        return None

    def _check_hc004_cross_engine(
        self, file_path: Path, tree: ast.AST
    ) -> list[Violation]:
        current_engine = self._extract_engine_name(file_path)
        if not current_engine:
            return []

        violations: list[Violation] = []
        for node in ast.walk(tree):
            if not (isinstance(node, ast.ImportFrom) and node.module):
                continue
            module = node.module
            if "engines" not in module or "constants" not in module:
                continue

            match = re.search(r"engines\.(\w+)", module)
            if not match:
                continue
            imported_engine = match.group(1)
            if imported_engine == current_engine:
                continue

            violations.append(
                Violation(
                    file_path=file_path,
                    line=node.lineno,
                    col=node.col_offset,
                    code=self.CODE_HC004,
                    message=self._msg_hc004.format(source=module),
                )
            )

        return violations

    # =====================================================================
    # 数值魔法（可调业务参数）（HC005）——与旧版逻辑对齐
    # =====================================================================

    def _is_suspicious_numeric(
        self,
        *,
        name: str | None,
        value: float | int,
        context: str,
    ) -> bool:
        """启发式判断是否为可调业务参数的魔法数值。

        逻辑从旧版 `hc001.py` 直接迁移，仅将配置来源改为 `_num_cfg`。
        """

        lowered = (name or "").lower()
        strong_tokens, float_tokens, int_tokens, int_max = (
            self._build_numeric_token_context()
        )

        # 1) 历史上的强语义规则，保证兼容性
        if self._is_strong_label_param(lowered, value):
            return True
        if self._is_float_threshold_param(lowered, value):
            return True
        if self._is_int_limit_param(lowered, value):
            return True

        # 2) 简单的全局豁免：典型哨兵值（0/1/-1），除非命中强 token
        if self._is_globally_exempt_sentinel(lowered, value, strong_tokens):
            return False

        # 3) 按数值类型分派更细粒度规则
        if isinstance(value, float):
            return self._is_suspicious_float_value(
                lowered=lowered,
                value=value,
                context=context,
                strong_tokens=strong_tokens,
                float_tokens=float_tokens,
            )

        # _eval_numeric_literal 仅返回 int 或 float，且上方已处理 float 分支，
        # 此处可以安全地将剩余情况视为 int 参数。
        int_ctx = (strong_tokens, int_tokens, int_max)
        return self._is_suspicious_int_value(
            lowered=lowered,
            value=value,
            context=context,
            int_ctx=int_ctx,
        )

    @staticmethod
    def _is_globally_exempt_sentinel(
        lowered: str,
        value: float | int,
        strong_tokens: list[str],
    ) -> bool:
        """是否属于全局豁免的典型哨兵值（0/1/-1）。"""

        return (
            isinstance(value, int)
            and value in (-1, 0, 1)
            and not any(tok in lowered for tok in strong_tokens)
        )

    def _is_suspicious_float_value(
        self,
        *,
        lowered: str,
        value: float,
        context: str,
        strong_tokens: list[str],
        float_tokens: list[str],
    ) -> bool:
        """0~1 区间浮点阈值/权重的可疑性判断。"""

        if not 0.0 < value < 1.0:
            return False

        if any(tok in lowered for tok in strong_tokens + float_tokens):
            return True

        return context in ("compare", "default", "kwarg")

    def _is_suspicious_int_value(
        self,
        *,
        lowered: str,
        value: int,
        context: str,
        int_ctx: tuple[list[str], list[str], int],
    ) -> bool:
        """整型窗口/上限参数的可疑性判断。"""

        strong_tokens, int_tokens, int_max = int_ctx

        if not 1 <= value <= int_max:
            return False

        if any(tok in lowered for tok in strong_tokens + int_tokens):
            return True

        if value < self._get_min_control_value():
            return False
        if context not in ("compare", "default", "kwarg"):
            return False

        control_tokens = self._get_control_tokens()
        return any(token in lowered for token in control_tokens)

    def _is_file_exempt_for_numeric(self, file_path: Path) -> bool:
        """判断当前文件是否在 HC005 魔法数值检查的豁免名单中。"""

        exempt_files, _ = self._get_numeric_param_exemptions()
        if not exempt_files:
            return False

        return self._match_file_patterns(file_path, exempt_files)

    def _collect_hc005_assign_violations(
        self,
        *,
        file_path: Path,
        tree: ast.AST,
        lines: list[str],
        exempt_names: list[str],
    ) -> list[Violation]:
        """HC005 - 简单赋值中的数值魔法检查。"""

        violations: list[Violation] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                target_name = self._get_assign_target_name(target)
                if not target_name or self._is_name_exempt_for_numeric(
                    target_name, exempt_names
                ):
                    continue
                value = self._eval_numeric_literal(node.value)
                if value is None or not self._is_suspicious_numeric(
                    name=target_name,
                    value=value,
                    context="assign",
                ):
                    continue
                line = (
                    lines[node.lineno - 1].strip()
                    if 0 < node.lineno <= len(lines)
                    else ""
                )
                violations.append(
                    Violation(
                        file_path=file_path,
                        line=node.lineno,
                        col=getattr(node, "col_offset", 0),
                        code=self.CODE_HC005,
                        message=self._msg_hc005.format(
                            snippet=line[:60] if line else target_name
                        ),
                    )
                )
        return violations

    def _collect_hc005_annassign_violations(
        self,
        *,
        file_path: Path,
        tree: ast.AST,
        lines: list[str],
        exempt_names: list[str],
    ) -> list[Violation]:
        """HC005 - 带类型注解赋值中的数值魔法检查。"""

        violations: list[Violation] = []
        for node in ast.walk(tree):
            if not (isinstance(node, ast.AnnAssign) and node.value is not None):
                continue
            target = node.target
            name: str | None = None
            if isinstance(target, ast.Name):
                name = target.id
            elif isinstance(target, ast.Attribute):
                name = target.attr
            if not name or self._is_name_exempt_for_numeric(name, exempt_names):
                continue
            value = self._eval_numeric_literal(node.value)
            if value is None or not self._is_suspicious_numeric(
                name=name,
                value=value,
                context="annassign",
            ):
                continue
            line = (
                lines[node.lineno - 1].strip() if 0 < node.lineno <= len(lines) else ""
            )
            violations.append(
                Violation(
                    file_path=file_path,
                    line=node.lineno,
                    col=getattr(node, "col_offset", 0),
                    code=self.CODE_HC005,
                    message=self._msg_hc005.format(snippet=line[:60] if line else name),
                )
            )
        return violations

    def _collect_hc005_call_kwarg_violations(
        self,
        *,
        file_path: Path,
        tree: ast.AST,
        lines: list[str],
        exempt_names: list[str],
    ) -> list[Violation]:
        """HC005 - 函数调用关键字参数中的数值魔法检查。"""

        violations: list[Violation] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            for kw in node.keywords or []:
                if kw.arg is None:
                    continue
                kw_name = kw.arg
                if self._is_name_exempt_for_numeric(kw_name, exempt_names):
                    continue
                value = self._eval_numeric_literal(kw.value)
                if value is None or not self._is_suspicious_numeric(
                    name=kw_name,
                    value=value,
                    context="kwarg",
                ):
                    continue
                line = (
                    lines[node.lineno - 1].strip()
                    if 0 < node.lineno <= len(lines)
                    else ""
                )
                violations.append(
                    Violation(
                        file_path=file_path,
                        line=node.lineno,
                        col=getattr(node, "col_offset", 0),
                        code=self.CODE_HC005,
                        message=self._msg_hc005.format(
                            snippet=line[:60] if line else kw_name
                        ),
                    )
                )
        return violations

    def _collect_hc005_call_mapping_get_violations(
        self,
        *,
        file_path: Path,
        tree: ast.AST,
        lines: list[str],
        exempt_names: list[str],
    ) -> list[Violation]:
        """HC005 - mapping.get(key, default) 形式中的数值魔法检查。"""

        del exempt_names  # HC005: mapping.get 默认值不区分名称豁免，仅靠上下文判断

        violations: list[Violation] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and len(node.args) == self._MAPPING_GET_ARG_COUNT
            ):
                continue

            default_expr = node.args[1]
            value = self._eval_numeric_literal(default_expr)
            if value is None:
                continue
            base_name = ast.unparse(node.func.value)
            name = f"{base_name}.default"
            if not self._is_suspicious_numeric(
                name=name,
                value=value,
                context="default",
            ):
                continue
            line = (
                lines[node.lineno - 1].strip() if 0 < node.lineno <= len(lines) else ""
            )
            violations.append(
                Violation(
                    file_path=file_path,
                    line=node.lineno,
                    col=getattr(node, "col_offset", 0),
                    code=self.CODE_HC005,
                    message=self._msg_hc005.format(snippet=line[:60] if line else name),
                )
            )
        return violations

    def _collect_hc005_call_violations(
        self,
        *,
        file_path: Path,
        tree: ast.AST,
        lines: list[str],
        exempt_names: list[str],
    ) -> list[Violation]:
        """HC005 - 函数调用中的数值魔法聚合检查。"""

        violations: list[Violation] = []
        violations.extend(
            self._collect_hc005_call_kwarg_violations(
                file_path=file_path,
                tree=tree,
                lines=lines,
                exempt_names=exempt_names,
            )
        )
        violations.extend(
            self._collect_hc005_call_mapping_get_violations(
                file_path=file_path,
                tree=tree,
                lines=lines,
                exempt_names=exempt_names,
            )
        )
        return violations

    def _collect_hc005_compare_violations(
        self,
        *,
        file_path: Path,
        tree: ast.AST,
        lines: list[str],
        exempt_names: list[str],
    ) -> list[Violation]:
        """HC005 - 比较表达式中的数值魔法（x < 10 / x >= 3 等）。"""

        violations: list[Violation] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            if len(node.comparators) != 1 or not isinstance(
                node.ops[0], (ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq)
            ):
                continue
            left_name: str | None = None
            if isinstance(node.left, ast.Name):
                left_name = node.left.id
            elif isinstance(node.left, ast.Attribute):
                left_name = node.left.attr
            if not left_name or self._is_name_exempt_for_numeric(
                left_name, exempt_names
            ):
                continue
            value = self._eval_numeric_literal(node.comparators[0])
            if value is None or not self._is_suspicious_numeric(
                name=left_name,
                value=value,
                context="compare",
            ):
                continue
            line = (
                lines[node.lineno - 1].strip() if 0 < node.lineno <= len(lines) else ""
            )
            violations.append(
                Violation(
                    file_path=file_path,
                    line=node.lineno,
                    col=getattr(node, "col_offset", 0),
                    code=self.CODE_HC005,
                    message=self._msg_hc005.format(
                        snippet=line[:60] if line else left_name
                    ),
                )
            )
        return violations

    def _collect_hc005_default_positional_violations(
        self,
        *,
        file_path: Path,
        tree: ast.AST,
        lines: list[str],
        exempt_names: list[str],
    ) -> list[Violation]:
        """HC005 - 位置参数默认值中的数值魔法检查。"""

        violations: list[Violation] = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            args = list(getattr(node.args, "args", []))
            defaults = list(getattr(node.args, "defaults", []))
            if not defaults:
                continue

            for param, default_expr in zip(
                args[-len(defaults) :], defaults, strict=True
            ):
                if not isinstance(param, ast.arg):
                    continue
                name = param.arg
                if self._is_name_exempt_for_numeric(name, exempt_names):
                    continue
                value = self._eval_numeric_literal(default_expr)
                if value is None or not self._is_suspicious_numeric(
                    name=name,
                    value=value,
                    context="default",
                ):
                    continue
                line_no = getattr(default_expr, "lineno", node.lineno)
                line = lines[line_no - 1].strip() if 0 < line_no <= len(lines) else ""
                violations.append(
                    Violation(
                        file_path=file_path,
                        line=line_no,
                        col=getattr(default_expr, "col_offset", 0),
                        code=self.CODE_HC005,
                        message=self._msg_hc005.format(
                            snippet=line[:60] if line else name
                        ),
                    )
                )
        return violations

    def _collect_hc005_default_kwonly_violations(
        self,
        *,
        file_path: Path,
        tree: ast.AST,
        lines: list[str],
        exempt_names: list[str],
    ) -> list[Violation]:
        """HC005 - 仅关键字参数默认值中的数值魔法检查。"""

        violations: list[Violation] = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            kwonlyargs = list(getattr(node.args, "kwonlyargs", []))
            kw_defaults = list(getattr(node.args, "kw_defaults", []))
            for param, default_expr in zip(kwonlyargs, kw_defaults, strict=True):
                if default_expr is None or not isinstance(param, ast.arg):
                    continue
                name = param.arg
                if self._is_name_exempt_for_numeric(name, exempt_names):
                    continue
                value = self._eval_numeric_literal(default_expr)
                if value is None or not self._is_suspicious_numeric(
                    name=name,
                    value=value,
                    context="default",
                ):
                    continue
                line_no = getattr(default_expr, "lineno", node.lineno)
                line = lines[line_no - 1].strip() if 0 < line_no <= len(lines) else ""
                violations.append(
                    Violation(
                        file_path=file_path,
                        line=line_no,
                        col=getattr(default_expr, "col_offset", 0),
                        code=self.CODE_HC005,
                        message=self._msg_hc005.format(
                            snippet=line[:60] if line else name
                        ),
                    )
                )
        return violations

    def _collect_hc005_default_violations(
        self,
        *,
        file_path: Path,
        tree: ast.AST,
        lines: list[str],
        exempt_names: list[str],
    ) -> list[Violation]:
        """HC005 - 函数参数默认值中的数值魔法聚合检查。"""

        violations: list[Violation] = []
        violations.extend(
            self._collect_hc005_default_positional_violations(
                file_path=file_path,
                tree=tree,
                lines=lines,
                exempt_names=exempt_names,
            )
        )
        violations.extend(
            self._collect_hc005_default_kwonly_violations(
                file_path=file_path,
                tree=tree,
                lines=lines,
                exempt_names=exempt_names,
            )
        )
        return violations

    def _check_hc005_numeric_magic(
        self,
        *,
        file_path: Path,
        tree: ast.AST,
        lines: list[str],
    ) -> list[Violation]:
        """检查可调业务参数的魔法数值硬编码（HC005）。

        逻辑整体与旧版 `_check_numeric_magic_numbers` 及其子函数保持一致，
        但内部拆分为多个子检查函数以降低单个函数的复杂度。
        """

        if self._is_file_exempt_for_numeric(file_path):
            return []

        _, exempt_names = self._get_numeric_param_exemptions()

        violations: list[Violation] = []
        violations.extend(
            self._collect_hc005_assign_violations(
                file_path=file_path,
                tree=tree,
                lines=lines,
                exempt_names=exempt_names,
            )
        )
        violations.extend(
            self._collect_hc005_annassign_violations(
                file_path=file_path,
                tree=tree,
                lines=lines,
                exempt_names=exempt_names,
            )
        )
        violations.extend(
            self._collect_hc005_call_violations(
                file_path=file_path,
                tree=tree,
                lines=lines,
                exempt_names=exempt_names,
            )
        )
        violations.extend(
            self._collect_hc005_compare_violations(
                file_path=file_path,
                tree=tree,
                lines=lines,
                exempt_names=exempt_names,
            )
        )
        violations.extend(
            self._collect_hc005_default_violations(
                file_path=file_path,
                tree=tree,
                lines=lines,
                exempt_names=exempt_names,
            )
        )

        return violations

    # =====================================================================
    # HC001: 硬编码字符串检测（完整版，尽量 1:1 复刻旧 hc001.py 行为）
    # =====================================================================

    def _get_exclude_substrings(self) -> tuple[str, ...]:
        """返回用于行级快速排除的字符串片段集合（小写）。"""

        return tuple(s.lower() for s in self._str_cfg.exclude_substrings)

    def _get_exempt_strings(self) -> list[str]:
        """返回 HC001 行级豁免字符串片段列表的副本。"""

        return list(self._str_cfg.exempt_strings)

    def _check_hc001_strings(
        self,
        file_path: Path,
        lines: list[str],
        tree: ast.AST | None,
    ) -> list[Violation]:
        """统一执行 HC001 相关字符串扫描（与旧版 investigate_strings_for_file 等价）。"""

        exempt_strings = self._get_exempt_strings()
        gen_range = self._maybe_get_report_range(file_path, tree)
        is_compat_file = self._is_compat_file(file_path)
        docstring_ranges = self._collect_docstring_ranges(tree)

        return self._scan_lines_for_hardcoding(
            file_path=file_path,
            lines=lines,
            exempt_strings=exempt_strings,
            gen_range=gen_range,
            is_compat_file=is_compat_file,
            docstring_ranges=docstring_ranges,
        )

    def _maybe_get_report_range(
        self, file_path: Path, tree: ast.AST | None
    ) -> tuple[int, int] | None:
        """若文件属于报表生成器范围，则返回 generate_report 的行号区间。"""

        patterns = self.config.get_exempt_files(self.KEY_HC001_REPORT_GENERATOR_FILES)
        if self._match_file_patterns(file_path, patterns):
            return self._generate_report_range(tree)
        return None

    def _is_compat_file(self, file_path: Path) -> bool:
        """判断当前文件是否属于兼容性常量容器文件集合。"""

        patterns = self.config.get_exempt_files(self.KEY_HC001_COMPAT_FILES)
        return self._match_file_patterns(file_path, patterns)

    def _collect_docstring_ranges(self, tree: ast.AST | None) -> list[tuple[int, int]]:
        """收集模块 / 类 / 函数级 docstring 的行号区间，用于豁免 HC001。"""

        if tree is None:
            return []

        ranges: list[tuple[int, int]] = []
        for node in ast.walk(tree):
            if (
                isinstance(
                    node,
                    ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
                )
                and node.body
            ):
                first = node.body[0]
                if isinstance(first, ast.Expr):
                    val = getattr(first, "value", None)
                    if isinstance(val, ast.Constant) and isinstance(val.value, str):
                        start = getattr(first, "lineno", None)
                        end = getattr(first, "end_lineno", None)
                        if isinstance(start, int) and isinstance(end, int):
                            ranges.append((start, end))
        return ranges

    def _generate_report_range(self, tree: ast.AST | None) -> tuple[int, int] | None:
        """返回 generate_report 函数的起止行号区间（若存在）。"""

        if tree is None:
            return None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "generate_report":
                end_lineno = getattr(node, "end_lineno", None)
                if isinstance(end_lineno, int):
                    return (node.lineno, end_lineno)
        return None

    def _scan_lines_for_hardcoding(  # noqa: PLR0913
        self,
        *,
        file_path: Path,
        lines: list[str],
        exempt_strings: list[str],
        gen_range: tuple[int, int] | None,
        is_compat_file: bool,
        docstring_ranges: list[tuple[int, int]],
    ) -> list[Violation]:
        """逐行扫描 HC001 硬编码违规（不含 HC002/3/4）。"""

        in_const_block = False
        paren_depth = 0

        in_argparse_block = False
        argparse_depth = 0

        violations: list[Violation] = []

        for line_num, line in enumerate(lines, 1):
            stripped_line = line.strip()
            if not stripped_line or stripped_line.startswith("#"):
                continue
            if self._in_docstring(line_num, docstring_ranges):
                continue

            (
                in_argparse_block,
                argparse_depth,
                in_const_block,
                paren_depth,
                violation,
            ) = self._process_single_line_for_hardcoding(
                file_path=file_path,
                line=line,
                stripped_line=stripped_line,
                line_num=line_num,
                exempt_strings=exempt_strings,
                gen_range=gen_range,
                is_compat_file=is_compat_file,
                in_argparse_block=in_argparse_block,
                argparse_depth=argparse_depth,
                in_const_block=in_const_block,
                paren_depth=paren_depth,
            )

            if violation is not None:
                violations.append(violation)

        return violations

    def _process_single_line_for_hardcoding(  # noqa: PLR0913
        self,
        *,
        file_path: Path,
        line: str,
        stripped_line: str,
        line_num: int,
        exempt_strings: list[str],
        gen_range: tuple[int, int] | None,
        is_compat_file: bool,
        in_argparse_block: bool,
        argparse_depth: int,
        in_const_block: bool,
        paren_depth: int,
    ) -> tuple[bool, int, bool, int, Violation | None]:
        """处理单行 HC001 检查，返回更新后的状态及可能的违规记录。"""

        in_argparse_block, argparse_depth = self._process_argparse_for_line(
            stripped_line=stripped_line,
            line=line,
            in_argparse_block=in_argparse_block,
            argparse_depth=argparse_depth,
        )

        early_result = self._maybe_skip_after_state_updates(
            line=line,
            line_num=line_num,
            stripped_line=stripped_line,
            gen_range=gen_range,
            is_compat_file=is_compat_file,
            in_argparse_block=in_argparse_block,
            argparse_depth=argparse_depth,
            in_const_block=in_const_block,
            paren_depth=paren_depth,
        )
        if early_result is not None:
            return early_result

        return self._finalize_single_line_violation(
            file_path=file_path,
            line=line,
            stripped_line=stripped_line,
            line_num=line_num,
            exempt_strings=exempt_strings,
            in_argparse_block=in_argparse_block,
            argparse_depth=argparse_depth,
            in_const_block=in_const_block,
            paren_depth=paren_depth,
        )

    def _maybe_skip_after_state_updates(  # noqa: PLR0913
        self,
        *,
        line: str,
        line_num: int,
        stripped_line: str,
        gen_range: tuple[int, int] | None,
        is_compat_file: bool,
        in_argparse_block: bool,
        argparse_depth: int,
        in_const_block: bool,
        paren_depth: int,
    ) -> tuple[bool, int, bool, int, Violation | None] | None:
        """在完成 argparse/兼容性状态更新后，统一处理早退逻辑。"""

        if (
            in_argparse_block
            and argparse_depth > 0
            and not self._is_argparse_start(line)
        ):
            # 仍处于 argparse 多行块内部，且本行不是起始行 → 整体豁免
            return in_argparse_block, argparse_depth, in_const_block, paren_depth, None

        in_const_block, paren_depth = self._process_compat_block_for_line(
            stripped_line=stripped_line,
            line=line,
            line_num=line_num,
            gen_range=gen_range,
            is_compat_file=is_compat_file,
            in_const_block=in_const_block,
            paren_depth=paren_depth,
        )
        if in_const_block:
            # 仍在兼容性常量容器块内 → 整体豁免
            return in_argparse_block, argparse_depth, in_const_block, paren_depth, None

        return None

    def _process_argparse_for_line(
        self,
        *,
        stripped_line: str,
        line: str,
        in_argparse_block: bool,
        argparse_depth: int,
    ) -> tuple[bool, int]:
        """更新 argparse 多行块相关状态。"""

        skip, new_in_block, new_depth = self._handle_argparse_multiline(
            stripped_line=stripped_line,
            line=line,
            in_argparse_block=in_argparse_block,
            argparse_depth=argparse_depth,
        )
        if skip:
            return new_in_block, new_depth
        return in_argparse_block, argparse_depth

    def _process_compat_block_for_line(  # noqa: PLR0913
        self,
        *,
        stripped_line: str,
        line: str,
        line_num: int,
        gen_range: tuple[int, int] | None,
        is_compat_file: bool,
        in_const_block: bool,
        paren_depth: int,
    ) -> tuple[bool, int]:
        """更新兼容性常量容器块相关状态。"""

        skip, new_in_block, new_depth = self._handle_compat_const_block(
            stripped_line=stripped_line,
            line=line,
            line_num=line_num,
            gen_range=gen_range,
            is_compat_file=is_compat_file,
            in_const_block=in_const_block,
            paren_depth=paren_depth,
        )
        if skip:
            return new_in_block, new_depth
        return in_const_block, paren_depth

    def _finalize_single_line_violation(  # noqa: PLR0913
        self,
        *,
        file_path: Path,
        line: str,
        stripped_line: str,
        line_num: int,
        exempt_strings: list[str],
        in_argparse_block: bool,
        argparse_depth: int,
        in_const_block: bool,
        paren_depth: int,
    ) -> tuple[bool, int, bool, int, Violation | None]:
        """在完成状态更新后，根据简单规则与字符串内容构建违规记录。"""

        if self._should_skip_by_simple_line_rules(
            file_path=file_path,
            line=line,
            stripped_line=stripped_line,
            exempt_strings=exempt_strings,
        ):
            return in_argparse_block, argparse_depth, in_const_block, paren_depth, None

        violation = self._build_hardcoding_violation_if_any(
            file_path=file_path,
            line=line,
            stripped_line=stripped_line,
            line_num=line_num,
        )

        return in_argparse_block, argparse_depth, in_const_block, paren_depth, violation

    def _build_hardcoding_violation_if_any(
        self,
        *,
        file_path: Path,
        line: str,
        stripped_line: str,
        line_num: int,
    ) -> Violation | None:
        """若当前行构成 HC001 违规，则构建一条 Violation；否则返回 None。"""

        string_match = re.search(r'["\'][^"\']{5,}["\']', line)
        if not string_match:
            return None

        line_lower = line.lower()
        exclude_tokens = self._get_exclude_substrings()
        if ("=" not in line and ":" not in line) or any(
            ex in line_lower for ex in exclude_tokens
        ):
            return None

        string_literal = string_match.group(0).strip("\"'")
        if self._should_exempt_string(line, string_literal):
            return None

        return Violation(
            file_path=file_path,
            line=line_num,
            col=0,
            code=self.CODE_HC001,
            message=self._msg_hc001.format(snippet=stripped_line[:60]),
        )

    @staticmethod
    def _is_argparse_start(line: str) -> bool:
        """是否为 argparse 多行定义起始行。"""

        return (
            "parser.add_argument(" in line
            or ".add_subparsers(" in line
            or ".add_parser(" in line
        )

    @staticmethod
    def _in_docstring(line_no: int, docstring_ranges: list[tuple[int, int]]) -> bool:
        """判断当前行是否处于 docstring 覆盖范围内。"""

        return any(s <= line_no <= e for (s, e) in docstring_ranges)

    def _handle_argparse_multiline(
        self,
        *,
        stripped_line: str,
        line: str,
        in_argparse_block: bool,
        argparse_depth: int,
    ) -> tuple[bool, bool, int]:
        """处理 argparse 多行块的进入与退出逻辑。"""

        if in_argparse_block:
            argparse_depth += stripped_line.count("(") - stripped_line.count(")")
            if argparse_depth <= 0:
                in_argparse_block = False
            return True, in_argparse_block, argparse_depth

        if self._is_argparse_start(line):
            in_argparse_block = True
            argparse_depth = stripped_line.count("(") - stripped_line.count(")")
            return True, in_argparse_block, argparse_depth

        return False, in_argparse_block, argparse_depth

    def _is_const_container_start(self, line: str) -> bool:
        """判断是否为兼容性常量容器赋值块起始行（HC001 兼容文件专用）。"""

        return ("self.violation_types" in line and "PromptViolationType(" in line) or (
            "self.severity_levels" in line and "PromptSeverityLevel(" in line
        )

    def _handle_compat_const_block(  # noqa: PLR0913
        self,
        *,
        stripped_line: str,
        line: str,
        line_num: int,
        gen_range: tuple[int, int] | None,
        is_compat_file: bool,
        in_const_block: bool,
        paren_depth: int,
    ) -> tuple[bool, bool, int]:
        """处理兼容性常量容器赋值块与报表键名豁免逻辑。"""

        if not is_compat_file:
            return False, in_const_block, paren_depth

        if not in_const_block and self._is_const_container_start(stripped_line):
            in_const_block = True
            paren_depth = stripped_line.count("(") - stripped_line.count(")")
            return True, in_const_block, paren_depth

        if in_const_block:
            paren_depth += stripped_line.count("(") - stripped_line.count(")")
            if paren_depth <= 0:
                in_const_block = False
            return True, in_const_block, paren_depth

        if self._is_report_key_line(gen_range, line_num, line):
            return True, in_const_block, paren_depth

        return False, in_const_block, paren_depth

    def _should_skip_by_simple_line_rules(
        self,
        *,
        file_path: Path,
        line: str,
        stripped_line: str,
        exempt_strings: list[str],
    ) -> bool:
        """执行一组简单的逐行豁免规则。"""

        checks = (
            self._is_line_exempt_by_strings(line, exempt_strings),
            self._is_argparse_declaration(line, stripped_line),
            self._is_typealias_forward_ref(stripped_line, line),
            self._is_prompt_report_legal_line(file_path, line),
            self._is_final_literal_token(stripped_line),
            self._is_hasattr_exempt(line),
            self._is_typevar_name_exempt(line),
            self._is_all_export_list(stripped_line),
        )
        return any(checks)

    def _is_report_key_line(
        self, gen_range: tuple[int, int] | None, line_num: int, line: str
    ) -> bool:
        """是否为报表生成函数中的 schema key（HC001 豁免）。"""

        return bool(
            gen_range
            and gen_range[0] <= line_num <= gen_range[1]
            and re.search(r'^\s*["\']\w+["\']\s*:', line)
        )

    @staticmethod
    def _is_line_exempt_by_strings(line: str, exempt_strings: list[str]) -> bool:
        """是否命中 HC001.exemptions.strings 中的任意豁免片段。"""

        return any(exempt_str in line for exempt_str in exempt_strings)

    @staticmethod
    def _is_argparse_declaration(line: str, stripped_line: str) -> bool:
        """是否为 argparse 一行式参数/子命令定义（HC001 全局豁免）。"""

        del stripped_line
        return (
            "parser.add_argument(" in line
            or ".add_subparsers(" in line
            or ".add_parser(" in line
        )

    @staticmethod
    def _is_typealias_forward_ref(stripped_line: str, line: str) -> bool:
        """是否为类型别名中的前向引用字符串（TypeAlias / type X = list["Y"])。"""

        return (
            ("TypeAlias" in line or stripped_line.startswith("type "))
            and ("dict[" in line or "list[" in line)
            and ('"' in line or "'" in line)
        )

    def _is_prompt_report_legal_line(self, file_path: Path, line: str) -> bool:
        """check_prompt/报告生成相关的合法字符串使用。

        相关配置来自 strings.report_generator_files：

        .. code-block:: yaml

           laws:
             hc001:
               payload:
                 strings:
                   report_generator_files: ["path/pattern/**", ...]
        """

        patterns = self._str_cfg.report_generator_files
        if not patterns:
            return False

        prompt_files = normalize_patterns(patterns)
        fp_str = str(file_path)
        if not any(
            fnmatch.fnmatch(fp_str, p) or fp_str.endswith(p) for p in prompt_files
        ):
            return False

        checks = (
            "violation_type=" in line,
            "legal_clause=" in line,
            "severity=" in line,
            "v.severity" in line and "==" in line,
            'rglob("*.json")' in line,
            " in line" in line,
            " in str(file_path)" in line,
            "file_path=" in line,
            "coverage_config[" in line,
            "scoring_rules[" in line,
        )
        return any(checks)

    @staticmethod
    def _is_final_literal_token(stripped_line: str) -> bool:
        """严格类型的协议令牌常量（Final[Literal[...]]）豁免。"""

        return bool(
            re.search(
                r"^\s*\w+\s*:\s*Final\s*\[\s*Literal\[[^\]]+\]\s*\]\s*=",
                stripped_line,
            )
        )

    @staticmethod
    def _is_hasattr_exempt(line: str) -> bool:
        """hasattr(obj, "attr") 的第二个参数豁免。"""

        return bool(
            "hasattr(" in line
            and re.search(r"hasattr\([^,]+,\s*['\"][^'\"]+['\"]\)", line)
        )

    @staticmethod
    def _is_typevar_name_exempt(line: str) -> bool:
        """TypeVar("Name") 的名称字符串豁免。"""

        return bool(
            "TypeVar(" in line and re.search(r"TypeVar\(\s*['\"][^'\"]+['\"]", line)
        )

    @staticmethod
    def _is_all_export_list(stripped_line: str) -> bool:
        """__all__ 导出列表/元组中的字符串整体豁免。"""

        return bool(
            re.match(
                r"^\s*__all__\s*=\s*(\[[^\]]*\]|\([^\)]*\))\s*$",
                stripped_line,
            )
        )

    # ---- 字符串级豁免（与旧版 _should_exempt_string 等价）----

    def _should_exempt_string(self, line: str, string_literal: str) -> bool:
        """判断字符串是否应该豁免硬编码检查。

        减少误报，只标记真正的配置值硬编码，而不是合理的字符串使用。
        """

        checks = (
            self._is_attr_method_access(line),
            self._is_logger_message(line),
            self._is_exception_message(line),
            self._is_short_or_empty_literal(string_literal),
            self._is_triple_quoted(line),
            self._is_literal_annotation(line),
            self._is_fstring(line),
            self._is_decorator_param(line),
            self._is_dict_key_access(line),
            self._is_class_attr_constant(line),
        )
        return any(checks)

    @staticmethod
    def _is_attr_method_access(line: str) -> bool:
        """方法名/属性名访问（getattr, hasattr, setattr, delattr）。"""

        return bool(
            re.search(r"(getattr|hasattr|setattr|delattr)\s*\([^,]+,\s*['\"]", line)
        )

    @staticmethod
    def _is_logger_message(line: str) -> bool:
        """日志消息（logger.info / logger.debug / logging.*）。"""

        return bool(re.search(r"(logger\.|log\.|logging\.)", line))

    @staticmethod
    def _is_exception_message(line: str) -> bool:
        """异常消息（raise SomeError("msg")）。"""

        return bool(re.search(r"raise\s+\w+\(", line))

    @staticmethod
    def _is_short_or_empty_literal(string_literal: str) -> bool:
        """单字符或空字符串（通常是分隔符等）。"""

        return len(string_literal) <= 1

    @staticmethod
    def _is_triple_quoted(line: str) -> bool:
        """文档字符串标记（三引号）。"""

        return '"""' in line or "'''" in line

    @staticmethod
    def _is_literal_annotation(line: str) -> bool:
        """类型注解中的 Literal 字符串。"""

        return "Literal[" in line

    @staticmethod
    def _is_fstring(line: str) -> bool:
        """f-string 格式化（通常是日志或消息）。"""

        stripped = line.strip()
        return stripped.startswith('f"') or stripped.startswith("f'")

    @staticmethod
    def _is_decorator_param(line: str) -> bool:
        """装饰器参数（@decorator(param="value")）。"""

        stripped = line.strip()
        return stripped.startswith("@") and "=" in line

    @staticmethod
    def _is_dict_key_access(line: str) -> bool:
        """字典键访问（obj["key"]）。"""

        return bool(re.search(r"\w+\[['\"]", line))

    @staticmethod
    def _is_class_attr_constant(line: str) -> bool:
        """类属性定义（CLASS_ATTR: type = "value"）- 协议常量。"""

        return bool(re.match(r"^\s+[A-Z][A-Z0-9_]*\s*:\s*\w+\s*=", line))
