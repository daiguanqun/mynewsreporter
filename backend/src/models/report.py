"""
报告数据模型
"""
from sqlalchemy import Column, String, Text, JSON, DateTime, Boolean, Enum
from .base import Base
import enum


class ReportType(enum.Enum):
    """报告类型枚举"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class ReportStatus(enum.Enum):
    """报告状态枚举"""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    PUBLISHED = "published"


class ReportTemplate(Base):
    """报告模板"""
    
    # 模板基本信息
    name = Column(String(100), nullable=False)
    description = Column(Text)
    template_type = Column(Enum(ReportType), nullable=False, index=True)
    
    # 模板内容
    sections = Column(JSON, nullable=False)  # 章节配置列表
    layout_config = Column(JSON)  # 布局配置
    style_config = Column(JSON)   # 样式配置
    
    # 模板设置
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    version = Column(String(20), default="1.0.0")
    
    # 创建者信息
    created_by = Column(String(36))
    
    def __repr__(self):
        return f"<ReportTemplate(name={self.name}, type={self.template_type.value})>"


class Report(Base):
    """生成的报告"""
    
    # 报告基本信息
    title = Column(String(200), nullable=False)
    subtitle = Column(String(200))
    report_type = Column(Enum(ReportType), nullable=False, index=True)
    status = Column(Enum(ReportStatus), default=ReportStatus.PENDING, nullable=False, index=True)
    
    # 报告内容
    content = Column(JSON, nullable=False)  # 报告完整内容（结构化数据）
    summary = Column(Text)  # 执行摘要
    
    # 使用的模板
    template_id = Column(String(36))
    template_name = Column(String(100))
    
    # 报告配置
    config = Column(JSON)  # 生成时的配置
    time_range = Column(JSON)  # 覆盖的时间范围
    categories_covered = Column(JSON)  # 包含的分类
    
    # 统计信息
    metadata = Column(JSON)  # 各种统计数据
    total_items = Column(String(10))  # 包含的新闻条数
    
    # 生成信息
    generation_time = Column(DateTime(timezone=True))
    generation_duration = Column(String(20))  # 生成耗时
    error_message = Column(Text)
    
    # 发布信息
    is_published = Column(Boolean, default=False, nullable=False)
    published_at = Column(DateTime(timezone=True))
    publish_channels = Column(JSON)  # 发布渠道列表
    
    # 文件存储
    file_urls = Column(JSON)  # 各种格式文件的URL
    
    def __repr__(self):
        return f"<Report(title={self.title}, type={self.report_type.value}, status={self.status.value})>"