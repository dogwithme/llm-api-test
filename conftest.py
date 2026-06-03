import pytest
import os
import requests
from jsonschema import validate
import allure
import json
import shutil
@pytest.fixture(scope="session")
def doubao_config():
    """
    豆包大模型接口配置
    从系统环境变量读取 API Key，安全不泄露
    """
    api_key = os.getenv("DOUBAO_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError("❌ 请先配置系统环境变量 DOUBAO_API_KEY")

    return {
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "api_key": api_key,
        "model": "ep-20260527211839-psk77"
    }
# 在doubao_config函数后面添加这个
@pytest.fixture(scope="session")
def parse_stream_response():
    """公共函数：解析流式输出响应，返回完整内容"""
    def _parse_stream(response):
        full_content = ""
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data:'):
                    data_str = line[6:].strip()
                    if data_str == '[DONE]':
                        break
                    try:
                        import json
                        chunk = json.loads(data_str)
                        if 'choices' in chunk and len(chunk['choices']) > 0:
                            delta = chunk['choices'][0].get('delta', {})
                            if 'content' in delta:
                                full_content += delta['content']
                    except json.JSONDecodeError:
                        continue
        return full_content
    return _parse_stream
# 保存原始的 requests.post 方法
original_post = requests.post

# ==================== 自动修正所有参数的补丁 ====================
@pytest.fixture(scope="session")
def patched_post():
    """自动修正所有大模型请求的非法参数，修复官方bug和400错误"""
    # 全局默认超时：连接3秒，读取15秒（行业标准值）
    DEFAULT_TIMEOUT = (3, 15)
    def _patched_post(url, *args, **kwargs):
        # 如果调用时传了timeout，就用传的；否则用默认值
        timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)
        # 新增开关：测试非法参数时传 skip_patch=True 即可绕过修正
        skip_patch = kwargs.pop("skip_patch", False)

        # 只处理火山方舟的接口请求，且不跳过补丁
        if "ark.cn-beijing.volces.com" in url and not skip_patch:
            if "json" in kwargs:
                data = kwargs["json"]

                # 1. 修正 max_tokens 非法值（官方不报错但会忽略）
                if "max_tokens" in data:
                    if data["max_tokens"] < 1:
                        data["max_tokens"] = 1
                    elif data["max_tokens"] > 4096:
                        data["max_tokens"] = 4096

                # 2. 修正 temperature 非法值（官方会返回400）
                if "temperature" in data:
                    if data["temperature"] < 0.0:
                        data["temperature"] = 0.0
                    elif data["temperature"] > 2.0:
                        data["temperature"] = 2.0

                # 3. 修正 top_p 非法值（官方会返回400）
                if "top_p" in data:
                    if data["top_p"] < 0.0:
                        data["top_p"] = 0.0
                    elif data["top_p"] > 1.0:
                        data["top_p"] = 1.0

                # 把修改后的数据放回请求
                kwargs["json"] = data

        # 调用原始的 post 方法发送请求
        return original_post(url, *args, **kwargs)

    return _patched_post

@pytest.fixture(scope="session")
def validate_chat_response():
    """公共函数：校验聊天接口响应格式符合OpenAI规范"""
    chat_schema = {
        "type": "object",
        "required": ["id", "object", "created", "model", "choices", "usage"],
        "properties": {
            "id": {"type": "string"},
            "object": {"const": "chat.completion"},
            "created": {"type": "integer"},
            "model": {"type": "string"},
            "choices": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["index", "message", "finish_reason"],
                    "properties": {
                        "index": {"type": "integer"},
                        "message": {
                            "type": "object",
                            "required": ["role", "content"],
                            "properties": {
                                "role": {"type": "string"},
                                "content": {"type": "string"}
                            }
                        },
                        "finish_reason": {"type": "string"}
                    }
                }
            },
            "usage": {
                "type": "object",
                "required": ["prompt_tokens", "completion_tokens", "total_tokens"],
                "properties": {
                    "prompt_tokens": {"type": "integer"},
                    "completion_tokens": {"type": "integer"},
                    "total_tokens": {"type": "integer"}
                }
            }
        }
    }

    def _validate(response_json):
        validate(instance=response_json, schema=chat_schema)

    return _validate


@pytest.fixture(scope="session", autouse=True)
def copy_environment_properties():
    """测试结束后自动复制环境配置文件到Allure报告目录"""
    yield  # 先执行所有测试
    source_file = "environment.properties"
    target_dir = "./reports"

    if os.path.exists(source_file):
        # 自动创建目标文件夹，即使不存在
        os.makedirs(target_dir, exist_ok=True)
        shutil.copy(source_file, os.path.join(target_dir, "environment.properties"))
        print(f"\n✅ 环境配置文件已自动复制到 {target_dir}")