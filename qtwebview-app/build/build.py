#!/usr/bin/env python3
"""
跨平台打包腳本
使用 PyInstaller 打包 Tiny Edge App
"""

import os
import sys
import platform
import subprocess
import shutil


def get_spec_file():
    """根據作業系統選擇對應的 spec 檔案"""
    system = platform.system()
    
    if system == 'Windows':
        return 'windows.spec'
    elif system == 'Darwin':
        return 'macos.spec'
    else:  # Linux
        return 'linux.spec'


def clean_build():
    """清理舊的建置檔案"""
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"清理 {dir_name}/")
            shutil.rmtree(dir_name)


def build():
    """執行打包"""
    print("=" * 60)
    print("Tiny Edge App - 打包腳本")
    print("=" * 60)
    
    # 取得 spec 檔案
    spec_file = get_spec_file()
    print(f"\n使用 spec 檔案: {spec_file}")
    
    if not os.path.exists(spec_file):
        print(f"錯誤: {spec_file} 不存在")
        print("請先建立對應的 spec 檔案")
        return 1
    
    # 清理舊檔案
    print("\n正在清理舊的建置檔案...")
    clean_build()
    
    # 執行 PyInstaller
    print("\n開始打包...")
    cmd = ['pyinstaller', '--clean', spec_file]
    
    try:
        subprocess.run(cmd, check=True)
        print("\n" + "=" * 60)
        print("打包完成！")
        print("=" * 60)
        print(f"\n輸出目錄: dist/")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\n打包失敗: {e}")
        return 1
    except FileNotFoundError:
        print("\n錯誤: 找不到 pyinstaller")
        print("請先安裝: pip install pyinstaller")
        return 1


if __name__ == '__main__':
    sys.exit(build())
