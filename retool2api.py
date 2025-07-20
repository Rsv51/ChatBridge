from curl_cffi import requests
from chatbridge.chatbridge import *
from dotenv import load_dotenv
from fastapi import FastAPI
from bs4 import BeautifulSoup

import os
import uvicorn
import json
import time

load_dotenv()
app = FastAPI(title="retool2api")
chat_id = 0
access_token = os.getenv("accessToken")
x_xsrf_token = os.getenv("x_xsrf_token")
url_header = os.getenv("url_header")
if not access_token or not x_xsrf_token or not url_header:
    raise ValueError(
        "accessToken, x_xsrf_token, or url_header is not set in the environment variables."
    )


def get_agent_id():
    url = "https://googlexxxx.retool.com/api/agents"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "x-xsrf-token": f"{x_xsrf_token}",
        "accept-language": "zh-CN,zh;q=0.9",
        "Cookie": f"accessToken={access_token}",
    }

    response = requests.get(url, headers=headers, impersonate="chrome")
    json_res = response.json()
    agent_list = json_res.get("agents", [])
    return agent_list[0].get("id", "") if agent_list else None


agent_id = get_agent_id()


@app.post("/v1/chat/completions")
@chatCompletions(1)
def retool(prompt: str, res: ChatResponse, new_session: bool):
    global chat_id
    print(new_session, chat_id)
    set_model(model=res.model)
    if new_session:
        chat_id = 0
    if chat_id != 0:
        return retool2(chat_id, prompt)
    url = f"{url_header}/api/agents/{agent_id}/threads"
    print(url)
    payload = {"name": f"tool use", "timezone": "Asia/Shanghai"}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Content-Type": "application/json",
        "x-xsrf-token": f"{x_xsrf_token}",
        "accept-language": "zh-CN,zh;q=0.9",
        "Cookie": f"accessToken={access_token}",
    }

    response = requests.post(url, data=json.dumps(payload), headers=headers)
    json_res = response.json()
    chat_id = json_res.get("id")
    print(f"Chat ID: {chat_id}")
    if chat_id == None:
        return {"error": f"{response.text}"}
    print(prompt)
    return retool2(chat_id, prompt)


def retool2(id, prompt: str):
    url = f"{url_header}/api/agents/{agent_id}/threads/{id}/messages"

    payload = {"type": "text", "text": prompt, "timezone": "Asia/Shanghai"}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Content-Type": "application/json",
        "x-xsrf-token": f"{x_xsrf_token}",
        "accept-language": "zh-CN,zh;q=0.9",
        "Cookie": f"accessToken={access_token}",
    }

    response = requests.post(url, data=json.dumps(payload), headers=headers)
    json_res = response.json()
    run_id = json_res.get("content", {}).get("runId")
    print(f"Run ID: {run_id}")
    return retool3(run_id)


def should_continue(url, headers):
    # 等待一段时间以确保请求完成
    index = 0
    while index < 10:  # 尝试十次
        index += 1
        print(f"Checking status... Attempt {index}")
        time.sleep(2)
        res = requests.get(url, headers=headers)
        json_res = res.json()
        if json_res.get("status") == "COMPLETED":
            print("Log completed.")
            return json_res


def retool3(id):
    url = f"{url_header}/api/agents/{agent_id}/logs/{id}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Content-Type": "application/json",
        "x-xsrf-token": f"{x_xsrf_token}",
        "accept-language": "zh-CN,zh;q=0.9",
        "Cookie": f"accessToken={access_token}",
    }
    json_res = should_continue(url, headers)
    if json_res == None:
        return {"error": "Log not completed or not found."}
    trace = json_res.get("trace", [])
    if not trace:
        print("No trace found in the response.")
        return
    if (
        trace[-1].get("reason", "") == "finished"
        and trace[-1].get("spanType", "") == "AGENT_END"
    ):
        response = trace[-1].get("data", {}).get("data", {}).get("content", "")
        return response


@app.get("/v1/models")
@get_model_list
def get_models():
    model_ids = [
        ("gpt-4o", "openAI"),
        ("o3", "anthropic"),
        ("o3-mini", "anthropic"),
        ("gpt-4.1", "openAI"),
        ("gpt-4.1-mini", "openAI"),
        ("gpt-4o-mini", "openAI"),
        ("claude-opus-4-20250514", "anthropic"),
        ("claude-sonnect-4-20250514", "anthropic"),
        ("claude-3-5-haiku-20241022", "anthropic"),
        ("deepseek-v3", "ossProvider"),
    ]
    return model_ids


def set_model(model: str):
    provider = ""
    if model.startswith("gpt-") or model.startswith("o3"):
        provider = "openAI"
    elif model.startswith("claude-"):
        provider = "anthropic"
    elif model.startswith("deepseek-"):
        provider = "ossProvider"
    print(provider, model)
    url = f"{url_header}/api/workflow/{agent_id}"
    payload = {
        "newWorkflowData": {
            "id": "d2443c4c-02cd-4dfb-b090-0c89b4aab158",
            "saveId": "d34d2da0-1de2-4acd-a641-34ccc7229a1d",
            "name": "test",
            "apiKey": "retool_wk_48442e2440fb4aa89fa2dc713ca733f5",
            "description": "",
            "organizationId": 1154899,
            "isEnabled": False,
            "crontab": None,
            "timezone": "Asia/Shanghai",
            "blockData": [
                {
                    "top": 48,
                    "left": 48,
                    "uuid": "f5192d1b-4892-4248-82b7-dee4a75dac11",
                    "options": {},
                    "pluginId": "startTrigger",
                    "blockType": "webhook",
                    "editorType": "JavascriptQuery",
                    "environment": "production",
                    "isMinimized": False,
                    "resourceName": "webhook",
                    "incomingOnSuccessEdges": [],
                },
                {
                    "top": 48,
                    "left": 480,
                    "uuid": "39bd2c48-8c2e-4765-8f87-0c288599f906",
                    "pluginId": "aiAgentExecute1",
                    "blockType": "aiAgentExecute",
                    "editorType": "JavascriptQuery",
                    "environment": "production",
                    "isMinimized": False,
                    "resourceName": "RetoolAIAgentExecuteQuery",
                    "incomingPorts": [],
                    "incomingOnSuccessEdges": ["f5192d1b-4892-4248-82b7-dee4a75dac11"],
                },
            ],
            "templateData": '["~#iR",["^ ","n","appTemplate","v",["^ ","appMaxWidth","100%","appStyles","","appTesting",null,"appThemeId",null,"appThemeModeId",null,"appThemeName",null,"createdAt",null,"customComponentCollections",[],"customDocumentTitle","","customDocumentTitleEnabled",false,"customShortcuts",[],"experimentalDataTabEnabled",false,"experimentalFeatures",["^ ","disableMultiplayerEditing",false,"multiplayerEditingEnabled",false,"sourceControlTemplateDehydration",false],"folders",["~#iL",[]],"formAppSettings",["^ ","customRedirectUrl",""],"inAppRetoolPillAppearance","NO_OVERRIDE","instrumentationEnabled",false,"internationalizationSettings",["^ ","internationalizationEnabled",false,"internationalizationFiles",[]],"isFetching",false,"isFormApp",false,"isGlobalWidget",false,"isMobileApp",false,"loadingIndicatorsDisabled",false,"markdownLinkBehavior","auto","mobileAppSettings",["^ ","displaySetting",["^ ","landscapeMode",false,"tabletMode",false],"mobileOfflineModeBannerMode","default","mobileOfflineModeDelaySync",false,"mobileOfflineModeEnabled",false],"mobileOfflineAssets",[],"multiScreenMobileApp",false,"notificationsSettings",["^ ","globalQueryShowFailureToast",true,"globalQueryShowSuccessToast",false,"globalQueryToastDuration",4.5,"globalToastPosition","bottomRight"],"pageCodeFolders",["^ "],"pageLoadValueOverrides",["^B",[]],"persistUrlParams",false,"plugins",["~#iOM",["startTrigger",["^0",["^ ","n","pluginTemplate","v",["^ ","id","startTrigger","uuid",null,"comment",null,"type","datasource","subtype","JavascriptQuery","namespace",null,"resourceName","JavascriptQuery","resourceDisplayName",null,"template",["~#iM",["queryRefreshTime","","allowedGroupIds",["^B",[]],"streamResponse",false,"lastReceivedFromResourceAt",null,"isFunction",false,"functionParameters",null,"queryDisabledMessage","","servedFromCache",false,"offlineUserQueryInputs","","functionDescription",null,"successMessage","","queryDisabled","","playgroundQuerySaveId","latest","workflowParams",null,"resourceNameOverride","","runWhenModelUpdates",false,"workflowRunExecutionType","sync","showFailureToaster",true,"query","return null","playgroundQueryUuid","","playgroundQueryId",null,"error",null,"workflowRunBodyType","raw","privateParams",["^B",[]],"queryRunOnSelectorUpdate",false,"runWhenPageLoadsDelay","","data",null,"importedQueryInputs",["^1?",[]],"_additionalScope",["^B",[]],"isImported",false,"showSuccessToaster",true,"cacheKeyTtl","","requestSentTimestamp",null,"metadata",null,"queryRunTime",null,"changesetObject","","offlineOptimisticResponse",null,"errorTransformer","return data.error","finished",null,"confirmationMessage",null,"isFetching",false,"changeset","","rawData",null,"queryTriggerDelay","0","resourceTypeOverride",null,"watchedParams",["^B",[]],"enableErrorTransformer",false,"showLatestVersionUpdatedWarning",false,"timestamp",0,"evalType","script","importedQueryDefaults",["^1?",[]],"enableTransformer",false,"showUpdateSetValueDynamicallyToggle",true,"overrideOrgCacheForUserCache",false,"runWhenPageLoads",false,"transformer","return data","events",["^B",[]],"queryTimeout","100000","workflowId",null,"requireConfirmation",false,"queryFailureConditions","","changesetIsObject",false,"enableCaching",false,"allowedGroups",["^B",[]],"offlineQueryType","None","queryThrottleTime","750","updateSetValueDynamically",false,"notificationDuration",""]],"style",null,"position2",null,"mobilePosition2",null,"mobileAppPosition",null,"tabIndex",null,"container","","^7","~m1752662537424","updatedAt","~m1752662537424","folder","","presetName",null,"screen",null,"boxId",null,"subBoxIds",null]]],"aiAgentExecute1",["^0",["^ ","n","pluginTemplate","v",["^ ","id","aiAgentExecute1","^17",null,"^18",null,"^19","datasource","^1:","JavascriptQuery","^1;",null,"^1<","RetoolAIAgentExecuteQuery","^1=",null,"^1>",["^1?",["queryRefreshTime","","allowedGroupIds",["^B",[]],"streamResponse",false,"lastReceivedFromResourceAt",null,"isFunction",false,"functionParameters",null,"queryDisabledMessage","","servedFromCache",false,"offlineUserQueryInputs","","functionDescription",null,"successMessage","","queryDisabled","","instructions","You are a helpful assistant chatting with { current_user.firstName } { current_user.lastName }. Their email is { current_user.email }, and the date is { new Date() }.","playgroundQuerySaveId","latest","workflowParams",null,"resourceNameOverride","","runWhenModelUpdates",false,"workflowRunExecutionType","sync","showFailureToaster",true,"query","","playgroundQueryUuid","","playgroundQueryId",null,"error",null,"workflowRunBodyType","raw","privateParams",["^B",[]],"model","{model}","queryRunOnSelectorUpdate",false,"runWhenPageLoadsDelay","","data",null,"providerId","retoolAIBuiltIn::{provider}","importedQueryInputs",["^1?",[]],"_additionalScope",["^B",[]],"isImported",false,"showSuccessToaster",true,"cacheKeyTtl","","requestSentTimestamp",null,"metadata",null,"queryRunTime",null,"changesetObject","","offlineOptimisticResponse",null,"errorTransformer","return data.error","finished",null,"confirmationMessage",null,"isFetching",false,"changeset","","drafts",[],"rawData",null,"queryTriggerDelay","0","resourceTypeOverride",null,"watchedParams",["^B",[]],"temperature",0.00,"enableErrorTransformer",false,"showLatestVersionUpdatedWarning",false,"timestamp",0,"mcpServers",[],"importedQueryDefaults",["^1?",[]],"enableTransformer",false,"showUpdateSetValueDynamicallyToggle",true,"overrideOrgCacheForUserCache",false,"runWhenPageLoads",false,"transformer","return data","events",["^B",[]],"queryTimeout","100000","workflowId",null,"maxIterations",11,"requireConfirmation",false,"queryFailureConditions","","tools",[],"changesetIsObject",false,"providerName","{provider}","enableCaching",false,"allowedGroups",["^B",[]],"offlineQueryType","None","queryThrottleTime","750","updateSetValueDynamically",false,"notificationDuration",""]],"^1@",null,"^1A",null,"^1B",null,"^1C",null,"^1D",null,"^1E","","^7","~m1752662537424","^1F","~m1752678921915","^1G","","^1H",null,"^1I",null,"^1J",null,"^1K",null]]]]],"preloadedAppJavaScript",null,"preloadedAppJSLinks",[],"queryStatusVisibility",false,"responsiveLayoutDisabled",false,"rootScreen",null,"savePlatform","web","shortlink",null,"testEntities",[],"tests",[],"urlFragmentDefinitions",["^B",[]],"version","3.237.0","serializedLayout",null,"agentEvals",["^ "]]]]',
            "triggerWebhooks": [
                {
                    "uuid": "startTrigger",
                    "name": "startTrigger",
                    "inputSchema": {"properties": []},
                    "useHeaderApiKey": False,
                    "exampleInputJSON": "",
                    "headers": "{}",
                    "examplePathParams": "",
                }
            ],
            "releaseId": "2f5321f2-6043-443c-a58c-33e79c2147d2",
            "customLibraries": [
                {
                    "version": "4.17.21",
                    "language": "javascript",
                    "variable": "_",
                    "codeString": "/* Edit library variable below */\n\nconst _ = require('lodash')\n\n/* Add destructured imports from library below\neg. const { pow, log } = require(\"mathjs\") */\n",
                    "libraryName": "lodash",
                },
                {
                    "version": "2.1.0",
                    "language": "javascript",
                    "variable": "numbro",
                    "codeString": "/* Edit library variable below */\n\nconst numbro = require('numbro')\n\n/* Add destructured imports from library below\neg. const { pow, log } = require(\"mathjs\") */\n",
                    "libraryName": "numbro",
                },
                {
                    "version": "5.3.2",
                    "language": "javascript",
                    "variable": "Papa",
                    "codeString": "/* Edit library variable below */\n\nconst Papa = require('papaparse')\n\n/* Add destructured imports from library below\neg. const { pow, log } = require(\"mathjs\") */\n",
                    "libraryName": "papaparse",
                },
                {
                    "version": "0.5.23",
                    "language": "javascript",
                    "variable": "moment",
                    "codeString": "/* Edit library variable below */\n\nconst moment = require('moment-timezone')\n\n/* Add destructured imports from library below\neg. const { pow, log } = require(\"mathjs\") */\n",
                    "libraryName": "moment-timezone",
                },
                {
                    "version": "3.4.0",
                    "language": "javascript",
                    "variable": "uuid",
                    "codeString": "/* Edit library variable below */\n\nconst uuid = require('uuid')\n\n/* Add destructured imports from library below\neg. const { pow, log } = require(\"mathjs\") */\n",
                    "libraryName": "uuid",
                },
            ],
            "createdAt": "2025-07-16T15:14:45.849Z",
            "updatedAt": "2025-07-16T15:14:45.849Z",
            "createdBy": 1793219,
            "folderId": 7690296,
            "protected": False,
            "javascriptLanguageConfigurationSaveId": None,
            "pythonLanguageConfigurationSaveId": None,
            "setupScripts": {
                "python": {"codeString": ""},
                "javascript": {
                    "codeString": "// lodash\n/* Edit library variable below */\n\nconst _ = require('lodash')\n\n/* Add destructured imports from library below\neg. const { pow, log } = require(\"mathjs\") */\n\n// numbro\n/* Edit library variable below */\n\nconst numbro = require('numbro')\n\n/* Add destructured imports from library below\neg. const { pow, log } = require(\"mathjs\") */\n\n// papaparse\n/* Edit library variable below */\n\nconst Papa = require('papaparse')\n\n/* Add destructured imports from library below\neg. const { pow, log } = require(\"mathjs\") */\n\n// moment-timezone\n/* Edit library variable below */\n\nconst moment = require('moment-timezone')\n\n/* Add destructured imports from library below\neg. const { pow, log } = require(\"mathjs\") */\n\n// uuid\n/* Edit library variable below */\n\nconst uuid = require('uuid')\n\n/* Add destructured imports from library below\neg. const { pow, log } = require(\"mathjs\") */\n"
                },
            },
            "subflows": [],
            "type": "agent",
            "iconName": "CircleDashedDuotone",
            "iconColor": "gray",
            "hasProtectedTriggers": False,
            "protectedTriggers": [],
            "accessLevel": "own",
        }
    }
    payload_str = json.dumps(payload)
    payload_str = payload_str.replace("{model}", model).replace("{provider}", provider)
    payload = json.loads(payload_str)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Content-Type": "application/json",
        "x-xsrf-token": f"{x_xsrf_token}",
        "accept-language": "zh-CN,zh;q=0.9",
        "Cookie": f"accessToken={access_token}",
    }

    response = requests.post(
        url, data=json.dumps(payload), headers=headers, impersonate="chrome"
    )


def get_thread_id():
    thread_id_list = []
    url = f"{url_header}/api/agents/{agent_id}/threads"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Content-Type": "application/json",
        "x-xsrf-token": f"{x_xsrf_token}",
        "accept-language": "zh-CN,zh;q=0.9",
        "Cookie": f"accessToken={access_token}",
    }

    response = requests.get(url, headers=headers)
    threads = response.json().get("threads", [])
    if not threads:
        print("No threads found.")
        return []
    for thread in threads:
        print(
            f"Thread ID: {thread.get('id')}, Name: {thread.get('name')}, Created At: {thread.get('createdAt')}"
        )
        thread_id_list.append(thread.get("id"))
    return thread_id_list


def del_thread():
    thread_id_list = get_thread_id()
    for thread_id in thread_id_list:
        url = f"{url_header}/api/agents/{agent_id}/threads/{thread_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Content-Type": "application/json",
            "x-xsrf-token": f"{x_xsrf_token}",
            "accept-language": "zh-CN,zh;q=0.9",
            "Cookie": f"accessToken={access_token}",
        }
        response = requests.delete(url, headers=headers)
        print(response.text)


def main():
    uvicorn.run("retool2api:app", host="0.0.0.0", port=10001, reload=True)


if __name__ == "__main__":
    print(f"Agent ID: {agent_id}")
    del_thread()
    main()
