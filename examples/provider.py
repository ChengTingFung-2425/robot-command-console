#!/usr/bin/env python3
"""
LLM Copilot Provider 範例

展示如何註冊 LLM Copilot 實例及其技能到 discovery service
"""

import sys
from pathlib import Path

# 添加專案路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from llm_discovery import (
    ProviderManifest,
    Endpoint,
    Skill,
    AntiDecryptionConfig,
)
from llm_discovery.scanner import FilesystemScanner


def create_example_provider() -> ProviderManifest:
    """創建範例 LLM Copilot provider manifest"""

    # 定義技能（與 OpenAI function calling 相容）
    skills = [
        Skill(
            skill_id="code_review",
            name="Code Review",
            description="Review code for quality, security, and best practices",
            input_schema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Code to review"},
                    "language": {"type": "string", "description": "Programming language"},
                },
                "required": ["code"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "issues": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "severity": {"type": "string"},
                                "message": {"type": "string"},
                                "line": {"type": "integer"},
                            },
                        },
                    },
                },
            },
            category="code_analysis",
            tags=["review", "quality", "security"],
            llm_accessible=True,  # 可透過 LLM API 存取
            function_definition={  # OpenAI function calling 格式
                "name": "code_review",
                "description": "Review code for quality, security, and best practices",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "The source code to review"
                        },
                        "language": {
                            "type": "string",
                            "description": "Programming language (python, javascript, java, etc.)"
                        }
                    },
                    "required": ["code"]
                }
            }
        ),
        Skill(
            skill_id="refactor",
            name="Code Refactoring",
            description="Refactor code to improve readability and maintainability",
            input_schema={
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "target": {"type": "string", "enum": ["readability", "performance", "structure"]},
                },
                "required": ["code"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "refactored_code": {"type": "string"},
                    "changes": {"type": "array", "items": {"type": "string"}},
                },
            },
            category="code_transformation",
            tags=["refactor", "cleanup"],
        ),
        Skill(
            skill_id="security_scan",
            name="Security Scanner",
            description="Scan code for security vulnerabilities",
            input_schema={
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "scan_level": {"type": "string", "enum": ["basic", "advanced"]},
                },
                "required": ["code"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "vulnerabilities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "severity": {"type": "string"},
                                "description": {"type": "string"},
                            },
                        },
                    },
                },
            },
            category="security",
            tags=["security", "vulnerability", "scan"],
            llm_accessible=True,
            function_definition={
                "name": "security_scan",
                "description": "Scan code for security vulnerabilities",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Code to scan"},
                        "scan_level": {
                            "type": "string",
                            "enum": ["basic", "advanced"],
                            "description": "Scan depth level"
                        }
                    },
                    "required": ["code"]
                }
            },
            info_schema={
                "provides": ["vulnerability_database", "scan_history", "security_metrics"],
                "query_methods": {
                    "get_vulnerability_stats": {
                        "description": "Get vulnerability statistics",
                        "parameters": {
                            "time_range": {"type": "string", "enum": ["day", "week", "month"]}
                        }
                    },
                    "list_recent_scans": {
                        "description": "List recent security scans",
                        "parameters": {
                            "limit": {"type": "integer", "default": 10}
                        }
                    }
                }
            }
        ),
        Skill(
            skill_id="system_monitor",
            name="System Monitor",
            description="Monitor and query system status (LLM can get info from software)",
            input_schema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["status", "metrics", "logs"]},
                },
                "required": ["action"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "data": {"type": "object"},
                },
            },
            category="monitoring",
            tags=["monitoring", "system", "info"],
            llm_accessible=True,
            function_definition={
                "name": "system_monitor",
                "description": "Get system status and metrics",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["status", "metrics", "logs"],
                            "description": "Type of information to retrieve"
                        }
                    },
                    "required": ["action"]
                }
            },
            info_schema={
                "provides": ["system_status", "performance_metrics", "error_logs"],
                "query_methods": {
                    "get_status": {
                        "description": "Get current system status",
                        "parameters": {}
                    },
                    "get_metrics": {
                        "description": "Get performance metrics",
                        "parameters": {
                            "metric_type": {"type": "string", "enum": ["cpu", "memory", "disk"]}
                        }
                    },
                    "get_logs": {
                        "description": "Get recent error logs",
                        "parameters": {
                            "severity": {"type": "string", "enum": ["error", "warning", "info"]},
                            "limit": {"type": "integer", "default": 50}
                        }
                    }
                }
            }
        ),
    ]

    # 定義端點（OpenAI API 相容）
    endpoints = [
        Endpoint(
            type="http",
            address="http://localhost:9001",
            protocol="openai-compatible",
            health_check_path="/health",
            timeout_ms=5000,
            api_base="/v1",  # OpenAI API base path
        ),
    ]

    # 創建 manifest（LLM 相容）
    manifest = ProviderManifest(
        manifest_version="1.0.0",
        provider_id="example-llm-cop",
        provider_name="Example LLM Copilot",
        provider_version="1.0.0",
        description="Example LLM-compatible Copilot with code analysis skills",
        vendor="Robot Command Console Team",
        homepage="https://github.com/example/llm-cop",
        endpoints=endpoints,
        skills=skills,
        capabilities=["text-generation", "code-analysis", "security-scan"],
        anti_decryption=AntiDecryptionConfig(
            no_prompt_logging=True,
            no_model_exposure=True,
            prompt_sanitization=True,
            response_filtering=True,
            memory_cleanup=True,
            timing_obfuscation=False,
        ),
        llm_compatibility={
            "api_version": "openai-v1",
            "supported_endpoints": [
                "/v1/chat/completions",
                "/v1/completions",
                "/v1/models"
            ],
            "streaming_support": True,
            "function_calling": True
        },
    )

    return manifest


def main():
    """主程式"""
    print("=== LLM Copilot Provider 註冊範例 ===\n")

    # 創建範例 manifest
    manifest = create_example_provider()

    print(f"Provider ID: {manifest.provider_id}")
    print(f"Provider Name: {manifest.provider_name}")
    print(f"Skills: {len(manifest.skills)}")
    print("\nSkills (雙向互動 - LLM Compatible):")
    for skill in manifest.skills:
        print(f"\n  📦 {skill.skill_id}: {skill.name}")
        print(f"     Category: {skill.category}")
        print(f"     Tags: {', '.join(skill.tags)}")
        
        # 顯示 LLM 可操作的功能
        if skill.function_definition:
            print(f"     ✅ LLM 可操作: {skill.function_definition['name']}")
        
        # 顯示軟體可提供的資訊
        info_providers = skill.get_info_providers()
        if info_providers:
            print(f"     📊 提供資訊: {', '.join(info_providers)}")
        
        query_methods = skill.get_query_methods()
        if query_methods:
            print(f"     🔍 查詢方法: {', '.join(query_methods.keys())}")

    print("\nLLM Compatibility:")
    if manifest.llm_compatibility:
        print(f"  - API Version: {manifest.llm_compatibility.get('api_version')}")
        print(f"  - Streaming Support: {manifest.llm_compatibility.get('streaming_support')}")
        print(f"  - Function Calling: {manifest.llm_compatibility.get('function_calling')}")
        print(f"  - Supported Endpoints: {', '.join(manifest.llm_compatibility.get('supported_endpoints', []))}")
    
    print("\nOpenAI Functions (from Skills):")
    for func in manifest.get_openai_functions():
        print(f"  - {func['name']}: {func['description']}")

    print("\nSecurity Configuration:")
    print(f"  - No Prompt Logging: {manifest.anti_decryption.no_prompt_logging}")
    print(f"  - No Model Exposure: {manifest.anti_decryption.no_model_exposure}")
    print(f"  - Prompt Sanitization: {manifest.anti_decryption.prompt_sanitization}")
    print(f"  - Response Filtering: {manifest.anti_decryption.response_filtering}")
    print(f"  - Memory Cleanup: {manifest.anti_decryption.memory_cleanup}")

    # 詢問是否要註冊
    print("\n" + "=" * 50)
    response = input("是否要註冊此 provider 到系統？ (y/N): ").strip().lower()

    if response == "y":
        scanner = FilesystemScanner()
        success = scanner.save_manifest(manifest)

        if success:
            print(f"\n✅ 成功註冊 provider: {manifest.provider_id}")
            registry_path = scanner.get_registry_path()
            print(f"   Manifest 路徑: {registry_path / f'{manifest.provider_id}.json'}")
        else:
            print("\n❌ 註冊失敗")
    else:
        print("\n取消註冊")

    # 顯示 JSON
    print("\n" + "=" * 50)
    print("Manifest JSON:")
    print(manifest.to_json())


if __name__ == "__main__":
    main()
