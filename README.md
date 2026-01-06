# PythonCourt
A Python code audit engine powered by AST analysis and rule systems,ensuring AI-generated code meets production-grade quality standards.

> [简体中文](docs/zh/README.md)

PythonCourt is a **“code court”** for Python projects.

It audits Python code — especially AI‑generated code — against a growing set of architecture and style laws, and reports violations in human‑readable language (English / Simplified Chinese).

The goal is to keep humans and AI coding under the same set of rules:

- constrain dependencies between API / domain / infrastructure layers;
- define which paths are “civilized territory” and which are out of jurisdiction;
- make it clear what AI is allowed to change and what must remain under stricter control.

PythonCourt is distributed as a **CLI tool** that you can plug into local workflows, CI/CD pipelines, or AI toolchains.

---

## Features

- 🧩 **Law‑driven structural audits**
  - A curated set of laws around architecture boundaries, dependency directions, constant management, type discipline, time usage, and more.
  - Designed to work with your existing project layout; you don’t have to reorganise folders just to use it.

- 🧭 **Civilized territories & exemptions**
  - Use `pycourt.yaml` and `[tool.pycourt]` to declare:
    - which paths are “civilized territory” that must pass audits;
    - which files/paths are out of scope for the current round of trials.

- ⚙️ **Friendly CLI & shell workflows**
  - Subcommands for `file`, `scope`, `project`, `init`.
  - Optional “weapons” (`Dagger` / `Saber` / `Scepter`) that orchestrate PyCourt with Pyright, Mypy, Bandit and Ruff, so you can drop them into your own repos.

- 🤝 **Designed for human–AI collaboration**
  - Human‑readable output with bilingual templates (EN / zh‑CN).
  - Suitable as an “architecture and quality judge” for AI agents and tools.

---

## When to use PythonCourt

PythonCourt is especially useful for:

- medium to large Python projects developed together with AI assistants;
- long‑lived backends/services where you worry about slow architectural decay;
- teams that want a clear line between “code that can be changed freely” and “code that must obey stricter rules”.

---

## Installation & quick start

PythonCourt is published as a standalone Python package and is tested on Python **3.11–3.14** (developed primarily on 3.14).

Recommended installation:

```bash
# For multiple projects (recommended)
pipx install pycourt

# Or inside a single project’s virtualenv
pip install pycourt

# Or as a development dependency via poetry
poetry add -D pycourt
```

### Minimal usage in any repo

```bash
cd /path/to/your-project

# 1. Initialise project configuration (generates a pycourt.yaml template)
pycourt init

# 2. Run a static audit on the current directory
pycourt scope . --format human --non-blocking
```

### CLI overview

```bash
pycourt file <path>      # audit a single Python file
pycourt scope <target>   # audit a directory or single file
pycourt project          # project‑level audit driven by config
pycourt init             # generate a starter pycourt.yaml in your repo
```

For CI integration you can use `--format json` and parse the result.

---

## Weapons: Dagger / Saber / Scepter

In addition to the core CLI, this repo ships three optional shell scripts (“weapons”) that show how to orchestrate PyCourt with other tools in real projects:

- **Dagger · file (`qaf.sh`)** — fast trials for a single file
  - Runs PyCourt + Pyright + Mypy + Bandit + Ruff on one file.
  - Prints narrative output with clear explanations and suggested fixes.

- **Saber · scope (`qas.sh`)** — focused trials for a directory or module tree
  - Runs static audits over a “battlefield” scope:
    - PyCourt laws (architecture, types, hard‑coding, etc.),
    - type checkers (Pyright, Mypy),
    - security checks (Bandit),
    - style & formatting (Ruff),
    - optional TEST‑series checks for test purity and optional pytest runs.

- **Scepter · project (`qa.sh`)** — project‑wide “emperor’s review”
  - Reads civilized paths and coverage threshold from `[tool.pycourt]` in `pyproject.toml`.
  - Dispatches Saber over each territory.
  - Can drive unit and integration tests with coverage as part of the same flow.

These scripts are **reference workflows**. You can:

- copy them into your own project and tweak which laws/tools to run;
- use them as templates to design completely new weapons.

For more details, see:

- [Dagger](docs/script/official/qaf.md)
- [Saber](docs/script/official/qas.md)
- [Scepter](docs/script/official/qa.md)

---

## Configuration

PythonCourt reads configuration from:

- `pycourt.yaml` — project lawbook (laws in force, exemptions, etc.).
- `[tool.pycourt]` in `pyproject.toml` — CI/CD‑oriented settings such as civilized paths and coverage thresholds.

Example snippets are available in the docs and on the homepage.

---

## Documentation

- English landing page & guide: see the GitHub Pages / site generated from `docs/`.
- Simplified Chinese landing page (recommended for Chinese readers):
  - `/zh/` on the deployed site, or
  - `docs/zh/index.html` in this repository.

---

## Contributing

Contributions are very welcome — this project is meant to evolve together with real teams using AI to write Python.

- Report bugs or request features via GitHub Issues.
- Send code or documentation improvements via Pull Requests.
- Design your own laws or weapons and share them as examples.

Please see the contributing guide under `docs/guide/community/contribute.md` for more details.

---

## License

This project is open‑sourced under the [MIT License](LICENSE.md).

> 为 Python 项目提供「代码法庭」级别的结构审计，让你和 AI 都在同一套游戏规则下写代码。

PyCourt 是一个面向 **Python 架构与协作场景** 的静态审计工具。  
它不像传统 Linter 只关注「代码风格」，而是通过一套 **法典（Laws）**，帮助你：

- 约束 API / 领域 / 基础设施等层次之间的依赖关系；
- 定义「文明领土」与「治外法权」边界，防止架构慢慢腐化；
- 在与 AI 协作时，用统一的规则约束「它能改什么、不能改什么」。

PyCourt 目前以 **命令行工具** 的方式提供，可直接接入你的本地开发流程与 CI/CD 流水线，也可以作为 AI 工具链中的一环。

---

## 核心特性

- 🧩 **法典驱动的结构审计**
  - 内置多条针对架构边界、依赖方向、常量管理等场景的「法典」；
  - 支持按项目风格重写审计拓扑，不强行要求你改变目录结构。

- 🧭 **文明领土与豁免机制**
  - 通过 `pycourt.yaml` 与 `[tool.pycourt]`，精确声明：
    - 哪些路径是需要严苛审计的「文明领土」；
    - 哪些文件/路径享有「治外法权」，不参与本轮审计。

- ⚙️ **友好的 CLI 与脚本集成**
  - 提供 `file` / `scope` / `project` / `init` 等子命令；
  - 内置「匕首 / 军刀 / 节仗」等脚本范式，方便你复制到自己的项目中。

- 🤝 **为人与 AI 的协作设计**
  - 人类可读 + 机器可读的双语输出；
  - 适合接入各种 AI Agent / ChatGPT 插件，作为「架构与质量裁判」。


## 适用场景

PyCourt 尤其适合这些场景：

- 需要与 AI 协作开发的中大型 Python 项目；
- 需要长期维护、担心架构「慢性腐败」的后端 / 服务端项目；
- 多团队协作，希望统一「哪些代码可以随便写，哪些必须按规矩来」的组织。
---

## 安装与快速上手

PyCourt 已发布为独立的 Python 包，目前在 Python **3.11–3.14** 上测试通过（开发主力环境为 3.14）。

推荐安装方式：

```bash
# 多项目开发（推荐）
pipx install pycourt

# 或在单个项目虚拟环境中
pip install pycourt

# 或作为 poetry 开发依赖
poetry add -D pycourt
```

---

## 在任意项目仓库中，最小上手流程：

```bash
cd /path/to/your-project

# 1. 初始化项目级配置（生成 pycourt.yaml 模板）
pycourt init

# 2. 对当前目录下的代码执行静态审计
pycourt scope .
```

## 更多子命令：
```bash
pycourt file <path>   # 审计单个 Python 文件；
pycourt scope <target> # 审计目录或单个文件；
pycourt project       # 基于配置的项目级审计（会在后续版本逐步丰富）。
```

---

## 文档与指南

如果你准备认真把 PyCourt 用在实际项目中，建议直接阅读完整文档：

- 文档站（推荐）：  
  - https://pythoncourt.com

- 仓库内主要文档入口：
  - [安装与启动：从零开始使用 PyCourt](docs/guide/started/index.md)
  - [配置指南：成为 AI 指挥官](docs/guide/started/config.md)
  - [法典清单与设计说明](docs/laws/index.md)
  - [官方脚本与开发流程（匕首 / 军刀 / 节仗）](docs/script/official/index.md)
  - [社区贡献与参与方式](docs/guide/community/contribute.md)




## 参与贡献

欢迎你一起塑造 PyCourt 的法庭规则与武器库：

•  报告 Bug 或提出需求：请使用 GitHub Issues；
•  提交代码 / 文档改进：请先阅读 [CONTRIBUTING.md](docs/guide/community/contribute.md)；
•  想设计自己的法典或脚本：可以从  
  贡献指南（社区） 开始。



协议

本项目基于 [MIT License](LICENSE.md) 开源。