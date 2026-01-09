"""pycourt.utils - 最高法院法官共享的基础工具与类型

定位
====
- 为各个 Law 实现提供统一的工具函数和基础类型；
- 避免 law 模块直接依赖组合根 `pycourt.judge`，从而打破循环导入；
- 仅承载“法院内部通用基座”，不包含 ChiefJustice 或 CLI 入口逻辑。
"""

from __future__ import annotations

import ast
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Final

# =========================
# 公共常量（Law 实现可安全依赖）
# =========================

# 全局日志记录器名称，供 CLI / Judge / Laws 统一使用
LOGGER_NAME: Final[str] = "pycourt"


class ProjectFiles:
    """项目级文件/路径常量命名空间。

    当前仅承载工程根配置文件 `pyproject.toml` 等路径信息，避免在各处
    手写字符串拼接路径，便于后续集中演进和审计。
    """

    PYPROJECT_FILENAME: Final[str] = "pyproject.toml"


class DictContractTypes:
    """dict 契约检查相关基础类型命名空间。

    提供一组被视为“无契约”的基础 value 类型集合，供 AC/HC 系列法官在
    静态分析时快速识别 `dict[str, T]` 中的弱类型场景。
    """

    BASIC_VALUE_TYPES: Final[set[str]] = {
        "str",
        "int",
        "float",
        "bool",
        "bytes",
        "None",
        "Any",
        "object",
    }


# =========================
# 违规承载类型
# =========================


class Violation:
    """用于承载一次审计发现的完整违规详情，包含位置与裁决信息。"""

    def __init__(self, file_path: Path, line: int, col: int, code: str, message: str):
        self.file_path = file_path
        self.line = line
        self.col = col
        self.code = code
        self.message = message

    def __repr__(self) -> str:  # pragma: no cover - 调试友好
        return (
            f"Violation({self.file_path} L{self.line}:C{self.col} "
            f"[{self.code}] {self.message})"
        )


# =========================
# 工具函数（normalize / AST / IO）
# =========================


def find_project_root() -> Path:
    """定位并返回**调用方工程**的项目根目录。

    当前实现约定：

    - 从当前工作目录 (os.getcwd) 开始向上遍历父目录；
    - 返回第一个包含 ``pyproject.toml`` 的目录；
    - 若遍历至文件系统根仍未找到，则抛出 ``FileNotFoundError``。

    这意味着：当 PyCourt 作为依赖被引入其他工程时，``find_project_root``
    总是解析为**使用方工程**的根目录，而不是 PyCourt 包自身所在的仓库根。
    """

    current = Path(os.getcwd()).resolve()  # noqa: PTH109
    for parent in (current, *current.parents):
        if (parent / ProjectFiles.PYPROJECT_FILENAME).is_file():
            return parent

    msg = f"无法找到帝国根目录 ({ProjectFiles.PYPROJECT_FILENAME} not found)!"
    raise FileNotFoundError(msg)


def normalize_patterns(
    obj: list[str] | tuple[str, ...] | set[str] | None,
) -> list[str]:
    """轻量工具：将任意对象规范化为字符串模式列表，容错 Mock/错误类型。"""

    if isinstance(obj, list):
        return list(obj)
    if isinstance(obj, tuple):
        return list(obj)
    if isinstance(obj, set):
        return list(obj)
    return []


def normalize_str_list_map(
    val: Mapping[str, list[str] | tuple[str, ...] | set[str]] | None,
) -> dict[str, list[str]]:
    """规范化字典工具：无 cast，强类型过滤。"""

    if not isinstance(val, Mapping):
        return {}
    out: dict[str, list[str]] = {}
    for k, v in val.items():
        # 键为 str，值允许 list/tuple/set[str]，统一收敛为 list[str]
        if isinstance(v, list):
            out[k] = v
        else:
            # 覆盖 tuple/set 情形
            out[k] = list(v)
    return out


def normalize_int_map(val: Mapping[str, int] | None) -> Mapping[str, int]:
    """Normalize a mapping to ensure all values are integers.

    Returns an empty dict if input is None or not a Mapping.
    """

    if not isinstance(val, Mapping):
        return {}
    return {k: int(v) for k, v in val.items()}


def is_root_model_container(annotation_str: str) -> bool:
    """判断是否是 RootModel 受控容器模式。

    约定使用 ``RootModel[dict[str, T]]`` 作为受控容器，是一种合法的架构模式。
    """

    return annotation_str.startswith("RootModel[dict[")


def is_contracted_dict(annotation_str: str) -> bool:
    """判断 dict 是否有明确的类型契约。

    有契约的 dict 示例：
    - dict[str, LLMPort]
    - dict[str, SomeSchema]

    无契约的 dict 示例：
    - dict
    - dict[str, Any]
    - dict[str, str]
    - dict[str, object]
    """

    min_dict_parts = 2  # dict 需要至少 2 个泛型参数

    # 1. 检查是否是泛型 dict
    if not annotation_str.startswith("dict["):
        return False

    # 2. 提取泛型参数
    inner = annotation_str[5:-1]  # 去掉 "dict[" 和 "]"
    parts = [p.strip() for p in inner.split(",")]

    if len(parts) < min_dict_parts:
        return False

    # 3. 检查值类型是否是契约类型
    value_type = parts[1]

    # 排除基础类型和 Any/object
    if value_type in DictContractTypes.BASIC_VALUE_TYPES:
        return False

    # 如果值类型以大写字母开头，认为是契约类型
    return value_type[0].isupper() if value_type else False


def read_file_content(file_path: Path) -> tuple[str, list[str]]:
    """读取文件内容和行列表（供各法官使用的统一 IO 层）。"""

    try:
        with file_path.open(encoding="utf-8") as f:
            content = f.read()
            lines = content.splitlines()
            return content, lines
    except Exception:  # pragma: no cover - 审计工具的稳健性优先
        return "", []


def get_ast_tree(content: str, file_path: str) -> ast.AST | None:
    """安全地将源码解析为 AST 树（解析失败返回 None）。"""

    try:
        return ast.parse(content, filename=file_path)
    except SyntaxError:
        return None


__all__ = [
    "Violation",
    "find_project_root",
    "get_ast_tree",
    "is_contracted_dict",
    "is_root_model_container",
    "normalize_int_map",
    "normalize_patterns",
    "normalize_str_list_map",
    "read_file_content",
]
