#!/bin/bash
# ==============================================================================
# run_android_deterministic_eval.sh
# 
# Android / KMP プロジェクト向けの決定論的（Deterministic）Eval 実行ランナー
# 
# 【実行フロー】
#   1. ./gradlew assembleDebug (ビルド成功判定)
#   2. ./gradlew testDebugUnitTest (ユニットテスト通過判定)
#   3. ./gradlew lintDebug (静的解析パス判定 ※オプション)
#   4. python3 check_agent_diff.py (差分スコープ・Kotlin安全性判定)
# 
# 【終了コード】
#   0: すべてのGraderに合格
#   1: いずれかのGraderで不合格（タスク未達成）
# ==============================================================================

set -u

# 色付け用
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(pwd)"

DIFF_TARGET="${1:-working-tree}"
RUN_LINT="${RUN_LINT:-false}"

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}  Android Coding Agent Deterministic Eval Runner     ${NC}"
echo -e "${BLUE}======================================================${NC}"
echo "Project Root : $PROJECT_ROOT"
echo "Diff Target  : $DIFF_TARGET"
echo "Run Lint     : $RUN_LINT"
echo ""

START_TIME=$(date +%s)
FAILED_STEPS=()

# --- Helper function ---
run_step() {
    local step_name="$1"
    local command="$2"

    echo -e "${YELLOW}▶ Running: ${step_name}...${NC}"
    local step_start=$(date +%s)

    eval "$command"
    local exit_code=$?
    local step_end=$(date +%s)
    local elapsed=$((step_end - step_start))

    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✔ [PASS] ${step_name} (${elapsed}s)${NC}\n"
    else
        echo -e "${RED}✘ [FAIL] ${step_name} (${elapsed}s)${NC}\n"
        FAILED_STEPS+=("$step_name")
    fi
    return $exit_code
}

# --- 1. Gradle Assemble (Build) ---
if [ -f "./gradlew" ]; then
    run_step "Gradle Build (assembleDebug)" "./gradlew assembleDebug --quiet"
else
    echo -e "${YELLOW}⚠ ./gradlew が見つからないためビルドテストをスキップします。${NC}\n"
fi

# --- 2. Unit Tests ---
if [ -f "./gradlew" ]; then
    run_step "Unit Tests (testDebugUnitTest)" "./gradlew testDebugUnitTest --quiet"
fi

# --- 3. Lint (Optional) ---
if [ "$RUN_LINT" = "true" ] && [ -f "./gradlew" ]; then
    run_step "Android Lint (lintDebug)" "./gradlew lintDebug --quiet"
fi

# --- 4. Agent Diff Grader ---
CHECK_DIFF_SCRIPT="${SCRIPT_DIR}/check_agent_diff.py"
if [ -f "$CHECK_DIFF_SCRIPT" ]; then
    run_step "Diff Safety & Scope Check" "python3 $CHECK_DIFF_SCRIPT --diff-target $DIFF_TARGET"
else
    echo -e "${RED}✘ check_agent_diff.py not found at $CHECK_DIFF_SCRIPT${NC}"
    FAILED_STEPS+=("Diff Safety Check (Script missing)")
fi

END_TIME=$(date +%s)
TOTAL_ELAPSED=$((END_TIME - START_TIME))

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}  Evaluation Summary                                 ${NC}"
echo -e "${BLUE}======================================================${NC}"
echo "Total Time: ${TOTAL_ELAPSED}s"

if [ ${#FAILED_STEPS[@]} -eq 0 ]; then
    echo -e "Result    : ${GREEN}ALL GRADERS PASSED ✨${NC}"
    echo "AI Agentの実装はすべての決定論的品質基準を満たしました。"
    exit 0
else
    echo -e "Result    : ${RED}FAILED (${#FAILED_STEPS[@]} steps failed) ❌${NC}"
    echo "失敗したステップ:"
    for step in "${FAILED_STEPS[@]}"; do
        echo -e "  - ${RED}${step}${NC}"
    done
    exit 1
fi
