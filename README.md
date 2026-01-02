## 安装与快速上手

PyCourt 已发布为独立的 Python 包，你可以通过 `pip` 或 `pipx` 安装。

当前版本在 Python **3.11–3.14** 上测试通过（开发主力环境为 3.14）。

你可以通过以下命令安装：

```bash
pip install pycourt
# 或者
pipx install pycourt
```

在任意项目仓库中，建议的最小上手流程：

```bash
cd /path/to/your-project

# 1. 初始化项目级配置（生成 pycourt.yaml 模板）
pycourt init

# 2. 对当前目录下的代码执行静态审计
pycourt scope .
```

`pycourt init` 会在项目根目录生成一个带有注释的 `pycourt.yaml`，
你可以在其中为各法条追加需要完全豁免的路径模式（例如 `tests/**`）。

其余子命令：

- `pycourt file <path>`   审计单个 Python 文件；
- `pycourt scope <target>` 审计目录或单个文件；
- `pycourt project`       预留用于基于配置的项目级审计（后续版本会逐步完善）

更详细的安装说明、`pycourt.yaml` 模板讲解与使用示例，见 `docs/guide/getting_started.md`。
