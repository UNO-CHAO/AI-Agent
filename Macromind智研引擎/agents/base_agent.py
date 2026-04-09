"""
智能体基类
定义统一的 Agent 接口和基础 Pydantic 模型
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional, Type, TypeVar

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

# 加载环境变量
ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(ENV_PATH)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 泛型类型变量
T = TypeVar('T', bound=BaseModel)


class AgentResult(BaseModel):
    """
    Agent 执行结果的标准封装
    """
    success: bool = Field(description="执行是否成功")
    agent_name: str = Field(description="Agent 名称")
    output: Optional[BaseModel] = Field(default=None, description="结构化输出")
    error: Optional[str] = Field(default=None, description="错误信息")
    raw_response: Optional[str] = Field(default=None, description="LLM 原始响应")
    timestamp: str = Field(default_factory=lambda: __import__('time').strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> dict:
        """转换为字典格式"""
        result = {
            'success': self.success,
            'agent_name': self.agent_name,
            'error': self.error,
            'timestamp': self.timestamp
        }
        if self.output:
            result['output'] = self.output.model_dump()
        if self.raw_response:
            result['raw_response'] = self.raw_response
        return result


class BullBearFactor(BaseModel):
    """
    多空因子模型
    """
    factor_name: str = Field(description="因子名称/事件名称")
    description: str = Field(description="因子描述/具体内容")
    impact_level: str = Field(description="影响等级: 高/中/低")
    affected_assets: list[str] = Field(default_factory=list, description="受影响的资产类别")
    reasoning: str = Field(description="分析逻辑/原因")


class BaseAgent(ABC):
    """
    智能体基类
    所有专业分析师 Agent 都应继承此类
    """

    def __init__(
        self,
        agent_name: str,
        role_description: str,
        model: str = "qwen-plus",
        api_key: Optional[str] = None
    ):
        """
        初始化 Agent

        Args:
            agent_name: Agent 名称
            role_description: Agent 角色描述
            model: 使用的模型名称
            api_key: API Key，如未提供则从环境变量读取
        """
        self.agent_name = agent_name
        self.role_description = role_description
        self.model = model
        self.logger = logging.getLogger(f"agents.{agent_name}")

        # 获取 API Key
        self.api_key = api_key or os.environ.get('DASHSCOPE_API_KEY')
        if not self.api_key:
            raise ValueError("未找到 DASHSCOPE_API_KEY，请检查环境变量或 .env 文件")

        # 初始化 OpenAI 客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        获取系统提示词
        子类必须实现，定义 Agent 的专业角色和分析框架
        """
        pass

    @abstractmethod
    def get_output_model(self) -> Type[BaseModel]:
        """
        获取输出数据的 Pydantic 模型类
        子类必须实现，定义结构化输出的格式
        """
        pass

    @abstractmethod
    def format_input(self, data: Any) -> str:
        """
        格式化输入数据为文本
        子类必须实现，将原始数据转换为 LLM 可理解的格式
        """
        pass

    def analyze(self, data: Any) -> AgentResult:
        """
        执行分析任务

        Args:
            data: 输入数据

        Returns:
            AgentResult: 包含结构化输出的结果对象
        """
        self.logger.info(f"[{self.agent_name}] 开始分析任务...")

        try:
            # 格式化输入
            input_text = self.format_input(data)

            # 调用 LLM
            response = self._call_llm(input_text)

            # 解析结构化输出
            output = self._parse_response(response)

            self.logger.info(f"[{self.agent_name}] 分析完成")

            return AgentResult(
                success=True,
                agent_name=self.agent_name,
                output=output,
                raw_response=response
            )

        except Exception as e:
            self.logger.error(f"[{self.agent_name}] 分析失败: {e}")
            return AgentResult(
                success=False,
                agent_name=self.agent_name,
                error=str(e)
            )

    def _call_llm(self, input_text: str) -> str:
        """
        调用 LLM API

        Args:
            input_text: 格式化后的输入文本

        Returns:
            str: LLM 响应文本
        """
        system_prompt = self.get_system_prompt()
        output_model = self.get_output_model()

        # 构建提示，要求返回 JSON 格式
        full_system_prompt = f"""{system_prompt}

## 输出格式要求
你必须严格按照以下 JSON Schema 格式输出，不要输出任何其他内容：
```json
{json.dumps(output_model.model_json_schema(), ensure_ascii=False, indent=2)}
```

重要提醒：
1. 只输出符合上述 Schema 的 JSON 对象
2. 不要输出任何解释、说明或额外的文字
3. 确保 JSON 格式完整且可解析
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": full_system_prompt},
                {"role": "user", "content": input_text}
            ],
            temperature=0.3  # 降低温度以提高输出稳定性
        )

        return response.choices[0].message.content

    def _parse_response(self, response: str) -> BaseModel:
        """
        解析 LLM 响应为结构化数据

        Args:
            response: LLM 响应文本

        Returns:
            BaseModel: Pydantic 模型实例
        """
        output_model = self.get_output_model()

        # 清理响应文本（移除可能的 markdown 代码块标记）
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()

        # 解析 JSON
        try:
            data = json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON 解析失败，尝试修复: {e}")
            # 尝试更激进地清理
            cleaned_response = self._repair_json(cleaned_response)
            data = json.loads(cleaned_response)

        # 创建 Pydantic 模型
        return output_model.model_validate(data)

    def _repair_json(self, text: str) -> str:
        """
        尝试修复损坏的 JSON 文本
        """
        # 移除控制字符
        import re
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)

        # 尝试找到 JSON 对象的边界
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            text = text[start:end + 1]

        return text

    def safe_analyze(self, data: Any) -> AgentResult:
        """
        安全分析：捕获所有异常，确保返回结果对象

        Args:
            data: 输入数据

        Returns:
            AgentResult: 始终返回结果对象，不会抛出异常
        """
        try:
            return self.analyze(data)
        except Exception as e:
            self.logger.error(f"[{self.agent_name}] 安全分析失败: {e}")
            return AgentResult(
                success=False,
                agent_name=self.agent_name,
                error=str(e)
            )