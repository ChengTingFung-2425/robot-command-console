"""
Filesystem Registry Scanner

掃描標準化路徑以發現註冊的 LLM Copilot manifest 檔案
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Optional
import platform

from .models import ProviderManifest


logger = logging.getLogger(__name__)


class FilesystemScanner:
    """檔案系統掃描器 - 掃描 manifest 註冊路徑"""

    @staticmethod
    def get_registry_path() -> Path:
        """
        獲取當前平台的標準 registry 路徑
        
        Returns:
            Registry 路徑
        """
        system = platform.system()

        if system == "Linux":
            base_path = Path.home() / ".local" / "share"
        elif system == "Darwin":  # macOS
            base_path = Path.home() / "Library" / "Application Support"
        elif system == "Windows":
            base_path = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        else:
            # 預設使用 Linux 路徑
            base_path = Path.home() / ".local" / "share"

        registry_path = base_path / "llm-providers"

        # 確保目錄存在
        registry_path.mkdir(parents=True, exist_ok=True)

        return registry_path

    @staticmethod
    def scan_manifests() -> List[ProviderManifest]:
        """
        掃描所有註冊的 manifest 檔案
        
        Returns:
            ProviderManifest 列表
        """
        registry_path = FilesystemScanner.get_registry_path()
        manifests = []

        logger.info(f"掃描 manifest 路徑: {registry_path}")

        if not registry_path.exists():
            logger.warning(f"Registry 路徑不存在: {registry_path}")
            return manifests

        # 掃描所有 .json 檔案
        for json_file in registry_path.glob("*.json"):
            try:
                manifest = FilesystemScanner.load_manifest(json_file)
                if manifest:
                    manifests.append(manifest)
                    logger.info(f"成功載入 manifest: {manifest.provider_id}")
            except Exception as e:
                logger.error(f"載入 manifest 失敗 {json_file}: {e}")

        logger.info(f"共發現 {len(manifests)} 個 LLM Copilot 提供商")
        return manifests

    @staticmethod
    def load_manifest(file_path: Path) -> Optional[ProviderManifest]:
        """
        從檔案載入 manifest
        
        Args:
            file_path: manifest 檔案路徑
            
        Returns:
            ProviderManifest 或 None
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 驗證必要欄位
            required_fields = ["manifest_version", "provider_id", "provider_name", "provider_version", "endpoints"]
            for field in required_fields:
                if field not in data:
                    logger.error(f"Manifest 缺少必要欄位 '{field}': {file_path}")
                    return None

            # 創建 manifest 實例
            manifest = ProviderManifest.from_dict(data)

            # 驗證安全配置
            if not manifest.anti_decryption.no_prompt_logging:
                logger.warning(f"Manifest {manifest.provider_id} 未啟用 no_prompt_logging")

            if not manifest.anti_decryption.no_model_exposure:
                logger.warning(f"Manifest {manifest.provider_id} 未啟用 no_model_exposure")

            return manifest

        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析錯誤 {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"載入 manifest 失敗 {file_path}: {e}")
            return None

    @staticmethod
    def save_manifest(manifest: ProviderManifest) -> bool:
        """
        儲存 manifest 到檔案系統
        
        Args:
            manifest: 要儲存的 manifest
            
        Returns:
            成功返回 True，失敗返回 False
        """
        try:
            registry_path = FilesystemScanner.get_registry_path()
            file_path = registry_path / f"{manifest.provider_id}.json"

            # 檢查安全配置（不自動修改，而是拒絕不安全的 manifest）
            if not manifest.anti_decryption.no_prompt_logging:
                logger.error(
                    f"安全錯誤：Provider {manifest.provider_id} 未啟用 no_prompt_logging。"
                    "為了保護用戶隱私，此配置必須啟用。註冊被拒絕。"
                )
                return False

            if not manifest.anti_decryption.no_model_exposure:
                logger.error(
                    f"安全錯誤：Provider {manifest.provider_id} 未啟用 no_model_exposure。"
                    "為了防止模型解密攻擊，此配置必須啟用。註冊被拒絕。"
                )
                return False

            # 寫入檔案
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(manifest.to_json(indent=2))

            # 設定檔案權限為 0600（僅擁有者可讀寫）
            os.chmod(file_path, 0o600)

            logger.info(f"成功儲存 manifest: {file_path}")
            return True

        except Exception as e:
            logger.error(f"儲存 manifest 失敗: {e}")
            return False

    @staticmethod
    def delete_manifest(provider_id: str) -> bool:
        """
        刪除指定的 manifest
        
        Args:
            provider_id: 提供商 ID
            
        Returns:
            成功返回 True，失敗返回 False
        """
        try:
            registry_path = FilesystemScanner.get_registry_path()
            file_path = registry_path / f"{provider_id}.json"

            if file_path.exists():
                file_path.unlink()
                logger.info(f"成功刪除 manifest: {provider_id}")
                return True
            else:
                logger.warning(f"Manifest 不存在: {provider_id}")
                return False

        except Exception as e:
            logger.error(f"刪除 manifest 失敗: {e}")
            return False

    @staticmethod
    def validate_manifest_permissions(file_path: Path) -> bool:
        """
        驗證 manifest 檔案權限（應為 0600）
        
        Args:
            file_path: manifest 檔案路徑
            
        Returns:
            權限正確返回 True，否則 False
        """
        try:
            stat_info = os.stat(file_path)
            mode = stat_info.st_mode & 0o777

            # 檢查是否為 0600 (rw-------)
            if mode != 0o600:
                logger.warning(f"Manifest 權限不安全 {file_path}: {oct(mode)}")
                return False

            return True

        except Exception as e:
            logger.error(f"檢查檔案權限失敗: {e}")
            return False
