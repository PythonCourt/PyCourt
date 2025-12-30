#!/bin/bash

# ==============================================================================
# 🏛️ TimeOS Imperial Cleanup - V1.0
#
# A safe and powerful tool to purge all temporary caches, build artifacts,
# and runtime-generated data. Use this to restore your project directory
# to a pristine, "freshly cloned" state without losing your source code.
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

# --- DANGEROUS OPERATION - USER CONFIRMATION REQUIRED ---
print_header "清除运行时数据（需要确认！)"
DATA_DIR="$PROJECT_ROOT/data"
echo "这将永久删除本地运行时数据目录:"
echo "  $DATA_DIR"
echo "包括您的向量数据库、日志和其他运行时资产."
echo "This is irreversible."
read -p "输入'YES'以确认删除 '$DATA_DIR': " CONFIRM

if [ "$CONFIRM" = "YES" ]; then
    rm -rf "$DATA_DIR"
    echo "✅ 运行时数据目录已被清除: $DATA_DIR"
else
    echo "跳过运行时数据目录的删除: $DATA_DIR"
fi

echo -e "\n${GREEN}🎉 大帝国清洁行动已经完成！你的领地再次变得一尘不染！${NC}"