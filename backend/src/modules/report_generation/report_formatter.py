"""
报告格式化器
"""
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging
import re

from src.models.schemas import GeneratedReport, ReportSection

logger = logging.getLogger(__name__)


class ReportFormatter:
    """报告格式化器"""
    
    def format_to_markdown(self, report: GeneratedReport) -> str:
        """格式化为Markdown"""
        lines = []
        
        # 标题
        lines.append(f"# {report.title}")
        lines.append("")
        
        # 副标题
        if report.subtitle:
            lines.append(f"*{report.subtitle}*")
            lines.append("")
        
        # 生成信息
        lines.append(f"**生成时间**: {self._format_datetime(report.generated_time)}")
        lines.append("")
        
        # 目录
        if len(report.sections) > 3:
            lines.append("## 目录")
            lines.append("")
            toc = self._generate_table_of_contents(report.sections)
            for item in toc:
                lines.append(f"- [{item['name']}]({item['anchor']})")
            lines.append("")
        
        # 摘要
        if report.summary:
            lines.append("## 摘要")
            lines.append("")
            lines.append(report.summary)
            lines.append("")
        
        # 各个章节
        for section in report.sections:
            lines.append(f"## {section.section_name}")
            lines.append("")
            
            section_md = self._format_section_markdown(section)
            lines.append(section_md)
            lines.append("")
        
        # 统计信息
        if report.metadata and "statistics" in report.metadata:
            lines.append("---")
            lines.append("")
            lines.append("### 统计信息")
            lines.append("")
            stats = report.metadata["statistics"]
            lines.append(f"- 总条数: {stats.get('total_count', 0)}")
            lines.append(f"- 平均重要性: {stats.get('avg_importance_score', 0):.2f}")
            
            if stats.get("categories"):
                lines.append("- 分类分布:")
                for cat, count in stats["categories"].items():
                    lines.append(f"  - {cat}: {count}条")
        
        return "\n".join(lines)
    
    def format_to_html(self, report: GeneratedReport) -> str:
        """格式化为HTML"""
        html_parts = []
        
        # HTML头部
        html_parts.append(self._generate_html_header(report))
        
        # 主体内容
        html_parts.append('<body>')
        html_parts.append('<div class="container">')
        
        # 标题区域
        html_parts.append('<header>')
        html_parts.append(f'<h1>{self._escape_html(report.title)}</h1>')
        if report.subtitle:
            html_parts.append(f'<p class="subtitle">{self._escape_html(report.subtitle)}</p>')
        html_parts.append(f'<p class="meta">生成时间: {self._format_datetime(report.generated_time)}</p>')
        html_parts.append('</header>')
        
        # 目录
        if len(report.sections) > 3:
            html_parts.append('<nav class="toc">')
            html_parts.append('<h2>目录</h2>')
            html_parts.append('<ul>')
            toc = self._generate_table_of_contents(report.sections)
            for item in toc:
                html_parts.append(f'<li><a href="{item["anchor"]}">{self._escape_html(item["name"])}</a></li>')
            html_parts.append('</ul>')
            html_parts.append('</nav>')
        
        # 摘要
        if report.summary:
            html_parts.append('<section class="summary">')
            html_parts.append('<h2>摘要</h2>')
            html_parts.append(f'<p>{self._escape_html(report.summary)}</p>')
            html_parts.append('</section>')
        
        # 主要内容
        html_parts.append('<main>')
        for section in report.sections:
            html_parts.append(f'<section id="{section.section_id}">')
            html_parts.append(f'<h2>{self._escape_html(section.section_name)}</h2>')
            section_html = self._format_section_html(section)
            html_parts.append(section_html)
            html_parts.append('</section>')
        html_parts.append('</main>')
        
        # 页脚
        html_parts.append('<footer>')
        html_parts.append('<p>本报告由AI新闻报告系统自动生成</p>')
        html_parts.append('</footer>')
        
        html_parts.append('</div>')
        html_parts.append('</body>')
        html_parts.append('</html>')
        
        return '\n'.join(html_parts)
    
    def format_to_json(self, report: GeneratedReport) -> str:
        """格式化为JSON"""
        # 转换为字典
        report_dict = {
            "report_id": report.report_id,
            "title": report.title,
            "subtitle": report.subtitle,
            "report_type": report.report_type,
            "summary": report.summary,
            "generated_time": report.generated_time.isoformat() if report.generated_time else None,
            "template_used": report.template_used,
            "sections": [],
            "metadata": report.metadata
        }
        
        # 处理章节
        for section in report.sections:
            section_dict = {
                "section_id": section.section_id,
                "section_name": section.section_name,
                "section_type": section.section_type,
                "order": section.order,
                "content": section.content
            }
            report_dict["sections"].append(section_dict)
        
        return json.dumps(report_dict, ensure_ascii=False, indent=2)
    
    def _format_section_markdown(self, section: ReportSection) -> str:
        """格式化章节为Markdown"""
        if not section.content:
            return "暂无内容"
        
        content = section.content
        section_type = content.get("type", section.section_type)
        
        if section_type == "news_list":
            return self._format_news_list_markdown(content)
        elif section_type == "categorized_list":
            return self._format_categorized_list_markdown(content)
        elif section_type == "grouped_list":
            return self._format_grouped_list_markdown(content)
        elif section_type == "summary":
            return content.get("text", "")
        elif section_type == "executive_summary":
            return self._format_executive_summary_markdown(content)
        elif section_type == "trend_analysis":
            return self._format_trend_analysis_markdown(content)
        elif section_type == "insights":
            return self._format_insights_markdown(content)
        elif section_type == "investment_summary":
            return self._format_investment_summary_markdown(content)
        else:
            return str(content)
    
    def _format_news_list_markdown(self, content: Dict[str, Any]) -> str:
        """格式化新闻列表为Markdown"""
        lines = []
        items = content.get("items", [])
        
        for i, item in enumerate(items, 1):
            lines.append(f"### {i}. {item['title']}")
            lines.append("")
            
            if item.get('summary'):
                lines.append(f"{item['summary']}")
                lines.append("")
            
            meta_parts = []
            if item.get('source'):
                meta_parts.append(f"来源: {item['source']}")
            if item.get('author'):
                meta_parts.append(f"作者: {item['author']}")
            if item.get('publish_time'):
                meta_parts.append(f"时间: {self._format_datetime_str(item['publish_time'])}")
            
            if meta_parts:
                lines.append(f"*{' | '.join(meta_parts)}*")
                lines.append("")
            
            if item.get('url'):
                lines.append(f"[查看详情]({item['url']})")
                lines.append("")
            
            if item.get('tags'):
                tags_str = ' '.join([f"`{tag}`" for tag in item['tags']])
                lines.append(f"标签: {tags_str}")
                lines.append("")
            
            lines.append("---")
            lines.append("")
        
        return '\n'.join(lines)
    
    def _format_categorized_list_markdown(self, content: Dict[str, Any]) -> str:
        """格式化分类列表为Markdown"""
        lines = []
        categories = content.get("categories", [])
        
        for category in categories:
            lines.append(f"### {category['name']} ({category['count']}条)")
            lines.append("")
            
            for item in category.get("items", []):
                lines.append(f"- **{item['title']}**")
                if item.get('summary'):
                    lines.append(f"  {item['summary'][:100]}...")
                if item.get('url'):
                    lines.append(f"  [详情]({item['url']})")
                lines.append("")
        
        return '\n'.join(lines)
    
    def _format_executive_summary_markdown(self, content: Dict[str, Any]) -> str:
        """格式化执行摘要为Markdown"""
        lines = []
        
        if content.get("summary"):
            lines.append(content["summary"])
            lines.append("")
        
        if content.get("key_points"):
            lines.append("**关键要点:**")
            lines.append("")
            for point in content["key_points"]:
                lines.append(point)
            lines.append("")
        
        return '\n'.join(lines)
    
    def _format_section_html(self, section: ReportSection) -> str:
        """格式化章节为HTML"""
        if not section.content:
            return "<p>暂无内容</p>"
        
        content = section.content
        section_type = content.get("type", section.section_type)
        
        if section_type == "news_list":
            return self._format_news_list_html(content)
        elif section_type == "categorized_list":
            return self._format_categorized_list_html(content)
        elif section_type == "summary":
            return f'<p>{self._escape_html(content.get("text", ""))}</p>'
        elif section_type == "executive_summary":
            return self._format_executive_summary_html(content)
        else:
            return f'<pre>{self._escape_html(str(content))}</pre>'
    
    def _format_news_list_html(self, content: Dict[str, Any]) -> str:
        """格式化新闻列表为HTML"""
        html_parts = ['<div class="news-list">']
        items = content.get("items", [])
        
        for item in items:
            html_parts.append('<article class="news-item">')
            html_parts.append(f'<h3>{self._escape_html(item["title"])}</h3>')
            
            if item.get('summary'):
                html_parts.append(f'<p class="summary">{self._escape_html(item["summary"])}</p>')
            
            html_parts.append('<div class="meta">')
            if item.get('source'):
                html_parts.append(f'<span class="source">来源: {self._escape_html(item["source"])}</span>')
            if item.get('publish_time'):
                html_parts.append(f'<span class="time">时间: {self._format_datetime_str(item["publish_time"])}</span>')
            html_parts.append('</div>')
            
            if item.get('url'):
                html_parts.append(f'<a href="{item["url"]}" target="_blank" class="read-more">查看详情</a>')
            
            html_parts.append('</article>')
        
        html_parts.append('</div>')
        return '\n'.join(html_parts)
    
    def _generate_html_header(self, report: GeneratedReport) -> str:
        """生成HTML头部"""
        style_config = {}
        if report.metadata and "template" in report.metadata:
            template = report.metadata["template"]
            if isinstance(template, dict) and "style_config" in template:
                style_config = template["style_config"]
        
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self._escape_html(report.title)}</title>
    <style>
        {self._generate_css_styles(style_config)}
    </style>
</head>"""
    
    def _generate_css_styles(self, style_config: Dict[str, Any]) -> str:
        """生成CSS样式"""
        primary_color = style_config.get("primary_color", "#1890ff")
        secondary_color = style_config.get("secondary_color", "#f0f0f0")
        text_color = style_config.get("text_color", "#333333")
        
        return f"""
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif;
            line-height: 1.6;
            color: {text_color};
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: white;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}
        header {{
            text-align: center;
            padding: 40px 0;
            border-bottom: 2px solid {secondary_color};
        }}
        h1 {{
            color: {primary_color};
            margin: 0 0 10px 0;
        }}
        h2 {{
            color: {primary_color};
            border-bottom: 1px solid {secondary_color};
            padding-bottom: 10px;
        }}
        .subtitle {{
            font-style: italic;
            color: #666;
            margin: 10px 0;
        }}
        .meta {{
            color: #999;
            font-size: 0.9em;
        }}
        .toc {{
            background-color: {secondary_color};
            padding: 20px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        .toc ul {{
            list-style-type: none;
            padding-left: 20px;
        }}
        .news-item {{
            margin: 20px 0;
            padding: 20px;
            border: 1px solid {secondary_color};
            border-radius: 5px;
        }}
        .news-item h3 {{
            margin-top: 0;
            color: {primary_color};
        }}
        .summary {{
            color: #666;
            margin: 10px 0;
        }}
        .read-more {{
            color: {primary_color};
            text-decoration: none;
        }}
        .read-more:hover {{
            text-decoration: underline;
        }}
        footer {{
            text-align: center;
            padding: 40px 0;
            border-top: 1px solid {secondary_color};
            color: #999;
            margin-top: 40px;
        }}
        """
    
    def _generate_table_of_contents(self, sections: List[ReportSection]) -> List[Dict[str, str]]:
        """生成目录"""
        toc = []
        for section in sections:
            toc.append({
                "name": section.section_name,
                "anchor": f"#{section.section_id}"
            })
        return toc
    
    def _format_datetime(self, dt: Optional[datetime], format: str = "%Y年%m月%d日 %H:%M", relative: bool = False) -> str:
        """格式化日期时间"""
        if not dt:
            return "未知时间"
        
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        if relative:
            # 计算相对时间
            now = datetime.now(timezone.utc)
            delta = now - dt
            
            if delta.days > 7:
                return dt.strftime(format)
            elif delta.days > 0:
                return f"{delta.days}天前"
            elif delta.seconds > 3600:
                return f"{delta.seconds // 3600}小时前"
            elif delta.seconds > 60:
                return f"{delta.seconds // 60}分钟前"
            else:
                return "刚刚"
        else:
            return dt.strftime(format)
    
    def _format_datetime_str(self, dt_str: str) -> str:
        """格式化日期时间字符串"""
        try:
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            return self._format_datetime(dt)
        except:
            return dt_str
    
    def _escape_html(self, text: str) -> str:
        """转义HTML特殊字符"""
        if not text:
            return ""
        
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )
    
    def _format_trend_analysis_markdown(self, content: Dict[str, Any]) -> str:
        """格式化趋势分析为Markdown"""
        lines = []
        
        if content.get("analysis"):
            lines.append(content["analysis"])
            lines.append("")
        
        trends = content.get("trends", [])
        if trends:
            lines.append("| 关键词 | 出现次数 | 趋势 |")
            lines.append("|--------|----------|------|")
            for trend in trends:
                trend_icon = "📈" if trend.get("trend") == "rising" else "➡️"
                lines.append(f"| {trend['keyword']} | {trend['count']} | {trend_icon} |")
        
        return '\n'.join(lines)
    
    def _format_insights_markdown(self, content: Dict[str, Any]) -> str:
        """格式化洞察分析为Markdown"""
        lines = []
        data = content.get("data", {})
        
        if data.get("trend_analysis"):
            lines.append(data["trend_analysis"])
            lines.append("")
        
        if data.get("key_topics"):
            lines.append("**关键主题:**")
            for topic in data["key_topics"]:
                lines.append(f"- {topic['topic']} ({topic['count']}次)")
            lines.append("")
        
        if data.get("sentiment_distribution"):
            lines.append("**情感分布:**")
            for sentiment, count in data["sentiment_distribution"].items():
                emoji = {"positive": "😊", "negative": "😟", "neutral": "😐"}.get(sentiment, "")
                lines.append(f"- {sentiment}: {count} {emoji}")
        
        return '\n'.join(lines)
    
    def _format_investment_summary_markdown(self, content: Dict[str, Any]) -> str:
        """格式化投资摘要为Markdown"""
        lines = []
        
        total_deals = content.get("total_deals", 0)
        lines.append(f"本期共收录 **{total_deals}** 条投资相关资讯")
        lines.append("")
        
        items = content.get("items", [])
        for item in items:
            lines.append(f"- **{item['title']}**")
            if item.get("companies"):
                lines.append(f"  涉及公司: {', '.join(item['companies'])}")
            if item.get("url"):
                lines.append(f"  [详情]({item['url']})")
            lines.append("")
        
        return '\n'.join(lines)
    
    def _format_executive_summary_html(self, content: Dict[str, Any]) -> str:
        """格式化执行摘要为HTML"""
        html_parts = ['<div class="executive-summary">']
        
        if content.get("summary"):
            html_parts.append(f'<p>{self._escape_html(content["summary"])}</p>')
        
        if content.get("key_points"):
            html_parts.append('<div class="key-points">')
            html_parts.append('<h4>关键要点:</h4>')
            html_parts.append('<ul>')
            for point in content["key_points"]:
                html_parts.append(f'<li>{self._escape_html(point)}</li>')
            html_parts.append('</ul>')
            html_parts.append('</div>')
        
        html_parts.append('</div>')
        return '\n'.join(html_parts)
    
    def _format_categorized_list_html(self, content: Dict[str, Any]) -> str:
        """格式化分类列表为HTML"""
        html_parts = ['<div class="categorized-list">']
        
        for category in content.get("categories", []):
            html_parts.append('<div class="category">')
            html_parts.append(f'<h3>{self._escape_html(category["name"])} ({category["count"]}条)</h3>')
            html_parts.append('<ul>')
            
            for item in category.get("items", []):
                html_parts.append('<li>')
                html_parts.append(f'<strong>{self._escape_html(item["title"])}</strong>')
                if item.get("summary"):
                    html_parts.append(f'<br><span class="summary">{self._escape_html(item["summary"][:100])}...</span>')
                if item.get("url"):
                    html_parts.append(f'<br><a href="{item["url"]}" target="_blank">查看详情</a>')
                html_parts.append('</li>')
            
            html_parts.append('</ul>')
            html_parts.append('</div>')
        
        html_parts.append('</div>')
        return '\n'.join(html_parts)
    
    def _apply_styles(self, html_content: str, style_config: Dict[str, Any]) -> str:
        """应用样式到HTML内容"""
        # 这里可以根据style_config动态调整HTML内容
        # 简单实现，实际可以更复杂
        return html_content