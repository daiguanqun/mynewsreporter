"""
RSS源爬虫
"""
import asyncio
import feedparser
from typing import List, Optional
from datetime import datetime, timezone
import time
import uuid
import logging

from src.models.schemas import CollectedData, SourceConfig

logger = logging.getLogger(__name__)


class RSSCrawler:
    """RSS源爬虫"""
    
    def __init__(self):
        self.timeout = 30  # 超时时间（秒）
    
    async def fetch_feed(self, source_config: SourceConfig) -> List[CollectedData]:
        """获取RSS源数据"""
        try:
            # 使用线程池执行同步的feedparser
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(
                None,
                self._parse_feed,
                source_config.url
            )
            
            if feed.bozo:
                logger.error(f"RSS解析错误 {source_config.url}: {feed.bozo_exception}")
                return []
            
            results = []
            for entry in feed.entries:
                try:
                    data = self._parse_entry(entry, source_config)
                    if data:
                        results.append(data)
                except Exception as e:
                    logger.error(f"解析RSS条目错误: {e}")
                    continue
            
            logger.info(f"从 {source_config.name} 获取 {len(results)} 条数据")
            return results
            
        except Exception as e:
            logger.error(f"获取RSS源错误 {source_config.url}: {e}")
            return []
    
    def _parse_feed(self, url: str) -> feedparser.FeedParserDict:
        """解析RSS feed"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; AINewsBot/1.0)'
        }
        return feedparser.parse(url, request_headers=headers)
    
    def _parse_entry(self, entry: feedparser.FeedParserDict, source_config: SourceConfig) -> Optional[CollectedData]:
        """解析RSS条目"""
        try:
            # 提取基本信息
            title = entry.get('title', '').strip()
            if not title:
                return None
            
            # 提取链接
            link = entry.get('link', '')
            if not link:
                return None
            
            # 提取内容
            content = self._extract_content(entry)
            
            # 提取作者
            author = entry.get('author', '')
            if not author and 'authors' in entry:
                authors = entry.get('authors', [])
                if authors:
                    author = authors[0].get('name', '')
            
            # 提取发布时间
            publish_time = self._parse_publish_time(entry)
            
            # 提取标签
            tags = self._extract_tags(entry)
            
            # 创建数据对象
            return CollectedData(
                data_id=str(uuid.uuid4()),
                source_id=source_config.source_id,
                source_type="rss",
                source=source_config.name,
                title=title,
                content=content,
                url=link,
                author=author,
                publish_time=publish_time,
                tags=tags,
                collected_time=datetime.now(timezone.utc),
                raw_data={
                    'feed_title': entry.get('title', ''),
                    'feed_link': entry.get('link', ''),
                    'feed_id': entry.get('id', ''),
                    'feed_published': entry.get('published', ''),
                    'feed_updated': entry.get('updated', '')
                }
            )
            
        except Exception as e:
            logger.error(f"解析RSS条目错误: {e}")
            return None
    
    def _extract_content(self, entry: feedparser.FeedParserDict) -> str:
        """提取内容"""
        content = ''
        
        # 尝试从content字段提取
        if 'content' in entry:
            contents = entry.get('content', [])
            if contents and isinstance(contents, list):
                content = contents[0].get('value', '')
        
        # 如果没有content，尝试从summary提取
        if not content:
            content = entry.get('summary', '')
        
        # 如果还是没有，使用description
        if not content:
            content = entry.get('description', '')
        
        return content.strip()
    
    def _parse_publish_time(self, entry: feedparser.FeedParserDict) -> Optional[datetime]:
        """解析发布时间"""
        try:
            # 尝试从published_parsed获取
            time_tuple = entry.get('published_parsed')
            if time_tuple:
                timestamp = time.mktime(time_tuple)
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
            
            # 尝试从updated_parsed获取
            time_tuple = entry.get('updated_parsed')
            if time_tuple:
                timestamp = time.mktime(time_tuple)
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
            
            return None
            
        except Exception as e:
            logger.error(f"解析时间错误: {e}")
            return None
    
    def _extract_tags(self, entry: feedparser.FeedParserDict) -> List[str]:
        """提取标签"""
        tags = []
        
        # 从tags字段提取
        if 'tags' in entry:
            for tag in entry.get('tags', []):
                term = tag.get('term', '').strip()
                if term:
                    tags.append(term)
        
        # 从categories字段提取
        if 'categories' in entry:
            for category in entry.get('categories', []):
                if isinstance(category, str):
                    tags.append(category.strip())
                elif isinstance(category, dict):
                    term = category.get('term', '').strip()
                    if term:
                        tags.append(term)
        
        # 去重
        return list(set(tags))
    
    async def fetch_multiple_feeds(self, source_configs: List[SourceConfig]) -> List[CollectedData]:
        """批量获取多个RSS源"""
        tasks = []
        for config in source_configs:
            if config.enabled and config.source_type == "rss":
                task = self.fetch_feed(config)
                tasks.append(task)
        
        if not tasks:
            return []
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_data = []
        for result in results:
            if isinstance(result, list):
                all_data.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"批量获取RSS错误: {result}")
        
        return all_data