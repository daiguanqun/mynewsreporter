"""
数据库模型基类
"""
from datetime import datetime
from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.declarative import declared_attr
import uuid


class BaseModel:
    """模型基类"""
    
    @declared_attr
    def __tablename__(cls):
        """自动生成表名（将类名转换为下划线格式）"""
        name = cls.__name__
        # 将驼峰命名转换为下划线命名
        result = []
        for i, char in enumerate(name):
            if i > 0 and char.isupper() and name[i-1].islower():
                result.append('_')
            result.append(char.lower())
        return ''.join(result)
    
    # 基础字段
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def to_dict(self):
        """转换为字典"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result
    
    def update_from_dict(self, data: dict):
        """从字典更新数据"""
        for key, value in data.items():
            if hasattr(self, key) and key not in ['id', 'created_at']:
                setattr(self, key, value)
        return self


# 创建声明基类
Base = declarative_base(cls=BaseModel)