"""
报告生成模块单元测试
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
import json

from src.modules.report_generation.template_manager import TemplateManager
from src.modules.report_generation.content_aggregator import ContentAggregator
from src.modules.report_generation.report_generator import ReportGenerator
from src.modules.report_generation.report_formatter import ReportFormatter
from src.models.schemas import (
    ReportConfig, ReportTemplate, ProcessedContent, 
    GeneratedReport, ReportSection, Keyword
)


class TestTemplateManager:
    """模板管理器测试"""
    
    @pytest.fixture
    def template_manager(self):
        """创建模板管理器实例"""
        return TemplateManager()
    
    @pytest.fixture
    def sample_template(self):
        """示例报告模板"""
        return ReportTemplate(
            template_id="daily_report_v1",
            name="AI Daily Report",
            description="Daily AI news report template",
            template_type="daily",
            sections=[
                ReportSection(
                    section_id="highlights",
                    section_name="今日要闻",
                    section_type="news_list",
                    order=1,
                    max_items=5,
                    filters={"importance_score": {"$gte": 0.7}}
                ),
                ReportSection(
                    section_id="tech_updates",
                    section_name="技术动态",
                    section_type="categorized_list",
                    order=2,
                    max_items=10,
                    filters={"categories": ["技术", "研究"]}
                ),
                ReportSection(
                    section_id="summary",
                    section_name="今日总结",
                    section_type="summary",
                    order=3
                )
            ],
            layout_config={
                "page_size": "A4",
                "font_family": "Arial",
                "font_size": 12
            },
            style_config={
                "primary_color": "#1890ff",
                "secondary_color": "#f0f0f0"
            }
        )
    
    def test_create_template(self, template_manager, sample_template):
        """测试创建模板"""
        template_id = template_manager.create_template(sample_template)
        
        assert template_id == sample_template.template_id
        assert template_manager.get_template(template_id) == sample_template
    
    def test_update_template(self, template_manager, sample_template):
        """测试更新模板"""
        # 创建模板
        template_manager.create_template(sample_template)
        
        # 更新模板
        sample_template.name = "Updated AI Daily Report"
        sample_template.sections[0].max_items = 3
        
        success = template_manager.update_template(sample_template.template_id, sample_template)
        
        assert success
        updated = template_manager.get_template(sample_template.template_id)
        assert updated.name == "Updated AI Daily Report"
        assert updated.sections[0].max_items == 3
    
    def test_list_templates(self, template_manager, sample_template):
        """测试列出模板"""
        # 创建多个模板
        template_manager.create_template(sample_template)
        
        weekly_template = sample_template.model_copy()
        weekly_template.template_id = "weekly_report_v1"
        weekly_template.template_type = "weekly"
        template_manager.create_template(weekly_template)
        
        # 列出所有模板
        all_templates = template_manager.list_templates()
        assert len(all_templates) == 2
        
        # 按类型过滤
        daily_templates = template_manager.list_templates(template_type="daily")
        assert len(daily_templates) == 1
        assert daily_templates[0].template_type == "daily"
    
    def test_validate_template(self, template_manager, sample_template):
        """测试模板验证"""
        # 有效模板
        is_valid, errors = template_manager.validate_template(sample_template)
        assert is_valid
        assert len(errors) == 0
        
        # 无效模板（缺少必要字段）
        invalid_template = ReportTemplate(
            template_id="invalid",
            name="",  # 空名称
            template_type="unknown",  # 未知类型
            sections=[]  # 无章节
        )
        
        is_valid, errors = template_manager.validate_template(invalid_template)
        assert not is_valid
        assert len(errors) > 0


class TestContentAggregator:
    """内容聚合器测试"""
    
    @pytest.fixture
    def content_aggregator(self):
        """创建内容聚合器实例"""
        return ContentAggregator()
    
    @pytest.fixture
    def sample_contents(self):
        """示例处理后的内容"""
        base_time = datetime.now(timezone.utc)
        contents = []
        
        for i in range(15):
            content = ProcessedContent(
                content_id=f"content_{i}",
                title=f"AI新闻标题 {i}",
                cleaned_content=f"这是第{i}篇关于AI的新闻内容...",
                keywords=[
                    Keyword(term="AI", score=0.8),
                    Keyword(term=f"主题{i % 3}", score=0.6)
                ],
                categories=["技术", "研究"] if i % 2 == 0 else ["行业", "应用"],
                importance_score=0.5 + (i % 5) * 0.1,  # 0.5 - 0.9
                publish_time=base_time - timedelta(hours=i),
                source="TechNews",
                url=f"https://example.com/news/{i}"
            )
            contents.append(content)
        
        return contents
    
    def test_aggregate_by_time_range(self, content_aggregator, sample_contents):
        """测试按时间范围聚合"""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=6)
        
        aggregated = content_aggregator.aggregate_by_time_range(
            sample_contents,
            start_time,
            end_time
        )
        
        # 应该只包含最近6小时的内容（索引0-5）
        assert len(aggregated) == 6
        assert all(c.content_id in [f"content_{i}" for i in range(6)] for c in aggregated)
    
    def test_aggregate_by_category(self, content_aggregator, sample_contents):
        """测试按分类聚合"""
        categorized = content_aggregator.aggregate_by_category(sample_contents)
        
        assert "技术" in categorized
        assert "行业" in categorized
        assert len(categorized["技术"]) == 8  # 偶数索引的内容
        assert len(categorized["行业"]) == 7  # 奇数索引的内容
    
    def test_sort_by_importance(self, content_aggregator, sample_contents):
        """测试按重要性排序"""
        sorted_contents = content_aggregator.sort_by_importance(sample_contents)
        
        # 验证降序排列
        for i in range(len(sorted_contents) - 1):
            assert sorted_contents[i].importance_score >= sorted_contents[i + 1].importance_score
    
    def test_apply_filters(self, content_aggregator, sample_contents):
        """测试应用过滤器"""
        filters = {
            "importance_score": {"$gte": 0.7},
            "categories": ["技术"]
        }
        
        filtered = content_aggregator.apply_filters(sample_contents, filters)
        
        assert all(c.importance_score >= 0.7 for c in filtered)
        assert all("技术" in c.categories for c in filtered)
    
    def test_group_by_topic(self, content_aggregator, sample_contents):
        """测试按主题分组"""
        grouped = content_aggregator.group_by_keywords(sample_contents)
        
        # 应该有AI和3个主题关键词
        assert "AI" in grouped
        assert len(grouped["AI"]) == 15  # 所有内容都有AI关键词
        
        for i in range(3):
            topic = f"主题{i}"
            assert topic in grouped
            assert len(grouped[topic]) == 5  # 每个主题有5篇
    
    def test_limit_items_per_section(self, content_aggregator, sample_contents):
        """测试限制每个部分的项目数"""
        limited = content_aggregator.limit_items(sample_contents, max_items=5)
        
        assert len(limited) == 5
        # 应该保留重要性最高的5个
        assert all(c.importance_score >= 0.7 for c in limited)


class TestReportGenerator:
    """报告生成器测试"""
    
    @pytest.fixture
    def report_generator(self, mock_openai):
        """创建报告生成器实例"""
        return ReportGenerator(
            template_manager=TemplateManager(),
            content_aggregator=ContentAggregator(),
            ai_client=mock_openai
        )
    
    @pytest.fixture
    def report_config(self):
        """示例报告配置"""
        return ReportConfig(
            report_type="daily",
            template_id="daily_report_v1",
            time_range={
                "start_date": datetime.now(timezone.utc).date() - timedelta(days=1),
                "end_date": datetime.now(timezone.utc).date()
            },
            categories=["技术", "研究"],
            max_items_per_section=5,
            include_summary=True,
            include_charts=False
        )
    
    @pytest.mark.asyncio
    async def test_generate_daily_report(self, report_generator, report_config, sample_contents, sample_template):
        """测试生成日报"""
        # 设置模板
        report_generator.template_manager.create_template(sample_template)
        
        # 生成报告
        with patch.object(report_generator, '_fetch_contents', return_value=sample_contents):
            report = await report_generator.generate_report(report_config)
        
        assert isinstance(report, GeneratedReport)
        assert report.title.startswith("AI日报")
        assert len(report.sections) == len(sample_template.sections)
        assert report.metadata["total_items"] > 0
    
    @pytest.mark.asyncio
    async def test_generate_section_content(self, report_generator, sample_contents):
        """测试生成章节内容"""
        section = ReportSection(
            section_id="test_section",
            section_name="测试章节",
            section_type="news_list",
            max_items=3
        )
        
        content = await report_generator._generate_section_content(
            section, 
            sample_contents[:5]
        )
        
        assert "items" in content
        assert len(content["items"]) <= 3
        assert all("title" in item for item in content["items"])
    
    @pytest.mark.asyncio
    async def test_generate_summary(self, report_generator, sample_contents, mock_openai):
        """测试生成摘要"""
        # 配置mock返回
        mock_openai.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content="这是AI生成的摘要内容。"))]
        )
        
        summary = await report_generator._generate_summary(sample_contents[:5])
        
        assert summary is not None
        assert "摘要" in summary
        mock_openai.chat.completions.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_enrich_with_insights(self, report_generator, sample_contents):
        """测试添加洞察分析"""
        insights = await report_generator._generate_insights(sample_contents)
        
        assert "trend_analysis" in insights
        assert "key_topics" in insights
        assert "sentiment_distribution" in insights
    
    @pytest.mark.asyncio
    async def test_handle_empty_content(self, report_generator, report_config, sample_template):
        """测试处理空内容"""
        report_generator.template_manager.create_template(sample_template)
        
        with patch.object(report_generator, '_fetch_contents', return_value=[]):
            report = await report_generator.generate_report(report_config)
        
        assert report is not None
        assert report.metadata["total_items"] == 0
        assert all(len(s.content.get("items", [])) == 0 for s in report.sections)


class TestReportFormatter:
    """报告格式化器测试"""
    
    @pytest.fixture
    def report_formatter(self):
        """创建报告格式化器实例"""
        return ReportFormatter()
    
    @pytest.fixture
    def sample_report(self):
        """示例生成的报告"""
        return GeneratedReport(
            report_id="report_123",
            title="AI日报 - 2024年1月1日",
            subtitle="今日AI领域重要进展",
            sections=[
                ReportSection(
                    section_id="highlights",
                    section_name="今日要闻",
                    section_type="news_list",
                    order=1,
                    content={
                        "items": [
                            {
                                "title": "OpenAI发布新模型",
                                "summary": "性能提升50%",
                                "url": "https://example.com/1"
                            }
                        ]
                    }
                ),
                ReportSection(
                    section_id="summary",
                    section_name="今日总结",
                    section_type="summary",
                    order=2,
                    content={
                        "text": "今天AI领域有重要突破..."
                    }
                )
            ],
            metadata={
                "total_items": 10,
                "generation_time": "2024-01-01T10:00:00Z",
                "categories_covered": ["技术", "研究"]
            },
            generated_time=datetime.now(timezone.utc)
        )
    
    def test_format_to_markdown(self, report_formatter, sample_report):
        """测试格式化为Markdown"""
        markdown = report_formatter.format_to_markdown(sample_report)
        
        assert sample_report.title in markdown
        assert "## 今日要闻" in markdown
        assert "OpenAI发布新模型" in markdown
        assert "[查看详情]" in markdown
        assert "## 今日总结" in markdown
    
    def test_format_to_html(self, report_formatter, sample_report):
        """测试格式化为HTML"""
        html = report_formatter.format_to_html(sample_report)
        
        assert f"<title>{sample_report.title}</title>" in html
        assert '<h2>今日要闻</h2>' in html
        assert 'OpenAI发布新模型' in html
        assert '<a href="https://example.com/1"' in html
    
    def test_format_to_json(self, report_formatter, sample_report):
        """测试格式化为JSON"""
        json_str = report_formatter.format_to_json(sample_report)
        json_data = json.loads(json_str)
        
        assert json_data["title"] == sample_report.title
        assert len(json_data["sections"]) == 2
        assert json_data["sections"][0]["section_name"] == "今日要闻"
    
    def test_apply_template_styles(self, report_formatter):
        """测试应用模板样式"""
        html_content = "<h1>标题</h1><p>内容</p>"
        style_config = {
            "primary_color": "#1890ff",
            "font_family": "Arial",
            "font_size": "14px"
        }
        
        styled_html = report_formatter._apply_styles(html_content, style_config)
        
        assert "style" in styled_html
        assert "#1890ff" in styled_html
        assert "Arial" in styled_html
    
    def test_generate_toc(self, report_formatter, sample_report):
        """测试生成目录"""
        toc = report_formatter._generate_table_of_contents(sample_report.sections)
        
        assert len(toc) == 2
        assert toc[0]["name"] == "今日要闻"
        assert toc[0]["anchor"] == "#highlights"
    
    def test_format_datetime(self, report_formatter):
        """测试日期时间格式化"""
        dt = datetime(2024, 1, 1, 10, 30, 0, tzinfo=timezone.utc)
        
        formatted = report_formatter._format_datetime(dt, format="%Y年%m月%d日 %H:%M")
        assert formatted == "2024年01月01日 10:30"
        
        formatted_relative = report_formatter._format_datetime(dt, relative=True)
        assert "前" in formatted_relative or "ago" in formatted_relative