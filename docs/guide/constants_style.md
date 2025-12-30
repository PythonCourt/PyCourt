# PyCourt 常量风格指南（命名空间 · 苹果风）

> 本文不是强制规范，而是 PyCourt 自带法典背后的个人风格说明。
> 你可以完全采纳，也可以按需调整或关闭相关法条（尤其是 HC003）。

PyCourt 的硬编码家族（HC 系列）有一个核心理念：

> **随手一写的裸常量，是未来的技术债；
> 经过命名和分组的常量，才是“法典的一部分”。**

在实现上，这体现在两个层面：

- 规则层：HC001 / HC003 会对“散落的裸常量”比较严格。
- 风格层：推荐使用“命名空间类 + `Final`”来组织常量（俗称“苹果风”）。

下面是推荐的写法和动机。

---

## 1. 反例：业务代码里的散落裸常量

这些写法是 HC003 / HC005 想要打击的典型目标：

```python path=null start=null
# user_profile.py
MAX_LOGIN_RETRY = 3
WELCOME_MESSAGE = "欢迎使用 ..."

SESSION_ICEBREAKER = "session.icebreaker"
```

问题不在于“有没有类型注解”，而在于：

- 常量散落在业务模块顶部，没有统一归档；
- 读者难以判断：这是配置？协议？还是随手写死的业务参数？
- 想在全局重构这些值，需要在仓库里“全文搜字符串”。

PyCourt 默认法典会把这类写法视为“可疑裸常量”，交给 HC003/HC005 审查。

---

## 2. 推荐模式一：集中常量模块 + 模块级 `Final`

对于很多项目，**一个简单、足够 Pythonic 的做法**是：

- 建一个专门的 constants 模块 / 目录，例如：
  - `core/constants/skill_ids.py`
  - `core/constants/timeouts.py`
- 在这些文件里用模块级 `Final` 定义常量：

```python path=null start=null
# core/constants/skill_ids.py
from typing import Final

SESSION_ICEBREAKER: Final[str] = "session.icebreaker"
SESSION_GUIDANCE: Final[str] = "session.guidance"
```

在 **“常量仓库”模块内部**，这种写法是被视为“法典定义”，
而不是“散落裸常量”，HC003 默认会对这类模块宽容得多。

---

## 3. 推荐模式二：命名空间类 + `Final`（苹果风）

这是 PyCourt 自身大量使用、也最能体现作者性格的一种写法。

### 3.1 基本示例

```python path=null start=null
from typing import Final


class ProjectFiles:
    """命名空间：项目级文件/路径相关常量。"""

    PYPROJECT_FILENAME: Final[str] = "pyproject.toml"


class DictContractTypes:
    """命名空间：dict 契约检查相关的基础类型集合。"""

    BASIC_VALUE_TYPES: Final[set[str]] = {
        "str",
        "int",
        "float",
        "bool",
        "bytes",
        "None",
        "Any",
        "object",
    }
```

使用时：

```python path=null start=null
from pycourt.utils import ProjectFiles, DictContractTypes

pyproject_path = root / ProjectFiles.PYPROJECT_FILENAME

if value_type in DictContractTypes.BASIC_VALUE_TYPES:
    ...
```

好处很直接：

- 可读性强：一眼就知道这是“项目文件相关常量”，不是业务字符串；
- IDE 友好：输入 `ProjectFiles.` / `DictContractTypes.` 就能补全所有成员；
- 对 HC003 来说：这是“集中管理的法典”，而不是散落的裸常量。


### 3.2 PyCourt 中的典型用法

#### YAML 结构键名

```python path=/Users/nian/PyCourt/pycourt/loader.py start=42
class YamlSectionKeys:
    """命名空间：config/exempt/judges_text 等 YAML 段落键名。"""

    LAWS: Final[str] = "laws"
    EXEMPTIONS: Final[str] = "exemptions"
    FILES: Final[str] = "files"
    COURTROOM: Final[str] = "courtroom"
    JUDGES: Final[str] = "judges"


class LawFamilyKeys:
    """命名空间：各 Law 家族在 YAML 中的小写键名。"""

    HC001: Final[str] = "hc001"
    BC001: Final[str] = "bc001"
    UW001: Final[str] = "uw001"
    VT001: Final[str] = "vt001"
    PC001: Final[str] = "pc001"
    DI001: Final[str] = "di001"
```

调用代码从：

```python path=null start=null
laws_section = root.get("laws")
hc_law_raw = laws_raw.get("hc001")
```

变成：

```python path=/Users/nian/PyCourt/pycourt/loader.py start=103
laws_section = root.get(YamlSectionKeys.LAWS)
...
hc_law_raw = laws_raw.get(LawFamilyKeys.HC001)
```

这就是“苹果风”的典型手感：

- 代码在“与一个有名字的概念对话”，而不是“对着字符串戳来戳去”；
- 读者不会怀疑 `"laws"` 是不是哪个业务字段，抽象层级非常清晰。


#### 路径相关配置

```python path=/Users/nian/PyCourt/pycourt/config/yaml_paths.py start=24
class YamlPathConfig:
    """命名空间：PyCourt 内置 YAML 相关路径常量。"""

    PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent.parent


def quality_yaml_path() -> Path:
    return YamlPathConfig.PACKAGE_ROOT / "yaml" / "config.yaml"
```

---

## 4. HC003 / HC001 与常量风格的关系

### 4.1 PyCourt 默认的态度

- **鼓励**：
  - 集中常量模块（`core/constants/...`）；
  - 命名空间类 + `Final` 的常量组织方式；
- **审查**：
  - 业务模块里散落的裸常量定义（`FOO = 3` / `"timeout"` 等）。

换句话说，**PyCourt 的规则默认体现了作者的个人审美**，
但不会强迫所有人都写成完全一样的风格。


### 4.2 不喜欢这种风格怎么办？

你有几种简单选择：

1. **在命令行层面关掉 HC003**

   ```bash
   pycourt scope . --select HC001,HC005      # 不跑 HC003
   # 或者
   pycourt scope . --ignore HC003
   ```

2. **在 `pycourt.yaml` 里为特定路径豁免 HC003**

   ```yaml
   exemptions:
     HC003:
       files:
         - "legacy/**"
         - "third_party/**"
   ```

3. **fork / 定制 HC 家族**

   真正的高级玩家可以直接在 `pycourt/laws/hc001.py` / `config.yaml`
   里调整规则，让 HC003 更宽松或更严格。

PyCourt 的设计初衷是：**把一套“有态度的默认规则”开源出来，
而不是强迫所有人遵守单一编码宗教。**

---

## 5. 实战迁移建议

如果你希望把自己项目逐步迁移到这种风格，可以按下面步骤来：

1. **先建立常量集中地**
   - 新建 `core/constants/` 目录，按领域拆分文件：`skill_ids.py`、`timeouts.py` 等。

2. **把“散落裸常量”搬进去**
   - 先不管命名空间类，先集中到一个地方，再慢慢整理。

3. **为稳定下来的常量分命名空间类**
   - 例如：

     ```python
     class SessionSkillId:
         ICEBREAKER: Final[str] = "session.icebreaker"
         GUIDANCE: Final[str] = "session.guidance"
     ```

4. **最后，再考虑调整 HC001/HC003 的严格程度**
   - 如果你想要和 PyCourt 本身一样苛刻，就保留默认配置；
   - 如果团队不习惯，可以只在 CI 的一部分 job 里开启硬编码审查。

---

## 6. 心态：规则是“礼物”，不是“枷锁”

PyCourt 自带的常量风格，来自作者在实际工程中的偏好：

- 字符串 / 数值不是“随便写的字面量”，而是“有名字的规则条文”；
- 命名空间类像一本本小法典，把概念分门别类摆好；
- 工具（HC001/HC003）只是帮你守住这套美学的一致性。

你可以：

- 全盘接受，把仓库打造成一座“极简苹果风法院”；
- 挑自己喜欢的部分用；
- 或者，关掉某些法条，只保留你认为真正有价值的那几条。

PyCourt 会给你一套有态度的默认答案，但最终的审美，永远在你和你的团队手里。