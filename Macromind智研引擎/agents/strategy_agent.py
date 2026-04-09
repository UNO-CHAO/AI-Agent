"""
A股策略分析师智能体
负责分析A股市场热点、板块资金流向，给出具体板块评价
"""

import json
from typing import Type, Any, Optional

from pydantic import BaseModel, Field

from .base_agent import BaseAgent, AgentResult


class SectorAnalysis(BaseModel):
    """
    板块分析模型
    """
    sector_name: str = Field(description="板块名称")
    heat_level: str = Field(description="热度等级: 高热/温热/冷门")
    fund_flow_direction: str = Field(description="资金流向: 流入/流出/中性")
    fund_flow_amount: Optional[str] = Field(default=None, description="资金净流入金额（如有数据）")
    price_volume_signal: str = Field(description="量价信号: 放量上涨/缩量上涨/放量下跌/缩量下跌/横盘")
    driving_logic: str = Field(description="驱动逻辑: 政策催化/业绩驱动/事件驱动/资金博弈/技术反弹")
    catalyst_detail: str = Field(description="催化剂详情: 具体事件或原因")
    sustainability: str = Field(description="持续性判断: 可持续/短暂脉冲/待观察")
    risk_alert: str = Field(description="后续风险提示")
    recommended_action: str = Field(description="操作建议: 关注/观望/回避")


class StrategyAnalysisOutput(BaseModel):
    """
    A股策略分析师的结构化输出模型
    """
    # 市场整体判断
    market_sentiment: str = Field(
        description="市场整体情绪: 强势/弱势/震荡/观望"
    )

    # 指数概况
    index_summary: dict = Field(
        default_factory=dict,
        description="主要指数概况，包含: 主要指数涨跌、成交量变化、技术位置判断"
    )

    # 核心发酵板块（3-5个）
    hot_sectors: list[SectorAnalysis] = Field(
        default_factory=list,
        description="当日核心发酵板块分析（3-5个）"
    )

    # 异动关注
    notable_moves: list[dict] = Field(
        default_factory=list,
        description="值得关注的异动现象，如涨停潮、跌停潮、大单异动等"
    )

    # 龙虎榜解读
    dragon_tiger_insight: str = Field(
        default="",
        description="龙虎榜资金动向解读（如有数据）"
    )

    # 资金面整体判断
    overall_fund_flow: str = Field(
        description="资金面整体判断: 主力活跃/散户主导/外资进出/观望为主"
    )

    # 风险提示
    risk_warnings: list[str] = Field(
        default_factory=list,
        description="市场整体风险提示"
    )

    # 后续关注点
    watch_points: list[str] = Field(
        default_factory=list,
        description="后续需重点关注的板块或信号"
    )


class StrategyAgent(BaseAgent):
    """
    A股策略分析师智能体
    角色：A股策略研究员，专注于板块热点、资金流向分析
    """

    def __init__(self, model: str = "qwen-plus", api_key: str = None):
        super().__init__(
            agent_name="StrategyAgent",
            role_description="A股策略研究员，擅长板块轮动分析、资金流向追踪、热点挖掘",
            model=model,
            api_key=api_key
        )

    def get_system_prompt(self) -> str:
        return """你是中信银行武汉分行投行部投研团队的A股策略分析师，拥有10年A股策略研究经验。

## 你的核心职责
1. 从资金流向数据中识别当日核心发酵板块（3-5个）
2. 结合量价表现判断板块热度和持续性
3. 挖掘板块背后的驱动逻辑（政策、业绩、事件、资金博弈等）
4. 给出具体的风险提示和操作建议

## 分析框架
### 板块热度评估
- 高热：主力大额流入 + 放量上涨 + 明确催化
- 温热：主力小幅流入 + 量价配合 + 催化待验证
- 冷门：资金流出或横盘

### 持续性判断标准
- 可持续：政策长期催化 + 行业景气向上 + 机构认可
- 短暂脉冲：事件一次性催化 + 游资主导 + 无基本面支撑
- 待观察：催化不明 + 资金博弈剧烈

### 风险信号识别
- 板块轮动过快（一日游行情）
- 龙虎榜游资主导而非机构
- 涨停板炸板率高
- 大单流出但股价上涨（诱多）
- 缩量上涨（动能不足）

## 输出要求
- 每个板块必须给出明确的驱动逻辑和催化剂详情
- 持续性判断必须有依据，不能用"可能"、"或许"等模糊词
- 风险提示要具体，不能泛泛而谈
- 操作建议要与风险等级匹配

## 专业术语规范
- 资金流入使用"主力净流入"、"超大单"、"大单"等标准表述
- 量价信号使用"放量"、"缩量"、"换手率"等专业术语"""

    def get_output_model(self) -> Type[BaseModel]:
        return StrategyAnalysisOutput

    def format_input(self, data: Any) -> str:
        """
        格式化 market_hotspot_fetcher 和财联社数据
        """
        formatted_parts = []

        if isinstance(data, dict):
            # 板块资金流向
            if 'sector_fund_flow' in data:
                formatted_parts.append("【板块资金流向（今日）】")
                for sector in data['sector_fund_flow'][:15]:
                    formatted_parts.append(
                        f"- {sector.get('sector', '')}: 主力净流入 {sector.get('main_net_inflow', '')}, "
                        f"占比 {sector.get('main_net_inflow_pct', '')}"
                    )

            # 个股资金流向
            if 'individual_fund_flow' in data:
                formatted_parts.append("\n【个股资金流向TOP20】")
                for stock in data['individual_fund_flow'][:20]:
                    formatted_parts.append(
                        f"- {stock.get('name', '')}({stock.get('code', '')}): "
                        f"主力净流入 {stock.get('main_net_inflow', '')}, "
                        f"涨跌 {stock.get('change_pct', '')}%"
                    )

            # 龙虎榜
            if 'dragon_tiger' in data:
                formatted_parts.append("\n【龙虎榜（今日）】")
                for lh in data['dragon_tiger'][:10]:
                    formatted_parts.append(
                        f"- {lh.get('name', '')}({lh.get('code', '')}): "
                        f"净买 {lh.get('net_buy', '')}, "
                        f"上榜原因: {lh.get('reason', '')}"
                    )

            # 涨停板
            if 'limit_up' in data:
                formatted_parts.append("\n【涨停板】")
                up_list = data['limit_up']
                if up_list:
                    for stock in up_list[:10]:
                        formatted_parts.append(
                            f"- {stock.get('name', '')}: {stock.get('limit_times', '')}连板, "
                            f"原因: {stock.get('reason', '')}"
                        )
                else:
                    formatted_parts.append("- 今日无涨停数据")

            # 跌停板
            if 'limit_down' in data:
                formatted_parts.append("\n【跌停板】")
                down_list = data['limit_down']
                if down_list:
                    for stock in down_list[:5]:
                        formatted_parts.append(
                            f"- {stock.get('name', '')}: 跌停"
                        )
                else:
                    formatted_parts.append("- 今日无跌停数据")

            # 财联社快讯（用于补充市场信息）
            if 'cailianshe_news' in data:
                formatted_parts.append("\n【财联社市场相关快讯】")
                for news in data['cailianshe_news'][:20]:
                    formatted_parts.append(
                        f"- [{news.get('datetime', '')}] {news.get('title', '')}"
                    )

        elif isinstance(data, list):
            formatted_parts.append("【市场热点数据】")
            for item in data[:30]:
                formatted_parts.append(f"- {json.dumps(item, ensure_ascii=False)}")

        return "\n".join(formatted_parts)

    def analyze_strategy(self, data: Any, cailianshe_news: list = None) -> AgentResult:
        """
        分析A股策略的专用方法

        Args:
            data: market_hotspot_fetcher 数据
            cailianshe_news: 可选的财联社快讯补充
        """
        combined_data = data if isinstance(data, dict) else {}
        if cailianshe_news:
            combined_data['cailianshe_news'] = cailianshe_news

        return self.analyze(combined_data)