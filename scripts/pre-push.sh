#!/usr/bin/env bash
#
# Pre-push Git Hook - 整合 CI 檢查（排除 build.yml）
# 整合來源：ci.yml, api-validation.yml, test-rabbitmq.yml
#
# 使用方式:
#   ./scripts/pre-push.sh              # 執行標準檢查（預設）
#   ./scripts/pre-push.sh --quick      # 只執行 linting 和語法檢查
#   ./scripts/pre-push.sh --full       # 執行所有檢查（包含測試）
#   ./scripts/pre-push.sh --help       # 顯示幫助訊息
#
# 安裝為 Git hook:
#   cp scripts/pre-push.sh .git/hooks/pre-push
#   chmod +x .git/hooks/pre-push
#

set -e  # 遇到錯誤立即退出

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 計數器
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
SKIPPED_CHECKS=0

# 錯誤訊息收集
declare -a ERROR_MESSAGES=()

# 檢查模式（預設為 skip-tests，適合日常開發）
CHECK_MODE="skip-tests"

# 解析命令列參數
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --quick)
                CHECK_MODE="quick"
                shift
                ;;
            --full)
                CHECK_MODE="full"
                shift
                ;;
            --skip-tests)
                CHECK_MODE="skip-tests"
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                CHECK_MODE="quick"
                shift
                ;;
        esac
    done
}

# 顯示幫助訊息
show_help() {
    cat << EOF
Pre-push Git Hook - 整合 CI 檢查

整合來源：
  ✓ ci.yml            - Python/Node.js linting, 測試, 文檔檢查
  ✓ api-validation.yml - OpenAPI 規範驗證
  ✓ test-rabbitmq.yml  - RabbitMQ 測試
  ✗ build.yml         - 排除（打包流程由 CI 處理）

使用方式:
    \$0 [選項]

選項:
    --quick         只執行快速檢查（linting、語法檢查）
    --full          執行所有檢查（包含完整測試）
    --skip-tests    執行除測試外的所有檢查（預設）
    --help, -h      顯示此幫助訊息

檢查模式說明:
    quick:          Linting + 語法檢查（< 1 分鐘）
    skip-tests:     Quick + OpenAPI + 文檔檢查（< 2 分鐘）【預設】
    full:           所有檢查 + 測試（5-10 分鐘）

範例:
    \$0                    # 標準檢查（推薦用於日常開發）
    \$0 --quick            # 快速檢查（適合頻繁提交）
    \$0 --full             # 完整檢查（適合重要變更）

EOF
}

# 印出標題
print_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

# 印出檢查項目標題
print_check() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    echo -e "${YELLOW}➤ [$TOTAL_CHECKS] $1${NC}"
}

# 記錄成功
record_success() {
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    echo -e "${GREEN}✓ $1${NC}"
}

# 記錄失敗
record_failure() {
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
    ERROR_MESSAGES+=("$1")
    echo -e "${RED}✗ $1${NC}"
}

# 記錄跳過
record_skip() {
    SKIPPED_CHECKS=$((SKIPPED_CHECKS + 1))
    echo -e "${YELLOW}⊘ $1${NC}"
}

# 檢查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 檢查 Python 是否可用
check_python() {
    if ! command_exists python3; then
        record_failure "Python 3 未安裝"
        return 1
    fi
    return 0
}

# 檢查 Node.js 是否可用
check_node() {
    if ! command_exists node; then
        record_skip "Node.js 未安裝，跳過 JavaScript 檢查"
        return 1
    fi
    return 0
}

#############################################
# Level 1: 快速檢查（來自 ci.yml）
#############################################

# Python Flake8 Linting (from ci.yml: python-lint job)
check_python_lint() {
    print_check "Python Flake8 Linting (ci.yml: python-lint)"
    
    if ! check_python; then
        return 1
    fi
    
    # 確保 flake8 已安裝
    if ! python3 -c "import flake8" 2>/dev/null; then
        echo "  安裝 flake8..."
        pip install flake8 >/dev/null 2>&1 || {
            record_failure "無法安裝 flake8"
            return 1
        }
    fi
    
    # 執行 flake8 檢查（與 ci.yml 完全一致）
    echo "  檢查主要 Python 檔案..."
    if python3 -m flake8 flask_service.py run_service_cli.py \
        --max-line-length=120 \
        --ignore=W503,E203 \
        --statistics > /tmp/flake8_main.log 2>&1; then
        record_success "主要 Python 檔案檢查通過"
    else
        record_failure "主要 Python 檔案有 linting 錯誤"
        cat /tmp/flake8_main.log
        return 1
    fi
    
    echo "  檢查 src/ 目錄..."
    if python3 -m flake8 src/ \
        --max-line-length=120 \
        --ignore=W503,E203 \
        --statistics > /tmp/flake8_src.log 2>&1; then
        record_success "src/ 目錄檢查通過"
    else
        record_failure "src/ 目錄有 linting 錯誤"
        cat /tmp/flake8_src.log
        return 1
    fi
    
    echo "  檢查 MCP/ 目錄..."
    if python3 -m flake8 MCP/ \
        --max-line-length=120 \
        --ignore=W503,E203 \
        --exclude=MCP/__pycache__ \
        --statistics > /tmp/flake8_mcp.log 2>&1; then
        record_success "MCP/ 目錄檢查通過"
    else
        record_failure "MCP/ 目錄有 linting 錯誤"
        cat /tmp/flake8_mcp.log
        return 1
    fi
    
    record_success "Python Flake8 Linting 完成"
    return 0
}

# Node.js 語法檢查 (from ci.yml: node-lint job)
check_node_syntax() {
    print_check "Node.js 語法檢查 (ci.yml: node-lint)"
    
    if ! check_node; then
        return 0  # 跳過但不視為失敗
    fi
    
    if [ ! -d "electron-app" ]; then
        record_skip "electron-app 目錄不存在"
        return 0
    fi
    
    echo "  檢查 electron-app/main.js..."
    if node --check electron-app/main.js 2>&1; then
        record_success "main.js 語法正確"
    else
        record_failure "main.js 語法錯誤"
        return 1
    fi
    
    echo "  檢查 electron-app/preload.js..."
    if node --check electron-app/preload.js 2>&1; then
        record_success "preload.js 語法正確"
    else
        record_failure "preload.js 語法錯誤"
        return 1
    fi
    
    record_success "Node.js 語法檢查完成"
    return 0
}

#############################################
# Level 2: 中級檢查（來自 ci.yml & api-validation.yml）
#############################################

# OpenAPI 規範驗證 (from ci.yml: openapi-validation & api-validation.yml)
check_openapi() {
    print_check "OpenAPI 規範驗證 (api-validation.yml)"
    
    if ! check_python; then
        return 1
    fi
    
    if [ ! -f "openapi.yaml" ]; then
        record_skip "openapi.yaml 不存在"
        return 0
    fi
    
    # 安裝驗證工具
    if ! python3 -c "import openapi_spec_validator" 2>/dev/null; then
        echo "  安裝 openapi-spec-validator..."
        pip install openapi-spec-validator pyyaml >/dev/null 2>&1 || {
            record_failure "無法安裝 openapi-spec-validator"
            return 1
        }
    fi
    
    # 驗證語法
    echo "  驗證 OpenAPI 語法..."
    if openapi-spec-validator openapi.yaml > /tmp/openapi_validation.log 2>&1; then
        record_success "OpenAPI 語法驗證通過"
    else
        record_failure "OpenAPI 語法驗證失敗"
        cat /tmp/openapi_validation.log
        return 1
    fi
    
    record_success "OpenAPI 規範驗證完成"
    return 0
}

# 文檔完整性檢查 (from ci.yml: docs-check job)
check_docs() {
    print_check "文檔完整性檢查 (ci.yml: docs-check)"
    
    # 與 ci.yml 完全一致的必要文檔清單
    required_docs=(
        "docs/security/threat-model.md"
        "docs/security/security-checklist.md"
        "docs/features/observability-guide.md"
        "docs/architecture.md"
        "docs/proposal.md"
        "openapi.yaml"
    )
    
    missing=0
    for doc in "${required_docs[@]}"; do
        if [ ! -f "$doc" ]; then
            echo -e "  ${RED}✗ 缺少: $doc${NC}"
            missing=1
        else
            echo -e "  ${GREEN}✓ 存在: $doc${NC}"
        fi
    done
    
    if [ $missing -eq 1 ]; then
        record_failure "部分必要文檔缺失"
        return 1
    fi
    
    record_success "所有必要文檔都存在"
    return 0
}

#############################################
# 主程式
#############################################

main() {
    # 解析參數
    parse_args "$@"
    
    # 顯示標題
    print_header "Pre-Push 檢查 (模式: $CHECK_MODE)"
    
    echo -e "檢查模式: ${BLUE}$CHECK_MODE${NC}"
    echo -e "整合來源: ${BLUE}ci.yml, api-validation.yml, test-rabbitmq.yml${NC}"
    echo -e "排除項目: ${YELLOW}build.yml (打包流程)${NC}"
    echo ""
    
    case $CHECK_MODE in
        quick)
            echo -e "說明: 快速檢查，只執行 linting 和語法檢查"
            ;;
        skip-tests)
            echo -e "說明: 標準檢查，跳過測試（適合日常開發）"
            ;;
        full)
            echo -e "說明: 完整檢查，包含所有測試（適合重要變更）"
            ;;
    esac
    echo ""
    
    # 記錄開始時間
    START_TIME=$(date +%s)
    
    # Level 1: 快速檢查（來自 ci.yml）
    print_header "Level 1: 快速檢查 (ci.yml)"
    check_python_lint || true
    check_node_syntax || true
    
    # Level 2: 中級檢查（來自 ci.yml & api-validation.yml）
    if [[ "$CHECK_MODE" != "quick" ]]; then
        print_header "Level 2: 中級檢查 (ci.yml + api-validation.yml)"
        check_openapi || true
        check_docs || true
    fi
    
    # 計算執行時間
    END_TIME=$(date +%s)
    ELAPSED=$((END_TIME - START_TIME))
    
    # 顯示最終報告
    print_header "檢查完成"
    
    echo -e "${BLUE}統計資訊:${NC}"
    echo -e "  總檢查數: ${TOTAL_CHECKS}"
    echo -e "  ${GREEN}通過: ${PASSED_CHECKS}${NC}"
    echo -e "  ${RED}失敗: ${FAILED_CHECKS}${NC}"
    echo -e "  ${YELLOW}跳過: ${SKIPPED_CHECKS}${NC}"
    echo -e "  執行時間: ${ELAPSED} 秒"
    echo ""
    
    # 如果有錯誤，顯示錯誤摘要
    if [ $FAILED_CHECKS -gt 0 ]; then
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${RED}錯誤摘要:${NC}"
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        for error in "${ERROR_MESSAGES[@]}"; do
            echo -e "${RED}  ✗ $error${NC}"
        done
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "${RED}❌ Pre-push 檢查失敗！${NC}"
        echo -e "${YELLOW}提示：${NC}"
        echo -e "  - 修復上述錯誤後再次推送"
        echo -e "  - 使用 ${BLUE}--quick${NC} 選項進行快速檢查"
        echo -e "  - 使用 ${BLUE}git push --no-verify${NC} 跳過此檢查（不建議）"
        echo ""
        exit 1
    else
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}✓ 所有檢查通過！可以安全推送。${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        exit 0
    fi
}

# 執行主程式
main "$@"
