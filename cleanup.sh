#!/bin/bash

# ==============================================================================
# 🏛️ TimeOS Imperial Cleanup - V1.0
#
# 一个安全且强大的工具，用于清除所有临时缓存、构建工件，
# 以及运行时生成数据。使用此工具可以将您的项目目录
# 恢复到原始的、“全新克隆”状态，而不会丢失您的源代码。
# ==============================================================================

set -euo pipefail

# --- Robust project root detection ---
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
cd "$PROJECT_ROOT"

# --- Colors & Helpers ---
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
print_header() { echo -e "\n${YELLOW}--- $1 ---${NC}"; }

echo "🧹 启动大扫除..."

print_header "清理工具缓存"
rm -rf .mypy_cache
rm -rf .pytest_cache
rm -rf .ruff_cache
echo "✅ 工具缓存已被清除."

print_header "清除Python字节码"
find . -type f -name "*.py[co]" -delete
find . -type d -name "__pycache__" -delete
echo "✅ Python字节码已被清除."

print_header "清除测试与覆盖率报告"
rm -rf htmlcov
rm -f .coverage
echo "✅ 测试和覆盖率报告已被清除."

print_header "清除 Jupyter Notebook 检查点"
rm -rf .ipynb_checkpoints
echo "✅ Jupyter检查点已被清除."

print_header "清除历史构建"
rm -rf dist
echo "✅ 历史构建已被清除."

# --- DANGEROUS OPERATION - USER CONFIRMATION REQUIRED ---
print_header "清除运行时数据（需要确认！)"
DATA_DIR="$PROJECT_ROOT/data"
echo "这将永久删除本地运行时数据目录:"
echo "  $DATA_DIR"
echo "包括您的向量数据库、日志和其他运行时资产."
echo "这是不可逆的."
read -p "输入'YES'以确认删除 '$DATA_DIR': " CONFIRM

if [ "$CONFIRM" = "YES" ]; then
    rm -rf "$DATA_DIR"
    echo "✅ 运行时数据目录已被清除: $DATA_DIR"
else
    echo "跳过运行时数据目录的删除: $DATA_DIR"
fi

echo -e "\n${GREEN}🎉 帝国大清洁行动已经完成！你的领地一尘不染！${NC}"