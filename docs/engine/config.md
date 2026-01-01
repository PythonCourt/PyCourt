# 配置指南：官方推荐模板
PyCourt 的配置可以分成三层：项目自身的 `pyproject.toml`、项目根的 `pycourt.yaml`，以及 PyCourt 内部自带的法律配置 YAML。

本页给出一套可以直接 **复制粘贴** 的推荐模板，适合作为「第一次在真实项目里接入 PyCourt」的起点。

---

## 1. 配置全景：需要关心哪些文件？
在一个普通的应用/服务仓库中，通常只需要维护下面三类配置：

1. `pyproject.toml` 里的 `[tool.pycourt]`
   - 声明 **哪些路径是“文明领土”**（需要被 PyCourt 严格审计）。
   - 提供一个 **统一的覆盖率门槛** 给 CI 使用。
2. 仓库根目录的 `pycourt.yaml`
   - 记录「哪些文件/目录拥有治外法权」，即完全不受某些法条约束。
   - 对应 CLI 子命令（`pycourt file/scope/project`）以及 Law 执行时的豁免视图。
3. PyCourt 包内部的 YAML（一般不用改）
   - `pycourt/yaml/config.yaml`：法条与家族的全局配置。
   - `pycourt/yaml/judges_text.*.yaml`：中英文判决模板文案。
   - 正常使用 PyCourt 时 **不需要修改** 这些文件，把它们当成“宪法法典库”即可。

> 如果你只想快速上手 CLI，可以先看《安装与快速上手：3 步跑起来 PyCourt》，
> 本页更偏向「在团队项目中如何稳妥落地」的配置视角。

---

## 2. 推荐项目结构示例
下面是一个常见的项目根目录布局，你可以在此基础上自由调整：

```text
/your-project
  ├── pyproject.toml       # 包/依赖/测试/工具统一入口
  ├── pycourt.yaml         # 项目级治外法权与法条豁免配置
  ├── src/                 # 业务代码（示例路径，可换成 core/ app/ 等）
  ├── tests/               # 测试代码
  └── tools/               # 可选：本仓库自定义 QA 脚本
      ├── qa.sh            # 全仓库质量体检脚本（参考 PyCourt 官方 qa.sh）
      ├── qas.sh           # 子目录/模块级审计脚本
      └── qaf.sh           # 单文件深度审计脚本
```

如果你不打算维护本地脚本，也可以直接在 CI / 本地命令行中调用：

- `pycourt file path/to/foo.py`
- `pycourt scope .`

---

## 3. `pyproject.toml` 中的 `[tool.pycourt]` 推荐模板
在项目的 `pyproject.toml` 中，新增一段最小可用配置：

```toml
[tool.pycourt]
# 所有已“净化”的文明领土路径将收录于此 —— 即你期望长期保持高质量的代码区。
# 这里的路径相对于仓库根目录，可以是包名、目录名或更细的子路径。
civilized_paths = [
  "src",      # 主业务代码目录
  "app",      # 可选：应用层（如 FastAPI / Django 等）
]

# 覆盖率门槛唯一真理源：
# - 官方脚本会把它视为 CI 的 `fail_under`；
# - 若不想在早期就卡死，可以先设为 60–80，后续再慢慢提高。
coverage = 80
```

推荐做法：

- **先只纳入最核心的业务路径**（例如 `src` / `timeos` / `service`），
  等团队反馈稳定后，再逐步扩展到更多子模块；
- 将测试目录 `tests/` 排除在 `civilized_paths` 之外——
  官方 CI 读取逻辑会自动把 `tests/**` 排除在覆盖率统计路径之外。

官方工具 `pycourt.config.read_toml` 会在 CI/脚本中统一解析这些字段：

- 从调用方工程的 `pyproject.toml` 里读取 `[tool.pycourt]`；
- 计算出：
  - `fail_under`：覆盖率阈值；
  - `civilized_paths`：全部审计路径；
  - `coverage_paths`：用于覆盖率收集的路径（自动排除 `tests/**`）。

你可以在脚本中通过：

```bash
python -m pycourt.config.read_toml --for-ci
```

获取一份 JSON 结构的配置快照，然后交给 `pytest --cov` / `coverage` 等工具使用。

---

## 4. 项目根 `pycourt.yaml` 推荐模板
`pycourt.yaml` 主要承担两件事：

1. 按法条代码（如 `HC001`/`DT001`/`DI001`）声明哪些文件/目录完全豁免；
2. 为后续团队协作留下「为什么在这里开了一个洞」的文字注释。

一个最小但实用的模板示例：

```yaml
# pycourt.yaml — 项目级治外法权与豁免配置示例

exemptions:
  HC001:
    files:
      - "tests/**"        # 测试目录允许更多硬编码与魔法数字
      - "migrations/**"   # 数据库迁移脚本往往是一次性脚本

  DT001:
    files:
      - "tests/**"        # 测试中允许直接使用 datetime.now() 等

  DI001:
    files:
      - "**/tests/**"     # 测试代码中允许更随意的依赖导入
```

路径模式采用 `fnmatch` 风格通配：

- `foo/bar.py`：精确匹配单个文件；
- `foo/**`：匹配整个目录及其子目录；
- `**/tests/**`：匹配任意层级下名为 `tests` 的目录。

推荐实践：

- **从少量豁免开始**：优先只为测试目录和迁移脚本开豁免；
- 每次新增豁免时，务必在注释里写明「业务原因」，避免将来无人敢删；
- 若某个文件长期需要大量豁免，通常意味着可以抽象出一个更好的结构，
  可以在 review/重构时重点关注。

---

## 5. 可选：为团队准备一套 QA 脚本模板
如果你希望像 PyCourt 自己一样，通过脚本来组织审计与测试，可以参考下面的思路：

1. 使用 `pycourt config.read_toml` 统一读取 `[tool.pycourt]`：
   - 拿到 `coverage_paths`，交给 `pytest --cov` 或 `coverage run`；
   - 拿到 `civilized_paths`，作为 `pycourt scope` 的默认审计范围。
2. 根据用途拆分三个脚本：
   - `qaf.sh`：单文件深度审计（传入单个 Python 文件路径，调用 `pycourt file`）。
   - `qas.sh`：子树级审计（传入目录，调用 `pycourt scope <dir>`）。
   - `qa.sh`：全仓库体检（对所有文明路径循环调用 `pycourt scope`，并串联测试/覆盖率）。

一个极简的伪代码式示例（省略错误处理与平台兼容性）：

```bash
#!/usr/bin/env bash
set -euo pipefail

# 1. 从调用方 pyproject.toml 解析 CI 配置
cfg_json=$(python -m pycourt.config.read_toml --for-ci)
fail_under=$(printf '%s' "$cfg_json" | jq '.fail_under')
coverage_paths=$(printf '%s' "$cfg_json" | jq -r '.coverage_paths[]' | tr '\n' ' ')

# 2. 运行测试并收集覆盖率
pytest --cov ${coverage_paths} --cov-fail-under=${fail_under}

# 3. 对所有文明路径执行 PyCourt 审计
for path in $(printf '%s' "$cfg_json" | jq -r '.civilized_paths[]'); do
  pycourt scope "${path}"
done
```

> 上面只是一个「思想模板」，真正落地时可以参考 PyCourt 仓库里的
> `qa.sh` / `qas.sh` / `qaf.sh`，按你自己的工程节奏进行裁剪与扩展。

---

## 6. 如何在团队中逐步推广？
最后给出一条推荐路线，可以作为落地 PyCourt 的节奏参考：

1. 在 `pyproject.toml` 中添加 `[tool.pycourt]`，只纳入最核心的 1–2 个路径；
2. 在仓库根创建一份精简版 `pycourt.yaml`，只为测试与迁移脚本开豁免；
3. 在本地开发机上先通过 `pycourt scope .` 熟悉输出，再决定哪些法条需要进入 CI；
4. 为 CI 加上一条「非阻塞」的 PyCourt 审计（先不作为强制门槛，只输出报告）；
5. 等团队熟悉之后，再将部分法条/覆盖率阈值升级为「必须通过」的质量红线。

这样，你既可以享受 PyCourt 带来的架构反馈，又不会在早期就被自己的规则反噬。
