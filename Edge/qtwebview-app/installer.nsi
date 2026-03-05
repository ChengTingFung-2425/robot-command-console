; ============================================================
; Robot Command Console - Windows NSIS 安裝程式腳本
;
; 此腳本將 PyInstaller 建置的 PyQt6 應用程式打包為
; Windows 安裝程式（.exe）。
;
; 使用方式（從專案根目錄執行）:
;   makensis Edge/qtwebview-app/installer.nsi
;
; 前置條件:
;   1. 已執行 pyinstaller Edge/qtwebview-app/build.spec
;   2. dist/RobotConsole/ 目錄存在
; ============================================================

Unicode True

; ─── MUI2 (Modern UI 2) ────────────────────────────────────
!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

; ─── 應用程式資訊 ────────────────────────────────────────────
!define APP_NAME        "Robot Command Console"
!define APP_PUBLISHER   "Robot Command Console Team"
!define APP_VERSION     "3.2.0"
!define APP_URL         "https://github.com/ChengTingFung-2425/robot-command-console"
!define APP_EXE         "RobotConsole.exe"

; 安裝目錄（64 位元 Program Files）
!define INSTALL_DIR     "$PROGRAMFILES64\${APP_NAME}"

; 登錄機碼（解除安裝資訊）
!define UNINSTALL_KEY   "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"

; ─── 安裝程式輸出設定 ────────────────────────────────────────
OutFile "..\..\dist\RobotConsole-Setup-${APP_VERSION}.exe"
InstallDir "${INSTALL_DIR}"
InstallDirRegKey HKLM "${UNINSTALL_KEY}" "InstallLocation"

; 要求管理員權限
RequestExecutionLevel admin

; ─── MUI 設定 ────────────────────────────────────────────────
!define MUI_ABORTWARNING

; 完成頁面：安裝後啟動應用程式
!define MUI_FINISHPAGE_RUN         "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT    "Launch ${APP_NAME}"
!define MUI_FINISHPAGE_LINK        "Visit project homepage"
!define MUI_FINISHPAGE_LINK_LOCATION "${APP_URL}"

; ─── 安裝精靈頁面 ────────────────────────────────────────────
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; ─── 解除安裝精靈頁面 ───────────────────────────────────────
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; ─── 語言 ────────────────────────────────────────────────────
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "TradChinese"

; ─── 版本資訊（安裝程式 EXE 中繼資料）──────────────────────
VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey /LANG=${LANG_ENGLISH} "ProductName"      "${APP_NAME}"
VIAddVersionKey /LANG=${LANG_ENGLISH} "ProductVersion"   "${APP_VERSION}"
VIAddVersionKey /LANG=${LANG_ENGLISH} "CompanyName"      "${APP_PUBLISHER}"
VIAddVersionKey /LANG=${LANG_ENGLISH} "LegalCopyright"   "Copyright (c) 2024-2026 ${APP_PUBLISHER}"
VIAddVersionKey /LANG=${LANG_ENGLISH} "FileDescription"  "${APP_NAME} Installer"
VIAddVersionKey /LANG=${LANG_ENGLISH} "FileVersion"      "${APP_VERSION}.0"

; ─── 安裝區段 ────────────────────────────────────────────────
Section "Main Application" SecMainApp
    SectionIn RO  ; 必要區段（無法取消選取）

    SetOutPath "$INSTDIR"
    SetOverwrite on

    ; 從 PyInstaller 輸出目錄複製所有檔案
    File /r "..\..\dist\RobotConsole\*.*"

    ; 產生解除安裝程式
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; 建立開始功能表捷徑
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortcut  "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" \
                    "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
    CreateShortcut  "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" \
                    "$INSTDIR\Uninstall.exe"

    ; 建立桌面捷徑
    CreateShortcut  "$DESKTOP\${APP_NAME}.lnk" \
                    "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0

    ; 寫入 Windows「程式和功能」登錄條目
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "DisplayName"          "${APP_NAME}"
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "DisplayVersion"       "${APP_VERSION}"
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "Publisher"            "${APP_PUBLISHER}"
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "URLInfoAbout"         "${APP_URL}"
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "InstallLocation"      "$INSTDIR"
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "UninstallString"      '"$INSTDIR\Uninstall.exe"'
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
    WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoModify"             1
    WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoRepair"             1

    ; 取得安裝大小並寫入登錄
    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "${UNINSTALL_KEY}" "EstimatedSize" "$0"

SectionEnd

; ─── 解除安裝區段 ────────────────────────────────────────────
Section "Uninstall"

    ; 刪除捷徑
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk"
    RMDir  "$SMPROGRAMS\${APP_NAME}"
    Delete "$DESKTOP\${APP_NAME}.lnk"

    ; 刪除解除安裝程式本身（最後執行）
    Delete "$INSTDIR\Uninstall.exe"

    ; 刪除安裝目錄
    RMDir /r "$INSTDIR"

    ; 刪除登錄條目
    DeleteRegKey HKLM "${UNINSTALL_KEY}"

SectionEnd

