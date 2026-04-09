# MacroMind 智研引擎

> 基于多智能体（Multi-Agent）架构的宏观投研分析系统  
> 模拟专业投研团队工作流，自动生成券商风格研报

---

## 目录

- [项目概述](#项目概述)
- [核心特性](#核心特性)
- [文件结构详解](#文件结构详解)
- [快速开始](#快速开始)
- [技术架构概览](#技术架构概览)
- [依赖环境](#依赖环境)
- [配置说明](#配置说明)
- [运行指南](#运行指南)
- [输出说明](#输出说明)
- [扩展开发](#扩展开发)
- [故障处理](#故障处理)
- [风险提示](#风险提示)

---

## 项目概述

**MacroMind 智研引擎** 是一套基于多智能体（Multi-Agent）架构的自动化投研分析系统，专为银行投行部、券商研究所等金融机构设计。系统模拟专业投研团队的工作流程，通过并行的数据采集、智能分析和报告生成，每日自动产出符合券商研报标准的股债双市跟踪报告。

### 系统定位

| 维度 | 说明 |
|------|------|
| **目标用户** | 银行投行部、券商研究所、基金公司投研团队 |
| **核心价值** | 自动化采集→分析→报告全流程，节省人工整理时间 |
| **输出形式** | Markdown 报告 + PDF 研报 + 飞书推送 |
| **数据覆盖** | 宏观经济、政策动态、A 股热点、债市流动性 |

### 工作流程

```
数据采集 → 智能分析 → 报告合成 → PDF 导出 → 消息推送
   │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼
4 个 Fetcher  3 个 Agent  Chief     Playwright  飞书 API
```

---

## 核心特性

### 🔄 异步多智能体架构

- **并发数据获取**：4 个数据抓取器并行运行，大幅缩短采集时间
- **并行 Agent 分析**：宏观、A 股、债市三个分析师同步工作
- **智能容错机制**：单点失败不影响整体流程，内置重试机制

### 📊 专业投研分析框架

| Agent | 角色定位 | 分析维度 |
|-------|----------|----------|
| **MacroAgent** | 资深宏观分析师 | 多空双视角（Bull/Bear 因子）、政策影响评估、国际形势分析 |
| **StrategyAgent** | A 股策略师 | 板块热度、资金流向、量价信号、持续性判断 |
| **BondAgent** | 固收分析师 | 流动性水位、利率债趋势、安全边际评估 |
| **ChiefSynthesizer** | 首席策略师 | 跨资产逻辑校验、风险/机会共振识别、报告整合 |

### 📄 券商研报风格输出

- **专业排版**：中信红灰主题 CSS，符合行业标准视觉风格
- **结构化内容**：严格遵循券商研报章节结构
- **PDF 导出**：Playwright 渲染，支持页眉页脚、专业字体

### 🔔 飞书原生 API 集成

- **PDF 附件推送**：直接发送 PDF 文件到指定群聊
- **卡片消息**：富文本摘要 + 附件组合展示
- **企业级安全**：Tenant Access Token 认证，支持权限管理

### 🛡️ 健壮性设计

- **重试机制**：数据抓取失败自动重试（最多 3 次）
- **兜底报告**：部分模块失败时生成降级版本
- **详细日志**：按日期分文件存储，便于问题排查

---

## 文件结构详解

```
MacroMind/
├── .env                        # 环境变量配置文件（API Key 等敏感信息）
├── main.py                     # 主程序入口，流程编排器
├── notifier.py                 # 飞书推送模块（原生 API 集成）
├── requirements.txt            # Python 依赖清单
├── run.sh                      # 快速启动脚本
├── README.md                   # 项目文档
│
├── agents/                     # 智能体分析层
│   ├── __init__.py             # 模块导出
│   ├── base_agent.py           # Agent 基类（统一接口定义）
│   ├── macro_agent.py          # 宏观分析师（多空双视角分析）
│   ├── strategy_agent.py       # A 股策略师（板块热点分析）
│   ├── bond_agent.py           # 固收分析师（流动性监控）
│   └── chief_synthesizer.py    # 首席架构师（跨资产逻辑校验）
│
├── data_fetchers/              # 数据获取层
│   ├── __init__.py             # 模块导出
│   ├── base_fetcher.py         # Fetcher 基类（重试机制）
│   ├── cailianshe_fetcher.py   # 财联社电报抓取器
│   ├── macro_policy_fetcher.py # 宏观政策数据抓取器
│   ├── market_hotspot_fetcher.py # 市场热点数据抓取器
│   └── bond_fetcher.py         # 债市流动性数据抓取器
│
├── utils/                      # 工具模块
│   ├── __init__.py             # 模块导出
│   └── pdf_generator.py        # PDF 生成器（Playwright 渲染）
│
├── logs/                       # 日志输出目录（自动生成）
│   └── pipeline_YYYYMMDD.log   # 按日期分文件的运行日志
│
└── reports/                    # 报告输出目录（自动生成）
    ├── daily_report_YYYY-MM-DD.md  # Markdown 格式报告
    └── daily_report_YYYY-MM-DD.pdf # PDF 格式研报
```

### 模块职责说明

| 目录/文件 | 职责 | 关键类/函数 |
|-----------|------|-------------|
| `main.py` | 流程编排 | `PipelineOrchestrator`、`main()` |
| `agents/base_agent.py` | Agent 抽象 | `BaseAgent`、`AgentResult` |
| `agents/macro_agent.py` | 宏观分析 | `MacroAgent`、`MacroAnalysisOutput` |
| `agents/strategy_agent.py` | A 股分析 | `StrategyAgent`、`StrategyAnalysisOutput` |
| `agents/bond_agent.py` | 债市分析 | `BondAgent`、`BondAnalysisOutput` |
| `agents/chief_synthesizer.py` | 报告合成 | `ChiefSynthesizer`、`CrossAssetWarning` |
| `data_fetchers/base_fetcher.py` | 数据抓取抽象 | `BaseFetcher`、`FetchResult`、`retry()` |
| `data_fetchers/cailianshe_fetcher.py` | 财联社数据 | `CailiansheFetcher` |
| `data_fetchers/macro_policy_fetcher.py` | 宏观数据 | `MacroPolicyFetcher` |
| `data_fetchers/market_hotspot_fetcher.py` | 市场热点 | `MarketHotspotFetcher` |
| `data_fetchers/bond_fetcher.py` | 债市数据 | `BondFetcher` |
| `utils/pdf_generator.py` | PDF 生成 | `PDFGenerator`、`REPORT_CSS` |
| `notifier.py` | 飞书推送 | `FeishuClient`、`send_report_to_feishu()` |

---

## 快速开始

### 1. 环境准备

#### 系统要求

| 项目 | 要求 |
|------|------|
| **Python** | 3.10 或更高版本 |
| **操作系统** | macOS / Linux / Windows |
| **网络连接** | 可访问 akshare 数据源和阿里云百炼 API |
| **磁盘空间** | 至少 500MB（含依赖库） |

#### 检查 Python 版本

```bash
python --version
# 或
python3 --version
```

### 2. 克隆/下载项目

```bash
# 进入项目目录
cd /path/to/MacroMind
```

### 3. 安装依赖

#### 3.1 安装 Python 包

```bash
# 使用 pip 安装依赖
pip install -r requirements.txt
```

#### 3.2 安装 Playwright 浏览器（PDF 生成必需）

```bash
# 安装 Playwright 及 Chromium 浏览器
playwright install chromium

# 可选：安装系统依赖（Linux 需要）
playwright install-deps chromium
```

> **注意**：Playwright 首次下载 Chromium 可能需要几分钟，请保持网络连接。

### 4. 配置 API Key

#### 4.1 创建 .env 文件

在项目根目录创建 `.env` 文件：

```bash
# LLM API 配置（必填）
DASHSCOPE_API_KEY=sk-your-api-key-here

# 飞书推送配置（可选，仅自动推送时需要）
FEISHU_APP_ID=cli_xxxxxxxxxxxxx
FEISHU_APP_SECRET=your-app-secret-here
FEISHU_CHAT_ID=oc_xxxxxxxxxxxxxxxxx
```

#### 4.2 获取阿里云百炼 API Key

1. 访问 [阿里云百炼控制台](https://dashscope.console.aliyun.com/)
2. 登录阿里云账号
3. 进入「API-KEY 管理」页面
4. 点击「创建新的 API-KEY」
5. 复制生成的 Key 到 `.env` 文件

#### 4.3 获取飞书应用凭证（可选）

如需自动推送报告到飞书群聊，需配置飞书企业应用：

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 登录企业管理后台
3. 进入「企业与集成」→「自建应用」
4. 创建新应用，获取 `App ID` 和 `App Secret`
5. 为应用开通「机器人」「消息推送」「文件上传」权限
6. 在目标群聊中添加机器人，获取 `Chat ID`

> **Chat ID 获取方法**：在飞书群聊中右键 → 群设置 → 复制链接，URL 中的 `chat_id` 参数即为所求。

### 5. 运行程序

#### 方式一：直接运行

```bash
python main.py
```

#### 方式二：使用启动脚本

```bash
bash run.sh
```

#### 预期输出

```
============================================================
🚀 启动 MacroMind 智研引擎 v2
============================================================

【阶段 1】并发数据获取...
  ✅ cailianshe     30 条
  ✅ macro          58 条
  ✅ market         20 条
  ✅ bond           25 条

【阶段 2】并发 Agent 分析...
  ✅ macroAgent
  ✅ strategyAgent
  ✅ bondAgent

【阶段 3】综合报告生成...
  ✅ Markdown 报告生成完成

【阶段 4】PDF 导出...
  ✅ PDF 报告生成完成

【阶段 5】保存报告...
  ✅ Markdown 已保存：reports/daily_report_2026-04-09.md

【阶段 6】推送飞书...
  ✅ 飞书推送成功

============================================================
📊 流程性能指标
============================================================
  总耗时：53.10 秒
  数据总计：133 条
============================================================
```

### 6. 查看输出

#### 生成的文件

| 文件类型 | 路径 | 说明 |
|----------|------|------|
| Markdown 报告 | `reports/daily_report_YYYY-MM-DD.md` | 原始 Markdown 格式，便于二次编辑 |
| PDF 研报 | `reports/daily_report_YYYY-MM-DD.pdf` | 专业排版 PDF，可直接分发 |
| 运行日志 | `logs/pipeline_YYYYMMDD.log` | 详细运行日志，便于问题排查 |

#### 查看报告

```bash
# 查看 Markdown 报告
cat reports/daily_report_$(date +%Y-%m-%d).md

# 打开 PDF 报告（macOS）
open reports/daily_report_$(date +%Y-%m-%d).pdf

# 打开 PDF 报告（Windows）
start reports/daily_report_$(date +%Y-%m-%d).pdf
```

---

## 技术架构概览

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                          用户接口层                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │   main.py       │  │   run.sh        │  │   定时任务       │     │
│  │   流程编排器     │  │   启动脚本       │  │   (cron)        │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        数据获取层 (data_fetchers)                    │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │
│  │ Cailianshe    │  │ MacroPolicy   │  │ MarketHotspot │           │
│  │ 财联社电报     │  │ 宏观/政策数据  │  │ A 股热点/资金流 │           │
│  │ 30 条快讯      │  │ CPI/PPI/PMI   │  │ 龙虎榜/涨跌停  │           │
│  └───────────────┘  └───────────────┘  └───────────────┘           │
│  ┌───────────────┐                                                  │
│  │ BondFetcher   │                                                  │
│  │ 债市/流动性    │                                                  │
│  │ OMO/SHIBOR    │                                                  │
│  └───────────────┘                                                  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Agent 分析层 (agents)                          │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │
│  │ MacroAgent    │  │ StrategyAgent │  │ BondAgent     │           │
│  │ 宏观分析师     │  │ A 股策略师      │  │ 固收分析师     │           │
│  │ Bull/Bear 因子 │  │ 板块热度分析   │  │ 流动性水位     │           │
│  └───────────────┘  └───────────────┘  └───────────────┘           │
│                          │                                          │
│                          ▼                                          │
│              ┌────────────────────────┐                             │
│              │   ChiefSynthesizer     │                             │
│              │   首席综合架构师        │                             │
│              │   跨资产逻辑校验        │                             │
│              └────────────────────────┘                             │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          输出层                                      │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │
│  │ Markdown      │  │ PDF Generator │  │ FeishuClient  │           │
│  │ 报告保存       │  │ Playwright    │  │ 飞书推送       │           │
│  └───────────────┘  └───────────────┘  └───────────────┘           │
└─────────────────────────────────────────────────────────────────────┘
```

### 数据流转图

```
原始数据源                Agent 处理                  最终输出
─────────                ──────────                  ────────
akshare 财经 API    →    MacroAgent    →    宏观利好/风险因子
                       (多空双视角分析)
                                               ↓
akshare 市场数据    →    StrategyAgent →    板块热度/资金流向
                       (板块轮动分析)
                                               ↓
akshare 债市数据    →    BondAgent     →    流动性水位/利率债
                       (流动性监控)            操作建议
                                               ↓
                                               ChiefSynthesizer
                                               (跨资产逻辑校验)
                                               ↓
                                    Markdown + PDF + 飞书推送
```

### 设计模式

| 模式 | 应用场景 |
|------|----------|
| **策略模式** | 不同 Agent 实现各自的分析策略 |
| **工厂模式** | FetchResult/AgentResult 统一结果封装 |
| **模板方法模式** | BaseFetcher/BaseAgent 定义执行框架 |
| **观察者模式** | 日志系统记录各模块状态变化 |

---

## 依赖环境

### Python 依赖

| 包名 | 版本 | 用途 |
|------|------|------|
| `akshare` | latest | 财经数据接口库 |
| `pandas` | latest | 数据处理与分析 |
| `openai` | latest | LLM API 调用（兼容阿里云百炼） |
| `pydantic` | latest | 数据验证与模型定义 |
| `python-dotenv` | latest | 环境变量管理 |
| `requests` | latest | HTTP 请求库 |
| `playwright` | latest | PDF 渲染引擎 |
| `markdown` | latest | Markdown 转 HTML |
| `nest_asyncio` | latest | 事件循环兼容 |
| `requests_toolbelt` | latest | 飞书文件上传 |

### 系统依赖

| 组件 | 用途 | 安装命令 |
|------|------|----------|
| **Chromium** | PDF 渲染浏览器 | `playwright install chromium` |
| **Python 3.10+** | 运行环境 | 系统包管理器安装 |

### 外部 API 依赖

| 服务 | 用途 | 配置项 |
|------|------|--------|
| **阿里云百炼** | LLM 推理 | `DASHSCOPE_API_KEY` |
| **akshare** | 数据采集 | 无需配置 |
| **飞书开放 API** | 消息推送 | `FEISHU_*` 系列 |

---

## 配置说明

### 环境变量

| 变量名 | 必填 | 说明 | 示例 |
|--------|------|------|------|
| `DASHSCOPE_API_KEY` | ✅ | 阿里云百炼 API Key | `sk-xxxxxxxx` |
| `FEISHU_APP_ID` | ❌ | 飞书应用 ID | `cli_xxxxxxxxx` |
| `FEISHU_APP_SECRET` | ❌ | 飞书应用密钥 | `xxxxxxxxxxxx` |
| `FEISHU_CHAT_ID` | ❌ | 飞书群聊 ID | `oc_xxxxxxxxx` |

### 模型配置

在 `main.py` 中可修改使用的模型：

```python
# 默认使用 qwen-plus
orchestrator = PipelineOrchestrator(api_key=api_key, model="qwen-plus")

# 可选模型：
# - qwen-plus:     性价比高（默认）
# - qwen-max:      更强推理能力
# - qwen-turbo:    快速低成本
```

### 日志配置

日志自动保存到 `logs/` 目录，按日期分文件：

```python
# 日志格式
'%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s'
# 示例：2026-04-09 10:30:00 | INFO     | data_fetchers   | 成功获取 30 条数据
```

---

## 运行指南

### 基础运行

```bash
# 确保依赖已安装
pip install -r requirements.txt
playwright install chromium

# 配置 API Key
cp .env.example .env  # 如存在示例文件
# 编辑 .env，填入 DASHSCOPE_API_KEY

# 运行
python main.py
```

### 定时任务配置

#### macOS/Linux (crontab)

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每个交易日早上 9 点运行）
0 9 * * 1-5 cd /path/to/MacroMind && python main.py >> logs/cron.log 2>&1
```

#### Windows (任务计划程序)

1. 打开「任务计划程序」
2. 创建基本任务 → 设置名称（如「MacroMind 研报生成」）
3. 触发器：每周 1-5，时间 9:00
4. 操作：启动程序
   - 程序：`python.exe`（填写完整路径）
   - 参数：`main.py`
   - 起始于：项目完整路径
5. 完成设置

### Docker 部署（可选）

如需容器化部署，可创建 Dockerfile：

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install -r requirements.txt && playwright install chromium

# 复制代码
COPY . .

# 运行
CMD ["python", "main.py"]
```

---

## 输出说明

### 报告结构

生成的 Markdown/PDF 报告包含以下章节：

```markdown
# 📅 股债双市每日跟踪报告
**报告日期：YYYY 年 MM 月 DD 日**

---

## 🔴 宏观与政策风向
- 整体情绪判断（偏乐观/偏谨慎/中性观望）
- 宏观利好因子（Bull 视角）
- 宏观风险因子（Bear 视角）
- 重要政策动向
- 国际形势分析

## 📈 A 股主线与热点异动
- 市场整体情绪（强势/弱势/震荡）
- 资金面判断
- 核心发酵板块（3-5 个）
  - 热度等级、资金流向、量价信号
  - 驱动逻辑、持续性判断
- 龙虎榜解读
- 市场风险提示

## 📉 债市与流动性观察
- 流动性水位（宽松/适度/收敛/紧张）
- 央行 OMO 操作
- 银行间利率水平
- 利率债趋势分析
- 安全边际评估
- 操作建议

## ⚠️ 跨资产共振与风险预警
- 逻辑背离识别
- 风险/机会共振
- 应对建议

---
*免责声明：本报告由系统自动生成，仅供参考，不构成投资建议。*
```

### 控制台输出示例

```
============================================================
🚀 启动 MacroMind 智研引擎 v2
============================================================

【阶段 1】并发数据获取...
  ✅ cailianshe     30 条
  ✅ macro          58 条
  ✅ market         20 条
  ✅ bond           25 条

【阶段 2】并发 Agent 分析...
  ✅ macroAgent
  ✅ strategyAgent
  ✅ bondAgent

【阶段 3】综合报告生成...
  ✅ Markdown 报告生成完成

【阶段 4】PDF 导出...
  ✅ PDF 报告生成完成

【阶段 5】保存报告...
  ✅ Markdown 已保存：reports/daily_report_2026-04-09.md

【阶段 6】推送飞书...
  ✅ 飞书推送成功

============================================================
📊 流程性能指标
============================================================
  阶段：数据获取 → 12.34 秒
  阶段：Agent 分析 → 28.56 秒
  阶段：报告生成 → 8.92 秒
  阶段：PDF 导出 → 3.28 秒
  ──────────────────────────────
  总耗时：53.10 秒

  数据统计:
    • cailianshe: 30 条
    • macro: 58 条
    • market: 20 条
    • bond: 25 条
    • 总计：133 条
============================================================
🏁 任务完成
============================================================
```

---

## 扩展开发

### 添加新数据源

1. 在 `data_fetchers/` 目录创建新的抓取器：

```python
# data_fetchers/my_fetcher.py
from data_fetchers.base_fetcher import BaseFetcher, FetchResult

class MyFetcher(BaseFetcher):
    """自定义数据源抓取器"""
    
    def __init__(self):
        super().__init__(source_name="我的数据源")
    
    def fetch(self) -> FetchResult:
        # 实现数据获取逻辑
        try:
            data = self._get_data()  # 自定义方法
            return FetchResult(
                success=True,
                data=data,
                source=self.source_name,
                count=len(data)
            )
        except Exception as e:
            return FetchResult(
                success=False,
                error=str(e),
                source=self.source_name
            )
    
    def normalize(self, raw_data) -> list[dict]:
        # 实现数据标准化
        result = []
        for item in raw_data:
            result.append({
                'title': item.get('title'),
                'content': item.get('content'),
                'source': self.source_name
            })
        return result
```

2. 在 `main.py` 中注册：

```python
from data_fetchers.my_fetcher import MyFetcher

class PipelineOrchestrator:
    def __init__(self, api_key: str, model: str = "qwen-plus"):
        self.fetchers = {
            'cailianshe': CailiansheFetcher(max_items=30),
            'macro': MacroPolicyFetcher(),
            'market': MarketHotspotFetcher(),
            'bond': BondFetcher(),
            'my_source': MyFetcher()  # 新增
        }
```

### 添加新 Agent

1. 在 `agents/` 目录创建新的分析师：

```python
# agents/my_agent.py
from agents.base_agent import BaseAgent, AgentResult
from pydantic import BaseModel, Field

class MyOutput(BaseModel):
    """定义输出数据结构"""
    conclusion: str = Field(description="分析结论")
    key_points: list[str] = Field(description="关键要点列表")

class MyAgent(BaseAgent):
    """自定义分析师"""
    
    def __init__(self, model: str = "qwen-plus", api_key: str = None):
        super().__init__(
            agent_name="MyAgent",
            role_description="专业分析师角色描述",
            model=model,
            api_key=api_key
        )
    
    def get_system_prompt(self) -> str:
        return """你是专业分析师，负责...
        
## 分析框架
...

## 输出要求
...
"""
    
    def get_output_model(self) -> type[BaseModel]:
        return MyOutput
    
    def format_input(self, data) -> str:
        # 格式化输入数据
        return f"分析数据：{data}"
```

2. 在 `main.py` 中集成：

```python
from agents.my_agent import MyAgent

class PipelineOrchestrator:
    def _init_agents(self):
        self.macro_agent = MacroAgent(model=self.model, api_key=self.api_key)
        self.strategy_agent = StrategyAgent(model=self.model, api_key=self.api_key)
        self.bond_agent = BondAgent(model=self.model, api_key=self.api_key)
        self.my_agent = MyAgent(model=self.model, api_key=self.api_key)  # 新增
        self.chief = ChiefSynthesizer(model=self.model, api_key=self.api_key)
```

### 自定义报告样式

修改 `utils/pdf_generator.py` 中的 CSS：

```python
REPORT_CSS = """
/* 修改主标题颜色 */
h1 {
    color: #0066CC; /* 改为主题蓝 */
    border-bottom-color: #0066CC;
}

/* 修改二级标题边框 */
h2 {
    border-left-color: #0066CC;
}
"""
```

---

## 故障处理

### 常见问题排查表

| 问题现象 | 可能原因 | 解决方案 |
|----------|----------|----------|
| `未找到 DASHSCOPE_API_KEY` | `.env` 文件不存在或配置错误 | 1. 确认 `.env` 在项目根目录<br>2. 检查 `DASHSCOPE_API_KEY=sk-xxx` 格式正确<br>3. 确保无多余空格或引号 |
| `PDF 生成失败` | Playwright 未安装或浏览器缺失 | 1. `pip install playwright`<br>2. `playwright install chromium`<br>3. 检查 Chromium 下载是否完整 |
| `飞书推送失败` | 配置不完整或权限不足 | 1. 确认三个 FEISHU_* 变量都已配置<br>2. 检查飞书应用已开通机器人权限<br>3. 验证 Chat ID 是否正确 |
| `数据获取超时/失败` | 网络问题或 akshare 接口不可用 | 1. 检查网络连接<br>2. 稍后重试（内置 3 次重试）<br>3. 查看 `logs/` 目录详细日志 |
| `ModuleNotFoundError` | 依赖未安装 | `pip install -r requirements.txt` |
| `JSON 解析失败` | LLM 返回格式异常 | 1. 检查 API Key 是否有效<br>2. 尝试切换模型（如 qwen-max）<br>3. 查看日志中原始响应 |

### 日志分析

日志文件位于 `logs/pipeline_YYYYMMDD.log`，关键信息：

```log
# 成功标志
✅ cailianshe     30 条
✅ macroAgent

# 警告信息
⚠️  报告生成异常，生成兜底报告

# 错误信息
❌ 流程执行失败：具体错误描述
```

### 调试技巧

1. **单步测试数据获取**：
```python
from data_fetchers import CailiansheFetcher
fetcher = CailiansheFetcher()
result = fetcher.safe_fetch()
print(result.to_dict())
```

2. **单步测试 Agent 分析**：
```python
from agents import MacroAgent
agent = MacroAgent(api_key="sk-xxx")
result = agent.safe_analyze(test_data)
print(result.output)
```

3. **单步测试 PDF 生成**：
```python
from utils.pdf_generator import PDFGenerator
generator = PDFGenerator()
pdf_path = generator.generate("# 测试报告\n内容...")
print(f"PDF 路径：{pdf_path}")
```

---

## 风险提示

### ⚠️ 投资风险

1. **非投资建议**：本报告由系统自动生成，仅供参考，不构成任何投资建议
2. **数据延迟**：公开数据存在采集延迟，可能影响分析时效性
3. **模型局限**：AI 分析基于历史数据和预设框架，无法预测突发事件
4. **独立判断**：投资决策应结合个人风险承受能力，独立判断

### ⚠️ 技术风险

1. **API 依赖**：系统依赖阿里云百炼、akshare 等外部服务，服务中断将影响运行
2. **数据准确性**：数据源错误可能导致分析偏差
3. **模型幻觉**：LLM 可能产生不符合事实的输出，需人工复核
4. **系统稳定性**：长时间运行可能积累内存占用，建议定期重启

### ⚠️ 合规风险

1. **数据使用**：请确保数据源使用符合相关服务条款
2. **信息传播**：报告分发需注意保密性和受众范围
3. **监管要求**：金融机构使用需符合内部合规要求

### ⚠️ 运维建议

1. **定期备份**：备份 `.env` 配置文件和生成的报告
2. **监控日志**：定期检查 `logs/` 目录，及时发现异常
3. **版本管理**：建议使用 git 管理代码变更
4. **权限控制**：API Key 等敏感信息需妥善保管，避免泄露

---

## 版本历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v2.0 | 2026-04 | 异步多智能体架构、PDF 生成、飞书推送 |
| v1.0 | - | 初始单一脚本版本 |

---

## 技术支持

- **问题反馈**：查看 `logs/` 目录日志获取详细错误信息
- **文档更新**：本 README 随代码同步更新
- **贡献指南**：欢迎提交 Issue 和 Pull Request

---

*最后更新：2026 年 04 月 09 日*