#!/usr/bin/env python3
"""
MCP 服務啟動腳本
"""

import logging
import os
import sys

# 設定 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn

from MCP.api import app
from MCP.config import MCPConfig


def main():
    """主函式"""
    # 設定日誌
    logging.basicConfig(
        level=MCPConfig.LOG_LEVEL,
        format=MCPConfig.LOG_FORMAT
    )

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("MCP 服務啟動")
    logger.info("=" * 60)
    logger.info(f"Host: {MCPConfig.API_HOST}")
    logger.info(f"Port: {MCPConfig.API_PORT}")
    logger.info(f"Log Level: {MCPConfig.LOG_LEVEL}")
    logger.info("=" * 60)

    # 啟動服務
    uvicorn.run(
        app,
        host=MCPConfig.API_HOST,
        port=MCPConfig.API_PORT,
        log_level=MCPConfig.LOG_LEVEL.lower(),
        access_log=True
    )


if __name__ == "__main__":
    main()
