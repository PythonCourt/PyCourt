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
from pycourt.judge import ChiefJustice
from pycourt.utils import LOGGER_NAME, Violation

logger = logging.getLogger(LOGGER_NAME)


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
    if verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)


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
    """占位实现：从 pycourt.yaml 读取项目审计路径列表。

    当前实现简单返回 ["timeos" ] 作为默认路径，后续可扩展为：
    - 读取 ``pycourt.yaml`` 中 ``pycourt.paths`` 列表；
    - 或支持从 ``[tool.pycourt]`` 读取。
    """

    del config_path  # TODO: 真正实现基于 pycourt.yaml 的路径解析
    return ["timeos"]


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
    else:  # pragma: no cover - 防御分支
        parser.print_help()
        code = 1

    raise SystemExit(code)


if __name__ == "__main__":
    main()
