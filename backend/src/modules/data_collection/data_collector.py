"""
数据采集器主类
"""
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import hashlib
import logging

from src.models.schemas import CollectedData, SourceConfig
from src.core.redis import RedisClient
from .rss_crawler import RSSCrawler
from .web_scraper import WebScraper

logger = logging.getLogger(__name__)


class DataCollector:
    """数据采集器"""
    
    def __init__(self, redis_client: Optional[RedisClient] = None):
        self.rss_crawler = RSSCrawler()
        self.web_scraper = WebScraper()
        self.redis_client = redis_client
        self.max_concurrent = 5  # 最大并发数
        self.dedup_expire = 86400 * 7  # 去重缓存7天
    
    async def collect_all(self, source_configs: List[SourceConfig]) -> List[CollectedData]:
        """从所有数据源采集数据"""
        # 按类型分组
        rss_sources = []
        web_sources = []
        
        for config in source_configs:
            if not config.enabled:
                continue
            
            if config.source_type == "rss":
                rss_sources.append(config)
            elif config.source_type == "web":
                web_sources.append(config)
        
        # 并发采集
        tasks = []
        
        if rss_sources:
            task = self._collect_with_limit(
                self.rss_crawler.fetch_multiple_feeds,
                rss_sources
            )
            tasks.append(task)
        
        if web_sources:
            task = self._collect_with_limit(
                self.web_scraper.scrape_multiple_urls,
                web_sources
            )
            tasks.append(task)
        
        if not tasks:
            return []
        
        # 执行采集
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合并结果
        all_data = []
        for result in results:
            if isinstance(result, list):
                all_data.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"采集错误: {result}")
        
        # 去重
        deduplicated_data = await self.deduplicate(all_data)
        
        logger.info(f"采集完成，共 {len(deduplicated_data)} 条数据（去重后）")
        
        return deduplicated_data
    
    async def _collect_with_limit(self, collect_func, sources: List[SourceConfig]) -> List[CollectedData]:
        """限制并发数的采集"""
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def collect_with_semaphore(source):
            async with semaphore:
                return await self._collect_from_source(collect_func, source)
        
        # 如果是批量函数，直接调用
        if hasattr(collect_func, '__name__') and 'multiple' in collect_func.__name__:
            return await collect_func(sources)
        
        # 否则逐个采集
        tasks = [collect_with_semaphore(source) for source in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        collected_data = []
        for result in results:
            if isinstance(result, list):
                collected_data.extend(result)
            elif isinstance(result, CollectedData):
                collected_data.append(result)
            elif isinstance(result, Exception):
                logger.error(f"采集源错误: {result}")
        
        return collected_data
    
    async def _collect_from_source(self, collect_func, source: SourceConfig) -> List[CollectedData]:
        """从单个源采集数据"""
        try:
            if source.source_type == "rss":
                result = await self.rss_crawler.fetch_feed(source)
                return result if isinstance(result, list) else [result]
            elif source.source_type == "web":
                result = await self.web_scraper.scrape_url(source)
                return [result] if result else []
            else:
                logger.warning(f"不支持的数据源类型: {source.source_type}")
                return []
        except Exception as e:
            logger.error(f"采集源 {source.name} 错误: {e}")
            return []
    
    async def deduplicate(self, data_list: List[CollectedData]) -> List[CollectedData]:
        """数据去重"""
        if not data_list:
            return []
        
        seen_urls = set()
        seen_hashes = set()
        deduplicated = []
        
        for item in data_list:
            # URL去重
            if item.url in seen_urls:
                continue
            seen_urls.add(item.url)
            
            # 内容哈希去重
            content_hash = self._calculate_content_hash(item)
            if content_hash in seen_hashes:
                continue
            seen_hashes.add(content_hash)
            
            # Redis去重（如果有Redis客户端）
            if self.redis_client:
                is_duplicate = await self._check_redis_duplicate(content_hash)
                if is_duplicate:
                    continue
                # 标记为已见
                await self._mark_as_seen(content_hash)
            
            deduplicated.append(item)
        
        return deduplicated
    
    def _calculate_content_hash(self, data: CollectedData) -> str:
        """计算内容哈希"""
        # 使用标题和内容的组合计算哈希
        content = f"{data.title}:{data.content[:500] if data.content else ''}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    async def _check_redis_duplicate(self, content_hash: str) -> bool:
        """检查Redis中是否已存在"""
        if not self.redis_client:
            return False
        
        try:
            key = f"content_hash:{content_hash}"
            exists = await self.redis_client.exists(key)
            return exists
        except Exception as e:
            logger.error(f"Redis检查去重错误: {e}")
            return False
    
    async def _mark_as_seen(self, content_hash: str):
        """在Redis中标记为已见"""
        if not self.redis_client:
            return
        
        try:
            key = f"content_hash:{content_hash}"
            await self.redis_client.set(key, "1", expire=self.dedup_expire)
        except Exception as e:
            logger.error(f"Redis标记已见错误: {e}")
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """获取采集统计信息"""
        stats = {
            "last_collection_time": None,
            "total_collected_today": 0,
            "sources_active": 0,
            "sources_failed": 0,
            "dedup_cache_size": 0
        }
        
        if self.redis_client:
            try:
                # 获取今日采集数
                today_key = f"collection_stats:{datetime.now().strftime('%Y-%m-%d')}"
                today_count = await self.redis_client.get(today_key)
                if today_count:
                    stats["total_collected_today"] = int(today_count)
                
                # 获取最后采集时间
                last_time = await self.redis_client.get("last_collection_time")
                if last_time:
                    stats["last_collection_time"] = last_time
                
            except Exception as e:
                logger.error(f"获取统计信息错误: {e}")
        
        return stats
    
    async def update_collection_stats(self, collected_count: int):
        """更新采集统计"""
        if not self.redis_client:
            return
        
        try:
            # 更新今日采集数
            today_key = f"collection_stats:{datetime.now().strftime('%Y-%m-%d')}"
            await self.redis_client.incr(today_key)
            await self.redis_client.expire(today_key, 86400 * 7)  # 保留7天
            
            # 更新最后采集时间
            await self.redis_client.set(
                "last_collection_time",
                datetime.now(timezone.utc).isoformat()
            )
            
        except Exception as e:
            logger.error(f"更新统计信息错误: {e}")