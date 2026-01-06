# PythonCourt 

由 ASTs 和 Rules 驱动的 Python 代码审计引擎。

## 常见 Python 代码质量隐患
### 第一章 架构生死线
1. 架构护城河
  - 循环依赖法庭：禁止使用TYPE_CHECKING等手段引入循环依赖
  - 门面纪律法庭：禁止在门面层使用领域逻辑并聚合导出
  - 依赖倒置法庭：禁止违反依赖倒置原则直接依赖具体实现

2. 事务与边界
- 2.1
- 2.2 
- 2.3

3. 类型安全
- 1.3.1
- 1.3.2
- 1.3.3
- 1.3.4

### 第四章 内政署（仪容仪表）

### 

## 安装与运行

PyCourt 已发布为独立的 Python 包，目前在 Python **3.11–3.14** 上测试通过（开发主力环境为 3.14）。

推荐安装方式：

```bash
# 多项目开发
pipx install pycourt

# 或在单个项目虚拟环境中（推荐）
pip install pycourt

# 或作为 poetry 开发依赖
poetry add -D pycourt
```
## 成为 AI 指挥官
在 AI 生成代码之后，运行 pycourt 审计并报告发现的任何非法行为，
并要求 AI 整改和修复，确保代码质量健壮和可长期维护，
构建 **生成 --> 审计 --> 修复** 工作流，真正享受 AI 编程的乐趣！

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