"""
债市与流动性数据抓取器
使用 akshare 获取央行OMO、SHIBOR、国债收益率等数据
"""

import akshare as ak
import pandas as pd
from typing import Optional
from datetime import datetime, timedelta

# 支持直接运行时的导入
try:
    from .base_fetcher import BaseFetcher, FetchResult
except ImportError:
    # 直接运行时使用绝对导入
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from data_fetchers.base_fetcher import BaseFetcher, FetchResult


class BondFetcher(BaseFetcher):
    """
    债市与流动性数据抓取器
    获取央行公开市场操作、SHIBOR利率、国债收益率等数据
    """

    def __init__(self):
        """初始化债市数据抓取器"""
        super().__init__(source_name="债市与流动性")

    def fetch(self, data_type: str = "all") -> FetchResult:
        """
        获取债市与流动性数据

        Args:
            data_type: 数据类型，可选值:
                - "all": 获取所有可用数据
                - "omo": 央行公开市场操作
                - "shibor": SHIBOR利率
                - "treasury": 国债收益率
                - "cd_rate": 同业存单利率
                - "repo": 回购利率

        Returns:
            FetchResult: 包含债市数据的结果对象
        """
        all_data = {}

        try:
            # 央行公开市场操作
            if data_type in ["all", "omo"]:
                omo_data = self._fetch_omo()
                if omo_data:
                    all_data['omo'] = omo_data

            # SHIBOR利率
            if data_type in ["all", "shibor"]:
                shibor_data = self._fetch_shibor()
                if shibor_data:
                    all_data['shibor'] = shibor_data

            # 国债收益率
            if data_type in ["all", "treasury"]:
                treasury_data = self._fetch_treasury_yield()
                if treasury_data:
                    all_data['treasury_yield'] = treasury_data

            # 同业存单利率
            if data_type in ["all", "cd_rate"]:
                cd_data = self._fetch_cd_rate()
                if cd_data:
                    all_data['cd_rate'] = cd_data

            # 回购利率
            if data_type in ["all", "repo"]:
                repo_data = self._fetch_repo_rate()
                if repo_data:
                    all_data['repo_rate'] = repo_data

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
            self.logger.error(f"获取债市数据失败: {e}")
            return FetchResult(
                success=False,
                error=str(e),
                source=self.source_name
            )

    def normalize(self, raw_data: dict) -> list[dict]:
        """
        标准化债市数据

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

    def _fetch_omo(self) -> Optional[list[dict]]:
        """
        获取央行公开市场操作数据
        包括逆回购、MLF等操作的投放与回笼情况
        """
        def _call():
            return ak.macro_china_central_bank_balance()

        try:
            self.logger.info("获取央行公开市场操作数据...")

            result_list = []

            # 获取央行资产负债表数据（推断流动性状态）
            df = self._safe_call(_call, default_value=None, func_name="ak.macro_china_central_bank_balance")

            if df is not None and not df.empty:
                # 取最近几条数据
                recent_df = df.head(5)
                for _, row in recent_df.iterrows():
                    result_list.append({
                        'date': str(row.get('统计时间', '')),
                        'foreign_assets': str(row.get('国外资产', '')),
                        'foreign_exchange': str(row.get('外汇', '')),
                        'total_assets': str(row.get('总资产', '')),
                        'reserve_money': str(row.get('储备货币', '')),
                        'government_deposit': str(row.get('政府存款', '')),
                        'total_liabilities': str(row.get('总负债', '')),
                        'type': '央行资产负债'
                    })
                self.logger.info(f"获取到 {len(result_list)} 条央行资产负债数据")
                return result_list

            return None

        except Exception as e:
            self.logger.warning(f"获取OMO数据失败: {e}")
            return None

    def _fetch_shibor(self) -> Optional[list[dict]]:
        """
        获取SHIBOR（上海银行间同业拆放利率）数据
        """
        def _call():
            return ak.macro_china_shibor_all()

        try:
            self.logger.info("获取SHIBOR利率数据...")

            # 获取SHIBOR数据
            df = self._safe_call(_call, default_value=None, func_name="ak.macro_china_shibor_all")

            if df is not None and not df.empty:
                result_list = []
                # 取最近几条数据
                recent_df = df.head(10)
                for _, row in recent_df.iterrows():
                    result_list.append({
                        'date': str(row.get('日期', '')),
                        'overnight': str(row.get('O/N-定价', '')),
                        'overnight_change': str(row.get('O/N-涨跌幅', '')),
                        '1week': str(row.get('1W-定价', '')),
                        '1week_change': str(row.get('1W-涨跌幅', '')),
                        '2week': str(row.get('2W-定价', '')),
                        '1month': str(row.get('1M-定价', '')),
                        '3month': str(row.get('3M-定价', '')),
                        '6month': str(row.get('6M-定价', '')),
                        '9month': str(row.get('9M-定价', '')),
                        '1year': str(row.get('1Y-定价', '')),
                        'type': 'SHIBOR'
                    })
                self.logger.info(f"获取到 {len(result_list)} 条SHIBOR数据")
                return result_list

            return None

        except Exception as e:
            self.logger.warning(f"获取SHIBOR数据失败: {e}")
            return None

    def _fetch_treasury_yield(self) -> Optional[list[dict]]:
        """
        获取国债收益率数据
        重点获取10年期和30年期国债收益率
        """
        def _call():
            return ak.bond_china_yield()

        try:
            self.logger.info("获取国债收益率数据...")

            # 获取国债收益率曲线
            df = self._safe_call(_call, default_value=None, func_name="ak.bond_china_yield")

            if df is not None and not df.empty:
                result_list = []
                # 筛选国债收益率曲线
                treasury_df = df[df['曲线名称'].str.contains('国债', na=False)]
                # 取最近数据
                recent_df = treasury_df.tail(10)
                for _, row in recent_df.iterrows():
                    result_list.append({
                        'curve_name': str(row.get('曲线名称', '')),
                        'date': str(row.get('日期', '')),
                        '3m': str(row.get('3月', '')),
                        '6m': str(row.get('6月', '')),
                        '1y': str(row.get('1年', '')),
                        '3y': str(row.get('3年', '')),
                        '5y': str(row.get('5年', '')),
                        '7y': str(row.get('7年', '')),
                        '10y': str(row.get('10年', '')),
                        '30y': str(row.get('30年', '')),
                        'type': '国债收益率曲线'
                    })
                self.logger.info(f"获取到 {len(result_list)} 条国债收益率曲线数据")
                return result_list

            return None

        except Exception as e:
            self.logger.warning(f"获取国债收益率数据失败: {e}")
            return None

    def _fetch_cd_rate(self) -> Optional[list[dict]]:
        """
        获取同业存单利率数据
        """
        try:
            self.logger.info("获取同业存单利率数据...")

            # 暂无可用接口，返回提示信息
            self.logger.warning("同业存单利率接口暂不可用，建议从财联社快讯获取相关信息")
            return None

        except Exception as e:
            self.logger.warning(f"获取同业存单数据失败: {e}")
            return None

    def _fetch_repo_rate(self) -> Optional[list[dict]]:
        """
        获取回购利率数据
        """
        try:
            self.logger.info("获取回购利率数据...")

            # 暂无可用接口，返回提示信息
            self.logger.warning("回购利率接口暂不可用，建议从财联社快讯获取相关信息")
            return None

        except Exception as e:
            self.logger.warning(f"获取回购利率数据失败: {e}")
            return None

    def fetch_omo_only(self) -> FetchResult:
        """仅获取央行公开市场操作数据"""
        return self.fetch(data_type="omo")

    def fetch_shibor_only(self) -> FetchResult:
        """仅获取SHIBOR利率数据"""
        return self.fetch(data_type="shibor")

    def fetch_treasury_only(self) -> FetchResult:
        """仅获取国债收益率数据"""
        return self.fetch(data_type="treasury")

    def get_liquidity_summary(self) -> dict:
        """
        获取流动性状态概览摘要
        用于快速判断资金面松紧
        """
        result = self.fetch(data_type="all")

        summary = {
            'data_available': result.success,
            'source': result.source,
            'timestamp': result.timestamp,
            'components': {}
        }

        if result.success and result.data:
            # 分析央行资产负债
            if 'omo' in result.data:
                omo_list = result.data['omo']
                if omo_list:
                    latest_omo = omo_list[0]
                    summary['components']['central_bank'] = {
                        'date': latest_omo.get('date', ''),
                        'total_assets': latest_omo.get('total_assets', ''),
                        'reserve_money': latest_omo.get('reserve_money', ''),
                        'government_deposit': latest_omo.get('government_deposit', '')
                    }

            # 分析SHIBOR水平
            if 'shibor' in result.data:
                shibor_list = result.data['shibor']
                if shibor_list:
                    latest_shibor = shibor_list[0]
                    overnight = latest_shibor.get('overnight', '')
                    summary['components']['shibor'] = {
                        'date': latest_shibor.get('date', ''),
                        'overnight': overnight,
                        'overnight_change': latest_shibor.get('overnight_change', ''),
                        '1week': latest_shibor.get('1week', ''),
                        '1month': latest_shibor.get('1month', '')
                    }

                    # 判断利率水平
                    try:
                        rate_val = float(overnight)
                        if rate_val < 1.5:
                            summary['liquidity_level'] = '宽松'
                        elif rate_val < 2.0:
                            summary['liquidity_level'] = '适度'
                        elif rate_val < 2.5:
                            summary['liquidity_level'] = '收敛'
                        else:
                            summary['liquidity_level'] = '紧张'
                    except:
                        summary['liquidity_level'] = '数据待评估'

            # 分析国债收益率
            if 'treasury_yield' in result.data:
                treasury_list = result.data['treasury_yield']
                if treasury_list:
                    latest = treasury_list[0]
                    summary['components']['treasury'] = {
                        'date': latest.get('date', ''),
                        'curve_name': latest.get('curve_name', ''),
                        '10y': latest.get('10y', ''),
                        '30y': latest.get('30y', '')
                    }

        return summary


# 直接运行测试
if __name__ == '__main__':
    print("\n")
    print("*" * 60)
    print("*" + " " * 18 + "BondFetcher 测试" + " " * 18 + "*")
    print("*" * 60)

    fetcher = BondFetcher()
    print(f"\n抓取器: {fetcher.source_name}")

    # 测试获取所有数据
    print("\n" + "=" * 60)
    print("  测试获取所有债市数据")
    print("=" * 60)

    result = fetcher.safe_fetch()

    print(f"\n状态: {'成功' if result.success else '失败'}")
    print(f"数据源: {result.source}")
    print(f"数据条数: {result.count}")
    print(f"时间戳: {result.timestamp}")

    if result.error:
        print(f"错误信息: {result.error}")

    if result.success and result.data:
        print("\n数据详情:")
        print("-" * 40)

        for key, value in result.data.items():
            print(f"\n【{key}】")
            if isinstance(value, list) and value:
                print(f"  共 {len(value)} 条记录")
                for i, item in enumerate(value[:3], 1):
                    print(f"  [{i}] {item}")
            else:
                print(f"  {value}")

        # 测试流动性摘要
        print("\n" + "=" * 60)
        print("  流动性状态概览")
        print("=" * 60)

        summary = fetcher.get_liquidity_summary()
        print(f"\n流动性水平: {summary.get('liquidity_level', '数据待评估')}")
        print(f"数据可用性: {summary.get('data_available', False)}")

        if 'components' in summary:
            for comp_name, comp_data in summary['components'].items():
                print(f"\n{comp_name}:")
                for k, v in comp_data.items():
                    print(f"  - {k}: {v}")

    else:
        print("\n未获取到数据，可能原因:")
        print("  1. akshare 相关接口暂时不可用")
        print("  2. 需要检查网络连接")
        print("  3. 部分接口需要更新参数")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)