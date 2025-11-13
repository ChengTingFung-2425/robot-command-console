"""MQTT 客戶端管理器

提供 MQTT 連接和訊息發布功能，用於發送指令到機器人。
支援 AWS IoT Core 和標準 MQTT broker。
"""

import json
import logging
import threading
from typing import Optional, Dict, Any
from flask import current_app

logger = logging.getLogger(__name__)


class MQTTClientManager:
    """MQTT 客戶端管理器（單例模式）"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化 MQTT 客戶端管理器"""
        if self._initialized:
            return
            
        self._initialized = True
        self.client = None
        self.connected = False
        self.use_aws_iot = True  # 預設使用 AWS IoT
        
    def is_enabled(self) -> bool:
        """檢查 MQTT 是否啟用"""
        try:
            return current_app.config.get('MQTT_ENABLED', False)
        except RuntimeError:
            # 在 Flask 應用上下文外部
            return False
    
    def connect(self, robot_name: str) -> bool:
        """連接到 MQTT broker
        
        Args:
            robot_name: 機器人名稱（用於選擇正確的憑證）
            
        Returns:
            bool: 連接是否成功
        """
        if not self.is_enabled():
            logger.info("MQTT 未啟用，跳過連接")
            return False
            
        try:
            # 動態導入 AWS IoT SDK（避免在未安裝時出錯）
            try:
                from awsiot import mqtt5_client_builder
                from awscrt import mqtt5
                self.use_aws_iot = True
            except ImportError:
                logger.warning("AWS IoT SDK 未安裝，無法使用 MQTT 功能")
                return False
            
            # 從配置獲取連接參數
            broker = current_app.config.get('MQTT_BROKER')
            port = current_app.config.get('MQTT_PORT', 8883)
            cert_path = current_app.config.get('MQTT_CERT_PATH')
            ca_cert = current_app.config.get('MQTT_CA_CERT')
            
            # 構建憑證路徑
            robot_cert = f"{cert_path}/{robot_name}/{robot_name}.cert.pem"
            robot_key = f"{cert_path}/{robot_name}/{robot_name}.private.key"
            ca_file = ca_cert if '/' in ca_cert else f"{cert_path}/{ca_cert}"
            
            # 建立 AWS IoT MQTT5 客戶端
            self.client = mqtt5_client_builder.mtls_from_path(
                endpoint=broker,
                port=port,
                cert_filepath=robot_cert,
                pri_key_filepath=robot_key,
                ca_filepath=ca_file,
                client_id=f"webui-{robot_name}",
                keep_alive_interval_sec=30
            )
            
            # 啟動客戶端
            self.client.start()
            self.connected = True
            logger.info(f"MQTT 客戶端已連接到 {broker} (robot: {robot_name})")
            return True
            
        except Exception as e:
            logger.error(f"MQTT 連接失敗: {str(e)}", exc_info=True)
            self.connected = False
            return False
    
    def publish(self, topic: str, payload: Dict[str, Any], timeout: int = 5) -> bool:
        """發布訊息到指定主題
        
        Args:
            topic: MQTT 主題
            payload: 訊息內容（字典）
            timeout: 超時時間（秒）
            
        Returns:
            bool: 發布是否成功
        """
        if not self.is_enabled():
            logger.warning("MQTT 未啟用，無法發布訊息")
            return False
            
        if not self.connected or not self.client:
            logger.warning("MQTT 未連接，無法發布訊息")
            return False
        
        try:
            # 將字典轉換為 JSON 字串
            message = json.dumps(payload)
            
            # 使用 AWS IoT MQTT5
            from awscrt import mqtt5
            
            publish_packet = mqtt5.PublishPacket(
                topic=topic,
                payload=message.encode('utf-8'),
                qos=mqtt5.QoS.AT_LEAST_ONCE
            )
            
            # 發布訊息
            publish_future = self.client.publish(publish_packet)
            publish_result = publish_future.result(timeout=timeout)
            
            logger.info(f"訊息已發布到主題 {topic}: {message}")
            return True
            
        except Exception as e:
            logger.error(f"發布訊息失敗: {str(e)}", exc_info=True)
            return False
    
    def disconnect(self):
        """斷開 MQTT 連接"""
        if self.client and self.connected:
            try:
                self.client.stop()
                self.connected = False
                logger.info("MQTT 客戶端已斷開連接")
            except Exception as e:
                logger.error(f"斷開 MQTT 連接時發生錯誤: {str(e)}")


# 全局 MQTT 客戶端實例
mqtt_manager = MQTTClientManager()


def publish_to_robot(robot_name: str, payload: Dict[str, Any]) -> bool:
    """便捷函式：發布訊息到機器人
    
    Args:
        robot_name: 機器人名稱
        payload: 訊息內容
        
    Returns:
        bool: 發布是否成功
    """
    # 構建主題（格式：{robot_name}/topic）
    topic = f"{robot_name}/topic"
    
    # 如果未連接，嘗試連接
    if not mqtt_manager.connected:
        if not mqtt_manager.connect(robot_name):
            return False
    
    # 發布訊息
    return mqtt_manager.publish(topic, payload)
