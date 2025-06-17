"""
测试配置和fixtures
"""
import asyncio
import pytest
from typing import Generator, AsyncGenerator
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from fastapi.testclient import TestClient
from httpx import AsyncClient
import redis.asyncio as redis
from unittest.mock import Mock, AsyncMock

# 添加src到Python路径
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.config.settings import Settings
from src.models.base import Base
from src.core.database import get_db, get_async_db
from src.core.redis import get_redis
from src.main import app


# 测试配置
@pytest.fixture(scope="session")
def test_settings():
    """测试环境配置"""
    return Settings(
        app_env="testing",
        database_url="sqlite:///./test.db",
        redis_url="redis://localhost:6379/9",
        secret_key="test-secret-key",
        jwt_secret_key="test-jwt-secret",
        openai_api_key="test-api-key",
    )


# 数据库fixtures
@pytest.fixture(scope="session")
def engine(test_settings):
    """创建测试数据库引擎"""
    engine = create_engine(
        test_settings.database_url,
        connect_args={"check_same_thread": False} if "sqlite" in test_settings.database_url else {}
    )
    return engine


@pytest.fixture(scope="session")
def async_engine(test_settings):
    """创建异步测试数据库引擎"""
    async_db_url = test_settings.database_url.replace("sqlite:", "sqlite+aiosqlite:")
    engine = create_async_engine(
        async_db_url,
        connect_args={"check_same_thread": False} if "sqlite" in async_db_url else {}
    )
    return engine


@pytest.fixture(scope="session")
def tables(engine):
    """创建测试数据库表"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(engine, tables) -> Generator[Session, None, None]:
    """创建数据库会话"""
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
async def async_db_session(async_engine, tables) -> AsyncGenerator[AsyncSession, None]:
    """创建异步数据库会话"""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session
        await session.rollback()


# Redis fixtures
@pytest.fixture
async def redis_client(test_settings):
    """创建Redis客户端"""
    client = await redis.from_url(test_settings.redis_url, decode_responses=True)
    await client.flushdb()
    yield client
    await client.close()


# FastAPI测试客户端
@pytest.fixture
def client(db_session, test_settings) -> Generator[TestClient, None, None]:
    """创建同步测试客户端"""
    def override_get_db():
        yield db_session
    
    def override_settings():
        return test_settings
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[Settings] = override_settings
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(async_db_session, redis_client, test_settings) -> AsyncGenerator[AsyncClient, None]:
    """创建异步测试客户端"""
    async def override_get_async_db():
        yield async_db_session
    
    async def override_get_redis():
        yield redis_client
    
    def override_settings():
        return test_settings
    
    app.dependency_overrides[get_async_db] = override_get_async_db
    app.dependency_overrides[get_redis] = override_get_redis
    app.dependency_overrides[Settings] = override_settings
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


# Mock fixtures
@pytest.fixture
def mock_openai():
    """Mock OpenAI客户端"""
    mock = Mock()
    mock.chat.completions.create = AsyncMock()
    mock.chat.completions.create.return_value = Mock(
        choices=[Mock(message=Mock(content="测试生成的内容"))]
    )
    return mock


@pytest.fixture
def mock_httpx():
    """Mock HTTP客户端"""
    mock = AsyncMock()
    mock.get.return_value = Mock(
        status_code=200,
        json=lambda: {"data": "test"},
        text="test content"
    )
    mock.post.return_value = Mock(
        status_code=201,
        json=lambda: {"id": "123", "status": "success"}
    )
    return mock


# 测试数据fixtures
@pytest.fixture
def sample_user_data():
    """示例用户数据"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User"
    }


@pytest.fixture
def sample_news_data():
    """示例新闻数据"""
    return {
        "title": "OpenAI发布GPT-5",
        "content": "OpenAI今天宣布发布最新的GPT-5模型...",
        "source": "TechCrunch",
        "url": "https://example.com/news/1",
        "author": "John Doe",
        "publish_time": datetime.now(timezone.utc).isoformat(),
        "tags": ["AI", "GPT", "OpenAI"]
    }


@pytest.fixture
def sample_report_config():
    """示例报告配置"""
    return {
        "report_type": "daily",
        "template_id": "default_daily",
        "time_range": {
            "start_date": "2024-01-01",
            "end_date": "2024-01-01"
        },
        "categories": ["技术突破", "行业动态"],
        "max_items_per_section": 5
    }


@pytest.fixture
def auth_headers(client, sample_user_data):
    """获取认证headers"""
    # 创建用户
    response = client.post("/api/v1/auth/register", json=sample_user_data)
    assert response.status_code == 201
    
    # 登录获取token
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": sample_user_data["username"],
            "password": sample_user_data["password"]
        }
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


# 事件循环配置
@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()