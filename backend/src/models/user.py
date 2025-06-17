"""
用户数据模型
"""
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from .base import Base


class User(Base):
    """用户模型"""
    
    # 用户基本信息
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(100))
    hashed_password = Column(String(200), nullable=False)
    
    # 用户状态
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # 用户偏好设置
    preferred_categories = Column(String(500))  # JSON格式存储
    preferred_keywords = Column(String(500))    # JSON格式存储
    notification_settings = Column(String(500)) # JSON格式存储
    
    # 最后登录时间
    last_login_at = Column(DateTime(timezone=True))
    
    # 关系
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(username={self.username}, email={self.email})>"
    
    def to_safe_dict(self):
        """转换为安全的字典（不包含密码）"""
        data = self.to_dict()
        data.pop('hashed_password', None)
        return data