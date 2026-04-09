"""
飞书推送模块（原生 API 版本 - 严格规范版）
支持获取 Token、上传文件、发送带附件的消息

严格按照飞书 OpenAPI 最新规范：
1. 上传文件：POST https://open.feishu.cn/open-apis/im/v1/files
2. 发送消息：POST https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional, Any
from datetime import datetime

import requests
from requests_toolbelt import MultipartEncoder

logger = logging.getLogger(__name__)

# 飞书 API 端点
FEISHU_API_BASE = "https://open.feishu.cn/open-apis"

# 请求超时
REQUEST_TIMEOUT = 30


class FeishuClient:
    """
    飞书客户端
    封装飞书原生 API 调用
    """

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        chat_id: str
    ):
        """
        初始化飞书客户端

        Args:
            app_id: 飞书应用 ID
            app_secret: 飞书应用密钥
            chat_id: 目标群聊 ID
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.chat_id = chat_id
        self._token: Optional[str] = None
        self._token_expire: int = 0

    async def get_tenant_access_token(self) -> str:
        """
        获取飞书 tenant_access_token

        Returns:
            str: access_token

        Raises:
            Exception: 获取失败时抛出异常
        """
        url = f"{FEISHU_API_BASE}/auth/v3/tenant_access_token/internal"

        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }

        headers = {"Content-Type": "application/json"}

        logger.info("=" * 50)
        logger.info("🔑 获取飞书 tenant_access_token")
        logger.info("=" * 50)
        logger.info(f"  URL: {url}")
        logger.info(f"  Headers: {json.dumps(headers, ensure_ascii=False)}")
        logger.info(f"  Payload: {json.dumps({'app_id': self.app_id, 'app_secret': '[已隐藏]'}, ensure_ascii=False)}")

        loop = asyncio.get_event_loop()

        def _request():
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )
            return response.status_code, response.text

        status, text = await loop.run_in_executor(None, _request)
        logger.info(f"  HTTP Status: {status}")
        logger.info(f"  Response: {text}")

        # 【严格校验】HTTP 状态码检查
        if status != 200:
            logger.error(f"  ❌ HTTP 错误：{status}")
            logger.error(f"  完整响应：{text}")
            raise Exception(f"获取飞书 token 失败 - HTTP 状态码：{status}, 响应：{text}")

        result = json.loads(text)

        # 【严格校验】API code 检查
        if result.get("code") != 0:
            error_msg = result.get("msg", "未知错误")
            logger.error(f"  ❌ API 错误：{error_msg}")
            logger.error(f"  完整响应：{json.dumps(result, ensure_ascii=False, indent=2)}")
            raise Exception(f"获取飞书 token 失败：{error_msg}")

        self._token = result.get("tenant_access_token")
        self._token_expire = result.get("expire", 0)

        logger.info(f"  ✅ Token 获取成功：{self._token[:20]}...")
        logger.info(f"  有效期：{self._token_expire} 秒")
        return self._token

    async def upload_file(self, file_path: str, file_name: Optional[str] = None) -> str:
        """
        上传文件到飞书（使用 im/v1/files 接口）

        严格按照飞书 API 规范：
        - URL: POST https://open.feishu.cn/open-apis/im/v1/files
        - Header: Authorization: Bearer <tenant_access_token>
        - Payload (multipart/form-data):
          - file_type: "stream"
          - file_name: "xxx.pdf"
          - file: 文件二进制流

        Args:
            file_path: 文件本地路径
            file_name: 上传后的文件名（可选）

        Returns:
            str: file_key

        Raises:
            Exception: 上传失败时抛出异常
        """
        if not self._token:
            await self.get_tenant_access_token()

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在：{file_path}")

        if file_name is None:
            file_name = file_path.name

        file_size = file_path.stat().st_size

        # 飞书文件上传接口
        url = f"{FEISHU_API_BASE}/im/v1/files"

        # 【严格规范】Header 只包含 Authorization
        headers = {
            "Authorization": f"Bearer {self._token}"
        }

        logger.info("=" * 50)
        logger.info("📤 上传文件到飞书（im/v1/files 接口）")
        logger.info("=" * 50)
        logger.info(f"  URL: {url}")
        logger.info(f"  Headers: Authorization: Bearer {self._token[:20]}...")
        logger.info(f"  File: {file_name} ({file_size/1024:.1f} KB)")

        loop = asyncio.get_event_loop()

        def _upload():
            with open(file_path, 'rb') as f:
                file_content = f.read()

            # 【严格规范】使用 MultipartEncoder 构建 multipart/form-data
            # 让 requests_toolbelt 自动生成正确的 Content-Type 和 boundary
            multipart_encoder = MultipartEncoder(
                fields={
                    "file_type": "stream",
                    "file_name": file_name,
                    "file": (file_name, file_content, "application/pdf")
                }
            )

            logger.info(f"  Form Data: file_type=stream, file_name={file_name}")
            logger.info(f"  File Content Size: {len(file_content)} bytes")

            # 【严格规范】将 multipart_encoder 的内容和 Content-Type 设置到 headers
            headers["Content-Type"] = multipart_encoder.content_type

            response = requests.post(
                url,
                headers=headers,
                data=multipart_encoder,
                timeout=120
            )
            return response.status_code, response.text

        status, text = await loop.run_in_executor(None, _upload)
        logger.info(f"  HTTP Status: {status}")
        logger.info(f"  Response: {text[:500] if len(text) > 500 else text}")

        # 【严格校验】HTTP 状态码检查
        if status != 200:
            logger.error(f"  ❌ HTTP 错误：{status}")
            logger.error(f"  完整响应：{text}")
            raise Exception(f"文件上传 HTTP 错误：{status}, 响应：{text}")

        result = json.loads(text)

        # 【严格校验】API code 检查
        if result.get("code") != 0:
            error_msg = result.get("msg", "未知错误")
            logger.error(f"  ❌ API 错误：{error_msg}")
            logger.error(f"  完整响应：{json.dumps(result, ensure_ascii=False, indent=2)}")
            raise Exception(f"文件上传失败：{error_msg}")

        file_key = result.get("data", {}).get("file_key")
        if not file_key:
            logger.error(f"  ❌ 未返回 file_key")
            logger.error(f"  完整响应：{json.dumps(result, ensure_ascii=False, indent=2)}")
            raise Exception("文件上传失败：未返回 file_key")

        logger.info(f"  ✅ 文件上传成功")
        logger.info(f"  file_key: {file_key}")
        return file_key

    async def send_file_message(
        self,
        file_key: str,
        file_name: str = "报告.pdf"
    ) -> dict:
        """
        发送文件类型消息

        严格按照飞书 API 规范：
        - URL: POST https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id
        - Header: Authorization: Bearer <tenant_access_token>
        - Payload (JSON):
          - receive_id: chat_id
          - msg_type: "file"
          - content: "{\"file_key\":\"<key>\"}" (JSON 序列化的字符串)

        Args:
            file_key: 文件 key
            file_name: 文件名

        Returns:
            dict: 发送结果
        """
        if not self._token:
            await self.get_tenant_access_token()

        url = f"{FEISHU_API_BASE}/im/v1/messages"

        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json"
        }

        # 【严格规范】query 参数必须包含 receive_id_type=chat_id
        params = {
            "receive_id_type": "chat_id"
        }

        # 【严格规范】content 必须是 JSON 序列化的字符串
        content_json = {
            "file_key": file_key
        }
        content_str = json.dumps(content_json)

        payload = {
            "receive_id": self.chat_id,
            "msg_type": "file",
            "content": content_str
        }

        logger.info("=" * 50)
        logger.info("📨 发送文件消息到飞书群聊")
        logger.info("=" * 50)
        logger.info(f"  URL: {url}")
        logger.info(f"  Params: {json.dumps(params, ensure_ascii=False)}")
        logger.info(f"  Headers: Authorization: Bearer {self._token[:20]}...")
        logger.info(f"  Payload: receive_id={self.chat_id}, msg_type=file, content={content_str}")

        loop = asyncio.get_event_loop()

        def _send():
            response = requests.post(
                url,
                headers=headers,
                params=params,
                json=payload,
                timeout=REQUEST_TIMEOUT
            )
            return response.status_code, response.text

        status, text = await loop.run_in_executor(None, _send)
        logger.info(f"  HTTP Status: {status}")
        logger.info(f"  Response: {text}")

        # 【严格校验】HTTP 状态码检查
        if status != 200:
            logger.error(f"  ❌ HTTP 错误：{status}")
            logger.error(f"  完整响应：{text}")
            raise Exception(f"文件消息发送 HTTP 错误：{status}, 响应：{text}")

        result = json.loads(text)

        # 【严格校验】API code 检查
        if result.get("code") != 0:
            error_msg = result.get("msg", "未知错误")
            logger.error(f"  ❌ API 错误：{error_msg}")
            logger.error(f"  完整响应：{json.dumps(result, ensure_ascii=False, indent=2)}")
            raise Exception(f"文件消息发送失败：{error_msg}")

        message_id = result.get("data", {}).get("message_id", "")
        logger.info(f"  ✅ 文件消息发送成功")
        logger.info(f"  message_id: {message_id}")

        return {
            "success": True,
            "message_id": message_id
        }

    async def send_card_message(
        self,
        title: str,
        content: str,
        file_key: Optional[str] = None
    ) -> dict:
        """
        发送卡片消息（可带附件）

        Args:
            title: 消息标题
            content: 消息内容（Markdown）
            file_key: 附件文件 key（可选）

        Returns:
            dict: 发送结果
        """
        # 确保有 token
        if not self._token:
            await self.get_tenant_access_token()

        url = f"{FEISHU_API_BASE}/im/v1/messages"

        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json"
        }

        # 构建富文本消息
        message_content = {
            "zh_cn": {
                "title": title,
                "content": [
                    [{"tag": "text", "text": content[:4000]}]
                ]
            }
        }

        # 如果有附件，添加附件
        if file_key:
            message_content["zh_cn"]["content"].append([
                {"tag": "attachment", "file_key": file_key}
            ])

        params = {
            "receive_id_type": "chat_id"
        }

        payload = {
            "receive_id": self.chat_id,
            "msg_type": "post",
            "content": json.dumps(message_content)
        }

        logger.info("=" * 50)
        logger.info("📨 发送卡片消息到飞书群聊")
        logger.info("=" * 50)
        logger.info(f"  URL: {url}")
        logger.info(f"  Params: {json.dumps(params, ensure_ascii=False)}")
        logger.info(f"  Headers: Authorization: Bearer {self._token[:20]}...")
        logger.info(f"  Payload: receive_id={self.chat_id}, msg_type=post")
        logger.info(f"  Content: {json.dumps(message_content, ensure_ascii=False, indent=2)[:500]}")

        loop = asyncio.get_event_loop()

        def _send():
            response = requests.post(
                url,
                headers=headers,
                params=params,
                json=payload,
                timeout=REQUEST_TIMEOUT
            )
            return response.status_code, response.text

        status, text = await loop.run_in_executor(None, _send)
        logger.info(f"  HTTP Status: {status}")
        logger.info(f"  Response: {text}")

        # 【严格校验】HTTP 状态码检查
        if status != 200:
            logger.error(f"  ❌ HTTP 错误：{status}")
            logger.error(f"  完整响应：{text}")
            raise Exception(f"卡片消息发送 HTTP 错误：{status}, 响应：{text}")

        result = json.loads(text)

        # 【严格校验】API code 检查
        if result.get("code") != 0:
            error_msg = result.get("msg", "未知错误")
            logger.error(f"  ❌ API 错误：{error_msg}")
            logger.error(f"  完整响应：{json.dumps(result, ensure_ascii=False, indent=2)}")
            raise Exception(f"卡片消息发送失败：{error_msg}")

        message_id = result.get("data", {}).get("message_id", "")
        logger.info(f"  ✅ 消息发送成功")
        logger.info(f"  message_id: {message_id}")

        return {
            "success": True,
            "message_id": message_id
        }

    async def send_report_with_attachment(
        self,
        pdf_path: str,
        summary: str = "今日宏观与 A 股主线推演报告已生成",
        title: str = "📅 股债双市每日跟踪报告"
    ) -> dict:
        """
        发送报告消息（含 PDF 附件）

        Args:
            pdf_path: PDF 文件路径
            summary: 摘要内容
            title: 消息标题

        Returns:
            dict: 发送结果
        """
        logger.info("\n" + "=" * 60)
        logger.info("📤 开始飞书推送流程")
        logger.info("=" * 60)
        logger.info(f"  PDF 文件：{pdf_path}")
        logger.info(f"  目标群聊：{self.chat_id}")

        try:
            # 1. 获取 token
            await self.get_tenant_access_token()

            # 2. 上传文件（使用严格规范的 im/v1/files 接口）
            logger.info("\n使用 im/v1/files 接口上传文件...")
            file_key = await self.upload_file(pdf_path)

            # 3. 发送文件消息
            result = await self.send_file_message(
                file_key=file_key,
                file_name=Path(pdf_path).name
            )

            # 4. 如果文件消息成功，再发送一条摘要消息
            if result.get("success"):
                logger.info("\n发送摘要消息...")
                await self.send_card_message(
                    title=title,
                    content=summary
                )

            logger.info("\n" + "=" * 60)
            logger.info("✅ 飞书推送流程完成")
            logger.info("=" * 60)

            return result

        except Exception as e:
            logger.error(f"\n❌ 飞书推送流程失败：{e}")
            logger.error(f"  错误类型：{type(e).__name__}")
            return {"success": False, "error": str(e)}


async def send_markdown_to_feishu(
    title: str,
    content: str
) -> dict:
    """
    发送 Markdown 消息到飞书（无附件）

    Args:
        title: 消息标题
        content: Markdown 内容

    Returns:
        dict: 发送结果
    """
    # 从环境变量读取配置
    app_id = os.environ.get('FEISHU_APP_ID')
    app_secret = os.environ.get('FEISHU_APP_SECRET')
    chat_id = os.environ.get('FEISHU_CHAT_ID')

    if not all([app_id, app_secret, chat_id]):
        return {"success": False, "error": "飞书配置不完整"}

    client = FeishuClient(
        app_id=app_id,
        app_secret=app_secret,
        chat_id=chat_id
    )

    try:
        # 获取 token
        await client.get_tenant_access_token()

        # 发送消息（无附件）
        result = await client.send_card_message(
            title=title,
            content=content,
            file_key=None
        )

        return result

    except Exception as e:
        return {"success": False, "error": str(e)}


async def send_report_to_feishu(
    pdf_path: str,
    summary: str = "今日宏观与 A 股主线推演报告已生成",
    title: str = "📅 股债双市每日跟踪报告"
) -> dict:
    """
    发送报告到飞书的便捷函数

    Args:
        pdf_path: PDF 文件路径
        summary: 摘要内容
        title: 消息标题

    Returns:
        dict: 发送结果
    """
    # 从环境变量读取配置
    app_id = os.environ.get('FEISHU_APP_ID')
    app_secret = os.environ.get('FEISHU_APP_SECRET')
    chat_id = os.environ.get('FEISHU_CHAT_ID')

    # 检查配置
    if not all([app_id, app_secret, chat_id]):
        logger.warning("⚠️ 飞书配置不完整，跳过推送")
        logger.info("  请配置以下环境变量:")
        logger.info("  - FEISHU_APP_ID")
        logger.info("  - FEISHU_APP_SECRET")
        logger.info("  - FEISHU_CHAT_ID")
        return {"success": False, "error": "飞书配置不完整"}

    client = FeishuClient(
        app_id=app_id,
        app_secret=app_secret,
        chat_id=chat_id
    )

    return await client.send_report_with_attachment(
        pdf_path=pdf_path,
        summary=summary,
        title=title
    )


# 同步版本（兼容旧调用）
def send_to_feishu(
    title: str,
    markdown_content: str,
    webhook_url: str,
    **kwargs
) -> dict:
    """
    兼容旧接口的同步版本（使用 Webhook）
    """
    logger.warning("使用旧版 Webhook 接口，建议升级为原生 API")

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue"
            },
            "elements": [
                {"tag": "markdown", "content": markdown_content}
            ]
        }
    }

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=REQUEST_TIMEOUT
        )
        result = response.json()

        if result.get("StatusCode") == 0 or result.get("code") == 0:
            return {"success": True}
        else:
            return {"success": False, "error": result.get("msg")}

    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == '__main__':
    # 测试飞书 API 连接
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s'
    )

    app_id = os.environ.get('FEISHU_APP_ID')
    app_secret = os.environ.get('FEISHU_APP_SECRET')
    chat_id = os.environ.get('FEISHU_CHAT_ID')

    if not all([app_id, app_secret, chat_id]):
        print("❌ 请在 .env 中配置飞书相关变量:")
        print("   FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_CHAT_ID")
        sys.exit(1)

    async def test():
        client = FeishuClient(app_id, app_secret, chat_id)

        # 测试获取 token
        token = await client.get_tenant_access_token()
        print(f"\n✅ Token 获取成功：{token[:20]}...")

        # 测试发送消息（无附件）
        result = await client.send_card_message(
            title="🧪 测试消息",
            content="这是一条测试消息，验证飞书 API 连接正常。"
        )

        if result.get("success"):
            print("\n✅ 消息发送成功!")
        else:
            print(f"\n❌ 消息发送失败：{result.get('error')}")

    asyncio.run(test())
