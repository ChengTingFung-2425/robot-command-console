# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Robot Command Console - Tiny Edge App

此檔案定義了 PyQt6 應用程式的打包配置，包括：
- 必要的程式碼和資源檔案
- 隱藏的導入（PyQt6 相關模組）
- 排除的模組（減小打包大小）
- 平台特定的配置

使用方式:
    pyinstaller Edge/qtwebview-app/build.spec
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 取得專案根目錄
project_root = os.path.abspath(os.path.join(SPECPATH, '../..'))
app_dir = os.path.join(project_root, 'Edge/qtwebview-app')

# 收集資料檔案
datas = [
    (os.path.join(app_dir, 'resources'), 'resources'),
    (os.path.join(project_root, 'Edge/WebUI/app/static'), 'Edge/WebUI/app/static'),
    (os.path.join(project_root, 'Edge/WebUI/app/templates'), 'Edge/WebUI/app/templates'),
]

# 收集所有 PyQt6 相關模組
hiddenimports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtWebEngineCore',
    'PyQt6.QtWebEngineWidgets',
    'PyQt6.QtWebChannel',
    'PyQt6.QtNetwork',
    'PyQt6.sip',
    # Flask 相關
    'Flask',
    'flask_login',
    'flask_sqlalchemy',
    'flask_wtf',
    'werkzeug',
    'jinja2',
    'markupsafe',
    # 專案模組
    'src.common.version',
    'src.common.backend_service_manager',
]

# 排除不必要的模組以減小打包大小
excludes = [
    'matplotlib',
    'scipy',
    'numpy',
    'pandas',
    'tensorflow',
    'torch',
    'PIL.ImageQt',  # 如果不需要 Qt 圖片支援
    'tkinter',
    'wx',
    'PySide6',
    'PySide2',
    'PyQt5',
]

# Analysis 階段 - 分析依賴關係
a = Analysis(
    [os.path.join(app_dir, 'main.py')],
    pathex=[project_root, os.path.join(project_root, 'src')],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# PYZ 階段 - 建立 Python 壓縮檔案庫
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# EXE 階段 - 建立可執行檔
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RobotConsole',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windows: 不顯示控制台視窗
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(app_dir, 'resources/icon.ico') if os.path.exists(os.path.join(app_dir, 'resources/icon.ico')) else None,
)

# COLLECT 階段 - 收集所有檔案到目錄
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RobotConsole',
)

# macOS 特定配置 - 建立 .app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='RobotConsole.app',
        icon=os.path.join(app_dir, 'resources/icon.icns') if os.path.exists(os.path.join(app_dir, 'resources/icon.icns')) else None,
        bundle_identifier='com.robotconsole.edge',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSAppleScriptEnabled': False,
            'CFBundleName': 'Robot Command Console',
            'CFBundleDisplayName': 'Robot Command Console',
            'CFBundleShortVersionString': '3.2.0',
            'CFBundleVersion': '3.2.0',
            'NSHighResolutionCapable': 'True',
        },
    )
