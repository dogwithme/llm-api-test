import pytest
import os
import requests
from jsonschema import validate
import allure
import json
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


# ==================== 全局配置与接口夹具 ====================
@pytest.fixture(scope="session")
def doubao_config():
    """豆包大模型接口+UI全局配置"""
    api_key = os.getenv("DOUBAO_API_KEY", "").strip()

    if not api_key:
        print("\n⚠️  未配置环境变量 DOUBAO_API_KEY，接口测试无法运行，UI测试不受影响")

    model_id = "ep-20260527211839-psk77"
    base_url = "https://ark.cn-beijing.volces.com/api/v3"
    debug_url = "https://console.volcengine.com/ark/region:ark+cn-beijing/experience/chat?modelId=ep-20260527211839-psk77&tab=Chat"

    return {
        "base_url": base_url,
        "api_key": api_key,
        "model": model_id,
        "debug_url": debug_url
    }


@pytest.fixture(scope="session")
def parse_stream_response():
    """解析流式输出响应"""

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
                        chunk = json.loads(data_str)
                        if 'choices' in chunk and len(chunk['choices']) > 0:
                            delta = chunk['choices'][0].get('delta', {})
                            if 'content' in delta:
                                full_content += delta['content']
                    except json.JSONDecodeError:
                        continue
        return full_content

    return _parse_stream


original_post = requests.post


@pytest.fixture(scope="session")
def patched_post():
    """自动修正大模型请求非法参数"""
    DEFAULT_TIMEOUT = (3, 15)

    def _patched_post(url, *args, **kwargs):
        timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)
        skip_patch = kwargs.pop("skip_patch", False)

        if "ark.cn-beijing.volces.com" in url and not skip_patch:
            if "json" in kwargs:
                data = kwargs["json"]
                if "max_tokens" in data:
                    data["max_tokens"] = max(1, min(4096, data["max_tokens"]))
                if "temperature" in data:
                    data["temperature"] = max(0.0, min(2.0, data["temperature"]))
                if "top_p" in data:
                    data["top_p"] = max(0.0, min(1.0, data["top_p"]))
                kwargs["json"] = data

        return original_post(url, *args, **kwargs)

    return _patched_post


@pytest.fixture(scope="session")
def validate_chat_response():
    """校验聊天接口响应格式"""
    chat_schema = {
        "type": "object",
        "required": ["id", "object", "created", "model", "choices", "usage"],
        "properties": {
            "id": {"type": "string"},
            "object": {"const": "chat.completion"},
            "created": {"integer"},
            "model": {"string"},
            "choices": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["index", "message", "finish_reason"],
                    "properties": {
                        "index": {"integer"},
                        "message": {
                            "type": "object",
                            "required": ["role", "content"],
                            "properties": {
                                "role": {"string"},
                                "content": {"string"}
                            }
                        },
                        "finish_reason": {"string"}
                    }
                }
            },
            "usage": {
                "type": "object",
                "required": ["prompt_tokens", "completion_tokens", "total_tokens"],
                "properties": {
                    "prompt_tokens": {"integer"},
                    "completion_tokens": {"integer"},
                    "total_tokens": {"integer"}
                }
            }
        }
    }

    def _validate(response_json):
        validate(instance=response_json, schema=chat_schema)

    return _validate


@pytest.fixture(scope="session", autouse=True)
def copy_environment_properties():
    """测试结束自动复制环境配置到报告"""
    yield
    source_file = "environment.properties"
    target_dir = "./reports"
    if os.path.exists(source_file):
        os.makedirs(target_dir, exist_ok=True)
        shutil.copy(source_file, os.path.join(target_dir, "environment.properties"))
        print(f"\n✅ 环境配置文件已自动复制到 {target_dir}")


# ==================== Selenium UI 夹具 ====================
@pytest.fixture(scope="session")
def chrome_driver():
    """全局只开1次浏览器"""
    options = Options()
    options.add_argument("--disable-features=RendererCodeIntegrity")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_experimental_option("detach", True)
    options.add_experimental_option("excludeSwitches", ["enable-automation","enable-logging"])
    options.add_experimental_option("useAutomationExtension",False)
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(2)
    yield driver
    driver.quit()


@pytest.fixture(scope="session")
def login_once(chrome_driver, doubao_config):
    """全局只打开一次页面"""
    driver = chrome_driver
    driver.get(doubao_config["debug_url"])
    yield driver


@pytest.fixture(scope="function")
def init_driver(login_once):
    """不刷新、不跳转、不重置页面"""
    driver = login_once
    # 【只加了这3行：每次用例前强制清理断网残留】
    driver.execute_script("""
    if(window.originalXMLHttpRequest) XMLHttpRequest = window.originalXMLHttpRequest;
    if(window.originalFetch) fetch = window.originalFetch;
    delete window.originalXMLHttpRequest;
    delete window.originalFetch;
    """)
    yield driver


# ==================== 自动截图 ====================
@pytest.fixture(autouse=True)
def screenshot_on_failure(request):
    yield
    if "chrome_driver" not in request.fixturenames:
        return
    driver = request.getfixturevalue("chrome_driver")
    if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
        with allure.step("测试失败自动截图"):
            allure.attach(
                driver.get_screenshot_as_png(),
                name="失败截图",
                attachment_type=allure.attachment_type.PNG
            )


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


def pytest_collection_modifyitems(config, items):
    # 1. 先给所有API用例标记为最高优先级
    for item in items:
        if "test_cases/api/" in item.nodeid:
            item.add_marker(pytest.mark.order(0))

    # 2. 给所有UI用例按原有的顺序标记
    order_map = {
        "test_ui_stream": 1,
        "test_ui_multi_turn": 2,
        "test_ui_error": 3
    }
    for item in items:
        for name, order in order_map.items():
            if name in item.nodeid:
                item.add_marker(pytest.mark.order(order))
                break