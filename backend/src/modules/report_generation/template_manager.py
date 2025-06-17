"""
报告模板管理器
"""
from typing import List, Optional, Dict, Any
import uuid
import json
import logging
from datetime import datetime, timezone

from src.models.schemas import ReportTemplate, ReportSection

logger = logging.getLogger(__name__)


class TemplateManager:
    """报告模板管理器"""
    
    def __init__(self):
        # 内存中的模板存储（实际应该使用数据库）
        self.templates: Dict[str, ReportTemplate] = {}
        # 初始化默认模板
        self._init_default_templates()
    
    def _init_default_templates(self):
        """初始化默认模板"""
        # 日报模板
        daily_template = ReportTemplate(
            template_id="default_daily",
            name="AI日报默认模板",
            description="AI领域每日新闻汇总报告模板",
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
                    max_items=8,
                    filters={"categories": ["技术", "研究"]}
                ),
                ReportSection(
                    section_id="industry_news",
                    section_name="行业资讯",
                    section_type="news_list",
                    order=3,
                    max_items=6,
                    filters={"categories": ["行业动态", "产品", "应用"]}
                ),
                ReportSection(
                    section_id="investment",
                    section_name="投资并购",
                    section_type="news_list",
                    order=4,
                    max_items=4,
                    filters={"categories": ["投资"]}
                ),
                ReportSection(
                    section_id="summary",
                    section_name="今日总结",
                    section_type="summary",
                    order=5
                )
            ],
            layout_config={
                "page_size": "A4",
                "orientation": "portrait",
                "margins": {"top": 20, "bottom": 20, "left": 20, "right": 20},
                "font_family": "Arial, 微软雅黑",
                "font_size": 12,
                "line_height": 1.5
            },
            style_config={
                "primary_color": "#1890ff",
                "secondary_color": "#f0f0f0",
                "text_color": "#333333",
                "link_color": "#1890ff",
                "heading_style": {
                    "h1": {"size": 24, "weight": "bold"},
                    "h2": {"size": 18, "weight": "bold"},
                    "h3": {"size": 14, "weight": "bold"}
                }
            },
            version="1.0.0",
            is_active=True,
            is_default=True,
            created_at=datetime.now(timezone.utc)
        )
        self.templates[daily_template.template_id] = daily_template
        
        # 周报模板
        weekly_template = ReportTemplate(
            template_id="default_weekly",
            name="AI周报默认模板",
            description="AI领域每周重要进展汇总报告模板",
            template_type="weekly",
            sections=[
                ReportSection(
                    section_id="overview",
                    section_name="本周概览",
                    section_type="executive_summary",
                    order=1
                ),
                ReportSection(
                    section_id="top_news",
                    section_name="重点新闻",
                    section_type="news_list",
                    order=2,
                    max_items=10,
                    filters={"importance_score": {"$gte": 0.75}}
                ),
                ReportSection(
                    section_id="tech_trends",
                    section_name="技术趋势",
                    section_type="trend_analysis",
                    order=3
                ),
                ReportSection(
                    section_id="research_papers",
                    section_name="重要研究",
                    section_type="categorized_list",
                    order=4,
                    max_items=8,
                    filters={"categories": ["研究"], "source_authority": {"$gte": 0.8}}
                ),
                ReportSection(
                    section_id="company_updates",
                    section_name="公司动态",
                    section_type="grouped_list",
                    order=5,
                    max_items=10,
                    filters={"entities.label": "ORG"}
                ),
                ReportSection(
                    section_id="investment_analysis",
                    section_name="投资分析",
                    section_type="investment_summary",
                    order=6,
                    filters={"categories": ["投资"]}
                ),
                ReportSection(
                    section_id="insights",
                    section_name="洞察分析",
                    section_type="insights",
                    order=7
                )
            ],
            layout_config={
                "page_size": "A4",
                "orientation": "portrait",
                "margins": {"top": 25, "bottom": 25, "left": 25, "right": 25},
                "font_family": "Arial, 微软雅黑",
                "font_size": 12,
                "line_height": 1.6,
                "include_toc": True
            },
            style_config={
                "primary_color": "#2c3e50",
                "secondary_color": "#ecf0f1",
                "accent_color": "#e74c3c",
                "text_color": "#2c3e50",
                "link_color": "#3498db",
                "heading_style": {
                    "h1": {"size": 28, "weight": "bold", "color": "#2c3e50"},
                    "h2": {"size": 20, "weight": "bold", "color": "#34495e"},
                    "h3": {"size": 16, "weight": "normal", "color": "#7f8c8d"}
                }
            },
            version="1.0.0",
            is_active=True,
            is_default=True,
            created_at=datetime.now(timezone.utc)
        )
        self.templates[weekly_template.template_id] = weekly_template
    
    def create_template(self, template: ReportTemplate) -> str:
        """创建模板"""
        if not template.template_id:
            template.template_id = str(uuid.uuid4())
        
        if template.template_id in self.templates:
            raise ValueError(f"模板ID已存在: {template.template_id}")
        
        # 验证模板
        is_valid, errors = self.validate_template(template)
        if not is_valid:
            raise ValueError(f"模板验证失败: {', '.join(errors)}")
        
        template.created_at = datetime.now(timezone.utc)
        self.templates[template.template_id] = template
        
        logger.info(f"创建模板: {template.name} ({template.template_id})")
        return template.template_id
    
    def update_template(self, template_id: str, template: ReportTemplate) -> bool:
        """更新模板"""
        if template_id not in self.templates:
            raise ValueError(f"模板不存在: {template_id}")
        
        # 验证模板
        is_valid, errors = self.validate_template(template)
        if not is_valid:
            raise ValueError(f"模板验证失败: {', '.join(errors)}")
        
        # 保留原始创建时间
        template.created_at = self.templates[template_id].created_at
        template.template_id = template_id
        
        self.templates[template_id] = template
        
        logger.info(f"更新模板: {template.name} ({template_id})")
        return True
    
    def get_template(self, template_id: str) -> Optional[ReportTemplate]:
        """获取模板"""
        return self.templates.get(template_id)
    
    def list_templates(self, template_type: Optional[str] = None, is_active: Optional[bool] = None) -> List[ReportTemplate]:
        """列出模板"""
        templates = list(self.templates.values())
        
        if template_type:
            templates = [t for t in templates if t.template_type == template_type]
        
        if is_active is not None:
            templates = [t for t in templates if t.is_active == is_active]
        
        # 按创建时间倒序
        templates.sort(key=lambda t: t.created_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        
        return templates
    
    def delete_template(self, template_id: str) -> bool:
        """删除模板"""
        if template_id not in self.templates:
            return False
        
        # 不允许删除默认模板
        if self.templates[template_id].is_default:
            raise ValueError("不能删除默认模板")
        
        del self.templates[template_id]
        logger.info(f"删除模板: {template_id}")
        return True
    
    def validate_template(self, template: ReportTemplate) -> tuple[bool, List[str]]:
        """验证模板"""
        errors = []
        
        # 验证基本信息
        if not template.name:
            errors.append("模板名称不能为空")
        
        if template.template_type not in ["daily", "weekly", "monthly", "custom"]:
            errors.append(f"无效的模板类型: {template.template_type}")
        
        # 验证章节
        if not template.sections:
            errors.append("模板至少需要一个章节")
        
        section_ids = set()
        for section in template.sections:
            if not section.section_id:
                errors.append("章节ID不能为空")
            elif section.section_id in section_ids:
                errors.append(f"章节ID重复: {section.section_id}")
            else:
                section_ids.add(section.section_id)
            
            if not section.section_name:
                errors.append(f"章节名称不能为空: {section.section_id}")
            
            if section.section_type not in [
                "news_list", "categorized_list", "grouped_list", 
                "summary", "executive_summary", "trend_analysis",
                "insights", "investment_summary", "custom"
            ]:
                errors.append(f"无效的章节类型: {section.section_type}")
        
        return len(errors) == 0, errors
    
    def get_default_template(self, template_type: str) -> Optional[ReportTemplate]:
        """获取默认模板"""
        templates = self.list_templates(template_type=template_type, is_active=True)
        for template in templates:
            if template.is_default:
                return template
        
        # 如果没有默认模板，返回第一个活跃模板
        return templates[0] if templates else None