"""
宏观经济与政策数据抓取器
使用 akshare 获取宏观经济指标、央行政策、财经新闻等
"""

import akshare as ak
import pandas as pd
from typing import Optional

from .base_fetcher import BaseFetcher, FetchResult


class MacroPolicyFetcher(BaseFetcher):
    """
    宏观经济与政策数据抓取器
    获取宏观经济指标、央行政策、财经新闻等数据
    """

    def __init__(self):
        """初始化宏观经济与政策抓取器"""
        super().__init__(source_name="宏观经济政策")

    def fetch(self, data_type: str = "all") -> FetchResult:
        """
        获取宏观经济与政策数据

        Args:
            data_type: 数据类型，可选值:
                - "all": 获取所有可用数据
                - "news": 财经新闻
                - "cpi": CPI数据
                - "ppI": PPI数据
                - "pmi": PMI数据
                - "m2": M2货币供应量
                - "rate": 利率数据

        Returns:
            FetchResult: 包含宏观数据的结果对象
        """
        all_data = {}

        try:
            # 财经新闻
            if data_type in ["all", "news"]:
                news_data = self._fetch_financial_news()
                if news_data:
                    all_data['news'] = news_data

            # CPI数据
            if data_type in ["all", "cpi"]:
                cpi_data = self._fetch_cpi()
                if cpi_data:
                    all_data['cpi'] = cpi_data

            # PPI数据
            if data_type in ["all", "ppi"]:
                ppi_data = self._fetch_ppi()
                if ppi_data:
                    all_data['ppi'] = ppi_data

            # PMI数据
            if data_type in ["all", "pmi"]:
                pmi_data = self._fetch_pmi()
                if pmi_data:
                    all_data['pmi'] = pmi_data

            # M2货币供应量
            if data_type in ["all", "m2"]:
                m2_data = self._fetch_m2()
                if m2_data:
                    all_data['m2'] = m2_data

            # 利率数据
            if data_type in ["all", "rate"]:
                rate_data = self._fetch_interest_rate()
                if rate_data:
                    all_data['interest_rate'] = rate_data

            if not all_data:
                return FetchResult(
                    success=False,
                    error="未获取到任何数据",
                    source=self.source_name
                )

            total_count = sum(len(v) if isinstance(v, list) else 1 for v in all_data.values())

            return FetchResult(
                success=True,
                data=all_data,
                source=self.source_name,
                count=total_count
            )

        except Exception as e:
            self.logger.error(f"获取宏观数据失败: {e}")
            return FetchResult(
                success=False,
                error=str(e),
                source=self.source_name
            )

    def normalize(self, raw_data: dict) -> list[dict]:
        """
        标准化宏观数据

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

    def _fetch_financial_news(self, limit: int = 30) -> Optional[list[dict]]:
        """获取财经新闻"""
        def _call():
            return ak.stock_news_em(symbol="财经")

        try:
            self.logger.info("获取财经新闻...")
            df = self._safe_call(_call, default_value=None, func_name="ak.stock_news_em")

            if df is None or df.empty:
                return None

            news_list = []
            for _, row in df.head(limit).iterrows():
                news_list.append({
                    'datetime': str(row.get('发布时间', '')),
                    'title': str(row.get('新闻标题', '')),
                    'content': str(row.get('新闻内容', '')),
                    'type': '新闻'
                })

            self.logger.info(f"获取到 {len(news_list)} 条财经新闻")
            return news_list

        except Exception as e:
            self.logger.warning(f"获取财经新闻失败: {e}")
            return None

    def _fetch_cpi(self) -> Optional[list[dict]]:
        """获取CPI数据"""
        def _call():
            return ak.macro_china_cpi_yearly()

        try:
            self.logger.info("获取CPI数据...")
            df = self._safe_call(_call, default_value=None, func_name="ak.macro_china_cpi_yearly")

            if df is None or df.empty:
                return None

            # 取最近几条数据
            recent_data = df.tail(12)
            result = []
            for _, row in recent_data.iterrows():
                result.append({
                    'month': str(row.get('月份', '')),
                    'cpi': str(row.get('全国当月', '')),
                    'cpi_yoy': str(row.get('全国同比', '')),
                    'type': 'CPI'
                })

            self.logger.info(f"获取到 {len(result)} 条CPI数据")
            return result

        except Exception as e:
            self.logger.warning(f"获取CPI数据失败: {e}")
            return None

    def _fetch_ppi(self) -> Optional[list[dict]]:
        """获取PPI数据"""
        def _call():
            return ak.macro_china_ppi_yearly()

        try:
            self.logger.info("获取PPI数据...")
            df = self._safe_call(_call, default_value=None, func_name="ak.macro_china_ppi_yearly")

            if df is None or df.empty:
                return None

            recent_data = df.tail(12)
            result = []
            for _, row in recent_data.iterrows():
                result.append({
                    'month': str(row.get('月份', '')),
                    'ppi': str(row.get('当月', '')),
                    'ppi_yoy': str(row.get('当月同比', '')),
                    'type': 'PPI'
                })

            self.logger.info(f"获取到 {len(result)} 条PPI数据")
            return result

        except Exception as e:
            self.logger.warning(f"获取PPI数据失败: {e}")
            return None

    def _fetch_pmi(self) -> Optional[list[dict]]:
        """获取PMI数据"""
        def _call():
            return ak.macro_china_pmi_yearly()

        try:
            self.logger.info("获取PMI数据...")
            df = self._safe_call(_call, default_value=None, func_name="ak.macro_china_pmi_yearly")

            if df is None or df.empty:
                return None

            recent_data = df.tail(12)
            result = []
            for _, row in recent_data.iterrows():
                result.append({
                    'month': str(row.get('月份', '')),
                    'pmi': str(row.get('制造业-指数', '')),
                    'type': 'PMI'
                })

            self.logger.info(f"获取到 {len(result)} 条PMI数据")
            return result

        except Exception as e:
            self.logger.warning(f"获取PMI数据失败: {e}")
            return None

    def _fetch_m2(self) -> Optional[list[dict]]:
        """获取M2货币供应量"""
        def _call():
            return ak.macro_china_m2_yearly()

        try:
            self.logger.info("获取M2货币供应量数据...")
            df = self._safe_call(_call, default_value=None, func_name="ak.macro_china_m2_yearly")

            if df is None or df.empty:
                return None

            recent_data = df.tail(12)
            result = []
            for _, row in recent_data.iterrows():
                result.append({
                    'month': str(row.get('月份', '')),
                    'm2': str(row.get('货币和准货币(M2)', '')),
                    'm2_yoy': str(row.get('货币和准货币(M2)同比增长', '')),
                    'type': 'M2'
                })

            self.logger.info(f"获取到 {len(result)} 条M2数据")
            return result

        except Exception as e:
            self.logger.warning(f"获取M2数据失败: {e}")
            return None

    def _fetch_interest_rate(self) -> Optional[list[dict]]:
        """获取利率数据（央行基准利率）"""
        def _call():
            return ak.macro_china_base_rate()

        try:
            self.logger.info("获取利率数据...")
            df = self._safe_call(_call, default_value=None, func_name="ak.macro_china_base_rate")

            if df is None or df.empty:
                return None

            result = []
            for _, row in df.head(10).iterrows():
                result.append({
                    'date': str(row.get('日期', '')),
                    'rate_type': str(row.get('利率类型', '')),
                    'rate': str(row.get('利率', '')),
                    'type': '基准利率'
                })

            self.logger.info(f"获取到 {len(result)} 条利率数据")
            return result

        except Exception as e:
            self.logger.warning(f"获取利率数据失败: {e}")
            return None

    def fetch_news_only(self) -> FetchResult:
        """仅获取财经新闻"""
        return self.fetch(data_type="news")

    def fetch_indicators_only(self) -> FetchResult:
        """仅获取宏观经济指标"""
        all_data = {}
        for dtype in ["cpi", "ppi", "pmi", "m2", "rate"]:
            result = self.fetch(data_type=dtype)
            if result.success and result.data:
                all_data.update(result.data)

        return FetchResult(
            success=bool(all_data),
            data=all_data,
            source=self.source_name,
            count=len(all_data)
        )