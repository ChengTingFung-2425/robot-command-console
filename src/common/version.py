"""
統一版本號管理

此模組提供整個專案的版本號管理，確保所有組件使用一致的版本號。
"""

__version__ = "3.2.0-beta"
__version_info__ = (3, 2, 0, "beta")

# Release metadata
RELEASE_NAME = "Phase 3.2 - Tiny Edge App"
RELEASE_DATE = "2026-02-04"
BUILD_NUMBER = "001"

# Project metadata
PROJECT_NAME = "Robot Command Console"
PROJECT_DESCRIPTION = "統一的 ALL-in-One Edge Application for Robot Management"
AUTHOR = "Robot Command Console Team"
LICENSE = "MIT"
REPOSITORY_URL = "https://github.com/ChengTingFung-2425/robot-command-console"


def get_version():
    """取得版本號字串"""
    return __version__


def get_version_info():
    """取得版本號元組"""
    return __version_info__


def get_full_version():
    """取得完整版本資訊（包含 build number）"""
    return f"{__version__}+{BUILD_NUMBER}"


def get_release_info():
    """取得發佈資訊"""
    return {
        "version": __version__,
        "version_info": __version_info__,
        "build_number": BUILD_NUMBER,
        "release_name": RELEASE_NAME,
        "release_date": RELEASE_DATE,
        "project_name": PROJECT_NAME,
        "description": PROJECT_DESCRIPTION,
        "author": AUTHOR,
        "license": LICENSE,
        "repository": REPOSITORY_URL
    }


if __name__ == "__main__":
    # 命令列輸出版本資訊
    import json
    print(json.dumps(get_release_info(), indent=2, ensure_ascii=False))
