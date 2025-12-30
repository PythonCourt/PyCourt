"""🏛️ SK001 技能使用审查官 (Skills Usage Inquisitor)

职责：
1. SK001: 检测在业务代码中直接硬编码 Skill ID 字符串（如 "session.guidance"、"memory.ingest" 等），
   要求通过集中 `SkillId` 常量或统一配置管理，而不是在各处散落裸字符串；

设计原则：
- 只关注 **纯 Skill ID 字符串字面量**，避免误伤普通文本；
- 豁免：
  - tools/ 与 tests/ 下的代码（兵工厂与测试战区）；
  - 模块 / 类 / 函数的文档字符串中的示例。

与现有法官的关系：
- HC001 负责通用硬编码字符串；
- PC002 负责绕过 RuleProvider 直接访问 assets/ 目录；
- SK001 专注于 Skill ID 这一类“能力标识符”的使用规范。
"""

from __future__ import annotations

import ast
import fnmatch
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Final, TypedDict

import yaml

from pycourt.config.config import CourtConfig
from pycourt.utils import Violation, normalize_patterns

# ---------------------------------------------------------------------------
# 内部常量命名空间
# ---------------------------------------------------------------------------


class AssetsBasePath:
    """assets 资源路径约定（与项目根目录的相对位置）。

    在 PyCourt 中仅定义与技能审计相关的部分，避免直接依赖上游系统常量。
    """

    # 相对于项目根目录的 Skill 资源根路径，例如 "assets/skills"
    SKILLS_RELATIVE: Final[str] = "assets/skills"


class SkillsPath:
    """Skill 资产物理根路径命名空间。

    基于相对路径约定（例如 `assets/skills`）推导技能索引所在目录，
    供技能法官在扫描本地文件系统时复用，避免在各处重复拼接路径。
    """

    # 默认假设项目根目录下存在 assets/skills 目录
    ROOT: Final[Path] = Path(AssetsBasePath.SKILLS_RELATIVE)


class SkillIndexPath:
    """SkillIndex 文件系统路径约定常量。"""

    # index.yaml 文件名称（位于各个技能目录下）
    MAX_LINES = 0
    INDEX_FILE: Final[str] = "index.yaml"


class SkillIndexField:
    """SkillIndex YAML 中的字段名称。"""

    ID: Final[str] = "id"


class SessionSkillId:
    """Session 引擎下的 Skill ID 常量。

    这些值应与 `skills/engines/session/*/index.yaml` 中的 id 字段保持一致。
    """

    ICEBREAKER: Final[str] = "session.icebreaker"
    GUIDANCE: Final[str] = "session.guidance"
    RECALL: Final[str] = "session.recall"
    CLOSING: Final[str] = "session.closing"


class MemorySkillId:
    """Memory 引擎下的 Skill ID 常量。"""

    INGEST: Final[str] = "memory.ingest"
    SLICE: Final[str] = "memory.slice"
    COMMIT: Final[str] = "memory.commit"
    GOLD: Final[str] = "memory.gold"
    INGEST_RAW: Final[str] = "memory.ingest_raw"
    BUILD_GOLD_MEMORIES: Final[str] = "memory.build_gold_memories"
    UPDATE_VECTOR_STORE: Final[str] = "memory.update_vector_store"


class InsightSkillId:
    """Insight 引擎下的 Skill ID 常量。"""

    HIGHLIGHT: Final[str] = "insight.highlight"
    FOCUS: Final[str] = "insight.focus"
    EXEC: Final[str] = "insight.exec"
    LEAD: Final[str] = "insight.lead"


class ExpertSkillId:
    """Expert 引擎下的 Skill ID 常量。"""

    PSYCH: Final[str] = "expert.psych"
    MGMT: Final[str] = "expert.mgmt"
    STORY: Final[str] = "expert.story"


class SystemSkillId:
    """System 级别 Skill ID 常量（非语境相关）。"""

    LLM_DEFAULTS: Final[str] = "system.llm_defaults"


class _SkillIndexData(TypedDict, total=False):
    """技能索引文件的最小结构描述。

    仅建模 index.yaml 中的 id 字段，用于为类型检查器提供精确结构信息。
    """

    id: str


class SkillsLawConstants:
    """命名空间常量：SK001/SK002 技能使用法条内部使用。

    - 集中管理法条编号与消息模板；
    - 避免在模块顶层散落裸常量定义，符合 HC 系列规范；
    - 提供路径拆分等技术参数的统一入口。
    """

    CODE_SK001: Final[str] = "SK001"
    CODE_SK002: Final[str] = "SK002"

    # Skill path must have at least <engine>/<skill>
    MIN_SKILL_PATH_PARTS: Final[int] = 2


# Skill ID 约定：<engine>.<skill_name>
# 目前 engine 前缀包括：session / memory / insight / expert / system
_SKILL_ID_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^(session|memory|insight|expert|system)\.[a-zA-Z0-9_]+$"
)

# 直接访问 assets/skills 的文件操作关键词（用于 SK002）
_SKILLS_FILE_OP_KEYWORDS: Final[tuple[str, ...]] = (
    "open(",
    "Path(",
    "rglob(",
    "glob(",
    ".read",
    ".load",
)

# 识别技能资产目录的标记（用于 SK002）
_SKILLS_DIR_MARKERS: Final[tuple[str, ...]] = (
    AssetsBasePath.SKILLS_RELATIVE,  # "assets/skills"
    "assets/skills",
    "SkillsPath.ROOT",
)


@lru_cache(maxsize=1)
def _load_known_skill_ids() -> set[str]:
    """从系统常量与 assets/skills/index.yaml 收集已知 Skill ID 集合。
    - 常量来源：SessionSkillId / MemorySkillId / InsightSkillId / ExpertSkillId /
      SystemSkillId 中声明的所有 str 值；
    - 资产来源：assets/skills/**/index.yaml 中的 id 字段，若缺失则根据
      <engine>/<skill>/index.yaml 推导为 ``f"{engine}.{skill}"``。
    """

    ids: set[str] = set()
    ids.update(_collect_skill_ids_from_constants())
    ids.update(_collect_skill_ids_from_assets())
    return ids


def _collect_skill_ids_from_constants() -> set[str]:
    """从 Session/Memory/Insight/Expert/System 常量类中收集 Skill ID。"""

    ids: set[str] = set()

    def _collect_from_class(cls: type[object]) -> None:
        for attr in dir(cls):
            if attr.isupper():
                value = getattr(cls, attr, None)
                if isinstance(value, str):
                    ids.add(value)

    for klass in (
        SessionSkillId,
        MemorySkillId,
        InsightSkillId,
        ExpertSkillId,
        SystemSkillId,
    ):
        _collect_from_class(klass)

    return ids


def _collect_skill_ids_from_assets() -> set[str]:
    """从 assets/skills/**/index.yaml 中收集 Skill ID。

    高阶流程拆分为若干小步骤以降低圈复杂度：
    - _path_exists_safely: 保护性检查目录是否存在；
    - _iter_skill_index_paths: 枚举所有 index.yaml；
    - _load_skill_index_data: 读取并解析 YAML；
    - _derive_skill_id_from_data: 从数据或路径中推导出 Skill ID。
    """

    ids: set[str] = set()

    base_dir = SkillsPath.ROOT
    if not _path_exists_safely(base_dir):
        return ids

    for index_path in _iter_skill_index_paths(base_dir):
        data = _load_skill_index_data(index_path)
        if data is None:
            continue
        skill_id = _derive_skill_id_from_data(
            index_path=index_path, base_dir=base_dir, data=data
        )
        if skill_id:
            ids.add(skill_id)

    return ids


def _path_exists_safely(path: Path) -> bool:
    """安全检测路径是否存在，兼容 OSError 等异常场景。"""

    try:
        return path.exists()
    except OSError:  # pragma: no cover - 容错读取
        return False


def _iter_skill_index_paths(base_dir: Path) -> list[Path]:
    """列举 assets/skills 下所有技能 index 文件路径。"""

    return list(base_dir.rglob(SkillIndexPath.INDEX_FILE))


def _load_skill_index_data(index_path: Path) -> _SkillIndexData | None:
    """从 index.yaml 中读取技能元数据，失败则返回 None。"""

    try:
        text = index_path.read_text(encoding="utf-8")
        raw = yaml.safe_load(text)
    except Exception:  # pragma: no cover - 容错读取
        logging.exception("Failed to load skill index from %s", index_path)
        return None

    if not isinstance(raw, dict):
        return None

    data: _SkillIndexData = {}
    for key, value in raw.items():  # pyright: ignore[reportUnknownVariableType]
        if key == SkillIndexField.ID and isinstance(value, str):
            data["id"] = value

    return data


def _derive_skill_id_from_data(
    *, index_path: Path, base_dir: Path, data: _SkillIndexData
) -> str | None:
    """根据 YAML 数据或路径信息推导 Skill ID。"""

    raw_id = data.get(SkillIndexField.ID)
    if isinstance(raw_id, str):
        return raw_id

    try:
        rel = index_path.relative_to(base_dir)
    except ValueError:
        return None

    parts = rel.parts
    if len(parts) < SkillsLawConstants.MIN_SKILL_PATH_PARTS:
        return None

    engine_name, skill_name = parts[0], parts[1]
    return f"{engine_name}.{skill_name}"


class TheSkillsUsageLaw:
    """🏛️ 技能使用审查官 (SK001/SK002)

    专注于 Skill 资产的使用规范：
    - SK001: 在业务代码中禁止直接硬编码 Skill ID 字符串；
    - SK002: 禁止直接通过文件 I/O 访问 assets/skills 下的技能资产，强制走
      SkillProviderPort + SkillId。
    """

    def __init__(self, config: CourtConfig) -> None:
        """SK001 使用 YAML 驱动的路径级豁免（sk001 法条）。"""
        self.config = config
        self.laws = config.laws
        self._msg_sk001: str = self.config.get_judge_template(
            SkillsLawConstants.CODE_SK001
        )
        self._msg_sk002: str = self.config.get_judge_template(
            SkillsLawConstants.CODE_SK002
        )

    def _collect_docstring_ranges(self, tree: ast.AST | None) -> list[tuple[int, int]]:
        """收集模块 / 类 / 函数级 docstring 所在的行号区间，用于豁免。"""

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

    @staticmethod
    def _in_ranges(line_no: int, ranges: list[tuple[int, int]]) -> bool:
        return any(start <= line_no <= end for (start, end) in ranges)

    def _check_skills_fs_access(
        self, file_path: Path, lines: list[str]
    ) -> list[Violation]:
        """检查直接文件访问技能资产的行为 (SK002)。"""

        violations: list[Violation] = []
        fp_str = file_path.as_posix()

        # 与 SK001 共用同一组路径级豁免（SK001 -> files）
        patterns = normalize_patterns(
            self.config.get_exempt_files(SkillsLawConstants.CODE_SK001)
        )
        if any(fnmatch.fnmatch(fp_str, p) or fp_str.endswith(p) for p in patterns):
            return violations

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "import" in line:
                continue

            # 识别技能资产目录引用
            has_skills_dir = any(marker in line for marker in _SKILLS_DIR_MARKERS)
            if not has_skills_dir:
                continue

            # 必须伴随文件操作行为
            has_file_op = any(kw in line for kw in _SKILLS_FILE_OP_KEYWORDS)
            if not has_file_op:
                continue

            violations.append(
                Violation(
                    file_path=file_path,
                    line=line_num,
                    col=0,
                    code=SkillsLawConstants.CODE_SK002,
                    message=self._msg_sk002.format(snippet=stripped[:60]),
                )
            )

        return violations

    def investigate(
        self,
        file_path: Path,
        content: str,
        lines: list[str],
        tree: ast.AST | None,
    ) -> list[Violation]:
        """审查代码中的 Skill 资产使用情况 (SK001/SK002)。"""

        del content

        violations: list[Violation] = []

        config = self.laws.sk001
        if not config.enabled:
            return violations

        fp_str = file_path.as_posix()
        patterns = normalize_patterns(
            self.config.get_exempt_files(SkillsLawConstants.CODE_SK001)
        )
        if any(fnmatch.fnmatch(fp_str, p) or fp_str.endswith(p) for p in patterns):
            return violations

        violations.extend(self._check_skills_fs_access(file_path, lines))

        if tree is None:
            return violations

        known_skill_ids = _load_known_skill_ids()
        docstring_ranges = self._collect_docstring_ranges(tree)

        violations.extend(
            self._collect_skill_constant_violations(
                file_path=file_path,
                tree=tree,
                known_skill_ids=known_skill_ids,
                docstring_ranges=docstring_ranges,
            )
        )

        return violations

    def _collect_skill_constant_violations(
        self,
        *,
        file_path: Path,
        tree: ast.AST,
        known_skill_ids: set[str],
        docstring_ranges: list[tuple[int, int]],
    ) -> list[Violation]:
        """在 AST 中查找所有 Skill ID 字符串并生成违规记录。"""

        violations: list[Violation] = []

        for node in ast.walk(tree):
            if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                continue

            value: str = node.value
            lineno = getattr(node, "lineno", None)
            col = getattr(node, "col_offset", 0)

            if not isinstance(lineno, int):
                continue

            if self._in_ranges(lineno, docstring_ranges):
                continue

            stripped = value.strip()
            if not _SKILL_ID_PATTERN.match(stripped):
                continue

            message = self._msg_sk001.format(skill_id=stripped)
            if stripped not in known_skill_ids:
                message += (
                    "\n📋 注意: 该 Skill ID 未在 assets/skills 索引或 SkillId 常量中注册，"
                    "请确认资产与常量是否已同步"
                )

            violations.append(
                Violation(
                    file_path=file_path,
                    line=lineno,
                    col=col,
                    code=SkillsLawConstants.CODE_SK001,
                    message=message,
                )
            )

        return violations
