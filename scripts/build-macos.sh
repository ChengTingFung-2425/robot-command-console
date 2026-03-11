#!/usr/bin/env bash
#
# macOS Build Script - PyInstaller Binary tar.gz 打包
#
# 此腳本支援 macOS 打包模式：
#   1. Binary tar.gz - 使用 PyInstaller 打包 PyQt6 應用
#
# 使用方式:
#   ./scripts/build-macos.sh                # 打包 macOS tar.gz
#   ./scripts/build-macos.sh --help         # 顯示幫助訊息
#

set -euo pipefail
trap 'log_error "腳本執行失敗於第 ${LINENO} 行"' ERR

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
QTAPP_DIR="${PROJECT_ROOT}/Edge/qtwebview-app"
DIST_DIR="${PROJECT_ROOT}/dist"


log_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

log_info()    { echo -e "${CYAN}➤  $1${NC}"; }
log_success() { echo -e "${GREEN}✓  $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠  $1${NC}"; }
log_error()   { echo -e "${RED}✗  $1${NC}" >&2; }

command_exists() {
    command -v "$1" >/dev/null 2>&1
}


show_help() {
    cat << EOF
macOS Build Script — Robot Command Console

使用方式:
    $(basename "$0") [選項]

選項:
    --help, -h      顯示此幫助訊息

輸出檔案:
    dist/RobotConsole-macos.tar.gz          PyInstaller macOS Application Bundle

前置需求:
    Python >= 3.11, pip, pyinstaller

範例:
    ./scripts/build-macos.sh

EOF
}


parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "未知選項：$1"
                show_help
                exit 1
                ;;
        esac
    done
}


check_python_env() {
    log_info "檢查 Python 環境..."

    if ! command_exists python3; then
        log_error "Python 3 未安裝。請安裝 Python >= 3.11。"
        return 1
    fi

    local py_version
    py_version=$(python3 --version 2>&1)
    log_success "Python 版本：${py_version}"

    if ! python3 -m pyinstaller --version >/dev/null 2>&1; then
        log_info "PyInstaller 未安裝，正在安裝..."
        python3 -m pip install --upgrade pyinstaller pillow || {
            log_error "PyInstaller 安裝失敗，請手動執行：pip install pyinstaller pillow"
            return 1
        }
    fi

    log_success "PyInstaller 版本：$(python3 -m pyinstaller --version 2>&1)"
    return 0
}


build_macos_tarball() {
    log_header "打包 macOS Binary tar.gz（PyInstaller）"

    if [[ ! -f "${QTAPP_DIR}/build.spec" ]]; then
        log_error "找不到 build.spec：${QTAPP_DIR}/build.spec"
        return 1
    fi

    check_python_env || return 1

    local splash_script="${QTAPP_DIR}/resources/images/create_splash_image.py"
    if [[ -f "${splash_script}" ]]; then
        log_info "建立啟動畫面圖片..."
        python3 "${splash_script}" 2>&1 || log_warning "啟動畫面建立失敗（繼續打包）"
    fi

    log_info "安裝 Python 依賴..."
    python3 -m pip install --upgrade pip setuptools wheel
    local edge_requirements="${PROJECT_ROOT}/Edge/requirements.txt"
    if [[ -f "${edge_requirements}" ]]; then
        python3 -m pip install -r "${edge_requirements}" || \
            log_warning "部分依賴安裝失敗：Edge/requirements.txt（繼續打包）"
    fi
    log_success "Python 依賴安裝完成"

    log_info "清理舊的打包結果..."
    rm -rf "${PROJECT_ROOT}/build" \
        "${DIST_DIR}/RobotConsole" \
        "${DIST_DIR}/RobotConsole.app" \
        "${DIST_DIR}/RobotConsole-macos.tar.gz"

    log_info "執行 PyInstaller..."
    (
        cd "${PROJECT_ROOT}"
        PYTHONPATH="${PROJECT_ROOT}/src" \
            python3 -m pyinstaller Edge/qtwebview-app/build.spec \
            --distpath "${DIST_DIR}" \
            --workpath "${PROJECT_ROOT}/build" \
            --log-level WARN
    ) || {
        log_error "PyInstaller 打包失敗"
        return 1
    }

    local bundle_name
    if [[ -d "${DIST_DIR}/RobotConsole.app" ]]; then
        bundle_name="RobotConsole.app"
    elif [[ -d "${DIST_DIR}/RobotConsole" ]]; then
        bundle_name="RobotConsole"
        log_warning "未找到 RobotConsole.app，改以 RobotConsole 目錄建立 tar.gz"
    else
        log_error "找不到 macOS 打包輸出：${DIST_DIR}/RobotConsole.app 或 ${DIST_DIR}/RobotConsole"
        return 1
    fi

    mkdir -p "${DIST_DIR}"
    local tarball_name="RobotConsole-macos.tar.gz"
    log_info "建立 ${tarball_name}..."
    (
        cd "${DIST_DIR}"
        tar -czf "${tarball_name}" "${bundle_name}"
    )

    local size
    size=$(du -sh "${DIST_DIR}/${tarball_name}" | cut -f1)
    log_success "macOS tar.gz 打包成功：dist/${tarball_name}（${size}）"
}


print_summary() {
    log_header "打包完成摘要"

    echo -e "${CYAN}輸出目錄：${PROJECT_ROOT}/dist/${NC}"
    echo ""

    if [[ -f "${DIST_DIR}/RobotConsole-macos.tar.gz" ]]; then
        local size
        size=$(du -sh "${DIST_DIR}/RobotConsole-macos.tar.gz" | cut -f1)
        log_success "RobotConsole-macos.tar.gz（${size}）"
    else
        log_warning "未找到輸出檔案。"
    fi

    echo ""
}


main() {
    parse_args "$@"

    log_header "Robot Command Console — macOS 打包腳本"
    echo -e "專案根目錄：${CYAN}${PROJECT_ROOT}${NC}"
    echo -e "輸出目錄：  ${CYAN}${DIST_DIR}${NC}"
    echo ""

    build_macos_tarball
    print_summary

    echo -e "${GREEN}✅ macOS 打包作業完成！${NC}"
}


main "$@"
