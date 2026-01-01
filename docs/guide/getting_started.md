# 安装与快速上手：3 步跑起来 PyCourt

> 目标：让第一次接触 PyCourt 的用户，在几分钟内完成：安装 → 初始化配置 → 跑一遍审计报告。

---

## 1. 安装 PyCourt CLI

推荐使用全局隔离的安装方式：

```bash
pipx install pycourt
```

如果你已经在使用某个项目级虚拟环境（如 `poetry` / `venv`），也可以直接：

```bash
pip install pycourt
```

安装完成后，可以先确认一下版本与帮助信息：

```bash
pycourt --help
```

你应该能看到包括 `file` / `scope` / `project` / `init` 在内的子命令列表。

---

## 2. 初始化 `pycourt.yaml`（项目级豁免配置）

在你希望审计的项目根目录下执行：

```bash
cd /path/to/your/project
pycourt init
```

PyCourt 会自动：

1. 通过项目中的 `pyproject.toml` / Git 根等信息，推断当前“项目根”；
2. 在项目根生成一个默认的 `pycourt.yaml`（如果已存在则**不会覆盖**，除非你显式传入 `--force`）。

如果你已经有了自己的配置文件，可以使用：

```bash
pycourt init --force
```

来用 PyCourt 的模板覆盖现有文件（请先自行备份或放入版本控制）。

生成的 `pycourt.yaml` 主要包含一个 `exemptions` 段落，你可以在其中按法条代码（如 `HC001`、`LL001`、`DI001`）配置需要“文件级治外法权”的路径模式，例如：

```yaml
exemptions:
  HC001:
    files:
      - "tests/**"        # 测试目录通常允许更多硬编码
      - "migrations/**"   # 数据库迁移脚本往往不需要太严
  LL001:
    files:
      - "**/tests/**"     # 某些长函数只在测试中存在
```

路径匹配遵循 `fnmatch` 风格通配：

- `foo/bar.py`：匹配单个文件；
- `foo/**`：匹配整个目录及其子项；
- `**/tests/**`：匹配任意层级下名为 `tests` 的目录。

---

## 3. 跑一遍审计（最小闭环）

配置文件就绪后，可以先在项目根做一次“整体预览”：

```bash
pycourt scope .
```

这会：

- 以当前目录为根，递归扫描 `.py` 文件；
- 应用 `pycourt.yaml` 中的 `exemptions` 规则；
- 按法条输出发现的“违宪行为”。

如果你更倾向于一次只看一个文件，可以使用：

```bash
pycourt file path/to/foo.py
```

当你对输出比较满意后，可以考虑把 PyCourt 接入 CI，例如：

```bash
pycourt scope . --select HC001,HC003,LL001
```

只跑几条你最关心的法条，作为质量红线。

---

## 4. 下一步：深入配置与风格指南

- 想了解如何组织项目内的常量、避免被 HC 系列误伤，可以参考：
  - `docs/guide/constants_style.md`
- 想定制更复杂的豁免规则、或根据团队习惯调整法条选择，可以直接阅读并修改：
  - `pycourt/yaml/config.yaml`
  - `pycourt/pycourt.yaml`（PyCourt 自身的自审配置，作为参考示例）

欢迎把 PyCourt 当作你项目里的“小宪法法院”，从最小闭环开始，逐步把你真正关心的工程习惯固化下来。