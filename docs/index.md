# 🏛️ Python Court

> A "Code Court" for Python: an AST + rules based quality audit engine.

Python Court 是一个面向 **工程实践与架构质量** 的静态审计引擎，
不只关心 PEP8，而是把一整套“法条”落在真实项目上，例如：

- 依赖倒置（DI001）、Unit of Work（UW 系列）；
- 时间抽象（DT001）、测试纯净度（TP 系列）；
- Any / 裸 dict / 硬编码常量 等“类型偷懒”问题（AC / HC 系列）。

三把官方武器脚本——`qaf.sh` / `qas.sh` / `qa.sh`——
把这些规则组合成可直接在本地和 CI 中使用的“质量武库”。

---

## 为什么会有 Python Court？（中文）

这里你可以用自己的话写一段“创始人声明”：

- 从真实项目中遇到哪些代码质量 / 架构痛点；
- 你是如何一步步把这些经验抽象成 Law 和武器脚本的；
- 希望这个项目怎样被个人开发者和团队使用。

> 提示：先用中文写舒服就好，后面再慢慢翻译成英文版本。

---

## English Summary

Python Court is a **static architecture court** for Python projects.
Instead of focusing only on style issues, it encodes higher-level
engineering practices into a set of "laws", enforced via AST analysis.

Out of the box, it provides:

- Dependency inversion / Unit of Work / time abstraction checks;
- Rules for test purity and explicit contracts at boundaries;
- Detection of "lazy" patterns such as loose `Any`, untyped `dict`,
  hard-coded constants spread across the codebase.

On top of the engine, three official scripts — `qaf.sh`, `qas.sh`,
and `qa.sh` — act as an opinionated QA arsenal for files, modules
and whole repositories.

> The English section is intentionally concise for now.
> You can expand it later as the project stabilizes.

---

## 接下来可以做什么？

- 在 `docs/` 目录下补充各个板块的内容（Engine / Arsenal / Laws / Playbooks）；
- 把你在真实项目中的案例写成 Playbook，分享给其他开发者；
- 设计并投稿你自己的武器脚本，让 Python Court 的武库越来越丰富。
