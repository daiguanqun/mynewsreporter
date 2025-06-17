"""
内容评分器
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import math
import logging

from src.models.schemas import ProcessedContent, Keyword

logger = logging.getLogger(__name__)


class ContentScorer:
    """内容评分器"""
    
    def __init__(self):
        # 权重配置
        self.weights = {
            'timeliness': 0.25,      # 时效性
            'authority': 0.20,       # 权威性
            'relevance': 0.20,       # 相关性
            'engagement': 0.15,      # 互动度
            'quality': 0.10,         # 质量
            'uniqueness': 0.10       # 独特性
        }
        
        # 权威来源配置
        self.authority_sources = {
            # 国际知名AI机构和公司
            'openai': 1.0,
            'google': 0.95,
            'microsoft': 0.95,
            'meta': 0.9,
            'deepmind': 0.95,
            'anthropic': 0.9,
            'nvidia': 0.85,
            
            # 知名科技媒体
            'techcrunch': 0.8,
            'verge': 0.75,
            'wired': 0.75,
            'mit technology review': 0.85,
            'ieee': 0.85,
            
            # 学术机构
            'arxiv': 0.9,
            'nature': 0.95,
            'science': 0.95,
            
            # 中文权威源
            '新华社': 0.85,
            '人民日报': 0.85,
            '中科院': 0.9,
            '清华大学': 0.85,
            '北京大学': 0.85,
        }
        
        # 重要关键词配置
        self.important_keywords = {
            'breakthrough': 1.0,
            'revolutionary': 0.9,
            'state-of-the-art': 0.85,
            'novel': 0.8,
            'significant': 0.75,
            '突破': 1.0,
            '革命性': 0.9,
            '重大': 0.85,
            '创新': 0.8,
            '首次': 0.85,
            '最新': 0.7,
        }
    
    def calculate_importance(self, content: ProcessedContent) -> float:
        """计算内容重要性分数"""
        try:
            scores = {
                'timeliness': self._calculate_timeliness(content.publish_time),
                'authority': self._calculate_authority(content.source, content.source_authority),
                'relevance': self._calculate_relevance(content.keywords, content.categories),
                'engagement': self._calculate_engagement(content.engagement_metrics),
                'quality': content.quality_score if hasattr(content, 'quality_score') else 0.5,
                'uniqueness': self._calculate_uniqueness(content.keywords)
            }
            
            # 加权计算总分
            total_score = 0.0
            for factor, score in scores.items():
                weight = self.weights.get(factor, 0.0)
                total_score += score * weight
            
            # 应用提升因子
            boost_factor = self._calculate_boost_factor(content)
            total_score *= boost_factor
            
            # 确保分数在0-1范围内
            return max(0.0, min(1.0, total_score))
            
        except Exception as e:
            logger.error(f"计算重要性分数错误: {e}")
            return 0.5  # 默认中等分数
    
    def _calculate_timeliness(self, publish_time: Optional[datetime]) -> float:
        """计算时效性分数"""
        if not publish_time:
            return 0.3
        
        try:
            # 确保时间有时区信息
            if publish_time.tzinfo is None:
                publish_time = publish_time.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            age = now - publish_time
            
            # 基于时间衰减的评分
            if age < timedelta(hours=1):
                return 1.0
            elif age < timedelta(hours=6):
                return 0.9
            elif age < timedelta(days=1):
                return 0.8
            elif age < timedelta(days=3):
                return 0.6
            elif age < timedelta(days=7):
                return 0.4
            elif age < timedelta(days=30):
                return 0.2
            else:
                return 0.1
                
        except Exception as e:
            logger.error(f"计算时效性错误: {e}")
            return 0.3
    
    def _calculate_authority(self, source: Optional[str], base_authority: float) -> float:
        """计算权威性分数"""
        if not source:
            return base_authority
        
        source_lower = source.lower()
        
        # 检查已知权威源
        for authority_source, score in self.authority_sources.items():
            if authority_source in source_lower:
                return max(score, base_authority)
        
        # 如果有基础权威分数，使用它
        if base_authority > 0:
            return base_authority
        
        # 默认权威分数
        return 0.5
    
    def _calculate_relevance(self, keywords: List[Keyword], categories: List[str]) -> float:
        """计算相关性分数"""
        score = 0.5  # 基础分数
        
        # 基于关键词的相关性
        if keywords:
            # AI相关关键词
            ai_keywords = ['ai', 'artificial intelligence', '人工智能', 'machine learning', 
                          '机器学习', 'deep learning', '深度学习', 'neural', '神经']
            
            keyword_terms = [kw.term.lower() for kw in keywords]
            ai_keyword_count = sum(1 for term in keyword_terms 
                                  if any(ai_kw in term for ai_kw in ai_keywords))
            
            if ai_keyword_count > 0:
                score += min(0.3, ai_keyword_count * 0.1)
        
        # 基于分类的相关性
        if categories:
            ai_categories = ['技术', '研究', 'AI', '人工智能', 'Technology', 'Research']
            category_match = any(cat in ai_categories for cat in categories)
            if category_match:
                score += 0.2
        
        return min(1.0, score)
    
    def _calculate_engagement(self, metrics: Optional[Dict[str, Any]]) -> float:
        """计算互动度分数"""
        if not metrics:
            return 0.5
        
        try:
            views = metrics.get('views', 0)
            shares = metrics.get('shares', 0)
            comments = metrics.get('comments', 0)
            likes = metrics.get('likes', 0)
            
            # 对数归一化处理
            view_score = math.log10(max(1, views)) / 6  # 假设最大100万浏览
            share_score = math.log10(max(1, shares)) / 4  # 假设最大1万分享
            comment_score = math.log10(max(1, comments)) / 3  # 假设最大1千评论
            like_score = math.log10(max(1, likes)) / 5  # 假设最大10万点赞
            
            # 加权平均
            engagement_score = (
                view_score * 0.2 +
                share_score * 0.3 +
                comment_score * 0.3 +
                like_score * 0.2
            )
            
            return max(0.0, min(1.0, engagement_score))
            
        except Exception as e:
            logger.error(f"计算互动度错误: {e}")
            return 0.5
    
    def _calculate_uniqueness(self, keywords: List[Keyword]) -> float:
        """计算独特性分数"""
        if not keywords:
            return 0.5
        
        # 基于关键词的独特性
        unique_score = 0.5
        
        # 检查是否包含独特或创新的关键词
        unique_terms = ['首次', 'first', '创新', 'innovative', '突破', 'breakthrough',
                       '新型', 'novel', '独家', 'exclusive', '原创', 'original']
        
        keyword_terms = [kw.term.lower() for kw in keywords]
        for term in unique_terms:
            if any(term in kw_term for kw_term in keyword_terms):
                unique_score += 0.1
        
        return min(1.0, unique_score)
    
    def _calculate_boost_factor(self, content: ProcessedContent) -> float:
        """计算提升因子"""
        boost = 1.0
        
        # 标题包含重要关键词
        if content.title:
            title_lower = content.title.lower()
            for keyword, factor in self.important_keywords.items():
                if keyword in title_lower:
                    boost = max(boost, 1.0 + (factor - 1.0) * 0.5)
        
        # 多个权威实体提及
        if hasattr(content, 'entities') and content.entities:
            org_entities = [e for e in content.entities if e.label == "ORG"]
            if len(org_entities) >= 3:
                boost *= 1.1
        
        # 高质量内容
        if hasattr(content, 'quality_score') and content.quality_score > 0.8:
            boost *= 1.05
        
        return boost
    
    def _calculate_keyword_relevance(self, keywords: List[Keyword]) -> float:
        """计算关键词相关性分数（用于测试）"""
        if not keywords:
            return 0.0
        
        # 计算平均关键词分数
        if len(keywords) > 0:
            avg_score = sum(kw.score for kw in keywords) / len(keywords)
            return min(1.0, avg_score)
        
        return 0.0