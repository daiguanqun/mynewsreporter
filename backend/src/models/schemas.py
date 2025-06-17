"""
Pydantic数据模式定义
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, validator
from enum import Enum


# 基础模式
class BaseSchema(BaseModel):
    """基础模式"""
    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


# 用户相关模式
class UserBase(BaseSchema):
    """用户基础模式"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """用户创建模式"""
    password: str = Field(..., min_length=6)


class UserLogin(BaseSchema):
    """用户登录模式"""
    username: str
    password: str


class UserUpdate(BaseSchema):
    """用户更新模式"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    preferred_categories: Optional[List[str]] = None
    preferred_keywords: Optional[List[str]] = None


class User(UserBase):
    """用户模式"""
    id: str
    is_active: bool
    is_verified: bool
    is_superuser: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None


# 数据源配置
class SourceConfig(BaseSchema):
    """数据源配置"""
    source_id: str
    source_type: str  # rss, web, api
    name: str
    url: str
    enabled: bool = True
    update_frequency: int = 60  # 分钟
    selectors: Optional[Dict[str, str]] = None  # 网页爬虫选择器
    headers: Optional[Dict[str, str]] = None
    api_config: Optional[Dict[str, Any]] = None


# 采集数据模式
class CollectedData(BaseSchema):
    """采集的数据"""
    data_id: str
    source_id: str
    source_type: str
    source: str
    title: str
    content: Optional[str] = None
    url: str
    author: Optional[str] = None
    publish_time: Optional[datetime] = None
    tags: List[str] = []
    collected_time: datetime
    raw_data: Optional[Dict[str, Any]] = None


# 关键词模式
class Keyword(BaseSchema):
    """关键词"""
    term: str
    score: float
    type: Optional[str] = None


class Entity(BaseSchema):
    """实体"""
    text: str
    label: str
    confidence: float


# 处理后的内容模式
class ProcessedContent(BaseSchema):
    """处理后的内容"""
    content_id: str
    title: str
    cleaned_content: str
    summary: Optional[str] = None
    keywords: List[Keyword] = []
    entities: List[Entity] = []
    categories: List[str] = []
    tags: List[str] = []
    importance_score: float = 0.0
    quality_score: float = 0.0
    sentiment: Optional[Dict[str, Any]] = None
    source: Optional[str] = None
    author: Optional[str] = None
    publish_time: Optional[datetime] = None
    url: Optional[str] = None
    extracted_links: List[str] = []
    source_authority: float = 0.5
    engagement_metrics: Optional[Dict[str, Any]] = None
    processing_time: Optional[datetime] = None


# 报告相关模式
class ReportSection(BaseSchema):
    """报告章节"""
    section_id: str
    section_name: str
    section_type: str
    order: int
    content: Optional[Dict[str, Any]] = None
    max_items: Optional[int] = None
    filters: Optional[Dict[str, Any]] = None


class ReportTemplate(BaseSchema):
    """报告模板"""
    template_id: str
    name: str
    description: Optional[str] = None
    template_type: str
    sections: List[ReportSection]
    layout_config: Optional[Dict[str, Any]] = None
    style_config: Optional[Dict[str, Any]] = None
    version: str = "1.0.0"
    is_active: bool = True
    is_default: bool = False
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None


class ReportConfig(BaseSchema):
    """报告配置"""
    report_type: str
    template_id: str
    time_range: Dict[str, Any]
    categories: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    max_items_per_section: int = 10
    include_summary: bool = True
    include_charts: bool = False
    export_formats: List[str] = ["html", "pdf"]


class GeneratedReport(BaseSchema):
    """生成的报告"""
    report_id: str
    title: str
    subtitle: Optional[str] = None
    report_type: str
    sections: List[ReportSection]
    summary: Optional[str] = None
    metadata: Dict[str, Any]
    generated_time: datetime
    template_used: Optional[str] = None
    file_urls: Optional[Dict[str, str]] = None


# 订阅相关模式
class SubscriptionBase(BaseSchema):
    """订阅基础模式"""
    subscription_type: str
    categories: List[str] = []
    keywords: List[str] = []
    delivery_channels: List[str] = ["email"]
    delivery_time: Optional[str] = "09:00"
    timezone: str = "Asia/Shanghai"
    is_active: bool = True


class SubscriptionCreate(SubscriptionBase):
    """创建订阅"""
    pass


class SubscriptionUpdate(BaseSchema):
    """更新订阅"""
    categories: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    delivery_channels: Optional[List[str]] = None
    delivery_time: Optional[str] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None


class Subscription(SubscriptionBase):
    """订阅信息"""
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime


# API响应模式
class Token(BaseSchema):
    """认证令牌"""
    access_token: str
    token_type: str = "bearer"


class Message(BaseSchema):
    """消息响应"""
    message: str
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class PaginatedResponse(BaseSchema):
    """分页响应"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool