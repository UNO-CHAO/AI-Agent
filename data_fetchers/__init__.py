"""
数据抓取模块
提供多源金融数据获取能力
"""

from .base_fetcher import BaseFetcher, FetchResult
from .cailianshe_fetcher import CailiansheFetcher
from .macro_policy_fetcher import MacroPolicyFetcher
from .market_hotspot_fetcher import MarketHotspotFetcher
from .bond_fetcher import BondFetcher

__all__ = [
    'BaseFetcher',
    'FetchResult',
    'CailiansheFetcher',
    'MacroPolicyFetcher',
    'MarketHotspotFetcher',
    'BondFetcher',
]