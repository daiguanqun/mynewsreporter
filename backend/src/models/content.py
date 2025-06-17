"""
内容数据模型
"""
from sqlalchemy import Column, String, Text, Float, DateTime, JSON, Boolean, Index
from .base import Base


class CollectedContent(Base):
    """采集的原始内容"""
    
    # 内容基本信息
    source_id = Column(String(50), nullable=False, index=True)
    source_type = Column(String(20), nullable=False)  # rss, web, api, social
    source_name = Column(String(100))
    
    # 内容数据
    title = Column(String(500), nullable=False)
    content = Column(Text)
    summary = Column(Text)
    url = Column(String(500), unique=True, nullable=False, index=True)
    
    # 元数据
    author = Column(String(200))
    publish_time = Column(DateTime(timezone=True))
    tags = Column(JSON)  # 标签列表
    categories = Column(JSON)  # 分类列表
    
    # 原始数据
    raw_data = Column(JSON)  # 保存原始数据以备后续处理
    
    # 处理标记
    is_processed = Column(Boolean, default=False, nullable=False, index=True)
    process_error = Column(Text)
    
    # 创建索引
    __table_args__ = (
        Index('idx_collected_content_publish_time', 'publish_time'),
        Index('idx_collected_content_source_processed', 'source_id', 'is_processed'),
    )
    
    def __repr__(self):
        return f"<CollectedContent(title={self.title[:30]}..., source={self.source_name})>"


class ProcessedContent(Base):
    """处理后的内容"""
    
    # 关联原始内容
    collected_content_id = Column(String(36), nullable=False, index=True)
    
    # 处理后的内容
    title = Column(String(500), nullable=False)
    cleaned_content = Column(Text, nullable=False)
    summary = Column(Text)
    
    # 提取的信息
    keywords = Column(JSON)  # 关键词列表 [{term: str, score: float, type: str}]
    entities = Column(JSON)  # 实体列表 [{text: str, label: str, confidence: float}]
    topics = Column(JSON)    # 主题列表
    sentiment = Column(JSON) # 情感分析结果
    
    # 分类和标签
    categories = Column(JSON)  # AI自动分类
    tags = Column(JSON)       # 合并和标准化后的标签
    
    # 评分
    importance_score = Column(Float, default=0.0, nullable=False, index=True)
    quality_score = Column(Float, default=0.0, nullable=False)
    relevance_score = Column(Float, default=0.0, nullable=False)
    
    # 附加信息
    extracted_links = Column(JSON)  # 提取的链接
    source_authority = Column(Float, default=0.5)  # 来源权威性
    engagement_metrics = Column(JSON)  # 互动指标
    
    # 去重信息
    content_hash = Column(String(64), unique=True, nullable=False, index=True)
    
    # 元数据（继承自原始内容）
    source_name = Column(String(100))
    author = Column(String(200))
    publish_time = Column(DateTime(timezone=True), index=True)
    url = Column(String(500))
    
    # 创建索引
    __table_args__ = (
        Index('idx_processed_content_importance', 'importance_score', 'publish_time'),
        Index('idx_processed_content_categories', 'categories'),
    )
    
    def __repr__(self):
        return f"<ProcessedContent(title={self.title[:30]}..., score={self.importance_score})>"