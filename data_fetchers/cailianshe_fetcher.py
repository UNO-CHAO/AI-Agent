"""
财联社电报数据抓取器
使用 akshare 获取财联社电报资讯
"""

import akshare as ak
import pandas as pd
from typing import Optional

from .base_fetcher import BaseFetcher, FetchResult


class CailiansheFetcher(BaseFetcher):
    """
    财联社电报数据抓取器
    获取高质量财经新闻资讯
    """

    def __init__(self, max_items: int = 60):
        """
        初始化财联社电报抓取器

        Args:
            max_items: 最大获取条数，默认60条
        """
        super().__init__(source_name="财联社电报")
        self.max_items = max_items

    def fetch(self, max_items: Optional[int] = None) -> FetchResult:
        """
        获取财联社电报资讯

        Args:
            max_items: 本次获取的最大条数，如未指定则使用初始化时的值

        Returns:
            FetchResult: 包含资讯列表的结果对象
        """
        limit = max_items or self.max_items

        try:
            self.logger.info(f"正在获取财联社电报数据...")
            df = ak.stock_info_global_cls()

            if df is None or df.empty:
                return FetchResult(
                    success=False,
                    error="获取到的数据为空",
                    source=self.source_name
                )

            # 限制条数
            df = df.head(limit)

            # 标准化数据
            news_list = self.normalize(df)

            self.logger.info(f"成功获取 {len(news_list)} 条财联社电报资讯")

            return FetchResult(
                success=True,
                data=news_list,
                source=self.source_name,
                count=len(news_list)
            )

        except Exception as e:
            self.logger.error(f"获取财联社电报数据失败: {e}")
            return FetchResult(
                success=False,
                error=str(e),
                source=self.source_name
            )

    def normalize(self, raw_data: pd.DataFrame) -> list[dict]:
        """
        将原始 DataFrame 标准化为字典列表

        Args:
            raw_data: akshare 返回的原始 DataFrame

        Returns:
            list[dict]: 标准化的资讯列表
        """
        news_list = []

        for _, row in raw_data.iterrows():
            title = str(row.get('标题', ''))
            content = str(row.get('内容', ''))

            # 如果标题为空，使用内容前50字作为标题
            if not title or title == 'nan':
                title = content[:50] if content else ''

            # 处理时间和日期
            date_str = str(row.get('发布日期', ''))
            time_str = str(row.get('发布时间', ''))

            # 清理 nan 值
            date_str = '' if date_str == 'nan' else date_str
            time_str = '' if time_str == 'nan' else time_str

            news_list.append({
                'datetime': f"{date_str} {time_str}".strip(),
                'date': date_str,
                'time': time_str,
                'title': title,
                'content': content,
                'source': self.source_name,
                'category': '快讯'
            })

        return news_list

    def fetch_as_dataframe(self, max_items: Optional[int] = None) -> pd.DataFrame:
        """
        获取数据并返回 DataFrame 格式

        Args:
            max_items: 最大获取条数

        Returns:
            pd.DataFrame: 资讯数据表
        """
        result = self.fetch(max_items)
        if result.success and result.data:
            return pd.DataFrame(result.data)
        return pd.DataFrame()