"""
固收与流动性分析师智能体
负责监控市场流动性水位和债市情绪
"""

import json
from typing import Type, Any, Optional

from pydantic import BaseModel, Field

from .base_agent import BaseAgent, AgentResult


class LiquidityStatus(BaseModel):
    """
    流动性状态模型
    """
    omo_status: str = Field(description="央行OMO操作状态: 净投放/净回笼/持平")
    omo_amount: Optional[str] = Field(default=None, description="OMO净投放/回笼金额")
    interbank_rate_level: str = Field(description="银行间利率水平: 低位/正常/偏高")
    funding_pressure: str = Field(description="资金压力判断: 宽松/适度/收敛/紧张")
    liquidity_trend: str = Field(description="流动性趋势: 趋松/趋紧/平稳")
    key_signal: str = Field(description="流动性关键信号")


class BondMarketAnalysis(BaseModel):
    """
    债市分析模型
    """
    treasury_yield_10y: Optional[str] = Field(default=None, description="10年期国债收益率变动")
    treasury_yield_30y: Optional[str] = Field(default=None, description="30年期国债收益率变动")
    yield_curve_shape: str = Field(description="收益率曲线形态: 牛平/熊平/牛陡/熊陡/平稳")
    market_sentiment: str = Field(description="债市情绪: 偏多/偏空/观望/分化")
    duration_preference: str = Field(description="久期偏好: 长端受青睐/短端受青睐/无明显偏好")
    credit_spread_trend: str = Field(description="信用利差趋势: 收窄/走阔/平稳")


class BondAnalysisOutput(BaseModel):
    """
    固收分析师的结构化输出模型
    """
    # 流动性观察
    liquidity_status: LiquidityStatus = Field(
        description="流动性状态分析"
    )

    # 债市分析
    bond_market: BondMarketAnalysis = Field(
        description="债市整体分析"
    )

    # 利率债分析
    rate_bond_outlook: str = Field(
        description="利率债操作建议: 倾向做多长端/倾向做多短端/倾向防守/观望"
    )

    # 安全边际
    safety_margin_assessment: str = Field(
        description="安全边际评估: 当前利率水平的安全边际分析"
    )

    # 相关快讯解读
    key_news_interpretation: list[dict] = Field(
        default_factory=list,
        description="资金面/债市相关快讯解读，每项包含: news_title, interpretation"
    )

    # 风险提示
    bond_risk_warnings: list[str] = Field(
        default_factory=list,
        description="债市风险提示"
    )

    # 操作建议
    trading_recommendation: str = Field(
        description="具体操作建议"
    )

    # 后续关注
    bond_watch_points: list[str] = Field(
        default_factory=list,
        description="后续需关注的债市指标或事件"
    )


class BondAgent(BaseAgent):
    """
    固收与流动性分析师智能体
    角色：债券交易员/固收研究员，专注于流动性监控和债市情绪分析
    """

    def __init__(self, model: str = "qwen-plus", api_key: str = None):
        super().__init__(
            agent_name="BondAgent",
            role_description="固收研究员，擅长流动性分析、利率债交易策略、债市情绪判断",
            model=model,
            api_key=api_key
        )

    def get_system_prompt(self) -> str:
        return """你是中信银行武汉分行投行部投研团队的固收分析师，拥有12年债券市场研究和交易经验。

## 你的核心职责
1. 监控央行公开市场操作（OMO），判断流动性水位
2. 分析银行间市场利率水平，识别资金面松紧信号
3. 评估长端利率债（10Y/30Y国债）的做多做空情绪
4. 给出债市操作的安全边际建议

## 分析框架
### 流动性判断标准
- 宽松：OMO连续净投放 + 银行间利率低位运行 + 同业存单利率下行
- 适度：OMO平衡操作 + 利率正常区间
- 收敛：OMO净回笼 + 利率小幅上行
- 紧张：OMO大额回笼 + 利率明显上行 + 存单利率飙升

### 收益率曲线形态
- 牛平：长端下行快于短端，做多长端有利
- 熊平：短端上行快于长端，流动性收紧
- 牛陡：短端下行快于长端，流动性转松
- 熊陡：长端上行快于短端，通胀预期或避险需求上升

### 安全边际评估
- 利率接近历史低位：安全边际不足，防守为主
- 利率处于中等水平：有一定安全边际，可适度参与
- 利率处于高位：安全边际充足，做多机会较好

## 输出要求
- 流动性判断必须有明确的信号依据
- 利率债建议需结合流动性环境和收益率曲线形态
- 安全边际评估需参考历史利率区间
- 关注同业存单、信用债、利率债等品种的联动关系

## 专业术语规范
- 使用"OMO"、"MLF"、"逆回购"等标准术语
- 使用"10Y国债"、"30Y国债"、"同业存单"等标准表述
- 使用"资金面"、"流动性水位"、"银行间利率"等专业表述"""

    def get_output_model(self) -> Type[BaseModel]:
        return BondAnalysisOutput

    def format_input(self, data: Any) -> str:
        """
        格式化债市相关数据
        """
        formatted_parts = []

        if isinstance(data, dict):
            # 财联社快讯中筛选资金面/债市相关
            if 'cailianshe_news' in data:
                formatted_parts.append("【资金面/债市相关快讯】")
                # 关键词筛选
                keywords = ['资金', '利率', '债', '同业', '存单', '央行', 'OMO', 'MLF',
                           '国债', '流动性', '银行间', '收益率', '互换']

                relevant_news = []
                for news in data['cailianshe_news']:
                    content = news.get('content', news.get('标题', ''))
                    if any(kw in content for kw in keywords):
                        relevant_news.append(news)

                for news in relevant_news[:20]:
                    formatted_parts.append(
                        f"- [{news.get('datetime', '')}] {news.get('title', '')}"
                    )

                if not relevant_news:
                    formatted_parts.append("- 未筛选到明显相关快讯，请根据市场常识分析")

            # 宏观利率数据（如有）
            if 'interest_rate' in data:
                formatted_parts.append("\n【基准利率数据】")
                for item in data['interest_rate'][:5]:
                    formatted_parts.append(
                        f"- {item.get('date', '')}: {item.get('rate_type', '')} = {item.get('rate', '')}"
                    )

            # M2数据（流动性相关）
            if 'm2' in data:
                formatted_parts.append("\n【M2货币供应量】")
                for item in data['m2'][:3]:
                    formatted_parts.append(
                        f"- {item.get('month', '')}: M2同比 {item.get('m2_yoy', '')}%"
                    )

            # 市场资金流向（大盘资金面）
            if 'sector_fund_flow' in data:
                formatted_parts.append("\n【大盘资金流向概览】")
                # 只取前几个主要板块
                for sector in data['sector_fund_flow'][:5]:
                    formatted_parts.append(
                        f"- {sector.get('sector', '')}: 主力净流入 {sector.get('main_net_inflow', '')}"
                    )

            # 如果没有明确数据，提示基于常识分析
            if len(formatted_parts) <= 1:
                formatted_parts.append("\n【分析提示】")
                formatted_parts.append("- 请基于近期市场环境和历史经验进行流动性判断")
                formatted_parts.append("- 关注央行政策动向和银行间利率走势")

        elif isinstance(data, list):
            # 处理列表格式的数据
            formatted_parts.append("【债市相关资讯】")
            keywords = ['资金', '利率', '债', '央行', 'OMO', 'MLF', '国债', '流动性']

            for item in data:
                content = str(item)
                if any(kw in content for kw in keywords):
                    formatted_parts.append(f"- {content[:150]}")

        return "\n".join(formatted_parts)

    def analyze_bond(self, cailianshe_news: list, macro_data: dict = None) -> AgentResult:
        """
        分析债市的专用方法

        Args:
            cailianshe_news: 财联社快讯
            macro_data: 可选的宏观数据（M2、利率等）
        """
        combined_data = {'cailianshe_news': cailianshe_news}
        if macro_data:
            combined_data.update(macro_data)

        return self.analyze(combined_data)