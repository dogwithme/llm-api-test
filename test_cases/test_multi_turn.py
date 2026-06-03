import requests
import allure
import pytest
import json
@pytest.mark.smoke
@allure.feature("核心聊天接口")
@allure.story("多轮对话上下文")
def test_chat_multi_turn(doubao_config, validate_chat_response,patched_post):
    url = f"{doubao_config['base_url']}/chat/completions"
    headers={
        "Authorization":f"Bearer {doubao_config['api_key']}",
        "Content-Type":"application/json"
    }
    #第一轮对话
    messages=[{"role":"user","content":"9+9等于几"}]
    data1={"model":doubao_config['model'],"messages":messages}
    response=patched_post(url,headers=headers,json=data1)
    assert response.status_code==200
    response_json1 = response.json()
    validate_chat_response(response_json1)
    # 第一轮的附件
    allure.attach(json.dumps(data1, ensure_ascii=False, indent=2), "第一轮请求", allure.attachment_type.JSON)
    allure.attach(json.dumps(response_json1, ensure_ascii=False, indent=2), "第一轮响应", allure.attachment_type.JSON)
    #把模型的回答加入上下文
    assistant_reply=response.json()['choices'][0]['message']['content']
    messages.append({"role":"assistant","content":assistant_reply})
    #第二轮对话
    messages.append({"role":"user","content":"再乘以二等于几"})
    data2={"model":doubao_config['model'],"messages":messages}
    response=patched_post(url,headers=headers,json=data2)
    assert response.status_code==200
    response_json2 = response.json()
    validate_chat_response(response_json2)
    # 第二轮的附件
    allure.attach(json.dumps(data2, ensure_ascii=False, indent=2), "第二轮请求", allure.attachment_type.JSON)
    allure.attach(json.dumps(response_json2, ensure_ascii=False, indent=2), "第二轮响应", allure.attachment_type.JSON)
    assert "36" in response.json()['choices'][0]['message']['content']

