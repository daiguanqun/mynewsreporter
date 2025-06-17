"""
数据处理模块单元测试
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
import hashlib

from src.modules.data_processing.content_cleaner import ContentCleaner
from src.modules.data_processing.keyword_extractor import KeywordExtractor
from src.modules.data_processing.content_scorer import ContentScorer
from src.modules.data_processing.data_processor import DataProcessor
from src.models.schemas import CollectedData, ProcessedContent, Keyword


class TestContentCleaner:
    """内容清洗器测试"""
    
    @pytest.fixture
    def content_cleaner(self):
        """创建内容清洗器实例"""
        return ContentCleaner()
    
    def test_clean_html_content(self, content_cleaner):
        """测试清洗HTML内容"""
        html_content = """
        <div>
            <p>这是一段<strong>重要的</strong>AI新闻。</p>
            <script>alert('spam');</script>
            <p>了解更多：<a href="https://example.com">点击这里</a></p>
            <!-- 广告内容 -->
            <div class="ad">购买最新产品！</div>
        </div>
        """
        
        cleaned = content_cleaner.clean_html(html_content)
        
        assert "<script>" not in cleaned
        assert "alert" not in cleaned
        assert "这是一段重要的AI新闻" in cleaned
        assert "了解更多" in cleaned
    
    def test_normalize_whitespace(self, content_cleaner):
        """测试空白字符标准化"""
        content = "这是   一段\n\n有很多    空白的\t\t文本。"
        normalized = content_cleaner.normalize_whitespace(content)
        
        assert normalized == "这是 一段 有很多 空白的 文本。"
    
    def test_remove_special_characters(self, content_cleaner):
        """测试移除特殊字符"""
        content = "AI发展@#$%迅速！！！>>>了解更多..."
        cleaned = content_cleaner.remove_special_chars(content, keep_punctuation=True)
        
        assert "@#$%" not in cleaned
        assert ">>>" not in cleaned
        assert "AI发展迅速" in cleaned
        assert "！" in cleaned  # 保留标点
    
    def test_extract_links(self, content_cleaner):
        """测试提取链接"""
        html_content = """
        <div>
            <a href="https://example.com/news1">新闻1</a>
            <a href="https://example.com/news2" target="_blank">新闻2</a>
            <a href="mailto:test@example.com">联系我们</a>
        </div>
        """
        
        links = content_cleaner.extract_links(html_content)
        
        assert len(links) == 2  # 不包括mailto链接
        assert "https://example.com/news1" in links
        assert "https://example.com/news2" in links
    
    def test_full_cleaning_pipeline(self, content_cleaner):
        """测试完整的清洗流程"""
        raw_content = """
        <html>
            <body>
                <h1>AI突破：新模型性能提升50%！！！</h1>
                <p>据报道，最新的AI模型在多项测试中表现优异。</p>
                <div class="ad">广告：购买AI课程</div>
                <script>tracking();</script>
                <p>详情请访问：<a href="https://ai-news.com">AI新闻网</a></p>
            </body>
        </html>
        """
        
        result = content_cleaner.clean(raw_content)
        
        assert result.cleaned_content is not None
        assert "AI突破：新模型性能提升50%" in result.cleaned_content
        assert "广告" not in result.cleaned_content
        assert "script" not in result.cleaned_content
        assert len(result.extracted_links) == 1
        assert result.quality_score > 0


class TestKeywordExtractor:
    """关键词提取器测试"""
    
    @pytest.fixture
    def keyword_extractor(self):
        """创建关键词提取器实例"""
        return KeywordExtractor()
    
    def test_extract_keywords_chinese(self, keyword_extractor):
        """测试中文关键词提取"""
        text = """
        人工智能技术在过去几年取得了突破性进展。深度学习模型的性能不断提升，
        自然语言处理能力大幅增强。OpenAI发布的GPT系列模型展示了强大的文本生成能力。
        机器学习算法在图像识别、语音识别等领域表现出色。
        """
        
        keywords = keyword_extractor.extract_keywords(text, max_keywords=10)
        
        assert len(keywords) <= 10
        assert any(k.term in ["人工智能", "深度学习", "模型", "GPT"] for k in keywords)
        assert all(k.score > 0 for k in keywords)
        assert keywords[0].score >= keywords[-1].score  # 按分数排序
    
    def test_extract_entities(self, keyword_extractor):
        """测试实体识别"""
        text = "OpenAI公司发布了GPT-4模型，Google的Bard也在不断改进。微软投资了100亿美元。"
        
        entities = keyword_extractor.extract_entities(text)
        
        # 检查组织实体
        org_entities = [e for e in entities if e.label == "ORG"]
        assert any("OpenAI" in e.text for e in org_entities)
        assert any("Google" in e.text for e in org_entities)
        
        # 检查产品实体
        product_entities = [e for e in entities if e.label == "PRODUCT"]
        assert any("GPT-4" in e.text for e in product_entities)
    
    def test_extract_topics(self, keyword_extractor):
        """测试主题提取"""
        text = """
        深度学习在计算机视觉领域的应用越来越广泛。卷积神经网络可以准确识别图像中的物体。
        同时，自然语言处理技术也在快速发展，Transformer架构革新了文本处理方式。
        """
        
        topics = keyword_extractor.extract_topics(text)
        
        assert len(topics) > 0
        assert any(topic in ["深度学习", "计算机视觉", "自然语言处理"] for topic in topics)
    
    def test_keyword_extraction_with_domain(self, keyword_extractor):
        """测试特定领域的关键词提取"""
        text = "Transformer模型使用self-attention机制，在NLP任务中表现出色。BERT和GPT都基于此架构。"
        
        keywords = keyword_extractor.extract_keywords(text, domain="AI", language="mixed")
        
        # 应该识别出技术术语
        terms = [k.term.lower() for k in keywords]
        assert any(term in terms for term in ["transformer", "attention", "nlp", "bert", "gpt"])


class TestContentScorer:
    """内容评分器测试"""
    
    @pytest.fixture
    def content_scorer(self):
        """创建内容评分器实例"""
        return ContentScorer()
    
    def test_calculate_importance_score(self, content_scorer):
        """测试重要性评分计算"""
        content = ProcessedContent(
            content_id="test_1",
            title="重大突破：AI模型达到人类水平",
            cleaned_content="这是一个重要的AI突破...",
            keywords=[
                Keyword(term="AI", score=0.9, type="tech"),
                Keyword(term="突破", score=0.8, type="general"),
                Keyword(term="人类水平", score=0.85, type="achievement")
            ],
            source_authority=0.9,  # 权威来源
            publish_time=datetime.now(timezone.utc),  # 最新发布
            engagement_metrics={
                "views": 10000,
                "shares": 500,
                "comments": 100
            }
        )
        
        score = content_scorer.calculate_importance(content)
        
        assert 0 <= score <= 1
        assert score > 0.7  # 应该是高分（权威来源+新鲜度+高互动）
    
    def test_timeliness_factor(self, content_scorer):
        """测试时效性因子"""
        from datetime import timedelta
        
        # 1小时前的内容
        recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
        recent_factor = content_scorer._calculate_timeliness(recent_time)
        
        # 7天前的内容
        old_time = datetime.now(timezone.utc) - timedelta(days=7)
        old_factor = content_scorer._calculate_timeliness(old_time)
        
        assert recent_factor > old_factor
        assert 0 <= recent_factor <= 1
        assert 0 <= old_factor <= 1
    
    def test_engagement_factor(self, content_scorer):
        """测试互动度因子"""
        high_engagement = {
            "views": 100000,
            "shares": 5000,
            "comments": 1000
        }
        
        low_engagement = {
            "views": 100,
            "shares": 5,
            "comments": 1
        }
        
        high_score = content_scorer._calculate_engagement(high_engagement)
        low_score = content_scorer._calculate_engagement(low_engagement)
        
        assert high_score > low_score
        assert 0 <= high_score <= 1
        assert 0 <= low_score <= 1
    
    def test_keyword_relevance_factor(self, content_scorer):
        """测试关键词相关性因子"""
        high_relevance_keywords = [
            Keyword(term="GPT-5", score=0.95, type="product"),
            Keyword(term="breakthrough", score=0.9, type="achievement"),
            Keyword(term="AI", score=0.88, type="tech")
        ]
        
        low_relevance_keywords = [
            Keyword(term="update", score=0.3, type="general"),
            Keyword(term="news", score=0.2, type="general")
        ]
        
        high_score = content_scorer._calculate_keyword_relevance(high_relevance_keywords)
        low_score = content_scorer._calculate_keyword_relevance(low_relevance_keywords)
        
        assert high_score > low_score


class TestDataProcessor:
    """数据处理器集成测试"""
    
    @pytest.fixture
    def data_processor(self, redis_client):
        """创建数据处理器实例"""
        return DataProcessor(
            content_cleaner=ContentCleaner(),
            keyword_extractor=KeywordExtractor(),
            content_scorer=ContentScorer(),
            redis_client=redis_client
        )
    
    @pytest.fixture
    def sample_collected_data(self):
        """示例采集数据"""
        return CollectedData(
            data_id="test_123",
            source_id="source_1",
            source_type="rss",
            title="OpenAI发布GPT-5：性能提升50%",
            content="""
            <div>
                <p><strong>突破性进展！</strong>OpenAI今天宣布发布GPT-5模型。</p>
                <p>新模型在推理、编程和创意写作方面都有显著提升。</p>
                <script>tracking();</script>
                <p>详情：<a href="https://openai.com/gpt5">官方公告</a></p>
            </div>
            """,
            url="https://example.com/gpt5-news",
            author="Tech Reporter",
            publish_time=datetime.now(timezone.utc),
            tags=["AI", "OpenAI", "GPT"],
            source="TechNews",
            collected_time=datetime.now(timezone.utc)
        )
    
    @pytest.mark.asyncio
    async def test_process_single_content(self, data_processor, sample_collected_data):
        """测试处理单个内容"""
        processed = await data_processor.process_content(sample_collected_data)
        
        assert isinstance(processed, ProcessedContent)
        assert processed.content_id == sample_collected_data.data_id
        assert processed.title == sample_collected_data.title
        assert "script" not in processed.cleaned_content.lower()
        assert len(processed.keywords) > 0
        assert any(k.term in ["OpenAI", "GPT", "模型"] for k in processed.keywords)
        assert 0 <= processed.importance_score <= 1
        assert processed.quality_score > 0
    
    @pytest.mark.asyncio
    async def test_batch_processing(self, data_processor, sample_collected_data):
        """测试批量处理"""
        # 创建多个数据项
        data_items = []
        for i in range(5):
            item = sample_collected_data.model_copy()
            item.data_id = f"test_{i}"
            item.title = f"AI新闻 {i}"
            data_items.append(item)
        
        results = await data_processor.batch_process(data_items)
        
        assert len(results) == 5
        assert all(isinstance(r, ProcessedContent) for r in results)
        assert all(r.content_id == f"test_{i}" for i, r in enumerate(results))
    
    @pytest.mark.asyncio
    async def test_deduplication_check(self, data_processor):
        """测试去重检查"""
        # 模拟已存在的内容哈希
        content1 = "这是第一篇关于AI的新闻"
        content2 = "这是第一篇关于AI的新闻"  # 相同内容
        content3 = "这是另一篇不同的AI新闻"
        
        # 第一次检查应该不重复
        is_dup1 = await data_processor.is_duplicate(content1)
        assert not is_dup1
        
        # 第二次检查相同内容应该重复
        is_dup2 = await data_processor.is_duplicate(content2)
        assert is_dup2
        
        # 不同内容不应该重复
        is_dup3 = await data_processor.is_duplicate(content3)
        assert not is_dup3
    
    @pytest.mark.asyncio
    async def test_error_handling(self, data_processor):
        """测试错误处理"""
        # 创建一个有问题的数据项
        bad_data = CollectedData(
            data_id="bad_data",
            source_id="source_1",
            source_type="rss",
            title=None,  # 缺少标题
            content=None,  # 缺少内容
            url="https://example.com",
            collected_time=datetime.now(timezone.utc)
        )
        
        # 应该优雅地处理错误，返回None或默认值
        result = await data_processor.process_content(bad_data)
        assert result is None or (result.cleaned_content == "" and result.keywords == [])
    
    @pytest.mark.asyncio
    async def test_processing_pipeline_integration(self, data_processor, sample_collected_data):
        """测试完整的处理流程"""
        # 处理内容
        processed = await data_processor.process_content(sample_collected_data)
        
        # 验证所有步骤都执行了
        assert processed.cleaned_content != sample_collected_data.content  # 内容被清洗
        assert not any(tag in processed.cleaned_content for tag in ["<script>", "<div>"])  # HTML被移除
        assert len(processed.keywords) > 0  # 提取了关键词
        assert processed.importance_score > 0  # 计算了重要性分数
        assert len(processed.extracted_links) > 0  # 提取了链接
        assert processed.processing_time is not None  # 记录了处理时间