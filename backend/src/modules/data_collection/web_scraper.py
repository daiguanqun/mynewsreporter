"""
网页爬虫
"""
import asyncio
import httpx
from bs4 import BeautifulSoup
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
import logging
from urllib.parse import urljoin, urlparse

from src.models.schemas import CollectedData, SourceConfig

logger = logging.getLogger(__name__)


class WebScraper:
    """网页爬虫"""
    
    def __init__(self):
        self.timeout = 30
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    async def scrape_url(self, source_config: SourceConfig) -> Optional[CollectedData]:
        """爬取单个URL"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 合并自定义headers
                headers = self.headers.copy()
                if source_config.headers:
                    headers.update(source_config.headers)
                
                response = await client.get(source_config.url, headers=headers)
                response.raise_for_status()
                
                # 解析HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 使用选择器提取内容
                selectors = source_config.selectors or {}
                
                # 提取标题
                title = self._extract_text(soup, selectors.get('title', 'h1'))
                if not title:
                    title = self._extract_text(soup, 'title')
                
                if not title:
                    logger.warning(f"无法提取标题: {source_config.url}")
                    return None
                
                # 提取内容
                content = self._extract_text(soup, selectors.get('content', 'article'))
                if not content:
                    content = self._extract_text(soup, 'main')
                
                # 提取作者
                author = self._extract_text(soup, selectors.get('author', '.author'))
                
                # 提取发布时间
                publish_time = self._extract_datetime(soup, selectors.get('date', 'time'))
                
                # 提取标签
                tags = self._extract_tags(soup, selectors.get('tags', '.tag'))
                
                # 提取所有链接
                links = self._extract_all_links(soup, source_config.url)
                
                return CollectedData(
                    data_id=str(uuid.uuid4()),
                    source_id=source_config.source_id,
                    source_type="web",
                    source=source_config.name,
                    title=title.strip(),
                    content=content.strip() if content else "",
                    url=source_config.url,
                    author=author.strip() if author else "",
                    publish_time=publish_time,
                    tags=tags,
                    collected_time=datetime.now(timezone.utc),
                    raw_data={
                        'status_code': response.status_code,
                        'headers': dict(response.headers),
                        'links': links[:10]  # 保存前10个链接
                    }
                )
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP错误 {source_config.url}: {e}")
            return None
        except Exception as e:
            logger.error(f"爬取网页错误 {source_config.url}: {e}")
            return None
    
    def _extract_text(self, soup: BeautifulSoup, selector: str) -> Optional[str]:
        """提取文本内容"""
        if not selector:
            return None
        
        try:
            # 尝试CSS选择器
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
            
            # 尝试标签名
            element = soup.find(selector)
            if element:
                return element.get_text(strip=True)
            
            return None
            
        except Exception as e:
            logger.error(f"提取文本错误 {selector}: {e}")
            return None
    
    def _extract_datetime(self, soup: BeautifulSoup, selector: str) -> Optional[datetime]:
        """提取日期时间"""
        if not selector:
            return None
        
        try:
            element = soup.select_one(selector) or soup.find(selector)
            if not element:
                return None
            
            # 尝试从datetime属性获取
            datetime_str = element.get('datetime')
            if datetime_str:
                return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            
            # 尝试从文本解析
            date_text = element.get_text(strip=True)
            # 这里可以添加更多日期格式的解析
            
            return None
            
        except Exception as e:
            logger.error(f"提取日期时间错误: {e}")
            return None
    
    def _extract_tags(self, soup: BeautifulSoup, selector: str) -> List[str]:
        """提取标签"""
        tags = []
        
        if not selector:
            return tags
        
        try:
            elements = soup.select(selector)
            if not elements:
                elements = soup.find_all(selector)
            
            for element in elements:
                tag = element.get_text(strip=True)
                if tag:
                    tags.append(tag)
            
            return list(set(tags))  # 去重
            
        except Exception as e:
            logger.error(f"提取标签错误: {e}")
            return tags
    
    def _extract_all_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """提取所有链接"""
        links = []
        
        try:
            for link in soup.find_all('a', href=True):
                href = link['href']
                # 转换为绝对URL
                absolute_url = urljoin(base_url, href)
                # 只保留HTTP(S)链接
                if urlparse(absolute_url).scheme in ['http', 'https']:
                    links.append(absolute_url)
            
            return list(set(links))  # 去重
            
        except Exception as e:
            logger.error(f"提取链接错误: {e}")
            return links
    
    async def scrape_multiple_urls(self, source_configs: List[SourceConfig]) -> List[CollectedData]:
        """批量爬取多个URL"""
        tasks = []
        for config in source_configs:
            if config.enabled and config.source_type == "web":
                task = self.scrape_url(config)
                tasks.append(task)
        
        if not tasks:
            return []
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        collected_data = []
        for result in results:
            if isinstance(result, CollectedData):
                collected_data.append(result)
            elif isinstance(result, Exception):
                logger.error(f"批量爬取错误: {result}")
        
        return collected_data
    
    async def discover_links(self, url: str, pattern: Optional[str] = None) -> List[str]:
        """发现页面中的链接"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                links = self._extract_all_links(soup, url)
                
                # 如果提供了模式，过滤链接
                if pattern:
                    import re
                    regex = re.compile(pattern)
                    links = [link for link in links if regex.search(link)]
                
                return links
                
        except Exception as e:
            logger.error(f"发现链接错误 {url}: {e}")
            return []