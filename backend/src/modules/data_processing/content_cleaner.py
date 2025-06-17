"""
内容清洗器
"""
import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


class CleaningResult:
    """清洗结果"""
    def __init__(self):
        self.cleaned_content: str = ""
        self.extracted_links: List[str] = []
        self.removed_elements: List[str] = []
        self.quality_score: float = 0.0


class ContentCleaner:
    """内容清洗器"""
    
    def __init__(self):
        # 需要移除的HTML标签
        self.remove_tags = ['script', 'style', 'noscript', 'iframe', 'object', 'embed']
        # 广告相关的类名和ID
        self.ad_patterns = [
            r'ad[s]?[-_]?', r'banner', r'sponsor', r'promo', r'advertis',
            r'popup', r'overlay', r'modal', r'newsletter', r'subscribe'
        ]
        # 噪音词汇
        self.noise_words = ['点击这里', '查看更多', '立即购买', '免费下载', '广告']
    
    def clean(self, raw_content: str) -> CleaningResult:
        """执行完整的清洗流程"""
        result = CleaningResult()
        
        try:
            # HTML清洗
            cleaned_html = self.clean_html(raw_content)
            
            # 提取纯文本
            text = self._extract_text(cleaned_html)
            
            # 文本清洗
            text = self.normalize_whitespace(text)
            text = self.remove_noise(text)
            
            # 提取链接
            result.extracted_links = self.extract_links(raw_content)
            
            # 计算质量分数
            result.quality_score = self._calculate_quality_score(text, raw_content)
            
            result.cleaned_content = text
            
        except Exception as e:
            logger.error(f"内容清洗错误: {e}")
            result.cleaned_content = self._basic_clean(raw_content)
            result.quality_score = 0.3
        
        return result
    
    def clean_html(self, html_content: str) -> str:
        """清洗HTML内容"""
        if not html_content:
            return ""
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 移除脚本和样式
            for tag in self.remove_tags:
                for element in soup.find_all(tag):
                    element.decompose()
            
            # 移除广告元素
            self._remove_ads(soup)
            
            # 移除隐藏元素
            for element in soup.find_all(style=re.compile(r'display:\s*none')):
                element.decompose()
            
            # 移除注释
            for comment in soup.find_all(text=lambda text: isinstance(text, str) and text.strip().startswith('<!--')):
                comment.extract()
            
            return str(soup)
            
        except Exception as e:
            logger.error(f"HTML清洗错误: {e}")
            return html_content
    
    def _remove_ads(self, soup: BeautifulSoup):
        """移除广告元素"""
        for pattern in self.ad_patterns:
            # 按class查找
            for element in soup.find_all(class_=re.compile(pattern, re.I)):
                element.decompose()
            
            # 按id查找
            for element in soup.find_all(id=re.compile(pattern, re.I)):
                element.decompose()
    
    def _extract_text(self, html_content: str) -> str:
        """从HTML提取纯文本"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            # 获取文本，保留换行
            text = soup.get_text(separator='\n', strip=True)
            return text
        except:
            # 基本的HTML标签移除
            text = re.sub(r'<[^>]+>', ' ', html_content)
            return text
    
    def normalize_whitespace(self, text: str) -> str:
        """标准化空白字符"""
        if not text:
            return ""
        
        # 替换各种空白字符为空格
        text = re.sub(r'[\t\r\f\v]+', ' ', text)
        
        # 多个空格替换为单个
        text = re.sub(r' +', ' ', text)
        
        # 多个换行替换为最多两个
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # 去除首尾空白
        text = text.strip()
        
        return text
    
    def remove_special_chars(self, text: str, keep_punctuation: bool = True) -> str:
        """移除特殊字符"""
        if not text:
            return ""
        
        if keep_punctuation:
            # 保留基本标点符号
            pattern = r'[^\w\s\u4e00-\u9fa5。，、；：？！""''（）《》【】\-\.\,\;\:\?\!\"\'\(\)\[\]]'
        else:
            # 只保留字母数字和中文
            pattern = r'[^\w\s\u4e00-\u9fa5]'
        
        text = re.sub(pattern, ' ', text)
        text = re.sub(r' +', ' ', text)
        
        return text.strip()
    
    def remove_noise(self, text: str) -> str:
        """移除噪音内容"""
        if not text:
            return ""
        
        # 移除噪音词汇
        for word in self.noise_words:
            text = text.replace(word, '')
        
        # 移除重复的标点
        text = re.sub(r'([。！？])\1+', r'\1', text)
        text = re.sub(r'([\.!?])\1+', r'\1', text)
        
        # 移除过短的行（可能是导航等）
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if len(line) > 10 or (line and not line.isdigit()):
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def extract_links(self, html_content: str) -> List[str]:
        """提取所有链接"""
        links = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.startswith('http'):
                    links.append(href)
        except Exception as e:
            logger.error(f"提取链接错误: {e}")
            # 使用正则作为后备
            pattern = r'href=[\'"]?(https?://[^\'" >]+)'
            links = re.findall(pattern, html_content)
        
        return list(set(links))  # 去重
    
    def _calculate_quality_score(self, cleaned_text: str, raw_content: str) -> float:
        """计算内容质量分数"""
        if not cleaned_text:
            return 0.0
        
        score = 1.0
        
        # 长度检查
        text_length = len(cleaned_text)
        if text_length < 100:
            score *= 0.5
        elif text_length < 300:
            score *= 0.8
        
        # 内容保留率
        if raw_content:
            retention_rate = len(cleaned_text) / len(raw_content)
            if retention_rate < 0.1:
                score *= 0.7
            elif retention_rate > 0.9:
                score *= 0.9  # 可能清洗不够
        
        # 检查是否包含中文或英文内容
        has_chinese = bool(re.search(r'[\u4e00-\u9fa5]', cleaned_text))
        has_english = bool(re.search(r'[a-zA-Z]{3,}', cleaned_text))
        
        if not (has_chinese or has_english):
            score *= 0.3
        
        # 检查是否有过多的特殊字符
        special_char_ratio = len(re.findall(r'[^\w\s\u4e00-\u9fa5]', cleaned_text)) / max(text_length, 1)
        if special_char_ratio > 0.3:
            score *= 0.8
        
        return max(0.0, min(1.0, score))
    
    def _basic_clean(self, text: str) -> str:
        """基础清洗（作为后备方案）"""
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', ' ', text)
        # 标准化空白
        text = re.sub(r'\s+', ' ', text)
        return text.strip()