<div align="center" markdown="1">

<a href="https://pythoncourt.com">
  <img src="docs/static/assets/pycourt-logo.svg" height="80" alt="PythonCourt Logo">
</a>

<h1>PythonCourt</h1>
<h3>An AST‑based rule engine for static auditing of Python code</h3>
<p>In the wild west of AI‑generated code, PyCourt tries to bring law and order.</p>
<br>

![PyPI](https://img.shields.io/pypi/v/pycourt?label=PyPI&color=blue)
![Python](https://img.shields.io/badge/Python-3.11%E2%86%923.14-blue)
![License](https://img.shields.io/github/license/PythonCourt/pycourt)

[![Website](https://img.shields.io/badge/Website-blue)](https://pythoncourt.com)
[![Docs (zh)](https://img.shields.io/badge/Docs-ZH-green)](docs/guide/started/index.md)
[![中文说明](https://img.shields.io/badge/README-ZH-orange)](docs/zh/README_zh.md)

</div>

---

## 📖 Brand Story: From "Coded by AI" to "Constrained AI Coding"

### **The Loop | Endless Repairs**

AI empowered me—someone who couldn't code—to build software.  
But without constraints, it generated code riddled with hidden bugs, circular dependencies, and architectural bad smells.  
I realized I wasn't creating; I was trapped in an **endless repair loop**.

### The Awakening | Laws, Not Prompts

This isn't merely an AI problem, nor can it be solved with better prompts alone.  
The core issue: **a lack of definable, explainable, repeatable constraints**.

I began codifying recurring problems into concrete "laws,"  
integrating them with PyCourt and orchestrating mature tools—  
Pyright, Mypy, Bandit, Ruff—into an automated workflow.  
Thus, PythonCourt emerged: a **system of order for AI-generated chaos**.

Now, AI must audit its own output before code enters the repository.  
The result isn't just "working code"—it's code **bounded by clear engineering discipline**.

### The Invitation | Co‑Creating This System

I'm still learning. PyCourt isn't a finished product;  
it's an **open invitation** for developers to refine it together.

Existing laws may be rough. Important patterns may be missing.  
If you spot false positives, omissions, or believe a certain smell deserves formal definition—  
**join us**. This isn't about declaring right or wrong.  
It's a collective search for **sustainable order in AI‑assisted development**.

---

## ⚖️ The Codex: Recurring Anti‑Patterns That Erode Engineering Order

The following **PyCourt Laws** are patterns I've distilled from practice.  
They aren't syntax errors, but **structural issues** that repeatedly lead to code being  
**hard to understand, maintain, or evolve**.

These laws focus on:
* **Architectural Boundaries** – Are modules at the correct abstraction level?  
* **Dependency Discipline** – Are there hidden couplings or inverted dependencies?  
* **Type Integrity** – Does the code evade constraints via `Any`, bare `dict`, or `object`?  
* **Configuration Governance** – Are parameters bypassing unified rule sources?  
* **Test Authenticity** – Do tests verify behavior, or just create false confidence?

Severity is about **blocking strategy**, not moral judgment:  


| Level | Law | Crime | Description |
|:-------:|:-----|:-------|:-------------|
| 🔴 | **TC001** | Circular Import Smuggling | Using `TYPE_CHECKING` to hide circular dependencies |
| 🔴 | **RE001** | Init Overreach | `__init__.py` handling core business logic improperly |
| 🔴 | **DI001** | Dependency Violation | Directly depending on concrete implementations |
| 🔴 | **UW001** | Transaction Tampering | Managing transactions without UoW approval |
| 🔴 | **BC001** | Data Boundary Violation | Raw data (dict/list) crossing domain boundaries |
| 🔴 | **VT001** | Signal Protocol Violation | Modifying event frequencies outside defined protocols |
| 🔴 | **AC001** | Type Deception | `Any`, `cast`, `dict` deceiving the type system |
| 🔴 | **OU001** | Naked Object Usage | Using `object` types with no domain identity |
| 🟠 | **DT001** | Time Manipulation | Freezing, accelerating, or forging system time |
| 🟠 | **SK001** | Unauthorized Skill Usage | Using skills without valid SkillID certification |
| 🟡 | **DS001** | Documentation Silence | Public interfaces lacking proper documentation |
| 🟡 | **LL001** | Over-Engineering | Functions with excessive complexity/nesting |
| 🟡 | **HC001** | Hardcode Graffiti | Carving magic numbers/strings directly into code |
| 🟡 | **HC002** | Constant Chaos | Constants scattered without organization |
| 🟡 | **PC001** | Configuration Bypass | Config params bypassing RuleProvider channels |
| 🔵 | **TP001** | Fake Testing | Tests that appear to run but verify nothing |

Severity: 🔴 Critical → 🟠 High → 🟡 Medium → 🔵 Low

<small>*Note: The Chinese version uses culturally‑rich crime metaphors.  
Join our [CulturalCodeCrimes](https://github.com/PythonCourt/pycourt/discussions/1) challenge to propose creative and humorous nicknames in your language!*</small>

---

## ⚔️ Architecture: A Composable, Automated Defense System

PythonCourt isn't a single tool—it's a **layered audit-and-adjudication system**.  
Each layer determines whether code **earns entry into the system boundary**.

### 1. ⚖️ **The Laws** (Core Engine)

* **What it is**: The rules codified from production experience  
* **What it does**: AST‑based structural analysis of Python code  
* **The question it answers**: "Does this code respect **engineering order**?"



### 2. ⚔️ **The Weapons** (Orchestration Scripts)  

* **What it is**: Configurable scripts combining PyCourt with other tools  
* **What it does**: Executes laws in sequence, enforces policies, delivers verdicts  
* **The question it answers**: "How should these laws be **applied and enforced**?"



### 3. 🎭 **The Scenes** (Workflow Contexts)

* **What it is**: Pre‑defined strategies for different development situations  
* **What it does**: Matches audit rigor to context (file‑level → project‑level)  
* **The question it answers**: "What's the **appropriate audit for this scenario**?"
---

## 🧩 Installation & Configuration: Customizing Your Supreme Court

### 1️⃣ Install PyCourt  
Published as a standalone Python package, tested on **Python 3.11–3.14**.

```bash
# Recommended: use within your project's virtual environment
pip install pycourt
```

### 2️⃣ Initialize Your Court

This creates pycourt.yaml—the single source of truth for your adjudication system.

```bash
pycourt init
```
### 3️⃣ 【Advanced but Recommended】Configure in pyproject.toml

```toml
[tool.pycourt]
civilized_paths = [
  "src/api",
  "src/domain", 
  "src/services",
  "src/infra",
]

coverage = 85  # test coverage threshold (%)
```
The philosophy: Declarative governance over reactive inspection.
You define the civilized territory; PythonCourt guards its boundaries.

---

## 🚀 Quick Start: Conduct Your First Adjudication

### 1️⃣ Choose a Weapon

Select an audit script based on your development phase:

* Dagger – Quick single‑file validation
* Saber – Module‑level structural audit
* Scepter – Cross‑domain project‑level review

👉 [View and download weapon scripts](/docs/script/official/index.md)

### 2️⃣ Launch the Audit

The script orchestrates tools in a defined sequence:

* PyCourt (architectural & rule‑based audits)
* Mypy / Pyright (type system)
* Ruff / Bandit (style & security)

All results are aggregated into a unified adjudication context.

### 3️⃣ Accept or Reject

❌ Critical violations → adjudication fails

✅ All clear → code earns eligibility for the main branch

PythonCourt doesn't fix code. It answers one question:

**Is this code worthy of existence?**

## 📜 Verdicts, Not Logs

PythonCourt doesn't output scattered inspection logs.

It produces structured, actionable, reviewable verdicts. Each violation is presented by its "judge" with clear guidance:

```yaml
# DI001 Judge's verdict
DI001:
  template: |
    🏛️ Dependency Inversion Judge (DI001): Suspicious cross‑module/component dependency detected
    📋 Violation: app.services.order_service → app.infra.db.session  
    💡 Recommendation: Prefer abstraction (interface/protocol) over concrete implementation
    🔧 Quick fix: Abstract the dependency and fulfill it through dependency injection
```
This means:

- AI can understand its own errors
- Humans can judge whether to accept the verdict
- CI can block based on severity thresholds

PythonCourt isn't concerned with "whether there are problems," but rather: Is this code worthy of crossing the system boundary?

---

## 🚫 When Not to Use PythonCourt

### ❌ These Are Poor Fits

- **"If it runs, it's good enough"**  
  When you're rapidly prototyping, writing throw‑away scripts, or building short‑lived proofs‑of‑concept,  
  PythonCourt's adjudication will feel **overly strict**.

- **You want the tool to "fix the code for you"**  
  PythonCourt doesn't generate code, perform automatic refactoring, or mask design flaws.  
  It **adjudicates**, not comforts.

- **No basic sense of engineering boundaries yet**  
  If your project doesn't distinguish between domain, interface, and infrastructure layers,  
  PythonCourt will just keep reminding you: **"This isn't civilized territory yet."**

- **Treating AI as an outsourcer, not a collaborator**  
  AI writes code, but humans own the structure, boundaries, and long‑term quality.  
  If you expect AI to make engineering decisions independently, this system will seem superfluous.


### ✅ These Are Excellent Fits

* You're using AI to write **production‑grade code**  
* You're starting to feel the "repair loop" and structural decay  
* You're willing to introduce explicit **laws, boundaries, and adjudication processes**  
* You accept that **some code should be refused existence**

---

**PythonCourt isn't a productivity tool. It's an engineering stance.**

Join the discussion 👉 [The Meaning and Methods of Architecture‑First Development](https://github.com/orgs/PythonCourt/discussions/2)



## 🔧 Contributing & Governance

PythonCourt isn't just a tool—it's a **methodology about code order**.  
If you want to help shape rule design, audit algorithms, or cross‑platform tooling:

### 1️⃣ Modify PyCourt Itself (Engine Contributions)
```bash
git clone https://github.com/PythonCourt/pycourt.git
cd pycourt
poetry install

# Run audits directly within the repository
poetry run pycourt scope pycourt
poetry run ./qa.sh
```

2️⃣ Use PyCourt Locally in Your Own Project

```toml
# In your project's pyproject.toml
[tool.poetry.dependencies]
pycourt = { path = "../PyCourt", develop = true }
```
3️⃣ Use PyCourt in Your Project (Standard Workflow)

```bash
poetry install          # Set up your environment
poetry run pycourt init # Generate configuration
poetry run pycourt scope . # Audit your project
```
For detailed contribution guidelines, architecture decisions, and governance model:
👉 Read the Contribution Guide

This is a collective search for sustainable order in AI‑assisted development.


---

<br><br>

<div align="center">

PythonCourt doesn't guarantee good code.<br>
It only tries to make bad code **harder to stay**.  

If you're also building long‑lived systems with AI,<br>
consider this an **ongoing engineering experiment**.


<br>

[![GitHub stars](https://img.shields.io/github/stars/PythonCourt/pycourt?style=social)](https://github.com/PythonCourt/pycourt)
[![GitHub forks](https://img.shields.io/github/forks/PythonCourt/pycourt?style=social)](https://github.com/PythonCourt/pycourt)
[![GitHub issues](https://img.shields.io/github/issues/PythonCourt/pycourt)](https://github.com/PythonCourt/pycourt/issues)

<br>

**Make AI Write Production‑Grade Code**

</div>