"""
订阅数据模型
"""
from sqlalchemy import Column, String, JSON, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .base import Base
from .report import ReportType


class Subscription(Base):
    """用户订阅"""
    
    # 用户关联
    user_id = Column(String(36), ForeignKey('user.id'), nullable=False, index=True)
    user = relationship("User", back_populates="subscriptions")
    
    # 订阅类型
    subscription_type = Column(Enum(ReportType), nullable=False, index=True)
    
    # 订阅内容设置
    categories = Column(JSON)  # 订阅的分类列表
    keywords = Column(JSON)    # 关键词列表
    sources = Column(JSON)     # 指定的来源列表
    
    # 投递设置
    delivery_channels = Column(JSON, nullable=False)  # 投递渠道 ["email", "web", "app"]
    delivery_time = Column(String(10))  # 投递时间 "HH:MM"
    timezone = Column(String(50), default="Asia/Shanghai")
    
    # 报告设置
    language = Column(String(10), default="zh")
    report_format = Column(JSON)  # 报告格式偏好
    
    # 订阅状态
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_paused = Column(Boolean, default=False, nullable=False)
    
    # 通知设置
    notify_on_generation = Column(Boolean, default=True)
    notify_on_important = Column(Boolean, default=True)
    importance_threshold = Column(String(10), default="0.7")
    
    def __repr__(self):
        return f"<Subscription(user_id={self.user_id}, type={self.subscription_type.value}, active={self.is_active})>"