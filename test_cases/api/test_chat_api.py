import allure
import requests
import pytest
import json

@pytest.mark.smoke
@allure.feature("核心聊天接口")
@allure.story("正常单轮对话")
def test_chat_normal(doubao_config, validate_chat_response,patched_post):
    url=f"{doubao_config['base_url']}/chat/completions"
    headers={
        "Authorization":f"Bearer {doubao_config['api_key']}",
        "Content-Type":"application/json"
    }
    data = {
        "model": doubao_config['model'],
        "messages": [{"role": "user", "content": "8+8等于多少"}]
    }
    response=patched_post(url,headers=headers,json=data)
    assert response.status_code==200
    response_json = response.json()
    validate_chat_response(response_json)
    # 添加请求体附件
    allure.attach(json.dumps(data, ensure_ascii=False, indent=2), "请求体", allure.attachment_type.JSON)
    # 添加响应体附件
    allure.attach(json.dumps(response_json, ensure_ascii=False, indent=2), "响应体", allure.attachment_type.JSON)
    print(response.status_code)
    print(response.json())

@pytest.mark.smoke
@allure.feature("核心聊天接口")
@allure.story("多输入场景关键词校验")
@pytest.mark.parametrize("question, expected_keyword", [
    ("北京的天气怎么样", "北京"),
    ("Python是什么", "Python"),
    ("1+1等于几", "2")
])
def test_chat_multiple_inputs(doubao_config, question, expected_keyword,validate_chat_response,patched_post):
    url = f"{doubao_config['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {doubao_config['api_key']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": doubao_config['model'],
        "messages": [{"role": "user", "content": question}]
    }
    response = patched_post(url, headers=headers, json=data)
    assert response.status_code == 200
    response_json = response.json()
    validate_chat_response(response_json)
    # 添加请求体附件
    allure.attach(json.dumps(data, ensure_ascii=False, indent=2), "请求体", allure.attachment_type.JSON)
    # 添加响应体附件
    allure.attach(json.dumps(response_json, ensure_ascii=False, indent=2), "响应体", allure.attachment_type.JSON)
    content = response.json()["choices"][0]["message"]["content"]
    assert expected_keyword in content and len(content) > 10

@pytest.mark.smoke
@allure.feature("核心聊天接口")
@allure.story("流式输出测试")
def test_chat_stream(doubao_config, parse_stream_response,patched_post):
    """测试基础流式输出功能"""
    url = f"{doubao_config['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {doubao_config['api_key']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": doubao_config['model'],
        "messages": [{"role": "user", "content": "简单介绍一下自己"}],
        "stream": True
    }
    response = patched_post(url, headers=headers, json=data, stream=True)
    assert response.status_code == 200
    full_content = parse_stream_response(response)
    assert len(full_content) > 0

@pytest.mark.smoke
@allure.feature("模型管理接口")
@allure.story("获取可用模型列表")
def test_list_models(doubao_config):
    url = f"{doubao_config['base_url']}/models"
    headers = {
        "Authorization": f"Bearer {doubao_config['api_key']}"
    }
    response = requests.get(url, headers=headers)
    assert response.status_code == 200
    assert "data" in response.json()
