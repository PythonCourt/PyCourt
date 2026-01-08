# 配置指南：让 PyCourt 为你服务

> 目标：掌控你的 PyCourt ，和你的项目无缝集成。

## 概述
1. 初始化生成 `pycourt.yaml` 文件，获得文件级豁免配置能力
2. 在`pyproject.toml` 添加 `[tool.pycourt]` 配置管辖范围
3. 利用脚本编排审计内容和流程

---

## 基础：文件豁免配置

### 1. 初始化配置文件

在项目根执行：
```bash
pycourt init
```
或者：
```bash
poetry run pycourt init
```
这会在当前工程根目录生成一个 pycourt.yaml 模板，里面有最基本的示例配置，你可以按需调整。
你可以在这里管理某些法律的启发拓扑路径，告诉法官们应该在哪里开展工作，
以及不适用某些法典的文件豁免，让他们免受 PyCourt 的审判。

### 2. 常用配置说明
阅读[法典清单](../../laws/index.md)，并将里你项目里免于审计的文件路径添加到 pycourt.yaml 里。
简单示例：

```yaml
# 若不配置 laws 段，将使用 PyCourt 内置的默认结构拓扑（见 config.yaml），
# 大多数中小项目可以先完全忽略本段，只关注下面的 exemptions。

# =================
# Law 家族启发拓扑配置
# =================
# 不同团队的目录习惯不同：路由、适配器、仓储、常量、向量 provider… 不一定都在默认的位置；
# laws.bc001/uw001/vt001/pc001/di001 这些配置，就是在告诉各个法官：
# “什么目录算路由层？”
# “仓储根在哪？”
# “常量仓在哪？”
# “向量 provider 在哪？”
# 它定义的是“应当重点关注的结构区域”，是审计的“地图”和“边界线”。
# 这样相应法官才知道自己的工作范围在哪里。
laws:
  bc001:
    router_dir_patterns:
      - "api/routes/"
    adapter_dir_patterns:
      - "infra/adapters/**"
    core_contract_module_suffixes:
      - "core.base.types"
      - "core.dto"
    api_contract_module_suffixes:
      - "api.http"

  uw001:
    infra_repo_subpath: "infra/database/repository"
    infra_system_repo_subpath: "infra/database/repository/system"

  vt001:
    provider_search_pattern: "infra/vector/providers.py"

  pc001:
    core_constants_subpath: "core/constants/"

  di001:
    # 注意：此处的前缀/精确模块名应包含根包前缀（例如 "timeos.api."）。
    # 若留空，则 DI001 将使用内置默认前缀：<root>.api.* 与 <root>.core.*。
    api_allowed_prefixes: []
    api_allowed_exact: []


# ===================
# Law 家族文件级豁免配置
# ===================
# exemptions.<CODE>.files 声明的是：即便按法条来看可能有风险，这些具体文件/路径这一次不要审；
# 常见场景：迁移脚本、运维脚本、测试、特殊入口文件、技术债暂时难以清理的模块；
# 当你重构、移动这些文件时，应该同步更新这里，保证豁免是“小而精确的白名单”，而不是一大片“永远不审的黑洞”。
# 这一部分是你日常维护最多的区域：为具体文件/路径发放治外法权。

exemptions:
  AC001:
    files: []

  BC001:
    files:
      - "pycourt/**/*.py"
      - "tests/**"

    reasons:
      "pycourt/**/*.py": "工具与脚手架脚本不直接暴露对外 API 或领域边界，允许使用基础类型与过程式参数，不强制 BC001 的 DTO 边界约束。"
      "tests/**": "测试代码用于验证行为而非定义正式边界契约，允许直接使用基础类型和临时结构，避免 BC001 干扰测试可读性。"
  DI001:
    files:
      - "pycourt/**"
      - "tests/**"
    reasons:
      "tests/**": "测试代码用于验证行为而非定义正式边界契约，允许直接使用基础类型和临时结构，避免 DI001 干扰测试可读性。"
      "pycourt/**": "PyCourt 本身作为法官工具集，其内部模块间依赖属于工具实现范畴，不适用 DI001 的约束。"

```

总结：

- laws 字段是告诉 pycourt 你的审计工作在哪里进行；
- exemptions字段是告诉 pycourt 对他们网开一面不要审计；
- 刚开始建议采用默认配置，等项目跑起来后，再逐步添加，避免让不该豁免的文件逃过审判。


**特别提醒** 
- 只有你才拥有对此文件的修改权限，我们甚至建议你亲自将豁免文件填入对应法典，并注明豁免理由。
- 除非你明确授权才允许 AI 操作，否则你应该命令禁止 AI 对该文件的执行权限。
- AI 在执行任务过程中，你需要特别注意此文件的变更情况，一旦发现 AI 自主添加豁免，你需要立即询问缘由并与它展开讨论后做出是否豁免的决策。

---

## 进阶：项目管理配置

在 `pyproject.toml` 里添加 `[tool.pycourt]`

示例：

```toml
[tool.pycourt]
civilized_paths = [
    "src/api",      # civilized
    "src/business", # civilized
    "src/services", # civilized
    "src/infra",    # civilized
    "src/core",     # civilized
    # "tools",      # excluded from this CI run
]
```

建议将它放到`pyproject.toml`文末，因为你会经常来这里调整配置。

不建议把 tests 目录放到里面，下一节介绍。

说明：

- 声明 **哪些路径是“文明领土”**（需要被 PyCourt 严格审计）。
- 提供一个 **统一的覆盖率门槛** 给 CI 使用。
- 你可以通过**注释掉一行**的方式来适配你的开发节奏；
- 你可以在这里很方便的**配置跨域组件和模块**的集成审计；
- 你还可以把这个配置**纳入 CI/CD 管道**，自定义 PR 范围的审计；
- 你需要用一个特别的脚本来消费这个配置，详见下一节。

---

## 高阶：开发流程配置
用 PyCourt Engine 驱动 shell 脚本，有效提升审计效率和自由度：

### 1. 文件级审计配置
你可以从丰富的 [审计法典](../../laws/index.md)挑选你认为对代码质量和安全有帮助的法条，将他们进行编排后，对单个创建和修改过的文件进行审计，PyCourt 会将发现的违法行为和整改与修复建议，分别用人类和机器阅读的语言输出。方便你和 AI 合作时解决问题。

你可以参考我为自己项目设计的**[匕首](../../script/official/qaf.sh)**脚本。

我集成了Mypy、Pyright、Bandit、Ruff，以便能通过一个命令，完成所有的审计项目，让文件彻底纯净。
你可以根据自己的实际需求对它重新设计和编排，以符合你的开发习惯。

### 2. 目录级审计配置
你还可以设计并配置目录级别的审计，它能将 **匕首** 的能力同时应用在一个文件夹里的所有文件身上。

你可以参考我为自己项目设计的 [军刀](../../script/official/qas.sh) 脚本。

我增加了自动探测审计目标 tests 文件的能力，对其执行静态审计后运行单元测试，因此不建议把 tests 目录添加到 [tool.pycourt]，否则会报错。
军刀的设计有助于你批量审计一个目录并自动执行测试，有效提升开发效率。

### 3. 模块级审计配置
为跨域审计而特别设计，弥补匕首和军刀在审计范围方面的不足。
它读取 `pyproject.toml` 里的 `[tool.pycourt]`信息，并调用军刀执行除测试以外的所有任务，然后自己跑单元和集成以及 E2E 测试，并对覆盖率是否达标进行审判。

你可以参考我为自己项目设计的 [节仗](../../script/official/qa.sh) 脚本。

你可以通过节仗脚本自定义审计多个审计目标，这方便你对跨域组件和模块进行进行系统性审计和验收，它甚至可以代替远程 CI/CD ，跑完后，你可以放心的直接 PR 。

---

## 下一步
当你完成这些配置后，你就已经掌控了你的代码质量和风格，接下来，你需要设计你与 AI 合作的方式与 [开发流程](runtime.md) 。


