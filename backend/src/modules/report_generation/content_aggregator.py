"""
内容聚合器
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import logging

from src.models.schemas import ProcessedContent, ReportSection

logger = logging.getLogger(__name__)


class ContentAggregator:
    """内容聚合器"""
    
    def aggregate_by_time_range(
        self,
        contents: List[ProcessedContent],
        start_time: datetime,
        end_time: datetime
    ) -> List[ProcessedContent]:
        """按时间范围聚合内容"""
        if not contents:
            return []
        
        # 确保时间有时区信息
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)
        
        filtered_contents = []
        for content in contents:
            if content.publish_time:
                # 确保发布时间有时区信息
                publish_time = content.publish_time
                if publish_time.tzinfo is None:
                    publish_time = publish_time.replace(tzinfo=timezone.utc)
                
                if start_time <= publish_time <= end_time:
                    filtered_contents.append(content)
            else:
                # 如果没有发布时间，使用处理时间
                if hasattr(content, 'processing_time') and content.processing_time:
                    processing_time = content.processing_time
                    if processing_time.tzinfo is None:
                        processing_time = processing_time.replace(tzinfo=timezone.utc)
                    
                    if start_time <= processing_time <= end_time:
                        filtered_contents.append(content)
        
        return filtered_contents
    
    def aggregate_by_category(
        self,
        contents: List[ProcessedContent]
    ) -> Dict[str, List[ProcessedContent]]:
        """按分类聚合内容"""
        categorized = defaultdict(list)
        
        for content in contents:
            if content.categories:
                for category in content.categories:
                    categorized[category].append(content)
            else:
                categorized["未分类"].append(content)
        
        # 按每个分类中的内容重要性排序
        for category in categorized:
            categorized[category].sort(
                key=lambda x: x.importance_score,
                reverse=True
            )
        
        return dict(categorized)
    
    def aggregate_by_source(
        self,
        contents: List[ProcessedContent]
    ) -> Dict[str, List[ProcessedContent]]:
        """按来源聚合内容"""
        source_grouped = defaultdict(list)
        
        for content in contents:
            source = content.source or "未知来源"
            source_grouped[source].append(content)
        
        # 按重要性排序
        for source in source_grouped:
            source_grouped[source].sort(
                key=lambda x: x.importance_score,
                reverse=True
            )
        
        return dict(source_grouped)
    
    def aggregate_by_keywords(
        self,
        contents: List[ProcessedContent],
        min_score: float = 0.5
    ) -> Dict[str, List[ProcessedContent]]:
        """按关键词聚合内容"""
        keyword_grouped = defaultdict(list)
        
        for content in contents:
            if content.keywords:
                for keyword in content.keywords:
                    if keyword.score >= min_score:
                        keyword_grouped[keyword.term].append(content)
        
        # 按关键词出现频率排序
        sorted_keywords = sorted(
            keyword_grouped.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        return dict(sorted_keywords)
    
    def aggregate_by_entity(
        self,
        contents: List[ProcessedContent],
        entity_type: Optional[str] = None
    ) -> Dict[str, List[ProcessedContent]]:
        """按实体聚合内容"""
        entity_grouped = defaultdict(list)
        
        for content in contents:
            if hasattr(content, 'entities') and content.entities:
                for entity in content.entities:
                    if entity_type is None or entity.label == entity_type:
                        entity_grouped[entity.text].append(content)
        
        # 按实体出现频率排序
        sorted_entities = sorted(
            entity_grouped.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        return dict(sorted_entities)
    
    def sort_by_importance(
        self,
        contents: List[ProcessedContent]
    ) -> List[ProcessedContent]:
        """按重要性排序"""
        return sorted(
            contents,
            key=lambda x: x.importance_score,
            reverse=True
        )
    
    def sort_by_time(
        self,
        contents: List[ProcessedContent],
        ascending: bool = False
    ) -> List[ProcessedContent]:
        """按时间排序"""
        def get_time(content):
            if content.publish_time:
                return content.publish_time
            elif hasattr(content, 'processing_time') and content.processing_time:
                return content.processing_time
            else:
                return datetime.min.replace(tzinfo=timezone.utc)
        
        return sorted(
            contents,
            key=get_time,
            reverse=not ascending
        )
    
    def apply_filters(
        self,
        contents: List[ProcessedContent],
        filters: Dict[str, Any]
    ) -> List[ProcessedContent]:
        """应用过滤器"""
        filtered_contents = contents
        
        for field, condition in filters.items():
            if isinstance(condition, dict):
                # 复杂条件
                if "$gte" in condition:
                    threshold = condition["$gte"]
                    filtered_contents = [
                        c for c in filtered_contents
                        if self._get_nested_value(c, field) >= threshold
                    ]
                elif "$lte" in condition:
                    threshold = condition["$lte"]
                    filtered_contents = [
                        c for c in filtered_contents
                        if self._get_nested_value(c, field) <= threshold
                    ]
                elif "$in" in condition:
                    values = condition["$in"]
                    filtered_contents = [
                        c for c in filtered_contents
                        if self._get_nested_value(c, field) in values
                    ]
            elif isinstance(condition, list):
                # 列表条件（包含任意值）
                filtered_contents = [
                    c for c in filtered_contents
                    if any(
                        val in self._get_nested_value(c, field, default=[])
                        for val in condition
                    )
                ]
            else:
                # 简单相等条件
                filtered_contents = [
                    c for c in filtered_contents
                    if self._get_nested_value(c, field) == condition
                ]
        
        return filtered_contents
    
    def limit_items(
        self,
        contents: List[ProcessedContent],
        max_items: int
    ) -> List[ProcessedContent]:
        """限制项目数量"""
        return contents[:max_items]
    
    def group_by_date(
        self,
        contents: List[ProcessedContent]
    ) -> Dict[str, List[ProcessedContent]]:
        """按日期分组"""
        date_grouped = defaultdict(list)
        
        for content in contents:
            if content.publish_time:
                date_key = content.publish_time.date().isoformat()
            elif hasattr(content, 'processing_time') and content.processing_time:
                date_key = content.processing_time.date().isoformat()
            else:
                date_key = "未知日期"
            
            date_grouped[date_key].append(content)
        
        # 按日期排序
        sorted_dates = sorted(date_grouped.items(), reverse=True)
        
        return dict(sorted_dates)
    
    def calculate_statistics(
        self,
        contents: List[ProcessedContent]
    ) -> Dict[str, Any]:
        """计算统计信息"""
        if not contents:
            return {
                "total_count": 0,
                "avg_importance_score": 0,
                "categories": {},
                "sources": {},
                "sentiment_distribution": {},
                "date_range": None
            }
        
        # 基本统计
        total_count = len(contents)
        avg_importance = sum(c.importance_score for c in contents) / total_count
        
        # 分类统计
        category_stats = defaultdict(int)
        for content in contents:
            if content.categories:
                for category in content.categories:
                    category_stats[category] += 1
        
        # 来源统计
        source_stats = defaultdict(int)
        for content in contents:
            source = content.source or "未知来源"
            source_stats[source] += 1
        
        # 情感统计
        sentiment_stats = defaultdict(int)
        for content in contents:
            if content.sentiment and isinstance(content.sentiment, dict):
                label = content.sentiment.get("label", "neutral")
                sentiment_stats[label] += 1
        
        # 时间范围
        times = []
        for content in contents:
            if content.publish_time:
                times.append(content.publish_time)
            elif hasattr(content, 'processing_time') and content.processing_time:
                times.append(content.processing_time)
        
        date_range = None
        if times:
            min_time = min(times)
            max_time = max(times)
            date_range = {
                "start": min_time.isoformat(),
                "end": max_time.isoformat(),
                "days": (max_time - min_time).days + 1
            }
        
        return {
            "total_count": total_count,
            "avg_importance_score": round(avg_importance, 3),
            "categories": dict(category_stats),
            "sources": dict(source_stats),
            "sentiment_distribution": dict(sentiment_stats),
            "date_range": date_range
        }
    
    def _get_nested_value(
        self,
        obj: Any,
        path: str,
        default: Any = None
    ) -> Any:
        """获取嵌套属性值"""
        try:
            parts = path.split(".")
            value = obj
            
            for part in parts:
                if hasattr(value, part):
                    value = getattr(value, part)
                elif isinstance(value, dict):
                    value = value.get(part)
                else:
                    return default
            
            return value
        except:
            return default
    
    def deduplicate_by_title(
        self,
        contents: List[ProcessedContent],
        similarity_threshold: float = 0.9
    ) -> List[ProcessedContent]:
        """基于标题去重"""
        if not contents:
            return []
        
        # 简单的去重策略：完全相同的标题
        seen_titles = set()
        unique_contents = []
        
        for content in contents:
            title_lower = content.title.lower().strip()
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                unique_contents.append(content)
        
        return unique_contents