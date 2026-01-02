#!/bin/bash

# ==============================================================================
# 🗡️ 帝国军刀 V4.0
# 勘察：使用非阻断模式对目标战区进行侦察 命令：./qas.sh -s <directory> -n
# 审计：使用阻断模式对目标战区进行审计 命令：./qas.sh -s <directory>
# 测试：可选开启 ENABLE_TEST_PHASE=1 时，自动寻找可用测试并执行静态审计 + pytest
# 覆盖率：仅打印警告，不中断执行
# ==============================================================================

# --- 帝国军法：零容忍，立即终止 ---
set -euo pipefail

# --- 核心：以当前位置为帝国中心 ---
export PYTHONPATH=$(pwd)

# --- PyCourt 语言切换：默认为中文，外部可覆盖 PYCOURT_LANG=en ---
export PYCOURT_LANG="${PYCOURT_LANG:-zh}"

# --- 颜色与辅助函数统一由帝国武备库提供（内联实现） ---
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

check_tool() {
    local cmd="$1"
    local desc="$2"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        print_warning "缺少外部工具: $cmd ($desc)，将跳过对应审计步骤。"
        return 1
    fi
    return 0
}

# --- 参数解析 ---
AUDIT_DIR=""
AUDIT_NON_BLOCKING=0
# 是否启用“国防演习”（测试阶段），默认 0：关闭；设置为 1 即可启用全部测试逻辑。
ENABLE_TEST_PHASE=${ENABLE_TEST_PHASE:-0}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -s)
      AUDIT_DIR="$2"
      shift 2
      ;;
    -n)
      AUDIT_NON_BLOCKING=1
      shift
      ;;
    *)
      echo "❌ 未知参数: $1" >&2
      exit 1
      ;;
  esac
done

if [ -z "$AUDIT_DIR" ]; then
    echo "❌ 用法错误: 必须提供 -s <directory>" >&2
    exit 1
fi

# --- 辅助函数定义 ---
run_or_warn() {
    "$@" || { [ "$AUDIT_NON_BLOCKING" = "0" ] && print_error "命令执行失败" && exit 1 || print_warning "命令执行发现问题"; }
}

run_judges() {
    # 覆盖占位实现：传入 (target, codes) 以便重用在目录或单文件场景。
    # 使用独立 PyCourt 包提供的 CLI，对目录或单文件目标执行 scope 审计。
    local target="$1"
    local codes="$2"
    run_or_warn poetry run pycourt scope "$target" --select "$codes"
}

run_static_audit_on_target() {
    local audit_target="$1"
    print_chapter_header "对【${audit_target}】进行静态审计"

    # 第一章：【道】架构与核心纪律（顺序同 qaf.sh，先架构 → 再事务 → 再类型）
    print_sub_header "0.1 循环依赖审查 (TC001)"
    run_judges "${audit_target}" "TC001"

    print_sub_header "0.2 门面纪律审查 (__init__.py 前台规约, RE001/RE002/RE003)"
    run_judges "${audit_target}" "RE001,RE002,RE003"

    print_sub_header "0.3 依赖倒置审查 (DI001)"
    run_judges "${audit_target}" "DI001"

    print_sub_header "0.4 仓库事务规范审查 (UW001, UW002, UW003, UW004)"
    run_judges "${audit_target}" "UW001,UW002,UW003,UW004"

    print_sub_header "0.5 边界管制审查 (BC001)"
    run_judges "${audit_target}" "BC001"

    print_sub_header "0.6 Vector Trigger 契约审查 (VT001)"
    run_judges "${audit_target}" "VT001"

    print_sub_header "0.7 类型偷懒审查 (Any, Cast, Object, OU001)"
    run_judges "${audit_target}" "AC001,AC002,AC003,OU001"

    print_sub_header "0.8 时间法官审查 (datetime.now/utcnow, DT001)"
    run_judges "${audit_target}" "DT001"

    print_sub_header "0.9 技能使用审查 (SK001)"
    run_judges "${audit_target}" "SK001"

    # 第二章：【法】类型检查（Pyright / Mypy）
    print_sub_header "1.0 Mypy 审查"
    if check_tool "mypy" "Python 静态类型检查器 (Mypy)"; then
        run_or_warn run_mypy_judgement "${audit_target}"
    else
        print_warning "跳过 Mypy 审查。"
    fi

    print_sub_header "1.1 Pyright 审查"
    if check_tool "pyright" "Python 静态类型检查器 (Pyright)"; then
        run_or_warn poetry run pyright "${audit_target}"
    else
        print_warning "跳过 Pyright 审查。"
    fi

    # 第三章：【术】安全与文法（Bandit / DS / LL / HC / PC）
    print_sub_header "2.0 Bandit 审查"
    if check_tool "bandit" "安全审计工具 (Bandit)"; then
        if [[ "${audit_target}" == tests* ]]; then
            run_or_warn poetry run bandit -q -r "${audit_target}" -s B101
        else
            run_or_warn poetry run bandit -q -r "${audit_target}"
        fi
    else
        print_warning "跳过 Bandit 审查。"
    fi

    print_sub_header "2.1 文法秩序审查 (DS, LL, HC, PC)"
    run_judges "${audit_target}" "DS001,DS002,LL001,LL002,HC001,HC002,HC003,HC004,HC005,PC001,PC002"

    # 第四章：【器】格式与落地形态（Ruff fix + format）
    print_sub_header "3.0 Ruff 审查与格式化"
    if check_tool "ruff" "Python Lint & Format 工具 (Ruff)"; then
        run_or_warn poetry run ruff check "${audit_target}" --fix
        poetry run ruff format "${audit_target}"
    else
        print_warning "跳过 Ruff 审查与格式化。"
    fi

    print_success "✅ 战区【${audit_target}】静态审计通过！"
}

# ==============================================================================
# --- 戎卫兵团：单元测试国防演习 ---
# ==============================================================================

print_chapter_header "🗡️ 帝国军刀 - 作战准备"
print_sub_header "审计目标: $AUDIT_DIR"
if [ "$AUDIT_NON_BLOCKING" = "1" ]; then print_warning "模式: 非阻断式侦察"; fi
if [ "$ENABLE_TEST_PHASE" -eq 1 ]; then print_warning "模式: 启用国防演习阶段"; fi

# --- 阶段一：战区静态总审查 ---
print_chapter_header "第一阶段：战区静态总审查"
run_static_audit_on_target "$AUDIT_DIR"

# --- 阶段二：帝国国防演习（可选，通过 ENABLE_TEST_PHASE 控制） ---
if [ "$ENABLE_TEST_PHASE" -eq 1 ]; then
  print_chapter_header "第二阶段：帝国国防演习"

  if [[ "$AUDIT_DIR" == tests* ]]; then
      print_warning "审计目标为测试战区，跳过国防演习。"
  elif [ ! -d "tests" ]; then
      print_warning "未发现‘国防演习场’(tests目录)，跳过演习。"
  else
      # --- 单元测试军规审查（仅在本次会发起演习时执行） ---
      print_sub_header "帝国戎卫兵团军规审查"
      poetry run python tools/court/judge.py tests --select TP001,TP002,TP003 || { print_error "❌ 发现调用生产代码和虚假测试，军规审查失败！"; exit 1; }
      print_success "✅ 单元测试纯净度通过"

      # 智能寻找关联测试目录
      RELATED_TEST_DIR=""
      if [[ "$AUDIT_DIR" == timeos/* ]]; then
          test_candidate="tests/${AUDIT_DIR#timeos/}"
          if [ -d "$test_candidate" ]; then RELATED_TEST_DIR="$test_candidate"; fi
      elif [[ "$AUDIT_DIR" == "tools"* ]]; then
          if [ -d "tests/tools" ]; then RELATED_TEST_DIR="tests/tools"; fi
      fi

      if [ -z "$RELATED_TEST_DIR" ]; then
          print_warning "未找到与 $AUDIT_DIR 匹配的镜像测试目录，跳过演习。"
      else
          # 追加阶段：对演习靶场进行静态审查
          print_chapter_header "追加阶段：对【演习靶场】进行静态审查"
          run_static_audit_on_target "$RELATED_TEST_DIR"

          print_sub_header "演习靶场: $RELATED_TEST_DIR"
          print_sub_header "演习兵种: 纯粹步兵 (标记: 'unit')"

          COV_ARGS=(--cov="$AUDIT_DIR" --cov-report=term-missing --cov-fail-under=0)

          set +e
          poetry run pytest -m "unit" ${COV_ARGS[@]} "$RELATED_TEST_DIR"
          status=$?
          set -e

          if [ "$status" -ne 0 ] && [ "$status" -ne 5 ]; then # 5 = no tests collected
              run_or_warn false
          fi
      fi
  fi
  print_success "国防演习阶段完成"
fi


# ==============================================================================
# --- 最终裁决 ---
# ==============================================================================
if [ "$AUDIT_NON_BLOCKING" = "1" ]; then
  print_chapter_header "🏛️ 帝国军刀完成侦察 - 战区情报已达！"
else
  print_chapter_header "🏛️ 帝国军刀审计完成 - 战区已达纯净！"
fi