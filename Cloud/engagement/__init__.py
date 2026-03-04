"""
Engagement Module - 社群互動模組

包含討論區、評論、點讚、排行榜等社群功能。

主要元件：
- models.py: SQLAlchemy 資料模型（Post, PostComment, PostLike, UserEngagementProfile, PointsLog）
- database.py: 資料庫初始化與 session 管理
- service.py: 業務邏輯（EngagementService）
- api.py: Flask Blueprint REST API 端點
- engagement.py: 積分獎勵便利函式
"""
