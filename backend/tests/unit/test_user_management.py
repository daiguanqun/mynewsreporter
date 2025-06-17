"""
用户管理模块单元测试
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
from jose import jwt

from src.modules.user_management.auth import AuthService
from src.modules.user_management.user_service import UserService
from src.modules.user_management.subscription_service import SubscriptionService
from src.models.schemas import UserCreate, UserLogin, User, Subscription
from src.core.security import get_password_hash, verify_password


class TestAuthService:
    """认证服务测试"""
    
    @pytest.fixture
    def auth_service(self):
        """创建认证服务实例"""
        return AuthService(secret_key="test-secret", algorithm="HS256")
    
    @pytest.fixture
    def sample_user(self):
        """示例用户"""
        return User(
            id="user_123",
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_superuser=False,
            created_at=datetime.now(timezone.utc)
        )
    
    def test_create_access_token(self, auth_service):
        """测试创建访问令牌"""
        user_id = "user_123"
        token = auth_service.create_access_token(user_id)
        
        assert token is not None
        # 解码验证
        payload = jwt.decode(token, "test-secret", algorithms=["HS256"])
        assert payload["sub"] == user_id
        assert "exp" in payload
    
    def test_verify_token(self, auth_service):
        """测试验证令牌"""
        user_id = "user_123"
        token = auth_service.create_access_token(user_id)
        
        # 验证有效令牌
        verified_user_id = auth_service.verify_token(token)
        assert verified_user_id == user_id
        
        # 验证无效令牌
        invalid_token = "invalid.token.here"
        assert auth_service.verify_token(invalid_token) is None
    
    def test_token_expiration(self, auth_service):
        """测试令牌过期"""
        user_id = "user_123"
        # 创建一个已过期的令牌
        expired_token = auth_service.create_access_token(
            user_id, 
            expires_delta=timedelta(seconds=-1)
        )
        
        # 验证过期令牌
        assert auth_service.verify_token(expired_token) is None
    
    def test_authenticate_user(self, auth_service, sample_user):
        """测试用户认证"""
        # 正确的密码
        authenticated = auth_service.authenticate_user(
            sample_user, 
            "password123"
        )
        assert authenticated is True
        
        # 错误的密码
        authenticated = auth_service.authenticate_user(
            sample_user, 
            "wrongpassword"
        )
        assert authenticated is False
        
        # 未激活用户
        sample_user.is_active = False
        authenticated = auth_service.authenticate_user(
            sample_user, 
            "password123"
        )
        assert authenticated is False


class TestUserService:
    """用户服务测试"""
    
    @pytest.fixture
    def user_service(self, db_session):
        """创建用户服务实例"""
        return UserService(db=db_session)
    
    @pytest.fixture
    def user_create_data(self):
        """用户创建数据"""
        return UserCreate(
            username="newuser",
            email="new@example.com",
            password="securepassword123",
            full_name="New User"
        )
    
    @pytest.mark.asyncio
    async def test_create_user(self, user_service, user_create_data):
        """测试创建用户"""
        user = await user_service.create_user(user_create_data)
        
        assert user.username == user_create_data.username
        assert user.email == user_create_data.email
        assert user.full_name == user_create_data.full_name
        assert user.hashed_password != user_create_data.password  # 密码已加密
        assert verify_password(user_create_data.password, user.hashed_password)
    
    @pytest.mark.asyncio
    async def test_get_user_by_username(self, user_service, user_create_data):
        """测试通过用户名获取用户"""
        # 创建用户
        created_user = await user_service.create_user(user_create_data)
        
        # 通过用户名查找
        found_user = await user_service.get_user_by_username(created_user.username)
        assert found_user is not None
        assert found_user.id == created_user.id
        
        # 查找不存在的用户
        not_found = await user_service.get_user_by_username("nonexistent")
        assert not_found is None
    
    @pytest.mark.asyncio
    async def test_get_user_by_email(self, user_service, user_create_data):
        """测试通过邮箱获取用户"""
        created_user = await user_service.create_user(user_create_data)
        
        found_user = await user_service.get_user_by_email(created_user.email)
        assert found_user is not None
        assert found_user.id == created_user.id
    
    @pytest.mark.asyncio
    async def test_update_user(self, user_service, user_create_data):
        """测试更新用户信息"""
        user = await user_service.create_user(user_create_data)
        
        # 更新用户信息
        update_data = {
            "full_name": "Updated Name",
            "email": "updated@example.com"
        }
        updated_user = await user_service.update_user(user.id, update_data)
        
        assert updated_user.full_name == "Updated Name"
        assert updated_user.email == "updated@example.com"
        assert updated_user.username == user.username  # 用户名未变
    
    @pytest.mark.asyncio
    async def test_delete_user(self, user_service, user_create_data):
        """测试删除用户"""
        user = await user_service.create_user(user_create_data)
        
        # 删除用户
        success = await user_service.delete_user(user.id)
        assert success is True
        
        # 验证用户已删除
        deleted_user = await user_service.get_user_by_id(user.id)
        assert deleted_user is None
    
    @pytest.mark.asyncio
    async def test_duplicate_user_prevention(self, user_service, user_create_data):
        """测试防止重复用户"""
        # 创建第一个用户
        await user_service.create_user(user_create_data)
        
        # 尝试创建相同用户名的用户
        with pytest.raises(ValueError, match="用户名已存在"):
            await user_service.create_user(user_create_data)
        
        # 尝试创建相同邮箱的用户
        user_create_data.username = "different_username"
        with pytest.raises(ValueError, match="邮箱已被使用"):
            await user_service.create_user(user_create_data)


class TestSubscriptionService:
    """订阅服务测试"""
    
    @pytest.fixture
    def subscription_service(self, db_session):
        """创建订阅服务实例"""
        return SubscriptionService(db=db_session)
    
    @pytest.fixture
    def sample_subscription(self):
        """示例订阅配置"""
        return Subscription(
            user_id="user_123",
            subscription_type="daily",
            categories=["技术", "研究", "行业"],
            keywords=["GPT", "深度学习", "AI应用"],
            delivery_channels=["email", "web"],
            delivery_time="09:00",
            timezone="Asia/Shanghai",
            is_active=True
        )
    
    @pytest.mark.asyncio
    async def test_create_subscription(self, subscription_service, sample_subscription):
        """测试创建订阅"""
        subscription = await subscription_service.create_subscription(
            sample_subscription.user_id,
            sample_subscription
        )
        
        assert subscription.user_id == sample_subscription.user_id
        assert subscription.subscription_type == "daily"
        assert "技术" in subscription.categories
        assert "email" in subscription.delivery_channels
    
    @pytest.mark.asyncio
    async def test_get_user_subscriptions(self, subscription_service, sample_subscription):
        """测试获取用户订阅"""
        # 创建多个订阅
        await subscription_service.create_subscription(
            sample_subscription.user_id,
            sample_subscription
        )
        
        # 创建周报订阅
        weekly_sub = sample_subscription.model_copy()
        weekly_sub.subscription_type = "weekly"
        await subscription_service.create_subscription(
            sample_subscription.user_id,
            weekly_sub
        )
        
        # 获取用户所有订阅
        subscriptions = await subscription_service.get_user_subscriptions(
            sample_subscription.user_id
        )
        
        assert len(subscriptions) == 2
        assert any(s.subscription_type == "daily" for s in subscriptions)
        assert any(s.subscription_type == "weekly" for s in subscriptions)
    
    @pytest.mark.asyncio
    async def test_update_subscription(self, subscription_service, sample_subscription):
        """测试更新订阅"""
        subscription = await subscription_service.create_subscription(
            sample_subscription.user_id,
            sample_subscription
        )
        
        # 更新订阅
        update_data = {
            "categories": ["技术", "投资"],
            "delivery_time": "18:00",
            "is_active": False
        }
        
        updated = await subscription_service.update_subscription(
            subscription.id,
            update_data
        )
        
        assert "投资" in updated.categories
        assert "研究" not in updated.categories
        assert updated.delivery_time == "18:00"
        assert updated.is_active is False
    
    @pytest.mark.asyncio
    async def test_delete_subscription(self, subscription_service, sample_subscription):
        """测试删除订阅"""
        subscription = await subscription_service.create_subscription(
            sample_subscription.user_id,
            sample_subscription
        )
        
        # 删除订阅
        success = await subscription_service.delete_subscription(subscription.id)
        assert success is True
        
        # 验证已删除
        subscriptions = await subscription_service.get_user_subscriptions(
            sample_subscription.user_id
        )
        assert len(subscriptions) == 0
    
    @pytest.mark.asyncio
    async def test_get_active_subscriptions_by_type(self, subscription_service):
        """测试按类型获取活跃订阅"""
        # 创建多个不同类型的订阅
        subscriptions_data = [
            ("user1", "daily", True),
            ("user2", "daily", True),
            ("user3", "weekly", True),
            ("user4", "daily", False),  # 未激活
        ]
        
        for user_id, sub_type, is_active in subscriptions_data:
            sub = Subscription(
                user_id=user_id,
                subscription_type=sub_type,
                categories=["技术"],
                delivery_channels=["email"],
                is_active=is_active
            )
            await subscription_service.create_subscription(user_id, sub)
        
        # 获取活跃的日报订阅
        daily_subs = await subscription_service.get_active_subscriptions_by_type("daily")
        assert len(daily_subs) == 2  # 只有2个活跃的日报订阅
        
        # 获取活跃的周报订阅
        weekly_subs = await subscription_service.get_active_subscriptions_by_type("weekly")
        assert len(weekly_subs) == 1
    
    @pytest.mark.asyncio
    async def test_subscription_validation(self, subscription_service):
        """测试订阅验证"""
        # 无效的订阅类型
        invalid_sub = Subscription(
            user_id="user_123",
            subscription_type="invalid_type",
            categories=[],
            delivery_channels=[]
        )
        
        with pytest.raises(ValueError, match="无效的订阅类型"):
            await subscription_service.create_subscription("user_123", invalid_sub)
        
        # 无效的投递渠道
        invalid_sub.subscription_type = "daily"
        invalid_sub.delivery_channels = ["invalid_channel"]
        
        with pytest.raises(ValueError, match="无效的投递渠道"):
            await subscription_service.create_subscription("user_123", invalid_sub)