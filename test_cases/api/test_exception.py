import requests
import allure
import pytest

@pytest.mark.smoke
@allure.feature("异常场景测试")
@allure.story("无效API Key")
def test_chat_invalid_api_key(doubao_config,patched_post):
    url = f"{doubao_config['base_url']}/chat/completions"
    headers = {
        "Authorization": "Bearer invalid_key",
        "Content-Type": "application/json"
    }
    data = {
        "model": doubao_config['model'],
        "messages": [{"role": "user", "content": "你好"}]
    }
    response = patched_post(url, headers=headers, json=data,skip_patch=True)
    assert response.status_code == 401


@allure.feature("异常场景测试")
@allure.story("不存在的模型")
def test_chat_invalid_model(doubao_config,patched_post):
    url = f"{doubao_config['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {doubao_config['api_key']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "invalid-model-123456",
        "messages": [{"role": "user", "content": "你好"}]
    }
    response = patched_post(url, headers=headers, json=data,skip_patch=True)
    assert response.status_code == 404


@allure.feature("异常场景测试")
@allure.story("缺失必填参数")
@pytest.mark.parametrize("missing_param", [
    "model",
    "messages",
    "messages[0].content"
])
def test_missing_required_params(doubao_config, missing_param,patched_post):
    url = f"{doubao_config['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {doubao_config['api_key']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": doubao_config['model'],
        "messages": [{"role": "user", "content": "你好"}]
    }
    # 动态删除指定参数
    if missing_param == "model":
        del data["model"]
    elif missing_param == "messages":
        del data["messages"]
    elif missing_param == "messages[0].content":
        del data["messages"][0]["content"]

    response = patched_post(url, headers=headers, json=data,skip_patch=True)
    assert response.status_code == 400


@allure.feature("异常场景测试")
@allure.story("无效的角色")
def test_invalid_role(doubao_config,patched_post):
    url = f"{doubao_config['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {doubao_config['api_key']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": doubao_config['model'],
        "messages": [{"role": "invalid_role", "content": "你好"}]
    }
    response = patched_post(url, headers=headers, json=data,skip_patch=True)
    assert response.status_code == 400