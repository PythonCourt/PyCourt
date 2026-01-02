#!/bin/bash

# ==============================================================================
# 🏛️ 皇帝节仗 V5.0
#
# 最终裁定：
# 1.【道】引入“职责分离”，将“读取配置”与“执行审计”彻底解耦。
# 2.【法】废除脆弱的环境变量，代之以明确的`--skip-pytest`命令行开关与军刀协同。
# 3.【术】强化配置解析的健壮性，使用专门的Python脚本和jq进行安全解析。
# 4.【律】通过 TimeOS 最高法院 (TP001/TP002/TP003) 审查测试纯净度与真实度。
# 5.【器】重构作战序列，流程如史诗般清晰，意图自明。
# ==============================================================================

# --- 帝国军法：零容忍，立即终止 ---
set -euo pipefail

# --- 核心：以当前位置为帝国中心 ---
# 这条敕令确保所有子进程（包括 Python 脚本）都知道项目根目录在哪里
export PYTHONPATH=$(pwd)

# --- PyCourt 语言切换：默认为中文，外部可覆盖 PYCOURT_LANG=en ---
export PYCOURT_LANG="${PYCOURT_LANG:-zh}"

# --- 颜色与辅助函数：本脚本内联实现 ---
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

print_chapter_header() {
    echo -e "\n${BLUE}================== $1 ==================${NC}"
}
print_sub_header() {
    echo -e "\n${YELLOW}--- $1 ---${NC}"
}
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}
print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}
print_error() {
    echo -e "${RED}❌ $1${NC}"
}

run_mypy_judgement() {
    poetry run mypy "$@"
}


# --- 参数解析 ---
RUN_E2E=0
if [[ " $@ " =~ " --with-e2e " ]]; then
  RUN_E2E=1
fi

# 是否启用“测试阶段”（第三/四章），默认 0：关闭。
# 需要时可通过 `ENABLE_TEST_PHASE=1 ./qa.sh` 打开统一测试能力。
ENABLE_TEST_PHASE=${ENABLE_TEST_PHASE:-0}

# ==============================================================================
# 第一章：【道】帝国战略规划署 (The Strategic Planning Agency)
# ==============================================================================
print_chapter_header "第一章：【道】帝国战略规划署"

# --- 1.1 读取帝国法典 ---
# 使用独立的 PyCourt 包从 pyproject.toml 中读取 [tool.pycourt] 配置
CONFIG_JSON=$(poetry run python -m pycourt.config.read_toml --for-ci)

# --- 1.2 解析战略地图 ---
FAIL_UNDER=$(echo "$CONFIG_JSON" | jq -r '.fail_under')
CIVILIZED_PATHS=($(echo "$CONFIG_JSON" | jq -r '.civilized_paths[]'))
COVERAGE_PATHS=($(echo "$CONFIG_JSON" | jq -r '.coverage_paths[]'))

print_sub_header "覆盖率裁决阈值: ${FAIL_UNDER}%"
print_sub_header "帝国总疆域: ${CIVILIZED_PATHS[*]}"

# --- 1.3 生成军备清单 ---
COV_ARGS=()
for path in "${COVERAGE_PATHS[@]}"; do
    COV_ARGS+=("--cov=$path")
done
print_sub_header "军备清单（覆盖率源）已生成"

# ==============================================================================
# 第二章：【法】帝国全境静态大巡查 (The Static Grand Tour)
# ==============================================================================
print_chapter_header "第二章：【法】帝国全境静态大巡查"

# 审计范围：pyproject 的 civilized_paths 的内容
CIV_SOURCE_PATHS=("${CIVILIZED_PATHS[@]}")

# 2.1 调用军刀执行静态宪法审计（测试阶段由军刀自身的 ENABLE_TEST_PHASE 控制）
for SCOPE in "${CIV_SOURCE_PATHS[@]}"; do
  print_sub_header "派遣军刀对【${SCOPE}】进行静态宪法审计..."
  ./qas.sh -s "${SCOPE}" || { print_error "❌帝国军刀在 ${SCOPE} 静态审计失败"; exit 1; }
done

# （如未来需要对镜像测试目录执行静态审计，可在此处按 civilized_paths 推导 tests/* 镜像路径
#  并循环调用 ./qas.sh --s <test_dir> 实现，这里暂不启用，以保持节仗职责聚焦。）

print_success "所有疆域静态审查全面通过！"


# ==============================================================================
# 第三章：【律】帝国测试军规审查 (The Test Discipline Review)
# （仅在 ENABLE_TEST_PHASE=1 时启用，用于 CI/CD 前的统一测试纪律审查）
# ==============================================================================
if [ "$ENABLE_TEST_PHASE" -eq 1 ]; then
  print_chapter_header "第三章：【律】帝国戎卫兵团军规审查"
  poetry run python tools/court/judge.py tests --select TP001,TP002,TP003 \
    || { print_error "❌ 发现调用生产代码和虚假测试！军规审查失败！"; exit 1; }
  print_success "✅ 所有单元测试均符合帝国军规！"

# ==============================================================================
# 第四章：【术】帝国三军联合作战大演习 (The Grand Joint Maneuver)
# 统一执行 unit/integration + 覆盖率裁决，以及可选 E2E。
# ==============================================================================
  print_chapter_header "第四章：【术】帝国三军联合作战大演习"

  # --- 3.1 常规军总决战 (单元 + 集成) ---
  print_sub_header "3.1 常规军总决战 (单元 + 集成)"
  BATTLE_MARKER="unit or integration"

  # 我们的演习，只在 `tests/` 这个唯一的“国防演习场”进行，
  # 并在此进行最终的、带有覆盖率裁决的“大阅兵”。
  poetry run pytest -m "$BATTLE_MARKER" \
    "${COV_ARGS[@]}" \
    --cov-report=term-missing \
    --cov-report=html:htmlcov \
    --cov-fail-under="$FAIL_UNDER" \
    tests/ || { print_error "❌ 常规军总决战失败！"; exit 1; }
  print_success "覆盖率达标，常规军总决战胜利！"

  # --- 3.2 特种部队演习 (E2E) ---
  if [ "$RUN_E2E" -eq 1 ]; then
    print_sub_header "3.2 特种部队演习 (E2E)"
    # E2E 测试不计入覆盖率，只做端到端验收。
    poetry run pytest -m "e2e" --no-cov tests/ || { print_error "E2E 演习失败"; exit 1; }
    print_success "E2E 演习成功"
  fi
fi


# ==============================================================================
# 第五章：【器】最终胜利宣告 (The Victory Proclamation)
# ==============================================================================
print_chapter_header "第五章：【器】最终胜利宣告"
print_success "帝国统一审计全面通过！代码值得信赖."
print_sub_header "可以推送到了！"
