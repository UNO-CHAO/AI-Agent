"""
首席综合架构师智能体
负责跨资产维度的逻辑校验与融合，生成最终晨报
"""

import json
from typing import Type, Any, Optional
from datetime import datetime

from pydantic import BaseModel, Field

from .base_agent import BaseAgent, AgentResult
from .macro_agent import MacroAnalysisOutput
from .strategy_agent import StrategyAnalysisOutput
from .bond_agent import BondAnalysisOutput


class CrossAssetWarning(BaseModel):
    """
    跨资产预警模型
    """
    warning_type: str = Field(description="预警类型: 逻辑背离/风险共振/机会共振")
    description: str = Field(description="预警具体描述")
    involved_assets: list[str] = Field(description="涉及的资产类别")
    severity: str = Field(description="严重程度: 高/中/低")
    suggested_action: str = Field(description="建议应对措施")


class FinalReportOutput(BaseModel):
    """
    最终报告的结构化输出模型
    """
    # 报告日期
    report_date: str = Field(description="报告日期")

    # 核心观点
    core_viewpoint: str = Field(description="今日核心观点一句话概括")

    # 宏观与政策风向
    macro_section: dict = Field(
        description="宏观与政策风向章节内容"
    )

    # A股主线与热点异动
    stock_section: dict = Field(
        description="A股主线与热点异动章节内容"
    )

    # 债市与流动性观察
    bond_section: dict = Field(
        description="债市与流动性观察章节内容"
    )

    # 跨资产共振与风险预警
    cross_asset_section: dict = Field(
        description="跨资产共振与风险预警章节内容"
    )

    # 完整 Markdown 报告
    markdown_report: str = Field(
        description="完整的 Markdown 格式晨报"
    )


class ChiefSynthesizer(BaseAgent):
    """
    首席综合架构师智能体
    角色：基金经理/首席策略师，负责跨资产维度融合与最终报告生成
    """

    def __init__(self, model: str = "qwen-plus", api_key: str = None):
        super().__init__(
            agent_name="ChiefSynthesizer",
            role_description="首席策略师，擅长跨资产逻辑校验、风险预警、报告整合",
            model=model,
            api_key=api_key
        )

    def get_system_prompt(self) -> str:
        return """你是中信银行武汉分行投行部投研团队的首席策略师，拥有20年跨资产投资经验。

## 你的核心职责
1. 接收宏观、A股策略、固收三个分析师的结构化输出
2. 进行跨资产维度的逻辑校验——识别背离、共振、风险
3. 生成结构完整的每日晨报

## 逻辑校验框架
### 逻辑背离识别
- 宏观提示收紧，但A股提示放量暴涨 → 情绪与基本面背离，警惕冲高回落
- 流动性收紧，但债市提示做多长端 → 需重新审视流动性判断
- A股板块火热，但宏观风险因子累积 → 行情可持续性存疑

### 风险共振识别
- 多个资产类别同时出现风险信号 → 系统性风险可能上升
- 宏观、A股、债市同时提示谨慎 → 需降低整体仓位

### 机会共振识别
- 宏观利好 + 流动性宽松 + A股资金流入 → 市场环境共振向好
- 利率下行 + 流动性宽松 + 债市偏多 → 债券做多窗口

## 报告生成要求
报告必须严格按照以下结构：

### 【🔴 宏观与政策风向】
- 必须包含多空双面解读（Bull视角 + Bear视角）
- 突出当日最重要的宏观事件

### 【📈 A 股主线与热点异动】
- 列出3-5个核心发酵板块
- 每个板块需有资金面+量价+驱动逻辑的完整分析

### 【📉 债市与流动性观察】
- 必须包含资金水位判断
- 需有利率债趋势分析
- 给出安全边际建议

### 【⚠️ 跨资产共振与风险预警】
- 必须识别逻辑背离或共振
- 给出具体的风险应对建议

## 输出要求
- 报告语气专业、简洁，避免冗余
- 每个章节需有明确的结论句
- 整体风格符合券商投研报告标准"""

    def get_output_model(self) -> Type[BaseModel]:
        return FinalReportOutput

    def format_input(self, data: Any) -> str:
        """
        格式化三个 Agent 的输出数据
        """
        formatted_parts = []

        formatted_parts.append("=" * 60)
        formatted_parts.append("【输入：三个分析师的结构化输出】")
        formatted_parts.append("=" * 60)

        # 宏观分析师输出
        if 'macro_output' in data:
            macro = data['macro_output']
            formatted_parts.append("\n## 宏观分析师输出\n")
            formatted_parts.append(f"整体判断: {macro.get('overall_sentiment', '')}")
            formatted_parts.append(f"\n利好因子 (Bull视角):")
            for factor in macro.get('bull_factors', [])[:5]:
                formatted_parts.append(
                    f"- {factor.get('factor_name', '')}: {factor.get('description', '')} "
                    f"(影响等级: {factor.get('impact_level', '')})"
                )
            formatted_parts.append(f"\n风险因子 (Bear视角):")
            for factor in macro.get('bear_factors', [])[:5]:
                formatted_parts.append(
                    f"- {factor.get('factor_name', '')}: {factor.get('description', '')} "
                    f"(影响等级: {factor.get('impact_level', '')})"
                )
            formatted_parts.append(f"\n政策动向:")
            for policy in macro.get('policy_updates', [])[:3]:
                formatted_parts.append(f"- {policy.get('policy_name', '')}: {policy.get('impact', '')}")

        # A股策略分析师输出
        if 'strategy_output' in data:
            strategy = data['strategy_output']
            formatted_parts.append("\n## A股策略分析师输出\n")
            formatted_parts.append(f"市场情绪: {strategy.get('market_sentiment', '')}")
            formatted_parts.append(f"资金面判断: {strategy.get('overall_fund_flow', '')}")
            formatted_parts.append(f"\n核心发酵板块:")
            for sector in strategy.get('hot_sectors', [])[:5]:
                formatted_parts.append(
                    f"- {sector.get('sector_name', '')}: 热度 {sector.get('heat_level', '')}, "
                    f"资金 {sector.get('fund_flow_direction', '')}, "
                    f"驱动: {sector.get('driving_logic', '')}"
                )
                formatted_parts.append(
                    f"  持续性: {sector.get('sustainability', '')}, "
                    f"风险: {sector.get('risk_alert', '')}"
                )
            formatted_parts.append(f"\n龙虎榜解读: {strategy.get('dragon_tiger_insight', '')}")

        # 固收分析师输出
        if 'bond_output' in data:
            bond = data['bond_output']
            formatted_parts.append("\n## 固收分析师输出\n")

            liquidity = bond.get('liquidity_status', {})
            formatted_parts.append(f"流动性状态:")
            formatted_parts.append(
                f"- OMO: {liquidity.get('omo_status', '')} "
                f"(金额: {liquidity.get('omo_amount', '未知')})"
            )
            formatted_parts.append(f"- 资金压力: {liquidity.get('funding_pressure', '')}")
            formatted_parts.append(f"- 流动性趋势: {liquidity.get('liquidity_trend', '')}")

            bond_market = bond.get('bond_market', {})
            formatted_parts.append(f"\n债市分析:")
            formatted_parts.append(
                f"- 10Y国债: {bond_market.get('treasury_yield_10y', '未知')}"
            )
            formatted_parts.append(
                f"- 30Y国债: {bond_market.get('treasury_yield_30y', '未知')}"
            )
            formatted_parts.append(f"- 收益率曲线: {bond_market.get('yield_curve_shape', '')}")
            formatted_parts.append(f"- 债市情绪: {bond_market.get('market_sentiment', '')}")

            formatted_parts.append(f"\n利率债建议: {bond.get('rate_bond_outlook', '')}")
            formatted_parts.append(f"安全边际: {bond.get('safety_margin_assessment', '')}")

        formatted_parts.append("\n" + "=" * 60)
        formatted_parts.append("请基于以上三个分析师的输出，进行跨资产逻辑校验并生成完整晨报")
        formatted_parts.append("=" * 60)

        return "\n".join(formatted_parts)

    def synthesize(
        self,
        macro_result: AgentResult,
        strategy_result: AgentResult,
        bond_result: AgentResult
    ) -> AgentResult:
        """
        综合三个分析师的输出，生成最终报告

        Args:
            macro_result: 宏观分析师结果
            strategy_result: A股策略分析师结果
            bond_result: 固收分析师结果

        Returns:
            AgentResult: 包含最终晨报的结果
        """
        self.logger.info(f"[{self.agent_name}] 开始综合分析...")

        # 检查输入结果
        if not macro_result.success:
            self.logger.warning(f"宏观分析师输出失败: {macro_result.error}")
        if not strategy_result.success:
            self.logger.warning(f"策略分析师输出失败: {strategy_result.error}")
        if not bond_result.success:
            self.logger.warning(f"固收分析师输出失败: {bond_result.error}")

        # 准备输入数据
        input_data = {
            'macro_output': macro_result.output.model_dump() if macro_result.output else {},
            'strategy_output': strategy_result.output.model_dump() if strategy_result.output else {},
            'bond_output': bond_result.output.model_dump() if bond_result.output else {},
        }

        return self.analyze(input_data)

    def generate_report(
        self,
        macro_output: MacroAnalysisOutput,
        strategy_output: StrategyAnalysisOutput,
        bond_output: BondAnalysisOutput
    ) -> str:
        """
        直接生成 Markdown 报告（不通过 LLM）

        Args:
            macro_output: 宏观分析结构化输出
            strategy_output: A股策略结构化输出
            bond_output: 固收分析结构化输出

        Returns:
            str: Markdown 格式晨报
        """
        report_date = datetime.now().strftime("%Y年%m月%d日")

        report = f"""# 📅 股债双市每日跟踪报告
**报告日期：{report_date}**

---

## 🔴 宏观与政策风向

### {macro_output.overall_sentiment}

"""

        # Bull视角
        report += "**宏观利好因子（Bull视角）：**\n"
        for factor in macro_output.bull_factors[:5]:
            report += f"- **{factor.factor_name}** ({factor.impact_level}影响)\n"
            report += f"  - {factor.description}\n"
            report += f"  - 受影响资产：{', '.join(factor.affected_assets)}\n"

        # Bear视角
        report += "\n**宏观风险因子（Bear视角）：**\n"
        for factor in macro_output.bear_factors[:5]:
            report += f"- **{factor.factor_name}** ({factor.impact_level}影响)\n"
            report += f"  - {factor.description}\n"
            report += f"  - 受影响资产：{', '.join(factor.affected_assets)}\n"

        # 政策动向
        if macro_output.policy_updates:
            report += "\n**重要政策动向：**\n"
            for policy in macro_output.policy_updates[:3]:
                report += f"- {policy.get('policy_name', '')}: {policy.get('impact', '')}\n"

        # 国际事件
        if macro_output.international_events:
            report += "\n**国际重要事件：**\n"
            for event in macro_output.international_events[:3]:
                report += f"- {event.get('event_name', '')}: 对中国影响 - {event.get('impact_on_china', '')}\n"

        report += f"\n**后续关注点：** {', '.join(macro_output.key_watch_points[:5])}\n"

        # A股章节
        report += f"""
---

## 📈 A股主线与热点异动

### 市场整体：{strategy_output.market_sentiment}
**资金面判断：** {strategy_output.overall_fund_flow}

"""

        report += "**核心发酵板块（今日）：**\n\n"
        for i, sector in enumerate(strategy_output.hot_sectors[:5], 1):
            report += f"**{i}. {sector.sector_name}**\n"
            report += f"- 热度等级：{sector.heat_level}\n"
            report += f"- 资金流向：{sector.fund_flow_direction} ({sector.fund_flow_amount or '数据待更新'})\n"
            report += f"- 量价信号：{sector.price_volume_signal}\n"
            report += f"- 驱动逻辑：{sector.driving_logic} - {sector.catalyst_detail}\n"
            report += f"- 持续性判断：{sector.sustainability}\n"
            report += f"- 风险提示：{sector.risk_alert}\n"
            report += f"- 操作建议：{sector.recommended_action}\n\n"

        if strategy_output.dragon_tiger_insight:
            report += f"**龙虎榜解读：** {strategy_output.dragon_tiger_insight}\n"

        if strategy_output.risk_warnings:
            report += "\n**市场风险提示：**\n"
            for warning in strategy_output.risk_warnings[:3]:
                report += f"- {warning}\n"

        report += f"\n**后续关注：** {', '.join(strategy_output.watch_points[:5])}\n"

        # 债市章节
        report += f"""
---

## 📉 债市与流动性观察

### 流动性水位：{bond_output.liquidity_status.funding_pressure}
"""

        report += f"- **央行OMO：** {bond_output.liquidity_status.omo_status} ({bond_output.liquidity_status.omo_amount or '金额待更新'})\n"
        report += f"- **银行间利率：** {bond_output.liquidity_status.interbank_rate_level}\n"
        report += f"- **流动性趋势：** {bond_output.liquidity_status.liquidity_trend}\n"
        report += f"- **关键信号：** {bond_output.liquidity_status.key_signal}\n"

        report += f"""
### 利率债趋势
"""
        report += f"- **10Y国债：** {bond_output.bond_market.treasury_yield_10y or '数据待更新'}\n"
        report += f"- **30Y国债：** {bond_output.bond_market.treasury_yield_30y or '数据待更新'}\n"
        report += f"- **收益率曲线：** {bond_output.bond_market.yield_curve_shape}\n"
        report += f"- **债市情绪：** {bond_output.bond_market.market_sentiment}\n"

        report += f"""
### 操作建议
"""
        report += f"- **利率债策略：** {bond_output.rate_bond_outlook}\n"
        report += f"- **安全边际：** {bond_output.safety_margin_assessment}\n"
        report += f"- **具体建议：** {bond_output.trading_recommendation}\n"

        if bond_output.bond_risk_warnings:
            report += "\n**债市风险提示：**\n"
            for warning in bond_output.bond_risk_warnings[:3]:
                report += f"- {warning}\n"

        # 跨资产章节
        report += f"""
---

## ️ 跨资产共振与风险预警

"""

        # 逻辑校验
        cross_warnings = self._validate_cross_asset_logic(
            macro_output, strategy_output, bond_output
        )

        if cross_warnings:
            report += "**识别的跨资产信号：**\n\n"
            for warning in cross_warnings:
                report += f"- **{warning.warning_type}** ({warning.severity})\n"
                report += f"  - {warning.description}\n"
                report += f"  - 涉及资产：{', '.join(warning.involved_assets)}\n"
                report += f"  - 建议：{warning.suggested_action}\n\n"
        else:
            report += "**整体判断：** 各资产类别逻辑一致，无明显背离或共振信号。\n"

        report += """
---

*本报告由中信银行武汉分行投行部投研多智能体系统生成，仅供参考，不构成投资建议。*
"""

        return report

    def _validate_cross_asset_logic(
        self,
        macro: MacroAnalysisOutput,
        strategy: StrategyAnalysisOutput,
        bond: BondAnalysisOutput
    ) -> list[CrossAssetWarning]:
        """
        跨资产逻辑校验
        """
        warnings = []

        # 检查宏观收紧 vs A股火爆
        if macro.overall_sentiment in ['偏谨慎', '中性观望']:
            if strategy.market_sentiment == '强势':
                warnings.append(CrossAssetWarning(
                    warning_type="逻辑背离",
                    description="宏观预期偏谨慎但A股情绪强势，情绪与基本面可能背离",
                    involved_assets=["A股", "宏观"],
                    severity="中",
                    suggested_action="警惕冲高回落，关注宏观风险因子是否开始发酵"
                ))

        # 检查流动性收紧 vs 债市做多
        if bond.liquidity_status.funding_pressure in ['收敛', '紧张']:
            if bond.rate_bond_outlook in ['倾向做多长端', '倾向做多短端']:
                warnings.append(CrossAssetWarning(
                    warning_type="逻辑背离",
                    description="流动性收敛但债市建议做多，需重新审视流动性判断",
                    involved_assets=["债券", "流动性"],
                    severity="高",
                    suggested_action="优先关注流动性指标变化，谨慎做多"
                ))

        # 检查宏观利好 + 流动性宽松 + A股强势的共振
        if macro.overall_sentiment == '偏乐观' and \
           bond.liquidity_status.funding_pressure == '宽松' and \
           strategy.market_sentiment == '强势':
            warnings.append(CrossAssetWarning(
                warning_type="机会共振",
                description="宏观利好、流动性宽松、A股强势三重共振，市场环境向好",
                involved_assets=["A股", "债券", "宏观"],
                severity="低",
                suggested_action="可适度增加仓位，但仍需关注风险因子变化"
            ))

        # 检查多个风险因子共振
        bear_count = len(macro.bear_factors)
        if bear_count >= 3 and strategy.market_sentiment != '强势':
            warnings.append(CrossAssetWarning(
                warning_type="风险共振",
                description=f"宏观累积{bear_count}个风险因子且A股情绪不强，系统性风险可能上升",
                involved_assets=["A股", "宏观"],
                severity="高",
                suggested_action="降低仓位，观望为主，等待风险释放"
            ))

        return warnings

    def analyze(self, data: Any) -> AgentResult:
        """
        执行综合分析
        """
        # 如果输入已经是结构化输出，可以直接生成报告
        if 'macro_output' in data and 'strategy_output' in data and 'bond_output' in data:
            try:
                macro = MacroAnalysisOutput.model_validate(data['macro_output'])
                strategy = StrategyAnalysisOutput.model_validate(data['strategy_output'])
                bond = BondAnalysisOutput.model_validate(data['bond_output'])

                # 直接生成报告
                report = self.generate_report(macro, strategy, bond)

                output = FinalReportOutput(
                    report_date=datetime.now().strftime("%Y年%m月%d日"),
                    core_viewpoint=f"宏观{macro.overall_sentiment}，A股{strategy.market_sentiment}，流动性{bond.liquidity_status.funding_pressure}",
                    macro_section=data['macro_output'],
                    stock_section=data['strategy_output'],
                    bond_section=data['bond_output'],
                    cross_asset_section={'warnings': [w.model_dump() for w in self._validate_cross_asset_logic(macro, strategy, bond)]},
                    markdown_report=report
                )

                return AgentResult(
                    success=True,
                    agent_name=self.agent_name,
                    output=output,
                    raw_response=report
                )
            except Exception as e:
                self.logger.warning(f"直接生成报告失败，转为调用LLM: {e}")

        # 否则调用 LLM
        return super().analyze(data)