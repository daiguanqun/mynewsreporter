"""
数据处理器主类
"""
import asyncio
import hashlib
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import logging

from src.models.schemas import CollectedData, ProcessedContent, Keyword
from src.core.redis import RedisClient
from .content_cleaner import ContentCleaner
from .keyword_extractor import KeywordExtractor
from .content_scorer import ContentScorer

logger = logging.getLogger(__name__)


class DataProcessor:
    """数据处理器"""
    
    def __init__(
        self,
        content_cleaner: Optional[ContentCleaner] = None,
        keyword_extractor: Optional[KeywordExtractor] = None,
        content_scorer: Optional[ContentScorer] = None,
        redis_client: Optional[RedisClient] = None
    ):
        self.content_cleaner = content_cleaner or ContentCleaner()
        self.keyword_extractor = keyword_extractor or KeywordExtractor()
        self.content_scorer = content_scorer or ContentScorer()
        self.redis_client = redis_client
        self.dedup_expire = 86400 * 30  # 去重缓存30天
    
    async def process_content(self, collected_data: CollectedData) -> Optional[ProcessedContent]:
        """处理单个内容"""
        try:
            # 检查必要字段
            if not collected_data.title:
                logger.warning(f"缺少标题，跳过处理: {collected_data.data_id}")
                return None
            
            # 检查是否已处理过（基于URL）
            if await self._is_already_processed(collected_data.url):
                logger.info(f"内容已处理过，跳过: {collected_data.url}")
                return None
            
            # 清洗内容
            cleaning_result = self.content_cleaner.clean(collected_data.content or "")
            cleaned_content = cleaning_result.cleaned_content
            quality_score = cleaning_result.quality_score
            
            # 如果清洗后内容太少，跳过
            if len(cleaned_content) < 50:
                logger.warning(f"清洗后内容太少，跳过: {collected_data.data_id}")
                return None
            
            # 提取关键词
            keywords = self.keyword_extractor.extract_keywords(
                cleaned_content,
                max_keywords=20,
                domain="AI"
            )
            
            # 提取实体
            entities = self.keyword_extractor.extract_entities(cleaned_content)
            
            # 提取主题
            topics = self.keyword_extractor.extract_topics(cleaned_content)
            
            # 简单的情感分析（正面/负面/中性）
            sentiment = self._analyze_sentiment(cleaned_content)
            
            # 分类
            categories = self._categorize_content(keywords, topics, collected_data.tags)
            
            # 创建处理后的内容对象
            processed_content = ProcessedContent(
                content_id=collected_data.data_id,
                title=collected_data.title,
                cleaned_content=cleaned_content,
                summary=self._generate_summary(cleaned_content),
                keywords=keywords,
                entities=entities,
                categories=categories,
                tags=self._merge_tags(collected_data.tags, keywords),
                quality_score=quality_score,
                sentiment=sentiment,
                source=collected_data.source,
                author=collected_data.author,
                publish_time=collected_data.publish_time,
                url=collected_data.url,
                extracted_links=cleaning_result.extracted_links,
                source_authority=0.7,  # 默认权威性
                engagement_metrics={},  # 需要从外部获取
                processing_time=datetime.now(timezone.utc)
            )
            
            # 计算重要性分数
            processed_content.importance_score = self.content_scorer.calculate_importance(processed_content)
            
            # 计算内容哈希（用于去重）
            content_hash = self._calculate_content_hash(cleaned_content)
            
            # 标记为已处理
            await self._mark_as_processed(collected_data.url, content_hash)
            
            logger.info(f"处理完成: {processed_content.title[:50]}... (分数: {processed_content.importance_score:.2f})")
            
            return processed_content
            
        except Exception as e:
            logger.error(f"处理内容错误 {collected_data.data_id}: {e}")
            return None
    
    async def batch_process(self, collected_data_list: List[CollectedData]) -> List[ProcessedContent]:
        """批量处理内容"""
        if not collected_data_list:
            return []
        
        # 并发处理
        tasks = []
        for data in collected_data_list:
            task = self.process_content(data)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤成功的结果
        processed_contents = []
        for result in results:
            if isinstance(result, ProcessedContent):
                processed_contents.append(result)
            elif isinstance(result, Exception):
                logger.error(f"批量处理错误: {result}")
        
        # 按重要性排序
        processed_contents.sort(key=lambda x: x.importance_score, reverse=True)
        
        logger.info(f"批量处理完成: {len(processed_contents)}/{len(collected_data_list)} 成功")
        
        return processed_contents
    
    async def is_duplicate(self, content: str) -> bool:
        """检查内容是否重复"""
        if not self.redis_client:
            return False
        
        content_hash = self._calculate_content_hash(content)
        key = f"content_hash:{content_hash}"
        
        try:
            exists = await self.redis_client.exists(key)
            if not exists:
                # 如果不存在，添加到缓存
                await self.redis_client.set(key, "1", expire=self.dedup_expire)
            return exists
        except Exception as e:
            logger.error(f"检查重复错误: {e}")
            return False
    
    def _calculate_content_hash(self, content: str) -> str:
        """计算内容哈希"""
        # 标准化内容（去除空白差异）
        normalized = ' '.join(content.split())
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    
    async def _is_already_processed(self, url: str) -> bool:
        """检查URL是否已处理"""
        if not self.redis_client or not url:
            return False
        
        try:
            key = f"processed_url:{hashlib.md5(url.encode()).hexdigest()}"
            return await self.redis_client.exists(key)
        except Exception as e:
            logger.error(f"检查已处理URL错误: {e}")
            return False
    
    async def _mark_as_processed(self, url: str, content_hash: str):
        """标记为已处理"""
        if not self.redis_client or not url:
            return
        
        try:
            # 标记URL已处理
            url_key = f"processed_url:{hashlib.md5(url.encode()).hexdigest()}"
            await self.redis_client.set(url_key, "1", expire=self.dedup_expire)
            
            # 标记内容哈希
            hash_key = f"content_hash:{content_hash}"
            await self.redis_client.set(hash_key, "1", expire=self.dedup_expire)
            
        except Exception as e:
            logger.error(f"标记已处理错误: {e}")
    
    def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """简单的情感分析"""
        # 这里使用简单的规则，实际可以接入更复杂的模型
        positive_words = ['突破', '创新', '成功', '领先', '优秀', 'breakthrough', 'success', 'excellent']
        negative_words = ['失败', '问题', '风险', '担忧', '争议', 'failure', 'problem', 'risk']
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            sentiment = "positive"
            confidence = min(0.9, 0.5 + positive_count * 0.1)
        elif negative_count > positive_count:
            sentiment = "negative"
            confidence = min(0.9, 0.5 + negative_count * 0.1)
        else:
            sentiment = "neutral"
            confidence = 0.7
        
        return {
            "label": sentiment,
            "confidence": confidence,
            "scores": {
                "positive": positive_count / max(len(text.split()), 1),
                "negative": negative_count / max(len(text.split()), 1)
            }
        }
    
    def _categorize_content(self, keywords: List[Keyword], topics: List[str], tags: List[str]) -> List[str]:
        """内容分类"""
        categories = set()
        
        # 基于主题分类
        topic_category_map = {
            "深度学习": "技术",
            "自然语言处理": "技术",
            "计算机视觉": "技术",
            "机器学习": "技术",
            "大语言模型": "技术",
            "生成式AI": "应用",
        }
        
        for topic in topics:
            if topic in topic_category_map:
                categories.add(topic_category_map[topic])
        
        # 基于关键词分类
        keyword_terms = [kw.term.lower() for kw in keywords]
        
        if any(term in ['research', '研究', 'paper', '论文'] for term in keyword_terms):
            categories.add("研究")
        
        if any(term in ['product', '产品', 'launch', '发布', 'release'] for term in keyword_terms):
            categories.add("产品")
        
        if any(term in ['investment', '投资', 'funding', '融资'] for term in keyword_terms):
            categories.add("投资")
        
        # 如果没有分类，使用默认
        if not categories:
            categories.add("行业动态")
        
        return list(categories)
    
    def _merge_tags(self, original_tags: List[str], keywords: List[Keyword]) -> List[str]:
        """合并标签"""
        tags = set(original_tags) if original_tags else set()
        
        # 添加高分关键词作为标签
        for kw in keywords[:5]:  # 前5个关键词
            if kw.score > 0.5:
                tags.add(kw.term)
        
        return list(tags)
    
    def _generate_summary(self, content: str) -> str:
        """生成摘要（简单版本）"""
        # 取前200个字符作为摘要
        if len(content) <= 200:
            return content
        
        # 尝试在句号处截断
        summary = content[:200]
        last_period = summary.rfind('。')
        if last_period == -1:
            last_period = summary.rfind('.')
        
        if last_period > 100:
            summary = summary[:last_period + 1]
        else:
            summary = summary + "..."
        
        return summary