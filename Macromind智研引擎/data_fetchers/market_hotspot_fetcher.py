"""
市场热点数据抓取器
使用 akshare 获取A股资金流向、异动板块、龙虎榜等数据
"""

import akshare as ak
import pandas as pd
from typing import Optional
from datetime import datetime

from .base_fetcher import BaseFetcher, FetchResult


class MarketHotspotFetcher(BaseFetcher):
    """
    市场热点数据抓取器
    获取A股资金流向、异动板块、龙虎榜等数据
    """

    def __init__(self):
        """初始化市场热点抓取器"""
        super().__init__(source_name="市场热点")

    def fetch(self, data_type: str = "all") -> FetchResult:
        """
        获取市场热点数据

        Args:
            data_type: 数据类型，可选值:
                - "all": 获取所有可用数据
                - "sector_flow": 板块资金流向
                - "individual_flow": 个股资金流向
                - "dragon_tiger": 龙虎榜
                - "limit_up": 涨停板
                - "limit_down": 跌停板
                - "active_stocks": 异动股票

        Returns:
            FetchResult: 包含市场热点数据的结果对象
        """
        all_data = {}

        try:
            # 板块资金流向
            if data_type in ["all", "sector_flow"]:
                sector_data = self._fetch_sector_fund_flow()
                if sector_data:
                    all_data['sector_fund_flow'] = sector_data

            # 个股资金流向
            if data_type in ["all", "individual_flow"]:
                individual_data = self._fetch_individual_fund_flow()
                if individual_data:
                    all_data['individual_fund_flow'] = individual_data

            # 龙虎榜
            if data_type in ["all", "dragon_tiger"]:
                lh_data = self._fetch_dragon_tiger()
                if lh_data:
                    all_data['dragon_tiger'] = lh_data

            # 涨停板
            if data_type in ["all", "limit_up"]:
                up_data = self._fetch_limit_up()
                if up_data:
                    all_data['limit_up'] = up_data

            # 跌停板
            if data_type in ["all", "limit_down"]:
                down_data = self._fetch_limit_down()
                if down_data:
                    all_data['limit_down'] = down_data

            # 异动股票
            if data_type in ["all", "active_stocks"]:
                active_data = self._fetch_active_stocks()
                if active_data:
                    all_data['active_stocks'] = active_data

            if not all_data:
                return FetchResult(
                    success=False,
                    error="未获取到任何数据",
                    source=self.source_name
                )

            total_count = sum(
                len(v) if isinstance(v, list) else 1
                for v in all_data.values()
            )

            return FetchResult(
                success=True,
                data=all_data,
                source=self.source_name,
                count=total_count
            )

        except Exception as e:
            self.logger.error(f"获取市场热点数据失败: {e}")
            return FetchResult(
                success=False,
                error=str(e),
                source=self.source_name
            )

    def normalize(self, raw_data: dict) -> list[dict]:
        """
        标准化市场数据

        Args:
            raw_data: 原始数据字典

        Returns:
            list[dict]: 标准化的数据列表
        """
        result = []
        for category, items in raw_data.items():
            if isinstance(items, list):
                for item in items:
                    item['category'] = category
                    item['source'] = self.source_name
                    result.append(item)
            else:
                result.append({
                    'category': category,
                    'data': items,
                    'source': self.source_name
                })
        return result

    def _fetch_sector_fund_flow(self, limit: int = 20) -> Optional[list[dict]]:
        """获取板块资金流向"""
        def _call():
            return ak.stock_sector_fund_flow_rank(indicator="今日")

        try:
            self.logger.info("获取板块资金流向...")
            df = self._safe_call(_call, default_value=None, func_name="ak.stock_sector_fund_flow_rank")

            if df is None or df.empty:
                return None

            result = []
            for _, row in df.head(limit).iterrows():
                result.append({
                    'sector': str(row.get('名称', '')),
                    'change_pct': str(row.get('涨跌幅', '')),
                    'main_net_inflow': str(row.get('主力净流入-净额', '')),
                    'main_net_inflow_pct': str(row.get('主力净流入-净占比', '')),
                    'super_net_inflow': str(row.get('超大单净流入-净额', '')),
                    'big_net_inflow': str(row.get('大单净流入-净额', '')),
                    'mid_net_inflow': str(row.get('中单净流入-净额', '')),
                    'small_net_inflow': str(row.get('小单净流入-净额', '')),
                    'type': '板块资金流'
                })

            self.logger.info(f"获取到 {len(result)} 条板块资金流数据")
            return result

        except Exception as e:
            self.logger.warning(f"获取板块资金流向失败: {e}")
            return None

    def _fetch_individual_fund_flow(self, limit: int = 30) -> Optional[list[dict]]:
        """获取个股资金流向"""
        def _call():
            return ak.stock_individual_fund_flow_rank(indicator="今日")

        try:
            self.logger.info("获取个股资金流向...")
            df = self._safe_call(_call, default_value=None, func_name="ak.stock_individual_fund_flow_rank")

            if df is None or df.empty:
                return None

            result = []
            for _, row in df.head(limit).iterrows():
                result.append({
                    'code': str(row.get('代码', '')),
                    'name': str(row.get('名称', '')),
                    'change_pct': str(row.get('涨跌幅', '')),
                    'main_net_inflow': str(row.get('主力净流入-净额', '')),
                    'main_net_inflow_pct': str(row.get('主力净流入-净占比', '')),
                    'type': '个股资金流'
                })

            self.logger.info(f"获取到 {len(result)} 条个股资金流数据")
            return result

        except Exception as e:
            self.logger.warning(f"获取个股资金流向失败: {e}")
            return None

    def _fetch_dragon_tiger(self) -> Optional[list[dict]]:
        """获取龙虎榜数据"""
        def _call():
            today = datetime.now().strftime("%Y%m%d")
            return ak.stock_lhb_detail_em(start_date=today, end_date=today)

        try:
            self.logger.info("获取龙虎榜数据...")
            df = self._safe_call(_call, default_value=None, func_name="ak.stock_lhb_detail_em")

            if df is None or df.empty:
                self.logger.info("今日暂无龙虎榜数据")
                return None

            result = []
            for _, row in df.head(20).iterrows():
                result.append({
                    'code': str(row.get('代码', '')),
                    'name': str(row.get('名称', '')),
                    'close_price': str(row.get('收盘价', '')),
                    'change_pct': str(row.get('涨跌幅', '')),
                    'turnover_rate': str(row.get('换手率', '')),
                    'net_buy': str(row.get('龙虎榜净买额', '')),
                    'buy_amount': str(row.get('龙虎榜买入额', '')),
                    'sell_amount': str(row.get('龙虎榜卖出额', '')),
                    'reason': str(row.get('上榜原因', '')),
                    'type': '龙虎榜'
                })

            self.logger.info(f"获取到 {len(result)} 条龙虎榜数据")
            return result

        except Exception as e:
            self.logger.warning(f"获取龙虎榜数据失败: {e}")
            return None

    def _fetch_limit_up(self, limit: int = 30) -> Optional[list[dict]]:
        """获取涨停板数据"""
        def _call():
            return ak.stock_zt_pool_em(date=None)

        try:
            self.logger.info("获取涨停板数据...")
            df = self._safe_call(_call, default_value=None, func_name="ak.stock_zt_pool_em")

            if df is None or df.empty:
                self.logger.info("今日暂无涨停板数据")
                return None

            result = []
            for _, row in df.head(limit).iterrows():
                result.append({
                    'code': str(row.get('代码', '')),
                    'name': str(row.get('名称', '')),
                    'close_price': str(row.get('最新价', '')),
                    'change_pct': str(row.get('涨跌幅', '')),
                    'turnover_rate': str(row.get('换手率', '')),
                    'first_limit_time': str(row.get('首次涨停时间', '')),
                    'last_limit_time': str(row.get('最后涨停时间', '')),
                    'limit_times': str(row.get('连板数', '')),
                    'reason': str(row.get('涨停统计', '')),
                    'type': '涨停板'
                })

            self.logger.info(f"获取到 {len(result)} 条涨停板数据")
            return result

        except Exception as e:
            self.logger.warning(f"获取涨停板数据失败: {e}")
            return None

    def _fetch_limit_down(self, limit: int = 30) -> Optional[list[dict]]:
        """获取跌停板数据"""
        def _call():
            return ak.stock_zt_pool_dtgc_em(date=None)

        try:
            self.logger.info("获取跌停板数据...")
            df = self._safe_call(_call, default_value=None, func_name="ak.stock_zt_pool_dtgc_em")

            if df is None or df.empty:
                self.logger.info("今日暂无跌停板数据")
                return None

            result = []
            for _, row in df.head(limit).iterrows():
                result.append({
                    'code': str(row.get('代码', '')),
                    'name': str(row.get('名称', '')),
                    'close_price': str(row.get('最新价', '')),
                    'change_pct': str(row.get('涨跌幅', '')),
                    'turnover_rate': str(row.get('换手率', '')),
                    'type': '跌停板'
                })

            self.logger.info(f"获取到 {len(result)} 条跌停板数据")
            return result

        except Exception as e:
            self.logger.warning(f"获取跌停板数据失败: {e}")
            return None

    def _fetch_active_stocks(self, limit: int = 30) -> Optional[list[dict]]:
        """获取异动股票数据"""
        def _call():
            return ak.stock_zt_pool_zbgc_em(date=None)

        try:
            self.logger.info("获取异动股票数据...")
            df = self._safe_call(_call, default_value=None, func_name="ak.stock_zt_pool_zbgc_em")

            if df is None or df.empty:
                self.logger.info("今日暂无异动股票数据")
                return None

            result = []
            for _, row in df.head(limit).iterrows():
                result.append({
                    'code': str(row.get('代码', '')),
                    'name': str(row.get('名称', '')),
                    'close_price': str(row.get('最新价', '')),
                    'change_pct': str(row.get('涨跌幅', '')),
                    'turnover_rate': str(row.get('换手率', '')),
                    'total_value': str(row.get('总市值', '')),
                    'active_type': str(row.get('异动类型', '')),
                    'type': '异动股票'
                })

            self.logger.info(f"获取到 {len(result)} 条异动股票数据")
            return result

        except Exception as e:
            self.logger.warning(f"获取异动股票数据失败: {e}")
            return None

    def fetch_sector_flow_only(self) -> FetchResult:
        """仅获取板块资金流向"""
        return self.fetch(data_type="sector_flow")

    def fetch_dragon_tiger_only(self) -> FetchResult:
        """仅获取龙虎榜数据"""
        return self.fetch(data_type="dragon_tiger")

    def fetch_limit_stocks_only(self) -> FetchResult:
        """仅获取涨跌停数据"""
        return self.fetch(data_type="limit_up")