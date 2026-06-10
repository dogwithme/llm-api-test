import pytest
import os    #与操作系统交互，获取环境变量、文件路径等
import requests
from jsonschema import validate   #用于验证聊天接口返回的json数据是否符合预期的结构和格式
import allure
import json   #对JSON数据进行编码和解码
import shutil    #用于在测试结束后将 environment.properties 文件复制到 ./reports 目录。
from selenium import webdriver    #用来启动浏览器、进行UI自动化测试
from selenium.webdriver.chrome.options import Options    #设置浏览器的启动参数，例如禁用 GPU、禁用沙盒模式、禁用后台渲染等，这些配置可以优化浏览器的运行环境，避免一些兼容性问题，同时满足测试的需求。


# ==================== 全局配置与接口夹具 ====================
@pytest.fixture(scope="session")
def doubao_config():
    """豆包大模型接口+UI全局配置"""
    api_key = os.getenv("DOUBAO_API_KEY", "").strip()    # strip() 的作用是确保从环境变量 DOUBAO_API_KEY 获取的值在首尾没有多余的空格或换行符，避免因意外的空格导致后续逻辑出错。

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
    def _parse_stream(response):
        full_content = ""
        for line in response.iter_lines():    #逐行读取流式数据，iter_lines() 方法会自动处理分块传输和数据流的边界，确保每次迭代返回完整的一行数据。
            if line:
                line = line.decode('utf-8')
                if line.startswith('data:'):
                    data_str = line[6:].strip()
                    if data_str == '[DONE]':
                        break                   # 如果行内容为 [DONE]，表示流式响应结束，直接退出循环。
                    try:
                        chunk = json.loads(data_str)
                        if 'choices' in chunk and len(chunk['choices']) > 0:
                            delta = chunk['choices'][0].get('delta', {})
                            if 'content' in delta:
                                full_content += delta['content']    #将每个数据块中的 content 字段累加到 full_content 变量中，最终得到完整的响应内容。
                    except json.JSONDecodeError:
                        continue           #捕获异常并跳过非JSON格式的行，继续处理下一行数据。
        return full_content

    return _parse_stream    #将解析流式响应的逻辑封装在一个函数中，并通过 pytest 的 fixture 机制提供给测试用例使用，使得测试代码更加简洁和可复用。

original_post = requests.post


@pytest.fixture(scope="session")
def patched_post():
    """自动修正大模型请求非法参数"""
    DEFAULT_TIMEOUT = (3, 15)    #设置默认的连接超时和读取超时，连接超时为3秒，读取超时为15秒，这样可以避免请求长时间挂起，提高测试的稳定性和效率。

    def _patched_post(url, *args, **kwargs):    #主要用于在发送 HTTP POST 请求时自动修正某些参数
        timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)
        skip_patch = kwargs.pop("skip_patch", False)    #pop 的作用是从字典中安全地获取值，同时移除该键，避免后续逻辑重复使用。如果键不存在，可以通过提供默认值避免抛出异常。

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
    chat_schema = {
        "type": "object",
        "required": ["id", "object", "created", "model", "choices", "usage"],
        "properties": {
            "id": {"type": "string"},
            "object": {"type": "string"},
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

    def _validate(resp):
        validate(instance=resp, schema=chat_schema)    #验证 resp 是否符合 chat_schema 定义的结构和规则。如果验证失败，会抛出 jsonschema.exceptions.ValidationError 异常。

    return _validate


@pytest.fixture(scope="session", autouse=True)    #autouse=True：表示该夹具会自动应用到所有测试用例，无需显式调用
def copy_environment_properties():
    """测试结束自动复制环境配置到报告"""
    yield
    source_file = "environment.properties"
    target_dir = "./reports"
    if os.path.exists(source_file):
        os.makedirs(target_dir, exist_ok=True)
        shutil.copy(source_file, os.path.join(target_dir, "environment.properties"))    #使用 shutil.copy 将源文件复制到目标目录，并命名为 environment.properties。
        print(f"\n✅ 环境配置文件已自动复制到 {target_dir}")


# ==================== Selenium UI 夹具 ====================
@pytest.fixture(scope="session")
def chrome_driver():
    options = Options()
    options.add_argument("--disable-features=RendererCodeIntegrity")    #禁用某些渲染器功能，避免兼容性问题
    options.add_argument("--no-sandbox")    #禁用沙盒模式，提升运行效率（适用于无头模式或受限环境）
    options.add_argument("--disable-dev-shm-usage")    #禁用 /dev/shm 使用，避免资源限制问题
    options.add_argument("--disable-gpu")    #禁用 GPU 加速，避免在无头模式下运行时的 GPU 相关问题
    options.add_argument("--disable-renderer-backgrounding")    #禁用后台渲染器，确保测试过程中页面始终保持活跃状态
    options.add_argument("--disable-background-timer-throttling")    #禁用后台定时器，确保测试过程中页面始终保持活跃状态
    options.add_argument("--disable-backgrounding-occluded-windows")    #禁用被遮挡窗口的后台处理，确保测试过程中页面始终保持活跃状态
    options.add_experimental_option("detach", True)    #保持浏览器在测试结束后仍然打开，方便调试和查看测试结果
    options.add_experimental_option("excludeSwitches", ["enable-automation","enable-logging"])    #隐藏自动化控制提示和日志，提供更干净的测试环境
    options.add_experimental_option("useAutomationExtension",False)    #禁用自动化扩展，避免在无头模式下运行时的自动化检测问题
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(2)
    yield driver    #将浏览器实例提供给测试用例使用，测试结束后会自动执行后续代码关闭浏览器
    driver.quit()


@pytest.fixture(scope="session")
def login_once(chrome_driver, doubao_config):
    #全局只打开一次页面
    driver = chrome_driver
    driver.get(doubao_config["debug_url"])
    yield driver


@pytest.fixture(scope="function")
def init_driver(login_once):
    driver = login_once
    # 确保页面的网络请求行为不受干扰，恢复到默认状态，以便测试用例能够正常运行
    driver.execute_script("""    
    if(window.originalXMLHttpRequest) XMLHttpRequest = window.originalXMLHttpRequest;    #如果之前被测试用例修改过 XMLHttpRequest 对象，就恢复原始的 XMLHttpRequest 对象，确保后续测试用例能够正常使用网络请求功能。
    if(window.originalFetch) fetch = window.originalFetch;    #如果之前被测试用例修改过 fetch 函数，就恢复原始的 fetch 函数，确保后续测试用例能够正常使用网络请求功能。
    delete window.originalXMLHttpRequest;    #删除之前保存的原始 XMLHttpRequest 对象的引用，释放内存并避免潜在的冲突。
    delete window.originalFetch;    #删除之前保存的原始 fetch 函数的引用，释放内存并避免潜在的冲突。
    """)
    yield driver


# ==================== 自动截图 ====================
@pytest.fixture(autouse=True)
def screenshot_on_failure(request):
    yield
    if "chrome_driver" not in request.fixturenames:
        return
    driver = request.getfixturevalue("chrome_driver")    #获取当前测试用例使用的 chrome_driver 夹具实例，如果当前测试用例没有使用 chrome_driver 夹具，则直接返回，不执行截图逻辑。
    if hasattr(request.node, "rep_call") and request.node.rep_call.failed:    #检查当前测试用例的执行结果，如果测试用例在执行过程中发生了失败（即 rep_call.failed 为 True），则执行截图逻辑。
        with allure.step("测试失败自动截图"):
            allure.attach(
                driver.get_screenshot_as_png(),
                name="失败截图",
                attachment_type=allure.attachment_type.PNG
            )


#为测试用例的不同阶段（如 setup、call、teardown）生成对应的报告。 （为自动截图功能提供测试报告对象）
@pytest.hookimpl(tryfirst=True, hookwrapper=True)    #表示这个钩子函数会优先于其他同类钩子函数执行；表示这个钩子函数是一个包装器，允许在钩子执行前后插入逻辑。
def pytest_runtest_makereport(item, call):
    outcome = yield    #暂停当前函数的执行，等待 pytest 的默认实现完成后继续
    report = outcome.get_result()    #获取测试用例的执行结果（pytest 生成的测试报告对象）
    setattr(item, f"rep_{report.when}", report)    #将测试报告对象存储到测试用例对象 item 中。report.when 表示测试阶段（setup、call 或 teardown）。例如，rep_call 表示测试用例的执行阶段报告。


def pytest_collection_modifyitems(config, items):
    # 1. 先给所有API用例标记为最高优先级
    for item in items:
        if "test_cases/api/" in item.nodeid:
            item.add_marker(pytest.mark.order(0))

    # 2. 给所有UI用例标记执行顺序
    order_map = {
        "test_ui_stream": 1,
        "test_ui_multi_turn": 2,
        "test_ui_error": 3
    }
    for item in items:
        for name, order in order_map.items():
            if name in item.nodeid:    #item.nodeid 是测试用例的唯一标识，通常包含文件路径和测试函数名，如果测试用例的标识中包含指定的 name，就给该测试用例添加对应的执行顺序标记。pytest.mark.order(order) 是 pytest-ordering 插件提供的功能，用于指定测试用例的执行顺序，order 参数越小，优先级越高。
                item.add_marker(pytest.mark.order(order))
                break