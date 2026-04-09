"""
PDF 报告生成模块（Playwright 版本）
将 Markdown 转换为专业的券商研报风格 PDF
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

import nest_asyncio

# 应用 nest_asyncio 以支持嵌套事件循环
nest_asyncio.apply()

logger = logging.getLogger(__name__)

# 中信红灰主题 CSS 样式（专业研报风格）
REPORT_CSS = """
/* 全局重置 */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'PingFang SC', 'Microsoft YaHei', 'Hiragino Sans GB', 'WenQuanYi Micro Hei', sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #4D4D4D;
    background: #fff;
    padding: 20px 20px 80px 20px; /* 底部留 80px 避免页脚堆叠 */
}

/* 主标题 - 中信红居中 */
h1 {
    font-size: 22pt;
    font-weight: 700;
    color: #E60012; /* 中信红 */
    text-align: center;
    margin-bottom: 0.5em;
    padding-bottom: 0.3em;
    border-bottom: 3px solid #E60012;
}

/* 副标题/日期 */
h1 + p {
    text-align: center;
    font-size: 10pt;
    color: #999999; /* 中灰 */
    margin-bottom: 1.5em;
}

/* 二级标题 - 左侧红色粗边框 */
h2 {
    font-size: 14pt;
    font-weight: 600;
    color: #4D4D4D; /* 深灰 */
    text-align: left;
    margin-top: 1.5em;
    margin-bottom: 0.8em;
    padding-left: 10px;
    border-left: 5px solid #E60012; /* 中信红粗边框 */
}

/* 三级标题 */
h3 {
    font-size: 12pt;
    font-weight: 600;
    color: #4D4D4D;
    margin-top: 1.2em;
    margin-bottom: 0.6em;
}

/* 四级标题 */
h4 {
    font-size: 11pt;
    font-weight: 600;
    color: #4D4D4D;
    margin-top: 1em;
    margin-bottom: 0.5em;
}

/* 段落 */
p {
    margin-bottom: 0.8em;
    text-align: justify;
}

/* 强调 - 中信红 */
strong {
    font-weight: 600;
    color: #E60012;
}

/* 列表 */
ul, ol {
    margin: 0.8em 0;
    padding-left: 1.5em;
}

li {
    margin-bottom: 0.4em;
}

/* 引用块 - 灰色背景 + 红色边框 */
blockquote {
    margin: 1em 0;
    padding: 0.8em 1em;
    background-color: #f9f9f9;
    border-left: 4px solid #E60012;
    color: #4D4D4D;
    font-size: 10pt;
}

blockquote p {
    margin-bottom: 0.4em;
}

/* 分隔线 - 灰色细线 */
hr {
    border: none;
    border-top: 1px solid #999999;
    margin: 1.5em 0;
}

/* 表格 */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    font-size: 10pt;
}

th {
    background-color: #4D4D4D; /* 深灰 */
    color: #fff;
    font-weight: 600;
    padding: 0.6em 0.8em;
    text-align: left;
}

td {
    padding: 0.5em 0.8em;
    border-bottom: 1px solid #999999;
}

tr:nth-child(even) {
    background-color: #f9f9f9;
}

/* 代码块 */
code {
    font-family: "SF Mono", "Menlo", "Monaco", "Courier New", monospace;
    font-size: 9pt;
    background-color: #f5f5f5;
    padding: 0.1em 0.3em;
    border-radius: 3px;
}

pre {
    background-color: #f5f5f5;
    padding: 1em;
    border-radius: 5px;
    overflow-x: auto;
    font-size: 9pt;
    margin: 1em 0;
}

pre code {
    background: none;
    padding: 0;
}

/* 链接 - 中信红 */
a {
    color: #E60012;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

/* 警告/风险提示样式 */
.warning {
    background-color: #fff3cd;
    border-left-color: #ffc107;
    padding: 0.8em 1em;
    margin: 1em 0;
}

/* 成功/利好样式 */
.success {
    background-color: #d4edda;
    border-left-color: #28a745;
    padding: 0.8em 1em;
    margin: 1em 0;
}

/* 表格头部悬停效果 */
th:hover {
    background-color: #333;
}

/* 打印优化 - 移除页脚绝对定位，使用 Playwright 原生页脚 */
@media print {
    body {
        padding: 0;
    }

    @page {
        size: A4;
        margin: 2.5cm 2cm 2cm 2cm;
    }
}
"""


class PDFGenerator:
    """
    PDF 报告生成器（Playwright 版本）
    将 Markdown 转换为专业的券商研报风格 PDF
    """

    def __init__(self, output_dir: str = "reports"):
        """
        初始化 PDF 生成器

        Args:
            output_dir: PDF 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self._check_dependencies()

    def _check_dependencies(self):
        """检查依赖库"""
        self._markdown_available = False
        self._playwright_available = False

        try:
            import markdown
            self._markdown_available = True
        except ImportError:
            logger.warning("markdown 库未安装，PDF 生成将不可用")

        try:
            import playwright
            self._playwright_available = True
        except ImportError:
            logger.warning("playwright 库未安装，PDF 生成将不可用")
            logger.info("  请运行：pip install playwright && playwright install chromium")

    def generate(
        self,
        markdown_content: str,
        filename: Optional[str] = None,
        title: str = "股债双市每日跟踪报告"
    ) -> Optional[str]:
        """
        生成 PDF 报告（同步接口，内部使用异步）

        Args:
            markdown_content: Markdown 格式的报告内容
            filename: 输出文件名（不含扩展名），默认使用日期
            title: 报告标题

        Returns:
            str: 生成的 PDF 文件绝对路径，失败返回 None
        """
        # 检查依赖
        if not self._markdown_available or not self._playwright_available:
            logger.warning("PDF 生成依赖不完整，跳过 PDF 生成")
            return None

        try:
            import markdown
        except ImportError:
            logger.error("markdown 库加载失败")
            return None

        logger.info("📄 开始生成 PDF 报告...")

        # 生成文件名
        if filename is None:
            filename = f"daily_report_{datetime.now().strftime('%Y-%m-%d')}"

        pdf_path = self.output_dir / f"{filename}.pdf"

        try:
            # 1. Markdown 转 HTML
            logger.info("  ├─ 转换 Markdown → HTML")
            md = markdown.Markdown(extensions=[
                'tables',
                'fenced_code',
                'nl2br',
                'sane_lists'
            ])
            html_body = md.convert(markdown_content)

            # 2. 构建完整 HTML 文档
            html_content = self._build_html_document(html_body, title)

            # 3. 使用 Playwright 异步生成 PDF
            logger.info("  ├─ 启动 Playwright 渲染 PDF")

            # 运行异步 PDF 生成
            pdf_path_result = asyncio.run(self._generate_pdf_async(html_content, str(pdf_path)))

            if pdf_path_result:
                logger.info(f"  └─ ✅ PDF 生成成功：{pdf_path_result}")
            else:
                logger.warning("  └─ ⚠️ PDF 生成失败")

            return pdf_path_result

        except Exception as e:
            logger.error(f"  └─ ❌ PDF 生成失败：{e}")
            logger.error(f"      详细错误：{type(e).__name__}")
            return None

    async def _generate_pdf_async(self, html_content: str, output_path: str) -> Optional[str]:
        """
        使用 Playwright 异步生成 PDF

        Args:
            html_content: 完整的 HTML 文档内容
            output_path: 输出 PDF 文件路径

        Returns:
            str: PDF 文件路径，失败返回 None
        """
        from playwright.async_api import async_playwright

        try:
            async with async_playwright() as p:
                # 启动 headless Chromium
                browser = await p.chromium.launch(headless=True)

                # 创建新页面
                page = await browser.new_page()

                # 设置 HTML 内容
                await page.set_content(html_content, wait_until='networkidle')

                # 等待页面渲染完成
                await page.wait_for_load_state('networkidle')

                # 生成 PDF - 使用 Playwright 原生页脚
                footer_date = datetime.now().strftime('%Y年%m月%d日 %H:%M')

                await page.pdf(
                    path=output_path,
                    format='A4',
                    print_background=True,
                    display_header_footer=True,
                    header_template='<span></span>',  # 清空页眉
                    footer_template=f"""
                    <div style="font-size: 10px; color: #999999; text-align: center; width: 100%; padding-bottom: 15px; font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;">
                        本报告由中信银行武汉分行投行部投研多智能体系统生成，仅供参考，不构成投资建议。<br>
                        生成时间：{footer_date}
                    </div>
                    """,
                    margin={
                        'top': '2.5cm',
                        'right': '2cm',
                        'bottom': '3.5cm',  # 增加底部边距容纳原生页脚
                        'left': '2cm'
                    }
                )

                # 关闭浏览器
                await browser.close()

                return output_path

        except Exception as e:
            logger.error(f"Playwright PDF 生成失败：{e}")
            return None

    def _build_html_document(self, body_html: str, title: str) -> str:
        """
        构建完整的 HTML 文档

        Args:
            body_html: 转换后的 HTML 正文
            title: 文档标题

        Returns:
            str: 完整的 HTML 文档
        """
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
{REPORT_CSS}
    </style>
</head>
<body>
{body_html}

</body>
</html>"""

    def generate_from_file(self, md_file_path: str) -> Optional[str]:
        """
        从 Markdown 文件生成 PDF

        Args:
            md_file_path: Markdown 文件路径

        Returns:
            str: 生成的 PDF 文件路径
        """
        md_path = Path(md_file_path)

        if not md_path.exists():
            logger.error(f"Markdown 文件不存在：{md_file_path}")
            return None

        # 读取 Markdown 内容
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 使用文件名（去掉扩展名）作为输出文件名
        filename = md_path.stem

        return self.generate(content, filename=filename)


# 便捷函数
def generate_pdf_report(
    markdown_content: str,
    output_dir: str = "reports",
    filename: Optional[str] = None
) -> Optional[str]:
    """
    生成 PDF 报告的便捷函数

    Args:
        markdown_content: Markdown 内容
        output_dir: 输出目录
        filename: 文件名

    Returns:
        str: PDF 文件路径
    """
    generator = PDFGenerator(output_dir=output_dir)
    return generator.generate(markdown_content, filename=filename)


if __name__ == '__main__':
    # 测试 PDF 生成
    import sys

    logging.basicConfig(level=logging.INFO)

    # 测试内容
    test_markdown = """
# 📅 股债双市每日跟踪报告
**报告日期：2026 年 04 月 08 日**

---

## 🔴 宏观与政策风向

### 偏乐观

**宏观利好因子（Bull 视角）：**

- **降准政策** (高影响)
  - 降准 0.5 个百分点释放 1 万亿长期资金
  - 受影响资产：A 股，债券

**宏观风险因子（Bear 视角）：**

- **通胀过低** (中影响)
  - CPI 同比仅 0.1%，需求端仍显疲弱

> 风险提示：内需恢复仍需时间，需关注后续政策力度

---

## 📈 A 股主线与热点异动

### 市场整体：震荡

| 板块 | 热度 | 资金流向 | 持续性 |
|------|------|----------|--------|
| 半导体 | 高热 | 流入 | 可持续 |
| AI 算力 | 高热 | 流入 | 可持续 |
| 新能源 | 温热 | 中性 | 待观察 |

---

## 📉 债市与流动性观察

### 流动性水位：宽松

- **央行 OMO：** 净投放 (1000 亿)
- **10Y 国债：** 2.28%
- **债市情绪：** 偏多

---

## ⚠️ 跨资产共振与风险预警

**整体判断：** 各资产类别逻辑一致，无明显背离信号。
"""

    result = generate_pdf_report(test_markdown)

    if result:
        print(f"\n✅ 测试成功，PDF 已生成：{result}")
    else:
        print("\n❌ 测试失败")
        sys.exit(1)
