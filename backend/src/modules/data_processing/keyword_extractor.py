"""
关键词提取器
"""
import re
import jieba
import jieba.analyse
from typing import List, Dict, Any, Optional
from collections import Counter
import logging

from src.models.schemas import Keyword, Entity

logger = logging.getLogger(__name__)


class KeywordExtractor:
    """关键词提取器"""
    
    def __init__(self):
        # AI领域专业词汇
        self.ai_terms = {
            'gpt', 'bert', 'transformer', 'llm', 'nlp', 'cnn', 'rnn', 'lstm',
            'gan', 'vae', 'reinforcement learning', 'deep learning', 'machine learning',
            'neural network', 'attention', 'embedding', 'fine-tuning', 'prompt',
            'ai', 'artificial intelligence', '人工智能', '机器学习', '深度学习',
            '神经网络', '自然语言处理', '计算机视觉', '强化学习', '生成对抗网络',
            '大语言模型', '预训练', '微调', '提示词', '向量', '嵌入'
        }
        
        # 加载自定义词典
        self._load_custom_dict()
    
    def _load_custom_dict(self):
        """加载自定义词典"""
        try:
            # 添加AI专业术语到jieba词典
            for term in self.ai_terms:
                jieba.add_word(term, freq=1000)
        except Exception as e:
            logger.error(f"加载自定义词典错误: {e}")
    
    def extract_keywords(
        self, 
        text: str, 
        max_keywords: int = 20,
        domain: str = "general",
        language: str = "auto"
    ) -> List[Keyword]:
        """提取关键词"""
        if not text:
            return []
        
        try:
            # 检测语言
            if language == "auto":
                language = self._detect_language(text)
            
            keywords = []
            
            # 使用TF-IDF提取关键词
            tfidf_keywords = self._extract_tfidf_keywords(text, max_keywords)
            keywords.extend(tfidf_keywords)
            
            # 使用TextRank提取关键词
            textrank_keywords = self._extract_textrank_keywords(text, max_keywords // 2)
            keywords.extend(textrank_keywords)
            
            # 提取AI领域专业术语
            if domain == "AI" or self._is_ai_content(text):
                ai_keywords = self._extract_ai_keywords(text)
                keywords.extend(ai_keywords)
            
            # 合并和去重
            keywords = self._merge_keywords(keywords)
            
            # 按分数排序并限制数量
            keywords.sort(key=lambda k: k.score, reverse=True)
            return keywords[:max_keywords]
            
        except Exception as e:
            logger.error(f"关键词提取错误: {e}")
            return self._fallback_extraction(text, max_keywords)
    
    def _detect_language(self, text: str) -> str:
        """检测文本语言"""
        # 简单的语言检测
        chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', text))
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        
        if chinese_chars > english_words:
            return "zh"
        elif english_words > chinese_chars:
            return "en"
        else:
            return "mixed"
    
    def _extract_tfidf_keywords(self, text: str, topk: int) -> List[Keyword]:
        """使用TF-IDF提取关键词"""
        keywords = []
        
        try:
            # 使用jieba的TF-IDF
            tags = jieba.analyse.extract_tags(
                text, 
                topK=topk, 
                withWeight=True,
                allowPOS=('n', 'nr', 'ns', 'nt', 'nz', 'v', 'vd', 'vn', 'a', 'ad', 'an')
            )
            
            for word, weight in tags:
                if len(word) >= 2:  # 过滤单字
                    keyword = Keyword(
                        term=word,
                        score=float(weight),
                        type="tfidf"
                    )
                    keywords.append(keyword)
                    
        except Exception as e:
            logger.error(f"TF-IDF提取错误: {e}")
        
        return keywords
    
    def _extract_textrank_keywords(self, text: str, topk: int) -> List[Keyword]:
        """使用TextRank提取关键词"""
        keywords = []
        
        try:
            # 使用jieba的TextRank
            tags = jieba.analyse.textrank(
                text, 
                topK=topk, 
                withWeight=True,
                allowPOS=('n', 'nr', 'ns', 'nt', 'nz', 'v', 'vd', 'vn')
            )
            
            for word, weight in tags:
                if len(word) >= 2:
                    keyword = Keyword(
                        term=word,
                        score=float(weight) * 0.8,  # TextRank分数通常较高，稍微降低
                        type="textrank"
                    )
                    keywords.append(keyword)
                    
        except Exception as e:
            logger.error(f"TextRank提取错误: {e}")
        
        return keywords
    
    def _extract_ai_keywords(self, text: str) -> List[Keyword]:
        """提取AI领域专业关键词"""
        keywords = []
        text_lower = text.lower()
        
        for term in self.ai_terms:
            if term.lower() in text_lower:
                # 计算出现次数
                count = text_lower.count(term.lower())
                score = min(1.0, count * 0.3)
                
                keyword = Keyword(
                    term=term,
                    score=score,
                    type="ai_term"
                )
                keywords.append(keyword)
        
        return keywords
    
    def _is_ai_content(self, text: str) -> bool:
        """判断是否为AI相关内容"""
        text_lower = text.lower()
        ai_indicators = ['ai', '人工智能', 'machine learning', '机器学习', 
                        'deep learning', '深度学习', 'neural', '神经']
        
        for indicator in ai_indicators:
            if indicator in text_lower:
                return True
        return False
    
    def _merge_keywords(self, keywords: List[Keyword]) -> List[Keyword]:
        """合并和去重关键词"""
        keyword_dict = {}
        
        for kw in keywords:
            term_lower = kw.term.lower()
            if term_lower in keyword_dict:
                # 如果已存在，取最高分数
                if kw.score > keyword_dict[term_lower].score:
                    keyword_dict[term_lower] = kw
            else:
                keyword_dict[term_lower] = kw
        
        return list(keyword_dict.values())
    
    def _fallback_extraction(self, text: str, max_keywords: int) -> List[Keyword]:
        """后备关键词提取方法"""
        # 简单的词频统计
        words = jieba.cut(text)
        word_freq = Counter()
        
        for word in words:
            if len(word) >= 2 and not word.isdigit():
                word_freq[word] += 1
        
        keywords = []
        total = sum(word_freq.values())
        
        for word, freq in word_freq.most_common(max_keywords):
            keyword = Keyword(
                term=word,
                score=freq / total,
                type="frequency"
            )
            keywords.append(keyword)
        
        return keywords
    
    def extract_entities(self, text: str) -> List[Entity]:
        """提取命名实体"""
        entities = []
        
        try:
            # 简单的规则基础实体识别
            # 提取组织机构（包含"公司"、"研究院"等的词）
            org_patterns = [
                r'([^\s，。、]{2,10}(?:公司|集团|研究院|研究所|实验室|大学|学院))',
                r'((?:Google|Microsoft|OpenAI|Meta|Amazon|Apple|IBM|Intel|NVIDIA|阿里|腾讯|百度|字节跳动|华为))',
            ]
            
            for pattern in org_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    entity = Entity(
                        text=match,
                        label="ORG",
                        confidence=0.8
                    )
                    entities.append(entity)
            
            # 提取产品/技术名称
            product_patterns = [
                r'(GPT-\d+\.?\d*)',
                r'(BERT|RoBERTa|DALL-E|Stable Diffusion|Midjourney)',
                r'(ChatGPT|Claude|Gemini|LLaMA|PaLM)',
            ]
            
            for pattern in product_patterns:
                matches = re.findall(pattern, text, re.I)
                for match in matches:
                    entity = Entity(
                        text=match,
                        label="PRODUCT",
                        confidence=0.9
                    )
                    entities.append(entity)
            
            # 去重
            seen = set()
            unique_entities = []
            for entity in entities:
                key = f"{entity.text}:{entity.label}"
                if key not in seen:
                    seen.add(key)
                    unique_entities.append(entity)
            
            return unique_entities
            
        except Exception as e:
            logger.error(f"实体提取错误: {e}")
            return []
    
    def extract_topics(self, text: str) -> List[str]:
        """提取主题"""
        topics = []
        
        try:
            # 基于关键词聚类的简单主题提取
            keywords = self.extract_keywords(text, max_keywords=30)
            
            # AI相关主题
            ai_topics = {
                "深度学习": ["深度学习", "神经网络", "deep learning", "neural network"],
                "自然语言处理": ["nlp", "自然语言", "文本", "语言模型", "language"],
                "计算机视觉": ["视觉", "图像", "vision", "image", "cv"],
                "生成式AI": ["生成", "generate", "gan", "diffusion", "创作"],
                "大语言模型": ["llm", "大模型", "语言模型", "gpt", "claude"],
                "机器学习": ["机器学习", "machine learning", "ml", "算法"],
            }
            
            keyword_terms = [kw.term.lower() for kw in keywords]
            
            for topic, indicators in ai_topics.items():
                for indicator in indicators:
                    if any(indicator in term for term in keyword_terms):
                        topics.append(topic)
                        break
            
            return list(set(topics))  # 去重
            
        except Exception as e:
            logger.error(f"主题提取错误: {e}")
            return []