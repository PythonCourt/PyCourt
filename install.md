# 开始使用

## 一、首次使用 PyCourt：从 0 到能跑的流程

### 步骤 1：安装 PyCourt

两种典型方式：

-  用 pip（适合单项目虚拟环境）：
```bash
  pip install pycourt
```
-  用 Poetry（适合使用 Poetry 管理的项目）：
```bash
  poetry add pycourt
```
安装完成后，在你的项目根目录执行以验证安装：
```bash
pycourt --help
# 或者在 Poetry 环境：
poetry run pycourt --help
```
### 步骤 2：在项目根生成 pycourt.yaml

在项目根执行：
```bash
pycourt init
# 或：poetry run pycourt init
```
这会在当前工程根目录生成一个带注释的 pycourt.yaml 模板，里面只有最基本的示例豁免配置，你可以按需增删。

> 这一步是“让 PyCourt 知道你的项目有哪些文件是永远不审的”，比如 tests/**、migrations/** 等。

更详细的配置说明见 [配置指南](config.md)。

### 步骤 3：快速试用 CLI（不用任何自定义脚本）

不改任何脚本，直接用 CLI 体验三种入口：

-  单文件极致审计：
```bash
  pycourt file <path/to/your_file.py>
```
•  目录/模块战区审计：
```bash
  pycourt scope src/    # 或 src/infra/adapter 这种子树
```
-  基于配置的整仓项目审计（结合 [tool.pycourt] 和 pycourt.yaml，见下一节）：
```bash
  pycourt project
```
这一步的目的，是让你先熟悉“PyCourt 本身能做什么”，而不用立刻写 QA 脚本。

### 步骤 4：（推荐）在 pyproject.toml 里加 [tool.pycourt] 用于 CI

当你想把 PyCourt 真正接进 CI 或自己写的 qa.sh 时，建议在项目的 pyproject.toml 里加一段：
```toml
[tool.pycourt]
# 希望被纳入“文明审计”的代码路径（相对项目根）
# 通常不放 tests，官方示例脚本会自动匹配审计目标的 tests 并对其进行静态审计后运行单元测试
civilized_paths = [
  "src",            # 希望被审计的路径（也可以是子树路径）
  # "tools",        # 不希望被审计并排除在CI之外的目录
]

# 覆盖率门槛（给你的 QA 脚本 / CI 使用）
coverage = 80
```
说明：
-  `civilized_paths`：告诉脚本“哪些子树要被视作需要重点审计/度量覆盖率的文明区域”；
-  `coverage`：给 QA 脚本一个统一的覆盖率阈值作为审判依据，你可以根据实际需求来自定义它。

### 步骤 5：设计你自己的武器脚本（高级用户）

- 把 pycourt 当成 “核心审计引擎”；
- 自己用 shell 组合 PyCourt + pytest + coverage 流程，例如：
```bash
# 单文件匕首：qaf.sh（示意）
poetry run pycourt scope "$FILE" --select "DI001,BC001,DT001"
poetry run pyright "$FILE"
poetry run mypy "$FILE"
poetry run bandit -q "$FILE"
poetry run ruff check "$FILE" --fix
```
你也可以直接下载并查看作者为自己的项目设计的脚本：[特战匕首](../arsenal/qaf.sh) / [帝国军刀](../arsenal/qas.sh) / [皇帝节仗](../arsenal/qa.sh)
    
- 你可以根据自己的实际需求，从 pycourt 的法典中选择适合你的法典组合。
- 通常建议将安全、架构、依赖等放在流程的第一阶段，之后是 mypy 等类型检查，最后是风格与格式。
- 欢迎你参与讨论并分享你的设计。


二、需要理解的两块配置：pycourt.yaml 和 pyproject.toml的[tool.pycourt]

1. `pycourt.yaml`（文件级豁免配置 & 法条配置）

作用：告诉 PyCourt：哪些文件/路径符合治外法权应该豁免不审，某些 Law 的家族级参数该怎么调。

典型结构（简化示例）：
```yaml
# 项目级 PyCourt 配置 (pycourt.yaml)

# laws 段：为特定 Law 家族提供项目级结构信息（可选，高级）
laws:
  bc001:
    router_dir_patterns:
      - "api/routes/"  # 边境管理的重点关注对象
    adapter_dir_patterns: 
      - "infra/adapters/**" # 来自外部第三方技术的适配器也应该被关注

  vt001:
    provider_search_pattern: "infra/vector/providers.py" # 配置向量触发路由支持

  pc001:
    core_constants_subpath: "core/constants/" # 业务调参不得混入技术常量

  di001:
    api_allowed_prefixes: [] # 占位符，在实际开发中逐渐添加
    api_allowed_exact: []

# exemptions 段：按法条编号提供“文件/路径级豁免”
exemptions:
  DT001:
    files:
      - "tests/**"                     # 测试代码中允许 datetime.now()
      - "src/infra/services/clock.py"  # 唯一合法直接用 datetime.now() 的地方

  HC001:
    files:
      - "tests/**" # 测试代码允许硬编码
      - "scripts/**" 

  LL001:
    files:
      - "migrations/**" 

  # 你可以根据需要为不同 code（AC001/BC001/UW001/...）配置 files 列表
```

建议：

必须理解的：exemptions 段
- 一开始可以只加 1～2 条，例如让 tests/** 和 migrations/** 整体豁免 HC/LL；
- 随着项目长大，再逐步补充精细豁免（比如“某个 clock 实现允许用 datetime.now”）。

可以先忽略的：laws 段
- 高级用户用来细调某些 Law 的“项目拓扑感知”；
- 初次上手可以完全不写，让 PyCourt 用内置默认规则解读项目结构；
- 等你发现 BC/ UW/ VT/ PC/ DI 这几个家族需要更贴合你项目时，再回到这里精调。

2. `pyproject.toml` 全局文明地图 & 覆盖率门槛）

这一块主要服务于“CI / 高级 QA 脚本”，而不是 PyCourt CLI 本身。

对于一个普通新用户，一个比较合适的“最低门槛”配置可以是：
```toml
# pyproject.toml 
[tool.pycourt]
civilized_paths = [
  "src",          # 或你的主代码目录，比如 "app", "myproject"
]
coverage = 80     # 你期望的覆盖率阈值
```
然后你可以在自己的 qa.sh 里，用：
```bash
CONFIG_JSON=$(pycourt.config.read_toml --for-ci)
# 从 JSON 里取出 fail_under / civilized_paths / coverage_paths
# 再结合 pytest --cov 做你想要的组合
```


