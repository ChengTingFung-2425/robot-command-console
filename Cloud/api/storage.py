"""
雲服務儲存 API

提供檔案上傳、下載、管理等功能
目前支援本地檔案系統儲存（可擴充整合 S3 相容的物件儲存）
"""

import hashlib
import logging
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, BinaryIO

from werkzeug.utils import safe_join


logger = logging.getLogger(__name__)

# 允許的 category 和 user_id 字元（防止路徑穿越）
# 不允許 "." 以防 ".." 繞過
SAFE_PATH_PATTERN = re.compile(r'^[A-Za-z0-9_-]+$')

# 分塊大小（8KB）
CHUNK_SIZE = 8192


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

    def _validate_path_component(self, component: str, name: str):
        """驗證路徑組件是否安全"""
        if not SAFE_PATH_PATTERN.match(component):
            raise ValueError(f"Invalid {name}: contains unsafe characters")

    def upload_file(
        self,
        file_data: BinaryIO,
        filename: str,
        user_id: str,
        category: str = "general",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        上傳檔案（使用串流方式避免記憶體尖峰）

        Args:
            file_data: 檔案資料流
            filename: 檔案名稱
            user_id: 上傳者 ID
            category: 檔案類別
            metadata: 額外元數據

        Returns:
            上傳結果資訊
        """
        # 驗證路徑組件安全性
        self._validate_path_component(category, "category")
        self._validate_path_component(user_id, "user_id")

        # 使用 werkzeug.safe_join 建立並驗證路徑（防止路徑穿越，含 startswith 繞過）
        safe_path = safe_join(str(self.storage_path), category, user_id)
        if safe_path is None:
            raise ValueError("Path traversal detected")
        category_path = Path(safe_path)
        category_path.mkdir(parents=True, exist_ok=True)

        # 建立臨時檔案並串流寫入，同時計算雜湊
        hash_obj = hashlib.sha256()
        file_size = 0

        # 使用臨時檔案避免部分寫入
        temp_fd, temp_path = tempfile.mkstemp(dir=category_path, prefix='.upload_')
        try:
            with os.fdopen(temp_fd, 'wb') as temp_file:
                while True:
                    chunk = file_data.read(CHUNK_SIZE)
                    if not chunk:
                        break

                    file_size += len(chunk)

                    # 檢查檔案大小
                    if file_size > self.max_file_size:
                        raise ValueError(f"File size exceeds maximum {self.max_file_size}")

                    hash_obj.update(chunk)
                    temp_file.write(chunk)

            # 計算最終雜湊
            file_hash = hash_obj.hexdigest()

            # 使用雜湊作為檔名，避免衝突
            ext = Path(filename).suffix
            storage_filename = f"{file_hash}{ext}"
            file_path = category_path / storage_filename

            # 如果檔案已存在（相同雜湊），刪除臨時檔案
            if file_path.exists():
                os.unlink(temp_path)
                logger.info(f"File already exists: {file_path}")
            else:
                # 原子性搬移到目標路徑
                os.rename(temp_path, file_path)
                logger.info(f"File uploaded: {file_path}")

        except Exception:
            # 清理臨時檔案
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

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
            file_id: 檔案 ID（完整 SHA-256 雜湊，64 hex）
            user_id: 下載者 ID
            category: 檔案類別

        Returns:
            檔案內容或 None（檔案不存在）
        """
        # 驗證路徑組件安全性
        self._validate_path_component(category, "category")
        self._validate_path_component(user_id, "user_id")

        # 驗證 file_id 格式（完整 SHA-256：64 hex）
        if len(file_id) != 64 or not all(c in "0123456789abcdefABCDEF" for c in file_id):
            logger.warning(f"Invalid file_id format for download_file: {file_id}")
            return None

        # 使用 safe_join 建立並驗證路徑（防止路徑穿越）
        safe_cat_path = safe_join(str(self.storage_path), category, user_id)
        if safe_cat_path is None:
            logger.warning(f"Path traversal detected in download_file: category={category} user_id={user_id}")
            return None
        category_path = Path(safe_cat_path)
        if not category_path.exists():
            logger.warning(f"Category path not found: {category_path}")
            return None

        # 尋找匹配的檔案（精確匹配前綴）
        matches = [
            file_path
            for file_path in category_path.glob(f"{file_id}*")
            if file_path.is_file()
        ]

        if not matches:
            logger.warning(f"File not found: {file_id}")
            return None

        if len(matches) > 1:
            logger.error(f"Multiple files matched for file_id={file_id}: {matches}")
            return None

        # 讀取唯一匹配的檔案
        file_path = matches[0]
        with open(file_path, "rb") as f:
            content = f.read()
        logger.info(f"File downloaded: {file_path}")
        return content

    def delete_file(
        self,
        file_id: str,
        user_id: str,
        category: str = "general"
    ) -> bool:
        """
        刪除檔案

        Args:
            file_id: 檔案 ID（完整 SHA-256 雜湊，64 hex）
            user_id: 擁有者 ID
            category: 檔案類別

        Returns:
            是否刪除成功
        """
        # 驗證路徑組件安全性
        self._validate_path_component(category, "category")
        self._validate_path_component(user_id, "user_id")

        # 驗證 file_id 格式（完整 SHA-256：64 hex）
        if len(file_id) != 64 or not all(c in "0123456789abcdefABCDEF" for c in file_id):
            logger.warning(f"Invalid file_id format for delete_file: {file_id}")
            return False

        # 使用 safe_join 建立並驗證路徑（防止路徑穿越）
        safe_cat_path = safe_join(str(self.storage_path), category, user_id)
        if safe_cat_path is None:
            logger.warning(f"Path traversal detected in delete_file: category={category} user_id={user_id}")
            return False
        category_path = Path(safe_cat_path)
        if not category_path.exists():
            logger.warning(f"Category path not found: {category_path}")
            return False

        # 尋找匹配的檔案
        matches = [
            file_path
            for file_path in category_path.glob(f"{file_id}*")
            if file_path.is_file()
        ]

        if not matches:
            logger.info(f"No file found to delete for file_id={file_id} in {category_path}")
            return False

        if len(matches) > 1:
            # 安全起見：若同一 file_id 對應多個檔案則不執行刪除
            logger.error(
                f"Multiple files matched for file_id={file_id} in {category_path}: {matches}"
            )
            return False

        # 僅刪除唯一匹配的檔案
        file_path = matches[0]
        file_path.unlink()
        logger.info(f"File deleted: {file_path}")
        return True

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
        # 驗證路徑組件安全性
        self._validate_path_component(user_id, "user_id")
        if category:
            self._validate_path_component(category, "category")

        files = []

        # 決定搜尋路徑（使用 safe_join 防止路徑穿越）
        if category:
            safe_cat_path = safe_join(str(self.storage_path), category, user_id)
            if safe_cat_path is None:
                logger.warning(f"Path traversal detected in list_files: category={category} user_id={user_id}")
                return []
            search_paths = [Path(safe_cat_path)]
        else:
            search_paths = []
            for p in self.storage_path.iterdir():
                if not p.is_dir():
                    continue
                safe_user_path = safe_join(str(self.storage_path), p.name, user_id)
                if safe_user_path is not None:
                    search_paths.append(Path(safe_user_path))

        # 搜尋檔案
        for path in search_paths:
            if not path.exists():
                continue

            for file_path in path.glob("*"):
                if file_path.is_file():
                    stat = file_path.stat()
                    # 返回 storage_filename（實際檔名）和 file_id（雜湊）
                    files.append({
                        "file_id": file_path.stem,
                        "storage_filename": file_path.name,
                        "filename": file_path.name,  # 保持相容性
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
            # 驗證 user_id 安全性（防止路徑穿越）
            try:
                self._validate_path_component(user_id, "user_id")
            except ValueError:
                logger.warning(f"get_storage_stats: invalid user_id rejected: {user_id!r}")
                raise
            # 特定使用者統計
            for category_path in self.storage_path.iterdir():
                if not category_path.is_dir():
                    continue
                safe_user_path = safe_join(str(category_path), user_id)
                if safe_user_path is None:
                    continue
                user_path = Path(safe_user_path)
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
