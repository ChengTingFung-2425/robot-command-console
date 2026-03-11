#!/usr/bin/env bash
#
# Linux Build Script - AppImage 與 Binary tar.gz 打包
#
# 此腳本支援兩種 Linux 打包模式：
#   1. AppImage  - 使用 Electron Builder 打包 Electron 應用
#   2. Binary    - 使用 PyInstaller 打包 PyQt6 應用，產生 tar.gz
#
# 使用方式:
#   ./scripts/build-linux.sh                # 打包所有格式（AppImage + Binary tar.gz）
#   ./scripts/build-linux.sh --appimage     # 僅打包 AppImage
#   ./scripts/build-linux.sh --binary       # 僅打包 Binary tar.gz
#   ./scripts/build-linux.sh --help         # 顯示幫助訊息
#

set -euo pipefail
trap 'log_error "腳本執行失敗於第 ${LINENO} 行"' ERR

# ─── 顏色定義 ───────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ─── 路徑設定 ────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ELECTRON_APP_DIR="${PROJECT_ROOT}/Edge/electron-app"
QTAPP_DIR="${PROJECT_ROOT}/Edge/qtwebview-app"
DIST_DIR="${PROJECT_ROOT}/dist"

# ─── 建置模式（預設：兩種都打包）────────────────────────────────────────────
BUILD_APPIMAGE=true
BUILD_BINARY=true

# ─── 輔助函式 ────────────────────────────────────────────────────────────────

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

# ─── 幫助訊息 ────────────────────────────────────────────────────────────────

show_help() {
    cat << EOF
Linux Build Script — Robot Command Console

使用方式:
    $(basename "$0") [選項]

選項:
    --appimage      僅打包 Electron AppImage
    --binary        僅打包 PyInstaller Binary tar.gz
    --help, -h      顯示此幫助訊息

不加任何選項時，兩種格式都會打包。

輸出檔案:
    dist/RobotConsole-linux.AppImage          Electron AppImage
    dist/RobotConsole-linux.tar.gz            PyInstaller Binary

前置需求:
    AppImage: Node.js >= 18, npm
    Binary:   Python >= 3.11, pip, pyinstaller

範例:
    ./scripts/build-linux.sh
    ./scripts/build-linux.sh --appimage
    ./scripts/build-linux.sh --binary

EOF
}

# ─── 參數解析 ────────────────────────────────────────────────────────────────

parse_args() {
    if [[ $# -eq 0 ]]; then
        BUILD_APPIMAGE=true
        BUILD_BINARY=true
        return
    fi

    BUILD_APPIMAGE=false
    BUILD_BINARY=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --appimage)
                BUILD_APPIMAGE=true
                shift
                ;;
            --binary)
                BUILD_BINARY=true
                shift
                ;;
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

# ─── 前置條件檢查 ────────────────────────────────────────────────────────────

check_system_deps_linux() {
    log_info "檢查 Linux 系統依賴..."

    local missing_pkgs=()
    local check_libs=(
        "libxcb-xinerama0"
        "libxcb-cursor0"
        "libxkbcommon-x11-0"
        "libdbus-1-3"
    )

    for pkg in "${check_libs[@]}"; do
        if ! dpkg -l "$pkg" 2>/dev/null | grep -q "^ii"; then
            missing_pkgs+=("$pkg")
        fi
    done

    if [[ ${#missing_pkgs[@]} -gt 0 ]]; then
        log_warning "以下系統套件可能未安裝（某些環境可預先裝好，可忽略此警告）："
        for pkg in "${missing_pkgs[@]}"; do
            echo "    - $pkg"
        done
        echo ""
        log_warning "如需安裝，請執行："
        echo "    sudo apt-get install -y ${missing_pkgs[*]}"
        echo ""
    else
        log_success "系統依賴檢查通過"
    fi
}

check_node_env() {
    log_info "檢查 Node.js 環境..."

    if ! command_exists node; then
        log_error "Node.js 未安裝。請安裝 Node.js >= 18。"
        log_error "安裝方式：https://nodejs.org/"
        return 1
    fi

    local node_version
    node_version=$(node --version 2>&1)
    log_success "Node.js 版本：${node_version}"

    if ! command_exists npm; then
        log_error "npm 未安裝。"
        return 1
    fi
    log_success "npm 版本：$(npm --version)"
    return 0
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

# ─── AppImage 打包（Electron Builder）───────────────────────────────────────

build_appimage() {
    log_header "打包 Linux AppImage（Electron Builder）"

    # 確認 electron-app 目錄存在
    if [[ ! -d "${ELECTRON_APP_DIR}" ]]; then
        log_error "找不到 Electron 應用目錄：${ELECTRON_APP_DIR}"
        return 1
    fi

    check_node_env || return 1

    # 安裝 npm 依賴
    log_info "安裝 npm 依賴..."
    (cd "${ELECTRON_APP_DIR}" && npm install --prefer-offline) || {
        log_error "npm install 失敗"
        return 1
    }
    log_success "npm 依賴安裝完成"

    # 執行 electron-builder
    log_info "執行 electron-builder --linux AppImage..."
    (
        cd "${ELECTRON_APP_DIR}"
        npx electron-builder --linux AppImage \
            --publish never 2>&1
    ) || {
        log_error "electron-builder 打包失敗"
        return 1
    }

    # 搜尋產生的 AppImage 檔案
    local appimage_file
    appimage_file=$(find "${ELECTRON_APP_DIR}/dist" -name "*.AppImage" 2>/dev/null | head -1)

    if [[ -z "${appimage_file}" ]]; then
        log_error "找不到產生的 AppImage 檔案"
        return 1
    fi

    # 複製到專案 dist/ 目錄
    mkdir -p "${DIST_DIR}"
    local output_name="RobotConsole-linux.AppImage"
    cp "${appimage_file}" "${DIST_DIR}/${output_name}"
    chmod +x "${DIST_DIR}/${output_name}"

    local size
    size=$(du -sh "${DIST_DIR}/${output_name}" | cut -f1)
    log_success "AppImage 打包成功：dist/${output_name}（${size}）"
}

# ─── Binary tar.gz 打包（PyInstaller）──────────────────────────────────────

build_binary_tarball() {
    log_header "打包 Linux Binary tar.gz（PyInstaller）"

    # 確認 build.spec 存在
    if [[ ! -f "${QTAPP_DIR}/build.spec" ]]; then
        log_error "找不到 build.spec：${QTAPP_DIR}/build.spec"
        return 1
    fi

    check_python_env || return 1
    check_system_deps_linux

    # 建立啟動畫面圖片（如腳本存在）
    local splash_script="${QTAPP_DIR}/resources/images/create_splash_image.py"
    if [[ -f "${splash_script}" ]]; then
        log_info "建立啟動畫面圖片..."
        python3 "${splash_script}" 2>&1 || log_warning "啟動畫面建立失敗（繼續打包）"
    fi

    # 安裝 Python 依賴
    log_info "安裝 Python 依賴..."
    python3 -m pip install --upgrade pip setuptools wheel
    local edge_requirements="${PROJECT_ROOT}/Edge/requirements.txt"
    if [[ -f "${edge_requirements}" ]]; then
        python3 -m pip install -r "${edge_requirements}" || \
            log_warning "部分依賴安裝失敗：Edge/requirements.txt（繼續打包）"
    fi
    log_success "Python 依賴安裝完成"

    # 清理舊的打包結果
    log_info "清理舊的打包結果..."
    rm -rf "${PROJECT_ROOT}/build" "${PROJECT_ROOT}/dist/RobotConsole"

    # 執行 PyInstaller
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

    # 驗證打包目錄
    if [[ ! -d "${DIST_DIR}/RobotConsole" ]]; then
        log_error "找不到打包輸出目錄：${DIST_DIR}/RobotConsole"
        return 1
    fi
    log_success "PyInstaller 打包完成"

    # 建立 tar.gz
    local tarball_name="RobotConsole-linux.tar.gz"
    log_info "建立 ${tarball_name}..."
    (
        cd "${DIST_DIR}"
        tar -czf "${tarball_name}" RobotConsole/
    )

    local size
    size=$(du -sh "${DIST_DIR}/${tarball_name}" | cut -f1)
    log_success "Binary tar.gz 打包成功：dist/${tarball_name}（${size}）"
}

# ─── 打包摘要 ────────────────────────────────────────────────────────────────

print_summary() {
    log_header "打包完成摘要"

    echo -e "${CYAN}輸出目錄：${PROJECT_ROOT}/dist/${NC}"
    echo ""

    local found=false
    for f in \
        "${DIST_DIR}/RobotConsole-linux.AppImage" \
        "${DIST_DIR}/RobotConsole-linux.tar.gz"; do
        if [[ -f "$f" ]]; then
            local size
            size=$(du -sh "$f" | cut -f1)
            log_success "$(basename "$f")（${size}）"
            found=true
        fi
    done

    if [[ "${found}" == false ]]; then
        log_warning "未找到任何輸出檔案。"
    fi

    echo ""
}

# ─── 主程式 ──────────────────────────────────────────────────────────────────

main() {
    parse_args "$@"

    log_header "Robot Command Console — Linux 打包腳本"
    echo -e "專案根目錄：${CYAN}${PROJECT_ROOT}${NC}"
    echo -e "輸出目錄：  ${CYAN}${DIST_DIR}${NC}"
    echo ""

    local exit_code=0

    if [[ "${BUILD_APPIMAGE}" == true ]]; then
        build_appimage || {
            log_error "AppImage 打包失敗"
            exit_code=1
        }
    fi

    if [[ "${BUILD_BINARY}" == true ]]; then
        build_binary_tarball || {
            log_error "Binary tar.gz 打包失敗"
            exit_code=1
        }
    fi

    print_summary

    if [[ ${exit_code} -ne 0 ]]; then
        echo -e "${RED}❌ 部分打包作業失敗，請檢查以上錯誤訊息。${NC}"
    else
        echo -e "${GREEN}✅ 所有打包作業完成！${NC}"
    fi

    return ${exit_code}
}

main "$@"
