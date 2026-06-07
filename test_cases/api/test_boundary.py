import requests
import pytest
import allure
import json


def estimate_token_count(text):
    return int(len(text) * 1.3)


# ==================== max_tokens边界测试 ====================
@pytest.mark.parametrize("max_tokens, expected_type, expected_status", [
    (100, "normal", 200),  # 正常合法值
    (2048, "max", 200),    # 合法上限
    (-100, "invalid_low", 400),
    (10000, "invalid_high", 200) # 非法超上限：服务端自动修正为4096
])
@allure.feature("参数边界测试")
@allure.story("参数边界值测试 - max_tokens")
def test_max_tokens_boundary(doubao_config, max_tokens, expected_type, expected_status, validate_chat_response,
                             patched_post):
    url = f"{doubao_config['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {doubao_config['api_key']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": doubao_config["model"],
        "messages": [{"role": "user", "content": "写一句关于春天的话"}],
        "max_tokens": max_tokens
    }

    skip_patch = expected_type != "normal"
    response = patched_post(url, headers=headers, json=data, skip_patch=skip_patch)

    assert response.status_code == expected_status, f"预期状态码{expected_status}，实际{response.status_code}"

    if expected_status == 200:
        response_json = response.json()
        validate_chat_response(response_json)

        content = response_json['choices'][0]['message']['content']
        estimated_tokens = estimate_token_count(content)

        if expected_type == "normal":
            assert estimated_tokens <= max_tokens * 1.1, f"正常值{max_tokens}限制失效"
        elif expected_type == "max":
            assert estimated_tokens <= 2048 * 1.1, f"上限值2048限制失效"
        elif expected_type == "invalid_low":
            assert estimated_tokens <= 4096 * 1.1, f"负值未自动修正"
        elif expected_type == "invalid_high":
            assert estimated_tokens <= 4096 * 1.1, f"非法超上限{max_tokens}未自动修正"

# ==================== temperature边界测试 ====================
@pytest.mark.parametrize("temperature, expect_same, expected_status", [
    (0.0, True, 200),  # 合法最小值
    (1.0, False, 200), # 合法中间值
    (2.0, False, 200), # 合法最大值
    (-0.1, False, 400),# 非法负值：返回400
    (2.1, False, 400)  # 非法超上限：返回400
])
@pytest.mark.smoke
@allure.feature("参数边界测试")
@allure.story("参数边界值测试 - temperature")
def test_temperature_boundary(doubao_config, temperature, expect_same, expected_status, validate_chat_response, patched_post):
    url = f"{doubao_config['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {doubao_config['api_key']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": doubao_config['model'],
        "messages": [{"role": "user", "content": "输出：2"}],
        "temperature": temperature
    }
    skip_patch = temperature < 0.0 or temperature > 2.0

    results = []
    # 恢复2次循环，验证多次结果一致
    for i in range(2):
        response = patched_post(url, headers=headers, json=data, skip_patch=skip_patch)
        assert response.status_code == expected_status, f"预期状态码{expected_status}，实际{response.status_code}"

        if expected_status == 200:
            response_json = response.json()
            validate_chat_response(response_json)
            content = response_json["choices"][0]["message"]["content"].strip()
            results.append(content)  # 每次循环都添加结果

    # 只有0.0需要断言结果一致
    if expect_same and expected_status == 200:
        assert len(set(results)) == 1

# ==================== top_p边界测试 ====================
@pytest.mark.parametrize("top_p, expect_same, expected_status", [
    (0.0, True, 200),  # 合法最小值
    (0.5, False, 200), # 合法中间值
    (1.0, False, 200), # 合法最大值
    (-0.1, False, 400),# 非法负值：返回400
    (1.1, False, 400)  # 非法超上限：返回400
])
@allure.feature("参数边界测试")
@allure.story("参数边界值测试 - top_p")
def test_top_p_boundary(doubao_config, top_p, expect_same, expected_status, validate_chat_response, patched_post):
    url = f"{doubao_config['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {doubao_config['api_key']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": doubao_config['model'],
        "messages": [{"role": "user", "content": "输出：4"}],
        "top_p": top_p,
        "temperature": 1.0
    }
    skip_patch = top_p < 0.0 or top_p > 1.0

    results = []
    for i in range(2):
        response = patched_post(url, headers=headers, json=data, skip_patch=skip_patch)
        assert response.status_code == expected_status, f"预期状态码{expected_status}，实际{response.status_code}"

        if expected_status == 200:
            response_json = response.json()
            validate_chat_response(response_json)
            content = response_json["choices"][0]["message"]["content"].strip()
            results.append(content)

    if expect_same and expected_status == 200:
        assert len(set(results)) == 1
# ==================== 组合场景测试 ====================
@allure.feature("参数边界测试")
@allure.story("流式输出 + max_tokens 参数校验")
def test_max_tokens_with_stream(doubao_config, parse_stream_response, patched_post):
    url = f"{doubao_config['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {doubao_config['api_key']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": doubao_config["model"],
        "messages": [{"role": "user", "content": "写一篇短文"}],
        "max_tokens": 10,
        "stream": True
    }
    response = patched_post(url, headers=headers, json=data, stream=True)
    assert response.status_code == 200
    full_content = parse_stream_response(response)
    assert len(full_content) <= 40, "流式输出时max_tokens失效"

# ==================== stop停止词参数测试 ====================
@allure.feature("参数边界测试")
@allure.story("stop 停止词参数")
def test_stop_parameter(doubao_config, validate_chat_response, patched_post):
    url = f"{doubao_config['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {doubao_config['api_key']}",
        "Content-Type": "application/json"
    }
    stop_word = "###STOP###"
    data = {
        "model": doubao_config["model"],
        "messages": [
            {"role": "user", "content": f"写一句描写春天的话，看到{stop_word}就立刻停止"}],
        "stop": [stop_word],
        "max_tokens": 100
    }
    response = patched_post(url, headers=headers, json=data)
    assert response.status_code == 200
    response_json = response.json()
    validate_chat_response(response_json)

    allure.attach(json.dumps(data, ensure_ascii=False, indent=2), "请求体", allure.attachment_type.JSON)
    allure.attach(json.dumps(response_json, ensure_ascii=False, indent=2), "响应体", allure.attachment_type.JSON)

    content = response_json['choices'][0]['message']['content']
    assert stop_word not in content
    assert len(content) > 0