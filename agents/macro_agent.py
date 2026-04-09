"""
宏观分析师智能体
负责梳理国内外宏观大事件，输出多空双视角分析
"""

import json
from typing import Type, Any

from pydantic import BaseModel, Field

from .base_agent import BaseAgent, AgentResult, BullBearFactor


class MacroAnalysisOutput(BaseModel):
    """
    宏观分析师的结构化输出模型
    """
    # 宏观概览
    macro_summary: str = Field(
        description="宏观整体形势一句话概括"
    )

    # 利好因子（Bull视角）
    bull_factors: list[BullBearFactor] = Field(
        default_factory=list,
        description="宏观利好因子列表"
    )

    # 风险因子（Bear视角）
    bear_factors: list[BullBearFactor] = Field(
        default_factory=list,
        description="宏观风险因子/隐患列表"
    )

    # 政策动向
    policy_updates: list[dict] = Field(
        default_factory=list,
        description="重要政策动向列表，每项包含: policy_name, description, impact"
    )

    # 国际形势
    international_events: list[dict] = Field(
        default_factory=list,
        description="国际重要事件列表，每项包含: event_name, description, impact_on_china"
    )

    # 综合判断
    overall_sentiment: str = Field(
        description="整体宏观情绪判断: 偏乐观/偏谨慎/中性观望"
    )

    # 关键关注点
    key_watch_points: list[str] = Field(
        default_factory=list,
        description="后续需重点关注的宏观指标或事件"
    )


class MacroAgent(BaseAgent):
    """
    宏观分析师智能体
    角色：资深宏观分析师，专注于国内外宏观大事件的梳理与分析
    """

    def __init__(self, model: str = "qwen-plus", api_key: str = None):
        super().__init__(
            agent_name="MacroAgent",
            role_description="资深宏观分析师，擅长解读宏观经济数据、政策动向和国际形势",
            model=model,
            api_key=api_key
        )

    def get_system_prompt(self) -> str:
        return """你是中信银行武汉分行投行部投研团队的资深宏观分析师，拥有15年宏观经济研究经验。

## 你的核心职责
1. 从海量资讯中筛选出真正影响宏观预期的核心事件
2. 对每个重要事件进行"多空双视角"分析——既看利好面也看风险面
3. 关注央行货币政策、财政政策、地产政策、国际地缘政治等关键领域

## 分析框架
### Bull视角（利好因子）
- 政策刺激预期（降息、降准、财政发力等）
- 经济数据超预期向好
- 国际环境改善（贸易缓和、地缘降温等）
- 产业政策支持

### Bear视角（风险因子）
- 政策收紧信号
- 经济数据不及预期
- 国际风险事件（贸易摩擦、地缘冲突等）
- 系统性风险隐患（债务、地产等）

## 输出要求
- 每个因子需明确说明影响等级（高/中/低）和受影响资产
- 必须给出清晰的逻辑推理，而非模糊表述
- 国际事件需分析对中国的影响传导路径
- 避免将个股异动、行业噪音混入宏观分析

## 专业术语规范
- 金融衍生品统一使用"互换"表述
- 利率相关使用"10Y国债"、"30Y国债"等标准表述
- 资金面使用"OMO"、"MLF"、"同业存单"等专业术语"""

    def get_output_model(self) -> Type[BaseModel]:
        return MacroAnalysisOutput

    def format_input(self, data: Any) -> str:
        """
        格式化 macro_policy_fetcher 的数据
        """
        if isinstance(data, dict):
            # 处理字典格式的数据
            formatted_parts = []

            # 新闻数据
            if 'news' in data:
                formatted_parts.append("【财经新闻】")
                for news in data['news'][:30]:
                    formatted_parts.append(
                        f"- [{news.get('datetime', '')}] {news.get('title', '')}"
                    )

            # CPI数据
            if 'cpi' in data:
                formatted_parts.append("\n【CPI数据（近12月）】")
                for item in data['cpi'][:6]:
                    formatted_parts.append(
                        f"- {item.get('month', '')}: CPI同比 {item.get('cpi_yoy', '')}"
                    )

            # PPI数据
            if 'ppi' in data:
                formatted_parts.append("\n【PPI数据（近12月）】")
                for item in data['ppi'][:6]:
                    formatted_parts.append(
                        f"- {item.get('month', '')}: PPI同比 {item.get('ppi_yoy', '')}"
                    )

            # PMI数据
            if 'pmi' in data:
                formatted_parts.append("\n【PMI数据（近12月）】")
                for item in data['pmi'][:6]:
                    formatted_parts.append(
                        f"- {item.get('month', '')}: PMI {item.get('pmi', '')}"
                    )

            # M2数据
            if 'm2' in data:
                formatted_parts.append("\n【M2货币供应量（近12月）】")
                for item in data['m2'][:6]:
                    formatted_parts.append(
                        f"- {item.get('month', '')}: M2同比 {item.get('m2_yoy', '')}"
                    )

            # 利率数据
            if 'interest_rate' in data:
                formatted_parts.append("\n【基准利率】")
                for item in data['interest_rate'][:5]:
                    formatted_parts.append(
                        f"- {item.get('date', '')}: {item.get('rate_type', '')} = {item.get('rate', '')}"
                    )

            return "\n".join(formatted_parts)

        elif isinstance(data, list):
            # 处理列表格式的新闻数据
            formatted_parts = ["【宏观经济资讯】"]
            for item in data[:50]:
                time_str = item.get('datetime', item.get('时间', ''))
                title = item.get('title', item.get('标题', ''))
                content = item.get('content', item.get('内容', ''))
                formatted_parts.append(
                    f"- [{time_str}] {title}\n  {content[:100]}..."
                )
            return "\n".join(formatted_parts)

        else:
            return str(data)

    def analyze_macro(self, data: Any) -> AgentResult:
        """
        分析宏观数据的专用方法
        """
        return self.analyze(data)