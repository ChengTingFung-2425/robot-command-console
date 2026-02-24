# imports
import logging
from contextlib import contextmanager
from typing import Optional, Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.pool import StaticPool

from Cloud.shared_commands.models import Base

logger = logging.getLogger(__name__)

# 全域引擎和 session factory
_engine = None
_session_factory = None


def init_db(database_url: str, echo: bool = False, create_tables: bool = True):
    """初始化資料庫引擎和 session factory
    
    Args:
        database_url: 資料庫 URL (例如: sqlite:///path/to/db.sqlite 或 postgresql://...)
        echo: 是否輸出 SQL 語句 (開發用)
        create_tables: 是否自動建立資料表
        
    Example:
        >>> init_db('sqlite:///cloud_commands.db')
        >>> init_db('postgresql://user:pass@localhost/commands')
    """
    global _engine, _session_factory
    
    # 建立引擎
    if database_url.startswith('sqlite:///:memory:'):
        # In-memory SQLite 需要特殊配置
        _engine = create_engine(
            database_url,
            connect_args={'check_same_thread': False},
            poolclass=StaticPool,
            echo=echo
        )
    else:
        _engine = create_engine(database_url, echo=echo)
    
    # 建立 session factory (使用 scoped_session 支援多執行緒)
    _session_factory = scoped_session(sessionmaker(
        bind=_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False
    ))
    
    # 建立資料表
    if create_tables:
        Base.metadata.create_all(_engine)
        logger.info(f"Database initialized with URL: {database_url}")
    
    return _engine


def get_db_session() -> Session:
    """取得資料庫 session
    
    Returns:
        SQLAlchemy Session 實例
        
    Raises:
        RuntimeError: 如果資料庫尚未初始化
        
    Note:
        建議使用 session_scope() context manager 而非直接呼叫此函數
    """
    if _session_factory is None:
        raise RuntimeError(
            "Database not initialized. Call init_db() first."
        )
    return _session_factory()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """提供資料庫 session 的 context manager
    
    自動處理 commit、rollback 和 close。
    
    Yields:
        SQLAlchemy Session
        
    Example:
        >>> with session_scope() as session:
        ...     service = SharedCommandService(session)
        ...     result = service.upload_command(...)
    """
    session = get_db_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def close_db():
    """關閉資料庫連接
    
    清理所有 session 和引擎連接。應在應用程式關閉時呼叫。
    """
    global _engine, _session_factory
    
    if _session_factory is not None:
        _session_factory.remove()
        _session_factory = None
    
    if _engine is not None:
        _engine.dispose()
        _engine = None
        logger.info("Database connections closed")


def get_engine():
    """取得資料庫引擎
    
    Returns:
        SQLAlchemy Engine 實例或 None
    """
    return _engine


def is_initialized() -> bool:
    """檢查資料庫是否已初始化
    
    Returns:
        True 如果資料庫已初始化，否則 False
    """
    return _engine is not None and _session_factory is not None
