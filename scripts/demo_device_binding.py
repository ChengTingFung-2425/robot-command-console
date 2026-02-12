#!/usr/bin/env python3
"""
裝置綁定示範腳本

展示如何使用 DeviceBindingClient 將 Edge 裝置綁定到雲端帳號。
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.edge_app.auth.device_binding import DeviceBindingClient


def main():
    print("=" * 60)
    print("雲端帳號與裝置綁定示範")
    print("=" * 60)
    print()

    # Initialize client
    cloud_api_url = os.getenv('CLOUD_API_URL', 'http://localhost:5000')
    client = DeviceBindingClient(cloud_api_url=cloud_api_url)

    # Step 1: Get device ID
    print("步驟 1: 取得裝置 ID")
    print("-" * 60)
    device_id = client.get_device_id()
    print(f"裝置 ID: {device_id}")
    print()

    # Step 2: Get device metadata
    print("步驟 2: 收集裝置資訊")
    print("-" * 60)
    metadata = client.get_device_metadata()
    print(f"平台: {metadata['platform']}")
    print(f"主機名稱: {metadata['hostname']}")
    print(f"裝置類型: {metadata['device_type']}")
    print()

    # Step 3: Simulate user login and get access token
    print("步驟 3: 使用者登入（模擬）")
    print("-" * 60)
    print("提示：在實際應用中，這裡會引導使用者登入")
    print("並從 /api/auth/login 端點獲取 access_token")
    print()

    # For demo purposes, we'll assume a token
    access_token = os.getenv('ACCESS_TOKEN', None)

    if not access_token:
        print("⚠️  未提供 ACCESS_TOKEN 環境變數")
        print("請先執行以下命令登入並獲取 token：")
        print()
        print("  curl -X POST http://localhost:5000/api/auth/login \\")
        print("    -H 'Content-Type: application/json' \\")
        print("    -d '{\"username\": \"your_username\", \"password\": \"your_password\"}'")
        print()
        print("然後執行：")
        print("  export ACCESS_TOKEN=<your_access_token>")
        print()
        return

    # Step 4: Auto-register device
    print("步驟 4: 自動註冊裝置")
    print("-" * 60)
    try:
        device_name = os.getenv('DEVICE_NAME', f"{metadata['hostname']} ({metadata['platform']})")
        result = client.auto_register_if_needed(access_token, device_name=device_name)

        if result.get('already_bound'):
            print("✓ 裝置已綁定到此帳號")
        else:
            print("✓ 裝置成功註冊並綁定")
            print(f"  裝置名稱: {result['device']['device_name']}")
            print(f"  裝置平台: {result['device']['platform']}")

        print()
    except Exception as e:
        print(f"✗ 裝置註冊失敗: {e}")
        return

    # Step 5: List all devices
    print("步驟 5: 列出所有綁定裝置")
    print("-" * 60)
    try:
        devices_response = client.list_devices(access_token, active_only=True)
        devices = devices_response.get('devices', [])

        print(f"共 {len(devices)} 台活躍裝置：")
        for idx, device in enumerate(devices, 1):
            is_current = device['device_id'] == device_id
            marker = "→" if is_current else " "
            print(f"{marker} {idx}. {device['device_name']}")
            print(f"    ID: {device['device_id'][:16]}...")
            print(f"    平台: {device['platform']}")
            print(f"    最後連線: {device['last_seen_at']}")

        print()
    except Exception as e:
        print(f"✗ 列出裝置失敗: {e}")
        return

    # Step 6: Verify device bound
    print("步驟 6: 驗證裝置綁定狀態")
    print("-" * 60)
    try:
        is_bound = client.verify_device_bound(access_token)
        if is_bound:
            print("✓ 當前裝置已綁定且為活躍狀態")
        else:
            print("✗ 當前裝置未綁定")
        print()
    except Exception as e:
        print(f"✗ 驗證失敗: {e}")

    print("=" * 60)
    print("示範完成！")
    print()
    print("下一步：")
    print("- 在 Edge App 中整合此流程")
    print("- 建立 WebUI 裝置管理頁面")
    print("- 實作離線模式下的裝置驗證")
    print("=" * 60)


if __name__ == '__main__':
    main()
