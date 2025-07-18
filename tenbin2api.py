from chatbridge.chatbridge import *
from curl_cffi import requests
from fastapi import FastAPI
from dotenv import load_dotenv
import json
import os

import uvicorn
import websocket

load_dotenv()
app = FastAPI(title="retool2api")
session_id = os.getenv(
    "session_id",
    "",
)
if session_id == "":
    raise ValueError("session_id is not set in the environment variables.")
print(f"Session ID: {session_id}")


@app.get("/v1/models")
@get_model_list
def get_models():
    model_ids = []
    url = "https://graphql.tenbin.ai/graphql"

    payload = {
        "operationName": "MeForChatUsages",
        "variables": {},
        "query": "query MeForChatUsages {\n  me {\n    chatUsages: todayChatUsages {\n      modelGroup\n      models {\n        model\n        credit\n        __typename\n      }\n      totalChatCount\n      consumptionChatCount\n      remainingChatCount\n      __typename\n    }\n    __typename\n  }\n}",
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Content-Type": "application/json",
        "sec-ch-ua-platform": '"Windows"',
        "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        "sec-ch-ua-mobile": "?0",
        "origin": "https://tenbin.ai",
        "sec-fetch-site": "same-site",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "referer": "https://tenbin.ai/",
        "accept-language": "zh-CN,zh;q=0.9",
        "priority": "u=1, i",
        "Cookie": f"sessionId={session_id}",
    }

    response = requests.post(url, data=json.dumps(payload), headers=headers)

    print(response.text)
    model_list = response.json().get("data", {}).get("me", {}).get("chatUsages", [])
    for model in model_list:
        model_group = model.get("modelGroup", "")
        models = model.get("models", [])
        for model_name in models:
            model_id = model_name.get("model", "")
            if model_id:
                model_ids.append((model_id, model_group))
    return model_ids


def getTaskId():

    url = "http://192.168.0.207:5000/turnstile?url=https://tenbin.ai/workspace&sitekey=0x4AAAAAABGR2exxRproizri&action=issue_execution_token"

    response = requests.get(url)
    response.raise_for_status()
    return response.json()["task_id"]


def getCaptcha(task_id):

    url = f"http://192.168.0.207:5000/result?id={task_id}"

    while True:
        try:
            response = requests.get(url)
            response.raise_for_status()
            captcha = response.json().get("value", "")
            if captcha:
                return captcha
            else:
                time.sleep(1)
        except Exception as e:
            print(e)
            time.sleep(1)


def get_execute_token(captcha: str = None, model_name: str = None):
    url = "https://graphql.tenbin.ai/graphql"

    payload = {
        "operationName": "IssueExecutionTokensMultiple",
        "variables": {
            "turnstileToken": f"{captcha}",
            "models": [model_name],
        },
        "query": "query IssueExecutionTokensMultiple($turnstileToken: String!, $models: [ChatModel!]!) {\n  executionTokens: issueExecutionTokensMultiple(\n    turnstileToken: $turnstileToken\n    models: $models\n  )\n}",
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Content-Type": "application/json",
        "sec-ch-ua-platform": '"Windows"',
        "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        "sec-ch-ua-mobile": "?0",
        "origin": "https://tenbin.ai",
        "sec-fetch-site": "same-site",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "referer": "https://tenbin.ai/",
        "accept-language": "zh-CN,zh;q=0.9",
        "priority": "u=1, i",
        "Cookie": f"sessionId={session_id}",
    }

    response = requests.post(url, data=json.dumps(payload), headers=headers)

    return response.json().get("data", {}).get("executionTokens", [])


def create_history():
    url = "https://graphql.tenbin.ai/graphql"

    payload = {
        "operationName": "createWorkspaceSessionHistory",
        "variables": {
            "stateTokens": [
                "ada8b16914eb18b2e9210523abff9a673d425193b3270b3796aa3742e0f6e03219ddf512539f11113e3e16d4b760da5d7902a886e5af3e9173d211f0fe6640ad9c7235d82360cdd337bd1d264174b6bf2420e4ee4fe90d17d687e6f2381704a18dada23ad5f3bbbf90052e1acd15e43225b63fcba8efc182a3798d4c34b53fe5c1ef867be6e874fc2aecbea87152d2b608bd4f42fc754987ae49df9f9dcc58894907f69d1a4e4cd968432cf3e629ed25f675fb248dc87687106f5e8c65902c21439b0536cd2cbdea9420d4fa29254cabd3c321fcd564e753d2bd6f68fa04ae989078796d0ab715360aacbd24475403cc4277e033932bc9c198169ff65a29183929c60e283ead187c6b817bb63ad48463c9b03504d61e5b1dc14618e1943b3b0e-5b7a97f94d53ce6dab164a38d3020437"
            ]
        },
        "query": "mutation createWorkspaceSessionHistory($stateTokens: [String!]!) {\n  createWorkspaceSessionHistory(stateTokens: $stateTokens) {\n    id\n    title\n    userId\n    createdAt\n    workspaceSessionHistoryMessages {\n      ...WorkspaceSessionHistoryMessageFragment\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment WorkspaceSessionHistoryMessageFragment on WorkspaceSessionHistoryMessage {\n  id\n  model\n  stateToken\n  createdAt\n  updatedAt\n  aiConversation {\n    id\n    model\n    variableConfigs {\n      id\n      name\n      value\n      __typename\n    }\n    messages {\n      id\n      role\n      itemId\n      content\n      fileUrls\n      webSearchResults {\n        id\n        title\n        url\n        faviconUrl\n        summary\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  __typename\n}",
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Content-Type": "application/json",
        "sec-ch-ua-platform": '"Windows"',
        "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        "sec-ch-ua-mobile": "?0",
        "origin": "https://tenbin.ai",
        "sec-fetch-site": "same-site",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "referer": "https://tenbin.ai/",
        "accept-language": "zh-CN,zh;q=0.9",
        "priority": "u=1, i",
        "Cookie": f"sessionId={session_id}",
    }

    response = requests.post(url, data=json.dumps(payload), headers=headers)

    # print(response.text)
    return (
        response.json()
        .get("data", {})
        .get("createWorkspaceSessionHistory", {})
        .get("id", "")
    )


def del_history(id: str):
    url = "https://graphql.tenbin.ai/graphql"

    payload = {
        "operationName": "deleteWorkspaceSessionHistory",
        "variables": {"workspaceSessionHistoryId": id},
        "query": "mutation deleteWorkspaceSessionHistory($workspaceSessionHistoryId: String!) {\n  deleteWorkspaceSessionHistory(\n    workspaceSessionHistoryId: $workspaceSessionHistoryId\n  )\n}",
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Content-Type": "application/json",
        "sec-ch-ua-platform": '"Windows"',
        "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        "sec-ch-ua-mobile": "?0",
        "origin": "https://tenbin.ai",
        "sec-fetch-site": "same-site",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "referer": "https://tenbin.ai/",
        "accept-language": "zh-CN,zh;q=0.9",
        "priority": "u=1, i",
        "Cookie": f"sessionId={session_id}",
    }

    response = requests.post(url, data=json.dumps(payload), headers=headers)

    print(response.text)


def get_history_id_list():

    url = "https://graphql.tenbin.ai/graphql"

    payload = {
        "operationName": "MeForWorkspace",
        "variables": {},
        "query": "query MeForWorkspace {\n  me {\n    workspaceSessionHistories(limit: 1000) {\n      id\n      title\n      userId\n      createdAt\n      updatedAt\n      workspaceSessionHistoryMessages {\n        ...WorkspaceSessionHistoryMessageFragment\n        __typename\n      }\n      __typename\n    }\n    workspaceUserAISet(setType: FAVORITE) {\n      id\n      userId\n      config {\n        id\n        models\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment WorkspaceSessionHistoryMessageFragment on WorkspaceSessionHistoryMessage {\n  id\n  model\n  stateToken\n  createdAt\n  updatedAt\n  aiConversation {\n    id\n    model\n    variableConfigs {\n      id\n      name\n      value\n      __typename\n    }\n    messages {\n      id\n      role\n      itemId\n      content\n      fileUrls\n      webSearchResults {\n        id\n        title\n        url\n        faviconUrl\n        summary\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  __typename\n}",
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Content-Type": "application/json",
        "sec-ch-ua-platform": '"Windows"',
        "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        "sec-ch-ua-mobile": "?0",
        "origin": "https://tenbin.ai",
        "sec-fetch-site": "same-site",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "referer": "https://tenbin.ai/",
        "accept-language": "zh-CN,zh;q=0.9",
        "priority": "u=1, i",
        "Cookie": f"sessionId={session_id}",
    }

    response = requests.post(url, data=json.dumps(payload), headers=headers)
    history_list = (
        response.json()
        .get("data", {})
        .get("me", {})
        .get("workspaceSessionHistories", [])
    )
    history_ids = []
    for history in history_list:
        history_id = history.get("id", "")
        if history_id:
            history_ids.append(history_id)
    return history_ids


@app.post("/v1/chat/completions")
@chatCompletions(1)
def tenbin(prompt: str, model, new_session: bool = True):
    print(f"Prompt: {prompt}, Model: {model}, New Session: {new_session}")
    task_id = getTaskId()
    captcha = getCaptcha(task_id)
    execution_token = get_execute_token(captcha, model)
    print(execution_token)
    url = "wss://graphql.tenbin.ai/graphql"
    if len(execution_token) == 0 or execution_token is None:
        print("Failed to get execution token.")
        return
    execution_token = execution_token[0]
    headers = {
        "Host": "graphql.tenbin.ai",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Connection": "Upgrade",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
        "Upgrade": "websocket",
        "Origin": "https://tenbin.ai",
        "Sec-WebSocket-Version": "13",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Sec-WebSocket-Key": "j69v2Cji3YAr5YZ31inBew==",
        "Sec-WebSocket-Extensions": "permessage-deflate; client_max_window_bits",
        "Sec-WebSocket-Protocol": "graphql-transport-ws",
        "Cookie": f"sessionId={session_id}",
    }

    ws = websocket.create_connection(url, header=headers)
    ws.send(json.dumps({"type": "connection_init"}))
    ws.recv()
    data = {
        "id": "d4b0b72a-5b87-4027-b370-a52d4fe55ca4",
        "type": "subscribe",
        "payload": {
            "variables": {
                "prompt": f"{prompt}",
                "executionToken": f"{execution_token}",
                "stateToken": "",
            },
            "extensions": {},
            "operationName": "StartConversation",
            "query": "subscription StartConversation($executionToken: String!, $itemId: String, $itemDraftId: String, $systemPrompt: String, $prompt: String, $stateToken: String, $variables: [ConversationVariableInput!], $itemCallOption: ItemCallOption, $fileKey: String, $fileUploadIds: [String!], $selectedToolsByUser: [ToolType!]) {\n  startConversation(\n    executionToken: $executionToken\n    itemId: $itemId\n    itemDraftId: $itemDraftId\n    systemPrompt: $systemPrompt\n    prompt: $prompt\n    stateToken: $stateToken\n    variables: $variables\n    itemCallOption: $itemCallOption\n    fileKey: $fileKey\n    fileUploadIds: $fileUploadIds\n    selectedToolsByUser: $selectedToolsByUser\n  ) {\n    ...DeltaConversation\n    __typename\n  }\n}\n\nfragment DeltaConversation on AIConversationStreamResult {\n  seq\n  deltaToken\n  isFinished\n  newStateToken\n  error\n  fileUploadIds\n  toolResult {\n    id\n    title\n    url\n    faviconUrl\n    summary\n    __typename\n  }\n  action\n  activity\n  toolError\n  __typename\n}",
        },
    }
    ws.send(json.dumps(data))
    ret_content = ""
    while True:
        content = ws.recv()
        json_content = json.loads(content)
        if json_content.get("type", "") == "complete":
            break
        content = (
            json_content.get("payload", {})
            .get("data", {})
            .get("startConversation", {})
            .get("deltaToken", "")
        )
        ret_content += content
    print(ret_content)
    return ret_content


def main():
    uvicorn.run("tenbin2api:app", host="0.0.0.0", port=10005, reload=True)


if __name__ == "__main__":
    hisory_list = get_history_id_list()
    for history_id in hisory_list:
        del_history(history_id)
    main()
