from pydantic import BaseModel, Field
from typing import List, Union, Callable, Any
from fastapi.responses import StreamingResponse
import time
import uuid
from prompt.prompt import TOOLCALL_PRMPT
import re


# Constant definitions
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


# Request body
class Model(BaseModel):
    id: str
    object: str
    created: int
    owned_by: str


# Request models
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


# Default request
class ChatResponse(BaseModel):
    messages: List[Messages]
    temperature: float = 0.0
    model: str = "gpt-4o"
    stream: bool = False
    tools: List[Tools] = Field(default_factory=list)


# Response body
class Choice(BaseModel):
    index: int
    message: Messages
    finish_reason: str = FINISH_REASON_STOP


# Non-streaming
class CompletionRes(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[Choice]
    usage: dict


# Streaming with delta
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


# Utility functions
def get_current_timestamp() -> int:
    """Get current timestamp"""
    return int(time.time())


def generate_chat_completion_id() -> str:
    """Generate chat completion ID"""
    return f"chatcmpl-{uuid.uuid4().hex}"


def generate_tool_call_id() -> str:
    """Generate tool call ID"""
    return f"call_0_{uuid.uuid4().hex}"


def create_usage_dict() -> dict:
    """Create usage statistics dictionary"""
    return {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }


def get_model_list(func: Callable) -> Callable:
    """Get model list decorator"""

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
    """Extract message content"""
    if isinstance(message.content, str):
        return message.content
    else:
        return message.content[-1]["text"]


def is_tool_system_message(message: Messages) -> bool:
    """Check if it's a tool system message"""
    return message.role == ROLE_SYSTEM and "Tool" in message.content


def build_tool_message(tools: List[Tools]) -> str:
    """Build tool message"""
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
    """Prepare prompt without tools"""
    is_new_session = False
    last_message = messages[-1]
    prompt = extract_message_content(last_message)

    if len(messages) == 2:
        for message in messages:
            if is_tool_system_message(message):
                is_new_session = True
                prompt = (
                    str(message.content)
                    + "\n\nYou now have permission to use all tools\n"
                    + str(prompt)
                )
                break
    elif len(messages) == 1:
        is_new_session = True

    return prompt, is_new_session


def prepare_prompt_with_tools(
    messages: List[Messages], tools: List[Tools]
) -> tuple[str, bool]:
    """Prepare prompt with tools"""
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
            if (
                message.role == ROLE_SYSTEM
            ):  # Two messages, one of which is a system message
                is_new_session = True
                prompt = str(system_prompt) + str(prompt)
                break

    return prompt, is_new_session, system_prompt


def is_function_call(response: str) -> bool:
    """Check if response contains function call"""
    return "FC_USE" in response


def parse_function_call(response: str) -> dict:
    """Parse function call"""
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
    """Create tool call response"""
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
    """Create normal response"""
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
    """Create streaming tool call response"""

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
    """Create streaming normal response"""

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


def chatCompletions(build_all_prompt: int = 0):
    """Chat completion decorator"""

    def decorator(func: Callable) -> Callable:
        """Decorator function"""

        def wrapper(res: ChatResponse):
            model = res.model
            messages = res.messages

            # Prepare prompt and session state
            if not res.tools:
                prompt, is_new_session = prepare_prompt_without_tools(messages)
            else:
                prompt, is_new_session, tools_system_prompt = prepare_prompt_with_tools(
                    messages, res.tools
                )

            # For 2api websites, sometimes continuous conversation is not supported, so all messages need to be concatenated into one prompt
            if build_all_prompt:
                is_new_session = True
                if res.tools:
                    prompt = tools_system_prompt
                else:
                    prompt = ""
                for msg in messages:
                    role = msg.role
                    content = msg.content
                    if isinstance(content, list):
                        # Simple handling of multimodal content, only extract text parts
                        content = " ".join(
                            [
                                item.get("text", "")
                                for item in content
                                if item.get("type") == "text"
                            ]
                        )

                    # Add to prompt
                    if role == "system":
                        # System messages as prefix for Human messages
                        prompt += f"\n\nHuman: <system>{content}</system>"
                    elif role == "user":
                        prompt += f"\n\nHuman: {content}"
                    elif role == "assistant":
                        prompt += f"\n\nAssistant: {content}"
                    elif role == "tool":
                        # Tool messages as prefix for Tool messages
                        prompt += f"\n\nTool: <tool>{content}</tool>"

            # Get model response
            response = func(prompt, new_session=is_new_session, model=model)
            if response is None:
                return {"error": "No response from model"}

            # Check if it's a function call
            if is_function_call(response):
                # Parse function call
                func_call_data = parse_function_call(response)
                if func_call_data:
                    if res.stream:
                        # Streaming function call response
                        return create_stream_tool_call_response(
                            model,
                            func_call_data["function_name"],
                            func_call_data["arguments"],
                        )
                    else:
                        # Non-streaming function call response
                        return create_tool_call_response(
                            model,
                            func_call_data["function_name"],
                            func_call_data["arguments"],
                        )

            # Normal response
            if res.stream:
                # Streaming normal response
                return create_stream_normal_response(model, response)
            else:
                # Non-streaming normal response
                return create_normal_response(model, response)

        return wrapper

    return decorator
