import allure
import requests
import pytest
import json
@allure.feature("已知限制和边界场景")
@allure.story("超过模型上下文窗口")
@pytest.mark.xfail(reason="已知问题：超过32k上下文窗口会返回错误")
def test_context_window_limit(doubao_config,validate_chat_response ,patched_post):
    """测试超过模型上下文窗口的输入"""
    url = f"{doubao_config['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {doubao_config['api_key']}",
        "Content-Type": "application/json"
    }
    #生成一个超长的输入
    long_text="你好"*20000
    data = {
        "model": doubao_config["model"],
        "messages": [{"role": "user", "content":long_text}]
    }
    response=patched_post(url,headers=headers,json=data)
    assert response.status_code==200
    response_json = response.json()
    validate_chat_response(response_json)
    allure.attach(json.dumps(data, ensure_ascii=False, indent=2), "请求体", allure.attachment_type.JSON)
    allure.attach(json.dumps(response_json, ensure_ascii=False, indent=2), "响应体", allure.attachment_type.JSON)

@allure.feature("已知限制和边界场景")
@allure.story("函数调用功能支持")
@pytest.mark.xfail(reason="已知限制：豆包32k不支持函数调用")
def test_function_call(doubao_config,validate_chat_response,patched_post):
    url = f"{doubao_config['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {doubao_config['api_key']}",
        "Content-Type": "application/json"
    }
    data={
        "model":doubao_config['model'],
        "messages":[{"role":"user","content":"今天北京的天气怎么样"}],
        "tools":[{
            "type":"function",
            "function":{
                "name":"get_weather",
                "description":"获取指定城市的天气",
                "parameters":{
                    "type":"object",
                    "properties":{
                        "city":{"type":"string","description":"城市名称"}
                    },
                    "required":["city"]
                }
            }
        }]
    }
    response=patched_post(url,headers=headers,json=data)
    assert response.status_code == 200
    response_json = response.json()
    validate_chat_response(response_json)
    allure.attach(json.dumps(data, ensure_ascii=False, indent=2), "请求体", allure.attachment_type.JSON)
    allure.attach(json.dumps(response_json, ensure_ascii=False, indent=2), "响应体", allure.attachment_type.JSON)
    assert "tool_calls" in response.json()['choices'][0]['message']


@allure.feature("已知限制和边界场景")
@allure.story("超长文本生成超时")
@pytest.mark.xfail(reason="性能优化中：生成超长文本会超时")
def test_long_generation_timeout(doubao_config,validate_chat_response,patched_post):
    """测试生成超长文本的超时情况"""
    url = f"{doubao_config['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {doubao_config['api_key']}",
        "Content-Type": "application/json"
    }

    data = {
        "model": doubao_config['model'],
        "messages": [{"role": "user", "content": "写一篇10000字的小说"}],
        "max_tokens": 4000
    }

    # 设置3秒超时，这个测试肯定会失败
    try:
        response = patched_post(url, headers=headers, json=data, timeout=3)
        assert response.status_code == 200
        response_json = response.json()
        validate_chat_response(response_json)
        allure.attach(json.dumps(data, ensure_ascii=False, indent=2), "请求体", allure.attachment_type.JSON)
        allure.attach(json.dumps(response_json, ensure_ascii=False, indent=2), "响应体", allure.attachment_type.JSON)
        pytest.fail("预期超时但接口成功返回")
    except requests.exceptions.Timeout:
        pass



