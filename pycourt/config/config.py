"""tools.court.config - 法院运行期配置契约

身份
====
- 本模块是「法院配置法典」，负责将外部 YAML 事实（config.yaml / judges_text.yaml /
  exempt.yaml）收敛为强类型配置模型；
- 只描述「法院本身」需要的事实：法律结构 (CourtLaws)、文本法典 (CourtTexts)、
  治外法权视图 (CourtExemptions) 以及少量 Law 家族级配置 (如 HCConfig)。

用法
====
- 所有调用方一律通过 :func:`tools.court.loader.load_court_config` 获取
  :class:`CourtConfig` 实例，**禁止**直接读取 YAML 文件；
- Law 实现只依赖 `CourtConfig` 暴露的方法和字段：
  - ``laws``: 读取当前启用的法律条文与路径级豁免；
  - ``texts``: 获取判决模板文案；
  - ``exemptions``: 查询治外法权路径；
  - ``hc``: （可选）HC 家族的统一配置视图；
- 任何新的 Law 配置需求，必须先在此处建模，再由 loader 负责与 YAML 对接。

禁止行为
========
- 禁止在 Law 实现或其他模块中绕过 :class:`CourtConfig` 直接 parse YAML
  （例如直接使用 ``yaml.safe_load`` 或自行读取路径）；
- 禁止在本模块中引入业务实现或领域逻辑，仅允许声明 Pydantic 模型
  与与之匹配的 YAML 结构；
- 禁止将 "临时配置" 混入 CourtConfig：若与 Court 领域无关的工具配置，
  应放在各自子域（如 tools.cli/config 等）中维护。
"""

from __future__ import annotations

import os

from pydantic import Field, RootModel

from pycourt.models import PyCourtBase, PyCourtLaws

# ---------------------------------------------------------------------------
# 最高法院通用配置模型：为各 Law 执法通用文案提供强类型契约
# ---------------------------------------------------------------------------


class CourtroomTexts(RootModel[dict[str, dict[str, str]]]):
    """庭审流程文案映射：section -> key -> text。

    应用场景：
    - 仅用于承载 `judges_text.yaml` 中可选的 ``courtroom:`` 段落；
    - 该段落主要服务于 Court 内部的流程性提示（例如开庭/宣判文案），
      与 CLI/外部系统无关；
    - 当前阶段业务方主要依赖 ``JudgeTemplates`` 提供的判决模板，
      ``CourtroomTexts`` 作为向后兼容保留，随时可以按需精简。
    """


class JudgeTemplates(RootModel[dict[str, dict[str, str]]]):
    """大法官判决模板映射：code -> {template: str, ...}。

    应用场景：
    - 由 `judges_text.yaml` 中的 ``judges:`` 段提供数据；
    - 每条法律（例如 HC001/DT001/AC001）在此拥有自己的判决模板；
    - 运行期由 :meth:`CourtConfig.get_judge_template` 统一访问，
      各 Law 实现通过该方法获取人类可读的违宪说明文案。
    """


class CourtTexts(PyCourtBase):
    """最高法院使用的文案配置总表。

    应用场景：
    - 对应 `judges_text.yaml` 中的全部内容；
    - ``courtroom``: 可选的庭审流程文案（section -> key -> text），当前主要为向后兼容保留；
    - ``judges``:   各法条的判决模板文案（code -> {template: str, ...}），
      是 :meth:`CourtConfig.get_judge_template` 的数据来源，也是各 Law
      向开发者/用户输出违宪说明时的唯一入口。
    """

    courtroom: CourtroomTexts = Field(
        default_factory=CourtroomTexts,
        description="庭审流程文案（section -> key -> text）",
    )
    judges: JudgeTemplates = Field(
        default_factory=JudgeTemplates,
        description="各法条判决模板（code -> {template: str, ...}）",
    )


class CourtExemptions(PyCourtBase):
    """各法条的路径/文件级治外法权视图。

    应用场景：
    - 对应 `exempt.yaml` 中的 ``exemptions:`` 段；
    - 记录每条法律在路径/文件粒度上的治外法权（即“完全不审”的文件模式）；
    - 具体 YAML 结构由 :mod:`tools.court.loader` 负责解析，
      Law 实现通过 :meth:`CourtConfig.get_exempt_files` 取得给定 code 的模式列表。
    """

    files: dict[str, list[str]] = Field(
        default_factory=dict,
        description="按法条编号汇总的文件/路径豁免表 (code -> [pattern])",
    )


# ---------------------------------------------------------------------------
# Law配置模型：为各 Law 读取 YAML 配置提供强类型契约
# ---------------------------------------------------------------------------


class HCConfig(PyCourtBase):
    """HC 系列（硬编码相关）统一配置模型（大平面法典）。

    场景说明
    ========
    - 对应 `config.yaml` 中 ``laws.hc001.*`` 下除 ``enabled`` / ``exempt_files`` /
      ``description`` 之外的全部字段；
    - 由 HC 家族法官 :class:`TheHardcodingLaw` 及其下属细法（HC001–HC005）
      在运行期统一消费，用于识别硬编码常量、字符串以及数值魔法等风险；
    - 字段在技术上可分为三类关注点：constants / strings / numeric_params，
      但在模型层面统一收敛为一个平面，便于从 Court 视角一眼看清 HC 家族配置版图。

    配置边界
    ========
    - 仅承载「HC 家族的审计启发式」：模块匹配模式、名称 token、数值阈值等；
    - 不存放具体业务系统的业务阈值（例如某单一服务的特定超时/重试次数）；
      此类参数应由各业务域自己的配置系统管理，HC 只负责识别可疑硬编码形态；
    - 字段设计应尽量保持中性和可复用，避免写入仅为某一个项目/仓库服务的
      特殊规则。

    禁止行为
    ========
    - 禁止在此模型中加入与运行期环境强绑定的动态状态（例如当前环境名字、
      feature flag 的实时开关等）；
    - 禁止新增 "自由形态" 字段（如 ``dict[str, object]``、嵌套 payload 等）：
      HCConfig 必须保持字段一一对应、强类型可审计；
    - 禁止在配置里编码复杂逻辑或条件判断，这些应当在
      :mod:`tools.court.laws.hc001` 中以可测试的 Python 逻辑表达，配置只提供
      简单数据（列表、阈值、关键字）。
    """

    # constants 相关（主要服务 HC002/HC003/HC004）
    module_patterns: list[str]
    naked_const_exempt_patterns: list[str]
    system_const_prefixes: list[str]
    allowed_naked_patterns: list[str]
    typevar_pattern: str

    # strings 相关（主要服务 HC001）
    # 行级快速排除的片段（统一转小写后在整行上做包含判断）。
    exclude_substrings: list[str]

    # 命中则整行豁免的字符串片段（例如旧 hardcode.yaml 中的 payload.strings）。
    exempt_strings: list[str]

    # 报表/Prompt 生成相关文件路径模式，用于限定特殊豁免逻辑的适用范围。
    report_generator_files: list[str] = []  # noqa: RUF012

    # 日志/异常/类型别名/f-string 等常见模式的前缀或关键字。
    logger_prefixes: list[str]
    exception_call_prefixes: list[str]
    typealias_keywords: list[str]
    fstring_prefixes: list[str]

    # numeric_params 相关（主要服务 HC005）
    # 整型参数的业务上限阈值（例如最大窗口大小、最大 top_k 等）。
    int_max: int

    # 被视为“控制型参数”的最小值（小于该值的整数直接豁免）。
    min_control_value: int

    # 命中即强烈怀疑是可调 label/score 阈值的名称 token。
    strong_name_tokens: list[str]

    # 较弱的名称 token：配合数值范围与上下文使用。
    weak_name_tokens: list[str]

    # 控制型 token：常见的重试/窗口/上限等关键词。
    control_tokens: list[str]

    # 名称片段豁免表（包含匹配即可豁免数值魔法检查）。
    exempt_names: list[str]


class BCConfig(PyCourtBase):
    """BC 系列（疆域边界相关）配置模型。

    场景说明
    ========
    - 该模型承载与“边界文件”识别与契约类型来源相关的结构性规则；
    - 默认配置遵循一个常见分层约定：
      - HTTP 路由层位于 ``api/routes/`` 目录下；
      - 第三方适配器位于 ``infra/adapters/**`` 目录树下；
      - 核心契约类型集中在 ``core.base.types`` 与 ``core.dto`` 等模块中；
      - API 级契约类型集中在 ``api.http`` 相关模块中；
    - 这些约定不应被写死在 Law 实现内部，而应通过配置模型统一暴露，便于
      不同项目按自身拓扑结构进行调整。

    配置字段
    ========
    - ``router_dir_patterns``: 用于识别 HTTP 路由层文件的路径片段/通配模式；
    - ``adapter_dir_patterns``: 用于识别 infra 适配器层文件的通配模式；
    - ``core_contract_module_suffixes``: 被视为“核心契约模块”的模块名后缀集合，
      典型值如 ``["core.base.types", "core.dto"]``；
    - ``api_contract_module_suffixes``: 在路由层额外允许作为契约模块的后缀集合，
      例如 ``["api.http"]``。
    """

    router_dir_patterns: list[str] = Field(
        default_factory=lambda: ["api/routes/"],
        description="HTTP 路由层目录识别模式（子串匹配）",
    )
    adapter_dir_patterns: list[str] = Field(
        default_factory=lambda: ["infra/adapters/**"],
        description="infra 适配器层目录识别模式（fnmatch 通配）",
    )
    core_contract_module_suffixes: list[str] = Field(
        default_factory=lambda: ["core.base.types", "core.dto"],
        description="核心契约类型模块名后缀集合（用于 ImportFrom 模块匹配）",
    )
    api_contract_module_suffixes: list[str] = Field(
        default_factory=lambda: ["api.http"],
        description="路由层额外允许的 API 契约模块名后缀集合",
    )


class UWConfig(PyCourtBase):
    """UW 系列（Unit of Work 相关）配置模型。

    场景说明
    ========
    - 用于描述“业务仓储所在目录”与“系统仓储子目录”等与 UoW 法官相关的
      目录拓扑约定；
    - 默认配置假定业务仓储位于 ``infra/database/repository`` 目录树下，
      而系统仓储位于其 ``system`` 子目录中。

    配置字段
    ========
    - ``infra_repo_subpath``: 业务仓储根目录（相对于项目根的子路径，不含根包）；
    - ``infra_system_repo_subpath``: 系统仓储子目录，相对于项目根的子路径。
    """

    infra_repo_subpath: str = Field(
        default="infra/database/repository",
        description="业务仓储根目录子路径（不含根包名前缀）",
    )
    infra_system_repo_subpath: str = Field(
        default="infra/database/repository/system",
        description="系统仓储子目录子路径（不含根包名前缀）",
    )


class VTConfig(PyCourtBase):
    """VT 系列（向量事务相关）配置模型。

    场景说明
    ========
    - 用于描述 Vector 提供商模块的位置发现规则；
    - 默认配置假定该模块位于 ``<root>/infra/vector/providers.py``。

    配置字段
    ========
    - ``provider_search_pattern``: 使用子串匹配的方式在仓库根下递归查找
      Vector 提供商模块的路径，例如 ``"infra/vector/providers.py"``。
    """

    provider_search_pattern: str = Field(
        default="infra/vector/providers.py",
        description="用于定位 Vector 提供商模块的相对路径片段",
    )


class PCConfig(PyCourtBase):
    """PC 系列（参数分类相关）配置模型。

    场景说明
    ========
    - 用于描述“核心常量模块”在项目中的典型位置；
    - 默认配置假定该目录为 ``<root>/core/constants/``。

    配置字段
    ========
    - ``core_constants_subpath``: 核心常量目录的子路径片段，用于快速筛选需要
      执行 PC001 审查的文件。
    """

    core_constants_subpath: str = Field(
        default="core/constants/",
        description="核心常量目录子路径片段（不含根包名前缀）",
    )


class DIDiConfig(PyCourtBase):
    """DI 系列（依赖倒置相关）专用配置模型。

    场景说明
    ========
    - 承载 DI001 在“API 外交特区”下允许的模块前缀与精确模块名白名单；
    - 默认配置假定：
      - API 路由层位于 ``<root>/api`` 目录下；
      - 可自由导入的模块前缀包括 ``<root>.api.*`` 与 ``<root>.core.*``；
      - 典型的 API 适配模块为 ``<root>.app.dependencies``；
    - 这些约定不应固定写死在 Law 实现内部，而应通过配置模型暴露，便于
      不同项目根据各自的 API/DI 结构进行调整。

    配置字段
    ========
    - ``api_allowed_prefixes``: API 外交特区内允许导入的模块前缀列表；
    - ``api_allowed_exact``: API 外交特区内允许导入的精确模块名列表。
    """

    api_allowed_prefixes: list[str] = Field(
        default_factory=list,
        description="API 外交特区内允许导入的模块前缀列表",
    )
    api_allowed_exact: list[str] = Field(
        default_factory=list,
        description="API 外交特区内允许导入的精确模块名列表",
    )


class CourtConfig(PyCourtBase):
    """最高法院统一配置快照（运行期）。

    由 :func:`tools.court.loader.load_court_config` 统一构建，一次性提供给
    ChiefJustice 与各 Law 实现使用：

    - ``laws``:        CourtLaws 结构法典（各法律条文的开关/豁免/描述等）；
    - ``texts``:       CourtTexts 文案法典（尤其是各法条的判决模板）；
    - ``exemptions``:  CourtExemptions 治外法权视图（路径/文件级豁免）。

    Law 实现通常只依赖两个辅助方法：
    - :meth:`get_exempt_files`: 取得某法条的路径豁免模式列表；
    - :meth:`get_judge_template`: 取得某法条的人类可读判决模板。
    其余底层 YAML 结构细节由 CourtConfig 与 loader 层统一封装。
    """

    laws: PyCourtLaws
    texts: CourtTexts = Field(default_factory=CourtTexts)
    exemptions: CourtExemptions = Field(default_factory=CourtExemptions)
    # 下列家族级配置由 loader 显式提供，作为必填字段，不在此处设置默认工厂。
    hc: HCConfig
    bc: BCConfig
    uw: UWConfig
    vt: VTConfig
    pc: PCConfig
    di: DIDiConfig

    def get_exempt_files(self, code: str) -> list[str]:
        """返回给定法条编号的路径/文件级豁免列表的副本。"""

        patterns = self.exemptions.files.get(code, [])
        # 返回副本避免调用方意外修改内部状态
        return list(patterns)

    def get_judge_template(self, code: str) -> str:
        """根据法条编号返回判决模板字符串。

        受众策略由环境变量 ``PYCOURT_AUDIENCE`` 控制：

        - 未设置 / 非 "ai" → 使用人类友好版 ``template`` 字段；
        - 设置为 "ai"        → 优先使用 ``template_ai`` 字段，缺失时回退到
          ``template``，以保证向后兼容。

        若最终无法取得合法字符串，将抛出 KeyError，鼓励在测试阶段尽早暴露
        配置问题。
        """

        entry = self.texts.judges.root.get(code)
        if not isinstance(entry, dict):  # pragma: no cover - 防御性分支
            msg = f"judge template entry not found for code: {code!r}"
            raise KeyError(msg)

        audience = os.getenv("PYCOURT_AUDIENCE", "human").strip().lower()
        if audience == "ai":
            # AI 模式下优先使用 template_ai，缺失时回退到 template
            tpl = entry.get("template_ai") or entry.get("template")
        else:
            tpl = entry.get("template")

        if not isinstance(tpl, str):  # pragma: no cover - 防御性分支
            msg = (
                "judge template missing 'template'/'template_ai' field for code: "
                f"{code!r}"
            )
            raise KeyError(msg)

        return tpl
