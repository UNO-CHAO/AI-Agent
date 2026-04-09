"""
智能体模块
多角色 AI 分析师团队
"""

from .base_agent import BaseAgent, AgentResult
from .macro_agent import MacroAgent, MacroAnalysisOutput
from .strategy_agent import StrategyAgent, StrategyAnalysisOutput
from .bond_agent import BondAgent, BondAnalysisOutput
from .chief_synthesizer import ChiefSynthesizer, FinalReportOutput

__all__ = [
    'BaseAgent',
    'AgentResult',
    'MacroAgent',
    'MacroAnalysisOutput',
    'StrategyAgent',
    'StrategyAnalysisOutput',
    'BondAgent',
    'BondAnalysisOutput',
    'ChiefSynthesizer',
    'FinalReportOutput',
]