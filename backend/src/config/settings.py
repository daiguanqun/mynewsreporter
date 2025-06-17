"""
系统配置管理
"""
from functools import lru_cache
from typing import List, Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import json


class Settings(BaseSettings):
    """系统配置"""
    
    # 应用配置
    app_name: str = Field(default="AI新闻报告平台", env="APP_NAME")
    app_env: str = Field(default="development", env="APP_ENV")
    app_host: str = Field(default="0.0.0.0", env="APP_HOST")
    app_port: int = Field(default=8000, env="APP_PORT")
    
    # 数据库配置
    database_url: str = Field(
        default="postgresql://user:password@localhost:5432/ainewsreport",
        env="DATABASE_URL"
    )
    
    # Redis配置
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )
    
    # Celery配置
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1",
        env="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2",
        env="CELERY_RESULT_BACKEND"
    )
    
    # 安全配置
    secret_key: str = Field(
        default="your-secret-key-here",
        env="SECRET_KEY"
    )
    jwt_secret_key: str = Field(
        default="your-jwt-secret-key-here",
        env="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # OpenAI配置
    openai_api_key: str = Field(
        default="your-openai-api-key-here",
        env="OPENAI_API_KEY"
    )
    openai_model: str = Field(default="gpt-3.5-turbo", env="OPENAI_MODEL")
    
    # RSS源配置
    rss_feeds: str = Field(
        default='[{"name": "AI News", "url": "https://example.com/ai-news.rss", "category": "general"}]',
        env="RSS_FEEDS"
    )
    
    # 采集配置
    collection_interval_minutes: int = Field(default=60, env="COLLECTION_INTERVAL_MINUTES")
    max_concurrent_collections: int = Field(default=5, env="MAX_CONCURRENT_COLLECTIONS")
    
    # 报告生成配置
    report_generation_hour: int = Field(default=9, env="REPORT_GENERATION_HOUR")
    report_timezone: str = Field(default="Asia/Shanghai", env="REPORT_TIMEZONE")
    
    # 邮件配置
    smtp_host: str = Field(default="smtp.example.com", env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_user: str = Field(default="noreply@example.com", env="SMTP_USER")
    smtp_password: str = Field(default="", env="SMTP_PASSWORD")
    smtp_tls: bool = Field(default=True, env="SMTP_TLS")
    
    # 日志配置
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    @validator("rss_feeds", pre=True)
    def parse_rss_feeds(cls, v):
        """解析RSS源配置"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v
    
    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.app_env == "production"
    
    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.app_env == "development"
    
    @property
    def is_testing(self) -> bool:
        """是否为测试环境"""
        return self.app_env == "testing"
    
    @property
    def database_echo(self) -> bool:
        """是否输出SQL语句"""
        return self.is_development
    
    @property
    def cors_origins(self) -> List[str]:
        """CORS允许的源"""
        if self.is_production:
            return ["https://ainewsreport.com"]
        return ["*"]
    
    def get_rss_sources(self) -> List[Dict[str, Any]]:
        """获取RSS源列表"""
        if isinstance(self.rss_feeds, str):
            try:
                return json.loads(self.rss_feeds)
            except:
                return []
        return self.rss_feeds if isinstance(self.rss_feeds, list) else []
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """获取系统配置（缓存）"""
    return Settings()