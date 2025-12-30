"""
🏛️ PyCourt 质量保证法典基类模型

所有外部数据必须通过 Pydantic 模型进行验证。
本模块定义了质量审计工具的所有数据结构，尽量消除 Any 类型和裸容器滥用。
"""

from pydantic import BaseModel, ConfigDict, Field


class PyCourtBase(BaseModel):
    """Court 领域内所有模型的共同基类。

    统一提供：
    - enabled: 是否启用该条款/组件；
    - exempt_files: 路径级治外法权（fnmatch 模式）；
    - description: 对该条款/组件职责的简短说明。
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
        extra="forbid",
        frozen=False,
        validate_default=True,
    )
    enabled: bool = Field(default=True, description="是否启用该条款/组件")
    exempt_files: list[str] = Field(
        default_factory=list,
        description="路径级治外法权（fnmatch模式），为空表示不做路径豁免",
    )
    description: str = Field(
        default="",
        description="对该条款/组件职责的简短说明，供文档与调试使用",
    )


# === 🏛️ 法院法官专用法律模型（按编号分组）===
# 这里定义的是「法律文本」的数据契约，由最高法院与各法官共同使用。


class HC001(PyCourtBase):
    """🏛️ HC001 硬编码审查官法条配置。

    场景说明：
    - 审计目标：检测代码中的「硬编码字符串/常量/数值魔法」，避免业务阈值、常量
      散落在各处而难以维护或按环境调优；
    - 典型风险：
      - 接口返回值、提示文案、错误信息等直接写死在代码中，难以国际化或统一管理；
      - 常量值分散在不同模块，无法集中治理，导致版本漂移和行为不一致；
      - 重试次数、窗口大小、阈值等数值魔法写死在代码里，线上不可调优；
    - 本模型只关心 HC 系列是否启用、路径级豁免和简要描述；
      具体的 constants/strings/numeric_params 细粒度配置由 :class:`HCConfig`
      承载，对应 `config.yaml -> laws.hc001.*` 段。
    """


class LL001(PyCourtBase):
    """🏛️ LL001/LL002 过度复杂审查官法条配置。

    场景说明：
    - 审计目标：约束单个函数/模块的体积与复杂度，防止出现「一眼看不完」的巨型
      函数或高圈复杂度逻辑，降低维护成本；
    - 典型风险：
      - 新人不敢改的「上古函数」，一处修改牵一身；
      - 逻辑分支过多，容易遗漏边界条件或引入回归；
    - 本模型仅控制 LL 系列是否启用、路径级豁免和描述；
      具体行数/复杂度阈值由 `tools.court.laws.ll001` 中的法官常量定义。
    """


class DS001(PyCourtBase):
    """🏛️ DS001/DS002 文档字符串审查官法条配置。

    场景说明：
    - 审计目标：确保模块/类/函数具备必要的 docstring，避免出现「黑盒函数」；
    - 典型风险：
      - 关键业务入口没有任何说明，知识只存在于少数开发者脑中；
      - 公共接口对外行为不清晰，调用方只能通过阅读实现猜测用法；
    - 本模型仅控制 DS 系列是否启用、路径级豁免和描述；
      具体最小 docstring 长度等规则由 `tools.court.laws.ds001` 内部常量控制。
    """


class BC001(PyCourtBase):
    """🏛️ BC001 疆域边界审查官法条配置。

    场景说明：
    - 审计目标：约束「领域边界」与「适配层」位置，防止业务逻辑泄漏到接口层，
      或基础层直接依赖上层实现，破坏洋葱分层；
    - 典型风险：
      - HTTP handler 直接操作领域对象，缺少清晰的应用服务/用例层；
      - 基础设施模块反向依赖业务模块，形成难以解开的循环；
    - 本模型仅控制 BC 系列是否启用、路径级豁免和描述；
      具体路由/适配器目录模式等规则由 `tools.court.laws.bc001` 内部常量解释。
    """


class AC001(PyCourtBase):
    """🏛️ AC001/AC002/AC003 无结构数据审查官法条配置。

    场景说明：
    - 审计目标：禁止在类型系统边界偷偷混入 ``dict[str, object]`` 等无结构
      容器，推动所有外部数据通过 DTO / TypedDict / Protocol 等结构化契约；
    - 典型风险：
      - 「万能 dict」在系统内部横传，类型信息丢失，修改一处牵连全局；
      - 边界对象缺少 schema，无法用 mypy/pyright 做静态校验；
    - 本模型仅控制 AC 系列是否启用、路径级豁免和描述；
      具体的“无结构嫌疑点”规则由 `tools.court.laws.ac001` 等实现。
    """


class UW001(PyCourtBase):
    """🏛️ UW001/UW002/UW003/UW004 - UoW 系列法官法条配置。

    场景说明：
    - 审计目标：确保复杂写操作在「事务单元 (Unit of Work)」内完成，避免
      半途失败导致状态不一致；
    - 典型风险：
      - 同一业务用例内多处直接操作仓储/外部系统，没有统一提交/回滚边界；
      - 事务边界分散在视图层/服务层/仓储层，难以推理；
    - 本模型仅控制 UoW 系列是否启用、路径级豁免和描述；
      具体检测规则由 UoW 法官实现类负责解释。
    """


class DT001(PyCourtBase):
    """🏛️ DT001 时间法官法条配置。

    场景说明：
    - 审计目标：禁止在代码中直接调用 ``datetime.now()/utcnow()``，强制通过
      ClockPort 接口获取时间，便于测试与时间线控制；
    - 典型风险：
      - 代码中散落真实时间调用，导致集成测试无法稳定复现；
      - 无法模拟未来/过去场景进行回归或演练；
    - 本模型仅控制 DT 系列是否启用、路径级豁免和描述；
      具体拦截规则由 ``tools.court.laws.dt001`` 实现。
    """


class OU001(PyCourtBase):
    """🏛️ OU001 灰色迷雾审查官法条配置。

    场景说明：
    - 审计目标：识别代码中「灰色地带」的逻辑（例如调试入口、临时脚本、
      未明确归属的 helper），避免这些区域悄然演变为核心依赖；
    - 典型风险：
      - 临时调试脚本被业务代码依赖，形成非正式但关键的路径；
      - 边界函数缺少明确的输入/输出契约，难以纳入整体架构；
    - 本模型仅控制 OU 系列是否启用、路径级豁免和描述；
      具体识别规则由 ``tools.court.laws.ou001`` 等法官实现。
    """


class PC001(PyCourtBase):
    """🏛️ PC001 参数分类审查官法条配置。

    场景说明：
    - 审计目标：规范函数参数的分类（domain dto / infra handle / config 等），
      防止出现「万能参数」或难以理解的参数列表；
    - 典型风险：
      - 函数签名包含过多弱语义参数（如 ``config``, ``options``, ``flags``）；
      - 领域对象与技术对象混杂在同一参数列表中，职责不清；
    - 本模型仅控制 PC 系列是否启用、路径级豁免和描述；
      具体分类规则由 ``tools.court.laws.pc001`` 实现。
    """


class TP001(PyCourtBase):
    """🏛️ TP001 测试纯净度审查官法条配置。

    场景说明：
    - 审计目标：保证测试代码「纯净」，避免引入网络请求、真实时间、随机性
      等难以控制的副作用；
    - 典型风险：
      - 测试依赖外部服务或真实时间，导致结果不稳定；
      - 测试中混入过多逻辑，掩盖真实被测行为；
    - 本模型仅控制 TP 系列是否启用、路径级豁免和描述；
      具体纯净度规则由 ``tools.court.laws.tp001`` 中的 TheTestPurityLaw 实现。
    """


class SK001(PyCourtBase):
    """🏛️ SK001 技能使用审查官法条配置。

    场景说明：
    - 审计目标：约束「技能/能力模块」的调用方式，防止滥用某些高危或代价高的
      技能（例如执行外部命令、直接操作生产数据等）；
    - 典型风险：
      - 开发/测试代码中不当调用生产级技能；
      - 技能调用散落在各处，缺少集中管控入口；
    - 本模型仅控制 SK 系列是否启用、路径级豁免和描述；
      具体技能审计规则由 ``tools.court.laws.sk001`` 实现。
    """


class VT001(PyCourtBase):
    """🏛️ VT001 向量事务法官法条配置。

    场景说明：
    - 审计目标：规范向量检索/写入过程中的事务行为，避免出现部分写入、
      复制不完整或索引未同步的情况；
    - 典型风险：
      - 多步向量更新操作中途失败，导致索引与存储不一致；
      - 在业务事务提交前就对向量索引执行更新；
    - 本模型仅控制 VT 系列是否启用、路径级豁免和描述；
      具体规则由 ``tools.court.laws.vt001`` 实现。
    """


class RE001(PyCourtBase):
    """🏛️ RE001/RE002/RE003 门面纪律法官法条配置。

    场景说明：
    - 审计目标：保证模块「门面」(facade) 文件（例如 ``__init__.py``）保持
      精简，只做导出与轻量装配，而不是承载复杂业务逻辑；
    - 典型风险：
      - ``__init__.py`` 中堆积大量业务代码，难以理解模块真实边界；
      - 门面层偷偷承担核心职责，导致依赖关系混乱；
    - 本模型仅控制 RE 系列是否启用、路径级豁免和描述；
      具体行数/结构规则由 ``tools.court.laws.re001`` 实现。
    """


class DI001(PyCourtBase):
    """🏛️ DI001 依赖倒置审查官法条通用配置。

    场景说明：
    - 审计目标：确保高层模块不直接依赖低层实现细节，而是依赖抽象接口，
      遵守依赖倒置原则 (Dependency Inversion Principle)；
    - 典型风险：
      - 领域层直接 import 基础设施实现，导致难以替换实现或进行单测；
      - API 层与应用层互相穿插依赖，架构方向混乱；
    - 本模型仅控制 DI 系列是否启用、路径级豁免和描述；
      具体「API/入口」等分层语义由 `tools.court.laws.di001` 通过路径/模块名
      自行推导，不在 Court 核心模型写死。
    """

    pass


class TC001(PyCourtBase):
    """🏛️ TC001 循环依赖/TYPECHECKING 审查官法条配置。

    场景说明：
    - 审计目标：检测 Python 模块之间的循环依赖，以及滥用 ``typing.TYPE_CHECKING``
      的情况，防止类型检查与运行时行为严重偏离；
    - 典型风险：
      - 业务模块之间互相 import，导致初始化顺序不可控；
      - 在 ``TYPE_CHECKING`` 分支中引入与运行时不同的依赖图；
    - 本模型仅控制 TC 系列是否启用、路径级豁免和描述；
      具体循环检测/TYPE_CHECKING 使用规范由 ``tools.court.laws.tc001`` 实现。
    """


# === 🏛️ 法院法律总表（CourtLaws）===
class PyCourtLaws(PyCourtBase):
    """法院法官使用的全部法律条文（按编号分组）。"""

    # HC001 仍然完全由外部 hardcode.yaml 提供配置，其余法条使用代码内默认值。
    hc001: HC001
    ll001: LL001 = Field(default_factory=LL001)
    ds001: DS001 = Field(default_factory=DS001)
    bc001: BC001 = Field(default_factory=BC001)
    ac001: AC001 = Field(default_factory=AC001)
    uw001: UW001 = Field(default_factory=UW001)
    dt001: DT001 = Field(default_factory=DT001)
    ou001: OU001 = Field(default_factory=OU001)
    pc001: PC001 = Field(default_factory=PC001)
    tp001: TP001 = Field(default_factory=TP001)
    sk001: SK001 = Field(default_factory=SK001)
    vt001: VT001 = Field(default_factory=VT001)
    re001: RE001 = Field(default_factory=RE001)
    di001: DI001 = Field(default_factory=DI001)
    tc001: TC001 = Field(default_factory=TC001)


# === 🏛️ 法院法官模型（PyCourtJudge）===
class PyCourtJudge(PyCourtBase):
    """🏛️ 帝国最高法院法官模型，只承载法院领域内的法律总表。

    目前仅聚合 `laws` 子树（PyCourtLaws），对应 `tools/dev/yaml` 中的
    `laws:` 段。其他子系统（prompt/tools_audit/ops 等）的配置由各自 loader 与
    YAML 文件接管，不再通过 PyCourtJudge 侧载。
    """

    laws: PyCourtLaws
