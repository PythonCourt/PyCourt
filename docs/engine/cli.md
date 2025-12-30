# CLI 使用

PyCourt 提供三层审计入口：

- `pycourt file path.py` — 针对单个文件的极致审计；
- `pycourt scope path/` — 针对目录/模块战区的范围审计；
- `pycourt project` — 基于配置的整仓库审计（结合 `pycourt.yaml` / `[tool.pycourt]`）。

后续可以在这里写：

- 安装方式；
- 每个子命令的参数说明与示例输出；
- 与三把武器脚本（`qaf.sh / qas.sh / qa.sh`）之间的关系。
