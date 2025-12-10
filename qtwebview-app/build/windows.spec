# -*- mode: python ; coding: utf-8 -*-
"""
Windows 平台 PyInstaller 配置
"""

block_cipher = None

a = Analysis(
    ['../main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../resources', 'resources'),
        ('../../WebUI/app/static', 'WebUI/app/static'),
        ('../../WebUI/app/templates', 'WebUI/app/templates'),
    ],
    hiddenimports=[
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtWebChannel',
        'flask',
        'flask_login',
        'flask_sqlalchemy',
        'flask_migrate',
        'flask_mail',
        'flask_bootstrap',
        'flask_moment',
        'flask_babel',
        'flask_wtf',
        'sqlalchemy',
        'requests',
        'psycopg2',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TinyEdgeApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 不顯示 console 視窗
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='../resources/icon.ico' if os.path.exists('../resources/icon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TinyEdgeApp',
)
