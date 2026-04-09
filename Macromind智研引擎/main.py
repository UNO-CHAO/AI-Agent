"""
主程序入口（异步架构 v2)
工作流：并发获取数据 → 并发分析 → 生成报告 → PDF导出 → 飞书推送

流程编排：
1. 并发调用4个Fetcher获取数据
2. 数据分发给3个Agent并发分析
3. ChiefSynthesizer综合生成Markdown报告
4. PDFGenerator生成专业研报PDF
5. FeishuClient推送PDF附件到群聊
"""

import asyncio
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

from dotenv import load_dotenv

from data_fetchers import (
    CailiansheFetcher,
    MacroPolicyFetcher,
    MarketHotspotFetcher,
    BondFetcher,
    FetchResult
)
from agents import (
    MacroAgent,
    StrategyAgent,
    BondAgent,
    ChiefSynthesizer,
    AgentResult
)
from utils.pdf_generator import PDFGenerator
from notifier import FeishuClient, send_report_to_feishu, send_markdown_to_feishu

# ============================================================================
# 日志配置
# ============================================================================

def setup_logging():
    """配置日志格式"""
    log_format = '%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(),
        ]
    )

    # 添加文件日志
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"pipeline_{datetime.now().strftime('%Y%m%d')}.log"

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    logging.getLogger().addHandler(file_handler)


logger = logging.getLogger(__name__)


# ============================================================================
# 流程编排器
# ============================================================================

class PipelineOrchestrator:
    """
    流程编排器
    管理完整的数据获取 → 分析 → 报告生成 → PDF导出 → 推送 流程
    """

    def __init__(self, api_key: str, model: str = "qwen-plus"):
        """
        初始化编排器

        Args:
            api_key: LLM API Key
            model: 使用的模型名称
        """
        self.api_key = api_key
        self.model = model
        self.start_time: float = 0

        # 初始化 Fetchers
        self.fetchers = {
            'cailianshe': CailiansheFetcher(max_items=30),
            'macro': MacroPolicyFetcher(),
            'market': MarketHotspotFetcher(),
            'bond': BondFetcher()
        }

        # 初始化 PDF 生成器
        self.pdf_generator = PDFGenerator(output_dir="reports")

        # 初始化 Agents (延迟初始化)
        self._agents_initialized = False
        self.macro_agent: Optional[MacroAgent] = None
        self.strategy_agent: Optional[StrategyAgent] = None
        self.bond_agent: Optional[BondAgent] = None
        self.chief: Optional[ChiefSynthesizer] = None

    def _init_agents(self):
        """延迟初始化 Agents"""
        if self._agents_initialized:
            return

        self.macro_agent = MacroAgent(model=self.model, api_key=self.api_key)
        self.strategy_agent = StrategyAgent(model=self.model, api_key=self.api_key)
        self.bond_agent = BondAgent(model=self.model, api_key=self.api_key)
        self.chief = ChiefSynthesizer(model=self.model, api_key=self.api_key)
        self._agents_initialized = True

    async def run(self) -> tuple[str, str, dict]:
        """
        执行完整流程

        Returns:
            tuple: (markdown_report, pdf_path, pipeline_metrics)
        """
        self.start_time = time.time()
        metrics = {
            'start_time': datetime.now().isoformat(),
            'stages': {}
        }

        logger.info("=" * 60)
        logger.info("🚀 启动 MacroMind 智研引擎 v2")
        logger.info("=" * 60)

        try:
            # ========== 阶段1：并发数据获取 ==========
            stage1_start = time.time()
            logger.info("\n【阶段1】并发数据获取...")

            fetch_results = await self._fetch_all_data()

            metrics['stages']['fetch'] = {
                'duration': time.time() - stage1_start,
                'status': {name: r.success for name, r in fetch_results.items()},
                'counts': {name: r.count for name, r in fetch_results.items()}
            }

            self._log_fetch_results(fetch_results)

            # 检查是否至少有一个数据源成功
            if not any(r.success for r in fetch_results.values()):
                raise RuntimeError("所有数据源获取失败，无法继续分析")

            # ========== 阶段2：并发Agent分析 ==========
            stage2_start = time.time()
            logger.info("\n【阶段2】并发Agent分析...")

            self._init_agents()

            agent_results = await self._run_all_agents(fetch_results)

            metrics['stages']['analyze'] = {
                'duration': time.time() - stage2_start,
                'status': {name: r.success for name, r in agent_results.items()}
            }

            self._log_agent_results(agent_results)

            # ========== 阶段3：综合报告生成 ==========
            stage3_start = time.time()
            logger.info("\n【阶段3】综合报告生成...")

            markdown_report = await self._synthesize_report(agent_results)

            metrics['stages']['synthesize'] = {
                'duration': time.time() - stage3_start,
                'report_length': len(markdown_report)
            }

            # ========== 阶段4：PDF导出 ==========
            stage4_start = time.time()
            logger.info("\n【阶段4】PDF导出...")

            pdf_path = await self._generate_pdf(markdown_report)

            metrics['stages']['pdf'] = {
                'duration': time.time() - stage4_start,
                'success': pdf_path is not None
            }

            # 计算总耗时
            metrics['total_duration'] = time.time() - self.start_time

            logger.info(f"\n✅ 流程完成，总耗时: {metrics['total_duration']:.2f}秒")

            return markdown_report, pdf_path or "", metrics

        except Exception as e:
            logger.error(f"\n❌ 流程执行失败: {e}")
            metrics['error'] = str(e)
            metrics['total_duration'] = time.time() - self.start_time
            raise

    async def _fetch_all_data(self) -> dict[str, FetchResult]:
        """
        并发调用4个Fetcher获取数据
        """
        fetcher_names = list(self.fetchers.keys())
        logger.info(f"  启动 {len(fetcher_names)} 个数据抓取器: {', '.join(fetcher_names)}")

        tasks = [
            self._async_fetch(name, fetcher)
            for name, fetcher in self.fetchers.items()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        fetch_results = {}
        for name, result in zip(fetcher_names, results):
            if isinstance(result, Exception):
                logger.error(f"  ❌ {name} 获取异常: {result}")
                fetch_results[name] = FetchResult(
                    success=False,
                    error=str(result),
                    source=name
                )
            else:
                fetch_results[name] = result

        return fetch_results

    async def _async_fetch(self, name: str, fetcher: Any) -> FetchResult:
        """异步包装 Fetcher"""
        loop = asyncio.get_event_loop()

        def _fetch():
            try:
                return fetcher.safe_fetch()
            except Exception as e:
                return FetchResult(success=False, error=str(e), source=name)

        result = await loop.run_in_executor(None, _fetch)
        logger.info(f"  ✅ {name} 完成: {result.count if result.success else 0} 条数据")
        return result

    async def _run_all_agents(self, fetch_results: dict) -> dict[str, AgentResult]:
        """
        并发运行3个Agent进行分析
        """
        agent_names = ['macro', 'strategy', 'bond']
        logger.info(f"  启动 {len(agent_names)} 个分析师Agent: {', '.join(agent_names)}")

        inputs = {
            'macro': self._prepare_macro_input(fetch_results),
            'strategy': self._prepare_strategy_input(fetch_results),
            'bond': self._prepare_bond_input(fetch_results)
        }

        tasks = [
            self._async_analyze(name, agent, inputs[name])
            for name, agent in [
                ('macro', self.macro_agent),
                ('strategy', self.strategy_agent),
                ('bond', self.bond_agent)
            ]
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        agent_results = {}
        for name, result in zip(agent_names, results):
            if isinstance(result, Exception):
                logger.error(f"  ❌ {name}Agent 分析异常: {result}")
                agent_results[name] = AgentResult(
                    success=False,
                    agent_name=f"{name}Agent",
                    error=str(result)
                )
            else:
                agent_results[name] = result

        return agent_results

    async def _async_analyze(self, name: str, agent: Any, data: Any) -> AgentResult:
        """异步包装 Agent 分析"""
        loop = asyncio.get_event_loop()

        def _analyze():
            try:
                return agent.safe_analyze(data)
            except Exception as e:
                return AgentResult(
                    success=False,
                    agent_name=f"{name}Agent",
                    error=str(e)
                )

        result = await loop.run_in_executor(None, _analyze)

        status = "✅" if result.success else "❌"
        logger.info(f"  {status} {name}Agent 完成")
        return result

    async def _synthesize_report(self, agent_results: dict) -> str:
        """综合生成最终报告"""
        loop = asyncio.get_event_loop()

        macro_result = agent_results.get('macro', AgentResult(success=False, agent_name='macro'))
        strategy_result = agent_results.get('strategy', AgentResult(success=False, agent_name='strategy'))
        bond_result = agent_results.get('bond', AgentResult(success=False, agent_name='bond'))

        def _synthesize():
            try:
                return self.chief.synthesize(macro_result, strategy_result, bond_result)
            except Exception as e:
                logger.error(f"Chief综合失败: {e}")
                return AgentResult(
                    success=False,
                    agent_name="ChiefSynthesizer",
                    error=str(e)
                )

        result = await loop.run_in_executor(None, _synthesize)

        if result.success:
            logger.info(f"  ✅ Markdown报告生成完成: {len(result.raw_response)} 字符")
            return result.raw_response
        else:
            logger.warning("  ⚠️ 报告生成异常，生成兜底报告")
            return self._generate_fallback_report(agent_results)

    async def _generate_pdf(self, markdown_content: str) -> Optional[str]:
        """生成 PDF 报告"""
        loop = asyncio.get_event_loop()

        def _generate():
            return self.pdf_generator.generate(markdown_content)

        pdf_path = await loop.run_in_executor(None, _generate)

        if pdf_path:
            logger.info(f"  ✅ PDF报告生成完成: {pdf_path}")
        else:
            logger.warning("  ⚠️ PDF生成失败，将仅保存Markdown")

        return pdf_path

    def _prepare_macro_input(self, fetch_results: dict) -> dict:
        """准备MacroAgent输入数据"""
        data = {}
        if fetch_results['macro'].success and fetch_results['macro'].data:
            data.update(fetch_results['macro'].data)
        if fetch_results['cailianshe'].success and fetch_results['cailianshe'].data:
            data['cailianshe_news'] = fetch_results['cailianshe'].data
        return data

    def _prepare_strategy_input(self, fetch_results: dict) -> dict:
        """准备StrategyAgent输入数据"""
        data = {}
        if fetch_results['market'].success and fetch_results['market'].data:
            data.update(fetch_results['market'].data)
        if fetch_results['cailianshe'].success and fetch_results['cailianshe'].data:
            data['cailianshe_news'] = fetch_results['cailianshe'].data
        return data

    def _prepare_bond_input(self, fetch_results: dict) -> dict:
        """准备BondAgent输入数据"""
        data = {}
        if fetch_results['bond'].success and fetch_results['bond'].data:
            data.update(fetch_results['bond'].data)
        if fetch_results['cailianshe'].success and fetch_results['cailianshe'].data:
            data['cailianshe_news'] = fetch_results['cailianshe'].data
        if fetch_results['macro'].success and fetch_results['macro'].data:
            macro_data = fetch_results['macro'].data
            if 'interest_rate' in macro_data:
                data['interest_rate'] = macro_data['interest_rate']
            if 'm2' in macro_data:
                data['m2'] = macro_data['m2']
        return data

    def _log_fetch_results(self, results: dict):
        """打印数据获取结果"""
        logger.info("  ┌─ 数据获取结果 ──────────────────┐")
        for name, result in results.items():
            status = "✅" if result.success else "❌"
            count = result.count if result.success else 0
            error = f" ({result.error[:25]}...)" if not result.success and result.error else ""
            logger.info(f"  │ {status} {name:12} {count:3} 条{error}")
        logger.info("  └────────────────────────────────┘")

    def _log_agent_results(self, results: dict):
        """打印Agent分析结果"""
        logger.info("  ┌─ Agent分析结果 ─────────────────┐")
        for name, result in results.items():
            status = "✅" if result.success else "❌"
            error = f" ({result.error[:25]}...)" if not result.success and result.error else ""
            logger.info(f"  │ {status} {name}Agent{error}")
        logger.info("  └────────────────────────────────┘")

    def _generate_fallback_report(self, agent_results: dict) -> str:
        """生成兜底报告"""
        date = datetime.now().strftime("%Y年%m月%d日")
        return f"""# 📅 股债双市每日跟踪报告
**报告日期：{date}**

---

## ⚠️ 系统提示

报告生成过程中部分模块出现异常，以下是各模块状态：

| 模块 | 状态 |
|------|------|
| 宏观分析 | {'✅ 正常' if agent_results.get('macro', AgentResult(success=False)).success else '❌ 异常'} |
| A股策略 | {'✅ 正常' if agent_results.get('strategy', AgentResult(success=False)).success else '❌ 异常'} |
| 债市分析 | {'✅ 正常' if agent_results.get('bond', AgentResult(success=False)).success else '❌ 异常'} |

---

*请检查系统日志获取详细错误信息。*
"""


# ============================================================================
# 辅助函数
# ============================================================================

def save_report(content: str, reports_dir: str = "reports") -> str:
    """保存 Markdown 报告到本地"""
    reports_path = Path(reports_dir)
    reports_path.mkdir(exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"daily_report_{today}.md"
    filepath = reports_path / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return str(filepath)


def print_metrics(metrics: dict):
    """打印性能指标"""
    logger.info("\n" + "=" * 60)
    logger.info("📊 流程性能指标")
    logger.info("=" * 60)

    stages = metrics.get('stages', {})

    # 阶段耗时
    stage_names = {
        'fetch': '数据获取',
        'analyze': 'Agent分析',
        'synthesize': '报告生成',
        'pdf': 'PDF导出'
    }

    for key, name in stage_names.items():
        if key in stages:
            duration = stages[key].get('duration', 0)
            logger.info(f"  阶段: {name} → {duration:.2f}秒")

    # 总耗时
    total = metrics.get('total_duration', 0)
    logger.info(f"  " + "-" * 30)
    logger.info(f"  总耗时: {total:.2f}秒")

    # 数据统计
    if 'fetch' in stages and 'counts' in stages['fetch']:
        logger.info("\n  数据统计:")
        counts = stages['fetch']['counts']
        total_items = sum(counts.values())
        for name, count in counts.items():
            logger.info(f"    • {name}: {count} 条")
        logger.info(f"    • 总计: {total_items} 条")


def extract_summary(markdown_content: str, max_length: int = 300) -> str:
    """
    从报告中提取摘要（用于飞书消息）
    """
    lines = markdown_content.split('\n')

    # 提取核心观点
    summary_parts = []

    for line in lines:
        line = line.strip()
        # 跳过空行和分隔线
        if not line or line.startswith('---') or line.startswith('#'):
            continue

        # 提取核心判断
        if '核心判断' in line or '整体判断' in line:
            summary_parts.append(line)

        # 提取流动性状态
        if '流动性' in line and '：' in line:
            summary_parts.append(line)

        # 提取市场情绪
        if '市场整体' in line or '情绪' in line:
            summary_parts.append(line)

        if len('\n'.join(summary_parts)) > max_length:
            break

    if summary_parts:
        return '\n'.join(summary_parts[:5])
    else:
        return "今日宏观与A股主线推演报告已生成，请查看附件获取详情。"


# ============================================================================
# 主流程
# ============================================================================

async def main():
    """主流程入口"""
    # 设置日志
    setup_logging()

    # 加载环境变量
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path)

    # 获取配置
    api_key = os.environ.get('DASHSCOPE_API_KEY')
    feishu_app_id = os.environ.get('FEISHU_APP_ID')
    feishu_app_secret = os.environ.get('FEISHU_APP_SECRET')
    feishu_chat_id = os.environ.get('FEISHU_CHAT_ID')

    # 检查API Key
    if not api_key:
        logger.error("❌ 未找到 DASHSCOPE_API_KEY，请检查 .env 文件")
        return

    logger.info(f"🔑 API Key 已加载")

    # 检查飞书配置
    feishu_configured = all([feishu_app_id, feishu_app_secret, feishu_chat_id])
    if feishu_configured:
        logger.info("📤 飞书配置完整，将推送PDF附件")
    else:
        logger.info("⚠️ 飞书配置不完整，跳过推送")

    try:
        # 创建编排器并执行
        orchestrator = PipelineOrchestrator(api_key=api_key)
        markdown_report, pdf_path, metrics = await orchestrator.run()

        # 保存 Markdown 报告
        logger.info("\n【阶段5】保存报告...")
        md_path = save_report(markdown_report)
        logger.info(f"  ✅ Markdown已保存: {md_path}")

        # 推送飞书
        if feishu_configured:
            logger.info("\n【阶段6】推送飞书...")

            # 提取摘要
            summary = extract_summary(markdown_report)

            if pdf_path:
                # 发送 PDF 附件
                result = await send_report_to_feishu(
                    pdf_path=pdf_path,
                    summary=summary,
                    title="📅 股债双市每日跟踪报告"
                )
            else:
                # PDF 不可用，发送 Markdown 消息
                logger.info("  📄 PDF不可用，发送 Markdown 消息...")
                result = await send_markdown_to_feishu(
                    title="📅 股债双市每日跟踪报告",
                    content=markdown_report
                )

            if result.get("success"):
                logger.info("  ✅ 飞书推送成功")
            else:
                logger.warning(f"  ⚠️ 飞书推送失败: {result.get('error')}")
        else:
            logger.info("\n  ⚠️ 飞书未配置，跳过推送")

        # 打印性能指标
        print_metrics(metrics)

        logger.info("\n" + "=" * 60)
        logger.info("🏁 任务完成")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"\n❌ 流程执行失败: {e}")
        raise


def run():
    """同步入口"""
    asyncio.run(main())


if __name__ == '__main__':
    run()