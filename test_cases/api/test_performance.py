import allure
import requests
import pytest
from requests.exceptions import Timeout
import json
@pytest.mark.xfail(reason="火山方舟API响应速度不稳定，偶尔会超时")
@pytest.mark.parametrize("request_content,timeout_seconds,test_desc",[
    ("你好",10,"简单问候请求—超时测试"),
    ("什么是软件测试",30,"中等复杂度请求-超时测试"),
    ("写一篇200字的软件测试面试经验",60,"复杂文本生成请求-超时测试")
])
@allure.feature("接口性能测试")
@allure.story("响应超时测试")
def test_chat_timeout(doubao_config,request_content,timeout_seconds,test_desc,validate_chat_response,patched_post):
    """测试接口超时"""
    url = f"{doubao_config['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {doubao_config['api_key']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": doubao_config['model'],
        "messages": [{"role": "user", "content":request_content}],
        "max_tokens":100
    }

    try:
        response = patched_post(url, headers=headers, json=data,timeout=timeout_seconds)
        assert response.status_code == 200,f"{test_desc}:接口返回非200状态码"
        response_json = response.json()
        validate_chat_response(response_json)
        allure.attach(json.dumps(data, ensure_ascii=False, indent=2), "请求体", allure.attachment_type.JSON)
        allure.attach(json.dumps(response_json, ensure_ascii=False, indent=2), "响应体", allure.attachment_type.JSON)
        response_time = response.elapsed.total_seconds()
        print(f"\n{test_desc}：实际响应时间 = {response_time:.2f}秒（阈值={timeout_seconds}秒）")
    except Timeout:
        pytest.fail(f"{test_desc}:接口响应超时（超过{timeout_seconds}秒）")

from concurrent.futures import  ThreadPoolExecutor
@allure.feature("接口性能测试")
@allure.story("多用户并发请求")
def test_concurrent_requests(doubao_config,patched_post):
    """测试10个并发请求"""
    url = f"{doubao_config['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {doubao_config['api_key']}",
        "Content-Type": "application/json"
    }
    def make_request():
        data={
            "model": doubao_config['model'],
            "messages": [{"role": "user", "content": "你好"}]
        }
        response=patched_post(url,headers=headers,json=data)
        return response.status_code
        # 10个并发请求
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request) for _ in range(10)]
        results = [future.result() for future in futures]
        # 断言所有请求都成功
    assert all(status == 200 for status in results)
