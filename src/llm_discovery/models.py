"""
資料模型定義

定義 LLM Copilot discovery 所需的資料結構
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Literal
from dataclasses import dataclass, field, asdict
import json


@dataclass
class AntiDecryptionConfig:
    """防止模型解密攻擊的配置"""
    no_prompt_logging: bool = True
    no_model_exposure: bool = True
    prompt_sanitization: bool = True
    response_filtering: bool = True
    memory_cleanup: bool = True
    timing_obfuscation: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Endpoint:
    """服務端點定義"""
    type: Literal["http", "https", "unix-socket", "tcp"]
    address: str
    protocol: str = "openai-compatible"
    health_check_path: str = "/health"
    timeout_ms: int = 5000
    api_base: str = "/v1"  # OpenAI API base path

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Skill:
    """技能定義（Copilot 可執行的功能）"""
    skill_id: str
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    llm_accessible: bool = True  # 是否可透過 LLM API 存取
    function_definition: Optional[Dict[str, Any]] = None  # OpenAI function calling 格式（LLM 操作）
    info_schema: Optional[Dict[str, Any]] = None  # 資訊提供 schema（軟體→LLM）

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_openai_function(self) -> Dict[str, Any]:
        """轉換為 OpenAI function calling 格式（LLM 用於操作軟體）"""
        if self.function_definition:
            return self.function_definition
        
        # 自動生成 function definition
        return {
            "name": self.skill_id,
            "description": self.description,
            "parameters": self.input_schema
        }
    
    def get_info_providers(self) -> List[str]:
        """獲取此 skill 可提供的資訊類型（軟體→LLM）"""
        if not self.info_schema:
            return []
        return self.info_schema.get("provides", [])
    
    def get_query_methods(self) -> Dict[str, Any]:
        """獲取資訊查詢方法（LLM 用於獲取資訊）"""
        if not self.info_schema:
            return {}
        return self.info_schema.get("query_methods", {})


@dataclass
class ProviderManifest:
    """LLM Copilot 提供商 Manifest"""
    manifest_version: str
    provider_id: str
    provider_name: str
    provider_version: str
    endpoints: List[Endpoint]
    skills: List[Skill] = field(default_factory=list)
    description: Optional[str] = None
    vendor: Optional[str] = None
    homepage: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)
    anti_decryption: AntiDecryptionConfig = field(default_factory=AntiDecryptionConfig)
    llm_compatibility: Optional[Dict[str, Any]] = None  # LLM 相容性配置
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典，包含嵌套物件"""
        data = {
            "manifest_version": self.manifest_version,
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "endpoints": [ep.to_dict() for ep in self.endpoints],
            "skills": [skill.to_dict() for skill in self.skills],
            "capabilities": self.capabilities,
            "security": {
                "anti_decryption": self.anti_decryption.to_dict(),
                "local_only": True,
                "require_auth": False,
            },
            "metadata": self.metadata,
        }
        if self.description:
            data["description"] = self.description
        if self.vendor:
            data["vendor"] = self.vendor
        if self.homepage:
            data["homepage"] = self.homepage
        if self.llm_compatibility:
            data["llm_compatibility"] = self.llm_compatibility
        return data
    
    def get_openai_functions(self) -> List[Dict[str, Any]]:
        """獲取所有可透過 LLM API 存取的 skills 作為 OpenAI functions"""
        return [
            skill.to_openai_function()
            for skill in self.skills
            if skill.llm_accessible
        ]

    def to_json(self, indent: int = 2) -> str:
        """轉換為 JSON 字符串"""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProviderManifest":
        """從字典創建實例"""
        endpoints = [Endpoint(**ep) for ep in data.get("endpoints", [])]
        skills = [Skill(**skill) for skill in data.get("skills", [])]

        anti_decryption_data = data.get("security", {}).get("anti_decryption", {})
        anti_decryption = AntiDecryptionConfig(**anti_decryption_data) if anti_decryption_data else AntiDecryptionConfig()

        return cls(
            manifest_version=data["manifest_version"],
            provider_id=data["provider_id"],
            provider_name=data["provider_name"],
            provider_version=data["provider_version"],
            endpoints=endpoints,
            skills=skills,
            description=data.get("description"),
            vendor=data.get("vendor"),
            homepage=data.get("homepage"),
            capabilities=data.get("capabilities", []),
            anti_decryption=anti_decryption,
            llm_compatibility=data.get("llm_compatibility"),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "ProviderManifest":
        """從 JSON 字符串創建實例"""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class ProviderHealth:
    """提供商健康狀態"""
    provider_id: str
    status: Literal["available", "unavailable", "degraded"]
    last_check: datetime
    response_time_ms: float
    error_message: Optional[str] = None
    consecutive_failures: int = 0
    available_endpoints: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "status": self.status,
            "last_check": self.last_check.isoformat(),
            "response_time_ms": self.response_time_ms,
            "error_message": self.error_message,
            "consecutive_failures": self.consecutive_failures,
            "available_endpoints": self.available_endpoints,
        }
