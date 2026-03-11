# build-windows.ps1
#
# Windows 打包腳本 - Electron NSIS 安裝程式與 PyInstaller NSIS 安裝程式建置
#
# 此腳本可建置兩種 Windows 安裝程式：
#   1. NSIS 安裝程式 (PyQt6/Tiny)  - 使用 PyInstaller 建置並以 NSIS 打包
#   2. NSIS 安裝程式 (Electron)    - 使用 electron-builder 建置 NSIS 安裝程式
#
# 使用方式:
#   .\scripts\build-windows.ps1                  # 建置兩種格式
#   .\scripts\build-windows.ps1 -Target nsis     # 僅建置 PyInstaller + NSIS
#   .\scripts\build-windows.ps1 -Target electron # 僅建置 Electron NSIS
#   .\scripts\build-windows.ps1 -Help            # 顯示說明
#
# 前置需求:
#   - Python 3.11+
#   - Node.js 18 LTS+
#   - NSIS 3.x (https://nsis.sourceforge.io/)
#   - pip (PyInstaller, Pillow)
#   - npm (electron-builder)

[CmdletBinding()]
param(
    [ValidateSet("all", "nsis", "electron")]
    [string]$Target = "all",

    [switch]$Help
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ─── 路徑設定 ────────────────────────────────────────────────
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Split-Path -Parent $ScriptDir
$ElectronAppDir = Join-Path $ProjectRoot "Edge\electron-app"
$QtAppDir       = Join-Path $ProjectRoot "Edge\qtwebview-app"
$DistDir        = Join-Path $ProjectRoot "dist"

# ─── 彩色輸出輔助函式 ────────────────────────────────────────
function Write-Header  { param($Msg) Write-Host "`n$("=" * 60)`n  $Msg`n$("=" * 60)`n" -ForegroundColor Blue }
function Write-Info    { param($Msg) Write-Host "  ➤  $Msg" -ForegroundColor Cyan }
function Write-Success { param($Msg) Write-Host "  ✓  $Msg" -ForegroundColor Green }
function Write-Warning { param($Msg) Write-Host "  ⚠  $Msg" -ForegroundColor Yellow }
function Write-Err     { param($Msg) Write-Host "  ✗  $Msg" -ForegroundColor Red }

# ─── 說明訊息 ────────────────────────────────────────────────
function Show-Help {
    Write-Host @"
Windows 打包腳本 — Robot Command Console

使用方式:
    .\scripts\build-windows.ps1 [選項]

選項:
    -Target <all|nsis|electron>
                all      : 建置兩種格式（預設）
                nsis     : 僅建置 PyInstaller NSIS 安裝程式
                electron : 僅建置 Electron NSIS 安裝程式
    -Help       : 顯示此說明

輸出檔案:
    dist\RobotConsole-Setup-3.2.0.exe           PyInstaller NSIS 安裝程式
    dist\RobotConsole-Electron-Setup-1.0.0.exe  Electron NSIS 安裝程式

前置需求:
    NSIS:     https://nsis.sourceforge.io/
    Python:   3.11 以上
    Node.js:  18 LTS 以上

範例:
    .\scripts\build-windows.ps1
    .\scripts\build-windows.ps1 -Target nsis
    .\scripts\build-windows.ps1 -Target electron
"@
}

# ─── 確認命令是否存在 ────────────────────────────────────────
function Test-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

# ─── 確認 Python 環境 ────────────────────────────────────────
function Assert-PythonEnv {
    Write-Info "正在確認 Python 環境..."

    if (-not (Test-Command "python")) {
        throw "找不到 Python。請安裝 Python 3.11+。"
    }

    $pyVersion = python --version 2>&1
    Write-Success "Python 版本：$pyVersion"

    # 確認 PyInstaller 與 Pillow 是否已安裝
    $pip = python -m pip show pyinstaller 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Info "正在安裝 PyInstaller..."
        python -m pip install --upgrade pyinstaller pillow
        if ($LASTEXITCODE -ne 0) {
            throw "PyInstaller 安裝失敗。"
        }
    }
    Write-Success "PyInstaller：OK"
}

# ─── 確認 NSIS ───────────────────────────────────────────────
function Assert-NSIS {
    Write-Info "正在確認 NSIS..."

    # 搜尋常見的 NSIS 安裝路徑
    $nsisLocations = @(
        "C:\Program Files (x86)\NSIS\makensis.exe",
        "C:\Program Files\NSIS\makensis.exe",
        (Get-Command "makensis.exe" -ErrorAction SilentlyContinue)?.Source
    )

    $makensis = $null
    foreach ($loc in $nsisLocations) {
        if ($loc -and (Test-Path $loc)) {
            $makensis = $loc
            break
        }
    }

    if (-not $makensis) {
        throw "找不到 NSIS。請從 https://nsis.sourceforge.io/ 安裝 NSIS。"
    }

    $nsisVersion = & $makensis /VERSION 2>&1
    Write-Success "NSIS 版本：$nsisVersion"
    return $makensis
}

# ─── 確認 Node.js 環境 ───────────────────────────────────────
function Assert-NodeEnv {
    Write-Info "正在確認 Node.js 環境..."

    if (-not (Test-Command "node")) {
        throw "找不到 Node.js。請安裝 Node.js 18 LTS。"
    }

    Write-Success "Node.js 版本：$(node --version)"
    Write-Success "npm 版本：$(npm --version)"
}

# ─── PyInstaller + NSIS 建置 ─────────────────────────────────
function Build-NsisInstaller {
    Write-Header "建置 PyInstaller + NSIS 安裝程式"

    Assert-PythonEnv

    # 產生啟動畫面圖片
    $splashScript = Join-Path $QtAppDir "resources\images\create_splash_image.py"
    if (Test-Path $splashScript) {
        Write-Info "正在產生啟動畫面圖片..."
        python $splashScript
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "啟動畫面產生失敗（繼續執行）"
        }
    }

    # 安裝 Python 依賴
    Write-Info "正在安裝 Python 依賴..."
    $reqFile = Join-Path $ProjectRoot "Edge\requirements.txt"
    if (Test-Path $reqFile) {
        python -m pip install -r $reqFile --quiet
    }

    # 清除舊的建置成果
    Write-Info "正在清除舊的建置成果..."
    $buildDir = Join-Path $ProjectRoot "build"
    $distConsole = Join-Path $DistDir "RobotConsole"
    if (Test-Path $buildDir)    { Remove-Item $buildDir    -Recurse -Force }
    if (Test-Path $distConsole) { Remove-Item $distConsole -Recurse -Force }

    # 使用 PyInstaller 建置
    Write-Info "正在使用 PyInstaller 建置..."
    $specFile = Join-Path $QtAppDir "build.spec"
    $env:PYTHONPATH = Join-Path $ProjectRoot "src"

    Push-Location $ProjectRoot
    try {
        python -m PyInstaller $specFile `
            --distpath $DistDir `
            --workpath $buildDir `
            --log-level WARN
        if ($LASTEXITCODE -ne 0) {
            throw "PyInstaller 建置失敗。"
        }
    } finally {
        Pop-Location
    }

    # 確認建置結果
    if (-not (Test-Path $distConsole)) {
        throw "找不到 PyInstaller 輸出目錄：$distConsole"
    }
    Write-Success "PyInstaller 建置完成"

    # 確認 NSIS
    $makensis = Assert-NSIS

    # 建置 NSIS 安裝程式
    Write-Info "正在建置 NSIS 安裝程式..."
    $nsiScript = Join-Path $QtAppDir "installer.nsi"

    Push-Location $QtAppDir
    try {
        & $makensis /V2 $nsiScript
        if ($LASTEXITCODE -ne 0) {
            throw "NSIS 建置失敗。"
        }
    } finally {
        Pop-Location
    }

    # 確認輸出檔案
    $installerFiles = Get-ChildItem $DistDir -Filter "RobotConsole-Setup-*.exe" -ErrorAction SilentlyContinue
    if ($installerFiles) {
        foreach ($f in $installerFiles) {
            $size = [math]::Round($f.Length / 1MB, 1)
            Write-Success "安裝程式建立完成：$($f.Name) ($($size) MB)"
        }
    } else {
        throw "找不到 NSIS 安裝程式輸出檔案。"
    }
}

# ─── Electron NSIS 建置 ──────────────────────────────────────
function Build-ElectronNsis {
    Write-Header "建置 Electron NSIS 安裝程式"

    Assert-NodeEnv

    if (-not (Test-Path $ElectronAppDir)) {
        throw "找不到 Electron 應用程式目錄：$ElectronAppDir"
    }

    # 安裝 npm 依賴
    Write-Info "正在安裝 npm 依賴..."
    Push-Location $ElectronAppDir
    try {
        npm install --prefer-offline
        if ($LASTEXITCODE -ne 0) {
            throw "npm install 失敗。"
        }
        Write-Success "npm 依賴安裝完成"

        # 使用 electron-builder 建置 NSIS 安裝程式
        Write-Info "正在使用 electron-builder 建置 Windows NSIS 安裝程式..."
        npx electron-builder --win nsis --publish never
        if ($LASTEXITCODE -ne 0) {
            throw "electron-builder 建置失敗。"
        }
    } finally {
        Pop-Location
    }

    # 確認輸出檔案並複製到 dist/
    $electronDist = Join-Path $ElectronAppDir "dist"
    $installerFiles = Get-ChildItem $electronDist -Filter "*.exe" -Recurse -ErrorAction SilentlyContinue |
                      Where-Object { $_.Name -notlike "*Uninstall*" }

    if ($installerFiles) {
        New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
        foreach ($f in $installerFiles) {
            $destName = "RobotConsole-Electron-Setup-$(Split-Path $f.Name -Leaf)"
            Copy-Item $f.FullName (Join-Path $DistDir $destName) -Force
            $size = [math]::Round($f.Length / 1MB, 1)
            Write-Success "安裝程式建立完成：$destName ($($size) MB)"
        }
    } else {
        Write-Warning "找不到 Electron NSIS 安裝程式輸出檔案（請確認 electron-builder 的 dist/ 目錄）"
    }
}

# ─── 完成摘要 ─────────────────────────────────────────────────
function Show-Summary {
    Write-Header "建置完成摘要"

    Write-Host "  輸出目錄：$DistDir" -ForegroundColor Cyan
    Write-Host ""

    $found = $false
    $patterns = @("RobotConsole-Setup-*.exe", "RobotConsole-Electron-Setup-*.exe")
    foreach ($pattern in $patterns) {
        $files = Get-ChildItem $DistDir -Filter $pattern -ErrorAction SilentlyContinue
        foreach ($f in $files) {
            $size = [math]::Round($f.Length / 1MB, 1)
            Write-Success "$($f.Name) ($($size) MB)"
            $found = $true
        }
    }

    if (-not $found) {
        Write-Warning "未找到輸出檔案。"
    }
    Write-Host ""
}

# ─── 主程式 ──────────────────────────────────────────────────
function Main {
    if ($Help) {
        Show-Help
        return
    }

    Write-Header "Robot Command Console — Windows 打包腳本"
    Write-Host "  專案根目錄：$ProjectRoot" -ForegroundColor Cyan
    Write-Host "  建置目標：  $Target" -ForegroundColor Cyan
    Write-Host ""

    $exitCode = 0

    if ($Target -eq "all" -or $Target -eq "nsis") {
        try {
            Build-NsisInstaller
        } catch {
            Write-Err "PyInstaller + NSIS 建置失敗：$_"
            $exitCode = 1
        }
    }

    if ($Target -eq "all" -or $Target -eq "electron") {
        try {
            Build-ElectronNsis
        } catch {
            Write-Err "Electron NSIS 建置失敗：$_"
            $exitCode = 1
        }
    }

    Show-Summary

    if ($exitCode -ne 0) {
        Write-Host "`n  ❌ 部分建置失敗。請確認錯誤訊息。" -ForegroundColor Red
    } else {
        Write-Host "`n  ✅ 所有建置完成！" -ForegroundColor Green
    }

    exit $exitCode
}

Main
