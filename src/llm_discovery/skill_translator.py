"""
Skills 格式轉換器

在不同格式間轉換 skills：
- Project Skill → OpenAI Function Definition
- Function Call → Project Skill Invocation
- Result → Function Response
"""

import logging
from typing import Dict, Any, List, Optional

from .models import Skill

logger = logging.getLogger(__name__)


class SkillTranslator:
    """
    Skills 轉換器

    在不同格式間轉換 skills：
    - Project Skill (internal format) → OpenAI Function Definition
    - OpenAI Function Call → Project Skill Invocation
    - Skill Result → OpenAI Function Response
    """

    @staticmethod
    def skill_to_openai_function(skill: Skill, provider_id: str, provider_name: str) -> Dict[str, Any]:
        """
        將 Skill 轉換為 OpenAI function definition

        Args:
            skill: Skill 物件
            provider_id: Provider ID
            provider_name: Provider 名稱

        Returns:
            OpenAI function definition
        """
        function_def = {
            "name": skill.skill_id,
            "description": skill.description,
            "parameters": skill.parameters,
        }

        # 附加內部使用的 metadata
        function_def["_provider_id"] = provider_id
        function_def["_provider_name"] = provider_name
        function_def["_skill_version"] = skill.version if hasattr(skill, 'version') else "1.0.0"

        logger.debug(f"轉換 Skill 為 OpenAI function: {skill.skill_id}")

        return function_def

    @staticmethod
    def openai_function_to_skill_call(function_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        將 OpenAI function call 轉換為 Skill 調用格式

        Args:
            function_call: OpenAI function call
                {
                    "name": "robot_command",
                    "arguments": "{\"robot_id\": \"robot-001\", \"action\": \"go_forward\"}"
                }

        Returns:
            Skill 調用格式
                {
                    "skill_id": "robot_command",
                    "parameters": {"robot_id": "robot-001", "action": "go_forward"}
                }
        """
        import json

        skill_id = function_call.get("name")

        # arguments 可能是字串或字典
        arguments = function_call.get("arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                logger.warning(f"無法解析 arguments: {arguments}")
                arguments = {}

        return {
            "skill_id": skill_id,
            "parameters": arguments
        }

    @staticmethod
    def skill_result_to_openai_response(
        result: Dict[str, Any],
        function_name: str
    ) -> Dict[str, Any]:
        """
        將 Skill 執行結果轉換為 OpenAI function response

        Args:
            result: Skill 執行結果
                {
                    "success": true,
                    "result": {...},
                    "error": null
                }
            function_name: Function 名稱

        Returns:
            OpenAI function response
                {
                    "role": "function",
                    "name": "robot_command",
                    "content": "{\"status\": \"success\", ...}"
                }
        """
        import json

        # 構建回應內容
        if result.get("success"):
            content = {
                "status": "success",
                "data": result.get("result")
            }
        else:
            content = {
                "status": "error",
                "error": result.get("error"),
                "data": None
            }

        return {
            "role": "function",
            "name": function_name,
            "content": json.dumps(content, ensure_ascii=False)
        }

    @staticmethod
    def validate_skill_parameters(
        parameters: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        驗證 Skill 參數是否符合 schema

        Args:
            parameters: 參數
            schema: JSON Schema

        Returns:
            (是否有效, 錯誤訊息)
        """
        try:
            import jsonschema
            jsonschema.validate(instance=parameters, schema=schema)
            return True, None
        except ImportError:
            logger.warning("jsonschema 未安裝，跳過參數驗證")
            return True, None
        except jsonschema.ValidationError as e:
            return False, f"Parameter validation failed: {e.message}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    @staticmethod
    def normalize_skill_parameters(parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        標準化 Skill 參數（清理和轉換）

        Args:
            parameters: 原始參數

        Returns:
            標準化後的參數
        """
        normalized = {}

        for key, value in parameters.items():
            # 移除空值（保留 False 和 0）
            if value is None:
                continue

            # 清理字串（去除前後空格）
            if isinstance(value, str):
                value = value.strip()
                if not value:  # 空字串也移除
                    continue

            # 遞迴處理巢狀字典
            if isinstance(value, dict):
                value = SkillTranslator.normalize_skill_parameters(value)

            # 處理列表
            elif isinstance(value, list):
                value = [
                    SkillTranslator.normalize_skill_parameters(item) if isinstance(item, dict) else item
                    for item in value
                ]

            normalized[key] = value

        return normalized

    @staticmethod
    def extract_provider_from_function(function_def: Dict[str, Any]) -> Optional[str]:
        """
        從 function definition 中提取 provider ID

        Args:
            function_def: Function definition

        Returns:
            Provider ID 或 None
        """
        return function_def.get("_provider_id")

    @staticmethod
    def batch_convert_skills_to_functions(
        skills_by_provider: Dict[str, List[Skill]],
        provider_names: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        批次轉換 Skills 為 OpenAI functions

        Args:
            skills_by_provider: provider_id -> [skills] 的字典
            provider_names: provider_id -> provider_name 的字典

        Returns:
            OpenAI function definitions 列表
        """
        functions = []

        for provider_id, skills in skills_by_provider.items():
            provider_name = provider_names.get(provider_id, provider_id)

            for skill in skills:
                function_def = SkillTranslator.skill_to_openai_function(
                    skill=skill,
                    provider_id=provider_id,
                    provider_name=provider_name
                )
                functions.append(function_def)

        logger.info(f"批次轉換 {len(functions)} 個 Skills 為 OpenAI functions")

        return functions
