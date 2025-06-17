"""
数据采集模块单元测试
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
import feedparser
from bs4 import BeautifulSoup

from src.modules.data_collection.rss_crawler import RSSCrawler
from src.modules.data_collection.web_scraper import WebScraper
from src.modules.data_collection.data_collector import DataCollector
from src.models.schemas import CollectedData, SourceConfig


class TestRSSCrawler:
    """RSS爬虫测试"""
    
    @pytest.fixture
    def rss_crawler(self):
        """创建RSS爬虫实例"""
        return RSSCrawler()
    
    @pytest.fixture
    def mock_rss_feed(self):
        """模拟RSS feed数据"""
        return {
            'feed': {
                'title': 'AI News Feed',
                'link': 'https://example.com',
                'description': 'Latest AI News'
            },
            'entries': [
                {
                    'title': 'OpenAI发布新模型',
                    'link': 'https://example.com/news/1',
                    'description': 'OpenAI今天发布了新的AI模型...',
                    'author': 'John Doe',
                    'published_parsed': (2024, 1, 1, 10, 0, 0, 0, 1, 0),
                    'tags': [{'term': 'AI'}, {'term': 'OpenAI'}]
                },
                {
                    'title': 'Google AI研究进展',
                    'link': 'https://example.com/news/2',
                    'description': 'Google AI团队发表最新研究...',
                    'author': 'Jane Smith',
                    'published_parsed': (2024, 1, 1, 9, 0, 0, 0, 1, 0),
                    'tags': [{'term': 'AI'}, {'term': 'Google'}]
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_fetch_rss_feed(self, rss_crawler, mock_rss_feed):
        """测试获取RSS feed"""
        with patch('feedparser.parse', return_value=mock_rss_feed):
            source_config = SourceConfig(
                source_id="test_rss_1",
                source_type="rss",
                name="Test RSS",
                url="https://example.com/rss",
                enabled=True
            )
            
            results = await rss_crawler.fetch_feed(source_config)
            
            assert len(results) == 2
            assert results[0].title == "OpenAI发布新模型"
            assert results[0].source == "Test RSS"
            assert results[0].url == "https://example.com/news/1"
            assert "AI" in results[0].tags
    
    @pytest.mark.asyncio
    async def test_parse_rss_entry(self, rss_crawler, mock_rss_feed):
        """测试解析RSS条目"""
        entry = mock_rss_feed['entries'][0]
        source_config = SourceConfig(
            source_id="test_rss_1",
            source_type="rss",
            name="Test RSS",
            url="https://example.com/rss",
            enabled=True
        )
        
        result = rss_crawler._parse_entry(entry, source_config)
        
        assert isinstance(result, CollectedData)
        assert result.title == "OpenAI发布新模型"
        assert result.author == "John Doe"
        assert result.source == "Test RSS"
        assert len(result.tags) == 2
    
    @pytest.mark.asyncio
    async def test_handle_invalid_feed(self, rss_crawler):
        """测试处理无效的RSS feed"""
        with patch('feedparser.parse', return_value={'bozo': True, 'bozo_exception': Exception("Invalid feed")}):
            source_config = SourceConfig(
                source_id="test_rss_invalid",
                source_type="rss",
                name="Invalid RSS",
                url="https://example.com/invalid",
                enabled=True
            )
            
            results = await rss_crawler.fetch_feed(source_config)
            assert results == []


class TestWebScraper:
    """网页爬虫测试"""
    
    @pytest.fixture
    def web_scraper(self):
        """创建网页爬虫实例"""
        return WebScraper()
    
    @pytest.fixture
    def mock_html_content(self):
        """模拟HTML内容"""
        return """
        <html>
            <head>
                <title>AI突破性进展：新模型实现人类水平推理</title>
            </head>
            <body>
                <article>
                    <h1>AI突破性进展：新模型实现人类水平推理</h1>
                    <div class="author">作者：张三</div>
                    <div class="date">2024-01-01</div>
                    <div class="content">
                        <p>最新研究表明，新的AI模型在推理任务上达到了人类水平...</p>
                        <p>这项研究由顶尖AI实验室完成，标志着人工智能发展的重要里程碑。</p>
                    </div>
                    <div class="tags">
                        <span class="tag">人工智能</span>
                        <span class="tag">深度学习</span>
                        <span class="tag">推理</span>
                    </div>
                </article>
            </body>
        </html>
        """
    
    @pytest.mark.asyncio
    async def test_scrape_webpage(self, web_scraper, mock_html_content, mock_httpx):
        """测试爬取网页"""
        mock_httpx.get.return_value = Mock(
            status_code=200,
            text=mock_html_content,
            headers={'content-type': 'text/html'}
        )
        
        with patch('httpx.AsyncClient', return_value=mock_httpx):
            source_config = SourceConfig(
                source_id="test_web_1",
                source_type="web",
                name="Test Website",
                url="https://example.com/ai-news",
                enabled=True,
                selectors={
                    "title": "h1",
                    "content": ".content",
                    "author": ".author",
                    "date": ".date",
                    "tags": ".tag"
                }
            )
            
            result = await web_scraper.scrape_url(source_config)
            
            assert result is not None
            assert result.title == "AI突破性进展：新模型实现人类水平推理"
            assert "张三" in result.author
            assert "最新研究表明" in result.content
            assert "人工智能" in result.tags
    
    @pytest.mark.asyncio
    async def test_extract_content(self, web_scraper, mock_html_content):
        """测试内容提取"""
        soup = BeautifulSoup(mock_html_content, 'html.parser')
        selectors = {
            "title": "h1",
            "content": ".content",
            "author": ".author",
            "date": ".date",
            "tags": ".tag"
        }
        
        title = web_scraper._extract_text(soup, selectors.get("title"))
        content = web_scraper._extract_text(soup, selectors.get("content"))
        tags = web_scraper._extract_tags(soup, selectors.get("tags"))
        
        assert title == "AI突破性进展：新模型实现人类水平推理"
        assert "最新研究表明" in content
        assert len(tags) == 3
        assert "深度学习" in tags
    
    @pytest.mark.asyncio
    async def test_handle_request_error(self, web_scraper, mock_httpx):
        """测试处理请求错误"""
        mock_httpx.get.side_effect = Exception("Network error")
        
        with patch('httpx.AsyncClient', return_value=mock_httpx):
            source_config = SourceConfig(
                source_id="test_web_error",
                source_type="web",
                name="Error Website",
                url="https://example.com/error",
                enabled=True
            )
            
            result = await web_scraper.scrape_url(source_config)
            assert result is None


class TestDataCollector:
    """数据采集器集成测试"""
    
    @pytest.fixture
    def data_collector(self, redis_client):
        """创建数据采集器实例"""
        return DataCollector(redis_client=redis_client)
    
    @pytest.fixture
    def sample_sources(self):
        """示例数据源配置"""
        return [
            SourceConfig(
                source_id="rss_1",
                source_type="rss",
                name="AI News RSS",
                url="https://example.com/ai-news.rss",
                enabled=True,
                update_frequency=60
            ),
            SourceConfig(
                source_id="web_1",
                source_type="web",
                name="Tech Blog",
                url="https://example.com/blog",
                enabled=True,
                update_frequency=120,
                selectors={
                    "title": "h1",
                    "content": ".post-content",
                    "author": ".author",
                    "date": ".publish-date"
                }
            ),
            SourceConfig(
                source_id="rss_2",
                source_type="rss",
                name="Disabled RSS",
                url="https://example.com/disabled.rss",
                enabled=False,
                update_frequency=60
            )
        ]
    
    @pytest.mark.asyncio
    async def test_collect_from_all_sources(self, data_collector, sample_sources, mock_httpx):
        """测试从所有数据源采集"""
        # Mock RSS feed
        mock_rss_data = {
            'entries': [
                {
                    'title': 'RSS News 1',
                    'link': 'https://example.com/rss/1',
                    'description': 'RSS content 1',
                    'published_parsed': (2024, 1, 1, 10, 0, 0, 0, 1, 0)
                }
            ]
        }
        
        # Mock web content
        mock_web_content = """
        <html>
            <body>
                <h1>Web News 1</h1>
                <div class="post-content">Web content 1</div>
                <div class="author">Web Author</div>
                <div class="publish-date">2024-01-01</div>
            </body>
        </html>
        """
        
        with patch('feedparser.parse', return_value=mock_rss_data):
            mock_httpx.get.return_value = Mock(
                status_code=200,
                text=mock_web_content,
                headers={'content-type': 'text/html'}
            )
            
            with patch('httpx.AsyncClient', return_value=mock_httpx):
                results = await data_collector.collect_all(sample_sources)
                
                # 应该只从启用的源采集（2个）
                assert len(results) == 2
                
                # 检查RSS源结果
                rss_results = [r for r in results if r.source == "AI News RSS"]
                assert len(rss_results) == 1
                assert rss_results[0].title == "RSS News 1"
                
                # 检查Web源结果
                web_results = [r for r in results if r.source == "Tech Blog"]
                assert len(web_results) == 1
                assert web_results[0].title == "Web News 1"
    
    @pytest.mark.asyncio
    async def test_collect_with_rate_limiting(self, data_collector, sample_sources):
        """测试速率限制"""
        # 测试并发限制
        with patch.object(data_collector, '_collect_from_source', new_callable=AsyncMock) as mock_collect:
            mock_collect.return_value = []
            
            await data_collector.collect_all(sample_sources[:2])  # 只用2个启用的源
            
            # 验证调用了2次
            assert mock_collect.call_count == 2
    
    @pytest.mark.asyncio
    async def test_deduplication(self, data_collector):
        """测试去重功能"""
        # 创建重复的数据
        data1 = CollectedData(
            data_id="1",
            source_id="source1",
            source_type="rss",
            title="Same Title",
            content="Same content",
            url="https://example.com/1",
            collected_time=datetime.now(timezone.utc)
        )
        
        data2 = CollectedData(
            data_id="2",
            source_id="source2",
            source_type="web",
            title="Same Title",
            content="Same content",
            url="https://example.com/2",
            collected_time=datetime.now(timezone.utc)
        )
        
        # 测试去重
        deduplicated = await data_collector.deduplicate([data1, data2])
        assert len(deduplicated) == 1
        assert deduplicated[0].data_id == "1"  # 保留第一个
    
    @pytest.mark.asyncio
    async def test_error_handling(self, data_collector):
        """测试错误处理"""
        source_with_error = SourceConfig(
            source_id="error_source",
            source_type="invalid_type",
            name="Error Source",
            url="https://example.com/error",
            enabled=True
        )
        
        # 不应该抛出异常，而是返回空结果
        results = await data_collector.collect_all([source_with_error])
        assert results == []