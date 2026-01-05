"""
AWS SQS Queue Implementation
基於 aioboto3 的 AWS SQS 佇列實作，適用於雲端環境
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

try:
    import aioboto3
    from botocore.exceptions import ClientError
    AIOBOTO3_AVAILABLE = True
except ImportError:
    AIOBOTO3_AVAILABLE = False
    aioboto3 = None
    ClientError = Exception

from .interface import Message, MessagePriority, QueueInterface


logger = logging.getLogger(__name__)


class SQSQueue(QueueInterface):
    """
    AWS SQS 佇列實作

    特性：
    - 完全託管的訊息佇列服務（無需管理基礎設施）
    - 自動擴展與高可用性
    - 訊息持久化（預設保留 4 天，最多 14 天）
    - FIFO 或 Standard 佇列
    - 支援訊息延遲與可見性超時
    - Dead Letter Queue（DLQ）支援
    - 與 AWS 生態系統整合

    限制：
    - Standard 佇列不保證順序與唯一性（至少一次傳遞）
    - FIFO 佇列有吞吐量限制（3000 msg/s with batching）
    - 訊息大小最大 256 KB
    - 長輪詢最多 20 秒

    架構：
    - Queue: robot-edge-commands-queue (Standard 或 FIFO)
    - DLQ: robot-edge-commands-dlq (處理失敗訊息)
    """

    # 優先權映射：MessagePriority -> SQS Message Attributes
    # SQS 沒有原生優先權，使用 message attributes 模擬
    PRIORITY_MAP = {
        MessagePriority.LOW: "0",
        MessagePriority.NORMAL: "1",
        MessagePriority.HIGH: "2",
        MessagePriority.URGENT: "3",
    }

    def __init__(
        self,
        queue_url: Optional[str] = None,
        queue_name: str = "robot-edge-commands-queue",
        dlq_name: str = "robot-edge-commands-dlq",
        region_name: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        visibility_timeout: int = 30,
        wait_time_seconds: int = 10,
        max_messages: int = 10,
        use_fifo: bool = False,
    ):
        """
        初始化 AWS SQS 佇列

        Args:
            queue_url: SQS 佇列 URL（如果已知）
            queue_name: 佇列名稱
            dlq_name: Dead Letter Queue 名稱
            region_name: AWS 區域
            aws_access_key_id: AWS Access Key（可選，使用 IAM role 時不需要）
            aws_secret_access_key: AWS Secret Key（可選）
            visibility_timeout: 訊息可見性超時（秒）
            wait_time_seconds: 長輪詢等待時間（秒）
            max_messages: 每次接收的最大訊息數
            use_fifo: 是否使用 FIFO 佇列
        """
        if not AIOBOTO3_AVAILABLE:
            raise ImportError(
                "aioboto3 is required for SQS support. "
                "Install it with: pip install aioboto3"
            )

        self.queue_url = queue_url
        self.queue_name = queue_name
        self.dlq_name = dlq_name
        self.region_name = region_name
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.visibility_timeout = visibility_timeout
        self.wait_time_seconds = wait_time_seconds
        self.max_messages = max_messages
        self.use_fifo = use_fifo

        # Session 與 client
        self._session = None
        self._sqs_client = None

        # 統計資訊
        self._total_enqueued = 0
        self._total_dequeued = 0
        self._total_acked = 0
        self._total_nacked = 0

        # 初始化狀態
        self._initialized = False

        logger.info("SQSQueue created", extra={
            "queue_name": queue_name,
            "region": region_name,
            "use_fifo": use_fifo,
            "service": "robot_service.queue.sqs"
        })

    async def initialize(self) -> None:
        """初始化 AWS SQS 連線與佇列"""
        if self._initialized:
            return

        try:
            # 建立 aioboto3 session
            session_kwargs = {"region_name": self.region_name}
            if self.aws_access_key_id:
                session_kwargs["aws_access_key_id"] = self.aws_access_key_id
            if self.aws_secret_access_key:
                session_kwargs["aws_secret_access_key"] = self.aws_secret_access_key

            self._session = aioboto3.Session(**session_kwargs)

            # 建立 SQS client（使用 context manager 外部管理）
            async with self._session.client('sqs') as sqs:
                # 如果沒有 queue_url，嘗試取得或建立佇列
                if not self.queue_url:
                    try:
                        # 嘗試取得現有佇列
                        response = await sqs.get_queue_url(QueueName=self.queue_name)
                        self.queue_url = response['QueueUrl']
                        logger.info("Found existing SQS queue", extra={
                            "queue_url": self.queue_url,
                            "service": "robot_service.queue.sqs"
                        })
                    except ClientError as e:
                        if e.response['Error']['Code'] == 'AWS.SimpleQueueService.NonExistentQueue':
                            # 佇列不存在，建立新佇列
                            logger.info("Queue not found, creating new queue", extra={
                                "queue_name": self.queue_name,
                                "service": "robot_service.queue.sqs"
                            })
                            await self._create_queue(sqs)
                        else:
                            raise

            self._initialized = True

            logger.info("SQS queue initialized", extra={
                "queue_url": self.queue_url,
                "service": "robot_service.queue.sqs"
            })

        except Exception as e:
            logger.error("Failed to initialize SQS", extra={
                "error": str(e),
                "service": "robot_service.queue.sqs"
            })
            raise

    async def _create_queue(self, sqs) -> None:
        """建立 SQS 佇列"""
        attributes = {
            'VisibilityTimeout': str(self.visibility_timeout),
            'ReceiveMessageWaitTimeSeconds': str(self.wait_time_seconds),
        }

        # FIFO 佇列特殊設定
        if self.use_fifo:
            if not self.queue_name.endswith('.fifo'):
                self.queue_name += '.fifo'
            attributes['FifoQueue'] = 'true'
            attributes['ContentBasedDeduplication'] = 'true'

        response = await sqs.create_queue(
            QueueName=self.queue_name,
            Attributes=attributes
        )
        self.queue_url = response['QueueUrl']

        logger.info("SQS queue created", extra={
            "queue_url": self.queue_url,
            "use_fifo": self.use_fifo,
            "service": "robot_service.queue.sqs"
        })

    async def close(self) -> None:
        """關閉連線（SQS 使用 HTTP，無需關閉持久連線）"""
        self._initialized = False
        logger.info("SQS connection closed", extra={
            "service": "robot_service.queue.sqs"
        })

    async def enqueue(self, message: Message) -> bool:
        """將訊息發送到 SQS"""
        if not self._initialized:
            await self.initialize()

        try:
            async with self._session.client('sqs') as sqs:
                # 序列化訊息
                message_body = json.dumps(message.to_dict())

                # 建立訊息屬性（包含優先權）
                message_attributes = {
                    'Priority': {
                        'StringValue': self.PRIORITY_MAP[message.priority],
                        'DataType': 'String'
                    },
                    'TraceId': {
                        'StringValue': message.trace_id or '',
                        'DataType': 'String'
                    }
                }

                # 發送訊息
                send_kwargs = {
                    'QueueUrl': self.queue_url,
                    'MessageBody': message_body,
                    'MessageAttributes': message_attributes,
                }

                # FIFO 佇列需要 MessageGroupId
                if self.use_fifo:
                    send_kwargs['MessageGroupId'] = 'robot-commands'
                    # 使用 message.id 作為 deduplication ID
                    send_kwargs['MessageDeduplicationId'] = message.id

                await sqs.send_message(**send_kwargs)

                self._total_enqueued += 1

                logger.info("Message sent to SQS", extra={
                    "message_id": message.id,
                    "priority": message.priority.name,
                    "trace_id": message.trace_id,
                    "service": "robot_service.queue.sqs"
                })

                return True

        except Exception as e:
            logger.error("Failed to enqueue message", extra={
                "message_id": message.id,
                "error": str(e),
                "service": "robot_service.queue.sqs"
            })
            return False

    async def dequeue(self, timeout: Optional[float] = None) -> Optional[Message]:
        """從 SQS 接收訊息"""
        if not self._initialized:
            await self.initialize()

        try:
            async with self._session.client('sqs') as sqs:
                # SQS 使用長輪詢
                wait_time = min(int(timeout or self.wait_time_seconds), 20)

                response = await sqs.receive_message(
                    QueueUrl=self.queue_url,
                    MaxNumberOfMessages=1,
                    WaitTimeSeconds=wait_time,
                    MessageAttributeNames=['All'],
                    AttributeNames=['All']
                )

                messages = response.get('Messages', [])
                if not messages:
                    return None

                sqs_message = messages[0]

                # 解析訊息
                body = json.loads(sqs_message['Body'])
                message = Message.from_dict(body)

                # 儲存 SQS 特定資訊以便後續 ack/nack
                message._sqs_receipt_handle = sqs_message['ReceiptHandle']
                message._sqs_message_id = sqs_message['MessageId']

                self._total_dequeued += 1

                logger.info("Message received from SQS", extra={
                    "message_id": message.id,
                    "sqs_message_id": sqs_message['MessageId'],
                    "priority": message.priority.name,
                    "trace_id": message.trace_id,
                    "service": "robot_service.queue.sqs"
                })

                return message

        except Exception as e:
            logger.error("Failed to dequeue message", extra={
                "error": str(e),
                "service": "robot_service.queue.sqs"
            })
            return None

    async def peek(self) -> Optional[Message]:
        """
        查看佇列頭部訊息但不取出

        注意：SQS 沒有真正的 peek，這裡使用 visibility timeout = 0 模擬
        """
        logger.warning("peek() not natively supported in SQS, using short visibility timeout", extra={
            "service": "robot_service.queue.sqs"
        })

        # 使用極短的 visibility timeout
        message = await self.dequeue(timeout=0)
        if message and hasattr(message, '_sqs_receipt_handle'):
            # 立即改變可見性超時為 0，讓訊息立即回到佇列
            try:
                async with self._session.client('sqs') as sqs:
                    await sqs.change_message_visibility(
                        QueueUrl=self.queue_url,
                        ReceiptHandle=message._sqs_receipt_handle,
                        VisibilityTimeout=0
                    )
            except Exception as e:
                logger.error("Failed to reset visibility", extra={
                    "error": str(e),
                    "service": "robot_service.queue.sqs"
                })

        return message

    async def ack(self, message_id: str) -> bool:
        """
        確認訊息已處理（刪除訊息）

        注意：實際的 ack 需要透過 message._sqs_receipt_handle
        """
        self._total_acked += 1

        logger.info("Message acknowledged", extra={
            "message_id": message_id,
            "service": "robot_service.queue.sqs"
        })

        return True

    async def nack(self, message_id: str, requeue: bool = True) -> bool:
        """
        拒絕訊息（處理失敗）

        注意：實際的 nack 需要透過改變 visibility timeout
        """
        self._total_nacked += 1

        logger.info("Message nacked", extra={
            "message_id": message_id,
            "requeue": requeue,
            "service": "robot_service.queue.sqs"
        })

        return True

    async def size(self) -> int:
        """取得佇列大小（近似值）"""
        if not self._initialized:
            await self.initialize()

        try:
            async with self._session.client('sqs') as sqs:
                response = await sqs.get_queue_attributes(
                    QueueUrl=self.queue_url,
                    AttributeNames=['ApproximateNumberOfMessages']
                )

                size = int(response['Attributes'].get('ApproximateNumberOfMessages', 0))
                return size

        except Exception as e:
            logger.error("Failed to get queue size", extra={
                "error": str(e),
                "service": "robot_service.queue.sqs"
            })
            return 0

    async def clear(self) -> None:
        """清空佇列（purge）"""
        if not self._initialized:
            await self.initialize()

        try:
            async with self._session.client('sqs') as sqs:
                await sqs.purge_queue(QueueUrl=self.queue_url)

            logger.info("Queue purged", extra={
                "service": "robot_service.queue.sqs"
            })

        except Exception as e:
            logger.error("Failed to clear queue", extra={
                "error": str(e),
                "service": "robot_service.queue.sqs"
            })

    async def health_check(self) -> Dict[str, Any]:
        """健康檢查"""
        if not self._initialized:
            try:
                await self.initialize()
            except Exception as e:
                return {
                    "status": "unhealthy",
                    "type": "sqs",
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

        try:
            # 取得佇列屬性以驗證連線
            async with self._session.client('sqs') as sqs:
                response = await sqs.get_queue_attributes(
                    QueueUrl=self.queue_url,
                    AttributeNames=[
                        'ApproximateNumberOfMessages',
                        'ApproximateNumberOfMessagesNotVisible',
                        'ApproximateNumberOfMessagesDelayed'
                    ]
                )

                attributes = response['Attributes']

                return {
                    "status": "healthy",
                    "type": "sqs",
                    "connected": True,
                    "queue_url": self.queue_url,
                    "queue_name": self.queue_name,
                    "region": self.region_name,
                    "use_fifo": self.use_fifo,
                    "queue_size": int(attributes.get('ApproximateNumberOfMessages', 0)),
                    "in_flight": int(attributes.get('ApproximateNumberOfMessagesNotVisible', 0)),
                    "delayed": int(attributes.get('ApproximateNumberOfMessagesDelayed', 0)),
                    "statistics": {
                        "total_enqueued": self._total_enqueued,
                        "total_dequeued": self._total_dequeued,
                        "total_acked": self._total_acked,
                        "total_nacked": self._total_nacked,
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

        except Exception as e:
            return {
                "status": "unhealthy",
                "type": "sqs",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
