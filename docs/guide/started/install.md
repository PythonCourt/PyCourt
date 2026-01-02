# 安装与启动：让 PyCourt 跑起来
> 目标：让初次接触 PyCourt 的你，在几分钟内完成：安装 → 初始化 → 启动。

---

## 第一步：安装 

### 方式一：全局安装

```bash
pipx install pycourt
```
◦  pipx 会给 pycourt 创建一个单独的虚拟环境；
◦  你机器上的所有项目都可以直接在命令行里用 pycourt（就像 black、ruff、poetry 一样）；  
◦  不需要在每个项目里重复安装，只要一个 pipx install 就够了。

### 方式二：项目依赖

```bash
pip install pycourt
```
- pycourt 被视为“这个项目的依赖”；
- 另一个项目如果也想用，就要在它自己的虚拟环境里再装一次；
- 好处是：每个项目可以固定自己的版本，比如：
    - 项目 A 用 pycourt==0.2.x
    - 项目 B 用 pycourt==0.3.x

### 验证安装
安装完成后，可以先确认一下版本与帮助信息：

```bash
pycourt --help
```

看到包括 `file` / `scope` / `project` / `init` 在内的子命令列表，表示安装成功。

---


## 第二步 启动

在项目根做一次“整体预览”，例如：

```bash
pycourt scope . --non-blocking  
```

PyCourt会：

- 以当前目录为根，递归扫描 `.py` 文件；
- 按法条输出发现的“违宪行为”以及解决方案。

---

## 下一步：配置

此时，你可能会看到满屏的问题，不要慌，这是让你的代码变得健康和优雅的开始。
现在，你已经掌握了 pycourt 的基本用法，接下来，你需要进一步掌握更多使用方法和技巧，来掌控你的代码质量。

你可以进一步：
- [完善配置](config.md)
- [使用脚本](script/index.md)
- [了解法典](laws/index.md)