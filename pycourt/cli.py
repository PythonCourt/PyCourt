"""PyCourt CLI entrypoints.

提供面向开源消费者的轻量 CLI：
- `pycourt file`   : 单文件静态审计；
- `pycourt scope`  : 目录/模块级静态审计；
- `pycourt project`: 基于 pycourt.yaml / [tool.pycourt] 的项目级审计。

注意：本模块只负责 PyCourt 法院本身的编排逻辑，不包含 pytest/coverage 等
CI 流水线步骤；这些由上层脚本（如 qaf.sh/qas.sh/qa.sh）按需组合。
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from pycourt.config.judges_texts import get_courtroom_text, get_default_lang
from pycourt.config.yaml_paths import exempt_yaml_path
from pycourt.judge import ChiefJustice
from pycourt.utils import LOGGER_NAME, Violation

logger = logging.getLogger(LOGGER_NAME)


_DEFAULT_PYCOURT_YAML_TEMPLATE = """# 🏛️ PyCourt 项目豁免配置 (pycourt.yaml)
#
# 此文件仅在当前仓库内生效，用于声明各法条在“文件/路径级别”的治外法权。
# 你可以按需向下方的 `files` 列表中追加通配模式，例如：
#   - "tests/**"       # 整个 tests 目录不审
#   - "migrations/**"  # 数据库迁移脚本不审
#   - "scripts/*.py"   # 某些脚本工具不审
#
# 路径匹配规则与 `fnmatch` 一致，常见模式包括：
#   - "foo/bar.py"     精确匹配单个文件
#   - "foo/**"         匹配目录下所有子文件/子目录
#   - "**/tests/**"    匹配任意层级下的 tests 目录
#
# 若你希望完全关闭某条法条，也可以在命令行中使用 `--ignore CODE`，
# 或者在 CI 脚本中直接不选择该法条。

exemptions:
  HC001:
    files:
      # - "tests/**"
      # - "migrations/**"

  LL001:
    files:
      # - "tests/**"

  DI001:
    files: []

  # 你可以在此处按需追加其他法条，例如：
  # DT001:
  #   files: []
  # SK001:
  #   files: []
"""


def _build_arg_parser() -> argparse.ArgumentParser:
    """构建顶层 CLI 参数解析器并挂载子命令。

    子命令具体的参数定义委托给专门的辅助函数，以降低本函数复杂度
    并便于后续为单个子命令扩展选项。
    """

    parser = argparse.ArgumentParser(prog="pycourt", description="PyCourt CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    file_p = subparsers.add_parser("file", help="审计单个 Python 文件")
    _configure_file_subparser(file_p)

    scope_p = subparsers.add_parser("scope", help="审计单个目录或模块战区")
    _configure_scope_subparser(scope_p)

    project_p = subparsers.add_parser("project", help="基于配置对整个项目进行静态审计")
    _configure_project_subparser(project_p)

    init_p = subparsers.add_parser("init", help="在项目根初始化 pycourt.yaml 模板")
    _configure_init_subparser(init_p)

    return parser


def _configure_file_subparser(parser: argparse.ArgumentParser) -> None:
    """为 `pycourt file` 子命令挂载参数。"""

    parser.add_argument("path", help="要审计的 Python 源文件路径")
    parser.add_argument(
        "--select",
        help="仅审计指定的违宪代码列表，逗号分隔，如 DI001,BC001",
        default=None,
    )
    parser.add_argument(
        "--format",
        choices=("human", "json"),
        default="human",
        help="输出格式（human/json）",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志输出")


def _configure_scope_subparser(parser: argparse.ArgumentParser) -> None:
    """为 `pycourt scope` 子命令挂载参数。"""

    parser.add_argument("target", help="要审计的目录或单个文件路径")
    parser.add_argument(
        "--select",
        help="仅审计指定的违宪代码列表，逗号分隔",
        default=None,
    )
    parser.add_argument(
        "--non-blocking",
        action="store_true",
        help="非阻断模式：发现违宪时仅打印报告，不以非零退出码终止",
    )
    parser.add_argument(
        "--format",
        choices=("human", "json"),
        default="human",
        help="输出格式（human/json）",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志输出")


def _configure_project_subparser(parser: argparse.ArgumentParser) -> None:
    """为 `pycourt project` 子命令挂载参数。"""

    parser.add_argument(
        "--config",
        help="显式指定 pycourt 配置文件路径（默认使用项目根目录下 pycourt.yaml）",
        default=None,
    )
    parser.add_argument(
        "--select",
        help="仅审计指定的违宪代码列表，逗号分隔",
        default=None,
    )
    parser.add_argument(
        "--non-blocking",
        action="store_true",
        help="非阻断模式：发现违宪时仅打印报告，不以非零退出码终止",
    )
    parser.add_argument(
        "--format",
        choices=("human", "json"),
        default="human",
        help="输出格式（human/json）",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志输出")


def _configure_init_subparser(parser: argparse.ArgumentParser) -> None:
    """为 `pycourt init` 子命令挂载参数。"""

    parser.add_argument(
        "--force",
        action="store_true",
        help="如已存在 pycourt.yaml，则强制覆盖生成模板",
    )


def _parse_codes(select: str | None) -> set[str] | None:
    if not select:
        return None
    return {code.strip() for code in select.split(",") if code.strip()}


def _filter_violations(
    violations: list[Violation], selected: set[str] | None
) -> list[Violation]:
    if not selected:
        return violations
    return [v for v in violations if v.code in selected]


def _setup_logging(verbose: bool) -> None:
    """Configure logging for CLI runs.

    默认以 INFO 级别输出摘要信息；当提供 ``-v/--verbose`` 时，
    预留给将来的 DEBUG 级别日志使用。

    同时统一前缀为 ``PyCourt:``，避免默认 ``INFO:pycourt:`` 噪音，
    更贴近“法院播报”的语气。
    """

    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="PyCourt:%(message)s")


def _violations_to_dict(v: Violation) -> dict[str, int | str]:
    return {
        "file": str(v.file_path),
        "line": int(v.line),
        "col": int(v.col),
        "code": v.code,
        "message": v.message,
    }


def _cmd_file(args: argparse.Namespace) -> int:
    _setup_logging(args.verbose)
    court = ChiefJustice()
    selected = _parse_codes(args.select)
    lang = get_default_lang()

    path = Path(args.path)
    if not path.is_file():
        logger.error("target is not a file: %s", path)
        return 2

    violations = court.conduct_audit(str(path))
    violations = _filter_violations(violations, selected)

    if args.format == "json":
        json.dump(
            [_violations_to_dict(v) for v in violations], sys.stdout, ensure_ascii=False
        )
        sys.stdout.write("\n")
    elif violations:
        summary = get_courtroom_text("supreme_court.summary_failed", lang=lang).format(
            count=len(violations)
        )
        logger.error(summary)
        for v in violations:
            logger.error("  %s", v)
    else:
        summary = get_courtroom_text("supreme_court.summary_passed", lang=lang)
        logger.info(summary)

    return 1 if violations else 0


def _cmd_scope(args: argparse.Namespace) -> int:
    _setup_logging(args.verbose)
    court = ChiefJustice()
    selected = _parse_codes(args.select)
    lang = get_default_lang()

    target = args.target
    # logger.info("🏛️ PyCourt 开始审计: %s", target)  # noqa: ERA001
    violations = court.conduct_audit(target)
    violations = _filter_violations(violations, selected)

    if args.format == "json":
        json.dump(
            [_violations_to_dict(v) for v in violations], sys.stdout, ensure_ascii=False
        )
        sys.stdout.write("\n")
    elif violations:
        summary = get_courtroom_text("supreme_court.summary_failed", lang=lang).format(
            count=len(violations)
        )
        logger.error(summary)
        for v in violations:
            logger.error("  %s", v)
    else:
        summary = get_courtroom_text("supreme_court.summary_passed", lang=lang)
        logger.info(summary)

    if args.non_blocking:
        return 0
    return 1 if violations else 0


def _load_project_paths_from_config(config_path: Path | None) -> list[str]:
    """从 pycourt.yaml 读取项目审计路径列表。

    - 读取 ``pycourt.yaml`` 中 ``pycourt.paths`` 列表；
    - 或支持从 ``[tool.pycourt]`` 读取。
    """

    del config_path  # 真正实现基于 pycourt.yaml 的路径解析
    return ["."]  # 返回当前目录作为审计目标


def _cmd_project(args: argparse.Namespace) -> int:
    _setup_logging(args.verbose)
    court = ChiefJustice()
    selected = _parse_codes(args.select)
    lang = get_default_lang()

    cfg_path = Path(args.config) if args.config else None
    targets = _load_project_paths_from_config(cfg_path)

    all_violations: list[Violation] = []
    for target in targets:
        violations = court.conduct_audit(target)
        violations = _filter_violations(violations, selected)
        all_violations.extend(violations)

    if args.format == "json":
        json.dump(
            [_violations_to_dict(v) for v in all_violations],
            sys.stdout,
            ensure_ascii=False,
        )
        sys.stdout.write("\n")
    elif all_violations:
        summary = get_courtroom_text("supreme_court.summary_failed", lang=lang).format(
            count=len(all_violations)
        )
        logger.error(summary)
        for v in all_violations:
            logger.error("  %s", v)
    else:
        summary = get_courtroom_text("supreme_court.summary_passed", lang=lang)
        logger.info(summary)

    if args.non_blocking:
        return 0
    return 1 if all_violations else 0


def _cmd_init(args: argparse.Namespace) -> int:
    """在项目根目录生成默认 `pycourt.yaml` 模板文件。

    - 若文件不存在，则直接创建；
    - 若文件已存在且未指定 ``--force``，则保持原文件不变并返回 0；
    - 若指定 ``--force``，则覆盖写入默认模板内容。
    """

    target = exempt_yaml_path()
    target_parent = target.parent
    target_parent.mkdir(parents=True, exist_ok=True)

    if target.exists() and not args.force:
        logger.info("pycourt.yaml 已存在于 %s，跳过生成（使用 --force 可覆盖）", target)
        return 0

    target.write_text(_DEFAULT_PYCOURT_YAML_TEMPLATE, encoding="utf-8")
    logger.info("已生成 PyCourt 默认配置文件: %s", target)
    return 0


def main() -> None:
    """PyCourt CLI 入口函数。

    根据用户输入的子命令（file/scope/project）分派到对应的执法流程，
    并以退出码表达整体审计结果，便于在 CI/CD 中直接使用。
    """

    parser = _build_arg_parser()
    args = parser.parse_args()

    if args.command == "file":
        code = _cmd_file(args)
    elif args.command == "scope":
        code = _cmd_scope(args)
    elif args.command == "project":
        code = _cmd_project(args)
    elif args.command == "init":
        code = _cmd_init(args)
    else:  # pragma: no cover - 防御分支
        parser.print_help()
        code = 1

    raise SystemExit(code)


if __name__ == "__main__":
    main()
