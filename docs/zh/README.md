# 🏛️ PythonCourt

由 AST 分析和 Rule 系统的 Python 代码审计引擎，确保AI生成的代码符合生产级质量标准。

https://img.shields.io/badge/python-3.8+-blue.svg

https://img.shields.io/badge/License-MIT-yellow.svg

https://img.shields.io/badge/PRs-%E6%AC%A2%E8%BF%8E-brightgreen.svg


## 📜 法院管辖职责（审计什么）

>"PythonCourt帮助你以法庭的权威为你的Python代码库建立司法系统，对代码的违规行为做出精确"判决"，让你（你的代码生成 AI）写出更好的代码，而不是为了惩罚。愿你的代码经得起时间的审判。" 

| 序号 | 法律 | 法庭 | 罪行 | 描述 | 等级 |
|------|----------|----------|----------|----------|-----|
| 1 | **TC001** | 循环依赖法庭 | 进口走私罪 | 使用`TYPE_CHECKING`等手段掩护循环依赖 | 🔴 严重 |
| 2 | **RE001** | 门面纪律法庭 | 门面僭越罪 | 前台接待`__init__.py`越权处理公司核心业务 | 🔴 严重 |
| 3 | **DI001** | 依赖倒置法庭 | 底层僭越罪| 臣子竟敢直接依赖皇帝的具体谕令而非圣旨规范 | 🔴 严重 |
| 4 | **UW001** | 仓库事务法庭 | 账目混乱罪 | 会计私自开启/关闭账本而不通过财务总监审批 | 🔴 严重 |
| 5 | **BC001** | 疆域边界法庭 | 非法越境罪 | 原始数据(dict/list)携带假护照跨越领域边界 | 🔴 严重 |
| 6 | **VT001** | 向量触发法庭 | 信号干扰罪 | 事件处理系统擅自修改协议规定的信号频率 | 🔴 严重 |
| 7 | **AC001** | 类型诈骗法庭 | 类型诈骗罪 | Any、cast、dict 扮演多重身份欺骗类型系统 | 🔴 严重  |
| 8 | **OU001** | 裸对象法庭 | 裸奔伤风罪 | 代码中的object赤身裸体，毫无领域身份标识 | 🔴 严重  |
| 9 | **DT001** | 时间漂移法庭 | 时间伪造罪 | 程序擅自冻结、加速或伪造宇宙时间常量 | 🟠 高度 |
| 10 | **SK001** | 技能配置法庭 | 技能冒用罪 | 未持有合格技能证书(SkillID)擅自调用专业能力 | 🟠 高度 |
| 11 | **DS001** | 文档字符串法庭 | 沉默是金罪 | 公共接口故作高深，拒绝提供使用说明书 | 🟡 中等 |
| 12 | **LL001** | 代码复杂度法庭 | 思维迷宫罪 | 函数变身俄罗斯套娃，循环嵌套深度堪比盗梦空间 | 🟡 中等 |
| 13 | **HC001** | 硬编码法庭 | 数字雕刻罪 | 将魔法数字和神秘字符串刻在代码石碑上永世流传 | 🟡 中等 |
| 14 | **HC002** | 常量风格法庭 | 散兵游勇罪 | 常量值如逃兵般散落各地，拒绝加入正规军(类/枚举) | 🟡 中等 |
| 15 | **PC001** | 可调参数法庭 | 走后门罪 | 配置参数试图绕过官方认证通道(RuleProvider) | 🟡 中等 |
| 16 | **TP001** | 测试忠诚度法庭 | 测试演员罪 | 测试用例演技浮夸，看似努力实则毫无实际贡献 | 🔵 轻度 |

*从长期实践中总结，并会持续更新和优化*

---
### 法院寄语：

- "最好的代码不是没有违规，而是知道为什么违规"

- "法律保护的不是完美，而是可维护性"

- "今天的豁免是明天的技术债务"

---

## ⚡ 安装与使用
PyCourt 已发布为独立的 Python 包，目前在 Python **3.11–3.14** 上测试通过（开发主力环境为 3.14）。
```bash
# 多项目开发
pipx install pycourt

# 或在单个项目虚拟环境中（推荐）
pip install pycourt

# 或作为 poetry 开发依赖
poetry add -D pycourt
```
基本使用

```bash
# 审计单个 Python 文件；
pycourt file < path >   
# 审计目录或单个文件；
pycourt scope < target >
# 基于配置的项目级审计（详见文档说明）。
pycourt project
```
## 🏗️ 高级配置 - 定制你的法院


## 🧑‍⚖️ 司法哲学

为什么采用"法院"隐喻？

- 发布正式判决，附带具体法律代码
- 提供判例，通过违规示例指导
- 允许上诉，通过配置豁免机制
- 实现正义，给出清晰、可执行的裁决

法治原则

PythonCourt 的每一条"法律"都具备：

- 可解释 - 明确的违规标准
- 正当性 - 基于已验证的最佳实践
- 可配置 - 可按项目启用/禁用
- 可操作 - 包含修复指导
- 可玩梗 - 技术也可以好玩

## 🚀 实际影响

PyCourt审判前

```python
# 违反BC001, DI001, HC001
def process_data(data: dict) -> Any: # 滥用any
    result = data.get("value", 0) * 1.1  # 硬编码乘数
    save_to_db(result)  # 直接数据库依赖
    return cast(int, result)  # 类型强制转换
```
PyCourt判决后

```python
# 符合所有法律
from typing import TypedDict
from dataclasses import dataclass

@dataclass
class ProcessedResult:
    value: float
    multiplier: float = 1.1  # 可配置常量

class DataProcessor:
    def __init__(self, repository: DataRepository):  # 符合DI001
        self.repository = repository
    
    def process_data(self, data: InputDTO) -> ProcessedResult:  # 使用 dto，符合BC001
        """使用可配置乘数处理输入数据。"""  # 添加字符串，符合DS001
        result = ProcessedResult(
            value=data.value * self.multiplier
        )
        self.repository.save(result)
        return result
```

## 🤝 贡献新法律

想要为法院增加新的"法律"？请查看我们的贡献指南。

提议法律：在Discussions中创建RFC
实现法官：扩展BaseLawJudge
添加测试用例：提供违规示例
提交审查：包含完整文档的PR
📚 文档与资源

完整法律目录 - 所有法律和示例的完整列表
配置指南 - 高级法院设置
集成示例 - CI/CD、IDE、pre-commit
案例研究 - 实际改进案例


⚖️ 为你的代码库实现正义

"好的代码不仅正确；它还公正。" - Python Court宣言
准备好为你的Python代码实现正义了吗？

🔧 开发与调试

直接从源码运行

bash
# 克隆仓库
git clone https://github.com/yourusername/pycourt.git
cd pycourt

# 设置环境
export PYTHONPATH=$(pwd)/src:$PYTHONPATH

# 直接运行（无需安装）
python src/pycourt/cli.py audit .
自我审查

bash
# 最高法院审查自己的代码
python src/pycourt/cli.py audit src/pycourt

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

🤝 加入社区

Python Court - 让你的代码质量无可争议。

<p align="center"> <br> <img src="https://img.shields.io/github/stars/yourusername/pycourt?style=social" alt="GitHub stars"> <img src="https://img.shields.io/github/forks/yourusername/pycourt?style=social" alt="GitHub forks"> <img src="https://img.shields.io/github/issues/yourusername/pycourt" alt="GitHub issues"> <br><br> <strong>让你的代码质量无可争议</strong> </p>
