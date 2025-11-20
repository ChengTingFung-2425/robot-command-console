"""
Queue Handler
佇列處理器，負責訊息的消費與分派
"""

import asyncio
import logging
from typing import Any, Callable, Coroutine, Dict, Optional

from .interface import Message, QueueInterface


logger = logging.getLogger(__name__)


class QueueHandler:
    """
    佇列處理器
    
    負責：
    - 從佇列消費訊息
    - 分派訊息給處理函式
    - 錯誤處理與重試
    - 優雅關閉
    """
    
    def __init__(
        self,
        queue: QueueInterface,
        processor: Callable[[Message], Coroutine[Any, Any, bool]],
        max_workers: int = 5,
        poll_interval: float = 0.1,
    ):
        """
        初始化佇列處理器
        
        Args:
            queue: 佇列實例
            processor: 訊息處理函式（async），返回 True 表示成功
            max_workers: 最大並行工作數
            poll_interval: 輪詢間隔（秒）
        """
        self.queue = queue
        self.processor = processor
        self.max_workers = max_workers
        self.poll_interval = poll_interval
        self._running = False
        self._workers: list[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        
        logger.info("QueueHandler initialized", extra={
            "max_workers": max_workers,
            "poll_interval": poll_interval,
            "service": "robot_service.queue"
        })
    
    async def start(self) -> None:
        """啟動處理器"""
        if self._running:
            logger.warning("QueueHandler already running", extra={
                "service": "robot_service.queue"
            })
            return
        
        self._running = True
        self._shutdown_event.clear()
        
        # 啟動工作協程
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)
        
        logger.info("QueueHandler started", extra={
            "worker_count": len(self._workers),
            "service": "robot_service.queue"
        })
    
    async def stop(self, timeout: Optional[float] = 30.0) -> None:
        """
        停止處理器
        
        Args:
            timeout: 等待工作完成的逾時（秒）
        """
        if not self._running:
            return
        
        logger.info("QueueHandler stopping", extra={
            "service": "robot_service.queue"
        })
        
        self._running = False
        self._shutdown_event.set()
        
        # 等待所有工作完成
        if self._workers:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._workers, return_exceptions=True),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.warning("QueueHandler stop timeout, cancelling workers", extra={
                    "service": "robot_service.queue"
                })
                for worker in self._workers:
                    worker.cancel()
        
        self._workers.clear()
        
        logger.info("QueueHandler stopped", extra={
            "service": "robot_service.queue"
        })
    
    async def _worker(self, worker_id: int) -> None:
        """
        工作協程
        
        Args:
            worker_id: 工作 ID
        """
        logger.info("Worker started", extra={
            "worker_id": worker_id,
            "service": "robot_service.queue"
        })
        
        while self._running:
            try:
                # 從佇列取出訊息（等待最多 poll_interval 秒）
                message = await self.queue.dequeue(timeout=self.poll_interval)
                
                if message is None:
                    # 逾時，繼續下一次迴圈
                    continue
                
                # 處理訊息
                try:
                    success = await self.processor(message)
                    
                    if success:
                        await self.queue.ack(message.id)
                        logger.info("Message processed successfully", extra={
                            "worker_id": worker_id,
                            "message_id": message.id,
                            "trace_id": message.trace_id,
                            "service": "robot_service.queue"
                        })
                    else:
                        await self.queue.nack(message.id, requeue=True)
                        logger.warning("Message processing failed", extra={
                            "worker_id": worker_id,
                            "message_id": message.id,
                            "trace_id": message.trace_id,
                            "service": "robot_service.queue"
                        })
                
                except Exception as e:
                    logger.error("Error processing message", extra={
                        "worker_id": worker_id,
                        "message_id": message.id,
                        "trace_id": message.trace_id,
                        "error": str(e),
                        "service": "robot_service.queue"
                    }, exc_info=True)
                    
                    await self.queue.nack(message.id, requeue=True)
            
            except asyncio.CancelledError:
                logger.info("Worker cancelled", extra={
                    "worker_id": worker_id,
                    "service": "robot_service.queue"
                })
                break
            
            except Exception as e:
                logger.error("Worker error", extra={
                    "worker_id": worker_id,
                    "error": str(e),
                    "service": "robot_service.queue"
                }, exc_info=True)
                
                # 錯誤後短暫休眠避免忙碌迴圈
                await asyncio.sleep(1.0)
        
        logger.info("Worker stopped", extra={
            "worker_id": worker_id,
            "service": "robot_service.queue"
        })
    
    async def health_check(self) -> Dict[str, Any]:
        """健康檢查"""
        queue_health = await self.queue.health_check()
        
        return {
            "status": "healthy" if self._running else "stopped",
            "running": self._running,
            "worker_count": len(self._workers),
            "max_workers": self.max_workers,
            "queue": queue_health,
        }
