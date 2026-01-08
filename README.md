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
[![Docs (zh)](https://img.shields.io/badge/Docs-zh-green)](docs/guide/started/index.md)
[![中文说明](https://img.shields.io/badge/README-zh-orange)](docs/zh/README_zh.md)

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

## ⚖️ Law catalogue (technical overview)

PyCourt ships a growing set of **laws** (`TC001`, `DI001`, …).  
They are not syntax errors; they are **structural smells** that repeatedly caused real teams pain.

They mainly look at:

- **Architecture boundaries** – which modules are allowed to depend on which
- **Dependency direction** – avoiding hidden coupling and “inverted” imports
- **Type discipline** – where `Any` / `dict` / `object` are used as escape hatches
- **Configuration hygiene** – whether parameters flow through a single, traceable source
- **Test quality** – whether tests are actually asserting behaviour

Below is the technical view of the current core laws.

| Level | Law | Crime | Description |
|-------|-----|-------|-------------|
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

<small>Severity: 🔴 Critical → 🟠 High → 🟡 Medium → 🔵 Low</small>

> Severity is about **blocking strategy**, not moral judgment:  
> 🔴 blocking · 🟠 high‑risk · 🟡 acceptable but suspicious · 🔵 informational.

In the English README, we keep the laws **technical and precise**.  
Humorous nicknames are delegated to the community (see “Law nicknaming” below).

---

## 🏛 Architecture: engine, weapons, workflow

PyCourt is not a single binary. It is a **stack of cooperating layers**:

### 1. PyCourt engine (core)

- **Input**: Python files / packages
- **Mechanism**: AST + rule definitions (`laws`)
- **Output**: structured violations keyed by law ID (e.g. `DI001`, `HC001`)

Think of it as a specialized linter for **architecture and discipline**, not formatting.

---

### 2. Weapons (orchestration layer)

The “weapons” are shell / CLI scripts that orchestrate:

- PyCourt (architecture & rule audit)
- Type checkers (Mypy / Pyright)
- Style & security tools (Ruff / Bandit)
- Tests and coverage (via your preferred test runner)

They turn individual tools into **repeatable workflows**, such as:

- “surgical” audit of a single AI‑generated file
- module‑level refactor safety checks
- full‑project gate in CI/CD

See `docs/script/official/index.md` for the current set:

- `qaf` – single‑file dagger
- `qas` – module / directory sabre
- `qa`  – full‑project sceptre for CI

---

### 3. Workflow layer

On top of weapons, each team can define:

- when to run which weapon (on save, pre‑commit, nightly, CI)
- which laws are **hard blockers** vs **soft warnings**
- how to combine static checks, tests, and coverage thresholds

PyCourt itself only answers:

> “Given these rules, does this code deserve to exist in this boundary?”

How you plug that answer into your delivery process is up to you.

---

## 🧩 Installation & configuration

### 1. Install the CLI

PyCourt is published as a regular Python package, currently tested on **Python 3.11–3.14**.

Recommended:

```bash
pip install pycourt
```
2. Initialize pycourt.yaml in your project

From your project root:
```bash
cd /path/to/your-project
pycourt init
```
This will:

1. Detect the project root (via pyproject.toml, VCS, etc.).
2. Generate a commented pycourt.yaml template if it does not exist.

pycourt.yaml is where you declare file‑level exemptions per law, e.g.:
```yaml
exemptions:
  HC001:
    files:
      - "tests/**"        # tests often tolerate more hard‑coded literals
      - "migrations/**"   # database migrations are usually not “clean” code
  LL001:
    files:
      - "**/tests/**"     # long helper functions only used in tests
```
The matching uses fnmatch‑style globs (foo/**, **/tests/**, etc.).

3. (Optional but recommended) Declare civilized paths

You can also declare the “civilized territory” of your project in pyproject.toml:
```toml
[tool.pycourt]
civilized_paths = [
  "src/api",
  "src/domain",
  "src/services",
  "src/infra",
]

coverage = 85  # coverage threshold (%) consumed by higher-level weapons
```
•  PyCourt (and especially the weapons) can use this to limit audits to code you consider “civilized”.
•  Unlisted paths can be treated as legacy / experiments / one‑off scripts.



🚀 Quick start: your first judgment

With pycourt installed and pycourt.yaml initialized:

1. Project‑wide preview
```bash
   pycourt scope .
```
 This will:

•  recursively scan Python files under the current directory
•  apply file‑level exemptions from pycourt.yaml
•  report violations grouped by law ID
2. Single‑file audit (great with AI‑generated code)
```bash
   pycourt file path/to/foo.py
```
3. Wire into CI/CD

   For example, only enforce a subset of strict laws:
```bash
   pycourt scope . --select HC001,HC003,DI001,TC001
```
PyCourt does not auto‑fix your code.  
It simply makes it harder for questionable code to slip into your main branch unnoticed.

📜 Judgment reports, not raw logs

PyCourt does not just dump tool output.  
It produces a structured, reviewable judgment keyed by law and location.

A (simplified) example for DI001:
```yaml
DI001:
  template: |
    🏛️ Dependency Inversion Officer (DI001): detected a suspicious cross-component import.
    📋 Offending import: app.services.order_service -> app.infra.db.session
    💡 Recommendation: depend on an abstract interface instead of a concrete implementation.
    🔧 Quick fix: extract an interface and inject the implementation via configuration.
```

This makes it easier for:

•  AI agents to understand and fix their own mistakes
•  humans to decide whether to accept or appeal the judgment
•  CI to block based on severity or specific laws

PyCourt cares less about “is there any issue at all”  
and more about “does this code meet the standards of this boundary”.



🚫 When not to use PyCourt

PyCourt is not for everyone, and is intentionally overkill for some workflows.

Poor fit

•  Prototype‑only / throwaway code

  If your goal is just to validate an idea with a short‑lived script,  
  PyCourt’s structure and discipline will feel like unnecessary friction.

•  “Fix my code for me” expectations

  PyCourt does not generate code, auto‑refactor, or hide design problems.  
  It judges; it does not comfort.

•  No basic architecture in place

  If your project does not yet distinguish domains, interfaces, and infrastructure,  
  PyCourt will mostly keep telling you “this is not a civilized territory yet”.

•  Treating AI as outsourced engineering

  AI can write code, but humans are still responsible for structure, boundaries, and longevity.  
  If you expect AI to make architectural decisions on its own, this system will feel redundant.

Good fit

•  You are using AI to write production‑grade code.
•  You are starting to feel “fixing loops” and structural decay.
•  You are willing to introduce laws, boundaries, and explicit judgment into your process.
•  You accept the idea that some code should be rejected from the system.

PyCourt is not a productivity tool.  
It is an engineering stance.



🔧 Contributing & local development

PyCourt is both a tool and an ongoing experiment in code governance.  
If you want to shape the laws, algorithms, or tooling, you are welcome.

1. Hacking on PyCourt itself

```bash
git clone https://github.com/PythonCourt/pycourt.git
cd pycourt

# Install dev dependencies
poetry install

# Run the CLI from source
poetry run pycourt --help
poetry run pycourt scope pycourt

# Or use the official weapons from this repo
poetry run ./qaf.sh               # single-file audit
poetry run ./qas.sh -s pycourt -n # non-blocking self-audit of the pycourt package
poetry run ./qa.sh                # full-project gate driven by pyproject.toml
```

No manual PYTHONPATH tweaking is required when using Poetry.

2. Depending on local PyCourt from your own project

In your own project’s pyproject.toml:
```toml
[tool.poetry.dependencies]
pycourt = { path = "../PyCourt", develop = true }
```
Then, from that project:
```bash
poetry install
poetry run pycourt scope .
```
Any changes you make in ../PyCourt/pycourt/ will be visible immediately.

For more community‑oriented contribution ideas, see:

•  docs/guide/community/contribute.md

🌍 Law nicknaming & cultural metaphors

In Chinese, many laws have playful nicknames (e.g. metaphors from history or idioms).  
Instead of hard‑coding those into the English spec, we treat nicknaming as a community activity.

•  The formal spec of each law lives in:
◦  its ID (DI001, HC001, …)
◦  its English technical description
◦  its detection logic and config
•  The fun parts – nicknames, stories, cultural metaphors – belong to the community.

If your language or culture has a vivid way to describe a particular code smell  
(a proverb, a historical reference, a meme), you are invited to:

•  propose a nickname for a law in your language
•  add a one‑paragraph story or explanation
•  discuss whether it matches the behaviour of that law

👉 Join the naming & translation discussion here:  
<https://github.com/orgs/PythonCourt/discussions/1>



<div align="center" markdown="1">
<br><br>

PythonCourt cannot guarantee good code.<br>
It only tries to make it harder for bad code to stay.<br>
If you are building long‑lived systems with AI as a collaborator,<br>
you are welcome to treat this as an ongoing engineering experiment.

<br>
<img src="https://img.shields.io/github/stars/pythoncourt/pycourt?style=social" alt="GitHub stars"> <img src="https://img.shields.io/github/forks/pythoncourt/pycourt?style=social" alt="GitHub forks"> <img src="https://img.shields.io/github/issues/pythoncourt/pycourt" alt="GitHub issues">
<br><br>
<p><strong>Let AI write code. Let the court decide what gets in.</strong></p>
</div>