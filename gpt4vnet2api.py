from chatbridge.chatbridge import *

# from curl_cffi import requests
import requests
from dotenv import load_dotenv
from fastapi import FastAPI
from datetime import datetime
import uvicorn
import hashlib
import os
import json


app = FastAPI(title="retool2api")


def getTaskId():

    url = "http://127.0.0.1:5000/turnstile?url=https://gpt4v.net&sitekey=0x4AAAAAAATOXAtQtziH-Rwq&action=issue_execution_token"

    response = requests.get(url)
    response.raise_for_status()
    return response.json()["task_id"]


def getCaptcha(task_id):

    url = f"http://127.0.0.1:5000/result?id={task_id}"

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


@app.get("/v1/models")
@get_model_list
def get_models():
    model_ids = [
        ("gpt-4o", "OpenAI"),
        ("claude-3-5-sonnet", "Anthropic"),
        ("DeepSeek-r1", "DeepSeek"),
    ]
    return model_ids


@app.post("/v1/chat/completions")
@chatCompletions(build_all_prompt=1)
def chat(prompt: str, res: ChatResponse, new_session: bool):
    if res.model == "claude-3-5-sonnet":
        res.model = "claude3"
    elif res.model == "gpt-4o":
        res.model = "gpt4o"
    elif res.model == "DeepSeek-r1":
        res.model = "deepseek"
    print(prompt, res.model, new_session)
    task_id = getTaskId()
    captcha = getCaptcha(task_id=task_id)
    print(captcha)
    uuid = hashlib.md5(captcha.encode()).hexdigest()
    url = f"https://gpt4vnet.erweima.ai/api/v1/chat/{res.model}/chat"

    current_time = datetime.now()

    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

    print(formatted_time)
    if res.model == "claude3":
        payload = {
            "prompt": prompt,
            "chatUuid": f"{uuid}",
            "sendTime": formatted_time,
            "attachments": [],
            "firstQuestionFlag": True,
            "searchFlag": False,
            "language": "zh-CN",
        }
    elif res.model == "deepseek":
        payload = {
            "prompt": prompt,
            "sessionId": f"{uuid}",
            "sendTime": formatted_time,
            "attachments": [],
            "firstQuestionFlag": True,
            "searchFlag": False,
            "thinkFlag": False,
            "language": "zh-CN",
        }
    else:
        payload = {
            "prompt": prompt,
            "sessionId": f"{uuid}",
            "attachments": [],
        }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Content-Type": "application/json",
        "accept-language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
        "referer": "https://gpt4v.net/",
        "authorization": "",
        "uniqueid": f"{captcha}",
        "verify": "",
        "origin": "https://gpt4v.net",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "priority": "u=4",
        "te": "trailers",
        "Cookie": "",
    }

    response = requests.post(
        url,
        data=json.dumps(payload),
        headers=headers,
        stream=True,
    )
    response.raise_for_status()
    lines = response.iter_lines()
    content = ""
    for line in lines:
        try:
            print(f"line: {line.decode()}")
            if "DONE" in line.decode():
                print("DONE")
                break
            if res.model == "claude3" or res.model == "gpt4o":
                json_line = json.loads(line.decode())
                if json_line.get("data", {}).get("recipient", "") == "title_generation":
                    continue
                content += json_line.get("data", {}).get("message", "")
            elif res.model == "deepseek":
                json_line = json.loads(line.decode())
                content += json_line.get("data", {}).get("content", "")
        except Exception as e:
            return {"error": str(e)}
    return content


def main():
    uvicorn.run("gpt4vnet2api:app", host="0.0.0.0", port=10006, reload=True)


if __name__ == "__main__":
    main()
