"""
雲服務儲存 API

提供檔案上傳、下載、管理等功能
支援本地檔案系統和 S3 相容的物件儲存
"""

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, BinaryIO


logger = logging.getLogger(__name__)


class CloudStorageService:
    """雲服務儲存服務"""

    def __init__(self, storage_path: str, max_file_size: int = 100 * 1024 * 1024):
        """
        初始化儲存服務

        Args:
            storage_path: 儲存路徑
            max_file_size: 最大檔案大小（位元組），預設 100MB
        """
        self.storage_path = Path(storage_path)
        self.max_file_size = max_file_size

        # 確保儲存目錄存在
        self.storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized storage service at: {self.storage_path}")

    def upload_file(
        self,
        file_data: BinaryIO,
        filename: str,
        user_id: str,
        category: str = "general",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        上傳檔案

        Args:
            file_data: 檔案資料流
            filename: 檔案名稱
            user_id: 上傳者 ID
            category: 檔案類別
            metadata: 額外元數據

        Returns:
            上傳結果資訊
        """
        # 讀取檔案內容
        content = file_data.read()
        file_size = len(content)

        # 檢查檔案大小
        if file_size > self.max_file_size:
            raise ValueError(f"File size {file_size} exceeds maximum {self.max_file_size}")

        # 計算檔案雜湊
        file_hash = hashlib.sha256(content).hexdigest()

        # 生成儲存路徑（使用雜湊避免重複）
        category_path = self.storage_path / category / user_id
        category_path.mkdir(parents=True, exist_ok=True)

        # 使用雜湊作為檔名，避免衝突
        ext = Path(filename).suffix
        storage_filename = f"{file_hash}{ext}"
        file_path = category_path / storage_filename

        # 如果檔案已存在（相同雜湊），直接返回
        if file_path.exists():
            logger.info(f"File already exists: {file_path}")
        else:
            # 寫入檔案
            with open(file_path, "wb") as f:
                f.write(content)
            logger.info(f"File uploaded: {file_path}")

        # 返回檔案資訊
        return {
            "file_id": file_hash,
            "filename": filename,
            "storage_path": str(file_path.relative_to(self.storage_path)),
            "size": file_size,
            "hash": file_hash,
            "category": category,
            "user_id": user_id,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        }

    def download_file(
        self,
        file_id: str,
        user_id: str,
        category: str = "general"
    ) -> Optional[bytes]:
        """
        下載檔案

        Args:
            file_id: 檔案 ID（雜湊）
            user_id: 下載者 ID
            category: 檔案類別

        Returns:
            檔案內容或 None（檔案不存在）
        """
        # 查找檔案
        category_path = self.storage_path / category / user_id
        if not category_path.exists():
            logger.warning(f"Category path not found: {category_path}")
            return None

        # 尋找匹配的檔案
        for file_path in category_path.glob(f"{file_id}*"):
            if file_path.is_file():
                with open(file_path, "rb") as f:
                    content = f.read()
                logger.info(f"File downloaded: {file_path}")
                return content

        logger.warning(f"File not found: {file_id}")
        return None

    def delete_file(
        self,
        file_id: str,
        user_id: str,
        category: str = "general"
    ) -> bool:
        """
        刪除檔案

        Args:
            file_id: 檔案 ID（雜湊）
            user_id: 擁有者 ID
            category: 檔案類別

        Returns:
            是否刪除成功
        """
        # 查找檔案
        category_path = self.storage_path / category / user_id
        if not category_path.exists():
            logger.warning(f"Category path not found: {category_path}")
            return False

        # 尋找並刪除匹配的檔案
        deleted = False
        for file_path in category_path.glob(f"{file_id}*"):
            if file_path.is_file():
                file_path.unlink()
                logger.info(f"File deleted: {file_path}")
                deleted = True

        return deleted

    def list_files(
        self,
        user_id: str,
        category: Optional[str] = None
    ) -> list:
        """
        列出使用者的檔案

        Args:
            user_id: 使用者 ID
            category: 檔案類別（可選）

        Returns:
            檔案清單
        """
        files = []

        # 決定搜尋路徑
        if category:
            search_paths = [self.storage_path / category / user_id]
        else:
            search_paths = [p / user_id for p in self.storage_path.iterdir() if p.is_dir()]

        # 搜尋檔案
        for path in search_paths:
            if not path.exists():
                continue

            for file_path in path.glob("*"):
                if file_path.is_file():
                    stat = file_path.stat()
                    files.append({
                        "file_id": file_path.stem,
                        "filename": file_path.name,
                        "size": stat.st_size,
                        "category": path.parent.name,
                        "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                    })

        return files

    def get_storage_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        取得儲存統計資訊

        Args:
            user_id: 使用者 ID（可選，None 表示全系統統計）

        Returns:
            統計資訊
        """
        total_files = 0
        total_size = 0

        if user_id:
            # 特定使用者統計
            for category_path in self.storage_path.iterdir():
                if not category_path.is_dir():
                    continue
                user_path = category_path / user_id
                if user_path.exists():
                    for file_path in user_path.glob("*"):
                        if file_path.is_file():
                            total_files += 1
                            total_size += file_path.stat().st_size
        else:
            # 全系統統計
            for file_path in self.storage_path.rglob("*"):
                if file_path.is_file():
                    total_files += 1
                    total_size += file_path.stat().st_size

        return {
            "user_id": user_id,
            "total_files": total_files,
            "total_size": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }
