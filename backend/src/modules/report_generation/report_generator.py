"""
报告生成器
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import uuid
import logging

from src.models.schemas import (
    ReportConfig, ReportTemplate, ReportSection,
    ProcessedContent, GeneratedReport
)
from .template_manager import TemplateManager
from .content_aggregator import ContentAggregator

logger = logging.getLogger(__name__)


class ReportGenerator:
    """报告生成器"""
    
    def __init__(
        self,
        template_manager: Optional[TemplateManager] = None,
        content_aggregator: Optional[ContentAggregator] = None,
        ai_client: Optional[Any] = None
    ):
        self.template_manager = template_manager or TemplateManager()
        self.content_aggregator = content_aggregator or ContentAggregator()
        self.ai_client = ai_client
    
    async def generate_report(
        self,
        report_config: ReportConfig
    ) -> GeneratedReport:
        """生成报告"""
        try:
            # 获取模板
            template = self.template_manager.get_template(report_config.template_id)
            if not template:
                # 使用默认模板
                template = self.template_manager.get_default_template(report_config.report_type)
                if not template:
                    raise ValueError(f"找不到报告模板: {report_config.template_id}")
            
            # 获取内容
            contents = await self._fetch_contents(report_config)
            
            # 生成报告标题
            title = self._generate_report_title(report_config, template)
            subtitle = self._generate_report_subtitle(report_config, contents)
            
            # 处理每个章节
            sections = []
            for section_template in sorted(template.sections, key=lambda s: s.order):
                section_content = await self._generate_section_content(
                    section_template,
                    contents,
                    report_config
                )
                
                # 创建章节副本并添加内容
                section = ReportSection(
                    section_id=section_template.section_id,
                    section_name=section_template.section_name,
                    section_type=section_template.section_type,
                    order=section_template.order,
                    content=section_content
                )
                sections.append(section)
            
            # 生成摘要
            summary = None
            if report_config.include_summary:
                summary = await self._generate_summary(contents)
            
            # 计算元数据
            metadata = {
                "total_items": len(contents),
                "generation_time": datetime.now(timezone.utc).isoformat(),
                "report_config": report_config.dict(),
                "statistics": self.content_aggregator.calculate_statistics(contents),
                "categories_covered": list(set(
                    cat for c in contents for cat in (c.categories or [])
                ))
            }
            
            # 创建报告
            report = GeneratedReport(
                report_id=str(uuid.uuid4()),
                title=title,
                subtitle=subtitle,
                report_type=report_config.report_type,
                sections=sections,
                summary=summary,
                metadata=metadata,
                generated_time=datetime.now(timezone.utc),
                template_used=template.template_id
            )
            
            logger.info(f"生成报告完成: {report.title} ({report.report_id})")
            
            return report
            
        except Exception as e:
            logger.error(f"生成报告错误: {e}")
            raise
    
    async def _fetch_contents(
        self,
        report_config: ReportConfig
    ) -> List[ProcessedContent]:
        """获取报告内容"""
        # 这里应该从数据库获取，现在返回空列表
        # 实际实现需要查询处理后的内容
        contents = []
        
        # 应用时间范围过滤
        if report_config.time_range:
            start_date = report_config.time_range.get("start_date")
            end_date = report_config.time_range.get("end_date")
            
            if start_date and end_date:
                # 转换为datetime
                if isinstance(start_date, str):
                    start_time = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
                else:
                    start_time = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
                
                if isinstance(end_date, str):
                    end_time = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
                else:
                    end_time = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)
                
                contents = self.content_aggregator.aggregate_by_time_range(
                    contents, start_time, end_time
                )
        
        # 应用分类过滤
        if report_config.categories:
            contents = self.content_aggregator.apply_filters(
                contents,
                {"categories": report_config.categories}
            )
        
        # 应用关键词过滤
        if report_config.keywords:
            # TODO: 实现关键词过滤
            pass
        
        return contents
    
    def _generate_report_title(
        self,
        report_config: ReportConfig,
        template: ReportTemplate
    ) -> str:
        """生成报告标题"""
        if report_config.report_type == "daily":
            date_str = datetime.now(timezone.utc).strftime("%Y年%m月%d日")
            return f"AI日报 - {date_str}"
        elif report_config.report_type == "weekly":
            # 计算周数
            now = datetime.now(timezone.utc)
            week_num = now.isocalendar()[1]
            return f"AI周报 - {now.year}年第{week_num}周"
        elif report_config.report_type == "monthly":
            date_str = datetime.now(timezone.utc).strftime("%Y年%m月")
            return f"AI月报 - {date_str}"
        else:
            return template.name
    
    def _generate_report_subtitle(
        self,
        report_config: ReportConfig,
        contents: List[ProcessedContent]
    ) -> str:
        """生成报告副标题"""
        total_count = len(contents)
        
        if total_count == 0:
            return "暂无相关内容"
        
        # 统计分类
        categories = set()
        for content in contents:
            if content.categories:
                categories.update(content.categories)
        
        category_str = "、".join(list(categories)[:3])
        if len(categories) > 3:
            category_str += "等"
        
        return f"共{total_count}条资讯，涵盖{category_str}领域"
    
    async def _generate_section_content(
        self,
        section: ReportSection,
        contents: List[ProcessedContent],
        report_config: ReportConfig
    ) -> Dict[str, Any]:
        """生成章节内容"""
        # 应用章节过滤器
        section_contents = contents
        if section.filters:
            section_contents = self.content_aggregator.apply_filters(
                contents,
                section.filters
            )
        
        # 限制数量
        if section.max_items:
            section_contents = self.content_aggregator.limit_items(
                section_contents,
                section.max_items
            )
        
        # 根据章节类型生成内容
        if section.section_type == "news_list":
            return self._generate_news_list(section_contents)
        elif section.section_type == "categorized_list":
            return self._generate_categorized_list(section_contents)
        elif section.section_type == "grouped_list":
            return self._generate_grouped_list(section_contents)
        elif section.section_type == "summary":
            return await self._generate_section_summary(section_contents)
        elif section.section_type == "executive_summary":
            return await self._generate_executive_summary(section_contents)
        elif section.section_type == "trend_analysis":
            return await self._generate_trend_analysis(section_contents)
        elif section.section_type == "insights":
            return await self._generate_insights(section_contents)
        elif section.section_type == "investment_summary":
            return self._generate_investment_summary(section_contents)
        else:
            return {"items": [], "type": section.section_type}
    
    def _generate_news_list(
        self,
        contents: List[ProcessedContent]
    ) -> Dict[str, Any]:
        """生成新闻列表"""
        items = []
        
        for content in contents:
            item = {
                "title": content.title,
                "summary": content.summary or content.cleaned_content[:200] + "...",
                "source": content.source,
                "author": content.author,
                "publish_time": content.publish_time.isoformat() if content.publish_time else None,
                "url": content.url,
                "importance_score": content.importance_score,
                "tags": content.tags[:5] if content.tags else []
            }
            items.append(item)
        
        return {
            "type": "news_list",
            "items": items,
            "count": len(items)
        }
    
    def _generate_categorized_list(
        self,
        contents: List[ProcessedContent]
    ) -> Dict[str, Any]:
        """生成分类列表"""
        categorized = self.content_aggregator.aggregate_by_category(contents)
        
        categories = []
        for category, category_contents in categorized.items():
            categories.append({
                "name": category,
                "items": self._generate_news_list(category_contents)["items"],
                "count": len(category_contents)
            })
        
        return {
            "type": "categorized_list",
            "categories": categories,
            "total_count": len(contents)
        }
    
    def _generate_grouped_list(
        self,
        contents: List[ProcessedContent]
    ) -> Dict[str, Any]:
        """生成分组列表（按实体）"""
        # 按组织实体分组
        entity_grouped = self.content_aggregator.aggregate_by_entity(
            contents,
            entity_type="ORG"
        )
        
        groups = []
        for entity, entity_contents in list(entity_grouped.items())[:10]:
            groups.append({
                "name": entity,
                "items": self._generate_news_list(entity_contents)["items"],
                "count": len(entity_contents)
            })
        
        return {
            "type": "grouped_list",
            "groups": groups,
            "total_count": len(contents)
        }
    
    async def _generate_section_summary(
        self,
        contents: List[ProcessedContent]
    ) -> Dict[str, Any]:
        """生成章节摘要"""
        if not contents:
            return {
                "type": "summary",
                "text": "本节暂无内容。"
            }
        
        # 简单的摘要生成
        summary_text = f"本节共收录{len(contents)}条相关资讯。"
        
        # 如果有AI客户端，使用AI生成摘要
        if self.ai_client:
            summary_text = await self._generate_ai_summary(contents)
        
        return {
            "type": "summary",
            "text": summary_text
        }
    
    async def _generate_executive_summary(
        self,
        contents: List[ProcessedContent]
    ) -> Dict[str, Any]:
        """生成执行摘要"""
        stats = self.content_aggregator.calculate_statistics(contents)
        
        # 关键要点
        key_points = []
        
        # 最重要的新闻
        top_news = self.content_aggregator.sort_by_importance(contents)[:3]
        for news in top_news:
            key_points.append(f"• {news.title}")
        
        # 热门类别
        if stats["categories"]:
            top_categories = sorted(
                stats["categories"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            category_str = "、".join([f"{cat[0]}({cat[1]}条)" for cat in top_categories])
            key_points.append(f"• 主要涉及领域：{category_str}")
        
        summary_text = (
            f"本期报告共收录{stats['total_count']}条AI领域重要资讯，"
            f"平均重要性评分{stats['avg_importance_score']}。"
        )
        
        return {
            "type": "executive_summary",
            "summary": summary_text,
            "key_points": key_points,
            "statistics": stats
        }
    
    async def _generate_trend_analysis(
        self,
        contents: List[ProcessedContent]
    ) -> Dict[str, Any]:
        """生成趋势分析"""
        # 按关键词聚合
        keyword_trends = self.content_aggregator.aggregate_by_keywords(contents)
        
        # 取前10个热门关键词
        top_keywords = list(keyword_trends.items())[:10]
        
        trends = []
        for keyword, keyword_contents in top_keywords:
            trends.append({
                "keyword": keyword,
                "count": len(keyword_contents),
                "trend": "rising"  # 简化处理，实际需要历史数据对比
            })
        
        return {
            "type": "trend_analysis",
            "trends": trends,
            "analysis": "基于本期内容的关键词分析显示，以上主题受到较多关注。"
        }
    
    def _generate_investment_summary(
        self,
        contents: List[ProcessedContent]
    ) -> Dict[str, Any]:
        """生成投资分析摘要"""
        investment_items = []
        
        for content in contents:
            # 简单的投资信息提取
            item = {
                "title": content.title,
                "summary": content.summary,
                "companies": [e.text for e in (content.entities or []) if e.label == "ORG"],
                "url": content.url
            }
            investment_items.append(item)
        
        return {
            "type": "investment_summary",
            "items": investment_items,
            "total_deals": len(investment_items)
        }
    
    async def _generate_summary(
        self,
        contents: List[ProcessedContent]
    ) -> str:
        """生成整体摘要"""
        if not contents:
            return "本期报告暂无内容。"
        
        # 简单的摘要
        stats = self.content_aggregator.calculate_statistics(contents)
        
        summary = (
            f"本期AI新闻报告共收录{stats['total_count']}条重要资讯，"
            f"时间范围涵盖{stats['date_range']['days'] if stats['date_range'] else 0}天。"
        )
        
        # 如果有AI客户端，生成更详细的摘要
        if self.ai_client:
            summary = await self._generate_ai_summary(contents)
        
        return summary
    
    async def _generate_insights(
        self,
        contents: List[ProcessedContent]
    ) -> Dict[str, Any]:
        """生成洞察分析"""
        insights = {
            "trend_analysis": "基于本期收录的内容分析...",
            "key_topics": [],
            "sentiment_distribution": {}
        }
        
        # 关键主题
        keyword_groups = self.content_aggregator.aggregate_by_keywords(contents)
        key_topics = [
            {"topic": kw, "count": len(items)}
            for kw, items in list(keyword_groups.items())[:5]
        ]
        insights["key_topics"] = key_topics
        
        # 情感分布
        sentiment_stats = {}
        for content in contents:
            if content.sentiment and isinstance(content.sentiment, dict):
                label = content.sentiment.get("label", "neutral")
                sentiment_stats[label] = sentiment_stats.get(label, 0) + 1
        
        insights["sentiment_distribution"] = sentiment_stats
        
        return {
            "type": "insights",
            "data": insights
        }
    
    async def _generate_ai_summary(
        self,
        contents: List[ProcessedContent],
        max_length: int = 500
    ) -> str:
        """使用AI生成摘要"""
        if not self.ai_client:
            return "AI摘要服务不可用"
        
        try:
            # 准备内容
            content_texts = []
            for content in contents[:10]:  # 限制输入数量
                content_texts.append(f"标题：{content.title}\n摘要：{content.summary or '无'}")
            
            prompt = f"""
            请为以下AI领域新闻生成一个简洁的中文摘要（不超过{max_length}字）：
            
            {chr(10).join(content_texts)}
            
            摘要应包括：
            1. 本期最重要的进展
            2. 主要趋势
            3. 值得关注的要点
            """
            
            response = await self.ai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是一个专业的AI领域新闻分析师。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_length,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"AI摘要生成错误: {e}")
            return "AI摘要生成失败"