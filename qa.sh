#!/bin/bash

# ==============================================================================
# 🏛️ 皇帝节仗
# 定位：对整个项目进行全面审计
# 用法: ./qa.sh
# 场景：跨域模块和组件综合验收以及在代码准备推送前进行全面审计。
# 要求：项目必须通过所有静态审计与测试，且测试覆盖率符合预设阈值。
# 说明：此脚适用于大多数常见场景，可根据实际需要自由搭配、修改和扩展。
# ==============================================================================
# 1. 引入“职责分离”，将“读取配置”与“执行审计”彻底解耦。
# 2. 全面覆盖静态审计与动态测试，确保代码质量万无一失。
# 3. 强化配置解析的健壮性，使用专门的Python脚本和jq进行安全解析。
# 4. 通过 PythonCourt 最高法院 (TP001/TP002/TP003) 审查测试纯净度与真实性。
# 5. 重构作战序列，流程如史诗般清晰，意图自明。
# ==============================================================================

# ===============
# 准备开始：环境配置
# ===============

# ---------------------------------------------------
# --- 1. 帝国军法：零容忍，立即终止 ---
# ---------------------------------------------------
set -euo pipefail

# ---------------------------------------------------
# --- 2. 核心：以当前位置为帝国中心 ---
# 确保所有子进程（包括 Python 脚本）都知道项目根目录在哪里
# ---------------------------------------------------
export PYTHONPATH=$(pwd)

# ---------------------------------------------------
# --- 3. PyCourt 语言切换：默认为中文，可选`-en` ---
# ---------------------------------------------------
export PYCOURT_LANG="${PYCOURT_LANG:-zh}"

# ---------------------------------------------------
# --- 4. 颜色与辅助函数：本脚本内联实现 ---
# ---------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

print_chapter_header() {
    # 人类模式下输出章节标题；AI 模式下默认关闭以减少噪音
    if [[ "${PYCOURT_UI_MODE:-human}" != "ai" ]]; then
        echo -e "\n${BLUE}================== $1 ==================${NC}"
    fi
}
print_sub_header() {
    # 人类模式下输出小节标题；AI 模式下默认关闭以减少噪音
    if [[ "${PYCOURT_UI_MODE:-human}" != "ai" ]]; then
        echo -e "\n${YELLOW}--- $1 ---${NC}"
    fi
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

# ---------------------------------------------------
# --- 5. 模式配置参数 ---
# ---------------------------------------------------
# 是否启用“特种部队演习”（E2E 测试），默认 0：关闭。
# 可通过在命令行添加 --with-e2e 参数启用。
RUN_E2E=0
if [[ " $@ " =~ " --with-e2e " ]]; then
  RUN_E2E=1
fi

# 是否启用 AI 模式（紧凑文案 + 抑制叙事输出）。
# 通过 -a 或 --ai 开启，环境变量优先级更高（若外部已设置则保留外部值）。
for arg in "$@"; do
  case "$arg" in
    -a|--ai)
      export PYCOURT_AUDIENCE=${PYCOURT_AUDIENCE:-ai}
      export PYCOURT_UI_MODE=${PYCOURT_UI_MODE:-ai}
      # 若当前语言为中文系 (zh*)，在 AI 模式下自动切换到英文文案，
      # 若用户已显式设为 en/其他语言，则尊重用户选择。
      if [[ "${PYCOURT_LANG:-}" == zh* ]]; then
        export PYCOURT_LANG=en
      fi
      ;;
  esac
done

# 是否启用“测试阶段”（第三/四章），默认 0：关闭。
# 需要时可通过修改为 `ENABLE_TEST_PHASE:-1` 打开统一测试能力。
ENABLE_TEST_PHASE=${ENABLE_TEST_PHASE:-0}

# ---------------------------------------------------
# --- 6. 读取审计参数 ---
# 从 pyproject.toml 中读取 [tool.pycourt] 配置
# ---------------------------------------------------
CONFIG_JSON=$(poetry run python -m pycourt.config.read_toml --for-ci)
FAIL_UNDER=$(echo "$CONFIG_JSON" | jq -r '.fail_under')
CIVILIZED_PATHS=($(echo "$CONFIG_JSON" | jq -r '.civilized_paths[]'))
COVERAGE_PATHS=($(echo "$CONFIG_JSON" | jq -r '.coverage_paths[]'))

print_sub_header "覆盖率阈值: ${FAIL_UNDER}%"
print_sub_header "帝国总疆域: ${CIVILIZED_PATHS[*]}"

# ---------------------------------------------------
# --- 准备就绪 ---
# 根据 coverage_paths 生成 pytest 覆盖率参数列表
# ---------------------------------------------------
COV_ARGS=()
for path in "${COVERAGE_PATHS[@]}"; do
    COV_ARGS+=("--cov=$path")
done
print_sub_header "军备清单（覆盖率源）已生成"
print_chapter_header "皇帝节仗 - 准备就绪"

# ==============================================================================
# 第一章：调用军刀执行静态大巡查
# ==============================================================================
print_chapter_header "第一章：静态大巡查"

# 审计范围：pyproject 的 civilized_paths 的内容
CIV_SOURCE_PATHS=("${CIVILIZED_PATHS[@]}")

for SCOPE in "${CIV_SOURCE_PATHS[@]}"; do
  print_sub_header "派遣军刀对【${SCOPE}】进行静态审计..."
  ./qas.sh "${SCOPE}" || { print_error "❌军刀在 ${SCOPE} 静态审计失败"; exit 1; }
done

print_success "所有疆域静态审查全面通过！"

# ==============================================================================
# 第二章：帝国三军联合作战大演习
# 仅对审计目标（civilized_paths）关联的 tests 目录展开审计与测试。
# ==============================================================================
if [ "$ENABLE_TEST_PHASE" -eq 1 ]; then
  print_chapter_header "第二章：帝国军团联合作战大演习"

# ---------------------------------------------------
# 智能推导测试目录
# ---------------------------------------------------
  if [ ! -d "tests" ]; then
    print_warning "未发现 tests 目录，跳过联合测试大演习。"
  else
    # 构建与 civilized_paths 相关联的测试目录列表。
    # 策略：
    #   对每个 SCOPE in CIV_SOURCE_PATHS：
    #     1) 优先尝试严格镜像：tests/SCOPE
    #     2) 其次尝试顶层镜像：tests/<top-level-of-SCOPE>
    #     3) 若仍未命中，则退化为全局 tests/
    TEST_DIRS=()

    add_test_dir() {
      local d="$1"
      # 简单去重，避免对同一 tests 目录重复执行 TP/静态审计/pytest。
      for existing in "${TEST_DIRS[@]}"; do
        if [ "$existing" = "$d" ]; then
          return
        fi
      done
      TEST_DIRS+=("$d")
    }

    for SCOPE in "${CIV_SOURCE_PATHS[@]}"; do
      # 1) 严格镜像
      candidate="tests/${SCOPE}"
      if [ -d "$candidate" ]; then
        add_test_dir "$candidate"
        continue
      fi

      # 2) 顶层目录镜像
      top_level="${SCOPE%%/*}"
      candidate="tests/${top_level}"
      if [ -d "$candidate" ]; then
        add_test_dir "$candidate"
      else
        # 3) 退化为全局 tests/
        add_test_dir "tests"
      fi
    done

    if [ "${#TEST_DIRS[@]}" -eq 0 ]; then
      print_warning "未找到与 civilized_paths 匹配的测试目录，跳过联合测试大演习。"
    else
      for TDIR in "${TEST_DIRS[@]}"; do
        print_sub_header "测试战区镜像: $TDIR"

      # ---------------------------------------------
      # 2.1 TP 系列军规审查（仅针对匹配到的测试战区）
      # ---------------------------------------------
        print_sub_header "2.1 帝国戎卫兵团军规审查 (TP 系列)"
        poetry run python pycourt/judge.py "$TDIR" --select TP001,TP002,TP003 \
          || { print_error "❌ 测试战区 ${TDIR} 发现违反军规！"; exit 1; }
        print_success "✅ 测试战区【${TDIR}】纯净度通过！"

      # ---------------------------------------------
      # 2.2 测试战区静态审计（复用军刀的静态能力）
      # ---------------------------------------------
        print_sub_header "2.2 派遣军刀对测试战区执行静态审计"
        ./qas.sh "$TDIR" || { print_error "❌ 军刀在测试战区 ${TDIR} 静态审计失败"; exit 1; }
        print_success "✅ 测试战区【${TDIR}】静态审计通过！"
      done

      # ---------------------------------------------
      # 2.3 常规军总决战 (单元 + 集成)
      # ---------------------------------------------
      print_sub_header "2.3 常规军总决战 (单元 + 集成)"
      BATTLE_MARKER="unit or integration"

      # 覆盖率阈值完全由开发者在 [tool.pycourt].coverage 中定义，并统一用于
      # pytest 的 --cov-fail-under 参数：
      # - FAIL_UNDER = 0  表示“只要测试运行通过即可”，不对覆盖率比例做约束；
      # - FAIL_UNDER > 0  表示要求覆盖率至少达到该百分比，否则视为失败。
      PYTEST_ARGS=("${COV_ARGS[@]}" --cov-report=term-missing --cov-report=html:htmlcov)
      if [ "$FAIL_UNDER" -le 0 ]; then
        print_warning "当前覆盖率阈值为 ${FAIL_UNDER}%，仅要求测试运行通过，不对覆盖率做约束。"
      fi
      PYTEST_ARGS+=(--cov-fail-under="$FAIL_UNDER")

      poetry run pytest -m "$BATTLE_MARKER" \
        "${PYTEST_ARGS[@]}" \
        "${TEST_DIRS[@]}" || { print_error "❌ 常规军总决战失败！"; exit 1; }
      print_success "覆盖率裁决通过，常规军总决战胜利！"

      # ---------------------------------------------
      # 2.4 特种部队演习 (E2E)
      # ---------------------------------------------
      if [ "$RUN_E2E" -eq 1 ]; then
        print_sub_header "2.4 特种部队演习 (E2E)"
        # E2E 测试不计入覆盖率，只做端到端验收。
        poetry run pytest -m "e2e" --no-cov "${TEST_DIRS[@]}" \
          || { print_error "E2E 演习失败"; exit 1; }
        print_success "E2E 演习成功！"
      fi
    fi
  fi
fi


# ==============================================================================
# 终章：胜利宣告
# ==============================================================================
print_chapter_header "终章：胜利宣言"
print_success "帝国统一审计全面通过！代码值得信赖."
print_sub_header "可以放心推送了！"
