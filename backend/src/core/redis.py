"""
Redis连接管理
"""
from typing import Optional
import redis.asyncio as redis
from redis.asyncio import ConnectionPool

from src.config import get_settings

settings = get_settings()


# Redis连接池
redis_pool: Optional[ConnectionPool] = None


async def init_redis() -> redis.Redis:
    """初始化Redis连接池"""
    global redis_pool
    
    if not redis_pool:
        redis_pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=50
        )
    
    return redis.Redis(connection_pool=redis_pool)


async def get_redis() -> redis.Redis:
    """获取Redis客户端"""
    if not redis_pool:
        await init_redis()
    
    return redis.Redis(connection_pool=redis_pool)


async def close_redis():
    """关闭Redis连接池"""
    global redis_pool
    
    if redis_pool:
        await redis_pool.disconnect()
        redis_pool = None


class RedisClient:
    """Redis客户端封装"""
    
    def __init__(self, redis_client: redis.Redis):
        self.client = redis_client
    
    async def get(self, key: str) -> Optional[str]:
        """获取值"""
        return await self.client.get(key)
    
    async def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        """设置值"""
        return await self.client.set(key, value, ex=expire)
    
    async def delete(self, key: str) -> int:
        """删除键"""
        return await self.client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return await self.client.exists(key) > 0
    
    async def expire(self, key: str, seconds: int) -> bool:
        """设置过期时间"""
        return await self.client.expire(key, seconds)
    
    async def ttl(self, key: str) -> int:
        """获取剩余过期时间"""
        return await self.client.ttl(key)
    
    async def incr(self, key: str) -> int:
        """递增"""
        return await self.client.incr(key)
    
    async def decr(self, key: str) -> int:
        """递减"""
        return await self.client.decr(key)
    
    # Hash操作
    async def hset(self, name: str, key: str, value: str) -> int:
        """设置哈希值"""
        return await self.client.hset(name, key, value)
    
    async def hget(self, name: str, key: str) -> Optional[str]:
        """获取哈希值"""
        return await self.client.hget(name, key)
    
    async def hgetall(self, name: str) -> dict:
        """获取所有哈希值"""
        return await self.client.hgetall(name)
    
    async def hdel(self, name: str, *keys: str) -> int:
        """删除哈希键"""
        return await self.client.hdel(name, *keys)
    
    # List操作
    async def lpush(self, key: str, *values: str) -> int:
        """左侧插入列表"""
        return await self.client.lpush(key, *values)
    
    async def rpush(self, key: str, *values: str) -> int:
        """右侧插入列表"""
        return await self.client.rpush(key, *values)
    
    async def lpop(self, key: str) -> Optional[str]:
        """左侧弹出"""
        return await self.client.lpop(key)
    
    async def rpop(self, key: str) -> Optional[str]:
        """右侧弹出"""
        return await self.client.rpop(key)
    
    async def lrange(self, key: str, start: int, stop: int) -> list:
        """获取列表范围"""
        return await self.client.lrange(key, start, stop)
    
    async def llen(self, key: str) -> int:
        """获取列表长度"""
        return await self.client.llen(key)
    
    # Set操作
    async def sadd(self, key: str, *values: str) -> int:
        """添加集合成员"""
        return await self.client.sadd(key, *values)
    
    async def srem(self, key: str, *values: str) -> int:
        """移除集合成员"""
        return await self.client.srem(key, *values)
    
    async def smembers(self, key: str) -> set:
        """获取集合所有成员"""
        return await self.client.smembers(key)
    
    async def sismember(self, key: str, value: str) -> bool:
        """检查是否为集合成员"""
        return await self.client.sismember(key, value)