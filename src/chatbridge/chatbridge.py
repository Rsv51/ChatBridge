from pydantic import BaseModel, Field
from typing import List, Union, Callable, Any
from fastapi.responses import StreamingResponse
import time
import uuid
from prompt.prompt import TOOLCALL_PRMPT
import re

# 常量定义
OBJECT_MODEL = "model"
OBJECT_LIST = "list"
OBJECT_CHAT_COMPLETION = "chat.completion"
OBJECT_CHAT_COMPLETION_CHUNK = "chat.completion.chunk"
FINISH_REASON_STOP = "stop"
FINISH_REASON_TOOL_CALLS = "tool_calls"
FINISH_REASON_NULL = "null"
ROLE_ASSISTANT = "assistant"
ROLE_SYSTEM = "system"
TOOL_TYPE_FUNCTION = "function"
PROVIDER_CHUTES = "Chutes"
FUNCTION_CALL_PATTERN = (
    r"<function_call>\s*<tool>(.*?)</tool>\s*<args>(.*?)</args>\s*</function_call>"
)
ARGS_PATTERN = r"<(\w+)>(.*?)</\1>"


# 请求体
class Model(BaseModel):
    id: str
    object: str
    created: int
    owned_by: str


# 请求model
class Models(BaseModel):
    object: str
    data: List[Model]


class ToolFunction(BaseModel):
    name: str
    description: str
    parameters: dict


class ToolCallFunction(BaseModel):
    name: str = Field(default="")
    arguments: str = Field(default_factory=str)


class ToolCalls(BaseModel):
    index: int = Field(default=0)
    id: str = Field(default_factory=lambda: f"call_{uuid.uuid4().hex}")
    type: str = TOOL_TYPE_FUNCTION
    function: ToolCallFunction = Field(default_factory=ToolCallFunction)


class Tools(BaseModel):
    function: ToolFunction = Field(default_factory=ToolFunction)
    tool_type: str = TOOL_TYPE_FUNCTION


class Messages(BaseModel):
    content: Union[str, List[dict], None]
    role: str
    tool_calls: List[ToolCalls] = Field(default_factory=list)


# 默认请求
class ChatResponse(BaseModel):
    messages: List[Messages]
    temperature: float = 0.0
    model: str = "gpt-4o"
    stream: bool = False
    tools: List[Tools] = Field(default_factory=list)


# 响应体
class Choice(BaseModel):
    index: int
    message: Messages
    finish_reason: str = FINISH_REASON_STOP


# 非流式
class CompletionRes(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[Choice]
    usage: dict


# 流式 含有delta
class ChoiceDelta(BaseModel):
    index: int = 0
    finish_reason: str = FINISH_REASON_NULL
    delta: dict = Field(default_factory=dict)


class StreamCompletionRes(BaseModel):
    id: str
    provider: str
    model: str
    object: str
    created: int
    choices: List[ChoiceDelta]


# 工具函数
def get_current_timestamp() -> int:
    """获取当前时间戳"""
    return int(time.time())


def generate_chat_completion_id() -> str:
    """生成聊天完成ID"""
    return f"chatcmpl-{uuid.uuid4().hex}"


def generate_tool_call_id() -> str:
    """生成工具调用ID"""
    return f"call_0_{uuid.uuid4().hex}"


def create_usage_dict() -> dict:
    """创建使用统计字典"""
    return {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }


def get_model_list(func: Callable) -> Callable:
    """获取模型列表装饰器"""

    def wrapper():
        model_ids = func()
        now = get_current_timestamp()
        models = Models(
            object=OBJECT_LIST,
            data=[
                Model(id=mid, object=OBJECT_MODEL, created=now, owned_by=owner)
                for mid, owner in model_ids
            ],
        )
        return models

    return wrapper


def extract_message_content(message: Messages) -> str:
    """提取消息内容"""
    if isinstance(message.content, str):
        return message.content
    else:
        return message.content[-1]["text"]


def is_tool_system_message(message: Messages) -> bool:
    """判断是否为工具系统消息"""
    return message.role == ROLE_SYSTEM and "Tool" in message.content


def build_tool_message(tools: List[Tools]) -> str:
    """构建工具消息"""
    tool_message = "<function_call>\n   "
    for tool in tools:
        tool_message += f"<tool>{tool.function.name}</tool>\n   "
        arguments = tool.function.parameters.get("properties", {})
        tool_message += f"<args>\n      "
        if arguments:
            for key, value in arguments.items():
                tool_message += f"<{key}>{value}</{key}>\n"
        else:
            tool_message += "<empty>no arguments</empty>\n"
        tool_message += "   </args>\n"
    tool_message += "</function_call>"
    return tool_message


def prepare_prompt_without_tools(messages: List[Messages]) -> tuple[str, bool]:
    """准备没有工具的提示"""
    is_new_session = False
    last_message = messages[-1]
    prompt = extract_message_content(last_message)

    if len(messages) == 2:
        for message in messages:
            if is_tool_system_message(message):
                is_new_session = True
                prompt = (
                    str(message.content)
                    + "\n\n你现在有权限使用所有工具\n"
                    + str(prompt)
                )
                break
    elif len(messages) == 1:
        is_new_session = True

    return prompt, is_new_session


def prepare_prompt_with_tools(
    messages: List[Messages], tools: List[Tools]
) -> tuple[str, bool]:
    """准备有工具的提示"""
    is_new_session = False
    tool_message = build_tool_message(tools)
    system_prompt = TOOLCALL_PRMPT.replace("{TOOLS_LIST}", tool_message)

    last_message = messages[-1]
    prompt = extract_message_content(last_message)

    if len(messages) == 1:
        is_new_session = True
        prompt = str(system_prompt) + str(prompt)
    if len(messages) == 2:
        for message in messages:
            if message.role == ROLE_SYSTEM:  # 两条消息,其中一条是system message
                is_new_session = True
                prompt = str(system_prompt) + str(prompt)
                break

    return prompt, is_new_session


def is_function_call(response: str) -> bool:
    """检查响应是否包含函数调用"""
    return "FC_USE" in response


def parse_function_call(response: str) -> dict:
    """解析函数调用"""
    match = re.search(FUNCTION_CALL_PATTERN, response, re.DOTALL)
    if not match:
        return {}

    function_name = match.group(1)
    args_block = match.group(2)
    arguments = re.findall(ARGS_PATTERN, args_block)

    argument_set = {}
    for arg in arguments:
        if arg[0] == "empty":
            argument_set = {}
            break
        else:
            argument_set[arg[0]] = arg[1]

    return {"function_name": function_name, "arguments": argument_set}


def create_tool_call_response(
    model: str, function_name: str, arguments: dict
) -> CompletionRes:
    """创建工具调用响应"""
    toolcalls = ToolCalls(
        index=0,
        id=generate_tool_call_id(),
        type=TOOL_TYPE_FUNCTION,
        function=ToolCallFunction(name=function_name, arguments=str(arguments)),
    )

    return CompletionRes(
        id=generate_chat_completion_id(),
        object=OBJECT_CHAT_COMPLETION,
        created=get_current_timestamp(),
        model=model,
        choices=[
            Choice(
                index=0,
                message=Messages(
                    content="", role=ROLE_ASSISTANT, tool_calls=[toolcalls]
                ),
                finish_reason=FINISH_REASON_TOOL_CALLS,
            )
        ],
        usage=create_usage_dict(),
    )


def create_normal_response(model: str, response: str) -> CompletionRes:
    """创建普通响应"""
    return CompletionRes(
        id=generate_chat_completion_id(),
        object=OBJECT_CHAT_COMPLETION,
        created=get_current_timestamp(),
        model=model,
        choices=[
            Choice(
                index=0,
                message=Messages(content=response, role=ROLE_ASSISTANT),
                finish_reason=FINISH_REASON_STOP,
            )
        ],
        usage=create_usage_dict(),
    )


def create_stream_tool_call_response(model: str, function_name: str, arguments: dict):
    """创建流式工具调用响应"""

    def event_stream():
        toolcalls = ToolCalls(
            index=0,
            id=generate_tool_call_id(),
            type=TOOL_TYPE_FUNCTION,
            function=ToolCallFunction(name=function_name, arguments=str(arguments)),
        )

        result = StreamCompletionRes(
            id=generate_chat_completion_id(),
            provider=PROVIDER_CHUTES,
            model=model,
            object=OBJECT_CHAT_COMPLETION_CHUNK,
            created=get_current_timestamp(),
            choices=[
                ChoiceDelta(
                    index=0,
                    delta={"tool_calls": [toolcalls.model_dump()]},
                    finish_reason=FINISH_REASON_TOOL_CALLS,
                )
            ],
        )
        yield f"data: {result.model_dump_json()}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def create_stream_normal_response(model: str, response: str):
    """创建流式普通响应"""

    def event_stream():
        result = StreamCompletionRes(
            id=generate_chat_completion_id(),
            provider=PROVIDER_CHUTES,
            model=model,
            object=OBJECT_CHAT_COMPLETION_CHUNK,
            created=get_current_timestamp(),
            choices=[
                ChoiceDelta(
                    index=0,
                    delta={"content": response},
                    finish_reason=FINISH_REASON_STOP,
                )
            ],
        )
        yield f"data: {result.model_dump_json()}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def chatCompletions(func: Callable) -> Callable:
    """聊天完成装饰器"""

    def wrapper(res: ChatResponse):
        model = res.model
        messages = res.messages

        # 准备提示和会话状态
        if not res.tools:
            prompt, is_new_session = prepare_prompt_without_tools(messages)
        else:
            prompt, is_new_session = prepare_prompt_with_tools(messages, res.tools)
        # 获取模型响应
        response = func(prompt, new_session=is_new_session, model=model)

        # 检查是否是函数调用
        if is_function_call(response):
            # 解析函数调用
            func_call_data = parse_function_call(response)
            if func_call_data:
                if res.stream:
                    # 流式函数调用响应
                    return create_stream_tool_call_response(
                        model,
                        func_call_data["function_name"],
                        func_call_data["arguments"],
                    )
                else:
                    # 非流式函数调用响应
                    return create_tool_call_response(
                        model,
                        func_call_data["function_name"],
                        func_call_data["arguments"],
                    )

        # 普通响应
        if res.stream:
            # 流式普通响应
            return create_stream_normal_response(model, response)
        else:
            # 非流式普通响应
            return create_normal_response(model, response)

    return wrapper
