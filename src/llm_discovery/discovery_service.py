"""
LLM Copilot Discovery Service

統一的發現服務介面，整合 scanner 和 probe
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone

from .models import ProviderManifest, ProviderHealth, Skill
from .scanner import FilesystemScanner
from .probe import EndpointProbe
from .security import PromptSanitizer, ResponseFilter


logger = logging.getLogger(__name__)


class DiscoveryService:
    """
    LLM Copilot 發現服務
    
    負責：
    - 掃描並發現本地註冊的 LLM Copilot
    - 探測端點健康狀態
    - 管理提供商註冊
    - 提供技能查詢介面
    """

    def __init__(self):
        self._providers: Dict[str, ProviderManifest] = {}
        self._health_cache: Dict[str, ProviderHealth] = {}
        self.scanner = FilesystemScanner()
        self.probe = EndpointProbe()

    async def scan_providers(self) -> List[ProviderManifest]:
        """
        掃描並返回所有註冊的提供商
        
        Returns:
            ProviderManifest 列表
        """
        logger.info("開始掃描 LLM Copilot 提供商")

        # 使用 scanner 掃描 filesystem
        manifests = self.scanner.scan_manifests()

        # 更新內部快取
        self._providers = {m.provider_id: m for m in manifests}

        logger.info(f"發現 {len(manifests)} 個提供商")

        return manifests

    async def check_health(self, provider_id: str) -> Optional[ProviderHealth]:
        """
        檢查特定提供商的健康狀態
        
        Args:
            provider_id: 提供商 ID
            
        Returns:
            ProviderHealth 或 None（如果提供商不存在）
        """
        manifest = self._providers.get(provider_id)
        if not manifest:
            logger.warning(f"提供商不存在: {provider_id}")
            return None

        # 獲取之前的失敗次數
        previous_health = self._health_cache.get(provider_id)
        previous_failures = previous_health.consecutive_failures if previous_health else 0

        # 探測健康狀態
        health = self.probe.check_provider_health(
            provider_id=provider_id,
            endpoints=manifest.endpoints,
            previous_failures=previous_failures
        )

        # 更新快取
        self._health_cache[provider_id] = health

        return health

    async def check_all_health(self) -> Dict[str, ProviderHealth]:
        """
        檢查所有提供商的健康狀態
        
        Returns:
            provider_id -> ProviderHealth 的字典
        """
        health_results = {}

        for provider_id in self._providers.keys():
            health = await self.check_health(provider_id)
            if health:
                health_results[provider_id] = health

        return health_results

    async def get_available_providers(self) -> List[str]:
        """
        返回所有可用的提供商 ID
        
        Returns:
            提供商 ID 列表
        """
        # 檢查所有提供商的健康狀態
        health_results = await self.check_all_health()

        # 篩選可用的提供商
        available = [
            provider_id
            for provider_id, health in health_results.items()
            if health.status == "available"
        ]

        return available

    async def register_provider(
        self,
        manifest: ProviderManifest,
        user_approved: bool = False
    ) -> bool:
        """
        註冊新的提供商（需用戶同意）
        
        Args:
            manifest: 提供商 manifest
            user_approved: 是否經用戶批准
            
        Returns:
            成功返回 True，失敗返回 False
        """
        if not user_approved:
            logger.warning(f"註冊被拒絕（未經用戶批准）: {manifest.provider_id}")
            return False

        # 檢查是否已存在
        if manifest.provider_id in self._providers:
            logger.warning(f"提供商已存在: {manifest.provider_id}")
            return False

        # 更新 metadata
        manifest.metadata["registered_at"] = datetime.now(timezone.utc).isoformat()
        manifest.metadata["user_approved"] = True

        # 儲存到 filesystem
        success = self.scanner.save_manifest(manifest)

        if success:
            # 更新內部快取
            self._providers[manifest.provider_id] = manifest
            logger.info(f"成功註冊提供商: {manifest.provider_id}")

        return success

    async def unregister_provider(self, provider_id: str) -> bool:
        """
        取消註冊提供商
        
        Args:
            provider_id: 提供商 ID
            
        Returns:
            成功返回 True，失敗返回 False
        """
        # 從 filesystem 刪除
        success = self.scanner.delete_manifest(provider_id)

        if success:
            # 從內部快取移除
            self._providers.pop(provider_id, None)
            self._health_cache.pop(provider_id, None)
            logger.info(f"成功取消註冊提供商: {provider_id}")

        return success

    async def get_provider_skills(self, provider_id: str) -> List[Skill]:
        """
        獲取提供商的技能列表
        
        Args:
            provider_id: 提供商 ID
            
        Returns:
            Skill 列表
        """
        manifest = self._providers.get(provider_id)
        if not manifest:
            logger.warning(f"提供商不存在: {provider_id}")
            return []

        return manifest.skills

    async def search_skills(
        self,
        keyword: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[tuple[str, Skill]]:
        """
        搜尋技能
        
        Args:
            keyword: 關鍵字（搜尋名稱和描述）
            category: 類別過濾
            
        Returns:
            (provider_id, Skill) 元組列表
        """
        results = []

        for provider_id, manifest in self._providers.items():
            for skill in manifest.skills:
                # 類別過濾
                if category and skill.category != category:
                    continue

                # 關鍵字搜尋
                if keyword:
                    keyword_lower = keyword.lower()
                    if (
                        keyword_lower not in skill.name.lower()
                        and keyword_lower not in skill.description.lower()
                    ):
                        continue

                results.append((provider_id, skill))

        return results

    def get_provider_info(self, provider_id: str) -> Optional[Dict]:
        """
        獲取提供商資訊（不包含敏感資料）
        
        Args:
            provider_id: 提供商 ID
            
        Returns:
            提供商資訊字典
        """
        manifest = self._providers.get(provider_id)
        if not manifest:
            return None

        # 獲取健康狀態
        health = self._health_cache.get(provider_id)

        info = {
            "provider_id": manifest.provider_id,
            "provider_name": manifest.provider_name,
            "provider_version": manifest.provider_version,
            "description": manifest.description,
            "capabilities": manifest.capabilities,
            "skills_count": len(manifest.skills),
            "endpoints_count": len(manifest.endpoints),
            "anti_decryption_enabled": {
                "no_prompt_logging": manifest.anti_decryption.no_prompt_logging,
                "no_model_exposure": manifest.anti_decryption.no_model_exposure,
            },
            "health": health.to_dict() if health else None,
        }

        return info

    def get_all_providers_info(self) -> List[Dict]:
        """
        獲取所有提供商資訊
        
        Returns:
            提供商資訊列表
        """
        return [
            self.get_provider_info(provider_id)
            for provider_id in self._providers.keys()
        ]
    
    async def query_skill_info(
        self,
        provider_id: str,
        skill_id: str,
        query_method: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        查詢 skill 提供的資訊（軟體→LLM）
        
        Args:
            provider_id: 提供商 ID
            skill_id: 技能 ID
            query_method: 查詢方法名稱
            params: 查詢參數
            
        Returns:
            查詢結果
        """
        manifest = self._providers.get(provider_id)
        if not manifest:
            logger.warning(f"提供商不存在: {provider_id}")
            return None
        
        # 找到對應的 skill
        skill = next((s for s in manifest.skills if s.skill_id == skill_id), None)
        if not skill:
            logger.warning(f"Skill 不存在: {skill_id}")
            return None
        
        # 檢查 info_schema
        if not skill.info_schema:
            logger.warning(f"Skill {skill_id} 未提供 info_schema")
            return None
        
        query_methods = skill.get_query_methods()
        if query_method not in query_methods:
            logger.warning(f"查詢方法不存在: {query_method}")
            return None
        
        # 這裡應該實際呼叫 provider 的端點來獲取資訊
        # 在 PoC 階段，我們返回 schema 定義
        return {
            "provider_id": provider_id,
            "skill_id": skill_id,
            "query_method": query_method,
            "schema": query_methods[query_method],
            "note": "In production, this would call the actual provider endpoint"
        }
    
    async def get_available_info_providers(self) -> Dict[str, List[str]]:
        """
        獲取所有可提供資訊的 skills（軟體→LLM）
        
        Returns:
            provider_id -> [info_types] 的字典
        """
        info_map = {}
        
        for provider_id, manifest in self._providers.items():
            info_types = []
            for skill in manifest.skills:
                info_types.extend(skill.get_info_providers())
            
            if info_types:
                info_map[provider_id] = list(set(info_types))
        
        return info_map
