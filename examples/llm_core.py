#!/usr/bin/env python3
"""
LLM Discovery Core 範例

展示如何使用 DiscoveryService 發現和管理 LLM Copilot 實例
"""

import sys
import asyncio
from pathlib import Path

# 添加專案路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from llm_discovery import DiscoveryService


async def main():
    """主程式"""
    print("=== LLM Copilot Discovery Core ===\n")

    # 初始化發現服務
    discovery = DiscoveryService()

    # 1. 掃描所有提供商
    print("步驟 1: 掃描註冊的提供商...")
    providers = await discovery.scan_providers()

    if not providers:
        print("❌ 未發現任何提供商")
        print("\n提示：請先執行 examples/provider.py 註冊範例提供商")
        return

    print(f"✅ 發現 {len(providers)} 個提供商\n")

    # 2. 顯示提供商資訊
    print("步驟 2: 提供商詳細資訊")
    print("-" * 60)
    for manifest in providers:
        print(f"\n📦 {manifest.provider_name} (ID: {manifest.provider_id})")
        print(f"   版本: {manifest.provider_version}")
        print(f"   描述: {manifest.description or 'N/A'}")
        print(f"   端點數量: {len(manifest.endpoints)}")
        print(f"   技能數量: {len(manifest.skills)}")

        # 顯示端點
        print(f"   端點:")
        for ep in manifest.endpoints:
            print(f"     - {ep.type}: {ep.address}")

        # 顯示技能
        if manifest.skills:
            print(f"   技能:")
            for skill in manifest.skills:
                print(f"     - {skill.skill_id}: {skill.name}")
                print(f"       類別: {skill.category}, 標籤: {', '.join(skill.tags)}")

        # 顯示安全配置
        print(f"   安全配置:")
        print(f"     - 禁止 Prompt 日誌: {manifest.anti_decryption.no_prompt_logging}")
        print(f"     - 禁止模型暴露: {manifest.anti_decryption.no_model_exposure}")

    # 3. 檢查健康狀態
    print("\n" + "=" * 60)
    print("步驟 3: 檢查提供商健康狀態...")
    print("-" * 60)

    health_results = await discovery.check_all_health()

    for provider_id, health in health_results.items():
        status_emoji = "✅" if health.status == "available" else "❌"
        print(f"\n{status_emoji} {provider_id}")
        print(f"   狀態: {health.status}")
        print(f"   響應時間: {health.response_time_ms:.2f} ms")
        print(f"   最後檢查: {health.last_check.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   可用端點: {len(health.available_endpoints)}")

        if health.error_message:
            print(f"   錯誤訊息: {health.error_message}")

        if health.available_endpoints:
            for endpoint in health.available_endpoints:
                print(f"     - {endpoint}")

    # 4. 獲取可用提供商
    print("\n" + "=" * 60)
    print("步驟 4: 列出可用提供商...")
    available = await discovery.get_available_providers()

    if available:
        print(f"✅ {len(available)} 個提供商可用:")
        for provider_id in available:
            print(f"   - {provider_id}")
    else:
        print("⚠️  目前無可用提供商（請確保提供商服務正在運行）")

    # 5. 搜尋技能
    print("\n" + "=" * 60)
    print("步驟 5: 搜尋技能...")
    print("-" * 60)

    # 搜尋所有技能
    all_skills = await discovery.search_skills()
    print(f"\n總共 {len(all_skills)} 個技能:")
    for provider_id, skill in all_skills:
        print(f"   - [{provider_id}] {skill.skill_id}: {skill.name}")

    # 按類別搜尋
    print("\n按類別搜尋 (category='security'):")
    security_skills = await discovery.search_skills(category="security")
    for provider_id, skill in security_skills:
        print(f"   - [{provider_id}] {skill.skill_id}: {skill.name}")

    # 按關鍵字搜尋
    print("\n按關鍵字搜尋 (keyword='code'):")
    code_skills = await discovery.search_skills(keyword="code")
    for provider_id, skill in code_skills:
        print(f"   - [{provider_id}] {skill.skill_id}: {skill.name}")

    # 6. 查詢資訊提供者（軟體→LLM）
    print("\n" + "=" * 60)
    print("步驟 6: 查詢可提供資訊的 Skills（軟體→LLM）...")
    print("-" * 60)

    info_providers = await discovery.get_available_info_providers()
    
    if info_providers:
        print(f"\n發現 {len(info_providers)} 個提供商可提供資訊:")
        for provider_id, info_types in info_providers.items():
            print(f"\n📊 {provider_id}")
            print(f"   可提供資訊類型: {', '.join(info_types)}")
            
            # 顯示每個 skill 的查詢方法
            manifest = discovery._providers.get(provider_id)
            if manifest:
                for skill in manifest.skills:
                    query_methods = skill.get_query_methods()
                    if query_methods:
                        print(f"\n   Skill: {skill.skill_id}")
                        for method_name, method_info in query_methods.items():
                            print(f"     - {method_name}: {method_info.get('description', 'N/A')}")
    else:
        print("未發現可提供資訊的 Skills")

    # 7. 顯示統計資訊
    print("\n" + "=" * 60)
    print("統計資訊:")
    print("-" * 60)

    total_providers = len(providers)
    total_skills = sum(len(m.skills) for m in providers)
    total_endpoints = sum(len(m.endpoints) for m in providers)
    available_count = len(available)

    print(f"   總提供商: {total_providers}")
    print(f"   可用提供商: {available_count}")
    print(f"   總技能: {total_skills}")
    print(f"   總端點: {total_endpoints}")

    # 按類別統計技能
    category_counts = {}
    for _, skill in all_skills:
        cat = skill.category or "uncategorized"
        category_counts[cat] = category_counts.get(cat, 0) + 1

    if category_counts:
        print(f"\n   技能分類:")
        for category, count in sorted(category_counts.items()):
            print(f"     - {category}: {count}")

    print("\n" + "=" * 60)
    print("✨ 發現完成！")


if __name__ == "__main__":
    asyncio.run(main())
