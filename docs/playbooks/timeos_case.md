# TimeOS / TimeBank 实战案例：PyCourt 的首位用户

> 目标：给第一次接触 PyCourt 的团队一个“真实仓库模板”，
> 展示如何在一个大型生产系统中分阶段接入 PyCourt，并用三把武器脚本组织审计与测试。

本案例基于 TimeOS / TimeBank 仓库，是 PyCourt 的首个真实使用者。
你可以把它当成一套 **可参考但不必照抄** 的工程战术：

- 如何在 `pyproject.toml` 里声明文明领土；
- 如何用 `pycourt.yaml` 做项目级豁免与 Law 家族配置；
- 如何用三把武器脚本（`qaf.sh` / `qas.sh` / `qa.sh`）把 PyCourt 接入日常开发与 CI。

---

## 1. [tool.pycourt]：从一小块“文明领土”开始

TimeOS 在 `pyproject.toml` 里通过 `[tool.pycourt]` 声明 PyCourt 的视角：

```toml
[tool.pycourt]
# 所有已“净化”的文明领土路径将收录于此。
# 这里的路径相对于仓库根目录，可以是包名、目录名或更细的子路径。
civilized_paths = [
  # "timeos/core",
  # "tools",
  "timeos/infra",
  # "timeos/engines",
  # "timeos/api",
  # "timeos/app",
]

# 覆盖率门槛唯一真理源（迁移自 [tool.coverage.report].fail_under）。
# TimeOS 在早期阶段将其设为 0，先把 PyCourt 接入完整流程，再逐步提高门槛。
coverage = 0
```

几个关键点：

1. **从最核心、最稳定的一块开始**：
   - TimeOS 只把 `timeos/infra` 纳入文明领土，其它路径暂时注释掉；
   - 这样可以在不“拖整个世界下水”的前提下，先把一块重点区域锁得很紧。
2. **覆盖率门槛先设低**：
   - `coverage = 0` 并不是“不要覆盖率”，而是“让 PyCourt 的管线先跑顺”；
   - 一旦工程和团队节奏稳定，再慢慢把门槛从 0 → 60 → 80 逐步提升。
3. **所有 CI/脚本统一从这里读配置**：
   - `python -m pycourt.config.read_toml --for-ci` 会解析出：
     - `fail_under`: 覆盖率门槛；
     - `civilized_paths`: 全部审计路径；
     - `coverage_paths`: 用于覆盖率统计的路径（自动排除 `tests/**`）。

---

## 2. pycourt.yaml：按法条组织豁免与家族配置

TimeOS 在仓库根维护一份较长的 `pycourt.yaml`，承载两类信息：

1. `laws` 段：针对特定 Law 家族的项目级配置；
2. `exemptions` 段：按法条编号分组的治外法权清单，附带详细原因。

### 2.1 Law 家族级配置：匹配仓库拓扑

示例（节选）：

```yaml
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
```

这里体现了一个重要思路：

- **让 Law 适应项目拓扑，而不是反过来**。
  - TimeOS 用 `bc001` / `uw001` / `vt001` / `pc001` / `di001` 的配置字段，
    显式描述“路由在哪、仓储在哪、向量 provider 在哪、核心常量在哪”；
  - Law 实现只关心这些子路径和模块后缀，不需要硬编码具体仓库结构。

当你在自己的项目中使用 PyCourt 时，可以仿照 TimeOS：

- 按你的实际目录结构调整这些子路径；
- 尽量保持字段语义通用，避免把极端局部规则写进 PyCourt 本身。

### 2.2 按法条的豁免与理由注释

TimeOS 为每条法条维护了细粒度的 `files` 列表，并配有 `reasons` 注释，例如：

```yaml
exemptions:
  BC001:
    files:
      - "tools/**/*.py"
      - "tests/**"
      - "timeos/api/*.py"
      - "timeos/app/main.py"
      - "timeos/app/worker.py"
      - "timeos/app/dependencies.py"
    reasons:
      "tools/**/*.py": "工具与脚手架脚本不直接暴露对外 API 或领域边界，允许使用基础类型与过程式参数，不强制 BC001 的 DTO 边界约束。"
      "tests/**": "测试代码用于验证行为而非定义正式边界契约，允许直接使用基础类型和临时结构，避免 BC001 干扰测试可读性。"
      "timeos/app/main.py": "HTTP 总指挥部只负责组装 FastAPI 应用与生命周期钩子，本身不承载领域输入/输出契约，放宽 BC001 以简化组合根实现。"
      # 其余条目略
```

再比如对 UoW 法条：

```yaml
  UW001:
    files:
      - "tests/**"
      - "tools/**"
      - "timeos/app/di/**"
      - "timeos/infra/services/issue.py"
      - "timeos/infra/graph/providers.py"
      - "timeos/infra/vector/providers.py"
    reasons:
      "tests/**": "测试代码可能直接调用 commit/rollback 或仓储工厂以模拟事务场景，UW 系列在此只会制造噪音，因此整体豁免。"
      "timeos/app/di/**": "DI 组合根需要显式 new 出 RepositoryFactory/UoW 实现并做 wiring，属于架构装配层，豁免 UW001 以避免对容器本身执法。"
      # 其余条目略
```

这种写法的经验：

1. **按法条而不是按目录思考豁免**：
   - 先问“这条法在这个区域有没有价值”，而不是“这个目录要不要豁免所有东西”。
2. **每条豁免都写清业务理由**：
   - TimeOS 几乎为每个 pattern 写了完整句子的注释；
   - 这让后来的人敢删、敢收紧，而不是面对一堆神秘的通配符。
3. **把元规则文件列到对应法条的豁免里**：
   - 例如 `tc001.py` 自己就豁免 TC001，`hc001.py` 在 HC/LL/TC 中都有自我豁免；
   - 这避免“法官审判自己”的循环尴尬。

---

## 3. 三把武器脚本：把 Law 变成可执行战术

TimeOS 沿用了 PyCourt 的三把官方武器概念，但实现完全在自己仓库里，并直接调用 PyCourt CLI：

- `qaf.sh`：帝国特战匕首 —— **单文件深度审计**；
- `qas.sh`：帝国军刀 —— **目录/子树审计 + 可选测试演习**；
- `qa.sh`：皇帝节仗 —— **全仓库统一审计 + 覆盖率裁决**。

### 3.1 qaf.sh：单文件深度审计（特战匕首）

核心职责：

1. 只接受一个文件路径作为审判目标；
2. 先用 PyCourt Law 从“架构生死线”一路审到“日常懒政”：
   - TC001 / RE00x / DI001；
   - UW00x / BC001 / VT001；
   - AC/OU/DT/SK/DS/LL/HC/PC 等；
3. 再串联类型、安全、风格链路：
   - `pyright` → `mypy` → `bandit` → `ruff check --fix` → `ruff format`。

在实现上，它通过一个统一的 `run_judges` 包装：

```bash
run_judges() {
  # 对单个文件执行指定法条组合
  local codes="$1"
  poetry run pycourt scope "$AUDIT_TARGET" --select "$codes"
}
```

然后按“先架构 → 再事务 → 再类型/领域 → 再风格”的顺序逐章执行。

> 适用场景：
> - review / 重构一个关键文件前后，用 qaf.sh 看“一个文件是否达到理想状态”；
> - 对新写的 Law 实现做自测；
> - 带新人理解一套完整的审计漏斗。

### 3.2 qas.sh：目录级军刀（战区静态总审查 + 可选国防演习）

`qas.sh` 面向的是 **目录或模块子树**：

1. 接受 `-s <directory>` 指定审计对象；
2. 通过 `run_static_audit_on_target <target>` 复用与 `qaf.sh` 类似的 Law/工具序列；
3. 支持 `-n` 非阻断模式（只打印警告，不退出非零码）；
4. 支持 `ENABLE_TEST_PHASE=1` 时追加“国防演习”：
   - 找到与审计目录镜像的 `tests/...` 目录；
   - 对该测试目录再跑一轮静态审计；
   - 对相关测试以 `-m unit` 形式运行 pytest + 覆盖率（但门槛只设在 0）。

示例片段（静态审计一整块战区）：

```bash
run_judges "${audit_target}" "TC001"
run_judges "${audit_target}" "RE001,RE002,RE003"
run_judges "${audit_target}" "DI001"
# ...
run_judges "${audit_target}" "DS001,DS002,LL001,LL002,HC001,HC002,HC003,HC004,HC005,PC001,PC002"
```

> 适用场景：
> - 对 `timeos/infra/enhance` 这样的大块子系统做阶段性审计；
> - 在开发迭代中只盯一个战区（目录），而不是一次性扫全仓；
> - 给 QA/架构师一把“侦察模式”（`-n`）来看当前健康度。

### 3.3 qa.sh：皇帝节仗（统一战略规划 + 全境审计 + 覆盖率）

`qa.sh` 是 TimeOS 的“一键总检”脚本，用于本地临时审计和 CI 前的全面裁决：

1. **第一章：战略规划署** —— 通过 PyCourt 读取统一配置。

   ```bash
   CONFIG_JSON=$(poetry run python -m pycourt.config.read_toml --for-ci)
   FAIL_UNDER=$(echo "$CONFIG_JSON" | jq -r '.fail_under')
   CIVILIZED_PATHS=($(echo "$CONFIG_JSON" | jq -r '.civilized_paths[]'))
   COVERAGE_PATHS=($(echo "$CONFIG_JSON" | jq -r '.coverage_paths[]'))
   ```

   - 这一步把配置解析完全交给 PyCourt，“节仗”只是做 orchestrator；
   - 后续所有覆盖率与审计范围都只信这个 JSON 输出。

2. **第二章：全境静态大巡查** —— 逐个文明领土调用 `qas.sh`：

   ```bash
   for SCOPE in "${CIVILIZED_PATHS[@]}"; do
     ./qas.sh -s "${SCOPE}" || exit 1
   done
   ```

3. **第三/四章：测试军规 + 三军联合作战**（可通过 `ENABLE_TEST_PHASE=1` 打开）：
   - 使用内部的 `tools/court/judge.py` 扫描测试纯净度（TP 系列）；
   - 按 `-m "unit or integration"` 一次性跑测试和覆盖率裁决；
   - 可选 `--with-e2e` 再追加一轮端到端验收。

> 适用场景：
> - 开发者本地在重要改动后跑一遍 `./qa.sh`；
> - CI 中作为“准强制”或“强制”质量门槛；
> - 观察覆盖率与架构健康的长期趋势。

---

## 4. 你可以如何借用 TimeOS 的战术？

如果你准备在自己的项目中使用 PyCourt，可以参考 TimeOS 的落地顺序：

1. **在 `pyproject.toml` 里添加 `[tool.pycourt]`**：
   - 先只纳入 1–2 个最重要的路径（例如 `src` / `service` / `infra`）；
   - 覆盖率门槛先设为 0 或较低数字，只做“有/无”报告。
2. **在仓库根创建 `pycourt.yaml`**：
   - 先只为测试目录和迁移脚本开豁免；
   - 按法条而不是按目录思考豁免，并写清每条豁免的业务理由。
3. **复制/改写三把脚本**：
   - 从 TimeOS 的 `qaf.sh` / `qas.sh` / `qa.sh` 中复制骨架；
   - 把其中的路径前缀（如 `timeos/...`）改成你自己的；
   - 保留“先架构 → 再事务 → 再类型 → 再安全/风格”的整体顺序。
4. **循序渐进地收紧规则**：
   - 先用 `qas.sh -n` 在非阻断模式下观察仓库当前“违宪”程度；
   - 再选几条你最在意的法条放进 CI（例如 DI001 / DT001 / HC001）；
   - 最后再考虑把全部 Law 套在关键模块上做强制执行。

TimeOS 的经验是：

- **不要一开始就当“极权法院”**，否则大家会只想关闭这个工具；
- 从一小块核心领土开始，把流程与脚本打磨顺手，再慢慢扩大版图；
- 所有“豁免”和“特权窗口”都要写在 `pycourt.yaml` 里，用自然语言解释清楚。

当你这么做时，PyCourt 就不再只是一个“linter”，而是你团队自己的“小宪法法院”。
